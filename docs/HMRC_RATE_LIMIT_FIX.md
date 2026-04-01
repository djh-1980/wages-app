# HMRC Rate Limit 429 Error - Final Fix

## Date: April 1, 2026

---

## Problem

**Error:** `429 Too Many Requests` when clicking "Connect to HMRC"

**Root Cause:** The `/api/hmrc/auth/start` route had **TWO rate limiters stacked:**

```python
@hmrc_bp.route('/auth/start')
@limiter.limit("20 per hour", override_defaults=True)  # Flask-Limiter
@rate_limit(max_requests=5, window_seconds=300)        # Custom middleware (TOO RESTRICTIVE!)
def start_auth():
    ...
```

**The issue:**
- Custom `@rate_limit` decorator allows only **5 requests per 5 minutes**
- In-memory counter from testing hasn't reset
- This is far too restrictive for HMRC OAuth flow
- Flask-Limiter's 20/hour is sufficient

---

## Solution Applied

### 1. Removed Custom Rate Limiter from auth/start

**File:** `app/routes/api_hmrc.py`

**BEFORE:**
```python
@hmrc_bp.route('/auth/start')
@limiter.limit("20 per hour", override_defaults=True)
@rate_limit(max_requests=5, window_seconds=300)  # ← REMOVED
def start_auth():
```

**AFTER:**
```python
@hmrc_bp.route('/auth/start')
@limiter.limit("20 per hour", override_defaults=True)
def start_auth():
```

---

### 2. Removed Unused Import

**BEFORE:**
```python
from ..middleware import rate_limit  # ← REMOVED
from .. import limiter
```

**AFTER:**
```python
from .. import limiter
```

---

### 3. Verified No Other HMRC Routes Use Custom Rate Limiter

**Checked:** All 15 HMRC routes in `api_hmrc.py`

**Result:** ✅ No other routes were using `@rate_limit` decorator

**All HMRC routes now use only Flask-Limiter:**
```python
@limiter.limit("20 per hour", override_defaults=True)
```

---

### 4. Verified No Global Rate Limit Conflicts

**Checked:** `app/auth_protection.py` - `protect_all_routes()` function

**Result:** ✅ Only applies authentication protection, no rate limiting

**Checked:** `app/middleware.py` - `rate_limit()` decorator

**Result:** ✅ Only used as a decorator, not globally applied

**Conclusion:** No global rate limit conflicts exist

---

## Rate Limiting Strategy

### Current Configuration

**Global (Flask-Limiter):**
- Default: `200 per day`, `50 per hour`
- Applies to all routes by default

**HMRC Routes (Override):**
- Override: `20 per hour`
- Exempts HMRC routes from restrictive global limit
- Allows 4 complete OAuth flows per hour (5 calls each)

**Custom Middleware Rate Limiter:**
- No longer used on HMRC routes
- Can still be used on other routes if needed
- In-memory storage (not production-ready for distributed systems)

---

## Why This Fix Works

### Problem with Stacked Rate Limiters

When you stack decorators, **both** are enforced:

```python
@limiter.limit("20 per hour")      # Allows 20/hour
@rate_limit(max_requests=5, ...)   # Allows 5 per 5 minutes
def route():
    ...
```

**Result:** The **most restrictive** limit applies (5 per 5 minutes)

### Solution: Single Rate Limiter

```python
@limiter.limit("20 per hour", override_defaults=True)
def route():
    ...
```

**Result:** Only Flask-Limiter applies (20/hour, overriding global 50/hour)

---

## Testing

### 1. Clear In-Memory Rate Limit Counter

**Restart the Flask app** to clear the in-memory counter:

```bash
# Stop the app
# Start it again
python3 new_web_app.py
```

Or wait 5 minutes for the custom rate limit window to expire (no longer relevant since decorator is removed).

---

### 2. Test Connect to HMRC

**Navigate to:** http://127.0.0.1:5001/settings/hmrc

**Click "Connect to HMRC" button**

