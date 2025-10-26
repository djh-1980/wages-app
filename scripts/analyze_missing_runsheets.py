#!/usr/bin/env python3
"""
Analyze RunSheets folder and report missing dates by year.
Scans all PDF files and finds gaps in the date sequence.
"""

import PyPDF2
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


def extract_date_from_pdf(pdf_path: Path) -> str:
    """Extract date from PDF run sheet."""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Check first page
            if len(reader.pages) > 0:
                text = reader.pages[0].extract_text()
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


def parse_date(date_str: str) -> datetime:
    """Parse DD/MM/YYYY date string to datetime object."""
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except:
        return None


def analyze_missing_dates(source_dir: str = "RunSheets", max_gap: int = 30):
    """Analyze run sheets and find missing dates."""
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"❌ Error: Directory not found: {source_dir}")
        return
    
    print("=" * 80)
    print("MISSING RUN SHEETS ANALYZER")
    print("=" * 80)
    print(f"Source directory: {source_path.absolute()}")
    print(f"Max gap to report: {max_gap} days")
    print()
    
    # Find all PDF files recursively
    pdf_files = list(source_path.rglob('*.pdf')) + list(source_path.rglob('*.PDF'))
    
    if not pdf_files:
        print("ℹ️  No PDF files found")
        return
    
    print(f"Found {len(pdf_files)} PDF files")
    print("Extracting dates...")
    print()
    
    # Extract dates from all PDFs
    dates_by_year = defaultdict(list)
    
    for pdf_file in pdf_files:
        date_str = extract_date_from_pdf(pdf_file)
        if date_str:
            date_obj = parse_date(date_str)
            if date_obj:
                dates_by_year[date_obj.year].append(date_obj)
    
    if not dates_by_year:
        print("❌ No valid dates found in PDFs")
        return
    
    # Analyze each year
    for year in sorted(dates_by_year.keys()):
        dates = sorted(dates_by_year[year])
        
        print("=" * 80)
        print(f"YEAR: {year}")
        print("=" * 80)
        print(f"Total run sheets: {len(dates)}")
        print(f"Date range: {dates[0].strftime('%d/%m/%Y')} to {dates[-1].strftime('%d/%m/%Y')}")
        print()
        
        # Find missing dates
        missing_dates = []
        
        for i in range(len(dates) - 1):
            current = dates[i]
            next_date = dates[i + 1]
            diff = (next_date - current).days
            
            # Only report gaps of 1-max_gap days
            if diff > 1 and diff <= max_gap:
                for j in range(1, diff):
                    missing_date = current + timedelta(days=j)
                    missing_dates.append(missing_date)
        
        if missing_dates:
            print(f"⚠️  Missing dates: {len(missing_dates)}")
            print()
            
            # Group by month
            by_month = defaultdict(list)
            for date in missing_dates:
                month_key = date.strftime('%B %Y')
                by_month[month_key].append(date)
            
            for month in sorted(by_month.keys(), key=lambda x: datetime.strptime(x, '%B %Y')):
                month_dates = by_month[month]
                print(f"  📅 {month} ({len(month_dates)} missing days)")
                print("  " + "-" * 40)
                for date in sorted(month_dates):
                    day_name = date.strftime('%A')
                    print(f"    • {date.strftime('%d/%m/%Y')} ({day_name})")
                print()
        else:
            print("✅ No missing dates found (within gap limit)")
            print()
    
    # Overall summary
    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    total_sheets = sum(len(dates_by_year[year]) for year in dates_by_year)
    print(f"Total run sheets analyzed: {total_sheets}")
    print(f"Years covered: {', '.join(str(y) for y in sorted(dates_by_year.keys()))}")
    print("=" * 80)


def main():
    """Run analyzer."""
    import sys
    
    source_dir = "RunSheets"
    max_gap = 30
    
    for arg in sys.argv[1:]:
        if arg.startswith("--dir="):
            source_dir = arg.split("=")[1]
        elif arg.startswith("--max-gap="):
            max_gap = int(arg.split("=")[1])
        elif arg in ["--help", "-h"]:
            print("Usage: python analyze_missing_runsheets.py [options]")
            print()
            print("Options:")
            print("  --dir=PATH         Use custom source directory (default: RunSheets)")
            print("  --max-gap=N        Maximum gap size to report (default: 30 days)")
            print("  --help, -h         Show this help message")
            print()
            print("Examples:")
            print("  python analyze_missing_runsheets.py")
            print("  python analyze_missing_runsheets.py --max-gap=14")
            print("  python analyze_missing_runsheets.py --dir=OldRunSheets")
            return
    
    analyze_missing_dates(source_dir, max_gap)


if __name__ == "__main__":
    main()
