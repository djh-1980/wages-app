# Authentication System Setup Guide

**Date:** March 19, 2026  
**Version:** 1.0  
**Status:** Ready for Implementation

---

## 🎯 Overview

A complete Flask-Login authentication system has been built for your TVS Wages application. This guide will help you set it up and start using it.

---

## 📦 Installation Steps

### Step 1: Install Required Packages

```bash
cd /Users/danielhanson/CascadeProjects/Wages-App
pip install -r requirements_auth.txt
```

This installs:
- Flask-Login (user session management)
- Flask-Bcrypt (password hashing)
- email-validator (email validation)

### Step 2: Initialize Database

The database will automatically create the `users` table when you restart the app. The table is already configured in `app/database.py`.

### Step 3: Create Your Admin Account

Run the admin user creation script:

```bash
python create_admin_user.py
```

You'll be prompted for:
- Username (e.g., `daniel`)
- Email (e.g., `danielhanson993@gmail.com`)
- Password (minimum 8 characters)
- Password confirmation

**Example:**
```
Username: daniel
Email: danielhanson993@gmail.com
Password: ********
Confirm password: ********

✓ Admin user created successfully!
```

### Step 4: Restart Your Application

```bash
./start_web.sh
```

The app will now require login for all pages.

---

## 🔐 How It Works

### Login Flow

1. **Visit any page** → Redirected to `/login`
2. **Enter credentials** → Authenticated
3. **Redirected back** to the page you wanted
4. **Session persists** (optional "Remember Me")

### Protected Routes

**All routes now require authentication:**
- `/` - Dashboard
- `/wages` - Wages page
- `/payslips` - Payslips
- `/runsheets` - Runsheets
- `/reports` - Reports
- `/expenses` - Expenses
- `/settings/*` - All settings pages
- `/api/*` - All API endpoints

**Public routes (no login required):**
- `/login` - Login page
- `/static/*` - CSS, JS, images

### User Management

**Admin users can:**
- Create new users
- Edit user details
- Deactivate users
- View all users
- Promote users to admin

**Regular users can:**
- Change their own password
- Update their email
- View their own profile

---

## 🛠️ Features Implemented

### Security Features

✅ **Password Hashing** - Bcrypt with salt  
✅ **Session Management** - Secure cookies with HTTPONLY  
✅ **CSRF Protection** - Built into Flask-Login  
✅ **Rate Limiting** - 10 login attempts per 5 minutes  
✅ **Remember Me** - Optional persistent sessions  
✅ **Last Login Tracking** - Audit trail  
✅ **Account Deactivation** - Soft delete users  

### User Features

✅ **Login/Logout** - Full authentication flow  
✅ **Change Password** - Secure password updates  
✅ **User Management API** - RESTful endpoints  
✅ **Admin Controls** - User administration  
✅ **Session Timeout** - 4 hours (matches HMRC tokens)  

---

## 📝 Usage Examples

### Creating Additional Users (via Python)

```python
from app.models.user import User

# Create regular user
user = User.create_user(
    username='john',
    email='john@example.com',
    password='SecurePass123',
    is_admin=False
)

# Create admin user
admin = User.create_user(
    username='admin',
    email='admin@example.com',
    password='AdminPass123',
    is_admin=True
)
```

### Creating Users via API (Admin Only)

```bash
# Login first to get session cookie
curl -X POST http://localhost:5001/login \
  -d "username=daniel&password=yourpassword"

# Create new user
curl -X POST http://localhost:5001/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "SecurePass123",
    "is_admin": false
  }'
```

### Changing Password (via UI)

1. Login to the application
2. Go to `/change-password`
3. Enter current password
4. Enter new password (min 8 characters)
5. Confirm new password
6. Submit

---

## 🔧 Configuration

### Session Settings (in `app/config.py`)

```python
SESSION_COOKIE_SECURE = True  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
PERMANENT_SESSION_LIFETIME = 14400  # 4 hours
```

### Login Settings (in `app/__init__.py`)

