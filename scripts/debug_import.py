#!/usr/bin/env python3
"""
Debug script to check address extraction for specific date.
"""

import PyPDF2
import re
from pathlib import Path

def debug_pdf_extraction(pdf_path: str, target_date: str = "24/10/2025"):
    """Debug PDF extraction for a specific date."""
    print(f"Analyzing: {pdf_path}")
    print(f"Looking for date: {target_date}")
    print("=" * 80)
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        for page_num, page in enumerate(reader.pages):
            page_text = page.extract_text()
            lines = page_text.split('\n')
            
            # Check if this page has the target date
            has_target_date = False
            for line in lines[:10]:
                if target_date in line:
                    has_target_date = True
                    break
            
            if not has_target_date:
                continue
            
            print(f"\n📄 PAGE {page_num + 1}")
            print("-" * 80)
            
            # Print all lines with line numbers
            for i, line in enumerate(lines):
                print(f"{i:3d}: {line}")
            
            print("\n" + "=" * 80)


def main():
    """Run debug."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python debug_import.py <pdf_file> [date]")
        print("Example: python debug_import.py RunSheets/runsheet_24oct.pdf 24/10/2025")
        return
    
    pdf_path = sys.argv[1]
    target_date = sys.argv[2] if len(sys.argv) > 2 else "24/10/2025"
    
    if not Path(pdf_path).exists():
        print(f"Error: File not found: {pdf_path}")
        return
    
    debug_pdf_extraction(pdf_path, target_date)


if __name__ == "__main__":
    main()
