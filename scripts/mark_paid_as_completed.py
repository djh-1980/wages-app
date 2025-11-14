#!/usr/bin/env python3
"""
Mark pending jobs as completed on days where they have pay data.
This assumes if a job has pay data, it was completed and paid.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

db_path = Path('data/database/payslips.db')

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    exit(1)

print("="*80)
print("MARK PAID PENDING JOBS AS COMPLETED")
print("="*80)
print()

# Create backup first
backup_path = Path(f'data/database/payslips_backup_before_completed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
print(f"📦 Creating backup at {backup_path}...")
import shutil
shutil.copy2(db_path, backup_path)
print(f"✅ Backup created\n")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Find all pending jobs that have pay data
print("🔍 Finding pending jobs with pay data...")
cursor.execute("""
    SELECT COUNT(*) as count
    FROM run_sheet_jobs
    WHERE status = 'pending'
    AND pay_amount IS NOT NULL 
    AND pay_amount > 0
""")

jobs_to_mark = cursor.fetchone()['count']

print(f"📊 Pending jobs with pay data: {jobs_to_mark}")
print()

if jobs_to_mark == 0:
    print("No pending jobs with pay data found. Exiting.")
    conn.close()
    exit(0)

# Show breakdown by year
cursor.execute("""
    SELECT 
        SUBSTR(date, -4) as year,
        COUNT(*) as count,
        SUM(pay_amount) as total_value
    FROM run_sheet_jobs
    WHERE status = 'pending'
    AND pay_amount IS NOT NULL 
    AND pay_amount > 0
    GROUP BY year
    ORDER BY year DESC
""")

print("📊 Breakdown by Year:")
for row in cursor.fetchall():
    print(f"   {row['year']}: {row['count']} jobs, £{row['total_value']:.2f}")

print()

# Show breakdown by customer (top 10)
cursor.execute("""
    SELECT 
        customer,
        COUNT(*) as count,
        SUM(pay_amount) as total_value
    FROM run_sheet_jobs
    WHERE status = 'pending'
    AND pay_amount IS NOT NULL 
    AND pay_amount > 0
    GROUP BY customer
    ORDER BY count DESC
    LIMIT 10
""")

print("📊 Top 10 Customers:")
for row in cursor.fetchall():
    customer = row['customer'][:50] if row['customer'] else 'Unknown'
    print(f"   {customer}: {row['count']} jobs, £{row['total_value']:.2f}")

print()

# Show some examples
print("📋 Example jobs to be marked as completed:")
cursor.execute("""
    SELECT 
        date,
        job_number,
        customer,
        activity,
        pay_amount
    FROM run_sheet_jobs
    WHERE status = 'pending'
    AND pay_amount IS NOT NULL 
    AND pay_amount > 0
    ORDER BY date DESC
    LIMIT 10
""")

for row in cursor.fetchall():
    print(f"   {row['date']} | {row['job_number'] or 'No Job#'} | {row['customer'][:40] if row['customer'] else 'Unknown'} | £{row['pay_amount']:.2f}")

print()

# Ask for confirmation
response = input(f"⚠️  Mark {jobs_to_mark} pending jobs as completed? (yes/no): ")
if response.lower() not in ['yes', 'y']:
    print("❌ Cancelled by user")
    conn.close()
    exit(0)

print()
print("📝 Updating jobs to completed status...")

# Update the jobs
cursor.execute("""
    UPDATE run_sheet_jobs
    SET status = 'completed',
        notes = CASE 
            WHEN notes IS NULL OR notes = '' THEN 'Auto-marked as completed - has pay data'
            ELSE notes || ' | Auto-marked as completed - has pay data'
        END
    WHERE status = 'pending'
    AND pay_amount IS NOT NULL 
    AND pay_amount > 0
""")

updated_count = cursor.rowcount
conn.commit()

print()
print("="*80)
print("✅ COMPLETED")
print("="*80)
print(f"   Updated: {updated_count} jobs")
print(f"   Status changed: pending → completed")
print(f"   Note added: 'Auto-marked as completed - has pay data'")
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

# Show pending jobs remaining (should be those without pay data)
cursor.execute("""
    SELECT COUNT(*) as count
    FROM run_sheet_jobs
    WHERE status = 'pending'
    AND (pay_amount IS NULL OR pay_amount = 0)
""")

remaining_pending = cursor.fetchone()['count']
print(f"📊 Remaining pending jobs (no pay data): {remaining_pending:,}")
print()
print(f"💾 Backup saved at: {backup_path}")
print()

conn.close()
