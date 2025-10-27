# Live Server Setup Guide

## Gmail API Setup on Live Server (192.168.1.202)

### 1. Copy credentials.json to live server
```bash
# From your local machine, copy the credentials file
scp credentials.json wagesapp@192.168.1.202:~/wages-app/
```

### 2. Authorize Gmail on live server
```bash
# SSH into live server
ssh wagesapp@192.168.1.202

# Go to wages-app directory
cd wages-app

# Run the Gmail authorization script (this will open a browser)
python3 scripts/download_gmail_attachments.py

# Follow the browser prompts to authorize
# This will create token.json file
```

**Note**: If the server doesn't have a GUI/browser, you can:
1. Authorize on your local machine first
2. Copy both `credentials.json` AND `token.json` to the server:
```bash
scp credentials.json token.json wagesapp@192.168.1.202:~/wages-app/
```

### 3. Test Gmail download
```bash
# On the live server, test the download
cd ~/wages-app
python3 scripts/download_gmail_attachments.py --after-date 2025/10/27
```

---

## Auto-Sync Setup (Cron Job)

### Option 1: Daily Auto Download & Sync (Recommended)
Run every day at 6 AM to download and import yesterday's run sheet:

```bash
# Edit crontab
crontab -e

# Add this line (downloads and syncs at 6 AM daily):
0 6 * * * cd /home/wagesapp/wages-app && /usr/bin/python3 scripts/auto_sync.py >> logs/auto_sync.log 2>&1
```

### Option 2: Multiple times per day
Download new run sheets every 4 hours:

```bash
# Add this to crontab:
0 */4 * * * cd /home/wagesapp/wages-app && /usr/bin/python3 scripts/auto_sync.py >> logs/auto_sync.log 2>&1
```

---

## Create Auto-Sync Script

Create `scripts/auto_sync.py`:

```python
#!/usr/bin/env python3
"""
Auto-sync script for downloading and importing run sheets.
Runs via cron job.
"""

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

def log(message):
    """Log with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def main():
    log("=== Starting auto-sync ===")
    
    # Get yesterday's date (run sheets usually arrive next day)
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y/%m/%d')
    
    log(f"Downloading run sheets from {date_str}...")
    
    try:
        # Step 1: Download from Gmail
        result = subprocess.run(
            [sys.executable, 'scripts/download_gmail_attachments.py', 
             '--after-date', date_str, '--type', 'runsheets'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            log(f"Download complete: {result.stdout.strip()}")
        else:
            log(f"Download failed: {result.stderr}")
            return 1
        
        # Step 2: Import run sheets
        log("Importing run sheets to database...")
        result = subprocess.run(
            [sys.executable, 'scripts/import_run_sheets.py'],
            capture_output=True,
            text=True,
            timeout=1800
        )
        
        if result.returncode == 0:
            log(f"Import complete: {result.stdout.strip()}")
        else:
            log(f"Import failed: {result.stderr}")
            return 1
        
        log("=== Auto-sync completed successfully ===")
        return 0
        
    except Exception as e:
        log(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## Verify Setup

### 1. Check Gmail is working:
```bash
ssh wagesapp@192.168.1.202
cd wages-app
python3 -c "from pathlib import Path; print('credentials.json:', Path('credentials.json').exists()); print('token.json:', Path('token.json').exists())"
```

### 2. Test auto-sync manually:
```bash
cd ~/wages-app
python3 scripts/auto_sync.py
```

### 3. Check cron is running:
```bash
crontab -l
```

### 4. View auto-sync logs:
```bash
tail -f ~/wages-app/logs/auto_sync.log
```

---

## Web Interface Access

Once setup is complete, you can also use the web interface:

1. Go to: http://192.168.1.202:5001/settings
2. Click **Gmail** tab to verify connection
3. Click **Data** tab
4. Click **"Download & Sync Run Sheets"** to manually trigger

---

## Troubleshooting

### Gmail authorization fails:
- Make sure credentials.json is in the wages-app directory
- Try authorizing on local machine and copying token.json

### Cron job not running:
```bash
# Check cron service
sudo systemctl status cron

# Check cron logs
grep CRON /var/log/syslog
```

### Auto-sync fails:
```bash
# Check logs
tail -50 ~/wages-app/logs/auto_sync.log

# Run manually to see errors
cd ~/wages-app
python3 scripts/auto_sync.py
```
