# Update Live Server Sync Files - Simple Method

## Step 1: Fix DNS Permanently (Run on live server)

```bash
# Add DNS servers
echo -e "nameserver 8.8.8.8\nnameserver 8.8.4.4" | sudo tee /etc/resolv.conf

# Make it immutable so it won't be overwritten
sudo chattr +i /etc/resolv.conf

# Test it works
ping -c 2 github.com
```

## Step 2: Pull Updates from Git

Once DNS is fixed:
```bash
cd /var/www/tvs-wages
git pull origin main
```

---

## Alternative: Manual File Upload (If DNS fix doesn't work)

Upload these 6 files from your local machine to live server using your hosting control panel or SFTP:

### Files to Upload:

**Local Path → Live Server Path**

1. `/Users/danielhanson/CascadeProjects/Wages-App/scripts/sync_master.py`
   → `/var/www/tvs-wages/scripts/sync_master.py`

2. `/Users/danielhanson/CascadeProjects/Wages-App/app/utils/sync_logger.py`
   → `/var/www/tvs-wages/app/utils/sync_logger.py`

3. `/Users/danielhanson/CascadeProjects/Wages-App/scripts/production/download_runsheets_gmail.py`
   → `/var/www/tvs-wages/scripts/production/download_runsheets_gmail.py`

4. `/Users/danielhanson/CascadeProjects/Wages-App/scripts/production/import_run_sheets.py`
   → `/var/www/tvs-wages/scripts/production/import_run_sheets.py`

5. `/Users/danielhanson/CascadeProjects/Wages-App/scripts/production/extract_payslips.py`
   → `/var/www/tvs-wages/scripts/production/extract_payslips.py`

6. `/Users/danielhanson/CascadeProjects/Wages-App/scripts/production/validate_addresses.py`
   → `/var/www/tvs-wages/scripts/production/validate_addresses.py`

---

## Step 3: Test Sync (Run on live server)

```bash
cd /var/www/tvs-wages
python3 scripts/sync_master.py
```

## Step 4: Check Log

```bash
tail -50 /var/www/tvs-wages/logs/sync.log
```

## Step 5: Verify Cron

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
