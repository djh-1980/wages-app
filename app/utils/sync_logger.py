"""
Unified Sync Logger
Centralizes all sync logging to a single file with consistent formatting.
"""

import os
import logging
from datetime import datetime
from pathlib import Path

class SyncLogger:
    def __init__(self, log_file='logs/sync.log'):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('sync')
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Create file handler
        handler = logging.FileHandler(self.log_file)
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
    
    def log_sync_start(self, sync_type="Manual"):
        """Log the start of a sync operation."""
        separator = "=" * 60
        self.logger.info(f"\n{separator}")
        self.logger.info(f"🚀 {sync_type.upper()} SYNC STARTED")
        self.logger.info(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(separator)
    
    def log_phase(self, phase_name, status="INFO"):
        """Log a sync phase."""
        if status == "SUCCESS":
            self.logger.info(f"✅ {phase_name}")
        elif status == "ERROR":
            self.logger.error(f"❌ {phase_name}")
        else:
            self.logger.info(f"🔧 {phase_name}")
    
    def log_download_result(self, runsheets=0, payslips=0):
        """Log download results."""
        self.logger.info(f"📥 Downloaded: {runsheets} runsheets, {payslips} payslips")
    
    def log_import_result(self, runsheet_jobs=0, payslip_jobs=0):
        """Log import results."""
        self.logger.info(f"📊 Imported: {runsheet_jobs} runsheet jobs, {payslip_jobs} payslip jobs")
    
    def log_sync_result(self, jobs_updated=0):
        """Log pay sync results."""
        self.logger.info(f"🔄 Pay sync: {jobs_updated} jobs updated")
    
    def log_error(self, error_msg):
        """Log an error."""
        self.logger.error(f"❌ {error_msg}")
    
    def log_sync_complete(self, success=True, duration=0, errors=None):
        """Log sync completion."""
        separator = "=" * 60
        
        if success:
            self.logger.info(f"✅ SYNC COMPLETED SUCCESSFULLY")
        else:
            self.logger.error(f"⚠️ SYNC COMPLETED WITH ERRORS")
            if errors:
                for error in errors:
                    self.logger.error(f"   • {error}")
        
        self.logger.info(f"Total time: {duration:.1f} seconds")
        self.logger.info(separator)
    
    def get_recent_logs(self, lines=50):
        """Get recent log entries."""
        try:
            with open(self.log_file, 'r') as f:
                return f.readlines()[-lines:]
        except FileNotFoundError:
            return ["No sync logs found"]

# Global instance
sync_logger = SyncLogger()
