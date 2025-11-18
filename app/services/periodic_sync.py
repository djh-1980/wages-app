"""
Periodic Sync Service
Handles automatic background syncing of recent files only.
Older files can be processed manually when needed.
"""
import logging
import threading
import time
import schedule
import subprocess
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from .sync_helpers import (
    get_latest_runsheet_date,
    get_latest_payslip_week,
    sync_payslips_to_runsheets,
    should_send_notification,
    format_sync_email
)
from ..database import DB_PATH

class PeriodicSyncService:
    def __init__(self):
        self.is_running = False
        self.sync_thread = None
        self.last_sync_time = None
        self.sync_interval_minutes = 15  # Sync every 15 minutes
        self.real_time_processing = False  # Disable file monitoring, use simple sync
        
        # Track what's been processed today/this week to avoid re-checking
        self.last_runsheet_date_processed = None
        self.last_payslip_week_processed = None
        self.last_check_date = None  # Reset tracking daily
        self.runsheet_completed_today = False  # Stop runsheet checks after processing
        self.payslip_completed_this_week = False  # Stop payslip checks after processing
        self.sync_started_today = False  # Track if 18:00 sync has started
        
        # Setup logging
        self.logger = logging.getLogger('periodic_sync')
        handler = logging.FileHandler('logs/periodic_sync.log')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def start_periodic_sync(self):
        """Start the periodic sync service - syncs at 18:00 daily, then every 15 mins until complete."""
        if self.is_running:
            self.logger.info("Periodic sync already running")
            return
        
        self.is_running = True
        self.logger.info(f"Starting periodic sync service (18:00 daily, then every {self.sync_interval_minutes} minutes until complete)")
        
        # Schedule daily sync at 18:00
        schedule.every().day.at("18:00").do(self._start_daily_sync)
        
        # Check if we should start syncing now (if past 18:00 today and not completed)
        now = datetime.now()
        if now.hour >= 18 and not self.runsheet_completed_today:
            # Already past 18:00 today, start interval syncing
            self.logger.info("Past 18:00 - starting sync checks now")
            schedule.every(self.sync_interval_minutes).minutes.do(self.sync_latest).tag('interval-sync')
        
        # Start the scheduler in a separate thread
        self.sync_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.sync_thread.start()
    
    def _start_daily_sync(self):
        """Start daily sync at 18:00 - runs every 15 mins until runsheet processed."""
        # Clear any existing interval jobs
        schedule.clear('interval-sync')
        
        self.logger.info("18:00 - Starting daily sync cycle")
        
        # Run the sync immediately
        self.sync_latest()
        
        # Schedule interval syncing every 15 minutes (will auto-stop when completed)
        schedule.every(self.sync_interval_minutes).minutes.do(self.sync_latest).tag('interval-sync')
    
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
        """Intelligent sync - only downloads and processes NEW files."""
        
        # Reset tracking at midnight each day
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')
        
        if self.last_check_date != current_date:
            self.logger.info(f"New day detected - resetting all tracking (was {self.last_check_date}, now {current_date})")
            self.last_runsheet_date_processed = None
            self.last_check_date = current_date
            self.runsheet_completed_today = False
            self.sync_started_today = False
            
            # Stop any running interval syncs from yesterday
            schedule.clear('interval-sync')
            self.logger.info("Cleared interval syncs - waiting for 18:00 to start new cycle")
        
        # Reset payslip tracking on Tuesdays (start of new week)
        if now.weekday() == 1:  # Tuesday
            latest_payslip_week = get_latest_payslip_week()
            if latest_payslip_week != self.last_payslip_week_processed:
                self.logger.info(f"New week detected - resetting payslip tracking")
                self.payslip_completed_this_week = False
        
        # If runsheet already completed today, stop checking
        if self.runsheet_completed_today:
            self.logger.info("Runsheet already processed today - stopping sync until tomorrow")
            schedule.clear('interval-sync')  # Stop the interval checks
            return
        
        sync_summary = {
            'runsheets_downloaded': 0,
            'runsheets_imported': 0,
            'payslips_downloaded': 0,
            'payslips_imported': 0,
            'jobs_synced': 0,
            'errors': []
        }
        
        try:
            self.logger.info("Starting intelligent sync - checking for new files")
            
            # Step 2: Download new runsheets (only during 18:00-06:00 window)
            if not self.runsheet_completed_today and (now.hour >= 18 or now.hour <= 6):
                self.logger.info(f"Runsheet window ({now.strftime('%H:%M')}) - checking for new runsheets")
                
                # Look for recent runsheets (last 7 days, includes today's)
                self.logger.info(f"Looking for recent runsheets (last 7 days)")
                
                try:
                    runsheet_result = subprocess.run(
                        [sys.executable, 'scripts/production/download_runsheets_gmail.py', '--runsheets', '--recent'],
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if runsheet_result.returncode == 0:
                        # Count new files downloaded
                        output_lines = runsheet_result.stdout.split('\n')
                        for line in output_lines:
                            if 'Downloaded:' in line:
                                sync_summary['runsheets_downloaded'] += 1
                        self.logger.info(f"Downloaded {sync_summary['runsheets_downloaded']} new runsheets")
                except Exception as e:
                    sync_summary['errors'].append(f"Runsheet download failed: {str(e)}")
                    self.logger.error(f"Runsheet download error: {e}")
            elif self.runsheet_completed_today:
                self.logger.info("Runsheet already processed today - skipping until tomorrow")
            
            # Step 3: Download new payslips (Tuesdays 06:00-14:00)
            if not self.payslip_completed_this_week and now.weekday() == 1 and 6 <= now.hour <= 14:  # Tuesday
                self.logger.info("Payslip window (Tuesday 06:00-14:00) - checking for new payslips")
                
                # Get the latest payslip week from database
                latest_payslip_week = get_latest_payslip_week()
                
                # Calculate next week number
                if latest_payslip_week:
                    # Parse "Week X, YYYY" format
                    import re
                    match = re.search(r'Week (\d+), (\d{4})', latest_payslip_week)
                    if match:
                        last_week = int(match.group(1))
                        last_year = int(match.group(2))
                        next_week = last_week + 1
                        # Simple increment (doesn't handle year rollover, but good enough)
                        if next_week > 52:
                            next_week = 1
                            last_year += 1
                        self.logger.info(f"Latest payslip: {latest_payslip_week}, looking for: Week {next_week}, {last_year}")
                        # Search from this Tuesday
                        search_date = now.strftime('%Y/%m/%d')
                    else:
                        search_date = now.strftime('%Y/%m/%d')
                        self.logger.warning(f"Invalid payslip format, using today: {search_date}")
                else:
                    # No payslips yet, search from today
                    search_date = now.strftime('%Y/%m/%d')
                    self.logger.info(f"No payslips in database, searching from: {search_date}")
                
                try:
                    payslip_result = subprocess.run(
                        [sys.executable, 'scripts/production/download_runsheets_gmail.py', '--payslips', f'--date={search_date}'],
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if payslip_result.returncode == 0:
                        output_lines = payslip_result.stdout.split('\n')
                        for line in output_lines:
                            if 'Downloaded:' in line:
                                sync_summary['payslips_downloaded'] += 1
                        self.logger.info(f"Downloaded {sync_summary['payslips_downloaded']} new payslips")
                except Exception as e:
                    sync_summary['errors'].append(f"Payslip download failed: {str(e)}")
                    self.logger.error(f"Payslip download error: {e}")
            elif self.payslip_completed_this_week and now.weekday() == 1 and 6 <= now.hour <= 14:
                self.logger.info("Payslip already processed this week - skipping until next Tuesday")
            
            # Step 4: Import new runsheets (only if downloaded)
            if sync_summary['runsheets_downloaded'] > 0:
                self.logger.info(f"Importing {sync_summary['runsheets_downloaded']} new runsheets")
                try:
                    import_result = subprocess.run(
                        [sys.executable, 'scripts/production/import_run_sheets.py', '--recent', '0'],
                        capture_output=True,
                        text=True,
                        timeout=600  # 10 minutes for large batches
                    )
                    if import_result.returncode == 0:
                        output_lines = import_result.stdout.split('\n')
                        for line in output_lines:
                            if 'Imported' in line and 'jobs' in line:
                                # Extract job count from output
                                import re
                                match = re.search(r'Imported (\d+) jobs', line)
                                if match:
                                    sync_summary['runsheets_imported'] = int(match.group(1))
                        self.logger.info(f"Imported {sync_summary['runsheets_imported']} runsheet jobs")
                        
                        # Mark runsheet as completed for today
                        self.runsheet_completed_today = True
                        self.logger.info("Runsheet processing complete - will not check again until tomorrow")
                except Exception as e:
                    sync_summary['errors'].append(f"Runsheet import failed: {str(e)}")
                    self.logger.error(f"Runsheet import error: {e}")
            
            # Step 5: Import new payslips (only if downloaded)
            if sync_summary['payslips_downloaded'] > 0:
                self.logger.info("Importing new payslips")
                try:
                    payslip_import = subprocess.run(
                        [sys.executable, 'scripts/production/extract_payslips.py', '--recent', '0'],
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if payslip_import.returncode == 0:
                        self.logger.info("Payslip import successful")
                        sync_summary['payslips_imported'] = 1
                        
                        # Step 6: Sync payslip data to runsheets
                        self.logger.info("Syncing payslip data to runsheets")
                        jobs_synced = sync_payslips_to_runsheets()
                        sync_summary['jobs_synced'] = jobs_synced
                        self.logger.info(f"Synced {jobs_synced} jobs with pay data")
                        
                        # Mark payslip as completed for this week
                        self.payslip_completed_this_week = True
                        new_latest = get_latest_payslip_week()
                        self.last_payslip_week_processed = new_latest
                        self.logger.info(f"Payslip processing complete ({new_latest}) - will not check again until next week")
                except Exception as e:
                    sync_summary['errors'].append(f"Payslip import failed: {str(e)}")
                    self.logger.error(f"Payslip import error: {e}")
            
            self.last_sync_time = datetime.now()
            
            # Step 7: Send email notification if anything was processed
            if should_send_notification(sync_summary):
                self._send_sync_notification(sync_summary)
            
            self.logger.info(f"Sync completed: {sync_summary}")
            
        except Exception as e:
            self.logger.error(f"Periodic sync failed: {str(e)}")
            sync_summary['errors'].append(str(e))
    
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
    
    def _send_sync_notification(self, sync_summary):
        """Send email notification about sync results using Gmail API."""
        try:
            from .gmail_notifier import gmail_notifier
            from ..models.settings import SettingsModel
            
            # Get recipient email from settings, fallback to environment, then default
            import os
            recipient_email = SettingsModel.get_setting('userEmail')
            if not recipient_email:
                recipient_email = os.environ.get('NOTIFICATION_EMAIL', 'danielhanson1980@gmail.com')
            
            self.logger.info(f"Sending sync notification to {recipient_email}")
            
            # Send via Gmail API
            success = gmail_notifier.send_sync_notification(sync_summary, recipient_email)
            
            if success:
                self.logger.info("✅ Email notification sent successfully")
            else:
                self.logger.warning("⚠️ Email notification failed to send")
                
            # Also save email to file as backup
            email_html = format_sync_email(sync_summary)
            email_file = Path('logs/sync_notifications') / f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            email_file.parent.mkdir(parents=True, exist_ok=True)
            email_file.write_text(email_html)
            self.logger.info(f"Email backup saved to: {email_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
    
    def force_sync_now(self):
        """Force an immediate sync (for manual trigger)."""
        # Run sync in background thread
        sync_thread = threading.Thread(target=self.sync_latest, daemon=True)
        sync_thread.start()
        return True

# Global instance
periodic_sync_service = PeriodicSyncService()
