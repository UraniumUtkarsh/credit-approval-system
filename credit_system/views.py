from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView
from decimal import Decimal
from datetime import date
import pandas as pd # Used for robust date calculations in CreateLoanView

# Assuming all necessary models, serializers, and services are defined and importable
from .models import Customer, Loan
from .serializers import (
    CustomerRegisterRequestSerializer, 
    EligibilityResponseSerializer,
    LoanRequestSerializer,
    CreateLoanResponseSerializer,
    LoanViewResponseSerializer,
    CustomerLoansListItemSerializer
)
from .services import check_loan_eligibility # Contains Credit Score and Eligibility Logic

# --- 1. POST /register ---
class RegisterCustomerView(APIView):
    """
    Endpoint to add a new customer and calculate their approved limit.
    POST /register
    """
    def post(self, request):
        serializer = CustomerRegisterRequestSerializer(data=request.data)
        
        # 1. Validate Input
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        monthly_salary = data['monthly_income']
        phone_number = data['phone_number']

        # Check for existing phone number to prevent duplicates
        if Customer.objects.filter(phone_number=phone_number).exists():
            return Response({
                "message": "Customer with this phone number already exists."
            }, status=status.HTTP_409_CONFLICT)

        # 2. Calculate Approved Limit (36 * monthly_salary, rounded to nearest lakh)
        calculated_limit = Decimal(36) * Decimal(monthly_salary)
        
        # Round to the nearest lakh (100,000)
        nearest_lakh = Decimal(100000)
        # Rounding rule: round(x / 100k) * 100k
        approved_limit = int(round(calculated_limit / nearest_lakh) * nearest_lakh)

        # 3. Get the next available customer_id
        try:
            latest_id = Customer.objects.latest('customer_id').customer_id
            new_customer_id = latest_id + 1
        except Customer.DoesNotExist:
            new_customer_id = 1
        
        # 4. Create and Save New Customer
        try:
            customer = Customer.objects.create(
                customer_id=new_customer_id,
                first_name=data['first_name'],
                last_name=data['last_name'],
                age=data['age'],
                phone_number=phone_number,
                monthly_salary=monthly_salary,
                approved_limit=approved_limit,
                current_debt=0, 
                total_current_emi=0
            )
        except IntegrityError as e:
            return Response({"error": f"Database error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 5. Format and Return Response (HTTP 201 Created)
        response_data = {
            "customer_id": customer.customer_id,
            "name": f"{customer.first_name} {customer.last_name}",
            "age": customer.age,
            "monthly_income": customer.monthly_salary,
            "approved_limit": customer.approved_limit,
            "phone_number": customer.phone_number,
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)

# --- 2. POST /check-eligibility ---
class CheckEligibilityView(APIView):
    """
    Endpoint to check loan eligibility based on credit score.
    POST /check-eligibility
    """
    def post(self, request):
        serializer = LoanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # 1. Retrieve Customer (Handle 404)
        customer = get_object_or_404(Customer, customer_id=data['customer_id'])
        
        # 2. Run Eligibility Service
        eligibility_result = check_loan_eligibility(
            customer=customer,
            loan_amount=data['loan_amount'],
            requested_rate=data['interest_rate'],
            tenure=data['tenure']
        )
        
        # 3. Format Response
        response_data = {
            'customer_id': customer.customer_id,
            'approval': eligibility_result['approval'],
            'interest_rate': data['interest_rate'], # Original requested rate
            'corrected_interest_rate': eligibility_result['corrected_interest_rate'],
            'tenure': data['tenure'],
            'monthly_installment': eligibility_result['monthly_installment'],
        }

        # The EligibilityResponseSerializer ensures the final output structure is correct
        response_serializer = EligibilityResponseSerializer(response_data)
        
        # Return 200 OK for a check, regardless of approval status
        return Response(response_serializer.data, status=status.HTTP_200_OK)

# --- 3. POST /create-loan ---
class CreateLoanView(APIView):
    """
    Endpoint to process a new loan based on eligibility.
    POST /create-loan
    """
    def post(self, request):
        serializer = LoanRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        customer = get_object_or_404(Customer, customer_id=data['customer_id'])
        
        # 1. Run Eligibility Check
        eligibility_result = check_loan_eligibility(
            customer=customer,
            loan_amount=data['loan_amount'],
            requested_rate=data['interest_rate'],
            tenure=data['tenure']
        )
        
        loan_approved = eligibility_result['approval']
        loan_id = None
        message = eligibility_result['message']
        monthly_installment = eligibility_result['monthly_installment']
        
        if loan_approved:
            # 2. Database Write (Atomic Transaction)
            with transaction.atomic():
                # Find the next available loan ID
                try:
                    latest_loan = Loan.objects.latest('loan_id').loan_id
                    new_loan_id = latest_loan + 1
                except Loan.DoesNotExist:
                    new_loan_id = 1
                
                # Calculate end date robustly
                today_date = date.today()
                # Create a simple date offset object for calculation
                end_date_offset = pd.DateOffset(months=data['tenure'])
                # Get the result from adding the offset, then extract the date part
                end_date = (pd.to_datetime(today_date) + end_date_offset).date()
                    
                # a. Create Loan Record
                new_loan = Loan.objects.create(
                    loan_id=new_loan_id,
                    customer=customer,
                    loan_amount=data['loan_amount'],
                    tenure=data['tenure'],
                    interest_rate=eligibility_result['corrected_interest_rate'],
                    monthly_installment=monthly_installment,
                    emis_paid_on_time=0,
                    start_date=today_date,
                    end_date=end_date,
                    is_active=True
                )
                loan_id = new_loan.loan_id
                message = "Loan approved and processed successfully."

                # b. Update Customer Debt/EMI
                customer.current_debt += data['loan_amount']
                customer.total_current_emi += monthly_installment
                customer.save(update_fields=['current_debt', 'total_current_emi'])

        # 3. Format and Return Response
        response_data = {
            'loan_id': loan_id,
            'customer_id': customer.customer_id,
            'loan_approved': loan_approved,
            'message': message,
            'monthly_installment': monthly_installment,
        }

        # Use the response serializer for clean output
        return Response(response_data, status=status.HTTP_201_CREATED if loan_approved else status.HTTP_200_OK)

# --- 4. GET /view-loan/{loan_id} ---
class ViewLoanDetailsView(RetrieveAPIView):
    """
    View loan details and customer details.
    GET /view-loan/{loan_id}
    """
    queryset = Loan.objects.all()
    serializer_class = LoanViewResponseSerializer
    lookup_field = 'loan_id' 
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Manually prepare the nested customer JSON structure
        customer_data = {
            'customer_id': instance.customer.customer_id,
            'first_name': instance.customer.first_name,
            'last_name': instance.customer.last_name,
            'phone_number': instance.customer.phone_number,
            'age': instance.customer.age,
        }

        response_data = {
            'loan_id': instance.loan_id,
            'customer': customer_data,
            'loan_amount': instance.loan_amount,
            'interest_rate': instance.interest_rate,
            'monthly_installment': instance.monthly_installment,
            'tenure': instance.tenure,
        }
        
        return Response(response_data, status=status.HTTP_200_OK)

# --- 5. GET /view-loans/{customer_id} ---
class ViewCustomerLoansView(APIView):
    """
    View all current loan details by customer ID.
    GET /view-loans/{customer_id}
    """
    def get(self, request, customer_id):
        customer = get_object_or_404(Customer, customer_id=customer_id)
        
        # Filter for active loans (end_date in the future)
        active_loans = Loan.objects.filter(customer=customer, end_date__gt=date.today())
        
        loan_list = []
        for loan in active_loans:
            # Calculate Repayments Left: Tenure - EMIs Paid On Time
            repayments_left = loan.tenure - loan.emis_paid_on_time
            
            loan_list.append({
                'loan_id': loan.loan_id,
                'loan_amount': loan.loan_amount,
                'interest_rate': loan.interest_rate,
                'monthly_installment': loan.monthly_installment,
                'repayments_left': repayments_left,
            })
            
        # The list serializer handles the list structure
        serializer = CustomerLoansListItemSerializer(loan_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
