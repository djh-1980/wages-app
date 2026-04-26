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
import pdfplumber


def find_driver_pages(pdf_path: str, driver_name: str = 'Daniel Hanson') -> List[int]:
    """
    Pre-scan PDF to find pages containing the driver's name.
    This dramatically speeds up processing of large multi-driver PDFs.
    
    Args:
        pdf_path: Path to PDF file
        driver_name: Driver name to search for
        
    Returns:
        List of page numbers (1-indexed for Camelot) containing the driver
    """
    driver_pages = []
    name_parts = driver_name.upper().split()
    
    print(f"  Pre-scanning PDF for '{driver_name}' pages...")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ''

                # Only consider the page header (first 2 lines). On real
                # runsheet pages line 2 is e.g. "Daniel Hanson 27/04/2026",
                # whereas on warehouse manifest pages line 2 is
                # "Warehouse manifest" and the driver name only appears in
                # body text (and on line 3 as "Driver Hanson, Daniel").
                # Restricting to the first 2 lines excludes those pages.
                first_lines = '\n'.join(text.split('\n')[:2]).upper()

                # Check if all parts of driver name are present in the header
                if all(part in first_lines for part in name_parts):
                    driver_pages.append(i + 1)  # Camelot uses 1-based page numbers
                    print(f"    ✓ Found '{driver_name}' on page {i + 1}/{total_pages}")
        
        if driver_pages:
            print(f"  Pre-scan complete: {len(driver_pages)} page(s) to process (out of {total_pages} total)")
        else:
            print(f"  ⚠️  Pre-scan found no pages for '{driver_name}' (will try all pages as fallback)")
    
    except Exception as e:
        print(f"  ⚠️  Pre-scan failed: {e} (will try all pages as fallback)")
        return []
    
    return driver_pages


