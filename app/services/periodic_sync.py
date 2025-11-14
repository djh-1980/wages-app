"""
Periodic Sync Service
Handles automatic background syncing of recent files only.
Older files can be processed manually when needed.
"""

import schedule
import time
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import sys
from ..database import DB_PATH
import sqlite3

class PeriodicSyncService:
    def __init__(self):
        self.is_running = False
        self.sync_thread = None
        self.last_sync_time = None
        self.sync_interval_minutes = 30  # Sync every 30 minutes
        self.real_time_processing = False  # Disable file monitoring, use simple sync
        
        # Setup logging
        self.logger = logging.getLogger('periodic_sync')
        handler = logging.FileHandler('logs/periodic_sync.log')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def start_periodic_sync(self):
        """Start the periodic sync service - syncs latest runsheet + payslip every 30 mins."""
        if self.is_running:
            self.logger.info("Periodic sync already running")
            return
        
        self.is_running = True
        self.logger.info(f"Starting periodic sync service (every {self.sync_interval_minutes} minutes)")
        
        # Schedule the sync job
        schedule.every(self.sync_interval_minutes).minutes.do(self.sync_latest)
        
        # Start the scheduler in a separate thread
        self.sync_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.sync_thread.start()
    
    def stop_periodic_sync(self):
        """Stop the periodic sync service."""
        self.is_running = False
        schedule.clear()
        self.logger.info("Periodic sync service stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop."""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def sync_latest(self):
        """Sync latest runsheet and payslip from Gmail."""
        try:
            self.logger.info("Starting periodic sync - downloading latest files from Gmail")
            
            # Download latest runsheet
            runsheet_result = subprocess.run(
                [sys.executable, 'scripts/production/download_runsheets_gmail.py', '--runsheets', '--recent'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Download latest payslip
            payslip_result = subprocess.run(
                [sys.executable, 'scripts/production/download_runsheets_gmail.py', '--payslips', '--recent'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Import any new files (modified today)
            import_result = subprocess.run(
                [sys.executable, 'scripts/production/import_run_sheets.py', '--recent', '0'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Import payslips
            payslip_import = subprocess.run(
                [sys.executable, 'scripts/production/extract_payslips.py', '--recent', '0'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            self.last_sync_time = datetime.now()
            self.logger.info(f"Periodic sync completed at {self.last_sync_time}")
            
        except Exception as e:
            self.logger.error(f"Periodic sync failed: {str(e)}")
    
    def _should_sync(self):
        """Determine if sync is needed based on time and data patterns."""
        now = datetime.now()
        
        # Always sync if it's been more than 2 hours
        if self.last_sync_time is None or (now - self.last_sync_time).total_seconds() > 7200:
            return True
        
        # Skip sync during night hours (11 PM - 6 AM)
        if now.hour >= 23 or now.hour <= 6:
            return False
        
        # More frequent sync during business hours (7 AM - 6 PM)
        if 7 <= now.hour <= 18:
            return True
        
        # Less frequent sync during evening hours
        if (now - self.last_sync_time).total_seconds() > 3600:  # 1 hour
            return True
        
        return False
    
    def _sync_recent_payslips(self):
        """Sync and immediately process payslips newer than the latest in database."""
        try:
            self.logger.info("Syncing payslips newer than latest database record...")
            
            # Get the most recent payslip date from database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(pay_date) FROM payslips WHERE pay_date IS NOT NULL AND pay_date != ''")
            last_payslip_result = cursor.fetchone()
            conn.close()
            
            # Calculate search date based on database content
            if last_payslip_result and last_payslip_result[0]:
                # Convert DD/MM/YYYY to date object and search from that date
                last_date_parts = last_payslip_result[0].split('/')
                if len(last_date_parts) == 3:
                    last_date = datetime(int(last_date_parts[2]), int(last_date_parts[1]), int(last_date_parts[0]))
                    # Search from the day of the last payslip (inclusive) to catch any missed files
                    search_date = last_date.strftime('%Y/%m/%d')
                    self.logger.info(f"Latest payslip in database: {last_payslip_result[0]}, searching from: {search_date}")
                else:
                    # Invalid date format, use fallback
                    search_date = (datetime.now() - timedelta(days=self.fallback_days)).strftime('%Y/%m/%d')
                    self.logger.warning(f"Invalid date format in database, using {self.fallback_days}-day fallback")
            else:
                # No payslips in database, use fallback period
                search_date = (datetime.now() - timedelta(days=self.fallback_days)).strftime('%Y/%m/%d')
                self.logger.info(f"No payslips in database, searching last {self.fallback_days} days from: {search_date}")
            
            self.logger.info(f"Downloading payslips from {search_date}...")
            
            # Run Gmail download for recent payslips with real-time processing
            download_process = subprocess.run([
                sys.executable, 
                'scripts/production/download_runsheets_gmail.py', 
                '--payslips', 
                f'--date={search_date}',
                '--auto-process'  # Enable immediate processing if supported
            ], capture_output=True, text=True, timeout=300)
            
            if download_process.returncode == 0:
                self.logger.info("Payslips downloaded successfully, processing...")
                
                # Immediately process downloaded payslips
                extract_process = subprocess.run([
                    sys.executable, 
                    'scripts/production/extract_payslips.py', 
                    '--recent', str(self.fallback_days),
                    '--quiet'  # Reduce logging noise for periodic runs
                ], capture_output=True, text=True, timeout=180)
                
                if extract_process.returncode == 0:
                    # Count processed files from output
                    output_lines = extract_process.stdout.split('\n')
                    processed_count = sum(1 for line in output_lines if 'processed' in line.lower())
                    
                    self.logger.info(f"Recent payslips synced and processed successfully ({processed_count} files)")
                    return True
                else:
                    self.logger.warning(f"Payslip processing failed: {extract_process.stderr}")
                    return False
            else:
                # Check if it's just "no new files" vs actual error
                if "No new" in download_process.stdout or "0 files" in download_process.stdout:
                    self.logger.info("No new payslips to download")
                    return True  # Not an error, just no new files
                else:
                    self.logger.warning(f"Payslip download failed: {download_process.stderr}")
                    return False
            
        except Exception as e:
            self.logger.error(f"Recent payslip sync failed: {str(e)}")
            return False
    
    def _sync_recent_runsheets(self):
        """Sync and immediately process runsheets newer than the latest in database."""
        try:
            self.logger.info("Syncing runsheets newer than latest database record...")
            
            # Get the most recent runsheet date from database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM run_sheet_jobs WHERE date IS NOT NULL AND date != ''")
            last_runsheet_result = cursor.fetchone()
            conn.close()
            
            # Determine search strategy based on database content
            if last_runsheet_result and last_runsheet_result[0]:
                # Convert DD/MM/YYYY to date object
                last_date_parts = last_runsheet_result[0].split('/')
                if len(last_date_parts) == 3:
                    last_date = datetime(int(last_date_parts[2]), int(last_date_parts[1]), int(last_date_parts[0]))
                    # Search from the day of the last runsheet (inclusive)
                    search_date = last_date.strftime('%Y/%m/%d')
                    self.logger.info(f"Latest runsheet in database: {last_runsheet_result[0]}, searching from: {search_date}")
                    
                    # Use date-based search instead of --recent
                    download_args = [
                        sys.executable, 
                        'scripts/production/download_runsheets_gmail.py', 
                        '--runsheets', 
                        f'--date={search_date}',
                        '--auto-process'
                    ]
                else:
                    # Invalid date format, use recent fallback
                    self.logger.warning("Invalid date format in database, using recent fallback")
                    download_args = [
                        sys.executable, 
                        'scripts/production/download_runsheets_gmail.py', 
                        '--runsheets', 
                        '--recent',
                        '--auto-process'
                    ]
            else:
                # No runsheets in database, use recent search
                self.logger.info(f"No runsheets in database, using recent search (last {self.fallback_days} days)")
                download_args = [
                    sys.executable, 
                    'scripts/production/download_runsheets_gmail.py', 
                    '--runsheets', 
                    '--recent',
                    '--auto-process'
                ]
            
            # Run Gmail download for runsheets
            download_process = subprocess.run(
                download_args, 
                capture_output=True, text=True, timeout=300
            )
            
            if download_process.returncode == 0:
                self.logger.info("Runsheets downloaded successfully, processing...")
                
                # Immediately process downloaded runsheets
                import_process = subprocess.run([
                    sys.executable, 
                    'scripts/production/import_run_sheets.py', 
                    '--recent', str(self.fallback_days),
                    '--quiet'  # Reduce logging noise for periodic runs
                ], capture_output=True, text=True, timeout=300)
                
                if import_process.returncode == 0:
                    # Count processed files from output
                    output_lines = import_process.stdout.split('\n')
                    processed_count = sum(1 for line in output_lines if 'imported' in line.lower() or 'processed' in line.lower())
                    
                    self.logger.info(f"Recent runsheets synced and processed successfully ({processed_count} files)")
                    return True
                else:
                    self.logger.warning(f"Runsheet processing failed: {import_process.stderr}")
                    return False
            else:
                # Check if it's just "no new files" vs actual error
                if "No new" in download_process.stdout or "0 files" in download_process.stdout:
                    self.logger.info("No new runsheets to download")
                    return True  # Not an error, just no new files
                else:
                    self.logger.warning(f"Runsheet download failed: {download_process.stderr}")
                    return False
            
        except Exception as e:
            self.logger.error(f"Recent runsheet sync failed: {str(e)}")
            return False
    
    def get_sync_status(self):
        """Get current sync status for API."""
        next_sync = self._estimate_next_sync()
        return {
            'is_running': self.is_running,
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'sync_interval_minutes': self.sync_interval_minutes,
            'next_sync_estimate': next_sync
        }
    
    def _estimate_next_sync(self):
        """Estimate when the next sync will occur."""
        if not self.is_running:
            return None
        
        # If we have a last sync time, calculate from that
        if self.last_sync_time:
            next_sync = self.last_sync_time + timedelta(minutes=self.sync_interval_minutes)
        else:
            # If no last sync yet, estimate from now
            next_sync = datetime.now() + timedelta(minutes=self.sync_interval_minutes)
        
        return next_sync.isoformat()
    
    def force_sync_now(self):
        """Force an immediate sync (for manual trigger)."""
        # Run sync in background thread
        sync_thread = threading.Thread(target=self.sync_latest, daemon=True)
        sync_thread.start()
        return True

# Global instance
periodic_sync_service = PeriodicSyncService()
