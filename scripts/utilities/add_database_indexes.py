#!/usr/bin/env python3
"""
Add database indexes for improved query performance.
Run this once to optimize the database.
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database import get_db_connection

def add_indexes():
    """Add performance indexes to the database."""
    
    indexes = [
        # Run sheet jobs indexes
        ("idx_runsheet_date", "run_sheet_jobs", "date"),
        ("idx_runsheet_job_number", "run_sheet_jobs", "job_number"),
        ("idx_runsheet_customer", "run_sheet_jobs", "customer"),
        ("idx_runsheet_activity", "run_sheet_jobs", "activity"),
        ("idx_runsheet_status", "run_sheet_jobs", "status"),
        ("idx_runsheet_pay_week", "run_sheet_jobs", "pay_week, pay_year"),
        
        # Payslips indexes
        ("idx_payslip_week", "payslips", "week_number, tax_year"),
        ("idx_payslip_period", "payslips", "period_start, period_end"),
        
        # Job items indexes
        ("idx_job_items_number", "job_items", "job_number"),
        ("idx_job_items_payslip", "job_items", "payslip_id"),
        
        # Attendance indexes
        ("idx_attendance_date", "attendance", "date"),
        ("idx_attendance_type", "attendance", "type"),
        
        # Customer mapping indexes
        ("idx_customer_mapping_original", "customer_mapping", "original_name"),
        
        # Runsheet daily data indexes
        ("idx_daily_data_date", "runsheet_daily_data", "date"),
    ]
    
    print("Adding database indexes for improved performance...")
    print("=" * 60)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get existing indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = {row[0] for row in cursor.fetchall()}
        
        added_count = 0
        skipped_count = 0
        
        for index_name, table_name, columns in indexes:
            if index_name in existing_indexes:
                print(f"⏭️  {index_name:30s} - Already exists")
                skipped_count += 1
                continue
            
            try:
                sql = f"CREATE INDEX {index_name} ON {table_name} ({columns})"
                cursor.execute(sql)
                print(f"✅ {index_name:30s} - Created on {table_name}({columns})")
                added_count += 1
            except sqlite3.Error as e:
                print(f"❌ {index_name:30s} - Failed: {e}")
        
        conn.commit()
    
    print("=" * 60)
    print(f"\n📊 Summary:")
    print(f"   Added: {added_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total: {len(indexes)}")
    print("\n✅ Database optimization complete!")

if __name__ == "__main__":
    try:
        add_indexes()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
