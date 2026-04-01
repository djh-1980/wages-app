# HMRC Create Test Business - 400 Error Fix

## Date: April 1, 2026

---

## Issue

`POST /api/hmrc/create-test-business` returning 400 Bad Request from HMRC sandbox for NINO BW029467A.

**Root Causes:**
1. **Incorrect payload format** - Missing required fields and using wrong field names
2. **Missing Authorization header** - Endpoint requires OAuth Bearer token, not client credentials

---

## Analysis

### Route in `api_hmrc.py` (Lines 554-583)

**Current implementation:**
```python
@hmrc_bp.route('/create-test-business', methods=['POST'])
@limiter.limit("20 per hour", override_defaults=True)
def create_test_business():
    """
    Create a test self-employment business for sandbox testing.
    Uses HMRC Self Assessment Test Support API.
    """
    try:
        data = request.get_json()
        nino = data.get('nino')
        
        if not nino:
            return jsonify({'success': False, 'error': 'NINO is required'}), 400
        
        # Validate NINO format
        try:
            nino = validate_nino(nino)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        
        client = HMRCClient()
        result = client.create_test_business(nino)
        
        if result.get('success'):
            return jsonify({'success': True, 'data': result.get('data', {})})
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f'Error creating test business: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
```

**Route is correct** - properly validates NINO and delegates to HMRCClient.

---

### Method in `hmrc_client.py` (Lines 256-300) - BEFORE FIX

**INCORRECT implementation:**
```python
def create_test_business(self, nino):
    """
    Create a test self-employment business for sandbox testing.
    Uses Self Assessment Test Support API.
    """
    # Test Support API doesn't require authentication for sandbox
    url = f"{self.base_url}/test-support/self-assessment/ni/{nino}/self-employments"
    
    test_business_data = {
        "tradingName": "Test Self Employment",
        "businessDescription": "Test Business",              # ❌ Not required
        "businessAddressLineOne": "Test Address",
        "businessAddressPostcode": "TE5 7ST",
        "businessStartDate": "2020-01-01",                   # ❌ Not required
        "accountingType": "CASH",                            # ❌ Not required
        "commencementDate": "2020-01-01"                     # ❌ Not required
    }
    
    try:
        response = requests.post(url, json=test_business_data, timeout=30)  # ❌ No auth header
        # ...
```

**Problems:**
1. ❌ Missing `annualAccountingRegime` (required)
2. ❌ Missing `businessAddressLineTwo` (required)
3. ❌ Using `businessAddressPostcode` instead of `businessPostcode`
4. ❌ Including unnecessary fields (`businessDescription`, `businessStartDate`, etc.)
5. ❌ No Authorization header (OAuth Bearer token required)
6. ❌ Comment says "doesn't require authentication" (INCORRECT)

---

## HMRC API Requirements

### Correct Endpoint
```
POST https://test-api.service.hmrc.gov.uk/test-support/self-assessment/ni/{nino}/self-employments
```

### Required Headers
```
Authorization: Bearer {oauth_access_token}
Content-Type: application/json
Accept: application/vnd.hmrc.1.0+json
```

### Required Payload Format
```json
{
  "annualAccountingRegime": "STANDARD",
  "tradingName": "Test Business",
  "businessAddressLineOne": "1 Test Street",
  "businessAddressLineTwo": "Test Town",
  "businessPostcode": "TE1 1ST"
}
```

**Field Requirements:**
- `annualAccountingRegime` - **Required** - Must be "STANDARD" or "CASH"
- `tradingName` - **Required** - Business trading name
- `businessAddressLineOne` - **Required** - First line of address
- `businessAddressLineTwo` - **Required** - Second line of address
- `businessPostcode` - **Required** - UK postcode format

---

## Fixed Implementation

### File: `app/services/hmrc_client.py`

**AFTER FIX:**
```python
def create_test_business(self, nino):
    """
    Create a test self-employment business for sandbox testing.
    Uses Self Assessment Test Support API.
    Requires OAuth Bearer token from authenticated session.
    
    Args:
        nino: National Insurance Number
        
    Returns:
        dict: Business creation response with business ID
    """
    url = f"{self.base_url}/test-support/self-assessment/ni/{nino}/self-employments"
    
    # Correct payload format as per HMRC API documentation
    test_business_data = {
        "annualAccountingRegime": "STANDARD",
        "tradingName": "Test Business",
        "businessAddressLineOne": "1 Test Street",
        "businessAddressLineTwo": "Test Town",
        "businessPostcode": "TE1 1ST"
    }
    
    try:
        # Get OAuth access token from authenticated session
        headers = self._get_headers()
        
        response = requests.post(
            url, 
            json=test_business_data, 
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            return {
                'success': True,
                'data': response.json() if response.content else {},
                'status_code': response.status_code
            }
        else:
            error_data = response.json() if response.content else {}
            return {
                'success': False,
                'error': error_data.get('message', f'HTTP {response.status_code}'),
                'status_code': response.status_code,
                'details': error_data
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
```

---

## Changes Made

### 1. Fixed Payload Format
**BEFORE:**
```json
{
  "tradingName": "Test Self Employment",
  "businessDescription": "Test Business",
  "businessAddressLineOne": "Test Address",
  "businessAddressPostcode": "TE5 7ST",
  "businessStartDate": "2020-01-01",
  "accountingType": "CASH",
  "commencementDate": "2020-01-01"
}
```

