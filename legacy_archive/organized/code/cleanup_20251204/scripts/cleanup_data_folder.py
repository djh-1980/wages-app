#!/usr/bin/env python3
"""
Data Folder Cleanup Script
Cleans up system files and optimizes the reorganized data folder structure.
"""

import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/danielhanson/CascadeProjects/Wages-App/logs/data_cleanup.log'),
        logging.StreamHandler()
    ]
)

class DataFolderCleanup:
    def __init__(self, data_path):
        self.data_path = Path(data_path)
        self.backup_excluded = 'reorganization_backup'
    
    def remove_system_files(self):
        """Remove .DS_Store and other system files"""
        logging.info("Removing system files (.DS_Store, Thumbs.db)...")
        
        system_files = ['.DS_Store', 'Thumbs.db', '._.DS_Store']
        removed_count = 0
        
        for root, dirs, files in os.walk(self.data_path):
            # Skip backup directory
            if self.backup_excluded in root:
                continue
                
            for file in files:
                if file in system_files:
                    file_path = Path(root) / file
                    try:
                        file_path.unlink()
                        removed_count += 1
                        logging.info(f"Removed: {file_path.relative_to(self.data_path)}")
                    except Exception as e:
                        logging.warning(f"Could not remove {file_path}: {e}")
        
        logging.info(f"Removed {removed_count} system files")
    
    def optimize_gitkeep_files(self):
        """Remove unnecessary .gitkeep files from directories with content"""
        logging.info("Optimizing .gitkeep files...")
        
        removed_count = 0
        kept_count = 0
        
        for root, dirs, files in os.walk(self.data_path):
            # Skip backup directory
            if self.backup_excluded in root:
                continue
            
            gitkeep_path = Path(root) / '.gitkeep'
            if gitkeep_path.exists():
                # Count non-gitkeep files in directory
                other_files = [f for f in files if f != '.gitkeep']
                
                if other_files:
                    # Directory has content, remove .gitkeep
                    try:
                        gitkeep_path.unlink()
                        removed_count += 1
                        logging.info(f"Removed unnecessary .gitkeep from: {gitkeep_path.parent.relative_to(self.data_path)}")
                    except Exception as e:
                        logging.warning(f"Could not remove {gitkeep_path}: {e}")
                else:
                    # Directory is empty, keep .gitkeep
                    kept_count += 1
                    logging.info(f"Kept .gitkeep in empty directory: {gitkeep_path.parent.relative_to(self.data_path)}")
        
        logging.info(f"Removed {removed_count} unnecessary .gitkeep files, kept {kept_count} for empty directories")
    
    def validate_structure(self):
        """Validate the reorganized structure and provide statistics"""
        logging.info("Validating reorganized structure...")
        
        stats = {
            'database_files': 0,
            'runsheet_files': 0,
            'payslip_files': 0,
            'report_files': 0,
            'export_files': 0,
            'total_size_mb': 0
        }
        
        # Database files
        db_path = self.data_path / 'database'
        if db_path.exists():
            for file_path in db_path.rglob('*'):
                if file_path.is_file():
                    stats['database_files'] += 1
                    stats['total_size_mb'] += file_path.stat().st_size / (1024 * 1024)
        
        # Runsheet files
        runsheets_path = self.data_path / 'documents' / 'runsheets'
        if runsheets_path.exists():
            for file_path in runsheets_path.rglob('*.pdf'):
                if file_path.is_file():
                    stats['runsheet_files'] += 1
                    stats['total_size_mb'] += file_path.stat().st_size / (1024 * 1024)
        
        # Payslip files
        payslips_path = self.data_path / 'documents' / 'payslips'
        if payslips_path.exists():
            for file_path in payslips_path.rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    stats['payslip_files'] += 1
                    stats['total_size_mb'] += file_path.stat().st_size / (1024 * 1024)
        
        # Report files
        reports_path = self.data_path / 'reports'
        if reports_path.exists():
            for file_path in reports_path.rglob('*'):
                if file_path.is_file():
                    stats['report_files'] += 1
                    stats['total_size_mb'] += file_path.stat().st_size / (1024 * 1024)
        
        # Export files
        exports_path = self.data_path / 'exports'
        if exports_path.exists():
            for file_path in exports_path.rglob('*'):
                if file_path.is_file():
                    stats['export_files'] += 1
                    stats['total_size_mb'] += file_path.stat().st_size / (1024 * 1024)
        
        # Log statistics
        logging.info("=== DATA FOLDER STATISTICS ===")
        logging.info(f"Database files: {stats['database_files']}")
        logging.info(f"Runsheet PDFs: {stats['runsheet_files']}")
        logging.info(f"Payslip files: {stats['payslip_files']}")
        logging.info(f"Report files: {stats['report_files']}")
        logging.info(f"Export files: {stats['export_files']}")
        logging.info(f"Total size: {stats['total_size_mb']:.2f} MB")
        logging.info("==============================")
        
        return stats
    
    def check_empty_directories(self):
        """Identify and report empty directories"""
        logging.info("Checking for empty directories...")
        
        empty_dirs = []
        
        for root, dirs, files in os.walk(self.data_path):
            # Skip backup directory
            if self.backup_excluded in root:
                continue
            
            # Check if directory is empty (no files, no subdirectories with files)
            has_content = False
            current_path = Path(root)
            
            # Check for files (excluding .gitkeep)
            non_gitkeep_files = [f for f in files if f != '.gitkeep']
            if non_gitkeep_files:
                has_content = True
            
            # Check subdirectories recursively
            if not has_content:
                for subdir in dirs:
                    subdir_path = current_path / subdir
                    if any(subdir_path.rglob('*')):
                        # Check if any files exist in subdirectories
                        for item in subdir_path.rglob('*'):
                            if item.is_file() and item.name != '.gitkeep':
                                has_content = True
                                break
                        if has_content:
                            break
            
            if not has_content and current_path != self.data_path:
                empty_dirs.append(current_path.relative_to(self.data_path))
        
        if empty_dirs:
            logging.info(f"Found {len(empty_dirs)} empty directories:")
            for empty_dir in empty_dirs:
                logging.info(f"  - {empty_dir}")
        else:
            logging.info("No empty directories found")
        
        return empty_dirs
    
    def create_maintenance_summary(self, stats):
        """Create a maintenance summary report"""
        summary_path = self.data_path / 'MAINTENANCE_SUMMARY.md'
        
        content = f"""# Data Folder Maintenance Summary

Generated on: {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))}

## Structure Statistics

- **Database files**: {stats['database_files']}
- **Runsheet PDFs**: {stats['runsheet_files']}
- **Payslip files**: {stats['payslip_files']}
- **Report files**: {stats['report_files']}
- **Export files**: {stats['export_files']}
- **Total size**: {stats['total_size_mb']:.2f} MB

## Organization Status

✅ **Completed Tasks:**
- System files (.DS_Store) cleaned up
- Unnecessary .gitkeep files removed
- Folder structure validated
- File counts verified

## Maintenance Recommendations

1. **Regular Cleanup**: Run cleanup script monthly to remove system files
2. **Monitor Size**: Database and documents folders will grow over time
3. **Backup Strategy**: Maintain regular backups of database/ folder
4. **Archive Old Data**: Consider archiving runsheets older than 2 years
5. **Processing Folders**: Monitor and clean processing/ folders regularly

## Next Steps

- Consider implementing automated cleanup in the main application
- Set up monitoring for folder sizes
- Create backup automation for critical data
"""
        
        with open(summary_path, 'w') as f:
            f.write(content)
        
        logging.info(f"Created maintenance summary: {summary_path}")
    
    def run_cleanup(self):
        """Run the complete cleanup process"""
        logging.info("Starting data folder cleanup...")
        
        try:
            # Clean up system files
            self.remove_system_files()
            
            # Optimize .gitkeep files
            self.optimize_gitkeep_files()
            
            # Validate structure
            stats = self.validate_structure()
            
            # Check for empty directories
            self.check_empty_directories()
            
            # Create maintenance summary
            self.create_maintenance_summary(stats)
            
            logging.info("Data folder cleanup completed successfully!")
            
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")
            raise

if __name__ == "__main__":
    data_path = "/Users/danielhanson/CascadeProjects/Wages-App/data"
    cleanup = DataFolderCleanup(data_path)
    cleanup.run_cleanup()
