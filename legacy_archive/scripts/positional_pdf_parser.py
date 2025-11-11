#!/usr/bin/env python3
"""
Positional PDF parser for runsheets using field positions instead of text flow parsing.
"""

import PyPDF2
import re
from pathlib import Path

def extract_text_by_position(pdf_path):
    """
    Extract text from PDF and try to identify field positions.
    This is a proof of concept for positional parsing.
    """
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        for page_num, page in enumerate(reader.pages):
            print(f"\n=== PAGE {page_num + 1} ===")
            
            # Extract all text
            text = page.extract_text()
            lines = text.split('\n')
            
            # Look for job patterns
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Find job number
                if line.startswith('Job #'):
                    print(f"JOB FOUND: {line}")
                    
                    # Extract fields in the next several lines
                    job_data = {'job_number': re.search(r'Job #\s*(\d+)', line).group(1) if re.search(r'Job #\s*(\d+)', line) else None}
                    
                    # Look ahead for specific fields
                    for j in range(i+1, min(i+20, len(lines))):
                        field_line = lines[j].strip()
                        
                        # Customer field (usually appears early)
                        if not job_data.get('customer') and field_line and not field_line.startswith(('SLA', 'Activity', 'Contact', 'Priority')):
                            # Skip obvious non-customer lines
                            if not re.match(r'^\d+/\d+/\d+', field_line) and len(field_line) > 3:
                                job_data['customer'] = field_line
                        
                        # Contact Name (skip this)
                        if 'Contact Name' in field_line:
                            contact_line = lines[j+1].strip() if j+1 < len(lines) else ''
                            print(f"  SKIPPING Contact Name: {contact_line}")
                        
                        # Activity
                        if field_line in ['TECH EXCHANGE', 'REPAIR WITH PARTS', 'REPAIR WITHOUT PARTS', 'COLLECTION', 'DELIVERY', 'INSTALL']:
                            job_data['activity'] = field_line
                        
                        # Priority
                        if re.match(r'^(4HR|8HR|6HR|ND\s+\d+)$', field_line):
                            job_data['priority'] = field_line
                    
                    # Look for address block (usually after contact info)
                    address_lines = []
                    collecting_address = False
                    
                    for j in range(i+1, min(i+30, len(lines))):
                        addr_line = lines[j].strip()
                        
                        # Start collecting after we see certain markers
                        if any(marker in addr_line for marker in ['Contact Phone', 'Priority', 'Ref 1']):
                            collecting_address = True
                            continue
                        
                        if collecting_address and addr_line:
                            # Stop at certain markers
                            if any(stop in addr_line for stop in ['Instructions', 'Job Notes', 'In Items', 'Request']):
                                break
                            
                            # UK postcode - this usually ends the address
                            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', addr_line)
                            if postcode_match:
                                job_data['postcode'] = postcode_match.group(1)
                                # Add line without postcode if there's more content
                                clean_addr = addr_line.replace(job_data['postcode'], '').strip()
                                if clean_addr:
                                    address_lines.append(clean_addr)
                                break
                            
                            # Skip obvious non-address lines
                            if (not re.match(r'^\d+\s+\d+.*Manager', addr_line) and  # Skip contact names
                                not re.match(r'^\d+[A-Z]+\s+\d+', addr_line) and      # Skip store codes
                                len(addr_line) > 2):
                                address_lines.append(addr_line)
                    
                    job_data['job_address'] = '\n'.join(address_lines) if address_lines else None
                    
                    print(f"  Customer: {job_data.get('customer')}")
                    print(f"  Activity: {job_data.get('activity')}")
                    print(f"  Priority: {job_data.get('priority')}")
                    print(f"  Address: {repr(job_data.get('job_address'))}")
                    print(f"  Postcode: {job_data.get('postcode')}")
                    print("-" * 50)

def main():
    # Test with the 12/11 file
    pdf_path = Path("RunSheets/Runsheet_12_runs_2025_11_12.pdf")
    if pdf_path.exists():
        print(f"Testing positional parsing on: {pdf_path}")
        extract_text_by_position(pdf_path)
    else:
        print(f"File not found: {pdf_path}")

if __name__ == "__main__":
    main()