```python
login_manager.login_view = 'auth.login'  # Redirect to login
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
```

---

## 🚨 Important Security Notes

### Password Requirements

- Minimum 8 characters
- Stored as bcrypt hash (never plain text)
- Cannot be recovered (only reset)

### Session Security

- Sessions expire after 4 hours
- "Remember Me" extends to 30 days
- Sessions invalidated on logout
- Secure cookies in production (HTTPS)

### Rate Limiting

- 10 login attempts per 5 minutes per IP
- Prevents brute force attacks
- Automatic cooldown period

### Admin Privileges

- Only admins can create/edit/delete users
- Admins cannot delete themselves
- At least one admin must exist

---

## 🎨 Customization

### Change Login Page Styling

Edit `templates/auth/login.html`:
- Gradient background colors
- Logo/branding
- Form styling
- Messages

### Add Additional User Fields

1. Update `users` table in `app/database.py`
2. Add fields to `User` model in `app/models/user.py`
3. Update forms in `templates/auth/`
4. Update API endpoints in `app/routes/auth.py`

### Custom Authentication Logic

Edit `app/routes/auth.py`:
- Add two-factor authentication
- Add password reset via email
- Add account lockout after failed attempts
- Add IP whitelisting

---

## 🐛 Troubleshooting

### "No module named 'flask_login'"

```bash
pip install -r requirements_auth.txt
```

### "Table users does not exist"

```bash
# Restart the app to create the table
./start_web.sh
```

### "Invalid username or password"

- Check username is correct (case-sensitive)
- Check password is correct
- Verify user exists: `python create_admin_user.py`
- Check user is active in database

### "Session expired" message

- Sessions expire after 4 hours
- Use "Remember Me" for longer sessions
- Re-login to continue

### Can't access any pages

- Make sure you created an admin user
- Check you're using correct credentials
- Verify database has users table
- Check Flask-Login is installed

---

## 📊 Database Schema

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

---

## 🔄 Migration from No Auth

### What Changes

**Before:** Anyone could access everything  
**After:** Must login to access anything

### User Impact

1. First visit → Redirected to login
2. Enter credentials → Access granted
3. Session persists → No repeated logins
4. Logout → Must login again

### Data Impact

- No data changes
- All existing data remains
- Only access control added

---

## 📈 Next Steps

### Recommended Enhancements

1. **Add User Management UI** - Admin page to manage users
2. **Password Reset** - Email-based password recovery
3. **Two-Factor Auth** - TOTP or SMS verification
4. **Audit Logging** - Track user actions
5. **IP Whitelisting** - Restrict access by IP
6. **Account Lockout** - After failed login attempts

### Optional Features

- User profiles with additional info
- User preferences/settings
- Activity history per user
- Email notifications
- API key authentication for scripts

---

## 🆘 Support

### Files Created

- `app/models/user.py` - User model
- `app/routes/auth.py` - Authentication routes
- `app/auth_decorator.py` - Protection decorators
- `templates/auth/login.html` - Login page
- `templates/auth/change_password.html` - Password change
- `create_admin_user.py` - Admin creation script
- `requirements_auth.txt` - Dependencies

### Files Modified

- `app/__init__.py` - Flask-Login integration
- `app/database.py` - Users table schema

### Getting Help

1. Check this guide
2. Review security audit reports
3. Check Flask-Login documentation
4. Test in development first

---

## ✅ Verification Checklist

After setup, verify:

- [ ] Packages installed (`pip list | grep Flask-Login`)
- [ ] Admin user created (`python create_admin_user.py`)
- [ ] App restarts without errors
- [ ] Login page loads at `/login`
- [ ] Can login with admin credentials
- [ ] Redirected to dashboard after login
- [ ] Can access all pages when logged in
- [ ] Logout works correctly
- [ ] Cannot access pages when logged out
- [ ] Session persists across page loads

---

**Authentication system is now ready to protect your application!**

For production deployment, ensure:
- HTTPS is enabled
- Strong passwords enforced
- Regular security updates
- Backup encryption keys
- Monitor login attempts
