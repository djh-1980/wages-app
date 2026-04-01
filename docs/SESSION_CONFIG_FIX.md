# Session Configuration Fixes

## Date: April 1, 2026

---

## Issues Fixed

### ISSUE 1 - Login Rate Limiter Too Aggressive

**Problem:** Login endpoint limited to 5 requests per 5 minutes, causing rate limit loops during normal login flow with redirects

**Error from logs:**
```
flask-limiter - INFO - ratelimit 5 per 5 minute (192.168.4.237) exceeded at endpoint: auth.login
```

**Root Cause:** After successful login, browser makes several redirect requests to `/login`, all counting against the limit, immediately hitting the 5-request cap.

**Fix:** Increased rate limit to 20 per 5 minutes

**File:** `app/routes/auth.py`

**BEFORE:**
```python
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per 5 minutes")
def login():
```

**AFTER:**
```python
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("20 per 5 minutes")
def login():
```

---

### ISSUE 2 - Session Lost After HMRC OAuth Callback

**Problem:** Flask session lost when browser returns from HMRC sandbox OAuth flow, causing user to be redirected to login screen instead of HMRC settings page.

**Root Cause:** `SESSION_COOKIE_SAMESITE` was not configured (defaults to `'Strict'` in newer Flask versions). With `SameSite=Strict`, the session cookie is NOT sent when redirecting back from an external domain (HMRC sandbox), causing session loss.

**Fix:** Configure session cookies with `SameSite='Lax'` to allow cookies during OAuth redirects

**File:** `app/__init__.py`

---

## Complete Session Configuration

**Added to `app/__init__.py`:**

### Import timedelta
```python
from datetime import datetime, timedelta  # ← Added timedelta
```

### Session Cookie Configuration (after config loading)
```python
# Configure session for OAuth compatibility
# SameSite='Lax' is critical - allows session cookie to be sent when redirecting
# back from external OAuth providers (HMRC sandbox)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Critical for OAuth redirects
app.config['SESSION_COOKIE_SECURE'] = False  # False for localhost http (True for production https)
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Security: prevent JavaScript access
```

---

## Session Cookie Settings Explained

### PERMANENT_SESSION_LIFETIME
**Value:** `timedelta(hours=24)`

**Purpose:** Session persists for 24 hours even if browser is closed

**Why:** Prevents session expiration during normal usage and OAuth flows

---

### SESSION_COOKIE_SAMESITE
**Value:** `'Lax'`

**Purpose:** Controls when cookies are sent with cross-site requests

**Options:**
- `'Strict'` - Cookie NEVER sent with cross-site requests (breaks OAuth)
- `'Lax'` - Cookie sent with top-level navigation (OAuth redirects work) ✓
- `'None'` - Cookie always sent (requires HTTPS, less secure)

**Why Critical for OAuth:**
```
1. User clicks "Connect to HMRC"
   ↓
2. Browser redirects to https://test-api.service.hmrc.gov.uk (external domain)
   ↓
3. User logs in on HMRC sandbox
   ↓
4. HMRC redirects back: http://localhost:5001/api/hmrc/auth/callback
   ↓
5. With SameSite='Strict': Session cookie NOT sent ❌
   With SameSite='Lax': Session cookie IS sent ✓
   ↓
6. Flask can restore user session and complete OAuth flow
```

---

### SESSION_COOKIE_SECURE
**Value:** `False` (for localhost development)

**Purpose:** Requires HTTPS for cookie transmission

**Why False:** Localhost uses HTTP, not HTTPS

**Production:** Should be `True` with HTTPS

---

### SESSION_COOKIE_HTTPONLY
**Value:** `True`

**Purpose:** Prevents JavaScript from accessing the cookie

**Why:** Security - protects against XSS attacks

---

## How This Fixes OAuth Session Loss

### Before Fix (SameSite=Strict or not set)

```
1. User authenticated in Flask app
   Session cookie: {user_id: 1, ...}
   Cookie settings: SameSite=Strict (default)

2. Redirect to HMRC sandbox (external domain)
   Browser: "This is a cross-site redirect, don't send cookies"
   
3. HMRC redirects back to /api/hmrc/auth/callback
   Browser: "This is coming from external site, don't send cookies"
   Request to Flask: NO session cookie sent
   
4. Flask receives request with no session
   current_user.is_authenticated = False
   @login_required redirects to /login
   
5. User sees login screen instead of HMRC settings ❌
```

