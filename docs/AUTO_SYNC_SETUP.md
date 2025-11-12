# Automatic Daily Run Sheet Sync Setup

Automatically download, organize, and import run sheets every day at 8:00 PM.

## 🚀 Quick Setup

### One-Command Setup (macOS & Linux)

```bash
bash scripts/setup_auto_sync_universal.sh
```

This will:
- ✅ Detect your OS (macOS or Debian/Linux)
- ✅ Create the appropriate scheduler (launchd or systemd)
- ✅ Set it to run daily at 8:00 PM
- ✅ Create log files for monitoring

## 📋 What It Does

The automated sync runs daily and:

1. **Downloads** run sheets from Gmail (yesterday's date)
2. **Organizes** PDFs into `data/runsheets/YYYY/MM/` folders
3. **Imports** all jobs to the database
4. **Creates notification** for the web app
5. **Logs** everything to `logs/runsheet_sync.log`

## 🖥️ Platform-Specific Details

### macOS (Development)

Uses **launchd** (Apple's task scheduler):

```bash
# Setup
bash scripts/setup_auto_sync_universal.sh

# Check if running
launchctl list | grep wages-app

# View logs
tail -f logs/runsheet_sync.log

# Test manually
python3 scripts/daily_runsheet_sync.py

# Disable
launchctl unload ~/Library/LaunchAgents/com.wages-app.runsheet-sync.plist
```

**Configuration file:**
`~/Library/LaunchAgents/com.wages-app.runsheet-sync.plist`

### Debian/Ubuntu Linux (Production)

Uses **systemd** (Linux task scheduler):

```bash
# Setup (requires sudo)
bash scripts/setup_auto_sync_universal.sh

# Check status
sudo systemctl status wages-app-runsheet-sync.timer

# View logs
tail -f logs/runsheet_sync.log

# Test manually
sudo systemctl start wages-app-runsheet-sync.service

# Disable
sudo systemctl disable wages-app-runsheet-sync.timer
sudo systemctl stop wages-app-runsheet-sync.timer
```

**Configuration files:**
- `/etc/systemd/system/wages-app-runsheet-sync.service`
- `/etc/systemd/system/wages-app-runsheet-sync.timer`

## ⏰ Schedule

**Default:** Every day at **8:00 PM** (20:00)

### Change the Time

#### macOS:
Edit `~/Library/LaunchAgents/com.wages-app.runsheet-sync.plist`:

```xml
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key>
    <integer>20</integer>  <!-- Change this -->
    <key>Minute</key>
    <integer>0</integer>   <!-- Change this -->
</dict>
```

Then reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.wages-app.runsheet-sync.plist
launchctl load ~/Library/LaunchAgents/com.wages-app.runsheet-sync.plist
```

#### Linux:
Edit `/etc/systemd/system/wages-app-runsheet-sync.timer`:

```ini
[Timer]
OnCalendar=*-*-* 20:00:00  # Change this (HH:MM:SS)
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart wages-app-runsheet-sync.timer
```

## 📊 Monitoring

### View Logs

```bash
# Live tail
tail -f logs/runsheet_sync.log

# Last 50 lines
tail -50 logs/runsheet_sync.log

# Errors only
tail -f logs/runsheet_sync_error.log
```

### Check Last Run

```bash
# macOS
ls -lh logs/runsheet_sync.log

# Linux
sudo systemctl status wages-app-runsheet-sync.service
```

## 🔔 Web Notifications

When new run sheets are downloaded, a notification appears in the web app:

- **Location:** Top right of the navigation bar
- **Shows:** Number of new run sheets
- **Auto-clears:** When you view the run sheets page

## 🧪 Testing

Test the sync manually without waiting for the scheduled time:

```bash
# Run directly
python3 scripts/daily_runsheet_sync.py

# Or trigger via scheduler
# macOS:
launchctl start com.wages-app.runsheet-sync

# Linux:
sudo systemctl start wages-app-runsheet-sync.service
```

## 🛠️ Troubleshooting

### "No emails found"

- Check your Gmail credentials are set up (`credentials.json` and `token.json`)
- Run the manual download first: `python3 scripts/download_runsheets_gmail.py`
- Check the search date in logs

### "Permission denied" (Linux)

- Make sure you ran setup with sudo
- Check file permissions: `ls -l scripts/daily_runsheet_sync.py`

### Sync not running

**macOS:**
```bash
# Check if loaded
launchctl list | grep wages-app

# Reload
launchctl unload ~/Library/LaunchAgents/com.wages-app.runsheet-sync.plist
launchctl load ~/Library/LaunchAgents/com.wages-app.runsheet-sync.plist
```

**Linux:**
```bash
# Check timer status
sudo systemctl status wages-app-runsheet-sync.timer

# Restart timer
sudo systemctl restart wages-app-runsheet-sync.timer
```

### Check logs for errors

```bash
# Standard output
cat logs/runsheet_sync.log

# Errors
cat logs/runsheet_sync_error.log
```

## 🔧 Manual Control

### Disable Auto-Sync

**macOS:**
```bash
launchctl unload ~/Library/LaunchAgents/com.wages-app.runsheet-sync.plist
```

**Linux:**
```bash
sudo systemctl disable wages-app-runsheet-sync.timer
sudo systemctl stop wages-app-runsheet-sync.timer
```

### Re-enable Auto-Sync

**macOS:**
```bash
launchctl load ~/Library/LaunchAgents/com.wages-app.runsheet-sync.plist
```

**Linux:**
```bash
sudo systemctl enable wages-app-runsheet-sync.timer
sudo systemctl start wages-app-runsheet-sync.timer
```

## 📝 Notes

- **Gmail OAuth:** Make sure `credentials.json` and `token.json` exist
- **Logs:** Automatically created in `logs/` directory
- **Notifications:** Stored in `data/new_runsheets.json`
- **Downloads:** Only fetches yesterday's run sheets (sent evening before)
- **Duplicates:** Automatically skipped
- **Database:** Jobs imported automatically

## 🔗 Related Documentation

- [Gmail Setup Guide](GMAIL_SETUP.md)
- [Run Sheet Import](../scripts/import_run_sheets.py)
- [Manual Download](../scripts/download_runsheets_gmail.py)
