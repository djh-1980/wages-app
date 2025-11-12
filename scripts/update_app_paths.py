#!/usr/bin/env python3
"""
Application Path Update Script
Updates hardcoded paths in the application code to match the new organized data folder structure.
"""

import os
import re
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/danielhanson/CascadeProjects/Wages-App/logs/path_updates.log'),
        logging.StreamHandler()
    ]
)

class AppPathUpdater:
    def __init__(self, app_path):
        self.app_path = Path(app_path)
        
        # Path mappings from old to new structure
        self.path_mappings = {
            # Database paths
            'data/payslips.db': 'data/database/payslips.db',
            
            # Old manual upload paths to new processing structure
            'data/payslips/Manual': 'data/processing/manual',
            'data/runsheets/Manual': 'data/processing/manual',
            'data/uploads/Manual': 'data/uploads/pending',
            
            # Processing paths
            'data/payslips/Processing': 'data/processing/queue',
            'data/runsheets/Processing': 'data/processing/queue',
            'data/uploads/Queue': 'data/uploads/pending',
            'data/uploads/Temp': 'data/processing/temp',
            
            # Download and temp paths
            'data/temp/downloads': 'data/processing/temp',
            'data/temp/processing': 'data/processing/temp',
            'data/temp/failed': 'data/processing/failed',
            
            # General data paths that need updating
            'data/payslips': 'data/documents/payslips',
            'data/runsheets': 'data/documents/runsheets',
            'data/uploads': 'data/uploads',
            'data/output': 'data/exports',
            'data/reports': 'data/reports',
            'data/backups': 'data/database/backups'
        }
    
    def update_file_paths(self, file_path):
        """Update paths in a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            updated_count = 0
            
            # Update each path mapping
            for old_path, new_path in self.path_mappings.items():
                # Use word boundaries to avoid partial matches
                pattern = re.compile(r'\b' + re.escape(old_path) + r'\b')
                matches = pattern.findall(content)
                if matches:
                    content = pattern.sub(new_path, content)
                    updated_count += len(matches)
                    logging.info(f"  Updated {len(matches)} instances of '{old_path}' -> '{new_path}'")
            
            # Write back if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logging.info(f"Updated {file_path.relative_to(self.app_path)} ({updated_count} changes)")
                return updated_count
            
            return 0
            
        except Exception as e:
            logging.error(f"Error updating {file_path}: {e}")
            return 0
    
    def update_config_file(self):
        """Update the main config file with new paths"""
        config_file = self.app_path / 'app' / 'config.py'
        if not config_file.exists():
            logging.warning("Config file not found")
            return
        
        logging.info("Updating config.py...")
        
        try:
            with open(config_file, 'r') as f:
                content = f.read()
            
            # Update database path
            content = re.sub(
                r"DATABASE_PATH = os\.environ\.get\('DATABASE_PATH'\) or 'data/payslips\.db'",
                "DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'data/database/payslips.db'",
                content
            )
            
            # Update backup directory
            content = re.sub(
                r"DATABASE_BACKUP_DIR = os\.environ\.get\('BACKUP_DIR'\) or 'Backups'",
                "DATABASE_BACKUP_DIR = os.environ.get('BACKUP_DIR') or 'data/database/backups'",
                content
            )
            
            with open(config_file, 'w') as f:
                f.write(content)
            
            logging.info("Updated config.py with new paths")
            
        except Exception as e:
            logging.error(f"Error updating config.py: {e}")
    
    def update_database_module(self):
        """Update the database module"""
        db_file = self.app_path / 'app' / 'database.py'
        if not db_file.exists():
            logging.warning("Database module not found")
            return
        
        logging.info("Updating database.py...")
        self.update_file_paths(db_file)
    
    def update_service_files(self):
        """Update service files"""
        services_dir = self.app_path / 'app' / 'services'
        if not services_dir.exists():
            logging.warning("Services directory not found")
            return
        
        logging.info("Updating service files...")
        for py_file in services_dir.glob('*.py'):
            self.update_file_paths(py_file)
    
    def update_route_files(self):
        """Update route files"""
        routes_dir = self.app_path / 'app' / 'routes'
        if not routes_dir.exists():
            logging.warning("Routes directory not found")
            return
        
        logging.info("Updating route files...")
        for py_file in routes_dir.glob('*.py'):
            self.update_file_paths(py_file)
    
    def update_script_files(self):
        """Update script files"""
        scripts_dir = self.app_path / 'scripts'
        if not scripts_dir.exists():
            logging.warning("Scripts directory not found")
            return
        
        logging.info("Updating script files...")
        for py_file in scripts_dir.glob('*.py'):
            # Skip the reorganization and cleanup scripts we just created
            if py_file.name in ['reorganize_data_folder.py', 'cleanup_data_folder.py', 'update_app_paths.py']:
                continue
            self.update_file_paths(py_file)
    
    def create_path_constants_file(self):
        """Create a centralized path constants file"""
        constants_file = self.app_path / 'app' / 'constants' / 'paths.py'
        constants_file.parent.mkdir(exist_ok=True)
        
        content = '''"""
