# HMRC Sandbox Test User Utility - Implementation Summary

⚠️ **CRITICAL: SANDBOX TESTING ONLY - Remove before production**

---

## ✅ Implementation Complete

Successfully implemented a comprehensive HMRC sandbox test user creation utility for tvstcms MTD ITSA testing.

---

## Features Implemented

### 1. **Automated Test User Creation** ✅
- Creates test individuals via HMRC Create Test User API
- Generates NINO, SA UTR, User ID, and Password
- Uses application-level OAuth (client_credentials grant)
- Stores credentials in SQLite database

### 2. **Automated Test Business Creation** ✅
- Creates self-employment business via Self Assessment Test Support API
- Sets up "TVS Test Business" with CASH accounting
- Requires user-level OAuth authentication
- Returns Business ID for API testing

### 3. **Sandbox Dashboard UI** ✅
- Clean, professional interface at `/mtd/sandbox`
- Red warning banner: "SANDBOX TESTING ONLY"
- Active test user display with all credentials
- Copy-to-clipboard buttons for easy testing
- Test user history table
- Step-by-step instructions

### 4. **Database Integration** ✅
- New table: `sandbox_test_users`
- Stores User ID, Password, NINO, SA UTR, Business ID
- Tracks active vs inactive test users
- Auto-deactivates old users when creating new ones

### 5. **Environment Variable Management** ✅
- Auto-updates `.env` with test credentials
- `HMRC_TEST_NINO` - populated after test user creation
- `HMRC_TEST_BUSINESS_ID` - populated after business creation
- Easy access for test scripts

---

## Files Created

### Database
- ✅ `migrations/005_hmrc_sandbox_test_users.sql` - Database schema

### Backend Services
- ✅ `app/services/hmrc_sandbox.py` - Core service layer
  - `create_test_individual()` - Creates test user
  - `create_test_business()` - Creates test business
  - `store_test_user()` - Saves to database
  - `get_active_test_user()` - Retrieves current test user
  - `_get_application_token()` - OAuth client_credentials flow
  - `_update_env_file()` - Updates .env automatically

### API Routes
- ✅ `app/routes/api_hmrc_sandbox.py` - RESTful API endpoints
  - `POST /api/hmrc/sandbox/create-test-user`
  - `POST /api/hmrc/sandbox/create-test-business`
  - `GET /api/hmrc/sandbox/active-test-user`
  - `GET /api/hmrc/sandbox/test-users`
  - `DELETE /api/hmrc/sandbox/test-users/{id}`

### Frontend
- ✅ `templates/mtd_sandbox.html` - Dashboard UI
  - Warning banner
  - Active user display
  - Action buttons
  - Credentials modal
  - History table
  - Instructions
- ✅ `static/js/mtd-sandbox.js` - Dashboard JavaScript
  - Test user creation
  - Test business creation
  - Clipboard copy functionality
  - History management
  - Loading states

### Configuration
- ✅ Updated `app/__init__.py` - Registered sandbox blueprint
- ✅ Updated `app/routes/main.py` - Added `/mtd/sandbox` route
- ✅ Updated `.env` - Added test credential placeholders

### Documentation
- ✅ `docs/SANDBOX_TEST_USER_UTILITY.md` - Complete usage guide
- ✅ `docs/SANDBOX_IMPLEMENTATION_SUMMARY.md` - This file

---

## API Endpoints Summary

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/hmrc/sandbox/create-test-user` | POST | Create test individual |
| `/api/hmrc/sandbox/create-test-business` | POST | Create test business |
| `/api/hmrc/sandbox/active-test-user` | GET | Get current test user |
| `/api/hmrc/sandbox/test-users` | GET | Get all test users |
| `/api/hmrc/sandbox/test-users/{id}` | DELETE | Delete test user |
| `/mtd/sandbox` | GET | Dashboard UI |

---

## Usage Workflow

### Quick Start

1. **Navigate to Dashboard**
   ```
   http://localhost:5001/mtd/sandbox
   ```

2. **Create Test User**
   - Click "Create New Test User"
   - Save the credentials shown in modal

3. **Authenticate**
   - Go to HMRC MTD settings
   - Click "Connect to HMRC"
   - Use User ID and Password from modal

4. **Create Test Business**
   - Return to sandbox dashboard
   - Click "Create Test Business"
   - Business ID will be displayed

5. **Start Testing**
   - Copy NINO and Business ID
   - Use in API testing tools
   - Test MTD ITSA endpoints

### Example API Test

```bash
# Get obligations
curl -X GET "http://localhost:5001/api/hmrc/obligations?nino=AA123456A"

# Submit period
curl -X POST "http://localhost:5001/api/hmrc/period/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "nino": "AA123456A",
    "business_id": "XAIS12345678901",
    "tax_year": "2024/2025",
    "period_id": "Q1"
  }'
```

---

## Technical Implementation Details

### OAuth Flow

**Application-Level Token (for Create Test User API):**
```python
# Uses client_credentials grant
POST https://test-api.service.hmrc.gov.uk/oauth/token
Body: {
  "grant_type": "client_credentials",
  "client_id": "...",
  "client_secret": "...",
  "scope": "create:test-user"
}
```

**User-Level Token (for Create Test Business API):**
```python
# Uses authorization_code grant (standard OAuth)
# Managed by existing HMRCAuthService
```

### Database Schema

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

### Auto-Update .env

When a test user is created, the service automatically updates `.env`:

```python
def _update_env_file(self, nino, business_id):
    # Read .env
    # Find or add HMRC_TEST_NINO and HMRC_TEST_BUSINESS_ID
    # Write back with new values
