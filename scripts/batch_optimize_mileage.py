#!/usr/bin/env python3
"""
Batch Route Optimization and Mileage Calculator
Optimizes routes for a date range and saves mileage to database
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import requests
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import Config

def get_db_connection():
    """Get database connection"""
    db_path = Path(Config.DATABASE_PATH)
    return sqlite3.connect(str(db_path))

def optimize_route_for_date(date_str):
    """Call the route optimization API for a specific date"""
    try:
        url = 'http://127.0.0.1:5001/api/route-planning/optimize'
        
        response = requests.post(url, json={
            'date': date_str,
            'include_depot': True
        }, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data
            else:
                print(f"  ❌ Optimization failed: {data.get('error', 'Unknown error')}")
                return None
        else:
            print(f"  ❌ HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None

def save_mileage(date_str, mileage):
    """Save mileage to database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if mileage record exists
            cursor.execute("SELECT id FROM daily_mileage WHERE date = ?", (date_str,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE daily_mileage 
                    SET total_miles = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE date = ?
                """, (mileage, date_str))
                print(f"  ✅ Updated mileage: {mileage} miles")
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO daily_mileage (date, total_miles, created_at, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """, (date_str, mileage))
                print(f"  ✅ Added mileage: {mileage} miles")
            
            conn.commit()
            return True
            
    except Exception as e:
        print(f"  ❌ Error saving mileage: {e}")
        return False

def save_route_order(date_str, route_data):
    """Save route order to database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get job IDs and their route order
            for idx, waypoint in enumerate(route_data.get('route', [])):
                job_id = waypoint.get('job_id')
                if job_id:
                    cursor.execute("""
                        UPDATE run_sheet_jobs
                        SET route_order = ?
                        WHERE id = ?
                    """, (idx, job_id))
            
            conn.commit()
            print(f"  ✅ Saved route order for {len(route_data.get('route', []))} waypoints")
            return True
            
    except Exception as e:
        print(f"  ❌ Error saving route order: {e}")
        return False

def batch_optimize(start_date_str, end_date_str):
    """Batch optimize routes for a date range"""
    
    print("=" * 70)
    print("BATCH ROUTE OPTIMIZATION & MILEAGE CALCULATOR")
    print("=" * 70)
    print(f"Date Range: {start_date_str} to {end_date_str}")
    print()
    
    # Parse dates
    start_date = datetime.strptime(start_date_str, '%d/%m/%Y')
    end_date = datetime.strptime(end_date_str, '%d/%m/%Y')
    
    current_date = start_date
    total_processed = 0
    total_success = 0
    total_mileage = 0
    
    while current_date <= end_date:
        date_str = current_date.strftime('%d/%m/%Y')
        
        print(f"📅 Processing {date_str}...")
        
        # Check if there are jobs for this date
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs WHERE date = ?", (date_str,))
            job_count = cursor.fetchone()[0]
        
        if job_count == 0:
            print(f"  ⏭️  No jobs found - skipping")
            current_date += timedelta(days=1)
            continue
        
        print(f"  📋 Found {job_count} jobs")
        
        # Optimize route
        route_data = optimize_route_for_date(date_str)
        
        if route_data:
            mileage = route_data.get('total_distance_miles', 0)
            total_mileage += mileage
            
            # Save mileage
            if save_mileage(date_str, round(mileage)):
                # Save route order
                save_route_order(date_str, route_data)
                total_success += 1
        
        total_processed += 1
        current_date += timedelta(days=1)
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Dates processed: {total_processed}")
    print(f"Successfully optimized: {total_success}")
    print(f"Total mileage calculated: {total_mileage:.1f} miles")
    print(f"Average per day: {total_mileage/total_success:.1f} miles" if total_success > 0 else "N/A")
    print("=" * 70)

if __name__ == '__main__':
    # Date range: 11/02/2026 to 22/02/2026
    batch_optimize('11/02/2026', '22/02/2026')
