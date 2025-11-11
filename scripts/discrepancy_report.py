#!/usr/bin/env python3
"""
Generate a discrepancy report showing jobs that appear in payslips but not in runsheets.
This helps identify missing runsheet data or data entry issues.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
import csv

def generate_discrepancy_report(db_path="data/payslips.db", output_dir="reports"):
    """Generate a report of jobs paid but not on runsheets."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔍 GENERATING DISCREPANCY REPORT")
    print("=" * 50)
    
    # Find jobs in payslips that don't exist in runsheets
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
            j.agency,
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
        ORDER BY p.tax_year DESC, p.week_number DESC, CAST(j.job_number AS INTEGER) DESC
    """)
    
    missing_jobs = cursor.fetchall()
    
    print(f"📊 ANALYSIS RESULTS:")
    print(f"   Jobs in payslips: {get_total_payslip_jobs(cursor)}")
    print(f"   Jobs in runsheets: {get_total_runsheet_jobs(cursor)}")
    print(f"   Jobs paid but missing from runsheets: {len(missing_jobs)}")
    
    if missing_jobs:
        # Calculate financial impact
        total_missing_amount = sum(job[7] for job in missing_jobs if job[7])  # amount column
        print(f"   Total value of missing jobs: £{total_missing_amount:,.2f}")
        
        # Group by tax year for summary
        year_summary = {}
        for job in missing_jobs:
            year = job[12]  # tax_year column
            if year not in year_summary:
                year_summary[year] = {'count': 0, 'amount': 0}
            year_summary[year]['count'] += 1
            year_summary[year]['amount'] += job[7] if job[7] else 0
        
        print(f"\n📅 BREAKDOWN BY TAX YEAR:")
        for year in sorted(year_summary.keys(), reverse=True):
            data = year_summary[year]
            print(f"   {year}: {data['count']} jobs, £{data['amount']:,.2f}")
        
        # Show recent examples
        print(f"\n📋 RECENT MISSING JOBS (Last 10):")
        for i, job in enumerate(missing_jobs[:10], 1):
            job_num, client, location, postcode, job_type, date, time, amount, rate, units, agency, week, year, pay_date = job
            location_str = f"{location} {postcode}" if location and postcode else (location or postcode or "Unknown location")
            print(f"   {i:2d}. Job #{job_num} | {client or 'Unknown client'}")
            print(f"       {location_str} | £{amount} | Week {week}/{year}")
            print()
        
        # Generate CSV report
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = output_path / f"discrepancy_report_{timestamp}.csv"
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Job Number', 'Client', 'Location', 'Postcode', 'Job Type',
                'Date', 'Time', 'Amount', 'Rate', 'Units', 'Agency',
                'Week Number', 'Tax Year', 'Pay Date'
            ])
            
            # Write data
            for job in missing_jobs:
                writer.writerow(job)
        
        print(f"📄 DETAILED REPORT SAVED:")
        print(f"   {csv_file}")
        print(f"   Contains all {len(missing_jobs)} missing jobs")
        
        # Generate recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if len(missing_jobs) > 100:
            print("   • High number of missing jobs - check runsheet import process")
        if any(job[12] == '2025' for job in missing_jobs[:20]):  # Recent jobs
            print("   • Recent jobs missing - ensure latest runsheets are imported")
        
        # Check for patterns
        agencies = [job[10] for job in missing_jobs if job[10]]
        if agencies:
            from collections import Counter
            agency_counts = Counter(agencies)
            top_agency = agency_counts.most_common(1)[0]
            print(f"   • Most missing jobs from: {top_agency[0]} ({top_agency[1]} jobs)")
        
    else:
        print("\n✅ EXCELLENT! No discrepancies found.")
        print("   All paid jobs are properly recorded in runsheets.")
    
    conn.close()
    
    return {
        'missing_jobs_count': len(missing_jobs),
        'total_missing_value': sum(job[7] for job in missing_jobs if job[7]),
        'csv_file': csv_file.name if missing_jobs else None,
        'year_summary': year_summary if missing_jobs else {}
    }

def get_total_payslip_jobs(cursor):
    """Get total number of jobs in payslips."""
    cursor.execute("SELECT COUNT(*) FROM job_items WHERE job_number IS NOT NULL")
    return cursor.fetchone()[0]

def get_total_runsheet_jobs(cursor):
    """Get total number of jobs in runsheets."""
    cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs WHERE job_number IS NOT NULL")
    return cursor.fetchone()[0]

def generate_reverse_discrepancy_report(db_path="data/payslips.db"):
    """Find jobs in runsheets but not in payslips (unpaid work)."""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"\n🔄 REVERSE DISCREPANCY CHECK")
    print("=" * 30)
    
    # Find jobs in runsheets that don't exist in payslips
    cursor.execute("""
        SELECT 
            r.job_number,
            r.date,
            r.customer,
            r.activity,
            r.job_address,
            r.postcode
        FROM run_sheet_jobs r
        WHERE r.job_number IS NOT NULL 
        AND r.job_number NOT IN (
            SELECT DISTINCT job_number 
            FROM job_items 
            WHERE job_number IS NOT NULL
        )
        ORDER BY substr(r.date, 7, 4) || '-' || substr(r.date, 4, 2) || '-' || substr(r.date, 1, 2) DESC
        LIMIT 20
    """)
    
    unpaid_jobs = cursor.fetchall()
    
    print(f"📊 UNPAID WORK ANALYSIS:")
    print(f"   Jobs in runsheets but not paid: {len(unpaid_jobs)}")
    
    if unpaid_jobs:
        print(f"\n📋 RECENT UNPAID JOBS (Last 10):")
        for i, job in enumerate(unpaid_jobs[:10], 1):
            job_num, date, customer, activity, address, postcode = job
            print(f"   {i:2d}. Job #{job_num} | {date}")
            print(f"       {customer} | {activity}")
            print()
    else:
        print("   ✅ All runsheet jobs have been paid!")
    
    conn.close()
    return len(unpaid_jobs)

def main():
    """Run the discrepancy analysis."""
    try:
        # Main discrepancy report
        result = generate_discrepancy_report()
        
        # Reverse check
        unpaid_count = generate_reverse_discrepancy_report()
        
        print("=" * 50)
        print("🎯 SUMMARY:")
        print(f"   Missing from runsheets: {result['missing_jobs_count']} jobs")
        print(f"   Missing from payslips: {unpaid_count} jobs")
        
        if result['missing_jobs_count'] == 0 and unpaid_count == 0:
            print("   🎉 Perfect data integrity!")
        else:
            print("   📝 Review recommended for data completeness")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
