#!/usr/bin/env python3
"""
Cleanup script to handle days with runsheet entries but no actual work.
This script will:
1. Find dates with runsheet_daily_data but no jobs or all jobs are "Not Started"
2. Remove the runsheet data for those dates
3. Optionally create attendance entries for those dates
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import get_db_connection
from datetime import datetime


def find_absent_days():
    """Find days with runsheet data but no actual work done."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find dates in runsheet_daily_data that have no jobs in run_sheet_jobs
        # OR have jobs but they're all in "Not Started" status
        query = """
            SELECT DISTINCT d.date, d.mileage, d.fuel_cost
            FROM runsheet_daily_data d
            LEFT JOIN run_sheet_jobs j ON d.date = j.date
            WHERE j.date IS NULL
               OR (
                   SELECT COUNT(*) 
                   FROM run_sheet_jobs 
                   WHERE date = d.date 
                   AND (status IS NOT NULL AND status != '')
               ) = 0
            ORDER BY d.date DESC
        """
        
        cursor.execute(query)
        absent_days = cursor.fetchall()
        
        return [dict(row) for row in absent_days]


def cleanup_absent_day(date, create_attendance=False):
    """Remove runsheet data for an absent day and optionally create attendance entry."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Delete from runsheet_daily_data
        cursor.execute("DELETE FROM runsheet_daily_data WHERE date = ?", (date,))
        daily_deleted = cursor.rowcount
        
        # Delete any jobs (should be none or empty status)
        cursor.execute("DELETE FROM run_sheet_jobs WHERE date = ?", (date,))
        jobs_deleted = cursor.rowcount
        
        # Optionally create attendance entry
        attendance_created = False
        if create_attendance:
            try:
                cursor.execute("""
                    INSERT INTO attendance (date, reason, notes)
                    VALUES (?, ?, ?)
                """, (date, 'Absent', 'Auto-created by cleanup script'))
                attendance_created = True
            except Exception as e:
                print(f"  Warning: Could not create attendance entry: {e}")
        
        conn.commit()
        
        return {
            'daily_deleted': daily_deleted,
            'jobs_deleted': jobs_deleted,
            'attendance_created': attendance_created
        }


def main():
    """Main cleanup function."""
    print("=" * 60)
    print("Absent Days Cleanup Script")
    print("=" * 60)
    print()
    
    # Find absent days
    print("Searching for days with runsheet data but no actual work...")
    absent_days = find_absent_days()
    
    if not absent_days:
        print("✓ No absent days found with runsheet data!")
        print("  Your database is clean.")
        return
    
    print(f"Found {len(absent_days)} day(s) with runsheet data but no work:")
    print()
    
    for day in absent_days:
        print(f"  • {day['date']}")
        if day['mileage']:
            print(f"    Mileage: {day['mileage']} miles")
        if day['fuel_cost']:
            print(f"    Fuel: £{day['fuel_cost']:.2f}")
    
    print()
    print("Options:")
    print("  1. Delete runsheet data only (recommended)")
    print("  2. Delete runsheet data AND create attendance entries")
    print("  3. Cancel")
    print()
    
    choice = input("Select option (1-3): ").strip()
    
    if choice == '3':
        print("Cancelled.")
        return
    
    create_attendance = (choice == '2')
    
    print()
    print("Processing...")
    print()
    
    total_daily = 0
    total_jobs = 0
    total_attendance = 0
    
    for day in absent_days:
        date = day['date']
        result = cleanup_absent_day(date, create_attendance)
        
        print(f"✓ {date}:")
        print(f"  - Deleted {result['daily_deleted']} daily record(s)")
        print(f"  - Deleted {result['jobs_deleted']} job(s)")
        if result['attendance_created']:
            print(f"  - Created attendance entry")
        
        total_daily += result['daily_deleted']
        total_jobs += result['jobs_deleted']
        if result['attendance_created']:
            total_attendance += 1
    
    print()
    print("=" * 60)
    print("Cleanup Complete!")
    print("=" * 60)
    print(f"Total daily records deleted: {total_daily}")
    print(f"Total jobs deleted: {total_jobs}")
    if create_attendance:
        print(f"Total attendance entries created: {total_attendance}")
    print()


if __name__ == '__main__':
    main()
