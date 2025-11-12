#!/usr/bin/env python3
"""
Comprehensive validation of run sheet data.
Checks for:
- Duplicate dates
- Invalid date formats
- Missing critical fields
- Unusual job counts
- Data consistency issues
"""

import sqlite3
from datetime import datetime
from collections import defaultdict
import re

DB_PATH = "data/payslips.db"


def validate_dates():
    """Validate date formats and check for duplicates."""
    print("\n" + "="*70)
    print("DATE VALIDATION")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get all dates
    cursor.execute("SELECT date, COUNT(*) as count FROM run_sheet_jobs GROUP BY date")
    dates = cursor.fetchall()
    
    invalid_dates = []
    duplicate_dates = []
    valid_dates = []
    
    date_pattern = re.compile(r'^\d{2}/\d{2}/\d{4}$')
    
    for date_str, count in dates:
        if not date_str:
            continue
            
        # Check format
        if not date_pattern.match(date_str):
            invalid_dates.append((date_str, "Invalid format"))
            continue
        
        # Try to parse
        try:
            dt = datetime.strptime(date_str, '%d/%m/%Y')
            valid_dates.append(date_str)
        except ValueError:
            invalid_dates.append((date_str, "Invalid date value"))
    
    conn.close()
    
    print(f"\n✅ Valid dates: {len(valid_dates)}")
    
    if invalid_dates:
        print(f"\n❌ Invalid dates found: {len(invalid_dates)}")
        for date, reason in invalid_dates[:10]:
            print(f"   - {date}: {reason}")
        if len(invalid_dates) > 10:
            print(f"   ... and {len(invalid_dates) - 10} more")
    else:
        print("✅ No invalid dates found")
    
    return len(invalid_dates) == 0


def validate_missing_fields():
    """Check for jobs with missing critical fields."""
    print("\n" + "="*70)
    print("MISSING FIELDS VALIDATION")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check for missing dates
    cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs WHERE date IS NULL OR date = ''")
    missing_dates = cursor.fetchone()[0]
    
    # Check for missing customers
    cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs WHERE customer IS NULL OR customer = ''")
    missing_customers = cursor.fetchone()[0]
    
    # Check for missing activities
    cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs WHERE activity IS NULL OR activity = ''")
    missing_activities = cursor.fetchone()[0]
    
    # Check for missing job numbers
    cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs WHERE job_number IS NULL OR job_number = ''")
    missing_job_numbers = cursor.fetchone()[0]
    
    # Get total jobs
    cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs")
    total_jobs = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\nTotal jobs: {total_jobs}")
    print(f"\nMissing fields:")
    print(f"  Dates: {missing_dates} ({missing_dates/total_jobs*100:.1f}%)")
    print(f"  Customers: {missing_customers} ({missing_customers/total_jobs*100:.1f}%)")
    print(f"  Activities: {missing_activities} ({missing_activities/total_jobs*100:.1f}%)")
    print(f"  Job Numbers: {missing_job_numbers} ({missing_job_numbers/total_jobs*100:.1f}%)")
    
    if missing_dates == 0 and missing_customers < total_jobs * 0.05:
        print("\n✅ Data completeness is good")
        return True
    else:
        print("\n⚠️  Some fields have missing data")
        return False


def validate_job_counts():
    """Check for unusual job counts per day."""
    print("\n" + "="*70)
    print("JOB COUNT VALIDATION")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get job counts per day
    cursor.execute("""
        SELECT date, COUNT(*) as job_count
        FROM run_sheet_jobs
        WHERE date IS NOT NULL
        GROUP BY date
        ORDER BY job_count DESC
    """)
    
    results = cursor.fetchall()
    conn.close()
    
    if not results:
        print("No data found")
        return False
    
    job_counts = [count for _, count in results]
    avg_jobs = sum(job_counts) / len(job_counts)
    max_jobs = max(job_counts)
    min_jobs = min(job_counts)
    
    print(f"\nJob count statistics:")
    print(f"  Average jobs per day: {avg_jobs:.1f}")
    print(f"  Maximum jobs in a day: {max_jobs}")
    print(f"  Minimum jobs in a day: {min_jobs}")
    
    # Find outliers (more than 2x average)
    outliers = [(date, count) for date, count in results if count > avg_jobs * 2]
    
    if outliers:
        print(f"\n⚠️  Days with unusually high job counts ({len(outliers)} days):")
        for date, count in outliers[:10]:
            print(f"   - {date}: {count} jobs")
        if len(outliers) > 10:
            print(f"   ... and {len(outliers) - 10} more")
    else:
        print("\n✅ No unusual job count outliers")
    
    # Find days with very few jobs
    low_days = [(date, count) for date, count in results if count <= 2]
    
    if low_days:
        print(f"\n⚠️  Days with very few jobs ({len(low_days)} days):")
        for date, count in low_days[:10]:
            print(f"   - {date}: {count} jobs")
        if len(low_days) > 10:
            print(f"   ... and {len(low_days) - 10} more")
    
    return True


