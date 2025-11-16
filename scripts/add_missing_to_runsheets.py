#!/usr/bin/env python3
"""
Add missing jobs from payslips to runsheets with 'extra' status.
This script adds jobs that have dates but are missing from runsheets.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

db_path = Path('data/database/payslips.db')

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    exit(1)

print("="*80)
print("ADD MISSING JOBS TO RUNSHEETS")
print("="*80)
print()

# Create backup first
backup_dir = Path('data/database/backups')
backup_dir.mkdir(parents=True, exist_ok=True)
backup_path = backup_dir / f'payslips_backup_before_runsheet_add_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
print(f"📦 Creating backup at {backup_path}...")
import shutil
shutil.copy2(db_path, backup_path)
print(f"✅ Backup created\n")

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Get all missing jobs that have dates
print("🔍 Finding missing jobs with dates...")
cursor.execute("""
    SELECT 
        j.job_number,
        j.client,
        j.location,
        j.postcode,
        j.job_type,
        j.date,
        j.time,
        j.amount,
        j.rate,
        j.units,
        p.week_number,
        p.tax_year,
        p.pay_date
    FROM job_items j
    JOIN payslips p ON j.payslip_id = p.id
    WHERE j.job_number IS NOT NULL 
    AND j.job_number NOT IN (
        SELECT DISTINCT job_number 
        FROM run_sheet_jobs 
        WHERE job_number IS NOT NULL
    )
    AND j.date IS NOT NULL 
    AND j.date != ''
    ORDER BY p.tax_year DESC, p.week_number DESC
""")

missing_jobs = cursor.fetchall()
total_jobs = len(missing_jobs)

print(f"✅ Found {total_jobs} jobs to add\n")

if total_jobs == 0:
    print("No jobs to add. Exiting.")
    conn.close()
    exit(0)

# Show summary by year
print("📊 Summary by Tax Year:")
cursor.execute("""
    SELECT 
        p.tax_year,
        COUNT(*) as count,
        SUM(j.amount) as total_value
    FROM job_items j
    JOIN payslips p ON j.payslip_id = p.id
    WHERE j.job_number IS NOT NULL 
    AND j.job_number NOT IN (
        SELECT DISTINCT job_number 
        FROM run_sheet_jobs 
        WHERE job_number IS NOT NULL
    )
    AND j.date IS NOT NULL 
    AND j.date != ''
    GROUP BY p.tax_year
    ORDER BY p.tax_year DESC
""")

for row in cursor.fetchall():
    print(f"   {row['tax_year']}: {row['count']} jobs, £{row['total_value']:.2f}")

print()

# Ask for confirmation
response = input(f"⚠️  Add {total_jobs} jobs to runsheets with status 'extra'? (yes/no): ")
if response.lower() not in ['yes', 'y']:
    print("❌ Cancelled by user")
    conn.close()
    exit(0)

print()
print("📝 Adding jobs to runsheets...")

added_count = 0
error_count = 0

for job in missing_jobs:
    try:
        # Convert date format from DD/MM/YY to DD/MM/YYYY if needed
        job_date = job['date']
        if job_date and len(job_date.split('/')) == 3:
            parts = job_date.split('/')
            if len(parts[2]) == 2:  # YY format
                # Convert YY to YYYY (assume 20XX for years < 50, 19XX for >= 50)
                year = int(parts[2])
                full_year = f"20{parts[2]}" if year < 50 else f"19{parts[2]}"
                job_date = f"{parts[0]}/{parts[1]}/{full_year}"
        
        cursor.execute("""
            INSERT INTO run_sheet_jobs (
                date,
                driver,
                job_number,
                customer,
                activity,
                job_address,
                postcode,
                source_file,
                status,
                pay_amount,
                pay_rate,
                pay_units,
                pay_week,
                pay_year,
                pay_updated_at,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_date,
            'Hanson, Daniel',
            job['job_number'],
            job['client'] or '',
            job['job_type'] or '',
            job['location'] or '',
            job['postcode'] or '',
            'RECONSTRUCTED_FROM_PAYSLIP',
            'extra',  # Special status to identify these
            job['amount'] or 0,
            job['rate'] or 0,
            job['units'] or 0,
            job['week_number'],
            job['tax_year'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Auto-added from payslip - no original runsheet found'
        ))
        
        added_count += 1
        
        if added_count % 100 == 0:
            print(f"   Added {added_count}/{total_jobs}...")
            
    except Exception as e:
        error_count += 1
        print(f"   ⚠️  Error adding job {job['job_number']}: {str(e)}")

conn.commit()

print()
print("="*80)
print("✅ COMPLETED")
print("="*80)
print(f"   Successfully added: {added_count} jobs")
print(f"   Errors: {error_count}")
print(f"   Status: 'extra' (to identify reconstructed entries)")
print()

# Show new discrepancy count
cursor.execute("""
    SELECT COUNT(*) as remaining
    FROM job_items j
    JOIN payslips p ON j.payslip_id = p.id
    WHERE j.job_number IS NOT NULL 
    AND j.job_number NOT IN (
        SELECT DISTINCT job_number 
        FROM run_sheet_jobs 
        WHERE job_number IS NOT NULL
    )
""")

remaining = cursor.fetchone()['remaining']
print(f"📊 Remaining discrepancies: {remaining} (jobs without dates)")
print()
print(f"💾 Backup saved at: {backup_path}")
print()

conn.close()
