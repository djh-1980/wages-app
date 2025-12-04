#!/usr/bin/env python3
"""
Template-based parser that uses the known structure of runsheet PDFs.
"""

import PyPDF2
import re
from pathlib import Path

def parse_job_with_template(text_lines, job_start_idx):
    """
    Parse a single job using the known template structure.
    """
    job = {}
    
    # Extract job number from the job line
    job_line = text_lines[job_start_idx].strip()
    job_match = re.search(r'Job #\s*(\d+)', job_line)
    if job_match:
        job['job_number'] = job_match.group(1)
    
    # The structure after "Job #" is typically:
    # Line 1: Customer name
    # Line 2: "SLA Window" or similar
    # Line 3: Contact Name (SKIP THIS)
    # Line 4: Activity 
    # Line 5: Contact Phone
    # Line 6: Priority
    # Then address block starts
    
    current_idx = job_start_idx + 1
    max_idx = min(job_start_idx + 50, len(text_lines))
    
    # Look for customer (first meaningful line after Job #)
    while current_idx < max_idx:
        line = text_lines[current_idx].strip()
        if line and not line.startswith(('SLA', 'Contact', 'Activity')):
            # This should be the customer
            job['customer'] = line
            break
        current_idx += 1
    
    # Look for specific fields in order
    address_started = False
    address_lines = []
    
    for i in range(job_start_idx + 1, max_idx):
        line = text_lines[i].strip()
        
        if not line:
            continue
            
        # Skip contact name (usually has numbers and "Manager")
        if re.match(r'^\d+.*Manager', line, re.IGNORECASE):
            print(f"  SKIPPING Contact Name: {line}")
            continue
        
        # Activity detection
        if line in ['TECH EXCHANGE', 'NON TECH EXCHANGE', 'REPAIR WITH PARTS', 
                   'REPAIR WITHOUT PARTS', 'CONSUMABLE INSTALL', 'COLLECTION', 'DELIVERY', 'INSTALL']:
            job['activity'] = line
            continue
        
        # Priority detection
        if re.match(r'^(4HR|8HR|6HR|ND\s+\d+)$', line):
            job['priority'] = line
            continue
        
        # Start collecting address after we see priority or certain markers
        if (job.get('priority') or 
            any(marker in line for marker in ['Ref 1', 'Ref 2', 'No. of Parts'])):
            address_started = True
        
        if address_started:
            # Stop collecting at certain markers
            if any(stop in line for stop in ['Instructions', 'Job Notes', 'In Items', 'Request', 'Returned Items']):
                break
            
            # Check for postcode (end of address)
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match:
                job['postcode'] = postcode_match.group(1)
                # Add line without postcode if there's more content
                clean_line = line.replace(job['postcode'], '').strip()
                if clean_line and len(clean_line) > 2:
                    address_lines.append(clean_line)
                break
            
            # Add to address if it looks like address content
            if (line and 
                len(line) > 2 and
                not re.match(r'^(Ref \d|No\. of Parts|Instructions)', line) and
                not line.isdigit()):
                address_lines.append(line)
    
    if address_lines:
        job['job_address'] = '\n'.join(address_lines)
    
    return job

def parse_runsheet_with_template(pdf_path):
    """Parse runsheet using template-based approach."""
    
    jobs = []
    
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            lines = text.split('\n')
            
            # Find all job starts on this page
            for i, line in enumerate(lines):
                if line.strip().startswith('Job #'):
                    print(f"\n=== PAGE {page_num + 1}, JOB: {line.strip()} ===")
                    
                    job = parse_job_with_template(lines, i)
                    
                    if job.get('job_number'):
                        jobs.append(job)
                        
                        print(f"  Job Number: {job.get('job_number')}")
                        print(f"  Customer: {job.get('customer')}")
                        print(f"  Activity: {job.get('activity')}")
                        print(f"  Priority: {job.get('priority')}")
                        print(f"  Address: {repr(job.get('job_address'))}")
                        print(f"  Postcode: {job.get('postcode')}")
    
    return jobs

def main():
    pdf_path = Path("RunSheets/Runsheet_12_runs_2025_11_12.pdf")
    if pdf_path.exists():
        print(f"Testing template-based parsing on: {pdf_path}")
        jobs = parse_runsheet_with_template(pdf_path)
        print(f"\n=== SUMMARY ===")
        print(f"Found {len(jobs)} jobs")
        
        # Show job 4285671 specifically
        for job in jobs:
            if job.get('job_number') == '4285671':
                print(f"\n=== JOB 4285671 DETAILS ===")
                print(f"Customer: {job.get('customer')}")
                print(f"Address: {job.get('job_address')}")
                print(f"Postcode: {job.get('postcode')}")
                break
    else:
        print(f"File not found: {pdf_path}")

if __name__ == "__main__":
    main()
