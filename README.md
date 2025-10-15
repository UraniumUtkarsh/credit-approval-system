# Credit Approval System Backend API
This project implements a Credit Approval System API using Django 4+, Django Rest Framework (DRF), PostgreSQL as the database, and Celery for background data ingestion. The entire application stack is containerized using Docker Compose, allowing it to be started with a single command.
---
# 🚀 Setup and Execution
## Prerequisites
You must have Docker Desktop (or Docker Engine and Docker Compose Plugin) installed and running on your system.

## Running the Application
1. Clone the Repository:
```bash
copy code
git clone https://github.com/UraniumUtkarsh/credit-approval-system.git
cd credit-approval-system
```
2. Create and activate Python Virtual Environment
```bash
python -m venv venv
```
- On Windows:
```bash
.\venv\Scripts\activate
```
- On macOS/Linux:
```bash
source venv/bin/activate
```

3. Install local dependencies
```bash
pip install -r requirements.txt
```

4. Start Services (Database, Web, Worker, Redis):
Execute this command in the project root where docker-compose.yml resides. This command builds the application image, starts all four services, and makes the application available on port 8000.
```bash
docker-compose up --build
```
Wait for all services to initialize. The postgres_db and celery_worker logs should show they are ready.
5. Run Migrations:
While the containers are running, open a second terminal and run migrations to create the database tables:
```bash
docker compose run web python manage.py migrate
```
6. Ingest Initial Data (Background Task):
Trigger the Celery background task to load data from customer_data.xlsx and loan_data.xlsx into the PostgreSQL database.
```bash
docker compose run web python manage.py ingest_data
```
(Verify the data ingestion completes successfully by checking the logs in the first terminal, specifically the output from the celery_worker container).

# 💡 Core Logic: Credit Score & Eligibility
The application's core logic, residing in credit_system/services.py, calculates a credit score (out of 100) based on historical data and applies two mandatory checks:

|-------------|----------------------|-----------------|
|Credit Score |Minimum Interest Rate | Approval Status |
|-------------|----------------------|-----------------|
|CS > 50 |Requested Rat | Approved |
|50 > CS > 30 | 12.0% | Approved (Rate corrected if needed) |
|30 > CS > 10 | 16.0% | Approved (Rate corrected if needed) |
|CS < 10 | NA | Rejected |

### Mandatory Rejection Rules:
1. If the sum of current loans (Customer.current_debt) + the requested loan_amount exceeds the Customer.approved_limit, the Credit Score is automatically 0.
2. If the sum of all current monthly EMIs (Customer.total_current_emi) is greater than 50% of Customer.monthly_salary, the loan is rejected.

# 🔌 API Endpoints Documentation
All endpoints are accessible via the base URL: `http://localhost:8000`
1. `/register` (POST)
- Registers a new customer.
- Calculates and sets the customer's approved credit limit.

---

## **1. `/register` (POST)**
Registers a new customer.

### **Fields**
| Field | Description |
|--------|-------------|
| `monthly_income` | Monthly income of the individual. |
| `approved_limit` | Calculated as `36 * monthly_income`, rounded to the nearest lakh (100,000). |

### **Example Request (Windows Curl Syntax)**
```bash
curl -X POST http://localhost:8000/register ^
     -H "Content-Type: application/json" ^
     -d "{\"first_name\": \"Test\", \"last_name\": \"User\", \"age\": 30, \"monthly_income\": 95000, \"phone_number\": 9998887776}"
```

## **2. `check-eligibility` (POST)**
- Checks loan eligibility based on the calculated credit score.
- Returns the approval status, corrected interest rate, and calculated EMI.
### **Example Request (Windows Curl)**
```bash
curl -X POST http://localhost:8000/check-eligibility ^
     -H "Content-Type: application/json" ^
     -d "{\"customer_id\": 1, \"loan_amount\": 100000, \"interest_rate\": 8.0, \"tenure\": 12}"
```

## **3. `/create-loan` (POST)**
- Processes the loan only if eligibility checks pass.
- If approved, persists the new `Loan` record.
- Updates the `Customer.current_debt` and `Customer.total_current_emi` fields in an atomic transaction.

### **Example Request (Windows Curl)**
```bash
curl -X POST http://localhost:8000/create-loan ^
     -H "Content-Type: application/json" ^
     -d "{\"customer_id\": 1, \"loan_amount\": 100000, \"interest_rate\": 12.0, \"tenure\": 12}"
```

## **4. `/view-loan/<loan_id>` (GET)**
- Retrieves full details for a specific loan.
- Includes nested JSON object containing customer information.
### **Example Request (Windows Curl)**
```bash
curl -X GET http://localhost:8000/view-loan/5930
```

## **5. `/view-loans/<customer_id>` (GET)**
- Retrieves a list of all current (active) loans associated with a specific customer ID.
- Calculates and includes `repayments_left` for each loan.

### **Example Request (Windows Curl)**
```bash
curl -X GET http://localhost:8000/view-loans/1
```