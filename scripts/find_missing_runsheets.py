#!/usr/bin/env python3
"""
Analyze existing run sheets and find missing days.
"""

import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


def extract_date_from_filename(filename: str) -> str:
    """Extract date from filename (YYYY-MM-DD format or from PDF name)."""
    # Try ISO format first (2025-10-25.pdf)
    iso_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if iso_match:
        return iso_match.group(1)
    
    # Try DD-MM-YYYY or DD_MM_YYYY
    date_match = re.search(r'(\d{2})[-_](\d{2})[-_](\d{4})', filename)
    if date_match:
        day, month, year = date_match.groups()
        return f"{year}-{month}-{day}"
    
    return None


def find_missing_days(source_dir: str = "RunSheets", year_filter: str = None, max_gap: int = 30):
    """Find missing days in run sheets."""
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"❌ Error: Directory not found: {source_dir}")
        return
    
    print("=" * 80)
    print("MISSING RUN SHEETS ANALYZER")
    print("=" * 80)
    print(f"Source directory: {source_path.absolute()}")
    if year_filter:
        print(f"Year filter: {year_filter}")
    print()
    
    # Find all PDF files recursively
    pdf_files = list(source_path.rglob('*.pdf')) + list(source_path.rglob('*.PDF'))
    
    if not pdf_files:
        print("ℹ️  No PDF files found")
        return
    
    print(f"Found {len(pdf_files)} PDF files")
    print()
    
    # Extract dates from filenames
    dates = []
    for pdf_file in pdf_files:
        date_str = extract_date_from_filename(pdf_file.name)
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                # Filter by year if specified
                if not year_filter or str(date_obj.year) == year_filter:
                    dates.append(date_obj)
            except:
                pass
    
    if not dates:
        print(f"ℹ️  No valid dates found{' for ' + year_filter if year_filter else ''}")
        return
    
    # Sort dates
    dates.sort()
    
    print(f"📅 Date range: {dates[0]} to {dates[-1]}")
    print(f"📊 Total run sheets: {len(dates)}")
    print()
    
    # Find missing days
    missing_dates = []
    
    for i in range(len(dates) - 1):
        current = dates[i]
        next_date = dates[i + 1]
        diff = (next_date - current).days
        
        # Only report gaps of 1-max_gap days
        if diff > 1 and diff <= max_gap:
            # Found a gap
            for j in range(1, diff):
                missing_date = current + timedelta(days=j)
                missing_dates.append(missing_date)
    
    if not missing_dates:
        print("✅ No missing days found!")
        print()
        return
    
    # Group by year and month
    by_year_month = defaultdict(list)
    for date in missing_dates:
        key = f"{date.year}-{date.strftime('%B')}"
        by_year_month[key].append(date)
    
    print(f"⚠️  Found {len(missing_dates)} missing days (gaps of 1-{max_gap} days)")
    print()
    print("=" * 80)
    print("MISSING DAYS BY MONTH")
    print("=" * 80)
    print()
    
    for year_month in sorted(by_year_month.keys()):
        dates_list = by_year_month[year_month]
        print(f"📅 {year_month} ({len(dates_list)} missing days)")
        print("-" * 40)
        
        for date in sorted(dates_list):
            day_name = date.strftime('%A')
            print(f"  • {date} ({day_name})")
        
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total run sheets: {len(dates)}")
    print(f"Missing days: {len(missing_dates)}")
    print(f"Coverage: {len(dates) / (len(dates) + len(missing_dates)) * 100:.1f}%")
    print("=" * 80)


def main():
    """Run analyzer."""
    import sys
    
    year_filter = None
    max_gap = 30
    source_dir = "RunSheets"
    
    for arg in sys.argv[1:]:
        if arg.startswith("--year="):
            year_filter = arg.split("=")[1]
        elif arg.startswith("--max-gap="):
            max_gap = int(arg.split("=")[1])
        elif arg.startswith("--dir="):
            source_dir = arg.split("=")[1]
        elif arg in ["--help", "-h"]:
            print("Usage: python find_missing_runsheets.py [options]")
            print()
            print("Options:")
            print("  --year=YYYY        Filter by specific year (e.g., --year=2024)")
            print("  --max-gap=N        Maximum gap size to report (default: 30 days)")
            print("  --dir=PATH         Use custom source directory (default: RunSheets)")
            print("  --help, -h         Show this help message")
            print()
            print("Examples:")
            print("  python find_missing_runsheets.py")
            print("  python find_missing_runsheets.py --year=2024")
            print("  python find_missing_runsheets.py --year=2021 --max-gap=14")
            return
    
    find_missing_days(source_dir, year_filter, max_gap)


if __name__ == "__main__":
    main()
