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
    conn.commit()
    
    print(f"✅ Updated {updated_count} runsheet jobs with pay information")
    
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
    
    print(f"\n📊 STATISTICS:")
    print(f"   Total runsheet jobs: {total_jobs:,}")
    print(f"   Jobs with pay info: {jobs_with_pay:,}")
    print(f"   Match rate: {(jobs_with_pay/total_jobs*100):.1f}%")
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
