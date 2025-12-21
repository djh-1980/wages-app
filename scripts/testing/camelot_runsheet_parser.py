#!/usr/bin/env python3
"""
Camelot-based Runsheet Parser

Uses table extraction instead of text parsing for cleaner, more reliable data.
Replaces 2,000+ lines of regex/pattern matching with structured table processing.
"""

import camelot
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict
import sys


class CamelotRunsheetParser:
    """Parse runsheets using table extraction."""
    
    def __init__(self, driver_name: str = "Daniel Hanson"):
        self.driver_name = driver_name
        
    def parse_pdf(self, pdf_path: str) -> List[Dict]:
        """Parse a runsheet PDF and extract job data."""
        print(f"Parsing: {Path(pdf_path).name}")
        
        # Extract all tables from PDF
        tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
        
        if len(tables) == 0:
            # Try stream mode if lattice fails
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
        
        print(f"  Found {len(tables)} tables")
        
        all_jobs = []
        
        # Process each table
        for table in tables:
            df = table.df
            
            # Check if this table is for our driver
            if not self._is_my_table(df):
                continue
            
            # Extract jobs from this table
            jobs = self._extract_jobs_from_table(df, Path(pdf_path).name)
            all_jobs.extend(jobs)
        
        # Remove duplicates
        all_jobs = self._remove_duplicates(all_jobs)
        
        print(f"  Extracted {len(all_jobs)} unique jobs for {self.driver_name}")
        return all_jobs
    
    def _is_my_table(self, df: pd.DataFrame) -> bool:
        """Check if table belongs to our driver."""
        # Look for driver name in first few rows
        for i in range(min(5, len(df))):
            row_text = ' '.join(str(cell) for cell in df.iloc[i])
            if self.driver_name in row_text:
                return True
        return False
    
    def _extract_jobs_from_table(self, df: pd.DataFrame, source_file: str) -> List[Dict]:
        """Extract job data from a table DataFrame."""
        jobs = []
        
        # Find header row (contains "Job #", "Customer", etc.)
        header_row = None
        for i in range(min(10, len(df))):
            row_text = ' '.join(str(cell) for cell in df.iloc[i]).upper()
            if 'JOB' in row_text and 'CUSTOMER' in row_text:
                header_row = i
                break
        
        if header_row is None:
            return jobs
        
        # Get column indices
        headers = df.iloc[header_row]
        col_map = self._map_columns(headers)
        
        # Extract date from header
        date = self._extract_date(df)
        
        # Process data rows (after header)
        for i in range(header_row + 1, len(df)):
            row = df.iloc[i]
            
            # Skip empty rows
            if row.isna().all() or all(str(cell).strip() == '' for cell in row):
                continue
            
            # Extract job data
            job = self._extract_job_from_row(row, col_map, date, source_file)
            
            if job and self._is_valid_job(job):
                jobs.append(job)
        
        return jobs
    
    def _map_columns(self, headers: pd.Series) -> Dict[str, int]:
        """Map column names to indices."""
        col_map = {}
        
        for i, header in enumerate(headers):
            header_str = str(header).upper().strip()
            
            if 'JOB' in header_str and '#' in header_str:
                col_map['job_number'] = i
            elif 'CUSTOMER' in header_str:
                col_map['customer'] = i
            elif 'ACTIVITY' in header_str or 'ACT' in header_str:
                col_map['activity'] = i
            elif 'ADDRESS' in header_str or 'ADDR' in header_str:
                col_map['address'] = i
            elif 'REF' in header_str and '1' in header_str:
                col_map['ref1'] = i
            elif 'TRACE' in header_str or 'REQUEST' in header_str:
                col_map['trace'] = i
        
        return col_map
    
    def _extract_date(self, df: pd.DataFrame) -> str:
        """Extract date from table header."""
        # Look in first few rows for date pattern
        for i in range(min(5, len(df))):
            row_text = ' '.join(str(cell) for cell in df.iloc[i])
            
            # Look for DD/MM/YYYY pattern
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', row_text)
            if date_match:
                return date_match.group(1)
        
        return None
    
    def _extract_job_from_row(self, row: pd.Series, col_map: Dict[str, int], 
                              date: str, source_file: str) -> Dict:
        """Extract job data from a table row."""
        job = {
            'date': date,
            'source_file': source_file,
            'driver': self.driver_name
        }
        
        # Extract job number
        if 'job_number' in col_map:
            job_num = str(row.iloc[col_map['job_number']]).strip()
            # Clean job number (remove non-digits)
            job_num = re.sub(r'[^\d]', '', job_num)
            if job_num:
                job['job_number'] = job_num
        
        # Extract customer
        if 'customer' in col_map:
            customer = str(row.iloc[col_map['customer']]).strip()
            job['customer'] = self._clean_customer(customer)
        
        # Extract activity
        if 'activity' in col_map:
            activity = str(row.iloc[col_map['activity']]).strip()
            job['activity'] = self._clean_activity(activity)
        
        # Extract address
        if 'address' in col_map:
            address = str(row.iloc[col_map['address']]).strip()
            address, postcode = self._extract_address_and_postcode(address)
            job['job_address'] = address
            job['postcode'] = postcode
        
        return job
    
    def _clean_customer(self, customer: str) -> str:
        """Clean customer name."""
        if customer in ['nan', 'None', '']:
            return ''
        
        # Remove newlines
        customer = customer.replace('\n', ' ')
        
        # Remove multiple spaces
        customer = re.sub(r'\s+', ' ', customer)
        
        return customer.strip()
    
    def _clean_activity(self, activity: str) -> str:
        """Clean activity name - preserve full details."""
        if activity in ['nan', 'None', '']:
            return ''
        
        # Remove newlines but keep spaces
        activity = activity.replace('\n', ' ')
        
        # Remove multiple spaces
        activity = re.sub(r'\s+', ' ', activity)
        
        # Return the full activity as-is (don't simplify)
        # This preserves details like "DESK & CHAIR SP INSTALL"
        return activity.strip()
    
    def _extract_address_and_postcode(self, address: str) -> tuple:
        """Extract address and postcode separately."""
        if address in ['nan', 'None', '']:
            return '', ''
        
        # Remove newlines but keep commas
        address = address.replace('\n', ', ')
        
        # Remove multiple spaces
        address = re.sub(r'\s+', ' ', address)
        
        # Remove multiple commas
        address = re.sub(r',\s*,+', ',', address)
        
        # Filter out "NA" values
        parts = [p.strip() for p in address.split(',')]
        parts = [p for p in parts if p.upper() not in ['NA', 'N/A', 'TBC', 'TBD']]
        address = ', '.join(parts)
        
        # Extract UK postcode - improved pattern
        # Look for patterns like "M18, 7EH" or "SK8 3PW" or "M1 2BP"
        postcode_patterns = [
            r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s+\d[A-Z]{2})\b',  # Standard format with space
            r'\b([A-Z]{1,2}\d{1,2}[A-Z]?),?\s*(\d[A-Z]{2})\b',  # Split by comma
        ]
        
        postcode = ''
        for pattern in postcode_patterns:
            match = re.search(pattern, address.upper())
            if match:
                if len(match.groups()) == 2:
                    # Split format: "M18, 7EH"
                    postcode = match.group(1) + ' ' + match.group(2)
                else:
                    # Standard format
                    postcode = match.group(1)
                
                # Ensure proper spacing
                postcode = postcode.replace(',', '').strip()
                if ' ' not in postcode and len(postcode) >= 6:
                    postcode = postcode[:-3] + ' ' + postcode[-3:]
                
                # Remove postcode from address
                address = address[:match.start()] + address[match.end():]
                break
        
        # Clean up address
        address = address.strip(' ,')
        
        # Remove trailing commas and extra spaces
        address = re.sub(r',\s*,+', ',', address)
        address = re.sub(r',\s*$', '', address)
        
        return address, postcode
    
    def _remove_duplicates(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs based on job number."""
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            job_num = job.get('job_number')
            if job_num and job_num not in seen:
                seen.add(job_num)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def _is_valid_job(self, job: Dict) -> bool:
        """Validate job data."""
        # Must have job number
        if not job.get('job_number'):
            return False
        
        # Must have customer or activity
        if not job.get('customer') and not job.get('activity'):
            return False
        
        # Skip PayPoint audits
        customer = job.get('customer', '').upper()
        if 'PAYPOINT' in customer and 'AUDIT' in customer:
            return False
        
        return True
    
    def calculate_quality_score(self, job: Dict) -> int:
        """Calculate quality score for a job (0-100)."""
        score = 0
        
        if job.get('job_number'):
            score += 20
        
        if job.get('customer') and len(job.get('customer', '')) > 3:
            score += 20
        
        if job.get('activity'):
            score += 15
        
        if job.get('job_address') and len(job.get('job_address', '')) > 10:
            score += 20
            
            address = job.get('job_address', '').upper()
            if any(word in address for word in ['ROAD', 'STREET', 'AVENUE', 'LANE', 'DRIVE']):
                score += 5
        
        if job.get('postcode'):
            score += 15
            
            if re.match(r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s\d[A-Z]{2}$', job.get('postcode', '')):
                score += 5
        
        return min(score, 100)


def main():
    """Test the Camelot parser."""
    if len(sys.argv) < 2:
        print("Usage: python3 camelot_runsheet_parser.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    parser = CamelotRunsheetParser()
    jobs = parser.parse_pdf(pdf_path)
    
    print(f"\n{'='*80}")
    print("EXTRACTED JOBS")
    print(f"{'='*80}\n")
    
    for i, job in enumerate(jobs, 1):
        score = parser.calculate_quality_score(job)
        quality = "HIGH" if score >= 80 else "MEDIUM" if score >= 50 else "LOW"
        
        print(f"Job #{i}: {job.get('job_number', 'UNKNOWN')}")
        print(f"  Customer:  {job.get('customer', 'N/A')}")
        print(f"  Activity:  {job.get('activity', 'N/A')}")
        print(f"  Address:   {job.get('job_address', 'N/A')}")
        print(f"  Postcode:  {job.get('postcode', 'N/A')}")
        print(f"  Quality:   {score}/100 ({quality})")
        print()
    
    # Calculate average quality
    if jobs:
        scores = [parser.calculate_quality_score(job) for job in jobs]
        avg_score = sum(scores) / len(scores)
        
        print(f"{'='*80}")
        print("QUALITY SUMMARY")
        print(f"{'='*80}")
        print(f"Total jobs: {len(jobs)}")
        print(f"Average quality: {avg_score:.1f}/100")
        print(f"High quality (80+): {sum(1 for s in scores if s >= 80)}")
        print(f"Medium quality (50-79): {sum(1 for s in scores if 50 <= s < 80)}")
        print(f"Low quality (<50): {sum(1 for s in scores if s < 50)}")
        print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
