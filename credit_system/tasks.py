# credit_system/tasks.py (MODIFIED to read XLSX)

from celery import shared_task
import pandas as pd
from datetime import date
from django.db import transaction
from .models import Customer, Loan

@shared_task
def ingest_initial_data():
    # Use the simple, corrected XLSX names
    CUSTOMER_FILE = "customer_data.xlsx"
    LOAN_FILE = "loan_data.xlsx"
    
    # --- Load and Prepare Data ---
    # !!! CRITICAL CHANGE: Use pd.read_excel() !!!
    # This assumes your Excel files have data in the first sheet (Sheet1)
    customer_df = pd.read_excel(CUSTOMER_FILE)
    loan_df = pd.read_excel(LOAN_FILE) 

    # Rename columns explicitly (in case headers are slightly different after Excel read)
    customer_df.columns = ['customer_id', 'first_name', 'last_name', 'age', 'phone_number', 'monthly_salary', 'approved_limit']
    loan_df.columns = ['customer_id', 'loan_id', 'loan_amount', 'tenure', 'interest_rate', 'monthly_installment', 'emis_paid_on_time', 'start_date', 'end_date']

    # Convert date columns (pd.read_excel often does a good job, but we ensure it)
    loan_df['start_date'] = pd.to_datetime(loan_df['start_date']).dt.date
    loan_df['end_date'] = pd.to_datetime(loan_df['end_date']).dt.date
    
    # ... rest of the ingestion logic continues as before ...
    # ... (No further changes needed below this point) ...
    today = date.today()

    # Determine active loans
    loan_df['is_active'] = loan_df['end_date'].apply(lambda x: x > today)

    # Calculate Current Debt and Total Current EMI
    active_loans_df = loan_df[loan_df['is_active'] == True]
    
    # Group by customer to find debt and EMI sum
    debt_emi_group = active_loans_df.groupby('customer_id').agg(
        current_debt=('loan_amount', 'sum'),
        total_current_emi=('monthly_installment', 'sum')
    )
    
    # Merge calculations back to customer data
    customer_df = customer_df.merge(debt_emi_group, on='customer_id', how='left').fillna(0)

    # --- Database Ingestion ---
    with transaction.atomic():
        # 1. Ingest Customers
        customer_objects = [
            Customer(
                customer_id=row['customer_id'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                age=row['age'],
                phone_number=row['phone_number'],
                monthly_salary=row['monthly_salary'],
                approved_limit=row['approved_limit'],
                current_debt=row['current_debt'],
                total_current_emi=row['total_current_emi']
            ) for index, row in customer_df.iterrows()
        ]
        Customer.objects.bulk_create(customer_objects, ignore_conflicts=True)
        
        # 2. Ingest Loans
        loan_objects = [
            Loan(
                loan_id=row['loan_id'],
                customer_id=row['customer_id'], # Use customer_id_id when working with bulk_create ForeignKeys
                loan_amount=row['loan_amount'],
                tenure=row['tenure'],
                interest_rate=row['interest_rate'],
                monthly_installment=row['monthly_installment'],
                emis_paid_on_time=row['emis_paid_on_time'],
                start_date=row['start_date'],
                end_date=row['end_date'],
                is_active=row['is_active']
            ) for index, row in loan_df.iterrows()
        ]
        Loan.objects.bulk_create(loan_objects, ignore_conflicts=True)
    
    return "Data ingestion complete!"