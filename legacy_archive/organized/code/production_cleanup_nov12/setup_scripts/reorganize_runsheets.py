#!/usr/bin/env python3
"""
Reorganize RunSheets folder:
1. Move all PDFs to data/runsheets/backup
2. Check each PDF for "Hanson, Daniel" driver name
3. If not found -> move to data/runsheets/manual
4. If found -> extract date, organize by year/month, rename to DH_DD-MM-YYYY.pdf
"""

import PyPDF2
import re
import shutil
from pathlib import Path
from datetime import datetime


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from PDF."""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        print(f"  ⚠️  Error reading {pdf_path.name}: {e}")
        return ""


def has_driver_name(text: str, driver_name: str = "Hanson, Daniel") -> bool:
    """Check if driver name appears anywhere in the PDF text."""
    # Case-insensitive search
    return driver_name.lower() in text.lower()


def extract_date_from_text(text: str) -> str:
    """Extract date in DD/MM/YYYY format from text."""
    # Look for date patterns in the text
    # Try header format first: "Date 25/10/2025"
    date_match = re.search(r'Date\s+(\d{2}/\d{2}/\d{4})', text)
    if date_match:
        return date_match.group(1)
    
    # Try standalone date pattern
    date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', text)
    if date_match:
        return date_match.group(1)
    
    return None


def parse_date(date_str: str) -> datetime:
    """Parse DD/MM/YYYY date string."""
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except:
        return None


def reorganize_runsheets(source_dir: str = "RunSheets", driver_name: str = "Hanson, Daniel", dry_run: bool = False):
    """Reorganize run sheets according to rules."""
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"❌ Error: Directory not found: {source_dir}")
        return
    
    print("=" * 80)
    print("RUN SHEETS REORGANIZATION")
    print("=" * 80)
    print(f"Source directory: {source_path.absolute()}")
    print(f"Driver name filter: {driver_name}")
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will move files)'}")
    print("=" * 80)
    print()
    
    # Create directories
    backup_dir = source_path / "backup"
    manual_dir = source_path / "manual"
    
    if not dry_run:
        backup_dir.mkdir(exist_ok=True)
        manual_dir.mkdir(exist_ok=True)
        print(f"✅ Created directories: backup, manual")
    
    # Find all PDF files (excluding backup and manual directories)
    pdf_files = []
    for pdf_file in source_path.rglob('*.pdf'):
        # Skip if already in backup or manual
        if 'backup' in pdf_file.parts or 'manual' in pdf_file.parts:
            continue
        pdf_files.append(pdf_file)
    
    # Also check for .PDF extension
    for pdf_file in source_path.rglob('*.PDF'):
        if 'backup' in pdf_file.parts or 'manual' in pdf_file.parts:
            continue
        pdf_files.append(pdf_file)
    
    if not pdf_files:
        print("ℹ️  No PDF files found to process")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    print()
    
    # Statistics
    stats = {
        'backed_up': 0,
        'manual': 0,
        'organized': 0,
        'errors': 0
    }
    
    # Step 1: Move all to backup
    print("STEP 1: Moving all PDFs to backup...")
    print("-" * 80)
    
    for pdf_file in pdf_files:
        backup_path = backup_dir / pdf_file.name
        
        # Handle duplicate names
        if backup_path.exists():
            counter = 1
            stem = pdf_file.stem
            while backup_path.exists():
                backup_path = backup_dir / f"{stem}_{counter}.pdf"
                counter += 1
        
        if not dry_run:
            try:
                shutil.move(str(pdf_file), str(backup_path))
                stats['backed_up'] += 1
            except Exception as e:
                print(f"  ❌ Error moving {pdf_file.name}: {e}")
                stats['errors'] += 1
        else:
            print(f"  [DRY RUN] Would move: {pdf_file.name} -> data/backups/{backup_path.name}")
            stats['backed_up'] += 1
    
    print(f"✅ Moved {stats['backed_up']} files to backup")
    print()
    
    # Step 2: Process each PDF from backup
    print("STEP 2: Processing PDFs from backup...")
    print("-" * 80)
    
    # In dry-run mode, process from original locations since files weren't actually moved
    if dry_run:
        backup_pdfs = pdf_files
        print(f"[DRY RUN] Processing {len(backup_pdfs)} files from original locations")
    else:
        backup_pdfs = list(backup_dir.glob('*.pdf')) + list(backup_dir.glob('*.PDF'))
        print(f"Processing {len(backup_pdfs)} files from backup directory")
    
    print()
    
    for pdf_file in backup_pdfs:
        print(f"Processing: {pdf_file.name}")
        
        # Extract text
        text = extract_text_from_pdf(pdf_file)
        
        if not text:
            print(f"  ⚠️  Could not extract text - moving to manual")
            dest = manual_dir / pdf_file.name
            if not dry_run:
                shutil.copy(str(pdf_file), str(dest))
            stats['manual'] += 1
            continue
        
        # Check for driver name
        if not has_driver_name(text, driver_name):
            print(f"  ℹ️  Driver name not found - moving to manual")
            dest = manual_dir / pdf_file.name
            if not dry_run:
                shutil.copy(str(pdf_file), str(dest))
            else:
                print(f"    [DRY RUN] Would copy to: manual/{pdf_file.name}")
            stats['manual'] += 1
            continue
        
        # Extract date
        date_str = extract_date_from_text(text)
        if not date_str:
            print(f"  ⚠️  Date not found - moving to manual")
            dest = manual_dir / pdf_file.name
            if not dry_run:
                shutil.copy(str(pdf_file), str(dest))
            else:
                print(f"    [DRY RUN] Would copy to: manual/{pdf_file.name}")
            stats['manual'] += 1
            continue
        
        # Parse date
        date_obj = parse_date(date_str)
        if not date_obj:
            print(f"  ⚠️  Could not parse date '{date_str}' - moving to manual")
            dest = manual_dir / pdf_file.name
            if not dry_run:
                shutil.copy(str(pdf_file), str(dest))
            else:
                print(f"    [DRY RUN] Would copy to: manual/{pdf_file.name}")
            stats['manual'] += 1
            continue
        
        # Create year/month directory structure
        year = date_obj.year
        month = date_obj.strftime('%B')  # e.g., "January"
        
        year_dir = source_path / str(year)
        month_dir = year_dir / month
        
        if not dry_run:
            month_dir.mkdir(parents=True, exist_ok=True)
        
        # Create new filename: DH_DD-MM-YYYY.pdf
        new_filename = f"DH_{date_obj.strftime('%d-%m-%Y')}.pdf"
        dest_path = month_dir / new_filename
        
        # Handle duplicates
        if dest_path.exists():
            counter = 1
            while dest_path.exists():
                new_filename = f"DH_{date_obj.strftime('%d-%m-%Y')}_{counter}.pdf"
                dest_path = month_dir / new_filename
                counter += 1
        
        print(f"  ✅ Date: {date_str} -> {year}/{month}/{new_filename}")
        
        if not dry_run:
            try:
                shutil.copy(str(pdf_file), str(dest_path))
                stats['organized'] += 1
            except Exception as e:
                print(f"  ❌ Error copying: {e}")
                stats['errors'] += 1
        else:
            print(f"    [DRY RUN] Would copy to: {year}/{month}/{new_filename}")
            stats['organized'] += 1
    
    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total files processed: {len(pdf_files)}")
    print(f"Backed up: {stats['backed_up']}")
    print(f"Organized by date: {stats['organized']}")
    print(f"Moved to manual: {stats['manual']}")
    print(f"Errors: {stats['errors']}")
    print("=" * 80)
    
    if dry_run:
        print()
        print("⚠️  This was a DRY RUN - no files were actually moved.")
        print("Run without --dry-run to perform the actual reorganization.")
    else:
        print()
        print("✅ Reorganization complete!")
        print(f"📁 Backup: {backup_dir}")
        print(f"📁 Manual review needed: {manual_dir}")
        print(f"📁 Organized: {source_path} (by year/month)")


def main():
    """Run reorganization."""
    import sys
    
    source_dir = "RunSheets"
    driver_name = "Hanson, Daniel"
    dry_run = False
    
    for arg in sys.argv[1:]:
        if arg.startswith("--dir="):
            source_dir = arg.split("=")[1]
        elif arg.startswith("--driver="):
            driver_name = arg.split("=")[1]
        elif arg == "--dry-run":
            dry_run = True
        elif arg in ["--help", "-h"]:
            print("Usage: python reorganize_runsheets.py [options]")
            print()
            print("Options:")
            print("  --dir=PATH         Source directory (default: RunSheets)")
            print("  --driver=NAME      Driver name to filter (default: 'Hanson, Daniel')")
            print("  --dry-run          Preview changes without moving files")
            print("  --help, -h         Show this help message")
            print()
            print("Examples:")
            print("  python reorganize_runsheets.py --dry-run")
            print("  python reorganize_runsheets.py")
            print("  python reorganize_runsheets.py --driver='Smith, John'")
            return
    
    # Confirm before running
    if not dry_run:
        print()
        print("⚠️  WARNING: This will reorganize all run sheets!")
        print("It's recommended to run with --dry-run first to preview changes.")
        print()
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            return
    
    reorganize_runsheets(source_dir, driver_name, dry_run)


if __name__ == "__main__":
    main()
