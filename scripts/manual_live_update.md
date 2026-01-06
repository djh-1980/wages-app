# Manual Live Server Update Commands

## Step 1: Connect to your live server
Use your normal method to SSH into the server (e.g., via terminal, cPanel, or hosting control panel)

## Step 2: Navigate to the app directory
```bash
cd /var/www/tvs-wages
```

## Step 3: Check current status
```bash
# See current commit
git log --oneline -1

# Check for uncommitted changes
git status
```

## Step 4: Pull latest changes
```bash
# Pull from main branch
git pull origin main

# Or if you need to force it:
git fetch origin
git reset --hard origin/main
```

## Step 5: Verify sync files are updated
```bash
# Check sync_master.py exists and is recent
ls -lh scripts/sync_master.py

# Check sync_logger.py exists
ls -lh app/utils/sync_logger.py

# View first few lines to confirm it's the right version
head -20 scripts/sync_master.py
```

## Step 6: Check cron schedule
```bash
crontab -l | grep sync
```

## Step 7: Test the sync manually
```bash
cd /var/www/tvs-wages
python3 scripts/sync_master.py
```

## Step 8: Check the sync log
```bash
tail -50 logs/sync.log
```

---

## Expected Results:

**Local commit:** `d05a3c8` - "Fix extra jobs report discrepancy display and null value handling"

**sync_master.py should start with:**
```python
#!/usr/bin/env python3
"""
Master Sync System - Complete end-to-end sync from scratch
Downloads -> Organizes -> Imports -> Validates -> Syncs -> Reports
"""
```

**Cron should show:**
```
0 20 * * * cd /var/www/tvs-wages && python3 scripts/sync_master.py >> logs/sync.log 2>&1
0 21 * * * cd /var/www/tvs-wages && python3 scripts/sync_master.py >> logs/sync.log 2>&1
0 9 * * 2 cd /var/www/tvs-wages && python3 scripts/sync_master.py >> logs/sync.log 2>&1
0 14 * * 2 cd /var/www/tvs-wages && python3 scripts/sync_master.py >> logs/sync.log 2>&1
```
