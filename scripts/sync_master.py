#!/usr/bin/env python3
"""
Master Sync System - Complete end-to-end sync from scratch
Downloads -> Organizes -> Imports -> Validates -> Syncs -> Reports
"""

import os
import sys
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import unified logger and config
from app.utils.sync_logger import sync_logger
from app.config import Config

class MasterSync:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.db_path = self.base_dir / "data/database/payslips.db"
        self.results = {
            'runsheets_downloaded': 0,
            'payslips_downloaded': 0,
            'runsheet_jobs_imported': 0,
            'payslip_jobs_imported': 0,
            'jobs_synced': 0,
            'errors': []
        }
        
    def log(self, message):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
        
    def setup_database(self):
        """Ensure database has proper indexes for fast syncing"""
        self.log("🔧 Setting up database indexes...")
        
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=10.0)
            cursor = conn.cursor()
            
            # Create indexes for fast job number matching
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_runsheet_job_number ON run_sheet_jobs(job_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_job_items_job_number ON job_items(job_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_runsheet_pay_amount ON run_sheet_jobs(pay_amount)')
            
            conn.commit()
            conn.close()
            self.log("   ✅ Database indexes ready")
            return True
            
        except Exception as e:
            self.log(f"   ❌ Database setup failed: {e}")
            self.results['errors'].append(f"Database setup: {e}")
            return False
    
    def download_files(self):
        """Phase 1: Download files from Gmail"""
        self.log("📥 Phase 1: Downloading files from Gmail...")
        
        os.chdir(self.base_dir)
        
        # Download runsheets
        self.log("   Downloading runsheets...")
        try:
            result = subprocess.run([
                sys.executable, 
                'scripts/production/download_runsheets_gmail.py', 
                '--runsheets', '--recent'
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                # Count downloaded files from output
                for line in result.stdout.split('\n'):
                    if 'Downloaded:' in line or 'Saved:' in line:
                        self.results['runsheets_downloaded'] += 1
                self.log(f"   ✅ Downloaded {self.results['runsheets_downloaded']} runsheets")
            else:
                self.log(f"   ❌ Runsheet download failed: {result.stderr}")
                self.results['errors'].append("Runsheet download failed")
                
        except Exception as e:
            self.log(f"   ❌ Runsheet download error: {e}")
            self.results['errors'].append(f"Runsheet download: {e}")
        
        # Download payslips (Tuesdays or if recent payslips exist)
        if datetime.now().weekday() == 1 or self._has_recent_payslips():
            self.log("   Downloading payslips...")
            try:
                search_date = datetime.now().strftime('%Y/%m/%d')
                result = subprocess.run([
                    sys.executable,
                    'scripts/production/download_runsheets_gmail.py',
                    '--payslips', f'--date={search_date}'
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'Downloaded:' in line or 'Saved:' in line:
                            self.results['payslips_downloaded'] += 1
                    self.log(f"   ✅ Downloaded {self.results['payslips_downloaded']} payslips")
                else:
                    self.log(f"   ❌ Payslip download failed: {result.stderr}")
                    
            except Exception as e:
                self.log(f"   ❌ Payslip download error: {e}")
        else:
            self.log("   ⏭️  Skipping payslips (not Tuesday)")
    
    def _has_recent_payslips(self):
        """Check if there are recent payslip files to process"""
        payslip_dir = Path(Config.PAYSLIPS_DIR)
        if not payslip_dir.exists():
            return False
            
        # Check for files modified in last 7 days
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=7)
        
        for pdf_file in payslip_dir.rglob("*.pdf"):
            if datetime.fromtimestamp(pdf_file.stat().st_mtime) > cutoff:
                return True
        return False
    
    def import_runsheets(self):
        """Phase 2a: Import runsheet data"""
        self.log("📋 Phase 2a: Importing runsheets...")
        
        try:
            result = subprocess.run([
                sys.executable,
                'scripts/production/import_run_sheets.py',
                '--recent', '7'  # Last 7 days
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Count imported jobs from output
                for line in result.stdout.split('\n'):
                    if 'jobs imported' in line.lower() or 'imported:' in line:
                        # Extract number from line
                        import re
                        numbers = re.findall(r'\d+', line)
                        if numbers:
                            self.results['runsheet_jobs_imported'] += int(numbers[0])
                
                self.log(f"   ✅ Imported {self.results['runsheet_jobs_imported']} runsheet jobs")
                return True
            else:
                self.log(f"   ❌ Runsheet import failed")
                self.results['errors'].append("Runsheet import failed")
                return False
                
        except Exception as e:
            self.log(f"   ❌ Runsheet import error: {e}")
            self.results['errors'].append(f"Runsheet import: {e}")
            return False
    
    def import_payslips(self):
        """Phase 2b: Import payslip data"""
        self.log("💰 Phase 2b: Importing payslips...")
        
        try:
            result = subprocess.run([
                sys.executable,
                'scripts/production/extract_payslips.py',
                '--recent', '7'  # Last 7 days
            ], capture_output=True, text=True, timeout=180)
            
            if result.returncode == 0:
                # Count imported jobs from output
                for line in result.stdout.split('\n'):
                    if 'job items' in line.lower():
                        import re
                        numbers = re.findall(r'\d+', line)
                        if numbers:
                            self.results['payslip_jobs_imported'] += int(numbers[-1])  # Last number is usually the count
                
                self.log(f"   ✅ Imported {self.results['payslip_jobs_imported']} payslip jobs")
                return True
            else:
                self.log(f"   ❌ Payslip import failed")
                self.results['errors'].append("Payslip import failed")
                return False
                
        except Exception as e:
            self.log(f"   ❌ Payslip import error: {e}")
            self.results['errors'].append(f"Payslip import: {e}")
            return False
    
    def validate_addresses(self):
        """Phase 2c: Validate and clean up addresses"""
        self.log("🔍 Phase 2c: Validating and cleaning addresses...")
        
        try:
            result = subprocess.run([
                sys.executable,
                'scripts/production/validate_addresses.py',
                '--recent', '7'  # Validate last 7 days
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # Extract fixes count from output
                fixes_applied = 0
                for line in result.stdout.split('\n'):
                    if 'Fixes applied:' in line:
                        import re
                        numbers = re.findall(r'\d+', line)
                        if numbers:
                            fixes_applied = int(numbers[0])
                            break
                
                self.log(f"   ✅ Applied {fixes_applied} address fixes")
                return True
            else:
                self.log(f"   ❌ Address validation failed")
                self.results['errors'].append("Address validation failed")
                return False
                
        except Exception as e:
            self.log(f"   ❌ Address validation error: {e}")
            self.results['errors'].append(f"Address validation: {e}")
            return False
    
    def sync_pay_data(self):
        """Phase 3: Match payslip data to runsheet jobs"""
        self.log("🔄 Phase 3: Syncing pay data to runsheet jobs...")
        
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0)
            conn.execute('PRAGMA journal_mode=DELETE')
            conn.execute('PRAGMA synchronous=NORMAL')
            cursor = conn.cursor()
            
            # First, handle PayPoint Van Stock Audit jobs (set to £0)
            self.log("   Setting PayPoint Van Stock Audit jobs to £0...")
            cursor.execute("""
                UPDATE run_sheet_jobs 
                SET 
                    pay_amount = 0.0,
                    pay_rate = 0.0,
                    pay_units = 1.0,
                    status = CASE WHEN status = 'DNCO' THEN 'completed' ELSE status END,
                    pay_updated_at = CURRENT_TIMESTAMP
                WHERE customer LIKE '%PayPoint - Van Stock Audit%'
                AND (pay_amount IS NULL OR status = 'DNCO')
            """)
            
            paypoint_updated = cursor.rowcount
            if paypoint_updated > 0:
                self.log(f"   ✅ Set {paypoint_updated} PayPoint audit jobs to £0")
            
            conn.commit()
            
            # Count jobs that need pay data
            cursor.execute("""
                SELECT COUNT(*) 
                FROM run_sheet_jobs r
                WHERE r.job_number IS NOT NULL
                AND r.pay_amount IS NULL
                AND EXISTS (
                    SELECT 1 FROM job_items j 
                    WHERE j.job_number = r.job_number
                )
            """)
            
            jobs_to_update = cursor.fetchone()[0]
            self.log(f"   Found {jobs_to_update} jobs needing pay data")
            
            if jobs_to_update == 0:
                self.log("   ✅ All jobs already have pay data")
                return True
            
            # Update pay data in one efficient query
            start_time = time.time()
            cursor.execute("""
                UPDATE run_sheet_jobs 
                SET 
                    pay_amount = (
                        SELECT j.amount 
                        FROM job_items j 
                        WHERE j.job_number = run_sheet_jobs.job_number
                        LIMIT 1
                    ),
                    pay_rate = (
                        SELECT j.rate 
                        FROM job_items j 
                        WHERE j.job_number = run_sheet_jobs.job_number
                        LIMIT 1
                    ),
                    pay_week = (
                        SELECT p.week_number 
                        FROM job_items j 
                        JOIN payslips p ON j.payslip_id = p.id
                        WHERE j.job_number = run_sheet_jobs.job_number
                        LIMIT 1
                    ),
                    pay_year = (
                        SELECT p.tax_year 
                        FROM job_items j 
                        JOIN payslips p ON j.payslip_id = p.id
                        WHERE j.job_number = run_sheet_jobs.job_number
                        LIMIT 1
                    ),
                    pay_updated_at = CURRENT_TIMESTAMP
                WHERE run_sheet_jobs.job_number IS NOT NULL
                AND run_sheet_jobs.pay_amount IS NULL
                AND EXISTS (
                    SELECT 1 FROM job_items j 
                    WHERE j.job_number = run_sheet_jobs.job_number
                )
            """)
            
            self.results['jobs_synced'] = cursor.rowcount
            conn.commit()
            conn.close()
            
            elapsed = time.time() - start_time
            self.log(f"   ✅ Synced pay data for {self.results['jobs_synced']} jobs in {elapsed:.2f}s")
            return True
            
        except Exception as e:
            self.log(f"   ❌ Pay sync failed: {e}")
            self.results['errors'].append(f"Pay sync: {e}")
            return False
    
    def generate_report(self):
        """Phase 4: Generate summary report"""
        self.log("📊 Phase 4: Generating report...")
        
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=5.0)
            cursor = conn.cursor()
            
            # Get summary statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_jobs,
                    COUNT(pay_amount) as jobs_with_pay,
                    ROUND(AVG(pay_amount), 2) as avg_pay,
                    MAX(date) as latest_runsheet
                FROM run_sheet_jobs 
                WHERE job_number IS NOT NULL
            """)
            
            total_jobs, jobs_with_pay, avg_pay, latest_runsheet = cursor.fetchone()
            
            cursor.execute("SELECT MAX(week_number || ', ' || tax_year) FROM payslips")
            latest_payslip = cursor.fetchone()[0]
            
            conn.close()
            
            # Print summary
            print("\n" + "=" * 60)
            print("📋 SYNC COMPLETE - SUMMARY REPORT")
            print("=" * 60)
            print(f"📥 Files Downloaded:")
            print(f"   Runsheets: {self.results['runsheets_downloaded']}")
            print(f"   Payslips: {self.results['payslips_downloaded']}")
            print(f"\n📊 Data Imported:")
            print(f"   Runsheet jobs: {self.results['runsheet_jobs_imported']}")
            print(f"   Payslip jobs: {self.results['payslip_jobs_imported']}")
            print(f"\n🔄 Pay Data Synced:")
            print(f"   Jobs updated: {self.results['jobs_synced']}")
            print(f"\n📈 Database Status:")
            print(f"   Total runsheet jobs: {total_jobs:,}")
            print(f"   Jobs with pay data: {jobs_with_pay:,} ({jobs_with_pay/total_jobs*100:.1f}%)")
            print(f"   Average pay per job: £{avg_pay or 0}")
            print(f"   Latest runsheet: {latest_runsheet}")
            print(f"   Latest payslip: Week {latest_payslip}")
            
            if self.results['errors']:
                print(f"\n⚠️  Errors ({len(self.results['errors'])}):")
                for error in self.results['errors']:
                    print(f"   • {error}")
            
            print("=" * 60)
            
            return True
            
        except Exception as e:
            self.log(f"   ❌ Report generation failed: {e}")
            return False
    
    def run(self):
        """Run the complete sync process"""
        start_time = time.time()
        
        # Log to unified sync log
        sync_logger.log_sync_start("Master")
        
        print("🚀 MASTER SYNC SYSTEM")
        print("=" * 60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Setup
        if not self.setup_database():
            return False
        
        # Phase 1: Download
        self.download_files()
        
        # Phase 2: Import
        self.import_runsheets()
        self.import_payslips()
        
        # Phase 2c: Validate addresses (after runsheet import)
        self.validate_addresses()
        
        # Phase 3: Sync
        self.sync_pay_data()
        
        # Phase 4: Report
        self.generate_report()
        
        # Final summary
        elapsed = time.time() - start_time
        success = len(self.results['errors']) == 0
        
        # Log to unified sync log
        sync_logger.log_download_result(
            self.results['runsheets_downloaded'], 
            self.results['payslips_downloaded']
        )
        sync_logger.log_import_result(
            self.results['runsheet_jobs_imported'], 
            self.results['payslip_jobs_imported']
        )
        sync_logger.log_sync_result(self.results['jobs_synced'])
        sync_logger.log_sync_complete(success, elapsed, self.results['errors'] if not success else None)
        
        print(f"\n{'✅ SUCCESS' if success else '⚠️  COMPLETED WITH ERRORS'}")
        print(f"Total time: {elapsed:.1f} seconds")
        print("=" * 60)
        
        return success

if __name__ == "__main__":
    sync = MasterSync()
    success = sync.run()
    sys.exit(0 if success else 1)
