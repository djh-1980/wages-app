# Auto-Sync System Improvements

## Overview
Completely redesigned the automatic sync process to be intelligent, efficient, and provide detailed notifications.

## Key Improvements

### 1. **Intelligent Time-Based Syncing**
- **Runsheets**: Only checks during arrival window (18:00-06:00 daily)
- **Payslips**: Only checks on Tuesdays during arrival window (06:00-14:00)
- **Efficiency**: Doesn't waste resources checking when files won't arrive

### 2. **Database-Aware Processing**
- Checks latest runsheet date in database before downloading
- Checks latest payslip week in database before downloading
- Only downloads and processes NEW files
- Avoids re-processing existing data

### 2.5 **Smart Stop Logic** ⭐ NEW
- **Process once, then STOP until next cycle**
  - Runsheets: After processing → STOPS until tomorrow (midnight reset)
  - Payslips: After processing → STOPS until next Tuesday (weekly reset)
- **No more checking after email sent**
  - Email sent = processing complete
  - Sync completely stops running
  - Resumes automatically next day/week
- **Maximum efficiency**
  - Zero wasted Gmail API calls
  - Zero unnecessary processing
  - Logs: "already processed - skipping until tomorrow/next week"

### 3. **Conditional Processing**
- Only imports runsheets if new ones were downloaded
- Only imports payslips if new ones were downloaded
- Automatically syncs payslip data to runsheets after import
- Each step only runs if the previous step succeeded

### When You'll Get Emails:
- ✅ When new runsheets are downloaded and imported
- ✅ When new payslips are downloaded and imported
- ✅ When payslip data is synced to runsheets
- ✅ When errors occur during sync
- ❌ NOT when there are no new files (unless errors)

### Email Subject Examples:
- ✅ Wages App Sync - 1 Runsheet(s) Processed - 18/11/2025 22:30
- ✅ Wages App Sync - 1 Payslip(s) Processed - 19/11/2025 10:00
- ✅ Wages App Sync - 2 Runsheet(s), 1 Payslip(s) Processed - 19/11/2025 10:30
- ⚠️ Wages App Sync - Completed with Errors (1 Runsheet(s)) - 18/11/2025 22:30

### 4. **Comprehensive Tracking**
Tracks everything that happens:
- Runsheets downloaded count
- Runsheets imported (job count)
- Payslips downloaded count
- Payslips imported count
- Jobs synced with pay data
- Any errors that occurred

### 5. **Email Notifications**
Sends you a detailed HTML email when:
- New files are downloaded
- Files are processed
- Errors occur

**Email includes:**
- Visual summary with counts
- Status indicator (Success/Errors/No New Files)
- List of any errors
- Next steps checklist
- Professional formatting

### 6. **Error Handling**
- Each step wrapped in try/catch
- Errors logged but don't stop the process
- All errors collected and reported
- Sync continues even if one step fails

### 7. **Performance Optimizations**
- Fast `find` command for file discovery (vs slow Python rglob)
- Increased timeouts for import steps
- Only processes files modified recently
- Skips unnecessary steps

## How It Works

### Daily Runsheet Sync (18:00-06:00)
1. Check latest runsheet date in database
2. Download any newer runsheets from Gmail
3. If new files downloaded → Import them
4. Log results

### Tuesday Payslip Sync (06:00-14:00)
1. Check latest payslip week in database
2. Download any newer payslips from Gmail
3. If new files downloaded → Import them
4. Automatically sync payslip data to runsheets
5. Send email notification with summary
6. Log results

### Every 30 Minutes
- Runs the intelligent sync check
- Only does work if in the right time window
- Logs what it checked and what it did

## What You Need to Do

### Nothing! (Almost)
The system now handles everything automatically:
- ✅ Downloads new files
- ✅ Imports them into database
- ✅ Syncs payslip data to runsheets
- ✅ Updates addresses where needed
- ✅ Sends you notifications

### Just Check the Website
After you get an email notification:
1. Open the website
2. Verify the data looks correct
3. Update any job statuses (DNCO, missed, etc.)
4. Done!

## Email Notification Setup ✅

**Uses Gmail API** - Same authentication as file downloads!

The system now sends emails using the Gmail API (same credentials as downloading files).

### First Time Setup:
1. Delete `token.json` (to re-authenticate with new permissions)
2. Restart the app
3. When prompted, authorize the "send email" permission
4. Done!

### Configure Recipient:
Set environment variable (optional, defaults to danielhanson1980@gmail.com):
```bash
export NOTIFICATION_EMAIL="your-email@gmail.com"
```

Or it will use your Gmail account (the one that downloads the files).

**Backup:** Emails are also saved to `logs/sync_notifications/` as HTML files.

## Files Changed

1. **app/services/periodic_sync.py** - Main sync service with intelligent logic
2. **app/services/sync_helpers.py** - Helper functions for database queries and email formatting
3. **app/services/gmail_notifier.py** - Gmail API email sender (NEW!)
4. **app/services/runsheet_sync_service.py** - Improved address syncing logic
5. **scripts/production/import_run_sheets.py** - Fast file discovery with `find` command
6. **scripts/production/extract_payslips.py** - Cleaner location/customer parsing, auto-sync
7. **scripts/production/download_runsheets_gmail.py** - Added gmail.send scope

## Schedule

- **18:00 daily**: Sync starts checking for runsheets
- **Every 15 minutes**: Checks for new runsheet (18:00, 18:15, 18:30, etc.)
- **Stops after processing**: Once runsheet processed and email sent, STOPS until next day
- **Midnight reset**: Tracking resets, waits for 18:00 to start again
- **Payslip window**: Tuesdays 06:00-14:00 (checks every 15 mins, stops after processing)

## Benefits

1. **Fully Automatic**: No manual intervention needed
2. **Efficient**: Only processes new files
3. **Reliable**: Error handling and logging
4. **Informative**: Detailed notifications
5. **Smart**: Knows when to check for files
6. **Fast**: Optimized file discovery and processing
7. **Complete**: Downloads → Imports → Syncs → Notifies

## Next Steps

1. Restart the app to activate the new sync system
2. Wait for the next sync window
3. Check `logs/periodic_sync.log` to see it working
4. Check `logs/sync_notifications/` for email summaries
5. (Optional) Configure SMTP for real email sending
