#!/usr/bin/env python3
"""
Smart Sync - Only runs full sync if new files are detected
Prevents unnecessary processing when no new files arrive
"""

import sys
import subprocess
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

def check_for_new_files():
    """Check if there are likely new files to process"""
    
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "data/database/payslips.db"
    
    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        cursor = conn.cursor()
        
        # Check last import time
        cursor.execute("""
            SELECT MAX(imported_at) as last_import
            FROM run_sheet_jobs
            WHERE imported_at IS NOT NULL
        """)
        
        result = cursor.fetchone()
        last_import = result[0] if result and result[0] else None
        
        if not last_import:
            print("No previous imports found - running full sync")
            return True
            
        # Parse last import time
        try:
            last_import_dt = datetime.fromisoformat(last_import.replace('Z', '+00:00'))
        except:
            # Try different format
            last_import_dt = datetime.strptime(last_import, '%Y-%m-%d %H:%M:%S')
        
        # Check if it's been more than 2 hours since last import
        time_since_import = datetime.now() - last_import_dt.replace(tzinfo=None)
        
        if time_since_import > timedelta(hours=2):
            print(f"Last import was {time_since_import} ago - checking for new files")
            return True
        else:
            print(f"Recent import found ({time_since_import} ago) - skipping sync")
            return False
            
    except Exception as e:
        print(f"Error checking for new files: {e}")
        print("Running sync to be safe")
        return True
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main smart sync logic"""
    
    print(f"🧠 SMART SYNC - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Check if we should run sync
    if not check_for_new_files():
        print("✅ No sync needed - exiting")
        return 0
    
    print("🚀 Running master sync...")
    
    # Run the master sync
    base_dir = Path(__file__).parent.parent
    master_sync_path = base_dir / "scripts" / "sync_master.py"
    
    try:
        result = subprocess.run(
            [sys.executable, str(master_sync_path)],
            cwd=str(base_dir),
            capture_output=False,  # Let output show in real-time
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Smart sync completed successfully")
            return 0
        else:
            print(f"❌ Smart sync failed with code {result.returncode}")
            return result.returncode
            
    except Exception as e:
        print(f"❌ Error running master sync: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
