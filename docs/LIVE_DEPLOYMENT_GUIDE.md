# Live Server Deployment Guide - Runsheet Data Improvements

## Overview
This deployment includes three major improvements:
1. **Add 1,415 "extra" jobs** - Reconstruct missing runsheet entries from payslips
2. **Mark 1,256 DNCO jobs** - Mark unpaid jobs on paid dates as "Did Not Carry Out"
3. **Fix DNCO display** - Ensure uppercase DNCO status displays correctly

## Expected Results
- **Discrepancy report**: Drops from 1,509 to 94 missing jobs (93.8% reduction)
- **Runsheet completeness**: 1,415 jobs added with "extra" status
- **Data clarity**: 1,256 jobs marked as DNCO (not paid on dates where others were)

---

## Pre-Deployment Checklist

### 1. Backup Database
```bash
# SSH into live server
ssh your-server

# Navigate to app directory
cd /path/to/wages-app

# Create timestamped backup
cp data/database/payslips.db data/database/payslips_backup_$(date +%Y%m%d_%H%M%S).db

# Verify backup was created
ls -lh data/database/payslips_backup_*.db
```

### 2. Stop Web Application (Optional)
```bash
# If running as a service
sudo systemctl stop wages-app

# Or if running in screen/tmux, stop it manually
```

### 3. Pull Latest Code
```bash
git pull origin main

# Verify new scripts are present
ls -la scripts/add_missing_to_runsheets.py
ls -la scripts/mark_unpaid_as_dnco.py
ls -la scripts/query_job.py
```

---

## Deployment Steps

### Step 1: Add Missing Jobs to Runsheets (Extra Status)

This adds 1,415 jobs from payslips that have dates but no runsheet entries.

```bash
cd /path/to/wages-app
python3 scripts/add_missing_to_runsheets.py
```

**What it will show:**
- Found 1,415 jobs to add
- Breakdown by year (2021-2025)
- Asks for confirmation: type `yes` or `y`
- Creates automatic backup before changes
- Shows progress every 100 jobs
- Final status: 1,415 jobs added with status "extra"

**Expected output:**
```
✅ COMPLETED
   Successfully added: 1415 jobs
   Status: 'extra' (to identify reconstructed entries)
   Remaining discrepancies: 94 (jobs without dates)
```

**Verification:**
```bash
sqlite3 data/database/payslips.db "SELECT COUNT(*) FROM run_sheet_jobs WHERE status='extra';"
# Should return: 1415
```

---

### Step 2: Mark Unpaid Jobs as DNCO

This marks 1,256 jobs as DNCO (Did Not Carry Out) - jobs on dates where other jobs were paid but these weren't.

```bash
python3 scripts/mark_unpaid_as_dnco.py
```

**What it will show:**
- Found 623 dates with mixed pay data
- 1,256 jobs to mark as DNCO
- Breakdown by year
- Top 10 customers
- Example jobs
- Asks for confirmation: type `yes` or `y`
- Creates automatic backup before changes
- Final status breakdown

**Expected output:**
```
✅ COMPLETED
   Updated: 1256 jobs
   Status: DNCO (Did Not Carry Out)
```

**Verification:**
```bash
sqlite3 data/database/payslips.db "SELECT COUNT(*) FROM run_sheet_jobs WHERE status='DNCO';"
# Should return: 1256
```

---

### Step 3: Restart Web Application

```bash
# If running as a service
sudo systemctl start wages-app
sudo systemctl status wages-app

# Or start manually if needed
./start_web.sh
```

---

## Post-Deployment Verification

### 1. Check Discrepancy Report
Navigate to the Reports page in the web interface:
1. Go to **Reports** → **Discrepancy Report**
2. Verify count dropped from ~1,509 to ~94
3. Export CSV to verify remaining discrepancies are jobs without dates

### 2. Check Runsheet Status Breakdown
```bash
sqlite3 data/database/payslips.db "SELECT status, COUNT(*) as count FROM run_sheet_jobs GROUP BY status ORDER BY count DESC;"
```

**Expected output:**
```
completed|12934
extra|1412
DNCO|1256
pending|1027
missed|3
```

### 3. Verify DNCO Display
1. Navigate to **Runsheets** page
2. Find a date with DNCO jobs (e.g., 15/10/2025)
3. Verify DNCO jobs show with yellow/warning badge
4. Verify status displays as "DNCO" (uppercase)

### 4. Test Query Script (Optional)
```bash
# Edit scripts/query_job.py and set a job number
# Then run:
python3 scripts/query_job.py
```

---

## Database Changes Summary

### New Rows Added
- **1,415 rows** in `run_sheet_jobs` table (status = 'extra')

### Updated Rows
- **1,256 rows** in `run_sheet_jobs` table (status changed to 'DNCO')

### Total Impact
- **2,671 rows** affected
- **0 rows** deleted
- All changes are additions or updates (no data loss)

