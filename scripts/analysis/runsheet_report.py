#!/usr/bin/env python3
"""
Generate a report showing which months have run sheets and which are missing.
"""

import PyPDF2
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict


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
        return None


def parse_date(date_str: str) -> tuple:
    """Parse DD/MM/YYYY date string and return (year, month, date_str)."""
    try:
        dt = datetime.strptime(date_str, '%d/%m/%Y')
        return (dt.year, dt.month, date_str)
    except:
        return None


def generate_report(source_dir: str = "RunSheets"):
    """Generate report of run sheet coverage."""
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"❌ Error: Directory not found: {source_dir}")
        return
    
    print("=" * 80)
    print("RUN SHEET COVERAGE REPORT")
    print("=" * 80)
    print(f"Source directory: {source_path.absolute()}")
    print()
    
    # Find all PDF files
    pdf_files = list(source_path.glob('*.pdf')) + list(source_path.glob('*.PDF'))
    
    if not pdf_files:
        print("ℹ️  No PDF files found")
        return
    
    print(f"Analyzing {len(pdf_files)} PDF files...")
    print()
    
    # Collect dates by year/month
    dates_by_month = defaultdict(list)
    skipped = []
    
    for pdf_file in pdf_files:
        date_str = extract_date_from_pdf(pdf_file)
        
        if not date_str:
            skipped.append(pdf_file.name)
            continue
        
        parsed = parse_date(date_str)
        if not parsed:
            skipped.append(pdf_file.name)
            continue
        
        year, month, _ = parsed
        dates_by_month[(year, month)].append(date_str)
    
    # Month names
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    # Get year range
    if not dates_by_month:
        print("⚠️  No valid run sheets found")
        return
    
    years = sorted(set(year for year, month in dates_by_month.keys()))
    
    # Print report by year
    for year in years:
        print("=" * 80)
        print(f"📅 YEAR {year}")
        print("=" * 80)
        print()
        
        total_days = 0
        
        for month in range(1, 13):
            month_name = month_names[month - 1]
            dates = dates_by_month.get((year, month), [])
            
            if dates:
                print(f"  ✅ {month_name:12} - {len(dates):3} run sheets")
                total_days += len(dates)
            else:
                print(f"  ❌ {month_name:12} - NO DATA")
        
        print()
        print(f"  📊 Total: {total_days} run sheets in {year}")
        print()
    
    # Overall summary
    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print()
    
    total_sheets = sum(len(dates) for dates in dates_by_month.values())
    total_months = len(dates_by_month)
    
    print(f"📄 Total run sheets: {total_sheets}")
    print(f"📅 Months with data: {total_months}")
    print(f"⚠️  Skipped files: {len(skipped)}")
    print()
    
    # Missing months analysis
    print("=" * 80)
    print("MISSING MONTHS")
    print("=" * 80)
    print()
    
    missing_count = 0
    for year in years:
        missing_in_year = []
        for month in range(1, 13):
            if (year, month) not in dates_by_month:
                missing_in_year.append(month_names[month - 1])
                missing_count += 1
        
        if missing_in_year:
            print(f"  {year}: {', '.join(missing_in_year)}")
    
    if missing_count == 0:
        print("  ✅ No missing months!")
    else:
        print()
        print(f"  Total missing: {missing_count} months")
    
    print()
    
    # Show skipped files if any
    if skipped:
        print("=" * 80)
        print(f"SKIPPED FILES ({len(skipped)})")
        print("=" * 80)
        print()
        for filename in sorted(skipped)[:20]:  # Show first 20
            print(f"  • {filename}")
        if len(skipped) > 20:
            print(f"  ... and {len(skipped) - 20} more")
        print()
    
    print("=" * 80)


def main():
    """Run report."""
    import sys
    
    source_dir = "RunSheets"
    
    for arg in sys.argv[1:]:
        if arg.startswith("--dir="):
            source_dir = arg.split("=")[1]
        elif arg in ["--help", "-h"]:
            print("Usage: python runsheet_report.py [options]")
            print()
            print("Options:")
            print("  --dir=PATH      Use custom source directory (default: RunSheets)")
            print("  --help, -h      Show this help message")
            print()
            print("Example:")
            print("  python runsheet_report.py")
            print("  python runsheet_report.py --dir=docs/Sheets")
            return
    
    generate_report(source_dir)


if __name__ == "__main__":
    main()
