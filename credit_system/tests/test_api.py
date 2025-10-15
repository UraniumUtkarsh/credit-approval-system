# credit_system/tests/test_api.py

from rest_framework.test import APITestCase
from rest_framework import status
from credit_system.models import Customer
from decimal import Decimal

class RegisterAPITest(APITestCase):
    
    def test_successful_registration(self):
        url = '/register'
        data = {
            "first_name": "Test",
            "last_name": "User",
            "age": 40,
            "monthly_income": 100000,
            "phone_number": 9988776655
        }
        
        response = self.client.post(url, data, format='json')
        
        # 1. Check HTTP Status
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 2. Check Database Insertion
        self.assertEqual(Customer.objects.count(), 1)
        
        # 3. Check Approved Limit Calculation (36 * 100k = 3.6M, rounded to nearest lakh)
        self.assertEqual(response.data['approved_limit'], 3600000)
        
        # 4. Check Response Structure
        self.assertIn('customer_id', response.data)
        self.assertEqual(response.data['age'], 40)

    def test_duplicate_phone_number_rejection(self):
        # Create one customer first
        Customer.objects.create(
            customer_id=1, first_name="A", last_name="B", age=30, phone_number=1111111111,
            monthly_salary=Decimal(50000), approved_limit=1800000
        )
        
        url = '/register'
        duplicate_data = {
            "first_name": "Dup",
            "last_name": "User",
            "age": 25,
            "monthly_income": 50000,
            "phone_number": 1111111111 # Duplicate phone number
        }
        
        response = self.client.post(url, duplicate_data, format='json')
        
        # Expect 409 Conflict
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Customer.objects.count(), 1) # No new customer created