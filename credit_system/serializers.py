# credit_system/serializers.py

from rest_framework import serializers
from .models import Customer, Loan

# --- 1. /register Serializers ---
class CustomerRegisterRequestSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField(min_value=18)
    monthly_income = serializers.IntegerField(min_value=1)
    phone_number = serializers.IntegerField()

class CustomerRegisterResponseSerializer(serializers.ModelSerializer):
    # Map 'monthly_salary' from model to 'monthly_income' in response
    monthly_income = serializers.DecimalField(source='monthly_salary', max_digits=10, decimal_places=2)

    class Meta:
        model = Customer
        # Include all required fields
        fields = ('customer_id', 'first_name', 'last_name', 'age', 'monthly_income', 'approved_limit', 'phone_number')
        read_only_fields = fields # Since this is a response serializer

# --- 2. /check-eligibility & /create-loan Request Serializers ---
class LoanRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1000)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0.0)
    tenure = serializers.IntegerField(min_value=1)

# --- 3. /check-eligibility Response Serializer ---
class EligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    corrected_interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()
    monthly_installment = serializers.DecimalField(max_digits=10, decimal_places=2)

# --- 4. /create-loan Response Serializer ---
class CreateLoanResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField(allow_null=True)
    customer_id = serializers.IntegerField()
    loan_approved = serializers.BooleanField()
    message = serializers.CharField()
    monthly_installment = serializers.DecimalField(max_digits=10, decimal_places=2)

# --- 5. /view-loan/{loan_id} Response Serializers ---
class CustomerLoanViewSerializer(serializers.ModelSerializer):
    # Only need specific fields for loan view
    class Meta:
        model = Customer
        fields = ('customer_id', 'first_name', 'last_name', 'phone_number', 'age')

class LoanViewResponseSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField()
    customer = CustomerLoanViewSerializer()
    loan_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    monthly_installment = serializers.DecimalField(max_digits=10, decimal_places=2)
    tenure = serializers.IntegerField()

# --- 6. /view-loans/{customer_id} (List Item) Response Serializer ---
class CustomerLoansListItemSerializer(serializers.Serializer):
    loan_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    monthly_installment = serializers.DecimalField(max_digits=10, decimal_places=2)
    repayments_left = serializers.IntegerField()