Path Constants for TVS Wages Application
Centralized path definitions for the organized data folder structure.
"""

from pathlib import Path

# Base paths
BASE_DATA_DIR = Path("data")
DATABASE_DIR = BASE_DATA_DIR / "database"
DOCUMENTS_DIR = BASE_DATA_DIR / "documents"
EXPORTS_DIR = BASE_DATA_DIR / "exports"
PROCESSING_DIR = BASE_DATA_DIR / "processing"
REPORTS_DIR = BASE_DATA_DIR / "reports"
UPLOADS_DIR = BASE_DATA_DIR / "uploads"

# Database paths
DATABASE_FILE = DATABASE_DIR / "payslips.db"
DATABASE_BACKUPS_DIR = DATABASE_DIR / "backups"

# Document paths
RUNSHEETS_DIR = DOCUMENTS_DIR / "runsheets"
PAYSLIPS_DIR = DOCUMENTS_DIR / "payslips"

# Export paths
CSV_EXPORTS_DIR = EXPORTS_DIR / "csv"
SUMMARY_EXPORTS_DIR = EXPORTS_DIR / "summaries"

# Processing workflow paths
PROCESSING_QUEUE_DIR = PROCESSING_DIR / "queue"
PROCESSING_TEMP_DIR = PROCESSING_DIR / "temp"
PROCESSING_FAILED_DIR = PROCESSING_DIR / "failed"
PROCESSING_MANUAL_DIR = PROCESSING_DIR / "manual"
PROCESSING_PROCESSED_DIR = PROCESSING_DIR / "processed"

# Upload paths
UPLOADS_PENDING_DIR = UPLOADS_DIR / "pending"
UPLOADS_PROCESSED_DIR = UPLOADS_DIR / "processed"

# Legacy compatibility - these should be gradually phased out
LEGACY_PATHS = {
    "payslips_db": str(DATABASE_FILE),
    "manual_uploads": str(PROCESSING_MANUAL_DIR),
    "temp_processing": str(PROCESSING_TEMP_DIR),
    "failed_processing": str(PROCESSING_FAILED_DIR)
}

# Notification files
NEW_RUNSHEETS_NOTIFICATION = BASE_DATA_DIR / "new_runsheets.json"

def ensure_directories():
    """Ensure all required directories exist."""
    directories = [
        DATABASE_DIR, DATABASE_BACKUPS_DIR,
        RUNSHEETS_DIR, PAYSLIPS_DIR,
        CSV_EXPORTS_DIR, SUMMARY_EXPORTS_DIR,
        PROCESSING_QUEUE_DIR, PROCESSING_TEMP_DIR, PROCESSING_FAILED_DIR,
        PROCESSING_MANUAL_DIR, PROCESSING_PROCESSED_DIR,
        UPLOADS_PENDING_DIR, UPLOADS_PROCESSED_DIR,
        REPORTS_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

def get_archive_path(document_type: str, year: int, month: int) -> Path:
    """Get archive path for a specific document type, year, and month."""
    month_names = [
        "01-January", "02-February", "03-March", "04-April",
        "05-May", "06-June", "07-July", "08-August",
        "09-September", "10-October", "11-November", "12-December"
    ]
    
    if document_type == "runsheets":
        return RUNSHEETS_DIR / str(year) / month_names[month - 1]
    elif document_type == "payslips":
        return PAYSLIPS_DIR / str(year) / month_names[month - 1]
    else:
        raise ValueError(f"Unknown document type: {document_type}")

def get_report_path(year: int, month: int) -> Path:
    """Get report path for a specific year and month."""
    month_names = [
        "01-January", "02-February", "03-March", "04-April",
        "05-May", "06-June", "07-July", "08-August",
        "09-September", "10-October", "11-November", "12-December"
    ]
    
    return REPORTS_DIR / str(year) / month_names[month - 1]
'''
        
        with open(constants_file, 'w') as f:
            f.write(content)
        
        # Create __init__.py for the constants package
        init_file = constants_file.parent / '__init__.py'
        with open(init_file, 'w') as f:
            f.write('"""Constants package for TVS Wages Application."""\n')
        
        logging.info(f"Created path constants file: {constants_file}")
    
    def run_updates(self):
        """Run all path updates"""
        logging.info("Starting application path updates...")
        
        try:
            # Create centralized path constants
            self.create_path_constants_file()
            
            # Update configuration
            self.update_config_file()
            
            # Update database module
            self.update_database_module()
            
            # Update service files
            self.update_service_files()
            
            # Update route files
            self.update_route_files()
            
            # Update script files
            self.update_script_files()
            
            logging.info("Application path updates completed successfully!")
            
            # Provide recommendations
            logging.info("\n=== RECOMMENDATIONS ===")
            logging.info("1. Test the application thoroughly after these changes")
            logging.info("2. Consider gradually migrating to use the new constants.paths module")
            logging.info("3. Update any external scripts or configurations")
            logging.info("4. Run the application and check for any path-related errors")
            logging.info("========================")
            
        except Exception as e:
            logging.error(f"Error during path updates: {e}")
            raise

if __name__ == "__main__":
    app_path = "/Users/danielhanson/CascadeProjects/Wages-App"
    updater = AppPathUpdater(app_path)
    updater.run_updates()
