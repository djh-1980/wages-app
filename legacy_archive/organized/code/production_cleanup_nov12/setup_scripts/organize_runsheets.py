#!/usr/bin/env python3
"""
Organize run sheet files into year/month folders based on the date in the PDF.
"""

import PyPDF2
import re
import shutil
from pathlib import Path
from datetime import datetime


def extract_date_from_pdf(pdf_path: Path) -> str:
    """Extract date from PDF run sheet."""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Check first few pages
            for page in reader.pages[:3]:
                text = page.extract_text()
                lines = text.split('\n')
                
                # Look for date in header line
                # Format: "Date 25/10/2025 Depot Warrington Driver..."
                for line in lines[:10]:
                    date_match = re.search(r'Date\s+(\d{2}/\d{2}/\d{4})', line)
                    if date_match:
                        return date_match.group(1)
                    
                    # Also try standalone date pattern
                    date_match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', line)
                    if date_match:
                        return date_match.group(1)
        
        return None
        
    except Exception as e:
        print(f"  ⚠️  Error reading {pdf_path.name}: {e}")
        return None


def parse_date(date_str: str) -> tuple:
    """Parse DD/MM/YYYY date string and return (year, month_name, filename)."""
    try:
        # Parse DD/MM/YYYY
        dt = datetime.strptime(date_str, '%d/%m/%Y')
        month_name = dt.strftime('%B')  # Full month name (e.g., "October")
        filename = dt.strftime('%Y-%m-%d.pdf')  # ISO date format
        return (dt.year, month_name, filename)
    except:
        return None


def organize_runsheets(source_dir: str = "RunSheets", dry_run: bool = False):
    """Organize run sheets into year/month folders."""
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"❌ Error: Directory not found: {source_dir}")
        return
    
    print("=" * 80)
    print("RUN SHEET ORGANIZER")
    print("=" * 80)
    print(f"Source directory: {source_path.absolute()}")
    print(f"Mode: {'DRY RUN (no files will be moved)' if dry_run else 'LIVE (files will be moved)'}")
    print()
    
    # Find all PDF files recursively (including subdirectories)
    pdf_files = list(source_path.rglob('*.pdf')) + list(source_path.rglob('*.PDF'))
    
    if not pdf_files:
        print("ℹ️  No PDF files found in directory or subdirectories")
        return
    
    print(f"Found {len(pdf_files)} PDF files to organize")
    print()
    
    # Process each file
    moved_count = 0
    skipped_count = 0
    error_count = 0
    
    for pdf_file in sorted(pdf_files):
        print(f"📄 {pdf_file.name}")
        
        # Extract date from PDF
        date_str = extract_date_from_pdf(pdf_file)
        
        if not date_str:
            print(f"  ⚠️  Could not extract date - skipping")
            skipped_count += 1
            print()
            continue
        
        print(f"  📅 Date found: {date_str}")
        
        # Parse date
        parsed = parse_date(date_str)
        if not parsed:
            print(f"  ⚠️  Could not parse date - skipping")
            skipped_count += 1
            print()
            continue
        
        year, month_name, new_filename = parsed
        
        # Create target directory structure: data/runsheets/2025/October/
        target_dir = source_path / str(year) / month_name
        target_file = target_dir / new_filename
        
        print(f"  📁 Target: {target_dir.relative_to(source_path)}/{new_filename}")
        
        # Check if file already exists in target
        if target_file.exists():
            print(f"  ⚠️  File already exists in target location - skipping")
            skipped_count += 1
            print()
            continue
        
        if not dry_run:
            try:
                # Create directory if it doesn't exist
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # Move file
                shutil.move(str(pdf_file), str(target_file))
                print(f"  ✅ Moved successfully")
                moved_count += 1
            except Exception as e:
                print(f"  ❌ Error moving file: {e}")
                error_count += 1
        else:
            print(f"  ℹ️  Would move here (dry run)")
            moved_count += 1
        
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Moved: {moved_count}")
    print(f"⚠️  Skipped: {skipped_count}")
    print(f"❌ Errors: {error_count}")
    print()
    
    if dry_run:
        print("ℹ️  This was a DRY RUN. No files were actually moved.")
        print("   Run with --live to actually move the files.")
    else:
        print("✅ Organization complete!")
    
    print("=" * 80)


def show_structure(source_dir: str = "RunSheets"):
    """Show the current directory structure."""
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"❌ Error: Directory not found: {source_dir}")
        return
    
    print()
    print("=" * 80)
    print("CURRENT STRUCTURE")
    print("=" * 80)
    print()
    
    # Show directory tree
    def print_tree(directory: Path, prefix: str = "", is_last: bool = True):
        """Print directory tree."""
        connector = "└── " if is_last else "├── "
        print(f"{prefix}{connector}{directory.name}/")
        
        # Get subdirectories and files
        items = sorted(directory.iterdir(), key=lambda x: (not x.is_dir(), x.name))
        dirs = [item for item in items if item.is_dir()]
        files = [item for item in items if item.is_file() and item.suffix.lower() == '.pdf']
        
        # Print directories
        for i, subdir in enumerate(dirs):
            is_last_dir = (i == len(dirs) - 1) and len(files) == 0
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(subdir, new_prefix, is_last_dir)
        
        # Print PDF files
        for i, file in enumerate(files):
            is_last_file = i == len(files) - 1
            file_connector = "└── " if is_last_file else "├── "
            new_prefix = prefix + ("    " if is_last else "│   ")
            print(f"{new_prefix}{file_connector}{file.name}")
    
    print_tree(source_path)
    print()
    print("=" * 80)


def main():
    """Run organizer."""
    import sys
    
    # Parse arguments
    dry_run = True
    show_tree = False
    source_dir = "RunSheets"
    
    for arg in sys.argv[1:]:
        if arg == "--live":
            dry_run = False
        elif arg == "--tree":
            show_tree = True
        elif arg.startswith("--dir="):
            source_dir = arg.split("=")[1]
        elif arg in ["--help", "-h"]:
            print("Usage: python organize_runsheets.py [options]")
            print()
            print("Options:")
            print("  --live          Actually move files (default is dry run)")
            print("  --tree          Show current directory structure")
            print("  --dir=PATH      Use custom source directory (default: RunSheets)")
            print("  --help, -h      Show this help message")
            print()
            print("Examples:")
            print("  python organize_runsheets.py                    # Dry run")
            print("  python organize_runsheets.py --live             # Actually move files")
            print("  python organize_runsheets.py --tree             # Show structure")
            print("  python organize_runsheets.py --dir=docs/Sheets  # Custom directory")
            return
    
    if show_tree:
        show_structure(source_dir)
    else:
        organize_runsheets(source_dir, dry_run)


if __name__ == "__main__":
    main()
