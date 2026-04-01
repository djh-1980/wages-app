# HMRC Business Routes - Correct URLs and Commands

## Date: April 1, 2026

---

## 1. Business List Route

### Registered Route Path
```python
@hmrc_bp.route('/businesses')
@limiter.limit("20 per hour", override_defaults=True)
def get_businesses():
```

**Full URL:** `/api/hmrc/businesses` (NOT `/api/hmrc/business-list`)

**Method:** GET

**Query Parameters:** `?nino=OA965288C`

**What it does:** Calls HMRC endpoint `/individuals/income-received/self-employment/{nino}`

---

## 2. Create Test Business Route

### Registered Route Path
```python
@hmrc_bp.route('/create-test-business', methods=['POST'])
@limiter.limit("20 per hour", override_defaults=True)
def create_test_business():
```

**Full URL:** `/api/hmrc/create-test-business`

**Method:** POST

**Request Body:** `{"nino": "OA965288C"}`

**What it does:** Calls HMRC Test Support API:
```
POST /test-support/self-assessment/ni/{nino}/self-employments
```

**Test business data sent:**
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

---

## Console Commands to Run

### A) Fetch Business List for NINO OA965288C

**In browser console (F12):**
```javascript
fetch('/api/hmrc/businesses?nino=OA965288C', {
  credentials: 'same-origin',
  headers: {'Content-Type': 'application/json'}
})
.then(r => r.json())
.then(data => {
  console.log('Business list response:', data);
  if (data.success && data.data) {
    console.log('Businesses:', data.data);
  } else {
    console.error('Error:', data.error);
  }
});
```

**Expected response (if businesses exist):**
```json
{
  "success": true,
  "data": {
    "selfEmployments": [
      {
        "businessId": "XAIS00000000001",
        "tradingName": "Test Self Employment",
        "businessDescription": "Test Business"
      }
    ]
  }
}
```

**Expected response (if no businesses):**
```json
{
  "success": false,
  "error": "No businesses found",
  "status_code": 404
}
```

---

### B) Create Test Business for OA965288C

**In browser console (F12):**
```javascript
fetch('/api/hmrc/create-test-business', {
  method: 'POST',
  credentials: 'same-origin',
  headers: {
    'Content-Type': 'application/json',
    ...getCSRFHeaders()
  },
  body: JSON.stringify({nino: 'OA965288C'})
})
.then(r => r.json())
.then(data => {
  console.log('Create business response:', data);
  if (data.success && data.data) {
    console.log('Business ID:', data.data.businessId || data.data);
  } else {
    console.error('Error:', data.error);
    console.error('Details:', data.details);
  }
});
```

**Expected success response:**
```json
{
  "success": true,
  "data": {
    "businessId": "XAIS00000000001"
  },
  "status_code": 201
}
```

**Expected error response (if already exists):**
```json
{
  "success": false,
  "error": "Business already exists",
  "status_code": 400,
  "details": {
    "code": "CONFLICT",
    "message": "A self-employment business already exists for this NINO"
  }
}
```

---

## Why Create Test Business Returns 400

The HMRC sandbox Test Support API returns 400 when:

1. **Business already exists** for the NINO
   - HMRC sandbox only allows one self-employment business per NINO
   - Solution: Use the existing business ID

2. **Invalid request body**
   - Missing required fields
   - Invalid date formats
   - Solution: Our request includes all required fields

3. **NINO not found in sandbox**
   - The test user doesn't exist in sandbox
   - Solution: Create test user first via HMRC Developer Hub

4. **Sandbox API limitations**
   - Some sandbox environments don't support Test Support API
   - Solution: Use standard test business ID `XAIS00000000001`

---

## Recommended Workflow

### Step 1: Try to Fetch Existing Business List
```javascript
fetch('/api/hmrc/businesses?nino=OA965288C', {
  credentials: 'same-origin'
})
.then(r => r.json())
.then(data => console.log(data));
```

**If successful:** Use the returned `businessId`

**If 404 or empty:** Proceed to Step 2

---

### Step 2: Create Test Business (if needed)
```javascript
fetch('/api/hmrc/create-test-business', {
  method: 'POST',
  credentials: 'same-origin',
  headers: {
    'Content-Type': 'application/json',
    ...getCSRFHeaders()
  },
  body: JSON.stringify({nino: 'OA965288C'})
})
.then(r => r.json())
.then(data => console.log(data));
```

**If successful:** Use the returned `businessId`

**If 400 (already exists):** Go back to Step 1

**If 400 (other error):** Use standard test business ID

---

### Step 3: Use Standard Test Business ID (fallback)

If both API calls fail, use the standard HMRC sandbox test business ID:

**Business ID:** `XAIS00000000001`

This is the default business ID for HMRC sandbox test users.

---

### Step 4: Configure in HMRC Settings

Once you have the Business ID:

1. Go to http://127.0.0.1:5001/settings/hmrc
2. Click "Configure" button
3. Enter:
   - **NINO:** `OA965288C`
   - **Business ID:** `XAIS00000000001` (or the ID from API)
4. Click "Save Configuration"

---

### Step 5: Fetch Obligations

After configuration:

```javascript
fetch('/api/hmrc/obligations?nino=OA965288C', {
  credentials: 'same-origin'
})
.then(r => r.json())
.then(data => console.log('Obligations:', data));
```

**Expected response:**
```json
{
  "success": true,
  "data": {
    "obligations": [
      {
        "periodKey": "Q1",
        "start": "2024-04-06",
        "end": "2024-07-05",
        "due": "2024-08-05",
        "status": "Open"
      },
      // ... Q2, Q3, Q4
    ]
  }
}
```

---

## Summary

**Correct Route URLs:**
- ✅ Business List: `/api/hmrc/businesses?nino=OA965288C`
- ✅ Create Test Business: `/api/hmrc/create-test-business` (POST)

**NOT:**
- ❌ `/api/hmrc/business-list` (doesn't exist)

**Standard Test Business ID for Sandbox:**
- `XAIS00000000001`

**Test User NINO:**
- `OA965288C`

**Next Steps:**
1. Run business list fetch command
2. If no businesses, try create test business
3. If create fails with 400, use `XAIS00000000001`
4. Configure NINO and Business ID in settings
5. Fetch obligations to verify setup
