# Security Audit Report - HMRC MTD Compliance

**Date:** March 19, 2026  
**Application:** TVS Wages App  
**Purpose:** HMRC Making Tax Digital Integration Security Review

---

## Executive Summary

This security audit evaluates the TVS Wages application for HMRC MTD compliance and general web security best practices. The application handles sensitive financial data and integrates with HMRC's API, requiring robust security measures.

**Overall Status:** ⚠️ **MODERATE RISK** - Several critical security improvements needed before production deployment.

---

## 🔴 CRITICAL ISSUES (Must Fix for HMRC Compliance)

### 1. **Exposed API Keys in .env File**
- **Risk Level:** CRITICAL
- **Issue:** Google Maps API key and HMRC credentials visible in .env file
- **Impact:** If .env file is committed to git or exposed, API keys can be stolen
- **Fix Required:**
  ```bash
  # Verify .env is in .gitignore
  echo ".env" >> .gitignore
  
  # Check git history for exposed keys
  git log --all --full-history -- .env
  
  # If found in history, rotate ALL API keys immediately
  ```

### 2. **Weak Session Security**
- **Risk Level:** CRITICAL
- **Issue:** No session configuration for security flags
- **Current State:**
  - No `SESSION_COOKIE_SECURE` flag (allows cookies over HTTP)
  - No `SESSION_COOKIE_HTTPONLY` flag (vulnerable to XSS)
  - No `SESSION_COOKIE_SAMESITE` protection (vulnerable to CSRF)
- **Fix Required:**
  ```python
  # In app/config.py
  SESSION_COOKIE_SECURE = True  # HTTPS only
  SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
  SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
  PERMANENT_SESSION_LIFETIME = timedelta(hours=4)  # Match HMRC token lifetime
  ```

### 3. **OAuth State Validation Disabled**
- **Risk Level:** CRITICAL
- **Issue:** CSRF protection temporarily disabled in OAuth callback
- **Location:** `app/routes/api_hmrc.py:53-60`
- **Current Code:**
  ```python
  # Verify state parameter (temporarily lenient for testing)
  stored_state = session.get('hmrc_oauth_state')
  if stored_state and stored_state != state:
      # Log warning but continue for now
      print(f"WARNING: State mismatch - stored: {stored_state}, received: {state}")
  # TODO: Re-enable strict validation after fixing session persistence
  ```
- **Fix Required:** Re-enable strict state validation immediately
- **Impact:** Vulnerable to CSRF attacks during OAuth flow

### 4. **Tokens Stored in Plain Text**
- **Risk Level:** CRITICAL
- **Issue:** HMRC access tokens and refresh tokens stored unencrypted in SQLite database
- **Location:** `app/services/hmrc_auth.py:158-168`
- **Impact:** If database is compromised, attacker gains full HMRC API access
- **Fix Required:** Encrypt tokens at rest using Fernet or similar

---

## 🟡 HIGH PRIORITY ISSUES

