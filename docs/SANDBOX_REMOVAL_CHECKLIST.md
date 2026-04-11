# 🚨 SANDBOX REMOVAL CHECKLIST 🚨

**CRITICAL: Complete this checklist before production deployment**

---

## Files to Delete

```bash
# Database
- [ ] migrations/005_hmrc_sandbox_test_users.sql

# Backend
- [ ] app/services/hmrc_sandbox.py
- [ ] app/routes/api_hmrc_sandbox.py

# Frontend
- [ ] templates/mtd_sandbox.html
- [ ] static/js/mtd-sandbox.js

# Documentation
- [ ] docs/SANDBOX_TEST_USER_UTILITY.md
- [ ] docs/SANDBOX_IMPLEMENTATION_SUMMARY.md
- [ ] SANDBOX_REMOVAL_CHECKLIST.md (this file)
```

---

## Code to Remove

### app/__init__.py

**Line 158 - DELETE:**
```python
from .routes.api_hmrc_sandbox import sandbox_bp  # WARNING: SANDBOX ONLY - Remove before production
```

**Line 187 - DELETE:**
```python
app.register_blueprint(sandbox_bp)  # WARNING: SANDBOX ONLY - Remove before production
```

### app/routes/main.py

**Lines 114-122 - DELETE ENTIRE ROUTE:**
```python
@main_bp.route('/mtd/sandbox')
def mtd_sandbox():
    """
    HMRC Sandbox Testing Dashboard.
    
    WARNING: SANDBOX TESTING ONLY
    Remove this route before production deployment.
    """
    return render_template('mtd_sandbox.html')
```

---

## Environment Variables to Remove

### .env

**Lines 47-50 - DELETE:**
```bash
# HMRC Sandbox Test User Credentials (Auto-populated by sandbox utility)
# WARNING: SANDBOX TESTING ONLY - Remove before production
HMRC_TEST_NINO=
HMRC_TEST_BUSINESS_ID=
```

---

## Database Cleanup

```sql
DROP TABLE IF EXISTS sandbox_test_users;
```

---

## Verification

After removal, verify:

- [ ] No files with "sandbox" in name exist
- [ ] No imports of `hmrc_sandbox` or `api_hmrc_sandbox`
- [ ] No routes to `/mtd/sandbox`
- [ ] No `HMRC_TEST_*` variables in `.env`
- [ ] No `sandbox_test_users` table in database
- [ ] Application starts without errors
- [ ] HMRC MTD features still work (non-sandbox)

---

## Quick Commands

```bash
# Find all sandbox references
grep -r "sandbox" app/ templates/ static/ migrations/ docs/

# Find sandbox imports
grep -r "hmrc_sandbox\|api_hmrc_sandbox" app/

# Find sandbox routes
grep -r "/mtd/sandbox\|/api/hmrc/sandbox" app/

# Check .env
grep "HMRC_TEST" .env
```

---

**DO NOT DEPLOY TO PRODUCTION WITHOUT COMPLETING THIS CHECKLIST!**
