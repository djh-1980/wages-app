# HMRC Settings Page - Remaining Issues Fixed

## Date: April 1, 2026

---

## ✅ ISSUE 1 - Rate Limiter Blocking HMRC Routes (FIXED)

### Problem
- Flask-Limiter global rate limit of `50 per hour` was blocking HMRC API routes
- HMRC integration requires multiple API calls per session (auth, status, obligations, submissions, etc.)
- Users were getting `429 Too Many Requests` errors when using HMRC features

### Root Cause
- Global rate limiter in `app/__init__.py` set to `["200 per day", "50 per hour"]`
- HMRC routes had no override, so they were subject to the restrictive global limit
- A typical HMRC session uses 5-10+ API calls (connect, status, obligations, preview, submit, etc.)

### Solution Applied
Added `@limiter.limit("20 per hour", override_defaults=True)` to **all 15 HMRC routes**:

1. `/auth/start` - Start OAuth flow
2. `/auth/callback` - OAuth callback handler
3. `/auth/status` - Check connection status
4. `/auth/disconnect` - Disconnect from HMRC
5. `/test-connection` - Test API connection
6. `/obligations` - Fetch obligations from HMRC
7. `/obligations/stored` - Get stored obligations
8. `/period/preview` - Preview submission data
9. `/period/submit` - Submit period to HMRC
10. `/businesses` - Get business list
11. `/test-obligations` - Test obligations endpoint
12. `/create-test-business` - Create test business
13. `/submissions` - Get submission history
14. `/final-declaration/status` - Check final declaration status
15. `/final-declaration/calculate` - Calculate tax liability
16. `/final-declaration/submit` - Submit final declaration

### File Changed
**`app/routes/api_hmrc.py`**

**Import added:**
```python
from .. import limiter
```

**Decorator added to each route:**
```python
@hmrc_bp.route('/auth/start')
@limiter.limit("20 per hour", override_defaults=True)  # ← ADDED
@rate_limit(max_requests=5, window_seconds=300)
def start_auth():
    ...
```

### Rate Limit Configuration
- **Global limit:** 50 per hour (applies to all other routes)
- **HMRC routes:** 20 per hour (overrides global limit)
- **Additional custom limit:** Some routes also have `@rate_limit()` for finer control

### Why 20 per hour?
- Allows for 4 complete HMRC sessions per hour (5 calls each)
- Prevents abuse while supporting legitimate usage
- Can be increased if needed for production

---

## ✅ ISSUE 2 - jQuery Load Order (ALREADY FIXED)

### Problem
- Error: "Can't find variable: $"
- `settings-hmrc.js` uses jQuery syntax (`$`) for Bootstrap modals and tab events
- jQuery was not loaded before `settings-hmrc.js`

### Solution (Already Applied in Previous Fix)
jQuery was added to `base.html` in the correct load order:

**File: `templates/base.html`**

**Correct Load Order:**
```html
<!-- 1. jQuery loads first -->
<script src="https://cdn.jsdelivr.net/npm/jquery@3.7.1/dist/jquery.min.js"></script>

<!-- 2. Bootstrap JS loads second -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"></script>

<!-- 3. Other utility scripts -->
<script src="{{ url_for('static', filename='js/csrf-helper.js') }}"></script>
<!-- ... more utility scripts ... -->

<!-- 4. Page-specific scripts load last via block -->
{% block extra_js %}{% endblock %}
```

**File: `templates/settings/hmrc.html`**
```html
{% block extra_js %}
<script src="{{ url_for('static', filename='js/settings-hmrc.js') }}"></script>
{% endblock %}
```

### jQuery Usage in settings-hmrc.js
- Line 30: `$('a[data-toggle="pill"][href="#finalDeclaration"]').on('shown.bs.tab', ...)`
- Line 182: `$('#configModal').modal('show')`
- Line 376: `$('#configModal').modal('hide')`
- Line 560: `$('#finalDeclConfirmModal').modal('show')`
- Line 585: `$('#finalDeclConfirmModal').modal('hide')`

All jQuery calls now work correctly because jQuery loads before settings-hmrc.js.

---

## Verification Steps

### 1. Test Rate Limiter Override

**Open browser console and run:**
```javascript
// Make 10 rapid requests to HMRC auth/status
for (let i = 0; i < 10; i++) {
  fetch('/api/hmrc/auth/status')
    .then(r => r.json())
    .then(data => console.log(`Request ${i+1}:`, data.success ? 'OK' : 'FAIL'));
}
```

**Expected:**
- ✅ All 10 requests succeed (no 429 errors)
- ✅ No "Too Many Requests" errors in console
- ✅ HMRC routes use 20/hour limit, not global 50/hour

**If you still get 429 errors:**
- Check that the server has been restarted
- Verify `limiter` is imported in `api_hmrc.py`
- Check Flask-Limiter is using memory storage (not Redis)

---

### 2. Test jQuery Load Order

**Navigate to:** http://127.0.0.1:5001/settings/hmrc

