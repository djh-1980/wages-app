#!/usr/bin/env python3
"""
Analyze runsheets to find jobs missing pay data on days where other jobs have pay data.
This helps identify jobs that should have been paid but weren't linked to payslips.
"""

import sqlite3
from pathlib import Path
from collections import defaultdict

db_path = Path('data/database/payslips.db')

if not db_path.exists():
    print(f"❌ Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("="*80)
print("RUNSHEET PAY DATA ANALYSIS")
print("="*80)
print()

# Get all runsheet jobs grouped by date
print("🔍 Analyzing runsheet jobs by date...")
cursor.execute("""
    SELECT 
        date,
        COUNT(*) as total_jobs,
        SUM(CASE WHEN pay_amount IS NOT NULL AND pay_amount > 0 THEN 1 ELSE 0 END) as jobs_with_pay,
        SUM(CASE WHEN pay_amount IS NULL OR pay_amount = 0 THEN 1 ELSE 0 END) as jobs_without_pay,
        SUM(CASE WHEN status = 'extra' THEN 1 ELSE 0 END) as extra_jobs
    FROM run_sheet_jobs
    WHERE date IS NOT NULL AND date != ''
    GROUP BY date
    HAVING jobs_with_pay > 0 AND jobs_without_pay > 0
    ORDER BY date DESC
""")

dates_with_mixed_pay = cursor.fetchall()

print(f"✅ Found {len(dates_with_mixed_pay)} dates with mixed pay data\n")

if len(dates_with_mixed_pay) == 0:
    print("No dates found where some jobs have pay data and others don't.")
    conn.close()
    exit(0)

# Summary statistics
total_jobs_without_pay = 0
total_jobs_with_pay = 0
dates_by_year = defaultdict(list)

print("📊 SUMMARY BY DATE")
print("-" * 80)
print(f"{'Date':<15} {'Total Jobs':<12} {'With Pay':<12} {'Without Pay':<15} {'Extra':<10}")
print("-" * 80)

for row in dates_with_mixed_pay:
    date_str = row['date']
    total = row['total_jobs']
    with_pay = row['jobs_with_pay']
    without_pay = row['jobs_without_pay']
    extra = row['extra_jobs']
    
    print(f"{date_str:<15} {total:<12} {with_pay:<12} {without_pay:<15} {extra:<10}")
    
    total_jobs_without_pay += without_pay
    total_jobs_with_pay += with_pay
    
    # Group by year for summary
    if '/' in date_str:
        parts = date_str.split('/')
        if len(parts) == 3:
            year = parts[2]
            dates_by_year[year].append(row)

print("-" * 80)
print(f"{'TOTAL':<15} {'':<12} {total_jobs_with_pay:<12} {total_jobs_without_pay:<15}")
print()

# Summary by year
print("📊 SUMMARY BY YEAR")
print("-" * 80)
print(f"{'Year':<10} {'Dates':<10} {'Jobs Without Pay':<20}")
print("-" * 80)

for year in sorted(dates_by_year.keys(), reverse=True):
    dates = dates_by_year[year]
    jobs_without = sum(d['jobs_without_pay'] for d in dates)
    print(f"{year:<10} {len(dates):<10} {jobs_without:<20}")

print()

# Get details of jobs without pay data on these dates
print("🔍 DETAILED BREAKDOWN")
print("-" * 80)

# Ask if user wants to see detailed breakdown
response = input("Show detailed job list for dates with missing pay data? (yes/no): ")
if response.lower() in ['yes', 'y']:
    print()
    
    for row in dates_with_mixed_pay[:20]:  # Limit to first 20 dates
        date_str = row['date']
        
        print(f"\n📅 Date: {date_str}")
        print(f"   Total Jobs: {row['total_jobs']}, With Pay: {row['jobs_with_pay']}, Without Pay: {row['jobs_without_pay']}")
        
        # Get jobs without pay for this date
        cursor.execute("""
            SELECT 
                job_number,
                customer,
                job_address,
                postcode,
                activity,
                status,
                source_file
            FROM run_sheet_jobs
            WHERE date = ?
            AND (pay_amount IS NULL OR pay_amount = 0)
            ORDER BY job_number
        """, (date_str,))
        
        jobs = cursor.fetchall()
        
        print(f"\n   Jobs without pay data:")
        for job in jobs[:10]:  # Limit to first 10 jobs per date
            status_marker = "🔄" if job['status'] == 'extra' else "📋"
            print(f"   {status_marker} {job['job_number']} - {job['customer'][:40]} - {job['activity']}")
        
        if len(jobs) > 10:
            print(f"   ... and {len(jobs) - 10} more jobs")

print()
print("="*80)
print("ANALYSIS COMPLETE")
print("="*80)
print()

# Overall statistics
cursor.execute("""
    SELECT 
        COUNT(*) as total_runsheet_jobs,
        SUM(CASE WHEN pay_amount IS NOT NULL AND pay_amount > 0 THEN 1 ELSE 0 END) as with_pay,
        SUM(CASE WHEN pay_amount IS NULL OR pay_amount = 0 THEN 1 ELSE 0 END) as without_pay,
        SUM(CASE WHEN status = 'extra' THEN 1 ELSE 0 END) as extra_jobs
    FROM run_sheet_jobs
""")

overall = cursor.fetchone()

print("📊 OVERALL RUNSHEET STATISTICS:")
print(f"   Total Runsheet Jobs: {overall['total_runsheet_jobs']:,}")
print(f"   Jobs with Pay Data: {overall['with_pay']:,} ({overall['with_pay']/overall['total_runsheet_jobs']*100:.1f}%)")
print(f"   Jobs without Pay Data: {overall['without_pay']:,} ({overall['without_pay']/overall['total_runsheet_jobs']*100:.1f}%)")
print(f"   Extra (Reconstructed) Jobs: {overall['extra_jobs']:,}")
print()

# Check if jobs without pay have job numbers
cursor.execute("""
    SELECT 
        COUNT(*) as count,
        SUM(CASE WHEN job_number IS NOT NULL AND job_number != '' THEN 1 ELSE 0 END) as with_job_number
    FROM run_sheet_jobs
    WHERE pay_amount IS NULL OR pay_amount = 0
""")

no_pay_stats = cursor.fetchone()

print("📊 JOBS WITHOUT PAY DATA BREAKDOWN:")
print(f"   Total without pay: {no_pay_stats['count']:,}")
print(f"   Have job number: {no_pay_stats['with_job_number']:,}")
print(f"   No job number: {no_pay_stats['count'] - no_pay_stats['with_job_number']:,}")
print()

print("💡 INSIGHTS:")
print(f"   • {len(dates_with_mixed_pay)} dates have partial pay data (some jobs paid, others not)")
print(f"   • {total_jobs_without_pay:,} jobs on these dates are missing pay data")
print(f"   • These jobs may need to be linked to payslips manually")
print()

conn.close()
