#!/usr/bin/env python3
"""
Optimized sync script with improved error handling and performance.
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import argparse

def run_with_timeout(cmd, timeout_minutes=10, description="Command"):
    """Run command with timeout and better error handling."""
    print(f"🔄 Running {description}...")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_minutes * 60
        )
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            return True, result.stdout
        else:
            print(f"❌ {description} failed with code {result.returncode}")
            print(f"Error: {result.stderr}")
            return False, result.stderr
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {description} timed out after {timeout_minutes} minutes")
        return False, f"Timeout after {timeout_minutes} minutes"
    except Exception as e:
        print(f"💥 {description} crashed: {e}")
        return False, str(e)

def main():
    parser = argparse.ArgumentParser(description='Optimized payslip and runsheet sync')
    parser.add_argument('--recent', type=int, default=7, help='Only process files from last N days')
    parser.add_argument('--payslips-only', action='store_true', help='Only sync payslips')
    parser.add_argument('--runsheets-only', action='store_true', help='Only sync runsheets')
    parser.add_argument('--skip-gmail', action='store_true', help='Skip Gmail download, only process local files')
    
    args = parser.parse_args()
    
    print("🚀 Starting optimized sync process...")
    print(f"📅 Processing files from last {args.recent} days")
    
    success_count = 0
    total_operations = 0
    
    if not args.runsheets_only:
        total_operations += 1
        if not args.skip_gmail:
            # Download payslips from Gmail
            success, output = run_with_timeout([
                sys.executable, 'scripts/download_runsheets_gmail.py', 
                '--payslips', '--recent'
            ], timeout_minutes=5, description="Gmail payslip download")
            
            if success:
                success_count += 1
        
        # Process payslips
        success, output = run_with_timeout([
            sys.executable, 'scripts/extract_payslips.py', '--recent', str(args.recent)
        ], timeout_minutes=10, description="Payslip extraction")
        
        if success:
            success_count += 1
    
    if not args.payslips_only:
        total_operations += 1
        if not args.skip_gmail:
            # Download runsheets from Gmail
            success, output = run_with_timeout([
                sys.executable, 'scripts/download_runsheets_gmail.py', 
                '--runsheets', '--recent'
            ], timeout_minutes=5, description="Gmail runsheet download")
            
            if success:
                success_count += 1
        
        # Process runsheets with parallel processing
        success, output = run_with_timeout([
            sys.executable, 'scripts/import_run_sheets.py', 
            '--recent', str(args.recent), '--workers', '2'
        ], timeout_minutes=15, description="Runsheet import")
        
        if success:
            success_count += 1
    
    print(f"\n📊 Sync completed: {success_count}/{total_operations} operations successful")
    
    if success_count == total_operations:
        print("🎉 All operations completed successfully!")
        return 0
    else:
        print("⚠️  Some operations failed - check logs above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
