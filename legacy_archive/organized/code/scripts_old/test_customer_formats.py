#!/usr/bin/env python3
"""
Test script to identify customer-specific format issues in payslips.
"""

import sys
from pathlib import Path
import os

# Change to parent directory so relative paths work correctly
os.chdir(Path(__file__).parent.parent)
sys.path.append(str(Path.cwd()))

from scripts.extract_payslips import PayslipExtractor
import re

def test_customer_formats():
    """Test different customer name formats."""
    
    # Test patterns
    test_lines = [
        "Daniel Hanson: 2609338 | TESCO | Store 1234 | TECH EXCHANGE - ND 1700",
        "Hanson, Daniel: 2609339 | ASDA | Store 5678 | REPAIR WITH PARTS - 4HR",
        "D. Hanson: 2609340 | SAINSBURY | Store 9012 | COLLECTION - AP",
        "HANSON, DANIEL: 2609341 | MORRISONS | Store 3456 | DELIVERY - 8HR",
        "Daniel Hanson: TESCO | Store 1234 | TECH EXCHANGE - ND 1700",  # No job number
    ]
    
    extractor = PayslipExtractor()
    
    print("🧪 Testing customer format detection...")
    print("=" * 60)
    
    for i, line in enumerate(test_lines, 1):
        print(f"\nTest {i}: {line}")
        
        # Test the parsing
        test_text = f"Some header text\n{line}\nSome footer text"
        jobs = extractor.parse_job_items(test_text)
        
        if jobs:
            job = jobs[0]
            print(f"  ✅ Parsed successfully:")
            print(f"     Job Number: {job.get('job_number', 'None')}")
            print(f"     Client: {job.get('client', 'None')}")
            print(f"     Location: {job.get('location', 'None')}")
            print(f"     Job Type: {job.get('job_type', 'None')}")
        else:
            print(f"  ❌ Failed to parse")
    
    print("\n" + "=" * 60)
    print("Test completed. Check results above for parsing issues.")

if __name__ == "__main__":
    test_customer_formats()
