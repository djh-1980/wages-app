#!/usr/bin/env python3
"""
Enhanced File Structure Setup for Database-Driven Sync
Creates optimized directory structure for real-time processing.
"""

import os
from pathlib import Path
import shutil

def setup_enhanced_file_structure():
    """Setup enhanced file structure for database-driven sync."""
    
    base_dirs = {
        'PaySlips': {
            'description': 'Payslip files organized by year/month',
            'subdirs': [
                'Manual',           # User manually uploaded files
                'Processing',       # Files being processed
                'Processed',        # Successfully processed files
                'Failed',          # Files that failed processing
                '2021', '2022', '2023', '2024', '2025', '2026'
            ]
        },
        'RunSheets': {
            'description': 'Runsheet files organized by year/month', 
            'subdirs': [
                'Manual',           # User manually uploaded files
                'Processing',       # Files being processed
                'Processed',        # Successfully processed files
                'Failed',          # Files that failed processing
                '2021', '2022', '2023', '2024', '2025', '2026'
            ]
        },
        'Uploads': {
            'description': 'Temporary upload staging area',
            'subdirs': [
                'Manual',           # Manual uploads via web interface
                'Temp',            # Temporary files during upload
                'Queue'            # Files queued for processing
            ]
        },
        'logs': {
            'description': 'Application and processing logs',
            'subdirs': [
                'sync',            # Periodic sync logs
                'processing',      # File processing logs
                'errors',          # Error logs
                'archive'          # Archived old logs
            ]
        }
    }
    
    print("🔧 Setting up enhanced file structure for database-driven sync...")
    
    # Create main directories and subdirectories
    for main_dir, config in base_dirs.items():
        main_path = Path(main_dir)
        main_path.mkdir(exist_ok=True)
        print(f"📁 {main_dir}/ - {config['description']}")
        
        for subdir in config['subdirs']:
            sub_path = main_path / subdir
            sub_path.mkdir(exist_ok=True)
            print(f"   └── {subdir}/")
            
            # Create month subdirectories for year folders
            if subdir.isdigit() and int(subdir) >= 2021:
                for month in range(1, 13):
                    month_path = sub_path / f"{month:02d}"
                    month_path.mkdir(exist_ok=True)
    
    # Standardize existing manual folders
    print("\n🔄 Standardizing existing manual folders...")
    
    # Fix RunSheets manual folder case
    old_manual = Path('RunSheets/manual')
    new_manual = Path('RunSheets/Manual')
    if old_manual.exists() and not new_manual.exists():
        print(f"   Moving {old_manual} → {new_manual}")
        shutil.move(str(old_manual), str(new_manual))
    elif old_manual.exists() and new_manual.exists():
        # Merge contents if both exist
        print(f"   Merging {old_manual} into {new_manual}")
        for item in old_manual.iterdir():
            shutil.move(str(item), str(new_manual / item.name))
        old_manual.rmdir()
    
    # Create .gitkeep files to preserve empty directories
    print("\n📝 Creating .gitkeep files for empty directories...")
    for main_dir in base_dirs.keys():
        for subdir_path in Path(main_dir).rglob('*'):
            if subdir_path.is_dir() and not any(subdir_path.iterdir()):
                gitkeep = subdir_path / '.gitkeep'
                gitkeep.touch()
    
    # Create processing workflow directories
    print("\n⚙️ Setting up processing workflow directories...")
    
    workflow_dirs = [
        'temp/downloads',      # Temporary Gmail downloads
        'temp/processing',     # Files currently being processed
        'temp/failed',         # Failed processing attempts
        'backup/daily',        # Daily backups
        'backup/weekly',       # Weekly backups
        'backup/monthly'       # Monthly backups
    ]
    
    for workflow_dir in workflow_dirs:
        Path(workflow_dir).mkdir(parents=True, exist_ok=True)
        print(f"   📂 {workflow_dir}/")
    
    print("\n✅ Enhanced file structure setup complete!")
    print("\n📋 Structure Summary:")
    print("   • PaySlips/ - Organized by year/month with processing workflow")
    print("   • RunSheets/ - Organized by year/month with processing workflow") 
    print("   • Uploads/ - Staging area for manual uploads")
    print("   • logs/ - Comprehensive logging structure")
    print("   • temp/ - Temporary processing directories")
    print("   • backup/ - Automated backup storage")
    
    return True

def create_processing_config():
    """Create configuration for the enhanced processing workflow."""
    
    config = {
        "file_structure": {
            "version": "2.0",
            "database_driven": True,
            "real_time_processing": True,
            "directories": {
                "payslips": {
                    "base": "PaySlips",
                    "manual": "PaySlips/Manual",
                    "processing": "PaySlips/Processing", 
                    "processed": "PaySlips/Processed",
                    "failed": "PaySlips/Failed",
                    "archive_pattern": "PaySlips/{year}/{month:02d}"
                },
                "runsheets": {
                    "base": "RunSheets",
                    "manual": "RunSheets/Manual",
                    "processing": "RunSheets/Processing",
                    "processed": "RunSheets/Processed", 
                    "failed": "RunSheets/Failed",
                    "archive_pattern": "RunSheets/{year}/{month:02d}"
                },
                "temp": {
                    "downloads": "temp/downloads",
                    "processing": "temp/processing",
                    "failed": "temp/failed"
                }
            }
        },
        "processing_workflow": {
            "immediate_processing": True,
            "move_after_processing": True,
            "retry_failed_files": True,
            "cleanup_temp_files": True,
            "max_processing_time": 300
        },
        "monitoring": {
            "watch_directories": [
                "PaySlips/Manual",
                "RunSheets/Manual", 
                "Uploads/Manual",
                "temp/downloads"
            ],
            "file_extensions": [".pdf"],
            "processing_delay": 2
        }
    }
    
    import json
    with open('config/file_structure.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("📄 Created processing configuration: config/file_structure.json")

if __name__ == '__main__':
    # Create config directory
    Path('config').mkdir(exist_ok=True)
    
    # Setup enhanced structure
    setup_enhanced_file_structure()
    
    # Create processing config
    create_processing_config()
    
    print("\n🎉 Enhanced file structure ready for database-driven sync!")
