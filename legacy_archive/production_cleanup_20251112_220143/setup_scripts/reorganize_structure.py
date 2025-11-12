#!/usr/bin/env python3
"""
Reorganize File Structure
Move data directories out of root to create cleaner application structure.
"""

import os
import shutil
from pathlib import Path
import json

def reorganize_to_data_directory():
    """Reorganize files to use a centralized data directory."""
    
    print("🔄 Reorganizing file structure to use data directory...")
    
    # Create main data directory
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    # Define the reorganization mapping
    moves = {
        # Current location -> New location
        'PaySlips': 'data/payslips',
        'RunSheets': 'data/runsheets', 
        'Uploads': 'data/uploads',
        'temp': 'data/temp',
        'backup': 'data/backups',
        'output': 'data/output',
        'reports': 'data/reports'
    }
    
    print("\n📦 Moving directories:")
    for old_path, new_path in moves.items():
        old_dir = Path(old_path)
        new_dir = Path(new_path)
        
        if old_dir.exists():
            print(f"   {old_path}/ → {new_path}/")
            
            # Create parent directory if needed
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            
            # Move the directory
            if new_dir.exists():
                # Merge if destination exists
                print(f"   Merging into existing {new_path}/")
                for item in old_dir.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(old_dir)
                        dest_file = new_dir / rel_path
                        dest_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(item), str(dest_file))
                # Remove empty source directory
                try:
                    shutil.rmtree(old_dir)
                except OSError:
                    pass
            else:
                # Simple move
                shutil.move(str(old_dir), str(new_dir))
        else:
            print(f"   {old_path}/ (not found, creating {new_path}/)")
            new_dir.mkdir(parents=True, exist_ok=True)
    
    # Create enhanced data structure
    print("\n🏗️  Creating enhanced data structure:")
    
    data_structure = {
        'data/payslips': {
            'Manual': 'User uploaded payslips',
            'Processing': 'Files currently being processed',
            'Processed': 'Successfully processed files', 
            'Failed': 'Files that failed processing',
            'Archive': 'Organized by year/month'
        },
        'data/runsheets': {
            'Manual': 'User uploaded runsheets',
            'Processing': 'Files currently being processed',
            'Processed': 'Successfully processed files',
            'Failed': 'Files that failed processing', 
            'Archive': 'Organized by year/month'
        },
        'data/uploads': {
            'Manual': 'Web interface uploads',
            'Temp': 'Temporary upload files',
            'Queue': 'Files queued for processing'
        },
        'data/temp': {
            'downloads': 'Gmail downloads',
            'processing': 'Temporary processing files',
            'failed': 'Failed processing attempts'
        },
        'data/backups': {
            'daily': 'Daily database backups',
            'weekly': 'Weekly backups', 
            'monthly': 'Monthly backups',
            'files': 'File backups'
        }
    }
    
    for base_path, subdirs in data_structure.items():
        base_dir = Path(base_path)
        base_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"   📁 {base_path}/")
        for subdir, description in subdirs.items():
            sub_path = base_dir / subdir
            sub_path.mkdir(exist_ok=True)
            print(f"      └── {subdir}/ ({description})")
            
            # Create year folders for Archive directories
            if subdir == 'Archive':
                for year in range(2021, 2027):
                    year_dir = sub_path / str(year)
                    year_dir.mkdir(exist_ok=True)
                    for month in range(1, 13):
                        month_dir = year_dir / f"{month:02d}"
                        month_dir.mkdir(exist_ok=True)
    
    return True