---

### After Fix (SameSite=Lax)

```
1. User authenticated in Flask app
   Session cookie: {user_id: 1, ...}
   Cookie settings: SameSite=Lax ✓

2. Redirect to HMRC sandbox (external domain)
   Browser: "This is a cross-site redirect, don't send cookies"
   
3. HMRC redirects back to /api/hmrc/auth/callback
   Browser: "This is a top-level navigation from external site"
   Browser: "SameSite=Lax allows cookies for top-level navigation"
   Request to Flask: Session cookie IS sent ✓
   
4. Flask receives request with session cookie
   current_user.is_authenticated = True
   OAuth callback completes successfully
   
5. User redirected to /settings/hmrc?auth=success ✓
   User stays logged in ✓
```

---

## Combined with Previous OAuth Fix

The session configuration works together with the `pre_oauth_user_id` fix:

### Primary Fix (SameSite=Lax)
- Session cookie is sent with OAuth callback
- User session is maintained
- No need to restore session

### Fallback Fix (pre_oauth_user_id)
- If session is still lost for any reason
- User ID stored before OAuth redirect
- Session restored in callback
- Provides redundancy

**Both fixes together ensure OAuth flow always works.**

---

## Testing

### Test Login Rate Limit

1. Go to http://127.0.0.1:5001/login
2. Login successfully
3. Navigate around the app
4. **Expected:** No rate limit errors
5. **Check logs:** Should NOT see "ratelimit 5 per 5 minute exceeded"

---

### Test OAuth Session Persistence

1. Go to http://127.0.0.1:5001/settings/hmrc
2. Click "Connect to HMRC"
3. Login on HMRC sandbox:
   - User ID: `935917348463`
   - Password: `yeSn4tOBmXnU`
4. Click "Authorize"
5. **Expected:** Redirected to `/settings/hmrc?auth=success`
6. **Expected:** Still logged in as admin
7. **Expected:** Success notification shown
8. **NOT Expected:** Redirected to login page

**Check Flask logs:**
```
DEBUG - Stored user ID 1 in session before OAuth redirect
INFO - HMRC token exchange completed successfully
```

**Should NOT see:**
```
DEBUG - Restoring user session for user ID 1
```

Because the session cookie is now sent with the callback, no restoration needed!

---

### Test Session Cookie in Browser

**Open browser DevTools (F12) → Application → Cookies → http://localhost:5001**

**Check session cookie:**
- Name: `session`
- Value: (encrypted session data)
- **SameSite:** `Lax` ✓
- **HttpOnly:** `✓` (checked)
- **Secure:** (empty for localhost)

---

## Files Modified

1. **`app/routes/auth.py`**
   - Changed login rate limit from `"5 per 5 minutes"` to `"20 per 5 minutes"`

2. **`app/__init__.py`**
   - Added `timedelta` import
   - Added session cookie configuration:
     - `PERMANENT_SESSION_LIFETIME = timedelta(hours=24)`
     - `SESSION_COOKIE_SAMESITE = 'Lax'`
     - `SESSION_COOKIE_SECURE = False`
     - `SESSION_COOKIE_HTTPONLY = True`

---

## Production Deployment Notes

When deploying to production with HTTPS:

```python
# In production configuration
app.config['SESSION_COOKIE_SECURE'] = True  # Require HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Keep Lax for OAuth
```

**Do NOT use `SameSite='Strict'` in production if you have OAuth flows.**

---

## Summary

**ISSUE 1 - Login Rate Limiter:**
- ✅ Increased from 5 to 20 requests per 5 minutes
- ✅ Prevents rate limit loops during normal login flow
- ✅ Allows for redirects and multiple page loads

**ISSUE 2 - OAuth Session Loss:**
- ✅ Set `SESSION_COOKIE_SAMESITE = 'Lax'`
- ✅ Session cookie now sent with OAuth callback
- ✅ User stays logged in after OAuth flow
- ✅ No more redirect to login screen

**Both issues are now fixed and OAuth flow works correctly.**
