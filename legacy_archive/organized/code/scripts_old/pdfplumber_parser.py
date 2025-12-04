#!/usr/bin/env python3
"""
Better PDF parser using pdfplumber to maintain spatial relationships.
"""

import pdfplumber
import re
from pathlib import Path

def extract_job_from_page(page):
    """Extract job information from a single page using spatial analysis."""
    
    # Extract text with bounding boxes
    text = page.extract_text()
    if not text:
        return None
    
    lines = text.split('\n')
    
    # Find job number
    job = {}
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('Job #'):
            job_match = re.search(r'Job #\s*(\d+)', line)
            if job_match:
                job['job_number'] = job_match.group(1)
                print(f"\n=== JOB {job['job_number']} ===")
                
                # Parse the rest of the job using the improved logic
                job.update(parse_job_fields(lines, i))
                break
    
    return job if job.get('job_number') else None

def parse_job_fields(lines, job_start_idx):
    """Parse job fields using the known form structure from the PDF."""
    
    fields = {}
    address_lines = []
    in_job_address_field = False
    
    # Look through the lines after the job number
    for i in range(job_start_idx + 1, min(job_start_idx + 40, len(lines))):
        line = lines[i].strip()
        
        if not line:
            continue
        
        # Look for the Customer field (comes after Job # line)
        if line.startswith('Customer') or (not fields.get('customer') and 'DO NOT INVOICE' in line):
            # The customer line might be the field label or the actual customer name
            if 'DO NOT INVOICE' in line:
                fields['customer'] = line
                print(f"  Customer: {line}")
            elif i + 1 < len(lines) and 'DO NOT INVOICE' in lines[i + 1]:
                fields['customer'] = lines[i + 1].strip()
                print(f"  Customer: {fields['customer']}")
            continue
        
        # Skip contact names (numbers + location + Manager)
        if re.match(r'^\d+.*Manager', line, re.IGNORECASE):
            print(f"  SKIPPING Contact Name: {line}")
            continue
        
        # Activity
        activities = ['TECH EXCHANGE', 'NON TECH EXCHANGE', 'REPAIR WITH PARTS', 
                     'REPAIR WITHOUT PARTS', 'CONSUMABLE INSTALL', 'COLLECTION', 'DELIVERY', 'INSTALL']
        if line in activities:
            fields['activity'] = line
            print(f"  Activity: {line}")
            continue
        
        # Priority
        if re.match(r'^(4HR|8HR|6HR|ND\s+\d+)$', line):
            fields['priority'] = line
            print(f"  Priority: {line}")
            continue
        
        # Look for Job Address field specifically
        if line.startswith('Job Address') or in_job_address_field:
            if line.startswith('Job Address'):
                in_job_address_field = True
                continue
            
            # Stop collecting address at certain markers
            if any(stop in line for stop in ['Instructions', 'Job Notes', 'In Items', 'Request', 'Returned Items', 'Activity', 'Priority']):
                in_job_address_field = False
                continue
            
            # Check for postcode (usually ends the address)
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match:
                fields['postcode'] = postcode_match.group(1)
                # Add the line without postcode if there's more content
                clean_line = line.replace(fields['postcode'], '').strip()
                if clean_line and len(clean_line) > 2:
                    address_lines.append(clean_line)
                in_job_address_field = False
                continue
            
            # Add line to address if it looks like address content
            if (line and 
                len(line) > 2 and
                not re.match(r'^(Ref \d|No\. of Parts|Contact Phone|Priority)', line) and
                not line.isdigit()):
                address_lines.append(line)
                continue
    
    if address_lines:
        fields['job_address'] = '\n'.join(address_lines)
        print(f"  Address: {repr(fields['job_address'])}")
    
    if fields.get('postcode'):
        print(f"  Postcode: {fields['postcode']}")
    
    return fields

def parse_runsheet_with_pdfplumber(pdf_path):
    """Parse runsheet using pdfplumber for better text extraction."""
    
    jobs = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            print(f"\n--- PAGE {page_num + 1} ---")
            
            job = extract_job_from_page(page)
            if job:
                jobs.append(job)
    
    return jobs

def main():
    pdf_path = Path("RunSheets/Runsheet_12_runs_2025_11_12.pdf")
    if pdf_path.exists():
        print(f"Testing pdfplumber parsing on: {pdf_path}")
        jobs = parse_runsheet_with_pdfplumber(pdf_path)
        
        print(f"\n=== SUMMARY ===")
        print(f"Found {len(jobs)} jobs")
        
        # Show job 4285671 specifically
        for job in jobs:
            if job.get('job_number') == '4285671':
                print(f"\n=== JOB 4285671 FINAL RESULT ===")
                print(f"Customer: {job.get('customer')}")
                print(f"Activity: {job.get('activity')}")
                print(f"Priority: {job.get('priority')}")
                print(f"Address: {job.get('job_address')}")
                print(f"Postcode: {job.get('postcode')}")
                break
    else:
        print(f"File not found: {pdf_path}")

if __name__ == "__main__":
    main()
