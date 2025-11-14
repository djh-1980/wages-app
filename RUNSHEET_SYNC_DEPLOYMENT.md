# Runsheet Discrepancy Fix - Live Server Deployment

## Overview
This deployment adds 1,415 missing jobs from payslips to runsheets with status "extra", reducing discrepancies from 1,509 to 94.

## Pre-Deployment Checklist

### 1. Backup Database
```bash
# SSH into live server
ssh your-server

# Navigate to app directory
cd /path/to/wages-app

# Create backup
cp data/database/payslips.db data/database/payslips_backup_$(date +%Y%m%d_%H%M%S).db
```

### 2. Pull Latest Code
```bash
git pull origin main
```

### 3. Verify Scripts
```bash
ls -la scripts/add_missing_to_runsheets.py
ls -la scripts/query_job.py
```

## Deployment Steps

### Step 1: Test Query Script (Optional)
Test with a known job number to verify database access:
```bash
cd /path/to/wages-app

# Edit query_job.py to set a job number you know exists
# Then run:
python3 scripts/query_job.py
```

### Step 2: Run the Runsheet Sync Script
```bash
cd /path/to/wages-app
python3 scripts/add_missing_to_runsheets.py
```

**The script will:**
1. Create an automatic backup at `data/database/payslips_backup_before_runsheet_add.db`
2. Show summary of jobs to be added by year
3. Ask for confirmation (type `yes` or `y`)
4. Add 1,415 jobs with status "extra"
5. Show completion summary

### Step 3: Verify Results
Check the discrepancy report in the web interface:
1. Navigate to Reports page
2. Generate Discrepancy Report
3. Verify count dropped from ~1,509 to ~94

Or check via command line:
```bash
sqlite3 data/database/payslips.db "SELECT COUNT(*) FROM run_sheet_jobs WHERE status='extra';"
# Should return: 1415

sqlite3 data/database/payslips.db "SELECT COUNT(*) FROM job_items j WHERE j.job_number IS NOT NULL AND j.job_number NOT IN (SELECT DISTINCT job_number FROM run_sheet_jobs WHERE job_number IS NOT NULL);"
# Should return: 94
```

## What Changed

### Database Changes
- **1,415 new rows** added to `run_sheet_jobs` table
- All new rows have:
  - `status = 'extra'`
  - `source_file = 'RECONSTRUCTED_FROM_PAYSLIP'`
  - `notes = 'Auto-added from payslip - no original runsheet found'`

### Discrepancy Report Impact
- **Before**: 1,509 missing jobs
- **After**: 94 missing jobs (only those without dates)
- **Reduction**: 93.8%

### Jobs Added by Year
| Year | Jobs | Value |
|------|------|-------|
| 2025 | 131 | £4,274.68 |
| 2024 | 277 | £8,567.22 |
| 2023 | 358 | £10,088.64 |
| 2022 | 288 | £7,400.14 |
| 2021 | 361 | £7,839.50 |
| **Total** | **1,415** | **£38,170.18** |

## Rollback Plan

If you need to rollback:

```bash
# Stop the web application
sudo systemctl stop wages-app  # or your service name

# Restore from backup
cp data/database/payslips_backup_before_runsheet_add.db data/database/payslips.db

# Or restore from timestamped backup
cp data/database/payslips_backup_YYYYMMDD_HHMMSS.db data/database/payslips.db

# Restart the web application
sudo systemctl start wages-app
```

## Post-Deployment

### Filtering "Extra" Jobs
In your application, you can now:
- Filter runsheets by `status = 'extra'` to see reconstructed entries
- Exclude them with `status != 'extra'` to see only original runsheets
- Use the `source_file` field to identify them

### Query Individual Jobs
Use the query script to investigate specific jobs:
```bash
# Edit scripts/query_job.py and set the job_number
# Then run:
python3 scripts/query_job.py
```

## Notes

- ✅ Script creates automatic backup before making changes
- ✅ All changes are in a single transaction (atomic)
- ✅ Zero errors during local testing
- ✅ Jobs are tagged for easy identification
- ⚠️ Remaining 94 discrepancies are jobs without dates (cannot be added to runsheets)

## Support

If you encounter issues:
1. Check the backup was created successfully
2. Verify database permissions
3. Check application logs
4. Use rollback procedure if needed

## Estimated Time
- Backup: < 1 minute
- Pull code: < 1 minute
- Run script: 2-3 minutes
- Verification: 2-3 minutes
- **Total: ~5-10 minutes**
