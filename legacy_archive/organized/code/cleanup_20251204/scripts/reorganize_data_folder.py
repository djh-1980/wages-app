#!/usr/bin/env python3
"""
Data Folder Reorganization Script
Reorganizes the data folder structure for better organization and consistency.
"""

import os
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/danielhanson/CascadeProjects/Wages-App/logs/data_reorganization.log'),
        logging.StreamHandler()
    ]
)

class DataFolderReorganizer:
    def __init__(self, data_path):
        self.data_path = Path(data_path)
        self.backup_path = self.data_path / 'reorganization_backup'
        
        # Month name mappings
        self.month_mapping = {
            '01': '01-January', '02': '02-February', '03': '03-March',
            '04': '04-April', '05': '05-May', '06': '06-June',
            '07': '07-July', '08': '08-August', '09': '09-September',
            '10': '10-October', '11': '11-November', '12': '12-December',
            'January': '01-January', 'February': '02-February', 'March': '03-March',
            'April': '04-April', 'May': '05-May', 'June': '06-June',
            'July': '07-July', 'August': '08-August', 'September': '09-September',
            'October': '10-October', 'November': '11-November', 'December': '12-December'
        }
    
    def create_backup(self):
        """Create a backup of the current data structure"""
        if self.backup_path.exists():
            shutil.rmtree(self.backup_path)
        
        logging.info("Creating backup of current data structure...")
        shutil.copytree(self.data_path, self.backup_path, ignore=shutil.ignore_patterns('reorganization_backup'))
        logging.info(f"Backup created at: {self.backup_path}")
    
    def create_new_structure(self):
        """Create the new organized folder structure"""
        logging.info("Creating new folder structure...")
        
        # Main structure
        new_dirs = [
            'database',
            'database/backups',
            'documents',
            'documents/runsheets',
            'documents/payslips',
            'reports',
            'exports',
            'exports/csv',
            'exports/summaries',
            'processing',
            'processing/queue',
            'processing/temp',
            'processing/failed',
            'processing/manual',
            'uploads',
            'uploads/pending',
            'uploads/processed'
        ]
        
        for dir_path in new_dirs:
            full_path = self.data_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created directory: {dir_path}")
    
    def move_database_files(self):
        """Move database and backup files to database folder"""
        logging.info("Moving database files...")
        
        # Move main database
        db_file = self.data_path / 'payslips.db'
        if db_file.exists():
            shutil.move(str(db_file), str(self.data_path / 'database' / 'payslips.db'))
            logging.info("Moved payslips.db to database folder")
        
        # Move existing backups
        old_backups = self.data_path / 'backups'
        if old_backups.exists():
            for item in old_backups.iterdir():
                if item.is_file():
                    shutil.move(str(item), str(self.data_path / 'database' / 'backups' / item.name))
                elif item.is_dir():
                    # Move subdirectories as well
                    target_dir = self.data_path / 'database' / 'backups' / item.name
                    if any(item.iterdir()):  # If directory has contents
                        shutil.move(str(item), str(target_dir))
                    else:  # If empty, just create it in new location
                        target_dir.mkdir(exist_ok=True)
                        item.rmdir()
            
            # Remove old backups directory
            try:
                old_backups.rmdir()
                logging.info("Moved backup structure to database/backups")
            except OSError:
                logging.warning("Could not remove old backups directory - may contain hidden files")
    
    def reorganize_runsheets(self):
        """Reorganize runsheet files with standardized naming"""
        logging.info("Reorganizing runsheets...")
        
        old_runsheets = self.data_path / 'runsheets'
        new_runsheets = self.data_path / 'documents' / 'runsheets'
        
        if not old_runsheets.exists():
            return
        
        # Process each year
        for year_dir in old_runsheets.iterdir():
            if not year_dir.is_dir() or year_dir.name in ['Archive', 'Failed', 'Manual', 'Processed', 'Processing', 'backup']:
                continue
            
            year = year_dir.name
            new_year_dir = new_runsheets / year
            new_year_dir.mkdir(exist_ok=True)
            
            # Process each month
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                
                month_name = month_dir.name
                if month_name in self.month_mapping:
                    standardized_name = self.month_mapping[month_name]
                    new_month_dir = new_year_dir / standardized_name
                    new_month_dir.mkdir(exist_ok=True)
                    
                    # Move all files
                    for file_path in month_dir.iterdir():
                        if file_path.is_file():
                            shutil.move(str(file_path), str(new_month_dir / file_path.name))
                    
                    logging.info(f"Moved {year}/{month_name} -> {year}/{standardized_name}")
        
        # Handle Archive folder separately
        archive_dir = old_runsheets / 'Archive'
        if archive_dir.exists():
            self.merge_archive_structure(archive_dir, new_runsheets)
        
        # Move special folders to processing
        special_folders = ['Failed', 'Manual', 'Processed', 'Processing']
        for folder_name in special_folders:
            folder_path = old_runsheets / folder_name
            if folder_path.exists():
                target_name = folder_name.lower()
                target_path = self.data_path / 'processing' / target_name
                if target_path.exists():
                    # Merge contents
                    for item in folder_path.iterdir():
                        shutil.move(str(item), str(target_path / item.name))
                else:
                    shutil.move(str(folder_path), str(target_path))
                logging.info(f"Moved {folder_name} to processing/{target_name}")
    
    def merge_archive_structure(self, archive_dir, target_dir):
        """Merge archive structure with main structure"""
        logging.info("Merging archive structure...")
        
        for year_dir in archive_dir.iterdir():
            if not year_dir.is_dir():
                continue
            
            year = year_dir.name
            target_year_dir = target_dir / year
            target_year_dir.mkdir(exist_ok=True)
            
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                
                month_name = month_dir.name
                if month_name in self.month_mapping:
                    standardized_name = self.month_mapping[month_name]
                    target_month_dir = target_year_dir / standardized_name
                    target_month_dir.mkdir(exist_ok=True)
                    
                    # Move all files
                    for file_path in month_dir.iterdir():
                        if file_path.is_file():
                            # Check for duplicates
                            target_file = target_month_dir / file_path.name
                            if target_file.exists():
                                # Add suffix to avoid overwrite
                                base_name = file_path.stem
                                extension = file_path.suffix
                                counter = 1
                                while target_file.exists():
                                    new_name = f"{base_name}_archive_{counter}{extension}"
                                    target_file = target_month_dir / new_name
                                    counter += 1
                            
                            shutil.move(str(file_path), str(target_file))
                    
                    logging.info(f"Merged archive {year}/{month_name} -> {year}/{standardized_name}")
    
    def reorganize_reports(self):
        """Reorganize reports by date"""
        logging.info("Reorganizing reports...")
        
        old_reports = self.data_path / 'reports'
        new_reports = self.data_path / 'reports'
        
        if not old_reports.exists():
            return
        
        # Create temp directory for reorganization
        temp_reports = self.data_path / 'temp_reports'
        temp_reports.mkdir(exist_ok=True)
        
        # Move all files to temp
        for file_path in old_reports.iterdir():
            if file_path.is_file():
                shutil.move(str(file_path), str(temp_reports / file_path.name))
        
        # Organize by date extracted from filename
        for file_path in temp_reports.iterdir():
            if file_path.is_file():
                # Extract date from filename (format: *_YYYYMMDD_*.*)
                filename = file_path.name
                year, month = self.extract_date_from_filename(filename)
                
                if year and month:
                    year_dir = new_reports / year
                    month_dir = year_dir / month
                    month_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(month_dir / filename))
                    logging.info(f"Moved report {filename} to {year}/{month}")
                else:
                    # Move to current year/month if no date found
                    current_date = datetime.now()
                    year_dir = new_reports / str(current_date.year)
                    month_dir = year_dir / f"{current_date.month:02d}-{current_date.strftime('%B')}"
                    month_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(month_dir / filename))
                    logging.info(f"Moved report {filename} to current date folder")
        
        # Remove temp directory
        temp_reports.rmdir()
    
    def extract_date_from_filename(self, filename):
        """Extract year and month from filename"""
        import re
        
        # Look for YYYYMMDD pattern
        date_pattern = r'(\d{4})(\d{2})(\d{2})'
        match = re.search(date_pattern, filename)
        
        if match:
            year = match.group(1)
            month_num = match.group(2)
            month_name = {
                '01': 'January', '02': 'February', '03': 'March',
                '04': 'April', '05': 'May', '06': 'June',
                '07': 'July', '08': 'August', '09': 'September',
                '10': 'October', '11': 'November', '12': 'December'
            }.get(month_num, month_num)
            
            return year, f"{month_num}-{month_name}"
        
        return None, None
    
    def move_output_files(self):
        """Move output files to exports folder"""
        logging.info("Moving output files...")
        
        old_output = self.data_path / 'output'
        if not old_output.exists():
            return
        
        csv_dir = self.data_path / 'exports' / 'csv'
        summaries_dir = self.data_path / 'exports' / 'summaries'
        
        for file_path in old_output.iterdir():
            if file_path.is_file():
                if file_path.suffix == '.csv':
                    shutil.move(str(file_path), str(csv_dir / file_path.name))
                else:
                    shutil.move(str(file_path), str(summaries_dir / file_path.name))
                logging.info(f"Moved {file_path.name} to exports")
        
        # Remove old output directory
        old_output.rmdir()
    
    def reorganize_uploads(self):
        """Reorganize upload folders"""
        logging.info("Reorganizing uploads...")
        
        old_uploads = self.data_path / 'uploads'
        if not old_uploads.exists():
            return
        
        # Map old structure to new
        folder_mapping = {
            'Queue': 'pending',
            'Temp': 'temp',
            'Manual': 'manual'
        }
        
        for old_name, new_name in folder_mapping.items():
            old_path = old_uploads / old_name
            if old_path.exists():
                if new_name == 'temp':
                    target_path = self.data_path / 'processing' / 'temp'
                elif new_name == 'manual':
                    target_path = self.data_path / 'processing' / 'manual'
                else:
                    target_path = self.data_path / 'uploads' / new_name
                
                # Move contents
                for item in old_path.iterdir():
                    shutil.move(str(item), str(target_path / item.name))
                old_path.rmdir()
                logging.info(f"Moved uploads/{old_name} to {target_path.relative_to(self.data_path)}")
    
    def cleanup_old_structure(self):
        """Remove empty old directories"""
        logging.info("Cleaning up old structure...")
        
        old_dirs = ['runsheets', 'output', 'temp', 'backups']
        for dir_name in old_dirs:
            dir_path = self.data_path / dir_name
            if dir_path.exists() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                logging.info(f"Removed empty directory: {dir_name}")
    
    def create_readme(self):
        """Create README documentation for the new structure"""
        readme_content = """# Data Folder Organization

This folder contains all data files for the TVS Wages application, organized for better maintainability and clarity.

## Structure

```
data/
├── database/                 # Database files and backups
│   ├── payslips.db          # Main SQLite database
│   └── backups/             # Database backup files
├── documents/               # Document storage
│   ├── runsheets/          # Runsheet PDFs organized by year/month
│   │   ├── 2021/
│   │   ├── 2022/
│   │   ├── 2023/
│   │   ├── 2024/
│   │   └── 2025/
│   │       ├── 01-January/
│   │       ├── 02-February/
│   │       └── ... (MM-MonthName format)
│   └── payslips/           # Payslip PDFs (if stored separately)
├── reports/                # Generated reports organized by date
│   ├── 2024/
│   │   ├── 10-October/
│   │   └── 11-November/
│   └── 2025/
├── exports/                # Data exports and summaries
│   ├── csv/               # CSV export files
│   └── summaries/         # Summary reports and text files
├── processing/            # File processing workflows
│   ├── queue/            # Files waiting to be processed
│   ├── temp/             # Temporary processing files
│   ├── failed/           # Files that failed processing
│   └── manual/           # Files requiring manual intervention
└── uploads/              # File upload staging
    ├── pending/          # Newly uploaded files
    └── processed/        # Successfully processed uploads
```

## Naming Conventions

- **Years**: 4-digit format (2024, 2025)
- **Months**: MM-MonthName format (01-January, 02-February, etc.)
- **Files**: Original naming preserved where possible

## Backup

A backup of the original structure is maintained in `reorganization_backup/` until you're satisfied with the new organization.

## Maintenance

- Reports are automatically organized by date when generated
- Runsheets follow the year/month structure
- Processing folders should be monitored and cleaned regularly
- Database backups are stored in `database/backups/`
"""
        
        readme_path = self.data_path / 'README.md'
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        
        logging.info("Created README.md documentation")
    
    def run_reorganization(self):
        """Run the complete reorganization process"""
        logging.info("Starting data folder reorganization...")
        
        try:
            # Create backup first
            self.create_backup()
            
            # Create new structure
            self.create_new_structure()
            
            # Move and reorganize files
            self.move_database_files()
            self.reorganize_runsheets()
            self.reorganize_reports()
            self.move_output_files()
            self.reorganize_uploads()
            
            # Cleanup
            self.cleanup_old_structure()
            
            # Create documentation
            self.create_readme()
            
            logging.info("Data folder reorganization completed successfully!")
            logging.info(f"Backup available at: {self.backup_path}")
            
        except Exception as e:
            logging.error(f"Error during reorganization: {e}")
            logging.error("You can restore from backup if needed")
            raise

if __name__ == "__main__":
    data_path = "/Users/danielhanson/CascadeProjects/Wages-App/data"
    reorganizer = DataFolderReorganizer(data_path)
    reorganizer.run_reorganization()
