# HMRC Test User Setup for MTD ITSA

## Current Issue

**Error:** `MATCHING_RESOURCE_NOT_FOUND` when calling `/api/hmrc/businesses?nino=BW029467A`

**Reason:** The NINO `BW029467A` is not a valid HMRC test user with MTD ITSA enrollment. Random NINOs don't work in sandbox.

---

## Solution: Create Proper Test User

### Option 1: Use HMRC Test User Service (Easiest)

**URL:** https://developer.service.hmrc.gov.uk/api-test-user

**Steps:**
1. Go to the test user service
2. Select **"Individual"**
3. Check these services:
   - ☑️ National Insurance
   - ☑️ Self Assessment
   - ☑️ MTD Income Tax
4. Click **"Create"**
5. **Save the credentials** - you'll need them!

**You'll receive:**
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
  "nino": "AA123456A",           ← Use this NINO
  "saUtr": "1234567890",
  "mtdItId": "XAIT00000000001"   ← MTD Income Tax ID
}
```

**Important:** Test users expire after 3 months of inactivity. Reuse them!

---

### Option 2: Use Create Test User API (Automated)

```bash
curl -X POST https://test-api.service.hmrc.gov.uk/create-test-user/individuals \
  -H "Content-Type: application/json" \
  -d '{
    "serviceNames": [
      "national-insurance",
      "self-assessment",
      "mtd-income-tax"
    ]
  }'
```

---

## Using Your Test User

### Step 1: Authenticate with HMRC

1. Go to HMRC Settings page
2. Click **"Connect to HMRC"**
3. When prompted, log in with:
   - **User ID:** (from test user creation)
   - **Password:** (from test user creation)
4. Authorize the application

### Step 2: Get Business Details

Once authenticated, use the test user's NINO:

```javascript
// In browser console
fetch('/api/hmrc/businesses?nino=AA123456A', {credentials:'same-origin'})
  .then(r=>r.json())
  .then(data=>console.log(JSON.stringify(data,null,2)))
```

Replace `AA123456A` with your actual test user's NINO.

---

## Standard Test Business IDs

HMRC provides **standard test business IDs** in sandbox that work with any authenticated test user:

| Business ID | Type | Description |
|-------------|------|-------------|
| `XAIS00000000001` | Self-employment | Standard test business #1 |
| `XAIS00000000002` | Self-employment | Standard test business #2 |
| `XBIS00000000001` | UK Property | UK property business |
| `XFIS00000000001` | Foreign Property | Foreign property business |

**You can use these directly** without calling the business list endpoint.

---

## Testing Obligations

Once you have a business ID, test obligations:

```javascript
// Get obligations for standard test business
fetch('/api/hmrc/obligations?nino=AA123456A&from_date=2023-04-06&to_date=2024-04-05', {
  credentials:'same-origin'
})
.then(r=>r.json())
.then(data=>console.log(JSON.stringify(data,null,2)))
```

---

## Using Gov-Test-Scenario

For specific test scenarios, add the `test_scenario` parameter:

```javascript
// Test with specific scenario
fetch('/api/hmrc/obligations?nino=AA123456A&test_scenario=ITSA_FINAL_DECLARATION', {
  credentials:'same-origin'
})
.then(r=>r.json())
.then(data=>console.log(JSON.stringify(data,null,2)))
```

**Available scenarios:**
- `SIGN_UP_RETURN_AVAILABLE`
- `ITSA_FINAL_DECLARATION`
- `ITSA_Q4_DECLARATION`
- And more...

---

## Quick Start Checklist

- [ ] Create test user at https://developer.service.hmrc.gov.uk/api-test-user
- [ ] Save User ID, Password, NINO, and MTD IT ID
- [ ] Connect to HMRC using test user credentials
- [ ] Test business list endpoint with test user's NINO
- [ ] Or use standard business ID `XAIS00000000001`
- [ ] Test obligations endpoint
- [ ] Test with Gov-Test-Scenario headers

---

## Why Random NINOs Don't Work

**HMRC Sandbox is STATEFUL:**
- Each test user has their own data
- NINOs must be from created test users
- Random NINOs have no data associated with them
- You can't just make up a NINO like `BW029467A`

**This is different from stateless APIs** that return hard-coded responses for any input.

---

## Next Steps

1. **Create a test user** using the service above
2. **Save the credentials** somewhere safe
3. **Authenticate** with HMRC using those credentials
4. **Use the test user's NINO** in API calls
5. **Or use standard business ID** `XAIS00000000001` directly

The test user will have pre-configured MTD ITSA data that works with all the APIs.
