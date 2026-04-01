# HMRC MTD ITSA Sandbox Testing - Correct Approach

## Date: April 1, 2026

---

## Issue with Current Approach

**Problem:** Trying to create test businesses via API (`/test-support/self-assessment/ni/{nino}/self-employments`) returns 404 because:
1. Test users created via Developer Hub don't have self-employment businesses pre-registered
2. The Test Support API for creating businesses may not work as expected in sandbox
3. We're using the wrong testing methodology

---

## HMRC's Recommended Testing Approach

### 1. Stateful vs Stateless Testing

According to HMRC documentation:

**Stateless APIs:**
- Return hard-coded happy path responses
- Don't require test data setup
- Use `Gov-Test-Scenario` header to simulate different scenarios

**Stateful APIs:**
- Let you create (POST) and retrieve (GET) actual test data
- Require test user creation
- May have accompanying Test Support APIs

**MTD ITSA APIs are STATEFUL** - they require proper test user setup and data creation.

---

## Correct Testing Methodology

### Step 1: Create Test User with Self-Employment

Use the **Create Test User API** or **Create Test User Service** to generate a test user with self-employment enrolments.

**API Endpoint:**
```
POST https://test-api.service.hmrc.gov.uk/create-test-user/individuals
```

**Request Body:**
```json
{
  "serviceNames": [
    "national-insurance",
    "self-assessment",
    "mtd-income-tax"
  ]
}
```

**Response:**
```json
{
  "userId": "935917348463",
  "password": "yeSn4tOBmXnU",
  "userFullName": "Test User",
  "emailAddress": "test@example.com",
  "individualDetails": {
    "firstName": "Test",
    "lastName": "User",
    "dateOfBirth": "1980-01-01",
    "address": {
      "line1": "1 Test Street",
      "line2": "Test Town",
      "postcode": "TE1 1ST"
    }
  },
  "nino": "AA123456A",
  "saUtr": "1234567890",
  "mtdItId": "XAIT00000000001"
}
```

**Key Fields:**
- `mtdItId` - MTD Income Tax ID (required for API calls)
- `nino` - National Insurance Number
- `saUtr` - Self Assessment UTR

---

### Step 2: Use Gov-Test-Scenario Header

HMRC APIs support test scenarios via the `Gov-Test-Scenario` header.

**Example Scenarios for Individual Details API:**

| Scenario Code | Description |
|---------------|-------------|
| `SIGN_UP_RETURN_AVAILABLE` | Sign up - return available |
| `SIGN_UP_NO_RETURN` | Sign up - no return available |
| `ITSA_FINAL_DECLARATION` | ITSA final declaration |
| `ITSA_Q4_DECLARATION` | ITSA Q4 declaration |
| `CESA_SA_RETURN` | CESA SA return |

**Request Example:**
```http
GET /individuals/self-assessment/{nino}/{taxYear}
Authorization: Bearer {token}
Accept: application/vnd.hmrc.2.0+json
Gov-Test-Scenario: ITSA_FINAL_DECLARATION
```

---

### Step 3: Stateful Testing Flow

For MTD ITSA, follow this flow:

1. **Create test user** with MTD ITSA enrolments
2. **Authenticate** via OAuth 2.0 to get access token
3. **List businesses** - Use Business Details API to get business IDs
4. **Get obligations** - Use Obligations API to see what needs filing
5. **Submit periods** - Use Self Employment Business API to submit quarterly updates
6. **Submit final declaration** - Complete the tax year

---

## HMRC Sandbox Test Data

### Pre-configured Test Scenarios

HMRC provides **stateless test scenarios** via `Gov-Test-Scenario` header for specific endpoints.

**Self Assessment Individual Details API** supports these scenarios:

```
00 = Sign up - return available
01 = Sign up - no return available
02 = ITSA final declaration
03 = ITSA Q4 declaration
04 = CESA SA return
05 = Complex
06 = Ceased income source
07 = Reinstated income source
08 = Rollover
09 = Income Source Latency Changes
10 = MTD ITSA Opt-Out
```

---

## Updated Testing Strategy

### Option 1: Use Test User Service (Recommended)

**Steps:**
1. Go to https://developer.service.hmrc.gov.uk/api-test-user
2. Create an **Individual** test user
3. Select services: **National Insurance**, **Self Assessment**, **MTD Income Tax**
4. Save the credentials (User ID, Password, NINO, MTD IT ID)
5. Use these credentials in OAuth flow
6. Use the MTD IT ID for API calls

**Advantages:**
- ✅ Properly configured test user
- ✅ Pre-enrolled in MTD ITSA
- ✅ Has MTD IT ID for API calls
- ✅ Can be reused for 3 months

---

### Option 2: Use Create Test User API (Automated)

**For automated testing:**

```python
def create_mtd_test_user():
    """Create a test user with MTD ITSA enrolments."""
    url = "https://test-api.service.hmrc.gov.uk/create-test-user/individuals"
    
    payload = {
        "serviceNames": [
            "national-insurance",
            "self-assessment",
            "mtd-income-tax"
        ]
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 201:
        user_data = response.json()
        return {
            'user_id': user_data['userId'],
            'password': user_data['password'],
            'nino': user_data['nino'],
            'mtd_it_id': user_data['mtdItId'],
            'sa_utr': user_data['saUtr']
        }
```

---

### Option 3: Use Gov-Test-Scenario for Specific Tests

**For testing specific scenarios without full setup:**

