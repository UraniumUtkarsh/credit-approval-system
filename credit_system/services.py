from datetime import date
from decimal import Decimal
from typing import Dict, Any

# Import necessary local components
from .models import Customer, Loan
from .utils import calculate_monthly_installment 

# --- Constants for Scoring & Eligibility ---
# Score components defined in the assignment, with logical weightage added.
SCORE_WEIGHTS = {
    'on_time_payment': 40,
    'loan_volume': 20,
    'activity': 15,
    'approved_volume': 15,
    'limit_check': 10 # Binary check (0 or 10)
}

# Interest rate slabs based on credit score
MIN_INTEREST_RATES = {
    'tier_2': Decimal('12.0'), # For 50 > score > 30
    'tier_3': Decimal('16.0'), # For 30 > score > 10
}

def calculate_credit_score(customer: Customer, requested_loan_amount: Decimal) -> int:
    """
    Calculates the credit score (0-100) based on historical loan data.
    
    The score is based on: Past Loans Paid on Time (40), No of Loans Taken (20), 
    Loan Activity (15), Approved Volume (15), and Debt-to-Limit (10).
    """
    
    today = date.today()
    # Use related manager to fetch all loans efficiently
    all_loans = customer.loans.all() 
    
    current_score = 0
    total_emis_paid = 0
    total_emis_due = 0
    total_closed_loans = 0
    total_approved_volume = Decimal(0)
    has_recent_default = False # Simplified flag for Loan activity (iii)

    # 1. CRITICAL CHECK (Component V): Debt-to-Limit Check (Highest Priority)
    # If sum of current loans of customer > approved limit of customer, credit score = 0
    if customer.current_debt + requested_loan_amount > customer.approved_limit:
        return 0 
    
    current_score += SCORE_WEIGHTS['limit_check'] # 10 points granted if within limit

    # --- Aggregate Loan Metrics ---
    for loan in all_loans:
        total_emis_paid += loan.emis_paid_on_time
        total_emis_due += loan.tenure
        total_approved_volume += loan.loan_amount
        
        if loan.end_date <= today:
            total_closed_loans += 1

        # Check for loan activity in current year (Component iii)
        # Simplified Check: If the loan was approved in the current year AND 
        # EMIs paid are significantly less than expected, flag a default risk.
        if loan.start_date.year == today.year:
             expected_emis = (today.year - loan.start_date.year) * 12 + (today.month - loan.start_date.month)
             if expected_emis > 0 and (loan.emis_paid_on_time / expected_emis) < 0.5:
                 has_recent_default = True

    # --- Score Calculation based on Weights ---
    
    # i. Past Loans Paid on Time (Max 40 points)
    if total_emis_due > 0: 
        on_time_ratio = total_emis_paid / total_emis_due
        current_score += round(SCORE_WEIGHTS['on_time_payment'] * on_time_ratio)

    # ii. No of loans taken in past (Max 20 points)
    # Score based on number of closed loans (e.g., 5 points per closed loan, max 4)
    score_from_volume = min(total_closed_loans * 5, SCORE_WEIGHTS['loan_volume'])
    current_score += score_from_volume

    # iv. Loan Approved Volume (Max 15 points)
    # Scale based on total historical volume
    volume_threshold_high = Decimal(5000000) 
    volume_threshold_medium = Decimal(1000000)
    
    if total_approved_volume >= volume_threshold_high:
        current_score += SCORE_WEIGHTS['approved_volume']
    elif total_approved_volume >= volume_threshold_medium:
        current_score += 5
        
    # iii. Loan activity in current year (Max 15 points)
    # If no recent defaults found, grant full points
    if not has_recent_default:
        current_score += SCORE_WEIGHTS['activity']

    return min(current_score, 100) # Ensure score is capped at 100


def check_loan_eligibility(customer: Customer, loan_amount: Decimal, requested_rate: Decimal, tenure: int) -> Dict[str, Any]:
    """
    Determines loan approval, handles the 50% EMI-to-salary check, 
    calculates the corrected rate, and finds the monthly installment.
    """
    
    # --- 1. Calculate Credit Score ---
    credit_score = calculate_credit_score(customer, loan_amount)
    
    # --- 2. CRITICAL PRE-CHECK: EMI-to-Salary Ratio ---
    # Assignment rule: If sum of all current EMIs > 50% of monthly salary, DON'T approve
    salary_limit = customer.monthly_salary / Decimal(2)
    
    if customer.total_current_emi > salary_limit:
        return {
            'approval': False,
            'corrected_interest_rate': requested_rate,
            'monthly_installment': Decimal(0),
            'message': 'Total current EMIs exceed 50% of monthly salary.',
            'credit_score': credit_score,
        }

    # --- 3. Eligibility and Rate Correction Logic ---
    
    approved = False
    corrected_rate = requested_rate
    required_min_rate = Decimal(0)

    # Determine approval status and required minimum rate based on score slabs
    if credit_score > 50:
        approved = True
        # Rate is approved (required_min_rate remains 0)
    elif 30 < credit_score <= 50:
        approved = True
        required_min_rate = MIN_INTEREST_RATES['tier_2'] # 12.0%
    elif 10 < credit_score <= 30:
        approved = True
        required_min_rate = MIN_INTEREST_RATES['tier_3'] # 16.0%
    else: # credit_score <= 10
        approved = False
        
    # --- 4. Interest Rate Correction ---
    
    # If approved, check if the requested rate meets the required minimum slab rate
    if approved and requested_rate < required_min_rate:
        corrected_rate = required_min_rate
    
    # --- 5. Final EMI Calculation (Use corrected rate if approved) ---
    emi_rate = corrected_rate if approved else Decimal(0) 
    monthly_installment = calculate_monthly_installment(loan_amount, emi_rate, tenure) if approved else Decimal(0)
    
    return {
        'approval': approved,
        'interest_rate': requested_rate, 
        'corrected_interest_rate': corrected_rate,
        'tenure': tenure,
        'monthly_installment': monthly_installment,
        'credit_score': credit_score,
        'message': 'Loan approved.' if approved else 'Credit score too low for loan approval.'
    }
