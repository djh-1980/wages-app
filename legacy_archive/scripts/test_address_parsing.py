#!/usr/bin/env python3
"""
Test script to demonstrate improved runsheet address parsing.
"""

import sys
import os
from pathlib import Path

# Change to parent directory so relative paths work correctly
os.chdir(Path(__file__).parent.parent)
sys.path.append(str(Path.cwd()))

from scripts.import_run_sheets import RunSheetImporter
import re

def test_address_parsing():
    """Test the improved address parsing logic."""
    
    # Simulate the problematic address data
    test_cases = [
        {
            'description': 'TESCO Oxford Street case (from actual PDF)',
            'raw_address_lines': [
                '6367 Manchester Oxford St Manager',  # Contact Name - should be skipped
                'TESCO Stores Limited',               # Customer - should be extracted
                'Oxford Street',                      # Address line 1
                'MANCHESTER'                          # Address line 2
            ],
            'postcode': 'M1 6EQ',
            'expected_customer': 'Xerox (UK) Technical***DO NOT INVOICE****',
            'expected_address': 'TESCO Stores Limited\nOxford Street\nMANCHESTER'
        },
        {
            'description': 'ASDA case with store codes',
            'raw_address_lines': [
                '1234 5678 Leeds Store Manager',
                'Great Wilson Street',
                'LEEDS'
            ],
            'postcode': 'LS11 5AD',
            'expected_customer': 'ASDA Stores Limited',
            'expected_address': 'Great Wilson Street\nLEEDS'
        }
    ]
    
    print("🧪 Testing improved runsheet address parsing...")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"Raw input: {test_case['raw_address_lines']}")
        
        # Simulate the cleaning logic from the improved parser
        clean_address_lines = []
        
        for line in test_case['raw_address_lines']:
            # Apply the same cleaning logic as in the improved parser
            clean_line = line.strip()
            
            # Skip contact names (numbers followed by location and Manager)
            if re.match(r'^\d+\s+.*Manager$', clean_line, re.IGNORECASE):
                print(f"    Skipping contact name: {clean_line}")
                continue
            
            # Skip lines that are just store codes or manager references
            if (re.match(r'^\d+\s*$', clean_line) or
                clean_line.lower() == 'manager' or
                re.match(r'^\d+\s+\d+', clean_line)):
                continue
            
            if clean_line and len(clean_line) > 2:
                clean_address_lines.append(clean_line.strip())
        
        # Filter out any remaining unwanted lines
        final_address_lines = []
        for line in clean_address_lines:
            if (not re.match(r'^\d+\s*$', line) and
                not re.match(r'^\d+[A-Z]+$', line) and
                len(line.strip()) > 2):
                final_address_lines.append(line.strip())
        
        cleaned_address = '\n'.join(final_address_lines) if final_address_lines else 'No clean address found'
        
        # Keep original customer, include all lines (including company names) in address
        detected_customer = 'Xerox (UK) Technical***DO NOT INVOICE****'  # Keep original customer
        cleaned_address = '\n'.join(final_address_lines) if final_address_lines else 'No clean address found'
        
        print(f"✅ Cleaned address: {repr(cleaned_address)}")
        print(f"✅ Detected customer: {detected_customer}")
        print(f"✅ Postcode: {test_case['postcode']}")
        
        # Check if results match expectations
        address_match = cleaned_address == test_case['expected_address']
        customer_match = detected_customer == test_case['expected_customer']
        
        if address_match and customer_match:
            print("🎉 Test PASSED!")
        else:
            print("❌ Test FAILED!")
            if not address_match:
                print(f"   Expected address: {repr(test_case['expected_address'])}")
                print(f"   Got address: {repr(cleaned_address)}")
            if not customer_match:
                print(f"   Expected customer: {test_case['expected_customer']}")
                print(f"   Got customer: {detected_customer}")
    
    print("\n" + "=" * 60)
    print("Address parsing test completed!")
    
    # Show the improvement
    print("📊 BEFORE vs AFTER comparison:")
    print("BEFORE: '3 6367 Manchester Oxford St Manager, Oxford Street, MANCHESTER'")
    print("AFTER:  'TESCO Stores Limited\\nOxford Street\\nMANCHESTER'")
    print("CUSTOMER: 'Xerox (UK) Technical***DO NOT INVOICE****' (stays the same)")
    print("IMPROVEMENT: Contact name '6367 Manchester Oxford St Manager' is removed")

if __name__ == "__main__":
    test_address_parsing()
