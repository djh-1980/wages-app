#!/usr/bin/env python3
"""
Mark runsheet jobs without pay data as DNCO (Did Not Carry Out).
Only marks jobs on dates where other jobs WERE paid, indicating the date was processed.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

db_path = Path('data/database/payslips.db')

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    exit(1)

print("="*80)
print("MARK UNPAID JOBS AS DNCO")
print("="*80)
print()

# Create backup first
backup_path = Path(f'data/database/payslips_backup_before_dnco_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
print(f"📦 Creating backup at {backup_path}...")
import shutil
shutil.copy2(db_path, backup_path)
print(f"✅ Backup created\n")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# First, get the dates that have mixed pay data (some paid, some not)
print("🔍 Finding dates with mixed pay data...")
cursor.execute("""
    SELECT DISTINCT date
    FROM run_sheet_jobs
    WHERE date IS NOT NULL AND date != ''
    AND date IN (
        SELECT date
        FROM run_sheet_jobs
        WHERE date IS NOT NULL AND date != ''
        GROUP BY date
        HAVING SUM(CASE WHEN pay_amount IS NOT NULL AND pay_amount > 0 THEN 1 ELSE 0 END) > 0
           AND SUM(CASE WHEN pay_amount IS NULL OR pay_amount = 0 THEN 1 ELSE 0 END) > 0
    )
""")

dates_with_mixed_pay = [row['date'] for row in cursor.fetchall()]
print(f"✅ Found {len(dates_with_mixed_pay)} dates with mixed pay data\n")

# Get count of jobs to be marked as DNCO
cursor.execute("""
    SELECT COUNT(*) as count
    FROM run_sheet_jobs
    WHERE date IN ({})
    AND (pay_amount IS NULL OR pay_amount = 0)
    AND (status IS NULL OR status != 'DNCO')
""".format(','.join('?' * len(dates_with_mixed_pay))), dates_with_mixed_pay)

jobs_to_mark = cursor.fetchone()['count']

print(f"📊 Jobs to mark as DNCO: {jobs_to_mark}")
print()

# Show breakdown by year
cursor.execute("""
    SELECT 
        SUBSTR(date, -4) as year,
        COUNT(*) as count
    FROM run_sheet_jobs
    WHERE date IN ({})
    AND (pay_amount IS NULL OR pay_amount = 0)
    AND (status IS NULL OR status != 'DNCO')
    GROUP BY year
    ORDER BY year DESC
""".format(','.join('?' * len(dates_with_mixed_pay))), dates_with_mixed_pay)

print("📊 Breakdown by Year:")
for row in cursor.fetchall():
    print(f"   {row['year']}: {row['count']} jobs")

print()

# Show some examples
print("📋 Example jobs to be marked as DNCO:")
cursor.execute("""
    SELECT 
        date,
        job_number,
        customer,
        activity,
        status
    FROM run_sheet_jobs
    WHERE date IN ({})
    AND (pay_amount IS NULL OR pay_amount = 0)
    AND (status IS NULL OR status != 'DNCO')
    ORDER BY date DESC
    LIMIT 10
""".format(','.join('?' * len(dates_with_mixed_pay))), dates_with_mixed_pay)

for row in cursor.fetchall():
    current_status = row['status'] or 'None'
    print(f"   {row['date']} | {row['job_number'] or 'No Job#'} | {row['customer'][:40]} | Status: {current_status}")

print()

# Ask for confirmation
response = input(f"⚠️  Mark {jobs_to_mark} jobs as DNCO? (yes/no): ")
if response.lower() not in ['yes', 'y']:
    print("❌ Cancelled by user")
    conn.close()
    exit(0)

print()
print("📝 Updating jobs to DNCO status...")

# Update the jobs
cursor.execute("""
    UPDATE run_sheet_jobs
    SET status = 'DNCO',
        notes = CASE 
            WHEN notes IS NULL OR notes = '' THEN 'Marked as DNCO - no payment on date with other paid jobs'
            ELSE notes || ' | Marked as DNCO - no payment on date with other paid jobs'
        END
    WHERE date IN ({})
    AND (pay_amount IS NULL OR pay_amount = 0)
    AND (status IS NULL OR status != 'DNCO')
""".format(','.join('?' * len(dates_with_mixed_pay))), dates_with_mixed_pay)

updated_count = cursor.rowcount
conn.commit()

print()
print("="*80)
print("✅ COMPLETED")
print("="*80)
print(f"   Updated: {updated_count} jobs")
print(f"   Status: DNCO (Did Not Carry Out)")
print(f"   Note added: 'Marked as DNCO - no payment on date with other paid jobs'")
print()

# Show final statistics
cursor.execute("""
    SELECT 
        status,
        COUNT(*) as count
    FROM run_sheet_jobs
    GROUP BY status
    ORDER BY count DESC
""")

print("📊 Final Status Breakdown:")
for row in cursor.fetchall():
    status = row['status'] or 'None'
    print(f"   {status}: {row['count']:,} jobs")

print()
print(f"💾 Backup saved at: {backup_path}")
print()

conn.close()
