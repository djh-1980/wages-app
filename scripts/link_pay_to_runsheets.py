#!/usr/bin/env python3
"""
Link payslip pay information to runsheet jobs using job numbers.
This allows you to see how much you were paid for each job on the runsheet.
"""

import sqlite3
from pathlib import Path
from datetime import datetime

def link_pay_to_runsheets(db_path="data/payslips.db"):
    """Link payslip pay information to runsheet jobs."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔗 LINKING PAY INFORMATION TO RUNSHEETS")
    print("=" * 50)
    
    # Add pay columns if they don't exist
    pay_columns = [
        "pay_amount REAL",
        "pay_rate REAL", 
        "pay_units REAL",
        "pay_week INTEGER",
        "pay_year TEXT",
        "pay_updated_at TIMESTAMP"
    ]
    
    for column in pay_columns:
        try:
            cursor.execute(f"ALTER TABLE run_sheet_jobs ADD COLUMN {column}")
            print(f"✅ Added column: {column.split()[0]}")
        except sqlite3.OperationalError:
            pass  # Column already exists
    
    # Update runsheet jobs with payslip data
    print("\n🔄 Updating runsheet jobs with pay information...")
    
    cursor.execute("""
        UPDATE run_sheet_jobs 
        SET 
            pay_amount = (
                SELECT j.amount 
                FROM job_items j 
                JOIN payslips p ON j.payslip_id = p.id
                WHERE j.job_number = run_sheet_jobs.job_number
                LIMIT 1
            ),
            pay_rate = (
                SELECT j.rate 
                FROM job_items j 
                JOIN payslips p ON j.payslip_id = p.id
                WHERE j.job_number = run_sheet_jobs.job_number
                LIMIT 1
            ),
            pay_units = (
                SELECT j.units 
                FROM job_items j 
                JOIN payslips p ON j.payslip_id = p.id
                WHERE j.job_number = run_sheet_jobs.job_number
                LIMIT 1
            ),
            pay_week = (
                SELECT p.week_number 
                FROM job_items j 
                JOIN payslips p ON j.payslip_id = p.id
                WHERE j.job_number = run_sheet_jobs.job_number
                LIMIT 1
            ),
            pay_year = (
                SELECT p.tax_year 
                FROM job_items j 
                JOIN payslips p ON j.payslip_id = p.id
                WHERE j.job_number = run_sheet_jobs.job_number
                LIMIT 1
            ),
            pay_updated_at = CURRENT_TIMESTAMP
        WHERE run_sheet_jobs.job_number IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM job_items j 
            WHERE j.job_number = run_sheet_jobs.job_number
        )
    """)
    
    updated_count = cursor.rowcount
    
    # Update address information for jobs with N/A addresses
    print("\n🏠 Updating N/A addresses with payslip location data...")
    
    cursor.execute("""
        UPDATE run_sheet_jobs 
        SET 
            job_address = (
                SELECT j.location 
                FROM job_items j 
                WHERE j.job_number = run_sheet_jobs.job_number
                AND j.location IS NOT NULL 
                AND j.location != ''
                AND j.location != 'N/A'
                LIMIT 1
            ),
            customer = COALESCE(
                (SELECT j.client 
                 FROM job_items j 
                 WHERE j.job_number = run_sheet_jobs.job_number
                 AND j.client IS NOT NULL 
                 AND j.client != ''
                 AND j.client != 'N/A'
                 LIMIT 1), 
                customer
            )
        WHERE run_sheet_jobs.job_number IS NOT NULL
        AND (
            run_sheet_jobs.job_address IN ('N/A', '', 'n/a', 'N/a') 
            OR run_sheet_jobs.job_address IS NULL
            OR run_sheet_jobs.customer IN ('N/A', '', 'n/a', 'N/a') 
            OR run_sheet_jobs.customer IS NULL
        )
        AND EXISTS (
            SELECT 1 FROM job_items j 
            WHERE j.job_number = run_sheet_jobs.job_number
            AND (
                (j.location IS NOT NULL AND j.location != '' AND j.location != 'N/A')
                OR (j.client IS NOT NULL AND j.client != '' AND j.client != 'N/A')
            )
        )
    """)
    
    address_updated_count = cursor.rowcount
    conn.commit()
    
    print(f"✅ Updated {updated_count} runsheet jobs with pay information")
    print(f"✅ Updated {address_updated_count} runsheet jobs with address/customer information")
    
    # Show statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_jobs,
            COUNT(pay_amount) as jobs_with_pay,
            ROUND(AVG(pay_amount), 2) as avg_pay,
            ROUND(SUM(pay_amount), 2) as total_pay
        FROM run_sheet_jobs
        WHERE job_number IS NOT NULL
    """)
    
    stats = cursor.fetchone()
    total_jobs, jobs_with_pay, avg_pay, total_pay = stats
    
    # Get address statistics
    cursor.execute("""
        SELECT 
            COUNT(*) as total_jobs,
            COUNT(CASE WHEN job_address NOT IN ('N/A', '', 'n/a', 'N/a') AND job_address IS NOT NULL THEN 1 END) as jobs_with_address,
            COUNT(CASE WHEN customer NOT IN ('N/A', '', 'n/a', 'N/a') AND customer IS NOT NULL THEN 1 END) as jobs_with_customer
        FROM run_sheet_jobs
        WHERE job_number IS NOT NULL
    """)
    
    address_stats = cursor.fetchone()
    total_jobs_addr, jobs_with_address, jobs_with_customer = address_stats
    
    print(f"\n📊 STATISTICS:")
    print(f"   Total runsheet jobs: {total_jobs:,}")
    print(f"   Jobs with pay info: {jobs_with_pay:,} ({(jobs_with_pay/total_jobs*100):.1f}%)")
    print(f"   Jobs with addresses: {jobs_with_address:,} ({(jobs_with_address/total_jobs_addr*100):.1f}%)")
    print(f"   Jobs with customer info: {jobs_with_customer:,} ({(jobs_with_customer/total_jobs_addr*100):.1f}%)")
    print(f"   Average pay per job: £{avg_pay}")
    print(f"   Total pay tracked: £{total_pay:,}")
    
    # Show recent examples
    cursor.execute("""
        SELECT 
            date, job_number, customer, pay_amount, pay_rate, pay_units, pay_year, pay_week
        FROM run_sheet_jobs 
        WHERE pay_amount IS NOT NULL 
        ORDER BY date DESC, CAST(job_number AS INTEGER) DESC
        LIMIT 10
    """)
    
    examples = cursor.fetchall()
    print(f"\n📋 RECENT EXAMPLES:")
    for date, job_num, customer, amount, rate, units, year, week in examples:
        customer_short = (customer[:30] + "...") if customer and len(customer) > 30 else customer
        print(f"   {date} | Job #{job_num} | £{amount} ({units}h @ £{rate}/h) | Week {week}/{year}")
        print(f"            {customer_short}")
        print()
    
    conn.close()
    
    return {
        'updated_jobs': updated_count,
        'total_jobs': total_jobs,
        'jobs_with_pay': jobs_with_pay,
        'match_rate': jobs_with_pay/total_jobs*100,
        'total_pay': total_pay
    }

def main():
    """Run the pay linking process."""
    try:
        result = link_pay_to_runsheets()
        
        print("=" * 50)
        print("🎉 PAY LINKING COMPLETE!")
        print(f"   {result['updated_jobs']} jobs updated")
        print(f"   {result['match_rate']:.1f}% match rate")
        print(f"   £{result['total_pay']:,} total pay tracked")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
