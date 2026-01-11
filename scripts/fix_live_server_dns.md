# Fix Live Server DNS Issue and Update Sync Files

## Problem
The server can't resolve `github.com` - DNS issue preventing git pull.

## Solution Options

### Option 1: Fix DNS (Recommended)
```bash
# Test DNS
ping github.com
nslookup github.com

# If DNS is broken, try using Google's DNS temporarily
# Edit resolv.conf (may need sudo)
sudo nano /etc/resolv.conf

# Add these lines at the top:
nameserver 8.8.8.8
nameserver 8.8.4.4

# Save and test again
ping github.com
```

### Option 2: Manual File Upload (If DNS can't be fixed quickly)

**On your LOCAL machine, create a tar of the sync files:**
```bash
cd /Users/danielhanson/CascadeProjects/Wages-App
tar -czf sync_files.tar.gz \
  scripts/sync_master.py \
  scripts/production/download_runsheets_gmail.py \
  scripts/production/import_run_sheets.py \
  scripts/production/extract_payslips.py \
  scripts/production/validate_addresses.py \
  app/utils/sync_logger.py
```

**Upload to server (using scp, SFTP, or your hosting control panel):**
```bash
scp sync_files.tar.gz tvswages@your-server:/tmp/
```

**On LIVE server, extract and copy:**
```bash
cd /var/www/tvs-wages
tar -xzf /tmp/sync_files.tar.gz
rm /tmp/sync_files.tar.gz

# Verify files
ls -lh scripts/sync_master.py
ls -lh app/utils/sync_logger.py
```

### Option 3: Use Git with IP Address
```bash
cd /var/www/tvs-wages

# Check current remote
git remote -v

# Temporarily use GitHub's IP (may change, not recommended long-term)
git remote set-url origin git@github.com:djh-1980/wages-app.git

# Or try HTTPS with IP
git remote set-url origin https://140.82.121.4/djh-1980/wages-app.git
```

### Option 4: Contact Hosting Provider
The DNS issue might be a server configuration problem. Contact your hosting provider to:
- Check DNS settings
- Verify network connectivity
- Ensure firewall isn't blocking GitHub

---

## After Files Are Updated

### 1. Verify the files
```bash
cd /var/www/tvs-wages
head -20 scripts/sync_master.py
```

Should show:
```python
#!/usr/bin/env python3
"""
Master Sync System - Complete end-to-end sync from scratch
Downloads -> Organizes -> Imports -> Validates -> Syncs -> Reports
"""
```

### 2. Test the sync
```bash
python3 scripts/sync_master.py
```

### 3. Check the log
```bash
tail -50 logs/sync.log
```

### 4. Verify cron is set up
```bash
crontab -l | grep sync_master
```

Should show:
```
0 20 * * * cd /var/www/tvs-wages && python3 scripts/sync_master.py >> logs/sync.log 2>&1
0 21 * * * cd /var/www/tvs-wages && python3 scripts/sync_master.py >> logs/sync.log 2>&1
0 9 * * 2 cd /var/www/tvs-wages && python3 scripts/sync_master.py >> logs/sync.log 2>&1
0 14 * * 2 cd /var/www/tvs-wages && python3 scripts/sync_master.py >> logs/sync.log 2>&1
```