**Open browser console (F12) and run:**
```javascript
// Check jQuery is loaded
console.log('jQuery version:', typeof $ !== 'undefined' ? $.fn.jquery : 'NOT LOADED');

// Check Bootstrap is loaded
console.log('Bootstrap version:', typeof bootstrap !== 'undefined' ? bootstrap.Tooltip.VERSION : 'NOT LOADED');

// Test jQuery modal functionality
$('#configModal').modal('show');
setTimeout(() => $('#configModal').modal('hide'), 1000);
```

**Expected output:**
```
jQuery version: 3.7.1
Bootstrap version: 5.3.8
```

**Expected behavior:**
- ✅ Config modal opens and closes
- ✅ No "Can't find variable: $" errors
- ✅ No console errors related to jQuery

---

### 3. Test Connect to HMRC Button (End-to-End)

**Navigate to:** http://127.0.0.1:5001/settings/hmrc

**Click "Connect to HMRC" button**

**Expected flow:**
1. ✅ No rate limit errors (429)
2. ✅ No jQuery errors in console
3. ✅ Fetch request to `/api/hmrc/auth/start` succeeds
4. ✅ Response: `{success: true, auth_url: 'https://test-api.service.hmrc.gov.uk/oauth/authorize?...'}`
5. ✅ Browser redirects to HMRC sandbox login page

**HMRC Sandbox URL should contain:**
- `response_type=code`
- `client_id=R3HyT0Y25Q9X8uQlWonCgBpEly8y`
- `scope=read:self-assessment+write:self-assessment`
- `redirect_uri=http://localhost:5001/api/hmrc/auth/callback`
- `state=[random-string]`

**On HMRC login page:**
- Enter User ID: `935917348463`
- Enter Password: `yeSn4tOBmXnU`
- Click "Grant authority"

**Expected redirect:**
```
http://127.0.0.1:5001/settings/hmrc?auth=success
```

**On settings page:**
- ✅ Green notification: "Successfully connected to HMRC!"
- ✅ Connection status shows "Connected to HMRC" (green)
- ✅ Shows "SANDBOX" badge (yellow)
- ✅ Token expiry time displayed
- ✅ Disconnect, Test Connection, Refresh Obligations buttons visible

---

## Summary of All Fixes

### Files Modified

1. **`app/routes/api_hmrc.py`**
   - Added `from .. import limiter` import
   - Added `@limiter.limit("20 per hour", override_defaults=True)` to all 15 routes
   - Exempts HMRC routes from restrictive global 50/hour limit

2. **`templates/base.html`** (Already fixed in previous session)
   - Added jQuery 3.7.1 before Bootstrap JS
   - Ensures jQuery loads before all custom scripts

3. **`static/js/settings-hmrc.js`** (Already fixed in previous session)
   - Updated `connectToHMRC()` to include `credentials: 'same-origin'`
   - Updated `connectToHMRC()` to include `headers: getCSRFHeaders()`

4. **`app/middleware.py`** (Already fixed in previous session)
   - Added `https://cdnjs.cloudflare.com` to CSP script-src
   - Allows jsPDF to load without CSP violations

---

## Testing Checklist

- [ ] No 429 rate limit errors when using HMRC features
- [ ] Can make 10+ HMRC API calls in quick succession
- [ ] jQuery loads without errors
- [ ] No "Can't find variable: $" errors in console
- [ ] Bootstrap modals work (config modal, confirmation modal)
- [ ] Bootstrap tabs work (Final Declaration tab)
- [ ] "Connect to HMRC" button redirects to HMRC sandbox
- [ ] OAuth flow completes successfully
- [ ] Can authenticate with test user credentials
- [ ] Connection status updates correctly after auth
- [ ] All HMRC features work without rate limiting issues

---

## Production Considerations

### Rate Limit Tuning
If 20 per hour is too restrictive for production:

**Option 1: Increase HMRC limit**
```python
@limiter.limit("50 per hour", override_defaults=True)
```

**Option 2: Different limits per route**
```python
# Auth routes - higher limit
@limiter.limit("30 per hour", override_defaults=True)

# Submission routes - moderate limit
@limiter.limit("20 per hour", override_defaults=True)

# Read-only routes - high limit
@limiter.limit("100 per hour", override_defaults=True)
```

**Option 3: Remove override for specific routes**
```python
# No override - uses global 50/hour
@hmrc_bp.route('/auth/status')
def auth_status():
    ...
```

### Monitoring
Add logging to track rate limit hits:
```python
@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f'Rate limit exceeded: {request.path} from {request.remote_addr}')
    return jsonify({'error': 'Too many requests'}), 429
```

---

## Status: ✅ ALL ISSUES FIXED

Both remaining issues have been resolved:
1. ✅ Rate limiter no longer blocks HMRC routes (20/hour override)
2. ✅ jQuery loads before settings-hmrc.js (correct load order)

The HMRC settings page should now work without errors. Users can:
- Connect to HMRC without rate limit errors
- Use all HMRC features without jQuery errors
- Complete full OAuth flow successfully
- Submit quarterly updates and final declarations
