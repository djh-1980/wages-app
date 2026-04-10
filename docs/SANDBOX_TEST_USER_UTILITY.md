# HMRC Sandbox Test User Creation Utility

⚠️ **WARNING: SANDBOX TESTING ONLY**  
This feature is for development and testing purposes only.  
**Remove all sandbox-related files before production deployment.**

---

## Overview

The HMRC Sandbox Test User Utility automates the creation of stateful test users and businesses for MTD ITSA sandbox testing. It eliminates the manual process of creating test users via HMRC's web interface.

### What It Does

1. **Creates Test Individual** - Generates a test user with NINO, SA UTR, and credentials
2. **Creates Test Business** - Sets up a self-employment business for the test user
3. **Stores Credentials** - Saves all details in SQLite for easy access
4. **Updates .env** - Auto-populates test credentials for quick testing

---

## Files Included

### Backend

- **`migrations/005_hmrc_sandbox_test_users.sql`** - Database schema for test users
- **`app/services/hmrc_sandbox.py`** - Service layer for test user creation
- **`app/routes/api_hmrc_sandbox.py`** - API routes for sandbox operations

### Frontend

- **`templates/mtd_sandbox.html`** - Dashboard UI for test user management
- **`static/js/mtd-sandbox.js`** - JavaScript for dashboard functionality

### Configuration

- **`.env`** - Added `HMRC_TEST_NINO` and `HMRC_TEST_BUSINESS_ID` fields

---

## How It Works

### Step 1: Create Test Individual

Uses HMRC's **Create Test User API** to generate a test individual:

```
POST https://test-api.service.hmrc.gov.uk/create-test-user/individuals
```

**Request:**
```json
{
  "serviceNames": [
    "mtd-income-tax",
    "self-assessment",
    "national-insurance"
  ]
}
```

**Response:**
```json
{
  "userId": "user123456789",
  "password": "password123",
  "nino": "AA123456A",
  "saUtr": "1234567890",
  "userFullName": "Test User",
  "emailAddress": "test@example.com"
}
```

### Step 2: OAuth Authentication

The test user must authenticate via OAuth to obtain an access token. This is done through the standard HMRC MTD OAuth flow.

### Step 3: Create Test Business

Uses **Self Assessment Test Support API** to create a self-employment business:

```
POST https://test-api.service.hmrc.gov.uk/individuals/business/details/{nino}/self-employment
```

**Request:**
```json
{
  "accountingType": "CASH",
  "typeOfBusiness": "self-employment",
  "tradingName": "TVS Test Business",
  "addressDetails": {
    "addressLine1": "1 Test Street",
    "addressLine2": "Manchester",
    "postcode": "M1 1AA",
    "countryCode": "GB"
  },
  "commencementDate": "2024-04-06"
}
```

**Response:**
```json
{
  "businessId": "XAIS12345678901"
}
```

### Step 4: Store & Update

- Stores all details in `sandbox_test_users` table
- Updates `.env` file with `HMRC_TEST_NINO` and `HMRC_TEST_BUSINESS_ID`
- Deactivates any previous test users

---

## Usage Instructions

### Access the Dashboard

Navigate to: **http://localhost:5001/mtd/sandbox**

You'll see a red warning banner indicating this is sandbox-only.

### Create a New Test User

1. Click **"Create New Test User"** button
2. Wait for the API call to complete (5-10 seconds)
3. A modal will display the test user credentials:
   - User ID
   - Password
   - NINO
   - SA UTR
4. **Save these credentials** - you'll need them for OAuth authentication

### Authenticate the Test User

1. Go to HMRC MTD settings page
2. Click **"Connect to HMRC"**
3. Use the **User ID** and **Password** from the modal
4. Complete the OAuth flow
5. Return to the sandbox dashboard

### Create Test Business

1. Click **"Create Test Business"** button
2. The system will use your OAuth session to create the business
3. Business details will be displayed:
   - Business ID
   - Trading Name
   - Accounting Type
   - Commencement Date

### Copy Credentials

Use the **Copy** buttons next to each field to quickly copy:
- NINO
- Business ID
- SA UTR
- User ID

These can be pasted into API testing tools or test scripts.

---

## API Endpoints

### Create Test User

```
POST /api/hmrc/sandbox/create-test-user
```

**Response:**
```json
{
  "success": true,
  "message": "Test user created successfully",
  "data": {
    "userId": "user123456789",
    "nino": "AA123456A",
    "saUtr": "1234567890",
    "password": "password123",
    "userFullName": "Test User",
    "emailAddress": "test@example.com"
  }
}
```

### Create Test Business

```
POST /api/hmrc/sandbox/create-test-business
Body: { "nino": "AA123456A" }
```

**Response:**
```json
{
  "success": true,
  "message": "Test business created successfully",
  "data": {
    "businessId": "XAIS12345678901",
    "tradingName": "TVS Test Business",
    "accountingType": "CASH",
    "commencementDate": "2024-04-06"
  }
}
```

### Get Active Test User

```
GET /api/hmrc/sandbox/active-test-user
```

**Response:**
```json
{
  "success": true,
  "data": {
    "userId": "user123456789",
    "nino": "AA123456A",
    "saUtr": "1234567890",
    "businessId": "XAIS12345678901",
    "tradingName": "TVS Test Business",
    "accountingType": "CASH",
    "commencementDate": "2024-04-06",
    "createdAt": "2026-04-10T21:00:00"
  }
}
```

### Get All Test Users (History)

```
GET /api/hmrc/sandbox/test-users
```

### Delete Test User

```
DELETE /api/hmrc/sandbox/test-users/{id}
```

---

## Database Schema

