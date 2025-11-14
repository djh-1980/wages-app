#!/usr/bin/env python3
"""
Re-process payslip PDFs to extract and update pay_date and period_end fields.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.production.extract_payslips import PayslipExtractor
import sqlite3

def update_payslip_dates():
    """Re-process all payslips to update pay_date and period_end."""
    
    db_path = "data/database/payslips.db"
    docs_path = Path("data/documents/payslips")
    
    if not docs_path.exists():
        print(f"Error: Payslips directory not found: {docs_path}")
        return
    
    # Create extractor
    extractor = PayslipExtractor(db_path)
    
    # Get all PDF files
    pdf_files = list(docs_path.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} payslip PDFs")
    
    updated = 0
    failed = 0
    
    for pdf_path in pdf_files:
        try:
            # Extract text and parse header
            text = extractor.extract_text_from_pdf(str(pdf_path))
            file_data = extractor.extract_from_filename(pdf_path.name)
            header_data = extractor.parse_payslip_header(text)
            
            if not file_data.get('tax_year') or not file_data.get('week_number'):
                print(f"  Skipping {pdf_path.name} - couldn't extract week/year from filename")
                continue
            
            # Update the payslip record with pay_date and period_end
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE payslips 
                SET pay_date = ?, period_end = ?
                WHERE tax_year = ? AND week_number = ?
            """, (
                header_data.get('pay_date'),
                header_data.get('period_end'),
                file_data['tax_year'],
                file_data['week_number']
            ))
            
            if cursor.rowcount > 0:
                updated += 1
                print(f"  ✓ Updated Week {file_data['week_number']} {file_data['tax_year']}: "
                      f"pay_date={header_data.get('pay_date')}, period_end={header_data.get('period_end')}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            failed += 1
            print(f"  ✗ Failed to process {pdf_path.name}: {e}")
    
    print(f"\n✓ Updated: {updated}")
    print(f"✗ Failed: {failed}")
    print(f"Total processed: {len(pdf_files)}")

if __name__ == "__main__":
    print("Re-processing payslips to extract dates...\n")
    update_payslip_dates()
    print("\nDone!")
