#!/usr/bin/env python3
"""
Cleanup script to remove runsheets for dates that have attendance records.
This handles the case where attendance was added before the automatic cleanup was implemented.
"""

import sqlite3
import sys
from pathlib import Path

def cleanup_attendance_runsheets():
    """Remove runsheet data for any dates that have attendance records."""
    
    # Connect to database
    db_path = Path(__file__).parent.parent / 'data' / 'payslips.db'
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Find all dates with attendance records
        cursor.execute("SELECT DISTINCT date FROM attendance ORDER BY date")
        attendance_dates = [row[0] for row in cursor.fetchall()]
        
        print(f"Found {len(attendance_dates)} dates with attendance records:")
        
        total_jobs_removed = 0
        total_daily_removed = 0
        
        for date in attendance_dates:
            # Check for runsheet jobs on this date
            cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs WHERE date = ?", (date,))
            job_count = cursor.fetchone()[0]
            
            # Check for daily data on this date
            cursor.execute("SELECT COUNT(*) FROM runsheet_daily_data WHERE date = ?", (date,))
            daily_count = cursor.fetchone()[0]
            
            if job_count > 0 or daily_count > 0:
                print(f"\n📅 {date}:")
                print(f"   - Jobs to remove: {job_count}")
                print(f"   - Daily records to remove: {daily_count}")
                
                # Get attendance reason for context
                cursor.execute("SELECT reason FROM attendance WHERE date = ? LIMIT 1", (date,))
                reason = cursor.fetchone()[0]
                print(f"   - Attendance reason: {reason}")
                
                # Remove runsheet jobs
                if job_count > 0:
                    cursor.execute("DELETE FROM run_sheet_jobs WHERE date = ?", (date,))
                    total_jobs_removed += job_count
                
                # Remove daily data
                if daily_count > 0:
                    cursor.execute("DELETE FROM runsheet_daily_data WHERE date = ?", (date,))
                    total_daily_removed += daily_count
                
                print(f"   ✅ Cleaned up runsheet data")
            else:
                print(f"📅 {date}: No runsheet data to clean up")
        
        # Commit all changes
        conn.commit()
        
        print(f"\n🎯 CLEANUP SUMMARY:")
        print(f"   - Total jobs removed: {total_jobs_removed}")
        print(f"   - Total daily records removed: {total_daily_removed}")
        print(f"   - Dates processed: {len(attendance_dates)}")
        print(f"\n✅ Cleanup completed successfully!")
        print(f"✅ Future attendance additions will automatically remove runsheets")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("🧹 ATTENDANCE RUNSHEET CLEANUP")
    print("=" * 50)
    print("This script removes runsheet data for dates with attendance records.")
    print("Attendance indicates you didn't work, so runsheets should be removed.")
    print()
    
    response = input("Continue with cleanup? (y/N): ").strip().lower()
    if response in ['y', 'yes']:
        cleanup_attendance_runsheets()
    else:
        print("Cleanup cancelled.")