```sql
CREATE TABLE sandbox_test_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    password TEXT NOT NULL,
    nino TEXT NOT NULL UNIQUE,
    sa_utr TEXT,
    business_id TEXT,
    trading_name TEXT,
    accounting_type TEXT,
    commencement_date TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Environment Variables

After creating a test user, `.env` is automatically updated:

```bash
# HMRC Sandbox Test User Credentials (Auto-populated by sandbox utility)
HMRC_TEST_NINO=AA123456A
HMRC_TEST_BUSINESS_ID=XAIS12345678901
```

These can be used in test scripts:

```python
import os
test_nino = os.getenv('HMRC_TEST_NINO')
test_business_id = os.getenv('HMRC_TEST_BUSINESS_ID')
```

---

## Testing Workflow

### Complete End-to-End Test

1. **Create Test User** via sandbox dashboard
2. **Authenticate** via OAuth using provided credentials
3. **Create Test Business** via sandbox dashboard
4. **Test Obligations API:**
   ```
   GET /api/hmrc/obligations?nino={HMRC_TEST_NINO}
   ```
5. **Test Period Submission:**
   ```
   POST /api/hmrc/period/submit
   Body: {
     "nino": "{HMRC_TEST_NINO}",
     "business_id": "{HMRC_TEST_BUSINESS_ID}",
     "tax_year": "2024/2025",
     "period_id": "Q1"
   }
   ```
6. **Test Calculations:**
   ```
   POST /api/hmrc/final-declaration/calculate?tax_year=2024/2025
   ```
7. **Test Final Declaration:**
   ```
   POST /api/hmrc/final-declaration/submit
   Body: {
     "tax_year": "2024/2025",
     "calculation_id": "...",
     "confirmed": true
   }
   ```

---

## Troubleshooting

### "Failed to obtain application token"

**Cause:** Invalid `HMRC_CLIENT_ID` or `HMRC_CLIENT_SECRET` in `.env`

**Solution:** 
1. Check your HMRC application credentials
2. Ensure they're registered for sandbox environment
3. Verify no typos in `.env` file

### "Not authenticated. Please authenticate via OAuth first"

**Cause:** Trying to create business before OAuth authentication

**Solution:**
1. Create test user first
2. Use credentials to authenticate via HMRC MTD page
3. Then create test business

### "Failed to create test business"

**Cause:** OAuth token expired or invalid

**Solution:**
1. Disconnect from HMRC (if connected)
2. Re-authenticate using test user credentials
3. Try creating business again

### Test user already exists

**Cause:** Previous test user still active

**Solution:**
1. Creating a new test user automatically deactivates the old one
2. Or delete old test users from history table

---

## Security Notes

### Credentials Storage

- Test user **passwords are stored in plain text** in the database
- This is acceptable for sandbox testing only
- **Never use this pattern in production**

### OAuth Tokens

- OAuth tokens are managed by the existing `HMRCAuthService`
- Tokens are stored encrypted in `hmrc_credentials` table
- Sandbox tokens expire after 4 hours

### API Access

- All sandbox routes require authentication
- Rate limiting applies (20 requests per hour)
- CSRF protection enabled

---

## Production Deployment Checklist

Before deploying to production, **remove all sandbox-related code:**

### Files to Delete

- [ ] `migrations/005_hmrc_sandbox_test_users.sql`
- [ ] `app/services/hmrc_sandbox.py`
- [ ] `app/routes/api_hmrc_sandbox.py`
- [ ] `templates/mtd_sandbox.html`
- [ ] `static/js/mtd-sandbox.js`
- [ ] `docs/SANDBOX_TEST_USER_UTILITY.md`

### Code to Remove

- [ ] Remove sandbox blueprint import in `app/__init__.py`:
  ```python
  from .routes.api_hmrc_sandbox import sandbox_bp  # DELETE THIS LINE
  ```
- [ ] Remove sandbox blueprint registration in `app/__init__.py`:
  ```python
  app.register_blueprint(sandbox_bp)  # DELETE THIS LINE
  ```
- [ ] Remove sandbox route in `app/routes/main.py`:
  ```python
  @main_bp.route('/mtd/sandbox')  # DELETE THIS ENTIRE ROUTE
  def mtd_sandbox():
      ...
  ```

### Environment Variables to Remove

- [ ] Remove from `.env`:
  ```bash
  HMRC_TEST_NINO=
  HMRC_TEST_BUSINESS_ID=
  ```

### Database Cleanup

- [ ] Drop sandbox table:
  ```sql
  DROP TABLE IF EXISTS sandbox_test_users;
  ```

---

## Technical Details

### OAuth Flow for Test User Creation

The Create Test User API requires **application-level OAuth** (not user-level):

```python
# Get application token using client_credentials grant
data = {
    'grant_type': 'client_credentials',
    'client_id': HMRC_CLIENT_ID,
    'client_secret': HMRC_CLIENT_SECRET,
    'scope': 'create:test-user'
}
response = requests.post(token_url, data=data)
access_token = response.json()['access_token']
```

This is different from the user-facing OAuth flow used for MTD APIs.

### Stateful Test Users

HMRC sandbox test users are **stateful**:
- Data persists across API calls
- Submissions are tracked
- Obligations are updated
- Calculations are stored

This allows realistic end-to-end testing of the MTD ITSA journey.

### API Versioning

- Create Test User API: No version header required
- Self Assessment Test Support API: `Accept: application/vnd.hmrc.2.0+json`

---

## Support

For issues with:
- **HMRC APIs:** Check HMRC Developer Hub documentation
- **Sandbox utility:** Review logs in `logs/app.log`
- **OAuth flow:** Check `logs/app.log` for authentication errors

---

**Remember:** This is a development tool. Remove before production! 🚨
