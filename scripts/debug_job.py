#!/usr/bin/env python3
"""
Debug script to show raw PDF text for a specific job number.
"""

import PyPDF2
import re
from pathlib import Path


def find_job_in_pdf(pdf_path: str, job_number: str):
    """Find and display text around a specific job number."""
    print(f"Searching for Job #{job_number} in {pdf_path}")
    print("=" * 80)
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            lines = text.split('\n')
            
            # Find the job number
            for i, line in enumerate(lines):
                if f'Job #{job_number}' in line or f'Job # {job_number}' in line:
                    print(f"\n📄 FOUND ON PAGE {page_num + 1}")
                    print("=" * 80)
                    
                    # Show 50 lines after the job number
                    start = max(0, i - 2)
                    end = min(len(lines), i + 50)
                    
                    for j in range(start, end):
                        marker = ">>> " if j == i else "    "
                        print(f"{marker}{j:3d}: {lines[j]}")
                    
                    print("\n" + "=" * 80)
                    return True
    
    print("❌ Job not found in this PDF")
    return False


def main():
    """Run debug."""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python debug_job.py <job_number> <date>")
        print("Example: python debug_job.py 4257141 24/10/2025")
        print("\nThis will search for the job in the run sheet for that date.")
        return
    
    job_number = sys.argv[1]
    date = sys.argv[2]
    
    # Convert date to find PDF
    # Date format: 24/10/2025 -> look in RunSheets/2025/10/
    parts = date.split('/')
    if len(parts) == 3:
        day, month, year = parts
        folder = Path(f"RunSheets/{year}/{month}")
        
        if not folder.exists():
            print(f"❌ Folder not found: {folder}")
            return
        
        # Find PDFs for that date
        pdfs = list(folder.glob('*.pdf')) + list(folder.glob('*.PDF'))
        
        found = False
        for pdf in pdfs:
            # Check if PDF is for this date
            if find_job_in_pdf(str(pdf), job_number):
                found = True
                break
        
        if not found:
            print(f"\n❌ Job #{job_number} not found in any PDFs for {date}")
            print(f"Searched {len(pdfs)} PDFs in {folder}")
    else:
        print("❌ Invalid date format. Use DD/MM/YYYY")


if __name__ == "__main__":
    main()