```

This allows test scripts to use:
```python
import os
nino = os.getenv('HMRC_TEST_NINO')
business_id = os.getenv('HMRC_TEST_BUSINESS_ID')
```

---

## Security Considerations

### ⚠️ Sandbox Only

- **Passwords stored in plain text** - Acceptable for sandbox, NOT for production
- **No encryption** - Test data only
- **Public credentials** - HMRC sandbox is isolated from production

### Production Safety

- All sandbox routes require authentication
- Rate limiting applied (20 requests/hour)
- CSRF protection enabled
- Clear warning banners throughout UI

---

## Production Deployment Checklist

**CRITICAL: Remove ALL sandbox code before production!**

### Files to Delete

```bash
# Database migration
rm migrations/005_hmrc_sandbox_test_users.sql

# Backend
rm app/services/hmrc_sandbox.py
rm app/routes/api_hmrc_sandbox.py

# Frontend
rm templates/mtd_sandbox.html
rm static/js/mtd-sandbox.js

# Documentation
rm docs/SANDBOX_TEST_USER_UTILITY.md
rm docs/SANDBOX_IMPLEMENTATION_SUMMARY.md
```

### Code Changes

**`app/__init__.py`:**
```python
# DELETE THIS LINE:
from .routes.api_hmrc_sandbox import sandbox_bp

# DELETE THIS LINE:
app.register_blueprint(sandbox_bp)
```

**`app/routes/main.py`:**
```python
# DELETE THIS ENTIRE ROUTE:
@main_bp.route('/mtd/sandbox')
def mtd_sandbox():
    ...
```

**`.env`:**
```bash
# DELETE THESE LINES:
HMRC_TEST_NINO=
HMRC_TEST_BUSINESS_ID=
```

### Database Cleanup

```sql
DROP TABLE IF EXISTS sandbox_test_users;
```

---

## Testing Checklist

### ✅ Test User Creation
- [ ] Creates test individual successfully
- [ ] Returns User ID, Password, NINO, SA UTR
- [ ] Stores in database
- [ ] Updates .env file
- [ ] Deactivates previous test users

### ✅ Test Business Creation
- [ ] Requires OAuth authentication
- [ ] Creates self-employment business
- [ ] Returns Business ID
- [ ] Updates database record
- [ ] Updates .env file

### ✅ Dashboard UI
- [ ] Displays active test user
- [ ] Shows all credentials
- [ ] Copy buttons work
- [ ] History table populates
- [ ] Instructions are clear
- [ ] Warning banner visible

### ✅ API Integration
- [ ] Can use test NINO for obligations
- [ ] Can use test Business ID for periods
- [ ] Can submit quarterly periods
- [ ] Can trigger calculations
- [ ] Can submit final declaration

---

## Known Limitations

### Create Test User API

- **Rate Limits:** HMRC may throttle test user creation
- **Quota:** Limited number of test users per application
- **Persistence:** Test users persist in sandbox until deleted

### Create Test Business API

- **OAuth Required:** Must authenticate before creating business
- **Single Business:** One business per test user (for now)
- **Fixed Details:** Trading name and address are hardcoded

### Sandbox Environment

- **Data Isolation:** Sandbox data doesn't affect production
- **Mock Responses:** Some HMRC responses may be mocked
- **Test Scenarios:** Use `Gov-Test-Scenario` header for specific test cases

---

## Future Enhancements (Optional)

### Potential Improvements

1. **Multiple Businesses** - Support creating multiple businesses per user
2. **Custom Business Details** - Allow editing trading name, address, etc.
3. **Bulk Test Users** - Create multiple test users at once
4. **Test Data Generator** - Auto-populate obligations and submissions
5. **Scenario Testing** - Pre-configured test scenarios (e.g., "4 quarters submitted")

### Not Recommended

- **Production Use** - Never use this in production
- **Real Credentials** - Never store real user credentials this way
- **Automated Testing** - Don't create test users in CI/CD (rate limits)

---

## Support & Troubleshooting

### Common Issues

**"Failed to obtain application token"**
- Check `HMRC_CLIENT_ID` and `HMRC_CLIENT_SECRET` in `.env`
- Ensure credentials are for sandbox environment

**"Not authenticated"**
- Complete OAuth flow before creating business
- Check OAuth token hasn't expired (4 hours)

**"Failed to create test business"**
- Ensure test user was created first
- Verify OAuth authentication is active
- Check NINO is correct

### Logs

Check `logs/app.log` for detailed error messages:
```bash
tail -f logs/app.log | grep -i sandbox
```

---

## Summary

✅ **Complete sandbox test user creation utility implemented**  
✅ **Automated workflow from user creation to business setup**  
✅ **Professional dashboard UI with clear warnings**  
✅ **Database integration with auto-update .env**  
✅ **Comprehensive documentation and removal checklist**

**Ready for sandbox testing!** 🎉

**Remember: Remove before production!** ⚠️