def update_configuration_files():
    """Update configuration files to reflect new structure."""
    
    print("\n⚙️  Updating configuration files...")
    
    # Update file structure config
    config = {
        "file_structure": {
            "version": "3.0",
            "organized": True,
            "database_driven": True,
            "real_time_processing": True,
            "base_data_dir": "data",
            "directories": {
                "payslips": {
                    "base": "data/payslips",
                    "manual": "data/payslips/Manual",
                    "processing": "data/payslips/Processing",
                    "processed": "data/payslips/Processed", 
                    "failed": "data/payslips/Failed",
                    "archive_pattern": "data/payslips/Archive/{year}/{month:02d}"
                },
                "runsheets": {
                    "base": "data/runsheets",
                    "manual": "data/runsheets/Manual",
                    "processing": "data/runsheets/Processing",
                    "processed": "data/runsheets/Processed",
                    "failed": "data/runsheets/Failed", 
                    "archive_pattern": "data/runsheets/Archive/{year}/{month:02d}"
                },
                "uploads": {
                    "base": "data/uploads",
                    "manual": "data/uploads/Manual",
                    "temp": "data/uploads/Temp",
                    "queue": "data/uploads/Queue"
                },
                "temp": {
                    "downloads": "data/temp/downloads",
                    "processing": "data/temp/processing", 
                    "failed": "data/temp/failed"
                },
                "backups": {
                    "daily": "data/backups/daily",
                    "weekly": "data/backups/weekly",
                    "monthly": "data/backups/monthly",
                    "files": "data/backups/files"
                }
            }
        },
        "processing_workflow": {
            "immediate_processing": True,
            "move_after_processing": True,
            "archive_processed_files": True,
            "retry_failed_files": True,
            "cleanup_temp_files": True,
            "max_processing_time": 300
        },
        "monitoring": {
            "watch_directories": [
                "data/payslips/Manual",
                "data/runsheets/Manual",
                "data/uploads/Manual", 
                "data/uploads/Queue",
                "data/temp/downloads"
            ],
            "file_extensions": [".pdf"],
            "processing_delay": 2
        }
    }
    
    # Ensure config directory exists
    Path('config').mkdir(exist_ok=True)
    
    # Write updated config
    with open('config/file_structure.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("   📄 Updated config/file_structure.json")
    
    # Update .gitignore to exclude data directory
    gitignore_additions = [
        "\n# Data directories (exclude from repository)",
        "data/payslips/",
        "data/runsheets/", 
        "data/uploads/",
        "data/temp/",
        "data/backups/",
        "!data/payslips/.gitkeep",
        "!data/runsheets/.gitkeep",
        "!data/uploads/.gitkeep"
    ]
    
    with open('.gitignore', 'a') as f:
        f.write('\n'.join(gitignore_additions))
    
    print("   📄 Updated .gitignore")

def create_path_constants():
    """Create a constants file for the new paths."""
    
    constants_content = '''"""
File Path Constants
Centralized path definitions for the reorganized structure.
"""

from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# Payslip directories
PAYSLIPS_DIR = DATA_DIR / "payslips"
PAYSLIPS_MANUAL = PAYSLIPS_DIR / "Manual"
PAYSLIPS_PROCESSING = PAYSLIPS_DIR / "Processing"
PAYSLIPS_PROCESSED = PAYSLIPS_DIR / "Processed"
PAYSLIPS_FAILED = PAYSLIPS_DIR / "Failed"
PAYSLIPS_ARCHIVE = PAYSLIPS_DIR / "Archive"

# Runsheet directories
RUNSHEETS_DIR = DATA_DIR / "runsheets"
RUNSHEETS_MANUAL = RUNSHEETS_DIR / "Manual"
RUNSHEETS_PROCESSING = RUNSHEETS_DIR / "Processing"
RUNSHEETS_PROCESSED = RUNSHEETS_DIR / "Processed"
RUNSHEETS_FAILED = RUNSHEETS_DIR / "Failed"
RUNSHEETS_ARCHIVE = RUNSHEETS_DIR / "Archive"

# Upload directories
UPLOADS_DIR = DATA_DIR / "uploads"
UPLOADS_MANUAL = UPLOADS_DIR / "Manual"
UPLOADS_TEMP = UPLOADS_DIR / "Temp"
UPLOADS_QUEUE = UPLOADS_DIR / "Queue"

# Temporary directories
TEMP_DIR = DATA_DIR / "temp"
TEMP_DOWNLOADS = TEMP_DIR / "downloads"
TEMP_PROCESSING = TEMP_DIR / "processing"
TEMP_FAILED = TEMP_DIR / "failed"

# Backup directories
BACKUPS_DIR = DATA_DIR / "backups"
BACKUPS_DAILY = BACKUPS_DIR / "daily"
BACKUPS_WEEKLY = BACKUPS_DIR / "weekly"
BACKUPS_MONTHLY = BACKUPS_DIR / "monthly"
BACKUPS_FILES = BACKUPS_DIR / "files"

# Database
DB_PATH = DATA_DIR / "payslips.db"

def get_archive_path(file_type: str, year: int, month: int) -> Path:
    """Get the archive path for a specific year/month."""
    if file_type.lower() == 'payslip':
        return PAYSLIPS_ARCHIVE / str(year) / f"{month:02d}"
    elif file_type.lower() == 'runsheet':
        return RUNSHEETS_ARCHIVE / str(year) / f"{month:02d}"
    else:
        raise ValueError(f"Unknown file type: {file_type}")

def ensure_directories():
    """Ensure all directories exist."""
    directories = [
        PAYSLIPS_MANUAL, PAYSLIPS_PROCESSING, PAYSLIPS_PROCESSED, PAYSLIPS_FAILED,
        RUNSHEETS_MANUAL, RUNSHEETS_PROCESSING, RUNSHEETS_PROCESSED, RUNSHEETS_FAILED,
        UPLOADS_MANUAL, UPLOADS_TEMP, UPLOADS_QUEUE,
        TEMP_DOWNLOADS, TEMP_PROCESSING, TEMP_FAILED,
        BACKUPS_DAILY, BACKUPS_WEEKLY, BACKUPS_MONTHLY, BACKUPS_FILES
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
'''
    
    # Create app/constants directory
    constants_dir = Path('app/constants')
    constants_dir.mkdir(exist_ok=True)
    
    # Write constants file
    with open(constants_dir / 'paths.py', 'w') as f:
        f.write(constants_content)
    
    # Create __init__.py
    with open(constants_dir / '__init__.py', 'w') as f:
        f.write('from .paths import *\n')
    
    print("   📄 Created app/constants/paths.py")

if __name__ == '__main__':
    print("🏗️  Reorganizing Wages App File Structure")
    print("=" * 50)
    
    # Reorganize directories
    reorganize_to_data_directory()
    
    # Update configuration
    update_configuration_files()
    
    # Create path constants
    create_path_constants()
    
    print("\n✅ File structure reorganization complete!")
    print("\n📋 New Structure:")
    print("   • app/ - Application code only")
    print("   • data/ - All data files organized by type")
    print("   • logs/ - Application logs")
    print("   • config/ - Configuration files")
    print("   • static/ - Web assets")
    print("   • templates/ - HTML templates")
    print("   • scripts/ - Processing scripts")
    
    print("\n🎯 Benefits:")
    print("   • Clean separation of code and data")
    print("   • Better organization and maintenance")
    print("   • Easier deployment and backup")
    print("   • Improved security (data not in code repo)")
    
    print("\n⚠️  Next Steps:")
    print("   1. Update import statements in code")
    print("   2. Update file processor watch directories")
    print("   3. Update periodic sync paths")
    print("   4. Test the reorganized structure")
