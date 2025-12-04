#!/usr/bin/env python3
"""
Robust pdfplumber parser that handles the jumbled text format from the PDF.
"""

import pdfplumber
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

class RobustPDFPlumberParser:
    def __init__(self, db_path: str = "data/payslips.db", name: str = "Daniel Hanson"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.name = name
    
    def parse_job_from_text_block(self, text_block: str, job_number: str):
        """Parse job information from a block of jumbled text."""
        
        job = {
            'job_number': job_number,
            'driver': self.name
        }
        
        print(f"\n=== PARSING JOB {job_number} ===")
        
        # Extract customer (look for DO NOT INVOICE pattern)
        customer_match = re.search(r'(.*?\*\*\*DO NOT INVOICE\*\*\*\*)', text_block)
        if customer_match:
            job['customer'] = customer_match.group(1).strip()
            print(f"  Customer: {job['customer']}")
        
        # Extract activity
        activities = ['TECH EXCHANGE', 'NON TECH EXCHANGE', 'REPAIR WITH PARTS', 
                     'REPAIR WITHOUT PARTS', 'CONSUMABLE INSTALL', 'COLLECTION', 
                     'DELIVERY', 'INSTALL']
        
        for activity in activities:
            if activity in text_block:
                job['activity'] = activity
                print(f"  Activity: {activity}")
                break
        
        # Extract priority
        priority_match = re.search(r'\b(4HR|8HR|6HR|ND\s+\d+)\b', text_block)
        if priority_match:
            job['priority'] = priority_match.group(1)
            print(f"  Priority: {job['priority']}")
        
        # Extract postcode (UK format)
        postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', text_block)
        if postcode_match:
            job['postcode'] = postcode_match.group(1)
            print(f"  Postcode: {job['postcode']}")
        
        # Extract address components
        address_parts = []
        
        # Look for TESCO, ASDA, etc. (store names)
        store_patterns = [
            r'(TESCO\s+Stores?\s+Limited)',
            r'(ASDA\s+Stores?\s+Limited)', 
            r'(Sainsbury\'?s?\s+Supermarkets?\s+Ltd)',
            r'(LIDL\s+Great\s+Britain\s+Limited)',
            r'(ALDI\s+Stores?\s+Limited)',
            r'(Wm\s+Morrison\s+Supermarkets?\s+Limited)'
        ]
        
        for pattern in store_patterns:
            match = re.search(pattern, text_block, re.IGNORECASE)
            if match:
                address_parts.append(match.group(1))
                print(f"  Found store: {match.group(1)}")
                break
        
        # Look for street address (common patterns)
        street_patterns = [
            r'(\d+\s+[A-Z][a-z]+\s+Street)',
            r'(\d+\s+[A-Z][a-z]+\s+Road)', 
            r'(\d+\s+[A-Z][a-z]+\s+Avenue)',
            r'([A-Z][a-z]+\s+Street)',
            r'([A-Z][a-z]+\s+Road)',
            r'(Oxford\s+Street)',  # Specific for this case
            r'(High\s+Street)',
            r'(Market\s+Street)'
        ]
        
        for pattern in street_patterns:
            match = re.search(pattern, text_block)
            if match:
                street = match.group(1)
                if street not in address_parts:  # Avoid duplicates
                    address_parts.append(street)
                    print(f"  Found street: {street}")
        
        # Look for city/town (usually before postcode)
        if job.get('postcode'):
            # Look for word before postcode that could be city
            city_pattern = rf'([A-Z][A-Z\s]+?)\s+{re.escape(job["postcode"])}'
            city_match = re.search(city_pattern, text_block)
            if city_match:
                city = city_match.group(1).strip()
                # Clean up city name
                city = re.sub(r'\s+', ' ', city)  # Normalize spaces
                if len(city) > 2 and city not in address_parts:
                    address_parts.append(city)
                    print(f"  Found city: {city}")
        
        # Combine address parts
        if address_parts:
            job['job_address'] = '\n'.join(address_parts)
            print(f"  Final Address: {repr(job['job_address'])}")
        
        return job
    
    def find_job_text_blocks(self, pdf_path: Path):
        """Find text blocks for each job in the PDF."""
        
        jobs = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue
                
                # Find job numbers on this page
                job_matches = re.finditer(r'Job #\s*(\d+)', text)
                
                for match in job_matches:
                    job_number = match.group(1)
                    start_pos = match.start()
                    
                    # Get text block around this job (next 2000 characters)
                    text_block = text[start_pos:start_pos + 2000]
                    
                    # Parse this job
                    job = self.parse_job_from_text_block(text_block, job_number)
                    job['source_file'] = pdf_path.name
                    job['date'] = self.extract_date_from_filename(pdf_path.name)
                    
                    jobs.append(job)
        
        return jobs
    
    def extract_date_from_filename(self, filename: str) -> str:
        """Extract date from filename."""
        
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
        
        return datetime.now().strftime("%d/%m/%Y")
    
    def import_to_database(self, jobs: List[Dict]):
        """Import jobs to database."""
        
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
                
            except Exception as e:
                print(f"  ✗ Error importing job {job.get('job_number')}: {e}")
        
        self.conn.commit()
        return imported_count
    
    def process_file(self, pdf_path: Path):
        """Process a single PDF file."""
        
        print(f"Processing: {pdf_path}")
        jobs = self.find_job_text_blocks(pdf_path)
        
        if jobs:
            imported_count = self.import_to_database(jobs)
            print(f"\nImported {imported_count} jobs from {pdf_path.name}")
            return imported_count
        else:
            print(f"No jobs found in {pdf_path.name}")
            return 0
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

def main():
    """Test the robust parser."""
    
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python3 robust_pdfplumber_parser.py <path_to_pdf>")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        sys.exit(1)
    
    # Delete existing data for this file first
    conn = sqlite3.connect("data/payslips.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM run_sheet_jobs WHERE source_file = ?", (pdf_path.name,))
    conn.commit()
    conn.close()
    
    # Create parser and process
    parser = RobustPDFPlumberParser()
    
    try:
        parser.process_file(pdf_path)
        
        # Show result for job 4285671
        cursor = parser.conn.cursor()
        cursor.execute("""
            SELECT job_number, customer, job_address, postcode, activity, priority
            FROM run_sheet_jobs 
            WHERE job_number = '4285671'
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"\n=== JOB 4285671 FINAL RESULT ===")
            print(f"Job Number: {result[0]}")
            print(f"Customer: {result[1]}")
            print(f"Address: {result[2]}")
            print(f"Postcode: {result[3]}")
            print(f"Activity: {result[4]}")
            print(f"Priority: {result[5]}")
        else:
            print("\nJob 4285671 not found in results")
        
    finally:
        parser.close()

if __name__ == "__main__":
    main()
