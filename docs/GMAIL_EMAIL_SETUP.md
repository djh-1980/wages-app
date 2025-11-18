# Gmail Email Notifications Setup

## Overview
The auto-sync system now sends email notifications using the **same Gmail API** you're already using to download files. No SMTP configuration needed!

## How It Works

1. **Same Authentication** - Uses your existing `credentials.json` and `token.json`
2. **Gmail API** - Sends emails through Gmail's API (not SMTP)
3. **Your Account** - Sends from the same Gmail account that receives the runsheets/payslips
4. **Automatic** - Sends whenever new files are processed

## First-Time Setup

### Step 1: Add Send Permission

Since we're adding a new permission (send email), you need to re-authorize:

```bash
# Delete the existing token
rm token.json

# Restart the app
# The next time it tries to access Gmail, it will ask for authorization
```

### Step 2: Authorize

When the app runs (or when the sync runs), you'll see a browser window asking you to:
- ✅ Read emails (already had this)
- ✅ **Send emails** (NEW - authorize this)

Click "Allow" and you're done!

### Step 3: Configure Recipient (Optional)

By default, emails go to: `danielhanson1980@gmail.com`

To change this, set an environment variable:

```bash
# In your terminal (temporary)
export NOTIFICATION_EMAIL="your-email@gmail.com"

# Or add to your shell profile (~/.zshrc or ~/.bash_profile) for permanent
echo 'export NOTIFICATION_EMAIL="your-email@gmail.com"' >> ~/.zshrc
```

## What You'll Receive

### Email Subject Examples:
- ✅ Wages App Sync - 1 Runsheet(s) Processed - 18/11/2025 22:30
- ✅ Wages App Sync - 1 Payslip(s) Processed - 19/11/2025 10:00
- ✅ Wages App Sync - 2 Runsheet(s), 1 Payslip(s) Processed - 19/11/2025 10:30
- ⚠️ Wages App Sync - Completed with Errors (1 Runsheet(s)) - 18/11/2025 22:30
- ℹ️ Wages App Sync - No New Files - 18/11/2025 18:30

### Email Content:
- **Visual Summary** with counts
- **Runsheets Downloaded** count
- **Runsheet Jobs Imported** count
- **Payslips Downloaded** count
- **Payslips Imported** count
- **Jobs Synced** with pay data count
- **Error List** (if any)
- **Next Steps** checklist

### When You'll Get Emails:
- ✅ When new runsheets are downloaded and imported
- ✅ When new payslips are downloaded and imported
- ✅ When errors occur during sync
- ❌ NOT when there are no new files (unless errors)

## Backup

Even if email sending fails, a copy is always saved to:
```
logs/sync_notifications/sync_YYYYMMDD_HHMMSS.html
```

You can open these in a browser to see what would have been emailed.

## Troubleshooting

### "Email failed to send"
1. Check `logs/periodic_sync.log` for the error
2. Make sure `token.json` exists and is valid
3. Try deleting `token.json` and re-authorizing
4. Check the backup HTML file in `logs/sync_notifications/`

### "Permission denied"
- You need to re-authorize with the new "send email" scope
- Delete `token.json` and restart the app

### "Wrong recipient"
- Set the `NOTIFICATION_EMAIL` environment variable
- Or edit `app/services/periodic_sync.py` line 427 to change the default

## Testing

To test email sending without waiting for the sync:

```python
from app.services.gmail_notifier import gmail_notifier

# Test email
success = gmail_notifier.send_email(
    to_email="your-email@gmail.com",
    subject="Test Email from Wages App",
    html_body="<h1>Test</h1><p>This is a test email.</p>",
    text_body="Test - This is a test email."
)

print(f"Email sent: {success}")
```

## Security

- ✅ Uses OAuth2 (more secure than SMTP passwords)
- ✅ Token stored locally in `token.json`
- ✅ No passwords in code or config files
- ✅ Same security as Gmail file downloads
- ✅ Can revoke access anytime from Google Account settings

## Benefits Over SMTP

1. **No password needed** - Uses OAuth2
2. **Same auth as downloads** - One setup for everything
3. **More reliable** - Gmail API is more stable than SMTP
4. **Better security** - Token-based, not password-based
5. **Easier setup** - Already have credentials.json