```python
def get_obligations_with_scenario(nino, scenario):
    """Get obligations using test scenario."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/vnd.hmrc.3.0+json',
        'Gov-Test-Scenario': scenario  # e.g., 'ITSA_FINAL_DECLARATION'
    }
    
    url = f"{base_url}/obligations/details/{nino}/income-tax-self-employment"
    response = requests.get(url, headers=headers)
    return response.json()
```

---

## Business ID Discovery

### Method 1: List Businesses API

**Endpoint:**
```
GET /individuals/business/details/{nino}/list
```

**Response:**
```json
{
  "businesses": [
    {
      "businessId": "XAIS00000000001",
      "typeOfBusiness": "self-employment",
      "tradingName": "Test Business",
      "accountingPeriods": [
        {
          "start": "2023-04-06",
          "end": "2024-04-05"
        }
      ]
    }
  ]
}
```

---

### Method 2: Use Standard Test Business ID

HMRC sandbox often uses **standard test business IDs**:

**Common Test Business IDs:**
- `XAIS00000000001` - Standard self-employment business
- `XAIS00000000002` - Second self-employment business
- `XBIS00000000001` - UK property business
- `XFIS00000000001` - Foreign property business

**Try these IDs first** before attempting to create businesses.

---

## Recommended Code Changes

### 1. Remove create_test_business Method

The `create_test_business()` method should be **removed** or **deprecated** as it doesn't work reliably in sandbox.

---

### 2. Add get_business_details Method

```python
def get_business_details(self, nino):
    """
    Get list of businesses for a NINO.
    Uses Business Details API.
    
    Args:
        nino: National Insurance Number
        
    Returns:
        dict: List of businesses with IDs
    """
    endpoint = f"/individuals/business/details/{nino}/list"
    return self._make_request('GET', endpoint)
```

---

### 3. Add Gov-Test-Scenario Support

```python
def _make_request(self, method, endpoint, data=None, params=None, test_scenario=None):
    """
    Make authenticated request to HMRC API with fraud prevention headers.
    
    Args:
        method: HTTP method (GET, POST, PUT)
        endpoint: API endpoint path
        data: Request body data
        params: Query parameters
        test_scenario: Optional Gov-Test-Scenario header value
        
    Returns:
        dict: Response data or error
    """
    access_token = self.auth_service.get_valid_access_token()
    
    if not access_token:
        return {
            'success': False,
            'error': 'Not authenticated. Please connect to HMRC first.'
        }
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': f'application/vnd.hmrc.{api_version}+json',
        'Content-Type': 'application/json',
        **self._get_fraud_prevention_headers()
    }
    
    # Add test scenario header if provided
    if test_scenario:
        headers['Gov-Test-Scenario'] = test_scenario
    
    # ... rest of method
```

---

### 4. Update Configuration with Test Data

```python
# app/config.py

class Config:
    # HMRC Sandbox Test Data
    HMRC_TEST_NINO = 'AA123456A'  # From test user creation
    HMRC_TEST_MTD_IT_ID = 'XAIT00000000001'
    HMRC_TEST_BUSINESS_ID = 'XAIS00000000001'  # Standard test business ID
    HMRC_TEST_SA_UTR = '1234567890'
```

---

## Testing Workflow

### Complete Test Flow

```python
# 1. Create test user (one-time setup)
test_user = create_mtd_test_user()
# Save: user_id, password, nino, mtd_it_id

# 2. Authenticate via OAuth
auth_url = get_authorization_url()
# User logs in with test_user credentials
# Exchange code for token

# 3. Get business details
businesses = get_business_details(test_user['nino'])
business_id = businesses['businesses'][0]['businessId']

# 4. Get obligations
obligations = get_obligations(
    nino=test_user['nino'],
    from_date='2023-04-06',
    to_date='2024-04-05'
)

# 5. Submit period
period_data = {
    'periodFromDate': '2023-04-06',
    'periodToDate': '2023-07-05',
    'income': {'turnover': 10000.00},
    'expenses': {'costOfGoods': 5000.00}
}
submit_period(test_user['nino'], business_id, period_data)

# 6. Submit final declaration
submit_final_declaration(test_user['nino'], '2023-24')
```

---

## Documentation References

**HMRC Developer Hub:**
- Testing Guide: https://developer.service.hmrc.gov.uk/api-documentation/docs/testing
- Test Users: https://developer.service.hmrc.gov.uk/api-documentation/docs/testing/test-users-test-data-stateful-behaviour
- MTD ITSA Guide: https://developer.service.hmrc.gov.uk/guides/income-tax-mtd-end-to-end-service-guide/

**Create Test User:**
- Service: https://developer.service.hmrc.gov.uk/api-test-user
- API: https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/api-platform-test-user/1.0

---

## Summary

**Don't:**
- ❌ Try to create businesses via Test Support API
- ❌ Use random NINOs without proper test user setup
- ❌ Expect stateless responses for stateful APIs

**Do:**
- ✅ Create test users with MTD ITSA enrolments
- ✅ Use the MTD IT ID from test user creation
- ✅ Use standard test business IDs (XAIS00000000001)
- ✅ Use Gov-Test-Scenario header for specific test cases
- ✅ Follow the proper OAuth → List Businesses → Get Obligations flow

**Next Steps:**
1. Update `create_hmrc_test_user.py` to use Create Test User API correctly
2. Remove or deprecate `create_test_business()` method
3. Add `get_business_details()` method
4. Add `Gov-Test-Scenario` support to `_make_request()`
5. Document test user credentials for reuse
6. Update HMRC settings page to show business discovery flow