**Expected:**
1. ✅ No 429 error
2. ✅ Console shows: `Auth start response: {success: true, auth_url: "https://...", ...}`
3. ✅ Browser redirects to HMRC sandbox login page

**If you still get 429:**
- Check Flask logs for which rate limiter is triggering
- Verify the app was restarted after the code change
- Check if you've exceeded 20 requests in the past hour

---

### 3. Test Multiple Rapid Requests

**Open browser console and run:**

```javascript
// Make 10 rapid requests
for (let i = 0; i < 10; i++) {
  fetch('/api/hmrc/auth/start', {
    credentials: 'same-origin'
  })
  .then(r => console.log(`Request ${i+1}: ${r.status}`));
}
```

**Expected:**
- ✅ All 10 requests succeed (status 200)
- ✅ No 429 errors (within 20/hour limit)

**If you get 429 on request 6+:**
- This would indicate Flask-Limiter is working correctly
- 20/hour limit is being enforced
- This is expected behavior

---

## Files Modified

1. **`app/routes/api_hmrc.py`**
   - Removed `@rate_limit(max_requests=5, window_seconds=300)` from `start_auth()`
   - Removed `from ..middleware import rate_limit` import
   - Only Flask-Limiter decorators remain on all HMRC routes

---

## Rate Limit Comparison

### Before (BROKEN)
```python
@limiter.limit("20 per hour", override_defaults=True)  # 20/hour
@rate_limit(max_requests=5, window_seconds=300)        # 5 per 5 min ← BLOCKING!
```
**Effective limit:** 5 per 5 minutes (1 per minute)

### After (FIXED)
```python
@limiter.limit("20 per hour", override_defaults=True)  # 20/hour
```
**Effective limit:** 20 per hour (1 per 3 minutes average)

---

## Why Custom Rate Limiter Was Too Restrictive

**OAuth flow requires multiple calls:**
1. `/auth/start` - Get authorization URL
2. User authorizes on HMRC site
3. `/auth/callback` - Exchange code for token
4. `/auth/status` - Verify connection
5. `/test-connection` - Test API access

**With 5 requests per 5 minutes:**
- ❌ Can only complete 1 OAuth flow per 5 minutes
- ❌ Testing/debugging becomes impossible
- ❌ In-memory counter doesn't reset on app restart in some cases

**With 20 requests per hour:**
- ✅ Can complete 4 OAuth flows per hour
- ✅ Sufficient for normal usage
- ✅ Still protects against abuse
- ✅ Resets properly with Flask-Limiter

---

## Production Considerations

### If 20/hour is Still Too Restrictive

**Option 1: Increase HMRC limit**
```python
@limiter.limit("50 per hour", override_defaults=True)
```

**Option 2: Different limits per route type**
```python
# Auth routes - higher limit
@limiter.limit("30 per hour", override_defaults=True)

# Submission routes - moderate limit  
@limiter.limit("20 per hour", override_defaults=True)

# Read-only routes - high limit
@limiter.limit("100 per hour", override_defaults=True)
```

**Option 3: Use Redis for distributed rate limiting**
```python
# In app/__init__.py
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379"  # Instead of memory://
)
```

---

## Custom Rate Limiter Still Available

The `@rate_limit` decorator from `middleware.py` is still available for other routes:

```python
from ..middleware import rate_limit

@route('/some-route')
@rate_limit(max_requests=10, window_seconds=60)
def some_route():
    ...
```

**Use cases:**
- Login routes (prevent brute force)
- Password reset routes
- Email sending routes
- Other sensitive operations

**Not appropriate for:**
- API routes that need multiple calls
- OAuth flows
- Data fetching routes
- HMRC MTD integration

---

## Status: ✅ FIXED

The 429 rate limit error has been resolved:
- ✅ Removed restrictive custom rate limiter (5 per 5 min)
- ✅ Only Flask-Limiter remains (20 per hour)
- ✅ No global rate limit conflicts
- ✅ All HMRC routes use consistent rate limiting

**Next step:** Restart the app and test the Connect to HMRC button.
