#!/usr/bin/env python3
"""
Debug script to see the actual text structure of the PDF for job 4285671.
"""

import pdfplumber
import re
from pathlib import Path

def debug_job_4285671(pdf_path):
    """Find and debug the structure of job 4285671."""
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            if not text:
                continue
            
            # Check if this page contains job 4285671
            if '4285671' in text:
                print(f"=== FOUND JOB 4285671 ON PAGE {page_num} ===")
                
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                # Find the job line and show context
                for i, line in enumerate(lines):
                    if '4285671' in line:
                        print(f"\nJob line found at index {i}: {line}")
                        
                        # Show 20 lines before and after
                        start = max(0, i - 5)
                        end = min(len(lines), i + 25)
                        
                        print(f"\n=== CONTEXT (lines {start} to {end}) ===")
                        for j in range(start, end):
                            marker = " >>> " if j == i else "     "
                            print(f"{j:3d}{marker}{lines[j]}")
                        
                        break
                break

def main():
    pdf_path = Path("RunSheets/Runsheet_12_runs_2025_11_12.pdf")
    if pdf_path.exists():
        debug_job_4285671(pdf_path)
    else:
        print(f"File not found: {pdf_path}")

if __name__ == "__main__":
    main()
