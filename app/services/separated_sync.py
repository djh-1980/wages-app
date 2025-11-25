"""
Separated Sync Service - Clear runsheet and payslip workflows
"""
import logging
import subprocess
import sys
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from .sync_helpers import (
    get_latest_runsheet_date,
    get_latest_payslip_week,
    sync_payslips_to_runsheets
)
from ..database import DB_PATH

class SeparatedSyncService:
    def __init__(self):
        self.logger = logging.getLogger('separated_sync')
        handler = logging.FileHandler('logs/separated_sync.log')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def runsheet_workflow(self):
        """
        RUNSHEET WORKFLOW
        Step 1: Check if already have tomorrow's runsheet → if yes, stop
        Step 2: Download new runsheets (19:00-06:00 window)
        Step 3: Import downloaded runsheets and stop until tomorrow
        Step 4: Send email notification
        """
        now = datetime.now()
        self.logger.info(f"Starting runsheet workflow at {now.strftime('%H:%M')}")
        
        result = {
            'success': False,
            'step_completed': 0,
            'message': '',
            'runsheets_downloaded': 0,
            'runsheets_imported': 0,
            'should_stop_until_tomorrow': False
        }
        
        try:
            # Step 1: Check if we already have tomorrow's runsheet
            tomorrow = (now + timedelta(days=1)).strftime('%d/%m/%Y')
            latest_runsheet = get_latest_runsheet_date()
            
            self.logger.info(f"Step 1: Checking for tomorrow's runsheet ({tomorrow})")
            
            if latest_runsheet:
                # Convert dates to comparable format
                latest_parts = latest_runsheet.split('/')
                tomorrow_parts = tomorrow.split('/')
                latest_comparable = f"{latest_parts[2]}{latest_parts[1]}{latest_parts[0]}"
                tomorrow_comparable = f"{tomorrow_parts[2]}{tomorrow_parts[1]}{tomorrow_parts[0]}"
                
                if latest_comparable >= tomorrow_comparable:
                    result['step_completed'] = 1
                    result['success'] = True
                    result['should_stop_until_tomorrow'] = True
                    result['message'] = f"Already have tomorrow's runsheet ({latest_runsheet}) - stopping until tomorrow"
                    self.logger.info(result['message'])
                    return result
            
            # Step 2: Check if we're in the download window (19:00-06:00)
            if not (now.hour >= 19 or now.hour <= 6):
                result['step_completed'] = 1
                result['message'] = f"Outside runsheet download window (19:00-06:00). Current time: {now.hour:02d}:00"
                self.logger.info(result['message'])
                return result
            
            self.logger.info("Step 2: Downloading new runsheets")
            
            # Download runsheets
            download_result = subprocess.run([
                sys.executable, 
                'scripts/production/download_runsheets_gmail.py', 
                '--runsheets', 
                '--recent'
            ], capture_output=True, text=True, timeout=120)
            
            if download_result.returncode != 0:
                result['message'] = f"Runsheet download failed: {download_result.stderr}"
                self.logger.error(result['message'])
                return result
            
            # Count downloaded files
            for line in download_result.stdout.split('\n'):
                if 'Downloaded:' in line:
                    result['runsheets_downloaded'] += 1
            
            result['step_completed'] = 2
            self.logger.info(f"Downloaded {result['runsheets_downloaded']} runsheets")
            
            # Step 3: Import downloaded runsheets (only if we downloaded any)
            if result['runsheets_downloaded'] > 0:
                self.logger.info("Step 3: Importing downloaded runsheets")
                
                import_result = subprocess.run([
                    sys.executable, 
                    'scripts/production/import_run_sheets.py', 
                    '--recent', '0'
                ], capture_output=True, text=True, timeout=300)
                
                if import_result.returncode != 0:
                    result['message'] = f"Runsheet import failed: {import_result.stderr}"
                    self.logger.error(result['message'])
                    return result
                
                # Count imported jobs
                for line in import_result.stdout.split('\n'):
                    if 'Imported' in line and 'jobs' in line:
                        import re
                        match = re.search(r'Imported (\d+) jobs', line)
                        if match:
                            result['runsheets_imported'] = int(match.group(1))
                
                result['step_completed'] = 3
                result['should_stop_until_tomorrow'] = True
                self.logger.info(f"Imported {result['runsheets_imported']} runsheet jobs")
            
            # Step 4: Send notification (if we imported anything)
            if result['runsheets_imported'] > 0:
                self.logger.info("Step 4: Sending notification")
                # TODO: Implement notification
                result['step_completed'] = 4
            
            result['success'] = True
            result['message'] = f"Runsheet workflow complete - downloaded {result['runsheets_downloaded']}, imported {result['runsheets_imported']}"
            self.logger.info(result['message'])
            
        except Exception as e:
            result['message'] = f"Runsheet workflow error: {str(e)}"
            self.logger.error(result['message'])
        
        return result
    
    def payslip_workflow(self):
        """
        PAYSLIP WORKFLOW  
        Step 3: Download new payslips (Tuesdays 06:00-14:00 window)
        Step 5: Import downloaded payslips
        Step 6: Sync payslip data to runsheets (match job numbers, add pay)
        Step 7: Send email notification
        """
        now = datetime.now()
        self.logger.info(f"Starting payslip workflow at {now.strftime('%H:%M on %A')}")
        
        result = {
            'success': False,
            'step_completed': 0,
            'message': '',
            'payslips_downloaded': 0,
            'payslips_imported': 0,
            'jobs_synced': 0
        }
        
        try:
            # Step 3: Check if we're in the payslip window (Tuesday 06:00-14:00)
            if now.weekday() != 1:  # Not Tuesday
                result['message'] = f"Not Tuesday - payslips only processed on Tuesdays. Today is {now.strftime('%A')}"
                self.logger.info(result['message'])
                return result
            
            if not (6 <= now.hour <= 14):
                result['message'] = f"Outside payslip window (06:00-14:00). Current time: {now.hour:02d}:00"
                self.logger.info(result['message'])
                return result
            
            self.logger.info("Step 3: Downloading new payslips")
            
            # Download payslips (search for emails from today - payslips arrive on Tuesdays)
            search_date = now.strftime('%Y/%m/%d')
            
            download_result = subprocess.run([
                sys.executable, 
                'scripts/production/download_runsheets_gmail.py', 
                '--payslips', 
                f'--date={search_date}'
            ], capture_output=True, text=True, timeout=120)
            
            if download_result.returncode != 0:
                result['message'] = f"Payslip download failed: {download_result.stderr}"
                self.logger.error(result['message'])
                return result
            
            # Count downloaded files
            for line in download_result.stdout.split('\n'):
                if 'Downloaded:' in line:
                    result['payslips_downloaded'] += 1
            
            result['step_completed'] = 3
            self.logger.info(f"Downloaded {result['payslips_downloaded']} payslips")
            
            # Step 5: Import payslips (check for recent files, not just downloaded)
            self.logger.info("Step 5: Importing payslips")
            
            import_result = subprocess.run([
                sys.executable, 
                'scripts/production/extract_payslips.py', 
                '--recent', '1'  # Check last 24 hours
            ], capture_output=True, text=True, timeout=120)
            
            if import_result.returncode != 0:
                result['message'] = f"Payslip import failed: {import_result.stderr}"
                self.logger.error(result['message'])
                return result
            
            # Check if any payslips were processed
            payslips_processed = 0
            if 'Successfully processed:' in import_result.stdout:
                import re
                match = re.search(r'Successfully processed: (\d+)/', import_result.stdout)
                if match:
                    payslips_processed = int(match.group(1))
            
            result['payslips_imported'] = payslips_processed
            result['step_completed'] = 5
            
            if payslips_processed > 0:
                self.logger.info(f"Imported {payslips_processed} payslips")
            else:
                self.logger.info("No new payslips imported, but checking for unsynced payslips")
            
            # Step 6: Sync payslip data to runsheets (match job numbers, add pay)
            self.logger.info("Step 6: Syncing payslip data to runsheets")
            
            jobs_synced = sync_payslips_to_runsheets()
            result['jobs_synced'] = jobs_synced
            result['step_completed'] = 6
            self.logger.info(f"Synced pay data to {jobs_synced} runsheet jobs")
            
            # Step 7: Send notification
            if result['payslips_imported'] > 0 or result['jobs_synced'] > 0:
                self.logger.info("Step 7: Sending notification")
                # TODO: Implement notification
                result['step_completed'] = 7
            
            result['success'] = True
            result['message'] = f"Payslip workflow complete - imported {result['payslips_imported']}, synced {result['jobs_synced']} jobs"
            self.logger.info(result['message'])
            
        except Exception as e:
            result['message'] = f"Payslip workflow error: {str(e)}"
            self.logger.error(result['message'])
        
        return result
    
    def run_appropriate_workflow(self):
        """Run the appropriate workflow based on current time and day"""
        now = datetime.now()
        
        # Check runsheet workflow first
        runsheet_result = self.runsheet_workflow()
        
        # Check payslip workflow (only on Tuesdays)
        payslip_result = None
        if now.weekday() == 1:  # Tuesday
            payslip_result = self.payslip_workflow()
        
        return {
            'runsheet_result': runsheet_result,
            'payslip_result': payslip_result,
            'timestamp': now.isoformat()
        }

# Global instance
separated_sync_service = SeparatedSyncService()
