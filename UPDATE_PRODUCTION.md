# Update Production Server to v1.0

## Pre-Update Checklist

Before updating wages.daniel-hanson.co.uk, complete these steps:

### 1. Backup Current Production
```bash
# SSH into your server
ssh root@wages.daniel-hanson.co.uk

# Backup the database
sudo -u wagesapp cp /home/wagesapp/wages-app/payslips.db /home/wagesapp/payslips.db.backup-$(date +%Y%m%d)

# Backup the entire app directory
sudo tar -czf /home/wagesapp/wages-app-backup-$(date +%Y%m%d).tar.gz /home/wagesapp/wages-app/

# Download backup to your Mac (from your Mac terminal)
scp root@wages.daniel-hanson.co.uk:/home/wagesapp/payslips.db.backup-$(date +%Y%m%d) ~/Desktop/
```

### 2. Check Current Version
```bash
# On server
cd /home/wagesapp/wages-app
git status
git log --oneline -5
```

## Update Process

### Step 1: Stop the Application
```bash
# On server
sudo supervisorctl stop wagesapp
```

### Step 2: Pull Latest Code
```bash
# On server
cd /home/wagesapp/wages-app
sudo -u wagesapp git fetch --all
sudo -u wagesapp git pull origin main
sudo -u wagesapp git checkout v1.0
```

### Step 3: Handle New Directory Structure

The v1.0 update reorganized files. You need to migrate the database and create new directories:

```bash
# On server, as wagesapp user
cd /home/wagesapp/wages-app

# Create new directories
sudo -u wagesapp mkdir -p data output

# Move database to new location (if it exists in old location)
if [ -f payslips.db ]; then
    sudo -u wagesapp mv payslips.db data/payslips.db
fi

# Move any existing CSV/reports to output
sudo -u wagesapp mv *.csv output/ 2>/dev/null || true
sudo -u wagesapp mv *.txt output/ 2>/dev/null || true

# Create .gitkeep files
sudo -u wagesapp touch data/.gitkeep output/.gitkeep

# Verify permissions
sudo chown -R wagesapp:wagesapp /home/wagesapp/wages-app
```

### Step 4: Update Dependencies (if needed)
```bash
# On server
cd /home/wagesapp/wages-app
sudo -u wagesapp pip3 install -r requirements.txt --upgrade
```

### Step 5: Verify Configuration

Check that paths are correct in your supervisor config:

```bash
sudo nano /etc/supervisor/conf.d/wagesapp.conf
```

Should look like:
```ini
[program:wagesapp]
directory=/home/wagesapp/wages-app
command=/usr/bin/python3 web_app.py
user=wagesapp
autostart=true
autorestart=true
stderr_logfile=/var/log/wagesapp.err.log
stdout_logfile=/var/log/wagesapp.out.log
environment=HOME="/home/wagesapp",USER="wagesapp"
```

### Step 6: Restart Application
```bash
# Reload supervisor config
sudo supervisorctl reread
sudo supervisorctl update

# Start the application
sudo supervisorctl start wagesapp

# Check status
sudo supervisorctl status wagesapp
```

### Step 7: Verify It's Working
```bash
# Check logs
tail -f /var/log/wagesapp.out.log

# Test the application
curl http://localhost:5001
```

### Step 8: Test in Browser
Visit: https://wages.daniel-hanson.co.uk

Check:
- ✓ Dashboard loads
- ✓ Data displays correctly
- ✓ All charts render
- ✓ Database queries work
- ✓ No console errors

## Rollback Plan (If Something Goes Wrong)

```bash
# Stop the app
sudo supervisorctl stop wagesapp

# Restore previous version
cd /home/wagesapp/wages-app
sudo -u wagesapp git checkout main
sudo -u wagesapp git reset --hard HEAD~2

# Restore database if needed
sudo -u wagesapp cp /home/wagesapp/payslips.db.backup-YYYYMMDD data/payslips.db

# Restart
sudo supervisorctl start wagesapp
```

## Post-Update Verification

### Check Version
```bash
cd /home/wagesapp/wages-app
cat VERSION
# Should show: 1.0

git describe --tags
# Should show: v1.0
```

### Verify New Structure
```bash
ls -la /home/wagesapp/wages-app/
# Should see: data/, output/, scripts/, docs/, templates/, static/
```

### Test Database Access
```bash
sudo -u wagesapp python3 scripts/quick_stats.py
```

## What's New in v1.0

- ✅ Reorganized file structure (scripts/, docs/, data/, output/)
- ✅ Fixed 5 code bugs (imports, error handling, validation)
- ✅ Improved error messages
- ✅ Better job description parsing
- ✅ Professional directory layout
- ✅ Updated documentation

## Monitoring After Update

```bash
# Watch logs for any errors
tail -f /var/log/wagesapp.out.log /var/log/wagesapp.err.log

# Check supervisor status
sudo supervisorctl status

# Monitor nginx
sudo tail -f /var/log/nginx/access.log
```

## Troubleshooting

### If app won't start:
```bash
# Check logs
sudo supervisorctl tail -f wagesapp stderr

# Check permissions
ls -la /home/wagesapp/wages-app/data/
sudo chown -R wagesapp:wagesapp /home/wagesapp/wages-app/

# Verify Python can find modules
sudo -u wagesapp python3 -c "import flask; print('Flask OK')"
```

### If database not found:
```bash
# Check database location
ls -la /home/wagesapp/wages-app/data/payslips.db

# If in wrong location, move it
sudo -u wagesapp mv /home/wagesapp/wages-app/payslips.db /home/wagesapp/wages-app/data/
```

### If getting 502 errors:
```bash
# Restart everything
sudo supervisorctl restart wagesapp
sudo systemctl restart nginx
```

## Success Indicators

✅ `supervisorctl status wagesapp` shows "RUNNING"
✅ Website loads at wages.daniel-hanson.co.uk
✅ Dashboard displays data correctly
✅ No errors in logs
✅ `cat VERSION` shows "1.0"

---

**Estimated Update Time:** 10-15 minutes
**Downtime:** ~2-3 minutes

Good luck with the update! 🚀