---

## Rollback Procedures

### If Issues Occur After Step 1 (Extra Jobs)
```bash
# Stop application
sudo systemctl stop wages-app

# Restore from backup created by script
cp data/database/payslips_backup_before_runsheet_add.db data/database/payslips.db

# Or restore from manual backup
cp data/database/payslips_backup_YYYYMMDD_HHMMSS.db data/database/payslips.db

# Restart application
sudo systemctl start wages-app
```

### If Issues Occur After Step 2 (DNCO)
```bash
# Stop application
sudo systemctl stop wages-app

# Restore from backup created by script
cp data/database/payslips_backup_before_dnco_*.db data/database/payslips.db

# Restart application
sudo systemctl start wages-app
```

### Selective Rollback (Remove Only Extra Jobs)
```bash
sqlite3 data/database/payslips.db "DELETE FROM run_sheet_jobs WHERE status='extra';"
```

### Selective Rollback (Revert DNCO to Pending)
```bash
sqlite3 data/database/payslips.db "UPDATE run_sheet_jobs SET status='pending' WHERE status='DNCO';"
```

---

## Code Changes Deployed

### Backend Changes
- `app/models/runsheet.py`: Case-insensitive status validation

### Frontend Changes
- `static/js/runsheets.js`: 
  - Uppercase DNCO badge support
  - DNCO button actions use uppercase
  - Status counting handles both cases

### New Scripts
- `scripts/add_missing_to_runsheets.py` - Add extra jobs
- `scripts/mark_unpaid_as_dnco.py` - Mark DNCO jobs
- `scripts/query_job.py` - Job lookup utility
- `scripts/export_dnco_jobs.py` - Export DNCO jobs to CSV
- `scripts/analyze_missing_pay_data.py` - Analyze pay data gaps

---

## Troubleshooting

### Issue: Script says "Database not found"
**Solution:** Check you're in the correct directory and database path is correct
```bash
pwd  # Should show /path/to/wages-app
ls -la data/database/payslips.db
```

### Issue: DNCO still shows as "Pending" in UI
**Solution:** 
1. Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
2. Verify database has uppercase DNCO: `sqlite3 data/database/payslips.db "SELECT DISTINCT status FROM run_sheet_jobs;"`
3. Restart web application

### Issue: Discrepancy count didn't change
**Solution:**
1. Verify scripts ran successfully (check for "✅ COMPLETED" message)
2. Check database counts with verification queries above
3. Clear browser cache and refresh

### Issue: Permission denied on scripts
**Solution:**
```bash
chmod +x scripts/*.py
```

---

## Performance Notes

- **Step 1 (Extra Jobs)**: ~2-3 minutes for 1,415 jobs
- **Step 2 (DNCO)**: ~1-2 minutes for 1,256 jobs
- **Total Downtime**: 5-10 minutes (if you stop the service)
- **Database Size Increase**: ~500KB-1MB

---

## Support & Verification

### Query Individual Jobs
```bash
# Edit job number in script
nano scripts/query_job.py
# Change: job_number = '4269797'

# Run query
python3 scripts/query_job.py
```

### Export DNCO Jobs for Review
```bash
python3 scripts/export_dnco_jobs.py
# Creates: data/exports/csv/dnco_jobs_TIMESTAMP.csv
```

### Check Specific Date
```bash
sqlite3 data/database/payslips.db "SELECT job_number, customer, status, pay_amount FROM run_sheet_jobs WHERE date='15/10/2025' ORDER BY status;"
```

---

## Success Criteria

✅ **Deployment is successful if:**
1. Discrepancy report shows ~94 missing jobs (down from 1,509)
2. 1,415 jobs have status "extra"
3. 1,256 jobs have status "DNCO"
4. DNCO status displays correctly in web UI
5. No errors in application logs
6. All runsheet pages load correctly

---

## Estimated Timeline

| Step | Duration | Can Skip? |
|------|----------|-----------|
| Backup | 1 min | No |
| Pull code | 1 min | No |
| Stop service | 30 sec | Optional |
| Run Step 1 | 2-3 min | No |
| Run Step 2 | 1-2 min | No |
| Start service | 30 sec | No |
| Verification | 2-3 min | No |
| **Total** | **8-12 min** | |

---

## Notes

- ✅ All scripts create automatic backups before making changes
- ✅ Changes are atomic (all or nothing per script)
- ✅ No data is deleted, only added or updated
- ✅ Scripts can be re-run safely (they check for existing data)
- ⚠️ The 94 remaining discrepancies are jobs without dates (cannot be added to runsheets)

---

## Contact

If you encounter any issues during deployment, check:
1. Application logs: `tail -f logs/app.log`
2. Database integrity: `sqlite3 data/database/payslips.db "PRAGMA integrity_check;"`
3. Backup files exist: `ls -lh data/database/payslips_backup_*`
