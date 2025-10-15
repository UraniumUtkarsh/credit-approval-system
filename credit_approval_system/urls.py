from django.contrib import admin
from django.urls import path

# Import all five implemented views from your app
from credit_system.views import (
    RegisterCustomerView, 
    CheckEligibilityView, 
    CreateLoanView, 
    ViewLoanDetailsView, 
    ViewCustomerLoansView 
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 1. POST /register
    path('register', RegisterCustomerView.as_view(), name='register-customer'),
    
    # 2. POST /check-eligibility
    path('check-eligibility', CheckEligibilityView.as_view(), name='check-eligibility'),
    
    # 3. POST /create-loan
    path('create-loan', CreateLoanView.as_view(), name='create-loan'),
    
    # 4. GET /view-loan/{loan_id} - Uses Django path converter for integer ID
    path('view-loan/<int:loan_id>', ViewLoanDetailsView.as_view(), name='view-loan-details'),
    
    # 5. GET /view-loans/{customer_id} - Uses Django path converter for integer ID
    path('view-loans/<int:customer_id>', ViewCustomerLoansView.as_view(), name='view-customer-loans'),
]
