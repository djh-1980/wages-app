#!/usr/bin/env python3
"""
Test Camelot table-based extraction on runsheet PDFs.
Compare with current text-based parsing approach.
"""

import camelot
import sys
from pathlib import Path

def test_camelot_extraction(pdf_path):
    """Test table extraction using Camelot."""
    print(f"\n{'='*80}")
    print(f"Testing Camelot Table Extraction: {Path(pdf_path).name}")
    print(f"{'='*80}\n")
    
    try:
        # Try lattice mode (for PDFs with visible table lines)
        print("Attempting lattice mode (for tables with borders)...")
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
        
        if len(tables) == 0:
            print("No tables found with lattice mode. Trying stream mode...")
            # Try stream mode (for PDFs without visible table lines)
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
        
        print(f"\n✓ Found {len(tables)} table(s)\n")
        
        for i, table in enumerate(tables):
            print(f"\n{'='*80}")
            print(f"TABLE {i+1}")
            print(f"{'='*80}")
            print(f"Accuracy: {table.accuracy:.1f}%")
            print(f"Shape: {table.df.shape[0]} rows x {table.df.shape[1]} columns")
            print(f"\nFirst 10 rows:")
            print(table.df.head(10).to_string())
            print(f"\n{'='*80}\n")
        
        return tables
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 test_camelot_extraction.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    tables = test_camelot_extraction(pdf_path)
    
    if tables:
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Total tables extracted: {len(tables)}")
        print(f"Total rows across all tables: {sum(t.df.shape[0] for t in tables)}")
        print(f"Average accuracy: {sum(t.accuracy for t in tables) / len(tables):.1f}%")
        print(f"{'='*80}\n")
