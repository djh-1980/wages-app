#!/usr/bin/env python3
"""
Daily Parsing Quality Check
Quick script to check parsing quality for a specific date
Usage: python3 daily_parsing_check.py [YYYY-MM-DD]
"""

import sys
import sqlite3
from datetime import datetime, timedelta

def check_date_quality(date_str):
    """Check parsing quality for a specific date."""
    # Convert date format if needed
    if len(date_str.split('-')) == 3:
        # Convert YYYY-MM-DD to DD/MM/YYYY
        year, month, day = date_str.split('-')
        db_date = f"{day}/{month}/{year}"
    else:
        db_date = date_str
    
    conn = sqlite3.connect('data/database/payslips.db')
    cursor = conn.cursor()
    
    print(f"🔍 Parsing Quality Check for {db_date}")
    print("=" * 50)
    
    # Get all jobs for the date
    cursor.execute("""
        SELECT job_number, customer, activity, job_address, postcode
        FROM run_sheet_jobs 
        WHERE date = ?
        ORDER BY customer, job_number
    """, (db_date,))
    
    jobs = cursor.fetchall()
    
    if not jobs:
        print(f"❌ No jobs found for {db_date}")
        return
    
    print(f"📊 Found {len(jobs)} jobs")
    
    # Analyze quality
    issues = []
    customers_with_issues = set()
    
    for job in jobs:
        job_number, customer, activity, address, postcode = job
        job_issues = []
        
        if not activity:
            job_issues.append("Missing activity")
        if not address:
            job_issues.append("Missing address")
        if not postcode:
            job_issues.append("Missing postcode")
        
        # Check for quality issues
        if address:
            if any(x in address for x in ['epot', 'orthern', 'tation']):
                job_issues.append("Truncated address")
            if address.startswith('+44') or address.startswith('0'):
                job_issues.append("Phone in address")
        
        if job_issues:
            issues.append((job_number, customer, job_issues))
            customers_with_issues.add(customer)
    
    if not issues:
        print("✅ All jobs have perfect parsing quality!")
        return
    
    print(f"\n⚠️  Found {len(issues)} jobs with issues:")
    for job_number, customer, job_issues in issues:
        print(f"  Job {job_number} ({customer}): {', '.join(job_issues)}")
    
    print(f"\n🎯 Customers that need parser improvements:")
    for customer in sorted(customers_with_issues):
        customer_issues = [j for j in issues if j[1] == customer]
        print(f"  - {customer}: {len(customer_issues)} jobs with issues")
        print(f"    Command: python3 scripts/parsing_manager.py start \"{customer}\"")
    
    conn.close()

def check_recent_dates(days=7):
    """Check parsing quality for recent dates."""
    print(f"🔍 Checking parsing quality for last {days} days")
    print("=" * 60)
    
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        print(f"\n📅 {date.strftime('%A, %d/%m/%Y')}:")
        
        # Quick check
        conn = sqlite3.connect('data/database/payslips.db')
        cursor = conn.cursor()
        
        db_date = date.strftime("%d/%m/%Y")
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN activity IS NULL THEN 1 ELSE 0 END) as missing_activity,
                   SUM(CASE WHEN job_address IS NULL THEN 1 ELSE 0 END) as missing_address
            FROM run_sheet_jobs 
            WHERE date = ?
        """, (db_date,))
        
        stats = cursor.fetchone()
        total, missing_activity, missing_address = stats
        
        if total == 0:
            print("  No jobs found")
        else:
            activity_rate = ((total - missing_activity) / total * 100) if total > 0 else 0
            address_rate = ((total - missing_address) / total * 100) if total > 0 else 0
            
            status = "✅" if activity_rate == 100 and address_rate == 100 else "⚠️"
            print(f"  {status} {total} jobs - Activity: {activity_rate:.0f}%, Address: {address_rate:.0f}%")
            
            if missing_activity > 0 or missing_address > 0:
                print(f"    Use: python3 daily_parsing_check.py {date_str}")
        
        conn.close()

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--recent":
            check_recent_dates()
        else:
            check_date_quality(sys.argv[1])
    else:
        # Default: check today
        today = datetime.now().strftime("%Y-%m-%d")
        check_date_quality(today)

if __name__ == "__main__":
    main()
