from decimal import Decimal

def calculate_monthly_installment(principal, annual_interest_rate, tenure_months):
    """
    Calculates the Equal Monthly Installment (EMI) using the compound interest formula.
    
    EMI = P * [ r * (1 + r)^n ] / [ (1 + r)^n - 1 ]
    Where:
    P = Principal (loan_amount)
    r = Monthly Interest Rate (annual_interest_rate / 1200)
    n = Tenure in Months
    
    :param principal: Requested loan amount (Decimal).
    :param annual_interest_rate: Annual rate percentage (Decimal).
    :param tenure_months: Loan duration in months (int).
    :return: Monthly installment amount (Decimal).
    """
    principal = Decimal(principal)
    annual_interest_rate = Decimal(annual_interest_rate)
    tenure_months = int(tenure_months)

    # Handle 0% interest rate case (Simple division)
    if annual_interest_rate == 0:
        if tenure_months == 0:
            return Decimal(0)
        # Round to two decimal places for currency consistency
        return (principal / tenure_months).quantize(Decimal('0.01'))

    # 1. Calculate Monthly Interest Rate (r)
    # Rate is given as percentage (e.g., 12.0), so divide by 100 * 12 = 1200
    r = annual_interest_rate / Decimal(1200) 

    # 2. Calculate EMI using the compound interest formula
    
    # Exponent part: (1 + r)^n
    pow_r_n = ((1 + r) ** tenure_months)
    
    # Numerator: P * r * (1 + r)^n
    numerator = principal * r * pow_r_n
    
    # Denominator: (1 + r)^n - 1
    denominator = pow_r_n - 1

    if denominator == 0:
        return Decimal(0)

    emi = numerator / denominator
    
    # Round to two decimal places for currency
    return emi.quantize(Decimal('0.01'))
