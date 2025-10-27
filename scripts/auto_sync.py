#!/usr/bin/env python3
"""
Auto-sync script for downloading and importing run sheets.
Runs via cron job.
"""

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

def log(message):
    """Log with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def main():
    log("=== Starting auto-sync ===")
    
    # Get yesterday's date (run sheets usually arrive next day)
    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y/%m/%d')
    
    log(f"Downloading run sheets from {date_str}...")
    
    try:
        # Step 1: Download from Gmail
        result = subprocess.run(
            [sys.executable, 'scripts/download_runsheets_gmail.py', 
             '--after-date', date_str],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            log(f"Download complete: {result.stdout.strip()}")
        else:
            log(f"Download failed: {result.stderr}")
            return 1
        
        # Step 2: Import run sheets (only recent files)
        log("Importing recent run sheets to database...")
        result = subprocess.run(
            [sys.executable, 'scripts/import_run_sheets.py', '--recent', '7'],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            log(f"Import complete")
            # Show summary from output
            lines = result.stdout.strip().split('\n')
            for line in lines[-10:]:  # Last 10 lines
                if line.strip():
                    log(f"  {line}")
        else:
            log(f"Import failed: {result.stderr}")
            return 1
        
        log("=== Auto-sync completed successfully ===")
        return 0
        
    except Exception as e:
        log(f"Error: {e}")
        import traceback
        log(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