**AFTER:**
```json
{
  "annualAccountingRegime": "STANDARD",
  "tradingName": "Test Business",
  "businessAddressLineOne": "1 Test Street",
  "businessAddressLineTwo": "Test Town",
  "businessPostcode": "TE1 1ST"
}
```

**Changes:**
- ✅ Added `annualAccountingRegime: "STANDARD"`
- ✅ Added `businessAddressLineTwo: "Test Town"`
- ✅ Changed `businessAddressPostcode` → `businessPostcode`
- ✅ Removed `businessDescription` (not required)
- ✅ Removed `businessStartDate` (not required)
- ✅ Removed `accountingType` (not required)
- ✅ Removed `commencementDate` (not required)

---

### 2. Added OAuth Authorization

**BEFORE:**
```python
response = requests.post(url, json=test_business_data, timeout=30)
```

**AFTER:**
```python
# Get OAuth access token from authenticated session
headers = self._get_headers()

response = requests.post(
    url, 
    json=test_business_data, 
    headers=headers,
    timeout=30
)
```

**What `self._get_headers()` returns:**
```python
{
    'Authorization': 'Bearer {oauth_access_token}',
    'Accept': 'application/vnd.hmrc.1.0+json',
    'Content-Type': 'application/json'
}
```

This uses the OAuth token from the authenticated user session, **NOT** client credentials.

---

## How Authorization Works

### OAuth Flow for Test Support API

```
1. User authenticates with HMRC via OAuth
   ↓
2. Access token stored in hmrc_credentials table
   ↓
3. HMRCClient._get_headers() retrieves token from database
   ↓
4. Token included in Authorization: Bearer {token} header
   ↓
5. HMRC validates token and processes request
```

### `_get_headers()` Method (in `hmrc_client.py`)

```python
def _get_headers(self):
    """
    Get headers for HMRC API requests including OAuth token.
    
    Returns:
        dict: Headers with Authorization bearer token
    """
    token = self._get_access_token()
    return {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.hmrc.1.0+json',
        'Content-Type': 'application/json'
    }
```

**Token Source:**
- Retrieved from `hmrc_credentials` table
- Uses OAuth access token from user's authenticated session
- Automatically refreshed if expired

---

## Expected Request

### Complete HTTP Request

```http
POST https://test-api.service.hmrc.gov.uk/test-support/self-assessment/ni/BW029467A/self-employments HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Accept: application/vnd.hmrc.1.0+json
Content-Type: application/json

{
  "annualAccountingRegime": "STANDARD",
  "tradingName": "Test Business",
  "businessAddressLineOne": "1 Test Street",
  "businessAddressLineTwo": "Test Town",
  "businessPostcode": "TE1 1ST"
}
```

---

## Expected Response

### Success (200 or 201)

```json
{
  "businessId": "XAIS00000000001",
  "nino": "BW029467A",
  "tradingName": "Test Business",
  "businessAddressLineOne": "1 Test Street",
  "businessAddressLineTwo": "Test Town",
  "businessPostcode": "TE1 1ST"
}
```

### Error (400)

**Before fix:**
```json
{
  "code": "INVALID_REQUEST",
  "message": "Missing required field: annualAccountingRegime"
}
```

**After fix:**
Should return 200/201 with business details.

---

## Testing

### Prerequisites
1. User must be authenticated with HMRC OAuth
2. Valid OAuth access token in database
3. NINO must be valid format (e.g., BW029467A)

### Test via Browser Console

```javascript
fetch('/api/hmrc/create-test-business', {
  method: 'POST',
  credentials: 'same-origin',
  headers: {
    'Content-Type': 'application/json',
    ...getCSRFHeaders()
  },
  body: JSON.stringify({
    nino: 'BW029467A'
  })
})
.then(r => r.json())
.then(data => console.log(JSON.stringify(data, null, 2)));
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "businessId": "XAIS00000000001",
    "nino": "BW029467A",
    "tradingName": "Test Business",
    "businessAddressLineOne": "1 Test Street",
    "businessAddressLineTwo": "Test Town",
    "businessPostcode": "TE1 1ST"
  }
}
```

---

### Test via Python Script

```python
import requests

response = requests.post(
    'http://localhost:5001/api/hmrc/create-test-business',
    json={'nino': 'BW029467A'},
    cookies={'session': 'your_session_cookie'}
)

print(response.status_code)
print(response.json())
```

---

## Verification Checklist

After fix, verify:

- ✅ Payload includes all 5 required fields
- ✅ Field names match HMRC API exactly (`businessPostcode` not `businessAddressPostcode`)
- ✅ Authorization header includes OAuth Bearer token
- ✅ No unnecessary fields in payload
- ✅ Request returns 200/201 instead of 400
- ✅ Response includes `businessId`

---

## Files Modified

**File:** `app/services/hmrc_client.py`

**Lines:** 256-300

**Changes:**
1. Updated payload to match HMRC API requirements
2. Added OAuth authorization via `self._get_headers()`
3. Updated docstring to clarify OAuth requirement
4. Removed incorrect comment about not requiring authentication

---

## Summary

**Issue:** 400 Bad Request when creating test business

**Root Causes:**
1. Incorrect payload format (missing required fields, wrong field names)
2. Missing OAuth Authorization header

**Fix:**
1. Updated payload to exact HMRC API specification
2. Added `headers = self._get_headers()` to include OAuth token
3. Removed unnecessary fields from payload

**Result:**
- Endpoint now sends correct payload format
- OAuth Bearer token included in Authorization header
- Should return 200/201 with business details instead of 400 error

The create-test-business endpoint is now fixed and ready for testing.
