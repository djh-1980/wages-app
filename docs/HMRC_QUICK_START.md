# HMRC MTD Quick Start Guide

Get up and running with HMRC Making Tax Digital in 5 minutes!

## Prerequisites

✅ HMRC Developer account  
✅ Application registered at developer.service.hmrc.gov.uk  
✅ Client ID and Client Secret  
✅ National Insurance Number (NINO)  
✅ Business ID from HMRC  

---

## Step 1: Configure Credentials (2 minutes)

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` file and add your credentials:**
   ```bash
   # HMRC MTD Configuration
   HMRC_CLIENT_ID=your-client-id-here
   HMRC_CLIENT_SECRET=your-client-secret-here
   HMRC_REDIRECT_URI=http://localhost:5000/api/hmrc/auth/callback
   HMRC_ENVIRONMENT=sandbox  # Start with sandbox for testing
   ```

3. **Update redirect URI in HMRC Developer Hub:**
   - Go to your application settings
   - Add: `http://localhost:5000/api/hmrc/auth/callback`

---

## Step 2: Start Application (1 minute)

1. **Restart the application:**
   ```bash
   python web_app.py
   ```

2. **Database tables are created automatically:**
   - `hmrc_credentials`
   - `hmrc_obligations`
   - `hmrc_submissions`

---

## Step 3: Connect to HMRC (1 minute)

1. **Navigate to Settings:**
   - Click **Settings** in navigation
   - Select **HMRC MTD** from dropdown

2. **Connect:**
   - Click **"Connect to HMRC"** button
   - Sign in with HMRC test credentials (sandbox)
   - Authorize the application
   - You'll be redirected back with success message

3. **Configure details:**
   - Enter your NINO (format: AA123456A)
   - Enter your Business ID
   - Click **"Save Configuration"**

---

## Step 4: Test Connection (30 seconds)

1. **Test the connection:**
   - Click **"Test Connection"** button
   - Should see success message

2. **Refresh obligations:**
   - Click **"Refresh Obligations"** button
   - View your quarterly deadlines

---

## Step 5: Submit Your First Quarter (30 seconds)

1. **Go to Expenses page**

2. **Ensure expenses are entered for the quarter**

3. **Click "Submit to HMRC"** (coming soon in next step)

4. **Select quarter (Q1, Q2, Q3, Q4)**

5. **Review and confirm submission**

---

## What's Included

### ✅ Completed (Phase 1 - Foundation)

- **Database Schema**: Tables for credentials, obligations, submissions
- **OAuth Authentication**: Full OAuth 2.0 flow with token refresh
- **API Client**: HMRC API client with fraud prevention headers
- **Data Mapper**: Maps expenses to HMRC format
- **API Endpoints**: 10+ REST endpoints for all operations
- **Settings UI**: Complete settings page with connection management
- **Documentation**: Comprehensive guides and API docs

### 🚧 Next Steps (Phase 2)

- **Submission UI**: Add submission interface to Expenses page
- **Period Preview**: Preview submission before sending
- **Validation UI**: Show validation errors in UI
- **Auto-sync**: Automatically refresh obligations
- **Notifications**: Email notifications for deadlines

---

## Testing in Sandbox

### Create Test User

1. **Go to HMRC Developer Hub**
2. **Create test user** for Self-Employment
3. **Use test credentials** to sign in
4. **Submit test data** to verify everything works

### Test Checklist

- ✅ Connect to HMRC
- ✅ Refresh obligations
- ✅ View quarterly deadlines
- ✅ Preview submission
- ✅ Submit test period
- ✅ View submission history
- ✅ Disconnect and reconnect

---

## Going Live

### When Ready for Production

1. **Test thoroughly in sandbox first!**

2. **Update environment:**
   ```bash
   HMRC_ENVIRONMENT=production
   ```

3. **Update redirect URI:**
   ```bash
   HMRC_REDIRECT_URI=https://yourdomain.com/api/hmrc/auth/callback
   ```

4. **Use real credentials:**
   - Real NINO
   - Real Business ID
   - Production HMRC login

5. **Enable HTTPS** (required for production)

---

## Troubleshooting

### "Not authenticated" Error
- Click "Disconnect" then "Connect to HMRC"
- Re-authorize the application

### "Invalid NINO format" Error
- Format: AA123456A (2 letters, 6 numbers, 1 letter)
- No spaces, all uppercase

### Connection Test Fails
- Check internet connection
- Verify credentials in `.env`
- Check HMRC service status

### Can't See Obligations
- Click "Refresh Obligations"
- Ensure NINO and Business ID are saved
- Check you're connected to HMRC

---

## Support

### Resources

- 📖 [Full Documentation](HMRC_MTD_INTEGRATION.md)
- 🔧 [HMRC Developer Hub](https://developer.service.hmrc.gov.uk)
- 📚 [API Documentation](https://developer.service.hmrc.gov.uk/api-documentation)
- 🧪 [Test Users](https://developer.service.hmrc.gov.uk/api-test-user)

### Getting Help

1. Check application logs in `logs/` directory
2. Review HMRC API documentation
3. Test in sandbox environment
4. Contact HMRC support for API issues

---

## Security Reminders

⚠️ **Never commit `.env` file to version control**  
⚠️ **Use HTTPS in production**  
⚠️ **Keep credentials secure**  
⚠️ **Rotate credentials regularly**  
⚠️ **Always test in sandbox first**  

---

## Next Steps

1. ✅ Complete Phase 1 setup (you're here!)
2. 🔄 Add submission UI to Expenses page
3. 📊 Test with real expense data
4. 🚀 Go live with production credentials

**Congratulations! Your HMRC MTD integration is ready to use!** 🎉
