#!/usr/bin/env python3
"""
New runsheet parser using pdfplumber for better field extraction.
Based on the exact form structure shown in the PDF.
"""

import pdfplumber
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class PDFPlumberRunSheetImporter:
    def __init__(self, db_path: str = "data/payslips.db", name: str = "Daniel Hanson"):
        self.db_path = db_path
        self.conn = None
        self.name = name
        self.setup_database()
    
    def setup_database(self):
        """Set up database connection and tables."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Create run_sheet_jobs table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_sheet_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                driver TEXT,
                jobs_on_run INTEGER,
                job_number TEXT,
                customer TEXT,
                activity TEXT,
                priority TEXT,
                job_address TEXT,
                postcode TEXT,
                notes TEXT,
                source_file TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                UNIQUE(date, job_number)
            )
        """)
        
        self.conn.commit()
    
    def extract_job_from_page(self, page, page_num):
        """Extract job information from a single PDF page."""
        
        # Get all text from the page
        text = page.extract_text()
        if not text:
            return None
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Find job number line
        job_line_idx = None
        for i, line in enumerate(lines):
            if line.startswith('Job #'):
                job_line_idx = i
                break
        
        if job_line_idx is None:
            return None
        
        # Extract job number
        job_match = re.search(r'Job #\s*(\d+)', lines[job_line_idx])
        if not job_match:
            return None
        
        job = {
            'job_number': job_match.group(1),
            'source_file': None,  # Will be set by caller
            'date': None,         # Will be extracted from filename
            'driver': self.name
        }
        
        print(f"\n=== PAGE {page_num}, JOB #{job['job_number']} ===")
        
        # Parse the structured fields based on the form layout
        self.parse_form_fields(lines, job_line_idx, job)
        
        return job
    
    def parse_form_fields(self, lines, job_start_idx, job):
        """Parse the form fields based on the known PDF structure."""
        
        # State tracking
        current_field = None
        address_lines = []
        
        for i in range(job_start_idx + 1, min(job_start_idx + 50, len(lines))):
            line = lines[i]
            
            if not line:
                continue
            
            # Identify field labels and content
            if line == 'Customer':
                current_field = 'customer'
                continue
            elif line == 'Job Address':
                current_field = 'job_address'
                continue
            elif line == 'Contact Name':
                current_field = 'contact_name'  # We'll skip this
                continue
            elif line == 'Activity':
                current_field = 'activity'
                continue
            elif line == 'Priority':
                current_field = 'priority'
                continue
            elif line in ['Contact Phone', 'Ref 1', 'Ref 2', 'No. of Parts']:
                current_field = 'other'  # Skip these fields
                continue
            elif line in ['Instructions 1', 'Instructions 2', 'Job Notes']:
                current_field = 'instructions'  # Stop parsing here
                break
            
            # Process field content based on current field
            if current_field == 'customer':
                if not job.get('customer') and line:
                    job['customer'] = line
                    print(f"  Customer: {line}")
                    current_field = None
            
            elif current_field == 'contact_name':
                # Skip contact name content
                if re.match(r'^\d+.*Manager', line, re.IGNORECASE):
                    print(f"  SKIPPING Contact Name: {line}")
                current_field = None
            
            elif current_field == 'activity':
                activities = ['TECH EXCHANGE', 'NON TECH EXCHANGE', 'REPAIR WITH PARTS', 
                             'REPAIR WITHOUT PARTS', 'CONSUMABLE INSTALL', 'COLLECTION', 
                             'DELIVERY', 'INSTALL']
                if line in activities:
                    job['activity'] = line
                    print(f"  Activity: {line}")
                    current_field = None
            
            elif current_field == 'priority':
                if re.match(r'^(4HR|8HR|6HR|ND\s+\d+)$', line):
                    job['priority'] = line
                    print(f"  Priority: {line}")
                    current_field = None
            
            elif current_field == 'job_address':
                # Collect address lines until we hit a postcode or field boundary
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                
                if postcode_match:
                    job['postcode'] = postcode_match.group(1)
                    # Add line without postcode if there's more content
                    clean_line = line.replace(job['postcode'], '').strip()
                    if clean_line and len(clean_line) > 2:
                        address_lines.append(clean_line)
                    
                    # Finalize address
                    if address_lines:
                        job['job_address'] = '\n'.join(address_lines)
                        print(f"  Address: {repr(job['job_address'])}")
                    print(f"  Postcode: {job['postcode']}")
                    current_field = None
                    break
                else:
                    # Add to address if it's meaningful content
                    if (line and len(line) > 2 and 
                        not line.isdigit() and 
                        not re.match(r'^(Contact Phone|Priority|Ref \d)', line)):
                        address_lines.append(line)
    
    def parse_pdf_runsheet(self, pdf_path: Path):
        """Parse a PDF runsheet using pdfplumber."""
        
        jobs = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                print(f"Processing PDF: {pdf_path.name}")
                print(f"Total pages: {len(pdf.pages)}")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    job = self.extract_job_from_page(page, page_num)
                    
                    if job:
                        # Set source file and extract date from filename
                        job['source_file'] = pdf_path.name
                        job['date'] = self.extract_date_from_filename(pdf_path.name)
                        jobs.append(job)
                
                print(f"\nExtracted {len(jobs)} jobs from {pdf_path.name}")
                return jobs
                
        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            return []
    
    def extract_date_from_filename(self, filename: str) -> str:
        """Extract date from filename in various formats."""
        
        # Try different date patterns
        patterns = [
            r'(\d{2})-(\d{2})-(\d{4})',  # DD-MM-YYYY
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\d{2})(\d{2})(\d{4})',    # DDMMYYYY
            r'(\d{4})_(\d{2})_(\d{2})',  # YYYY_MM_DD
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                groups = match.groups()
                if len(groups[0]) == 4:  # Year first
                    year, month, day = groups
                else:  # Day first
                    day, month, year = groups
                
                return f"{day}/{month}/{year}"
        
        # Default to today if no date found
        return datetime.now().strftime("%d/%m/%Y")
    
    def import_jobs_to_database(self, jobs: List[Dict]):
        """Import jobs to the database."""
        
        cursor = self.conn.cursor()
        imported_count = 0
        
        for job in jobs:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO run_sheet_jobs (
                        date, driver, job_number, customer, activity, priority,
                        job_address, postcode, source_file, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (
                    job.get('date'),
                    job.get('driver'),
                    job.get('job_number'),
                    job.get('customer'),
                    job.get('activity'),
                    job.get('priority'),
                    job.get('job_address'),
                    job.get('postcode'),
                    job.get('source_file')
                ))
                
                imported_count += 1
                print(f"  ✓ Imported job {job.get('job_number')}")
                
            except Exception as e:
                print(f"  ✗ Error importing job {job.get('job_number')}: {e}")
        
        self.conn.commit()
        return imported_count
    
    def process_runsheet_file(self, pdf_path: Path):
        """Process a single runsheet file."""
        
        jobs = self.parse_pdf_runsheet(pdf_path)
        if jobs:
            imported_count = self.import_jobs_to_database(jobs)
            print(f"Successfully imported {imported_count} jobs from {pdf_path.name}")
            return imported_count
        else:
            print(f"No jobs found in {pdf_path.name}")
            return 0
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

def main():
    """Test the pdfplumber parser."""
    
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 pdfplumber_runsheet_parser.py <path_to_pdf>")
        print("Example: python3 pdfplumber_runsheet_parser.py RunSheets/Runsheet_12_runs_2025_11_12.pdf")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)
    
    # Create parser
    parser = PDFPlumberRunSheetImporter()
    
    try:
        # Process the file
        imported_count = parser.process_runsheet_file(pdf_path)
        
        # Show results for job 4285671 if it exists
        cursor = parser.conn.cursor()
        cursor.execute("""
            SELECT job_number, customer, job_address, postcode 
            FROM run_sheet_jobs 
            WHERE job_number = '4285671'
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"\n=== JOB 4285671 RESULT ===")
            print(f"Job Number: {result[0]}")
            print(f"Customer: {result[1]}")
            print(f"Address: {result[2]}")
            print(f"Postcode: {result[3]}")
        
    finally:
        parser.close()

if __name__ == "__main__":
    main()
