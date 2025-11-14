#!/usr/bin/env python3
"""Export all DNCO jobs to CSV for review."""

import sqlite3
import csv
from pathlib import Path
from datetime import datetime

db_path = Path('data/database/payslips.db')
output_path = Path(f'data/exports/csv/dnco_jobs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    exit(1)

# Ensure output directory exists
output_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("="*80)
print("EXPORT DNCO JOBS TO CSV")
print("="*80)
print()

# Get all DNCO jobs
cursor.execute("""
    SELECT 
        date,
        job_number,
        customer,
        job_address,
        postcode,
        activity,
        priority,
        source_file,
        notes
    FROM run_sheet_jobs
    WHERE status = 'DNCO'
    ORDER BY date DESC, job_number
""")

jobs = cursor.fetchall()
total_jobs = len(jobs)

print(f"📊 Found {total_jobs} DNCO jobs")
print()

# Write to CSV
with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    
    # Write header
    writer.writerow([
        'Date',
        'Job Number',
        'Customer',
        'Address',
        'Postcode',
        'Activity',
        'Priority',
        'Source File',
        'Notes'
    ])
    
    # Write data
    for job in jobs:
        writer.writerow([
            job['date'],
            job['job_number'] or '',
            job['customer'] or '',
            job['job_address'] or '',
            job['postcode'] or '',
            job['activity'] or '',
            job['priority'] or '',
            job['source_file'] or '',
            job['notes'] or ''
        ])

print(f"✅ Exported to: {output_path}")
print()

# Show summary by year
cursor.execute("""
    SELECT 
        SUBSTR(date, -4) as year,
        COUNT(*) as count
    FROM run_sheet_jobs
    WHERE status = 'DNCO'
    GROUP BY year
    ORDER BY year DESC
""")

print("📊 DNCO Jobs by Year:")
for row in cursor.fetchall():
    print(f"   {row['year']}: {row['count']} jobs")

print()

# Show summary by customer (top 10)
cursor.execute("""
    SELECT 
        customer,
        COUNT(*) as count
    FROM run_sheet_jobs
    WHERE status = 'DNCO'
    GROUP BY customer
    ORDER BY count DESC
    LIMIT 10
""")

print("📊 Top 10 Customers with DNCO Jobs:")
for row in cursor.fetchall():
    customer = row['customer'][:50] if row['customer'] else 'Unknown'
    print(f"   {customer}: {row['count']} jobs")

print()

# Show first 20 jobs
print("📋 First 20 DNCO Jobs:")
print("-" * 80)
for i, job in enumerate(jobs[:20], 1):
    print(f"{i}. {job['date']} | {job['job_number'] or 'No Job#'} | {job['customer'][:40] if job['customer'] else 'Unknown'}")

print()
print(f"💾 Full list exported to: {output_path}")
print()

conn.close()