def validate_duplicates():
    """Check for duplicate jobs."""
    print("\n" + "="*70)
    print("DUPLICATE VALIDATION")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check for duplicate job numbers on the same date
    cursor.execute("""
        SELECT date, job_number, COUNT(*) as count
        FROM run_sheet_jobs
        WHERE date IS NOT NULL AND job_number IS NOT NULL
        GROUP BY date, job_number
        HAVING count > 1
        ORDER BY count DESC
    """)
    
    duplicates = cursor.fetchall()
    conn.close()
    
    if duplicates:
        print(f"\n⚠️  Found {len(duplicates)} duplicate job entries:")
        for date, job_num, count in duplicates[:10]:
            print(f"   - {date}, Job #{job_num}: {count} times")
        if len(duplicates) > 10:
            print(f"   ... and {len(duplicates) - 10} more")
        return False
    else:
        print("\n✅ No duplicate jobs found")
        return True


def validate_data_consistency():
    """Check for data consistency issues."""
    print("\n" + "="*70)
    print("DATA CONSISTENCY VALIDATION")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check for inconsistent customer names (similar but different)
    cursor.execute("""
        SELECT customer, COUNT(*) as count
        FROM run_sheet_jobs
        WHERE customer IS NOT NULL
        GROUP BY customer
        ORDER BY count DESC
        LIMIT 20
    """)
    
    top_customers = cursor.fetchall()
    
    print(f"\nTop 10 customers:")
    for customer, count in top_customers[:10]:
        print(f"   - {customer}: {count} jobs")
    
    # Check for unusual postcodes
    cursor.execute("""
        SELECT postcode, COUNT(*) as count
        FROM run_sheet_jobs
        WHERE postcode IS NOT NULL AND postcode != ''
        GROUP BY postcode
        HAVING count = 1
    """)
    
    unique_postcodes = cursor.fetchone()
    
    cursor.execute("""
        SELECT COUNT(DISTINCT postcode)
        FROM run_sheet_jobs
        WHERE postcode IS NOT NULL AND postcode != ''
    """)
    
    total_postcodes = cursor.fetchone()[0]
    
    print(f"\nPostcode statistics:")
    print(f"  Total unique postcodes: {total_postcodes}")
    
    conn.close()
    
    print("\n✅ Data consistency check complete")
    return True


def generate_validation_summary():
    """Generate overall validation summary."""
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Overall statistics
    cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs")
    total_jobs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT date) FROM run_sheet_jobs WHERE date IS NOT NULL")
    total_dates = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT customer) FROM run_sheet_jobs WHERE customer IS NOT NULL")
    total_customers = cursor.fetchone()[0]
    
    cursor.execute("SELECT MIN(date), MAX(date) FROM run_sheet_jobs WHERE date IS NOT NULL")
    date_range = cursor.fetchone()
    
    conn.close()
    
    print(f"\nDatabase Statistics:")
    print(f"  Total jobs: {total_jobs:,}")
    print(f"  Unique dates: {total_dates:,}")
    print(f"  Unique customers: {total_customers:,}")
    print(f"  Date range: {date_range[0]} to {date_range[1]}")
    print(f"  Average jobs per day: {total_jobs/total_dates:.1f}")
    
    print("\n" + "="*70)


def main():
    """Run all validations."""
    print("\n" + "="*70)
    print("RUN SHEET DATA VALIDATION")
    print("="*70)
    
    results = {
        'dates': validate_dates(),
        'missing_fields': validate_missing_fields(),
        'job_counts': validate_job_counts(),
        'duplicates': validate_duplicates(),
        'consistency': validate_data_consistency()
    }
    
    generate_validation_summary()
    
    # Overall result
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✅ ALL VALIDATIONS PASSED")
    else:
        print("\n⚠️  SOME VALIDATIONS FAILED")
        print("\nFailed checks:")
        for check, passed in results.items():
            if not passed:
                print(f"  - {check}")
    
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    main()
