#!/usr/bin/env python3
"""
Organize uploaded runsheet files into the proper year/month folder structure.
Moves files from data/uploads/pending to data/documents/runsheets/YYYY/MM-MonthName/
AND copies to Config.RUNSHEETS_DIR (NAS location) for auto-sync to find.
"""

import sys
from pathlib import Path
import re
import shutil
from datetime import datetime

# Add project root to path for Config import
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from app.config import Config

def parse_runsheet_filename(filename):
    """Extract date from runsheet filename."""
    # Pattern: Runsheet_Daniel_Hanson_DDMMYYYY_timestamp.pdf
    match = re.search(r'Runsheet_.*?_(\d{2})(\d{2})(\d{4})', filename)
    if match:
        day, month, year = match.groups()
        return datetime(int(year), int(month), int(day))
    return None

def get_month_name(month_num):
    """Get month name from month number."""
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    return months[month_num - 1]

def organize_runsheets():
    """Organize runsheet files from uploads/pending to documents/runsheets AND Config.RUNSHEETS_DIR."""
    pending_dir = Path('data/uploads/pending')
    base_dir = Path('data/documents/runsheets')
    runsheets_dir = Path(Config.RUNSHEETS_DIR)
    
    if not pending_dir.exists():
        print(f"Error: {pending_dir} does not exist")
        return
    
    # Find all runsheet PDFs
    runsheet_files = list(pending_dir.glob('Runsheet_*.pdf'))
    
    if not runsheet_files:
        print("No runsheet files found in pending directory")
        return
    
    print(f"Found {len(runsheet_files)} runsheet files to organize")
    print()
    
    moved_count = 0
    failed_count = 0
    
    for file_path in runsheet_files:
        try:
            # Parse date from filename
            date = parse_runsheet_filename(file_path.name)
            if not date:
                print(f"⚠️  Could not parse date from: {file_path.name}")
                failed_count += 1
                continue
            
            # Create target directory structure
            year = date.year
            month_folder = f"{date.month:02d}-{get_month_name(date.month)}"
            target_dir = base_dir / str(year) / month_folder
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Create new filename: DH_DD-MM-YYYY.pdf
            new_filename = f"DH_{date.day:02d}-{date.month:02d}-{date.year}.pdf"
            local_target_path = target_dir / new_filename
            
            # Check if file already exists in local documents
            if local_target_path.exists():
                print(f"⚠️  File already exists: {local_target_path.relative_to(base_dir)}")
                # Remove the duplicate from pending
                file_path.unlink()
                moved_count += 1
            else:
                # Move file to local documents folder
                shutil.move(str(file_path), str(local_target_path))
                print(f"✓ Moved: {file_path.name}")
                print(f"   → {local_target_path.relative_to(base_dir)}")
                moved_count += 1
            
            # ALSO copy to Config.RUNSHEETS_DIR (NAS location) for auto-sync
            if runsheets_dir.exists():
                nas_target_dir = runsheets_dir / str(year) / month_folder
                nas_target_dir.mkdir(parents=True, exist_ok=True)
                nas_target_path = nas_target_dir / new_filename
                
                if not nas_target_path.exists():
                    shutil.copy2(str(local_target_path), str(nas_target_path))
                    print(f"   → Also copied to NAS: {nas_target_path.relative_to(runsheets_dir)}")
                else:
                    print(f"   ℹ️  Already exists on NAS: {nas_target_path.relative_to(runsheets_dir)}")
            else:
                print(f"   ⚠️  NAS directory not accessible: {runsheets_dir}")
            
        except Exception as e:
            print(f"✗ Error processing {file_path.name}: {e}")
            failed_count += 1
    
    print()
    print("=" * 60)
    print(f"Organization complete!")
    print(f"  Files moved: {moved_count}")
    print(f"  Files failed: {failed_count}")
    print("=" * 60)

if __name__ == "__main__":
    organize_runsheets()
