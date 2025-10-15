# credit_system/models.py
from django.db import models

class Customer(models.Model):
    customer_id = models.IntegerField(primary_key=True) 
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    age = models.IntegerField()
    phone_number = models.BigIntegerField(unique=True) 
    monthly_salary = models.DecimalField(max_digits=10, decimal_places=2)
    approved_limit = models.IntegerField() 
    current_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)

    # Added to easily calculate total monthly EMI load for eligibility check
    total_current_emi = models.DecimalField(max_digits=12, decimal_places=2, default=0.0) 

class Loan(models.Model):
    loan_id = models.IntegerField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='loans')
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    tenure = models.IntegerField()
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    monthly_installment = models.DecimalField(max_digits=10, decimal_places=2)
    emis_paid_on_time = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Used for credit scoring and current debt calculation
    is_active = models.BooleanField(default=True)