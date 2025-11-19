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
        
        # Retry logic with exponential backoff
        self.retry_count = 0
        self.max_retries = 3
        self.retry_delays = [5, 15, 30]  # minutes
        self.last_error = None
        
        # Pause/Resume functionality
        self.is_paused = False
        self.pause_until = None
        
        # Current sync state tracking
        self.current_state = 'idle'  # idle, running, completed, failed, paused
        self.sync_history = []  # Last 7 days of sync results
        self.files_pending = 0
        
        # Configurable sync times (loaded from settings)
        self.sync_start_time = "18:00"
        self.payslip_sync_day = 1  # Tuesday (0=Monday)
        self.payslip_sync_start = 6  # 06:00
        self.payslip_sync_end = 14  # 14:00
        
        # Notification preferences
        self.notify_on_success = True
        self.notify_on_error_only = False
        self.notify_on_new_files_only = False
        
        # Selective sync control
        self.auto_sync_runsheets_enabled = True
        self.auto_sync_payslips_enabled = True
        
        # Setup logging
        self.logger = logging.getLogger('periodic_sync')
        handler = logging.FileHandler('logs/periodic_sync.log')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        
        # Load configuration from settings
        self._load_config()
    
    def _load_config(self):
        """Load sync configuration from settings."""
        try:
            from ..models.settings import SettingsModel
            
            # Load configurable times
            self.sync_start_time = SettingsModel.get_setting('sync_start_time') or "18:00"
            self.sync_interval_minutes = int(SettingsModel.get_setting('sync_interval_minutes') or 15)
            
            # Payslip sync settings
            payslip_day = SettingsModel.get_setting('payslip_sync_day')
            if payslip_day:
                days = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4}
                self.payslip_sync_day = days.get(payslip_day, 1)
            
            self.payslip_sync_start = int(SettingsModel.get_setting('payslip_sync_start') or 6)
            self.payslip_sync_end = int(SettingsModel.get_setting('payslip_sync_end') or 14)
            
            # Notification preferences
            self.notify_on_success = SettingsModel.get_setting('notify_on_success') != 'false'
            self.notify_on_error_only = SettingsModel.get_setting('notify_on_error_only') == 'true'
            self.notify_on_new_files_only = SettingsModel.get_setting('notify_on_new_files_only') == 'true'
            
            # Selective sync
            self.auto_sync_runsheets_enabled = SettingsModel.get_setting('auto_sync_runsheets_enabled') != 'false'
            self.auto_sync_payslips_enabled = SettingsModel.get_setting('auto_sync_payslips_enabled') != 'false'
            
            self.logger.info(f"Config loaded: start={self.sync_start_time}, interval={self.sync_interval_minutes}min")
        except Exception as e:
            self.logger.warning(f"Could not load config, using defaults: {e}")
    
    def start_periodic_sync(self):
        """Start the periodic sync service - syncs at configured time daily, then every N mins until complete."""
        if self.is_running:
            self.logger.info("Periodic sync already running")
            return
        
        self.is_running = True
        self.current_state = 'idle'
        self.logger.info(f"Starting periodic sync service ({self.sync_start_time} daily, then every {self.sync_interval_minutes} minutes until complete)")
        
        # Check if today's runsheet already exists in database
        # Note: Runsheets are for the NEXT day, so if we have today's date or later, we're done
        today_date = datetime.now().strftime('%d/%m/%Y')
        latest_runsheet = get_latest_runsheet_date()
        if latest_runsheet:
            # Convert DD/MM/YYYY to comparable format
            latest_parts = latest_runsheet.split('/')
            today_parts = today_date.split('/')
            latest_comparable = f"{latest_parts[2]}{latest_parts[1]}{latest_parts[0]}"
            today_comparable = f"{today_parts[2]}{today_parts[1]}{today_parts[0]}"
            
            if latest_comparable >= today_comparable:
                self.runsheet_completed_today = True
                self.logger.info(f"Latest runsheet ({latest_runsheet}) is today or later - marking as completed")
        
        # Schedule daily sync at configured time
        schedule.every().day.at(self.sync_start_time).do(self._start_daily_sync)
        
        # Check if we should start syncing now (if past start time today and not completed)
        now = datetime.now()
        start_hour = int(self.sync_start_time.split(':')[0])
        if now.hour >= start_hour and not self.runsheet_completed_today:
            # Already past start time today, start interval syncing
            self.logger.info(f"Past {self.sync_start_time} - starting sync checks now")
            schedule.every(self.sync_interval_minutes).minutes.do(self.sync_latest).tag('interval-sync')
        
        # Start the scheduler in a separate thread
        self.sync_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.sync_thread.start()
    
    def _start_daily_sync(self):
        """Start daily sync at configured time - runs every N mins until runsheet processed."""
        # Clear any existing interval jobs
        schedule.clear('interval-sync')
        
        self.logger.info(f"{self.sync_start_time} - Starting daily sync cycle")
        
        # Reset retry counter for new day
        self.retry_count = 0
        self.last_error = None
        
        # Run the sync immediately
        self.sync_latest()
        
        # Schedule interval syncing every N minutes (will auto-stop when completed)
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
    
    def pause_sync(self, duration_minutes=None):
        """Pause auto-sync temporarily."""
        self.is_paused = True
        self.current_state = 'paused'
        
        if duration_minutes:
            self.pause_until = datetime.now() + timedelta(minutes=duration_minutes)
            self.logger.info(f"Sync paused for {duration_minutes} minutes until {self.pause_until.strftime('%H:%M')}")
            # Schedule auto-resume
            schedule.once().at(self.pause_until.strftime('%H:%M')).do(self.resume_sync).tag('auto-resume')
        else:
            self.pause_until = None
            self.logger.info("Sync paused indefinitely")
    
    def resume_sync(self):
        """Resume auto-sync."""
        self.is_paused = False
        self.pause_until = None
        self.current_state = 'idle'
        schedule.clear('auto-resume')
        self.logger.info("Sync resumed")
        return True
    
    def get_health_status(self):
        """Get comprehensive health check status."""
        try:
            from ..models.settings import SettingsModel
            import os
            from pathlib import Path
            
            # Check Gmail authentication
            token_path = Path('token.json')
            gmail_authenticated = token_path.exists()
            
            # Check database
            db_accessible = Path(DB_PATH).exists()
            
            # Check disk space
            stat = os.statvfs('.')
            free_space_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            disk_space_ok = free_space_gb > 1  # At least 1GB free
            
            return {
                'gmail_authenticated': gmail_authenticated,
                'database_accessible': db_accessible,
                'sync_service_running': self.is_running,
                'sync_service_paused': self.is_paused,
                'disk_space_gb': round(free_space_gb, 2),
                'disk_space_ok': disk_space_ok,
                'last_error': self.last_error,
                'current_state': self.current_state,
                'retry_count': self.retry_count,
                'healthy': gmail_authenticated and db_accessible and disk_space_ok
            }
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def sync_latest(self, dry_run=False):
        """Intelligent sync - only downloads and processes NEW files."""
        
        # Check if paused
        if self.is_paused:
            if self.pause_until and datetime.now() >= self.pause_until:
                self.resume_sync()
            else:
                self.logger.info("Sync is paused - skipping")
                return
        
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
        
        # Check if we've already processed tomorrow's runsheet
        # Runsheets arrive in the evening for the NEXT day
        # So we should check: have we processed tomorrow's runsheet yet?
        tomorrow = (now + timedelta(days=1)).strftime('%d-%m-%Y')
        latest_runsheet = get_latest_runsheet_date()
        
        if latest_runsheet:
            # Convert latest runsheet date to comparable format (handle both / and - separators)
            separator = '/' if '/' in latest_runsheet else '-'
            latest_parts = latest_runsheet.split(separator)
            latest_comparable = f"{latest_parts[2]}{latest_parts[1]}{latest_parts[0]}"
            
            tomorrow_parts = tomorrow.split('-')
            tomorrow_comparable = f"{tomorrow_parts[2]}{tomorrow_parts[1]}{tomorrow_parts[0]}"
            
            # If we already have tomorrow's runsheet, we're done until tomorrow evening
            if latest_comparable >= tomorrow_comparable:
                self.logger.info(f"Already have tomorrow's runsheet ({latest_runsheet}) - stopping sync until tomorrow evening")
                schedule.clear('interval-sync')
                return
            else:
                self.logger.info(f"Latest runsheet is {latest_runsheet}, still need tomorrow's ({tomorrow})")
        else:
            self.logger.info("No runsheets in database yet")
        
        sync_summary = {
            'runsheets_downloaded': 0,
            'runsheets_imported': 0,
            'payslips_downloaded': 0,
            'payslips_imported': 0,
            'jobs_synced': 0,
            'errors': []
        }
        
        try:
            self._sync_start_time = datetime.now()
            self.logger.info("Starting intelligent sync - checking for new files")
            
            # Step 2: Download new runsheets (only during configured window and if enabled)
            start_hour = int(self.sync_start_time.split(':')[0])
            if (self.auto_sync_runsheets_enabled and 
                not self.runsheet_completed_today and 
                (now.hour >= start_hour or now.hour <= 6)):
                self.logger.info(f"Runsheet window ({now.strftime('%H:%M')}) - checking for new runsheets")
                
                # Look for recent runsheets (last 7 days, includes today's)
                self.logger.info(f"Looking for recent runsheets (last 7 days)")
                
                try:
                    if dry_run:
                        self.logger.info("[DRY RUN] Would download runsheets")
                    else:
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
                            self.retry_count = 0  # Reset on success
                        else:
                            raise Exception(f"Download failed with code {runsheet_result.returncode}")
                except Exception as e:
                    sync_summary['errors'].append(f"Runsheet download failed: {str(e)}")
                    self.logger.error(f"Runsheet download error: {e}")
                    self.last_error = str(e)
                    self._handle_retry('runsheet_download')
            elif self.runsheet_completed_today:
                self.logger.info("Runsheet already processed today - skipping until tomorrow")
            
            # Step 3: Download new payslips (configured day and time window, if enabled)
            if (self.auto_sync_payslips_enabled and 
                not self.payslip_completed_this_week and 
                now.weekday() == self.payslip_sync_day and 
                self.payslip_sync_start <= now.hour <= self.payslip_sync_end):
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
            
            sync_end_time = datetime.now()
            self.last_sync_time = sync_end_time
            self.current_state = 'completed' if not sync_summary['errors'] else 'failed'
            
            # Calculate sync duration
            if hasattr(self, '_sync_start_time'):
                sync_summary['duration_seconds'] = int((sync_end_time - self._sync_start_time).total_seconds())
            
            # Add latest data info
            sync_summary['latest_runsheet_date'] = get_latest_runsheet_date()
            sync_summary['latest_payslip_week'] = get_latest_payslip_week()
            
            # Add to sync history
            self._add_to_history(sync_summary)
            
            # Step 7: Send email notification based on preferences
            if self._should_notify(sync_summary):
                self._send_sync_notification(sync_summary)
            
            self.logger.info(f"Sync completed: {sync_summary}")
            
        except Exception as e:
            self.logger.error(f"Periodic sync failed: {str(e)}")
            sync_summary['errors'].append(str(e))
            self.last_error = str(e)
            self.current_state = 'failed'
            self._handle_retry('sync_general')
    
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
    
    def _handle_retry(self, operation):
        """Handle retry logic with exponential backoff."""
        if self.retry_count < self.max_retries:
            delay = self.retry_delays[self.retry_count]
            self.retry_count += 1
            self.logger.info(f"Scheduling retry {self.retry_count}/{self.max_retries} in {delay} minutes for {operation}")
            schedule.every(delay).minutes.do(self.sync_latest).tag('retry-sync')
        else:
            self.logger.error(f"Max retries ({self.max_retries}) reached for {operation}")
            self.retry_count = 0
    
    def _should_notify(self, sync_summary):
        """Determine if notification should be sent based on preferences."""
        has_errors = len(sync_summary['errors']) > 0
        has_new_files = (sync_summary['runsheets_downloaded'] > 0 or 
                        sync_summary['payslips_downloaded'] > 0)
        
        # Always notify on errors if not error-only mode
        if has_errors and not self.notify_on_error_only:
            return True
        
        # Error-only mode
        if self.notify_on_error_only:
            return has_errors
        
        # New files only mode
        if self.notify_on_new_files_only:
            return has_new_files
        
        # Success notifications
        if self.notify_on_success and has_new_files:
            return True
        
        return should_send_notification(sync_summary)
    
    def _add_to_history(self, sync_summary):
        """Add sync result to history (keep last 7 days)."""
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'runsheets': sync_summary['runsheets_downloaded'],
            'payslips': sync_summary['payslips_downloaded'],
            'errors': len(sync_summary['errors']),
            'success': len(sync_summary['errors']) == 0
        }
        self.sync_history.append(history_entry)
        
        # Keep only last 50 entries (roughly 7 days at 15min intervals)
        if len(self.sync_history) > 50:
            self.sync_history = self.sync_history[-50:]
    
    def get_sync_status(self):
        """Get current sync status for API."""
        next_sync = self._estimate_next_sync()
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'pause_until': self.pause_until.isoformat() if self.pause_until else None,
            'current_state': self.current_state,
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'sync_interval_minutes': self.sync_interval_minutes,
            'sync_start_time': self.sync_start_time,
            'next_sync_estimate': next_sync,
            'retry_count': self.retry_count,
            'last_error': self.last_error,
            'sync_history': self.sync_history[-10:],  # Last 10 entries
            'runsheet_completed_today': self.runsheet_completed_today,
            'payslip_completed_this_week': self.payslip_completed_this_week,
            'auto_sync_runsheets_enabled': self.auto_sync_runsheets_enabled,
            'auto_sync_payslips_enabled': self.auto_sync_payslips_enabled
        }
    
    def _estimate_next_sync(self):
        """Estimate when the next sync will occur."""
        try:
            if not self.is_running:
                return None
            
            # Check if we already have tomorrow's runsheet
            now = datetime.now()
            tomorrow = (now + timedelta(days=1)).strftime('%d-%m-%Y')
            latest_runsheet = get_latest_runsheet_date()
            
            if latest_runsheet:
                # Convert dates to comparable format (handle both / and - separators)
                separator = '/' if '/' in latest_runsheet else '-'
                latest_parts = latest_runsheet.split(separator)
                latest_comparable = f"{latest_parts[2]}{latest_parts[1]}{latest_parts[0]}"
                
                tomorrow_parts = tomorrow.split('-')
                tomorrow_comparable = f"{tomorrow_parts[2]}{tomorrow_parts[1]}{tomorrow_parts[0]}"
                
                # If we already have tomorrow's runsheet, next sync is tomorrow at start time
                if latest_comparable >= tomorrow_comparable:
                    tomorrow_date = now + timedelta(days=1)
                    start_time_parts = self.sync_start_time.split(':')
                    next_sync = tomorrow_date.replace(
                        hour=int(start_time_parts[0]),
                        minute=int(start_time_parts[1]),
                        second=0,
                        microsecond=0
                    )
                    return next_sync.isoformat()
            
            # Otherwise, next sync is based on interval
            if self.last_sync_time:
                next_sync = self.last_sync_time + timedelta(minutes=self.sync_interval_minutes)
            else:
                # If no last sync yet, check if we're past start time today
                start_time_parts = self.sync_start_time.split(':')
                start_hour = int(start_time_parts[0])
                start_minute = int(start_time_parts[1])
                
                if now.hour > start_hour or (now.hour == start_hour and now.minute >= start_minute):
                    # Past start time today, next sync is in X minutes
                    next_sync = now + timedelta(minutes=self.sync_interval_minutes)
                else:
                    # Before start time today, next sync is at start time
                    next_sync = now.replace(
                        hour=start_hour,
                        minute=start_minute,
                        second=0,
                        microsecond=0
                    )
            
            return next_sync.isoformat()
        except Exception as e:
            self.logger.error(f"Error estimating next sync: {e}")
            return None
    
    def _send_sync_notification(self, sync_summary):
        """Send email notification about sync results using Gmail API."""
        try:
            from .gmail_notifier import gmail_notifier
            from ..models.settings import SettingsModel
            
            # Get recipient email from settings (priority order: notification_email, userEmail, environment, default)
            import os
            recipient_email = SettingsModel.get_setting('notification_email')
            if not recipient_email:
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
