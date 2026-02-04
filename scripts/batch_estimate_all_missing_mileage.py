#!/usr/bin/env python3
"""
Batch estimate mileage for all dates with missing mileage across entire database.
Runs route optimization and saves rounded-up mileage + full route data.
"""

import sys
import os
import time
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db_connection
import requests

API_BASE_URL = "http://localhost:5000"

def get_missing_mileage_dates():
    """Get all dates with jobs but no mileage."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT r.date, COUNT(r.id) as job_count
            FROM run_sheet_jobs r
            LEFT JOIN runsheet_daily_data m ON r.date = m.date
            WHERE m.mileage IS NULL
            AND r.status != 'deleted'
            GROUP BY r.date
            ORDER BY r.date
        """)
        
        return [{'date': row[0], 'job_count': row[1]} for row in cursor.fetchall()]

def optimize_route(date):
    """Call route optimization API for a date."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/route-planning/optimize",
            json={'date': date, 'include_depot': True},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  ✗ API error {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"  ✗ Timeout after 30 seconds")
        return None
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return None

def save_mileage_and_route(date, route_data):
    """Save mileage and full route data to database."""
    try:
        # Round up mileage
        rounded_miles = int(route_data['total_distance_miles']) + (1 if route_data['total_distance_miles'] % 1 > 0 else 0)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Save mileage
            cursor.execute("""
                INSERT INTO runsheet_daily_data (date, mileage, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(date) DO UPDATE SET
                    mileage = excluded.mileage,
                    updated_at = CURRENT_TIMESTAMP
            """, (date, float(rounded_miles)))
            
            # Save full route data
            full_route_data = {
                'total_distance_miles': route_data['total_distance_miles'],
                'total_duration_minutes': route_data['total_duration_minutes'],
                'total_jobs': route_data['total_jobs'],
                'route': route_data.get('route', [])
            }
            
            cursor.execute("""
                UPDATE runsheet_daily_data
                SET route_data = ?
                WHERE date = ?
            """, (json.dumps(full_route_data), date))
            
            conn.commit()
            
        return True, rounded_miles
        
    except Exception as e:
        print(f"  ✗ Save error: {str(e)}")
        return False, None

def main():
    print("=" * 60)
    print("BATCH MILEAGE ESTIMATION - ALL MISSING DATES")
    print("=" * 60)
    
    # Get all missing dates
    print("\n📊 Finding dates with missing mileage...")
    missing_dates = get_missing_mileage_dates()
    
    if not missing_dates:
        print("✓ No missing mileage found!")
        return
    
    print(f"✓ Found {len(missing_dates)} dates with missing mileage\n")
    
    # Process each date
    success_count = 0
    fail_count = 0
    
    for i, date_info in enumerate(missing_dates, 1):
        date = date_info['date']
        job_count = date_info['job_count']
        
        print(f"[{i}/{len(missing_dates)}] {date} ({job_count} jobs)...")
        
        # Optimize route
        route_data = optimize_route(date)
        
        if route_data and route_data.get('success'):
            # Save to database
            saved, rounded_miles = save_mileage_and_route(date, route_data)
            
            if saved:
                print(f"  ✓ Saved: {rounded_miles} miles (from {route_data['total_distance_miles']:.2f})")
                success_count += 1
            else:
                fail_count += 1
        else:
            fail_count += 1
        
        # Small delay to avoid overwhelming API
        time.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 60)
    print("BATCH ESTIMATION COMPLETE")
    print("=" * 60)
    print(f"✓ Success: {success_count} dates")
    print(f"✗ Failed:  {fail_count} dates")
    print(f"📊 Total:   {len(missing_dates)} dates")
    print("=" * 60)

if __name__ == "__main__":
    main()