### 5. **No HTTPS Enforcement**
- **Risk Level:** HIGH
- **Issue:** Application runs on HTTP (localhost:5001)
- **Impact:** Data transmitted in plain text, vulnerable to interception
- **HMRC Requirement:** Production must use HTTPS
- **Fix Required:**
  - Development: Use self-signed certificate or ngrok
  - Production: Proper SSL/TLS certificate (Let's Encrypt)

### 6. **SQL Injection Risk (Low but Present)**
- **Risk Level:** MEDIUM-HIGH
- **Issue:** Most queries use parameterized queries (✅ good), but some use string formatting
- **Example:** `app/services/runsheet_service.py:68`
  ```python
  cursor.execute(f"""
      SELECT status, COUNT(*) as count
      FROM run_sheet_jobs
      WHERE {date_filter}
  """)
  ```
- **Fix Required:** Ensure ALL queries use parameterized inputs

### 7. **No Rate Limiting**
- **Risk Level:** HIGH
- **Issue:** No rate limiting on API endpoints
- **Impact:** Vulnerable to brute force attacks and API abuse
- **Fix Required:** Implement Flask-Limiter
  ```python
  from flask_limiter import Limiter
  limiter = Limiter(app, key_func=get_remote_address)
  
  @hmrc_bp.route('/auth/start')
  @limiter.limit("5 per minute")
  def start_auth():
      ...
  ```

### 8. **No Input Validation on File Uploads**
- **Risk Level:** HIGH
- **Issue:** File upload endpoints don't validate file types or scan for malware
- **Impact:** Potential for malicious file uploads
- **Fix Required:**
  - Validate file extensions
  - Check MIME types
  - Limit file sizes (already set to 50MB)
  - Consider virus scanning for production

---

## 🟢 MEDIUM PRIORITY ISSUES

### 9. **Weak Secret Key Generation**
- **Risk Level:** MEDIUM
- **Issue:** SECRET_KEY in .env is static
- **Current:** `SECRET_KEY=99cd2927171ddd2572fb9d52779939dde003e9bb3a63a8954e1e14bc463ba346`
- **Recommendation:** Rotate secret keys periodically
- **Best Practice:** Use environment-specific keys

### 10. **No Content Security Policy (CSP)**
- **Risk Level:** MEDIUM
- **Issue:** No CSP headers to prevent XSS attacks
- **Fix Required:**
  ```python
  @app.after_request
  def set_security_headers(response):
      response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;"
      response.headers['X-Content-Type-Options'] = 'nosniff'
      response.headers['X-Frame-Options'] = 'DENY'
      response.headers['X-XSS-Protection'] = '1; mode=block'
      return response
  ```

### 11. **Database Not Encrypted**
- **Risk Level:** MEDIUM
- **Issue:** SQLite database stored in plain text
- **Impact:** If server is compromised, all data is readable
- **Recommendation:** Use SQLCipher for database encryption in production

### 12. **No Audit Logging**
- **Risk Level:** MEDIUM
- **Issue:** No comprehensive audit trail for HMRC submissions
- **HMRC Requirement:** Maintain audit logs for compliance
- **Fix Required:** Log all HMRC API calls, submissions, and authentication events

---

## ✅ GOOD SECURITY PRACTICES FOUND

### Strengths:
1. ✅ **Parameterized SQL Queries** - Most database queries use proper parameterization
2. ✅ **Environment Variables** - Secrets stored in .env (not hardcoded)
3. ✅ **Token Refresh Logic** - Proper OAuth token refresh implementation
4. ✅ **Fraud Prevention Headers** - HMRC-required headers implemented
5. ✅ **Error Handling** - Comprehensive error handling in API calls
6. ✅ **Production Config Check** - Enforces SECRET_KEY in production mode
7. ✅ **Database Connection Management** - Proper context managers used
8. ✅ **CORS Not Enabled** - No unnecessary CORS exposure

---

## 📋 HMRC-SPECIFIC REQUIREMENTS

### Required for MTD Compliance:

1. **✅ OAuth 2.0 Implementation** - Correctly implemented
2. **✅ Fraud Prevention Headers** - All required headers present
3. **⚠️ HTTPS in Production** - Not yet configured
4. **⚠️ Token Security** - Tokens not encrypted at rest
5. **⚠️ Audit Logging** - Not comprehensive enough
6. **✅ Scope Management** - Correct scopes requested
7. **⚠️ State Parameter Validation** - Currently disabled (MUST FIX)

---

## 🔧 IMMEDIATE ACTION ITEMS (Before Production)

### Priority 1 (Critical - Do Now):
1. ✅ Verify .env is in .gitignore
2. ✅ Check git history for exposed secrets
3. ❌ Re-enable OAuth state validation
4. ❌ Add session security flags
5. ❌ Encrypt HMRC tokens at rest

### Priority 2 (High - This Week):
1. ❌ Implement HTTPS (even for development)
2. ❌ Add rate limiting to all API endpoints
3. ❌ Implement comprehensive audit logging
4. ❌ Add Content Security Policy headers
5. ❌ Review all SQL queries for injection risks

### Priority 3 (Medium - Before Go-Live):
1. ❌ Set up database encryption (SQLCipher)
2. ❌ Implement file upload validation
3. ❌ Add security headers middleware
4. ❌ Set up automated security scanning
5. ❌ Create security incident response plan

---

## 🛡️ RECOMMENDED SECURITY ENHANCEMENTS

### Additional Protections:

1. **Two-Factor Authentication** (for admin access)
2. **IP Whitelisting** (for HMRC API calls in production)
3. **Automated Backup Encryption**
4. **Security Monitoring & Alerts**
5. **Regular Security Audits**
6. **Penetration Testing** (before production launch)

---

## 📊 Security Score

| Category | Score | Status |
|----------|-------|--------|
| Authentication & Authorization | 6/10 | ⚠️ Needs Improvement |
| Data Protection | 4/10 | 🔴 Critical Issues |
| API Security | 7/10 | 🟡 Good but Incomplete |
| Input Validation | 7/10 | 🟡 Mostly Good |
| Session Management | 3/10 | 🔴 Critical Issues |
| HTTPS/TLS | 2/10 | 🔴 Not Configured |
| Audit & Logging | 5/10 | ⚠️ Needs Improvement |
| **OVERALL** | **5.1/10** | ⚠️ **NOT PRODUCTION READY** |

---

## 🎯 CONCLUSION

The application has a solid foundation with good OAuth implementation and proper use of parameterized queries. However, **critical security issues must be addressed before production deployment**, particularly:

1. OAuth state validation must be re-enabled
2. Session security must be properly configured
3. HMRC tokens must be encrypted at rest
4. HTTPS must be enforced
5. Comprehensive audit logging must be implemented

**Estimated Time to Production-Ready:** 2-3 days of focused security work

---

## 📞 NEXT STEPS

1. **Review this report** with your development team
2. **Prioritize fixes** based on risk levels
3. **Implement critical fixes** immediately
4. **Test security measures** thoroughly
5. **Schedule security review** before HMRC production deployment
6. **Consider hiring security consultant** for final audit

---

**Report Generated:** March 19, 2026  
**Auditor:** Cascade AI Security Analysis  
**Classification:** Internal Use Only