class CamelotRunsheetParser:
    """Parse runsheets using table extraction."""
    
    def __init__(self, driver_name: str = "Daniel Hanson"):
        self.driver_name = driver_name
        # When True, every table extracted is trusted to belong to this
        # driver (because find_driver_pages already vetted the page header).
        # See _is_my_table() for the corresponding short-circuit.
        self._on_driver_page = False

    def parse_pdf(self, pdf_path: str) -> List[Dict]:
        """Parse a runsheet PDF and extract job data."""
        print(f"Parsing: {Path(pdf_path).name}")

        # Pre-filter: Find pages containing driver name (PERFORMANCE OPTIMIZATION)
        # For large multi-driver PDFs (57+ pages), this reduces processing from
        # minutes to seconds by only scanning relevant pages
        driver_pages = find_driver_pages(pdf_path, self.driver_name)

        # Determine which pages to process
        if driver_pages:
            pages_param = ','.join(map(str, driver_pages))
            print(f"  Processing {len(driver_pages)} filtered page(s): {pages_param}")
            # Pages have already been validated as driver pages by their
            # header text - trust them and skip the table-level name match.
            self._on_driver_page = True
        else:
            # Fallback: process all pages if pre-scan failed or found nothing.
            # In this case we can't trust pages, so leave _is_my_table to filter.
            pages_param = 'all'
            self._on_driver_page = False
            print(f"  Processing all pages (no pre-filter applied)")
        
        # Extract runsheet date from page header (not from tables)
        import PyPDF2
        runsheet_date = None
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                # Check first page header for date
                text = reader.pages[0].extract_text()
                # Look for "Date DD/MM/YYYY" or "Daniel Hanson DD/MM/YYYY" pattern
                import re
                date_match = re.search(r'(?:Date\s+|Daniel Hanson\s+)(\d{2}/\d{2}/\d{4})', text)
                if date_match:
                    runsheet_date = date_match.group(1)
        except:
            pass
        
        # Extract tables from PDF (only from filtered pages)
        tables = camelot.read_pdf(pdf_path, pages=pages_param, flavor='lattice')
        
        if len(tables) == 0:
            # Try stream mode if lattice fails (use same page filtering)
            print(f"  Lattice mode found no tables, trying stream mode...")
            tables = camelot.read_pdf(pdf_path, pages=pages_param, flavor='stream')
        
        print(f"  Found {len(tables)} tables")
        
        all_jobs = []
        
        # Process each table
        for table in tables:
            df = table.df
            
            # Check if this table is for our driver
            if not self._is_my_table(df):
                continue
            
            # Extract jobs from this table (pass runsheet_date)
            jobs = self._extract_jobs_from_table(df, Path(pdf_path).name, runsheet_date)
            all_jobs.extend(jobs)
        
        # Remove duplicates
        all_jobs = self._remove_duplicates(all_jobs)
        
        print(f"  Extracted {len(all_jobs)} unique jobs for {self.driver_name}")
        return all_jobs
    
    def _is_my_table(self, df: pd.DataFrame) -> bool:
        """Check if table belongs to our driver."""
        # Trust the page-level pre-filter. find_driver_pages() already
        # confirmed the driver name appears in the page header, so any
        # table extracted from such a page is by construction a driver
        # table. This is essential for the per-page detail layout where
        # the driver name only appears in the page header (lines 1-2)
        # and not inside the Camelot-extracted table cells.
        if getattr(self, '_on_driver_page', False):
            return True

        # Fallback: legacy code path (no page pre-filter applied).
        # Split driver name into parts to handle both "Daniel Hanson" and
        # "Hanson, Daniel" formats and look for it in the first few rows.
        name_parts = self.driver_name.upper().split()
        for i in range(min(5, len(df))):
            row_text = ' '.join(str(cell) for cell in df.iloc[i]).upper()
            if all(part in row_text for part in name_parts):
                return True
        return False
    
    def _extract_jobs_from_table(self, df: pd.DataFrame, source_file: str, runsheet_date: str = None) -> List[Dict]:
        """Extract job data from a table DataFrame."""
        jobs = []

        # Per-page detail layout: every page in the per-driver section of
        # the PDF holds a single job in a vertical "form" (Job # / Customer
        # / Activity / Address all stacked). Detect that and extract a
        # single job rather than treating it as a list-style manifest.
        if self._is_detail_page_table(df):
            detail_job = self._extract_job_from_detail_table(df, runsheet_date, source_file)
            if detail_job:
                jobs.append(detail_job)
            return jobs

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
        
        # Use runsheet date from page header, fallback to table date
        date = runsheet_date if runsheet_date else self._extract_date(df)
        
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
    
    def _is_detail_page_table(self, df: pd.DataFrame) -> bool:
        """Detect the single-job per-page detail layout.

        On these pages row 0 column 0 is the literal text 'Job # NNNNNNN'
        (label and value combined) instead of a list-style header row.
        """
        if df.empty or df.shape[1] < 1:
            return False
        first_cell = str(df.iloc[0, 0]).strip()
        return bool(re.match(r'Job\s*#\s*\d+', first_cell))

    def _extract_job_from_detail_table(self, df: pd.DataFrame, runsheet_date: str,
                                       source_file: str) -> Dict:
        """Extract a single job from a per-page detail (vertical form) table.

        Layout (column indices vary slightly between rows):
            Row 0:  'Job # NNNNNNN' | _ | 'Customer' | _ | <CUSTOMER> | ... | 'Job Address'
            Row 1:  'SLA Window'    | _ | <SLA range> | _ | Contact Name\\n<NAME> | ... | <multi-line address>
            Row 2:  'Activity'      | _ | <ACTIVITY>  | _ | Contact Phone\\n<PHONE>
            Row 3:  'Priority'      | _ | <PRIORITY>
            Row 4:  'Ref 1'         | _ | <REF1>
        """
        # Job number is in row 0 col 0 ("Job # NNNNNNN")
        first_cell = str(df.iloc[0, 0]).strip()
        m = re.match(r'Job\s*#\s*(\d+)', first_cell)
        if not m:
            return None

        job = {
            'date': runsheet_date,
            'source_file': source_file,
            'driver': self.driver_name,
            'job_number': m.group(1),
        }

        ncols = df.shape[1]

        # Customer: scan row 0 for the cell immediately after a 'Customer' label
        for j in range(ncols):
            if str(df.iloc[0, j]).strip().upper() == 'CUSTOMER':
                for k in range(j + 1, ncols):
                    val = str(df.iloc[0, k]).strip()
                    if val and val.upper() != 'NAN':
                        job['customer'] = self._clean_customer(val)
                        break
                break

        # Helper: read the value next to a labelled row in column 0
        def _value_for_label(label):
            label_u = label.upper()
            for i in range(min(15, len(df))):
                if str(df.iloc[i, 0]).strip().upper() == label_u:
                    for k in range(1, ncols):
                        val = str(df.iloc[i, k]).strip()
                        if val and val.upper() != 'NAN':
                            return val
                    break
            return None

        activity = _value_for_label('Activity')
        if activity:
            job['activity'] = self._clean_activity(activity)

        priority = _value_for_label('Priority')
        if priority:
            job['priority'] = priority

        # Address: rightmost multi-line cell on row 1 (next to SLA Window)
        if len(df) > 1:
            for k in range(ncols - 1, 0, -1):
                cell = str(df.iloc[1, k]).strip()
                if cell and cell.upper() != 'NAN' and ('\n' in cell or len(cell) > 20):
                    addr_text = cell.replace('\n', ', ')
                    address, postcode = self._extract_address_and_postcode(addr_text)
                    if address:
                        job['job_address'] = address
                    if postcode:
                        job['postcode'] = postcode
                    break

        return job if self._is_valid_job(job) else None

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
        """Extract date from runsheet header (Date field, not SLA Window)."""
        # First priority: Look for "Date DD/MM/YYYY" pattern in header
        for i in range(min(5, len(df))):
            row_text = ' '.join(str(cell) for cell in df.iloc[i])
            
            # Match "Date 23/12/2025" pattern
            date_match = re.search(r'Date\s+(\d{2}/\d{2}/\d{4})', row_text)
            if date_match:
                return date_match.group(1)
        
        # Fallback: Look for any DD/MM/YYYY but skip SLA Window rows
        for i in range(min(5, len(df))):
            row_text = ' '.join(str(cell) for cell in df.iloc[i])
            
            # Skip SLA Window (contains date ranges, not the runsheet date)
            if 'SLA Window' in row_text:
                continue
                
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
