#!/usr/bin/env python3
"""
Import daily run sheets and extract job information.
Scans for: Name, Date, Job Number, Customer, Activity
"""

import PyPDF2
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import csv


class RunSheetImporter:
    def __init__(self, db_path: str = "data/payslips.db", name: str = "Daniel Hanson"):
        self.db_path = db_path
        self.conn = None
        self.name = name
        self.setup_database()
    
    def setup_database(self):
        """Create run_sheet_jobs table if it doesn't exist."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Create table for run sheet jobs
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS run_sheet_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                job_number TEXT,
                customer TEXT,
                activity TEXT,
                location TEXT,
                notes TEXT,
                source_file TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, job_number)
            )
        """)
        
        self.conn.commit()
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all text from a PDF file."""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    def parse_csv_run_sheet(self, csv_path: str) -> List[Dict]:
        """Parse CSV format run sheet."""
        jobs = []
        
        with open(csv_path, 'r', encoding='utf-8') as file:
            # Try to detect if there's a header
            sample = file.read(1024)
            file.seek(0)
            
            # Check for common delimiters
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample)
                has_header = sniffer.has_header(sample)
            except:
                dialect = csv.excel
                has_header = True
            
            reader = csv.DictReader(file, dialect=dialect) if has_header else csv.reader(file, dialect=dialect)
            
            for row in reader:
                if isinstance(row, dict):
                    # DictReader - look for relevant columns
                    job = self._extract_job_from_dict(row)
                else:
                    # Regular reader - parse as list
                    job = self._extract_job_from_list(row)
                
                if job:
                    jobs.append(job)
        
        return jobs
    
    def _extract_job_from_dict(self, row: Dict) -> Optional[Dict]:
        """Extract job info from CSV dictionary row."""
        # Look for name match (case insensitive)
        name_found = False
        for key, value in row.items():
            if self.name.lower() in str(value).lower():
                name_found = True
                break
        
        if not name_found:
            return None
        
        job = {}
        
        # Map common column names
        column_mapping = {
            'date': ['date', 'day', 'date_time', 'scheduled_date'],
            'job_number': ['job_number', 'job_no', 'job', 'ticket', 'ticket_no', 'wo', 'work_order'],
            'customer': ['customer', 'client', 'company', 'account'],
            'activity': ['activity', 'job_type', 'type', 'service', 'description'],
            'location': ['location', 'site', 'address', 'postcode'],
        }
        
        for field, possible_names in column_mapping.items():
            for col_name in possible_names:
                for key in row.keys():
                    if col_name.lower() in key.lower():
                        job[field] = row[key]
                        break
                if field in job:
                    break
        
        return job if job else None
    
    def _extract_job_from_list(self, row: List) -> Optional[Dict]:
        """Extract job info from CSV list row."""
        # Check if name appears in any column
        name_found = any(self.name.lower() in str(cell).lower() for cell in row)
        
        if not name_found or len(row) < 3:
            return None
        
        # Try to identify columns by content patterns
        job = {}
        
        for i, cell in enumerate(row):
            cell_str = str(cell).strip()
            
            # Date pattern: DD/MM/YY or DD/MM/YYYY or YYYY-MM-DD
            if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', cell_str) or re.match(r'\d{4}-\d{2}-\d{2}', cell_str):
                job['date'] = cell_str
            
            # Job number pattern: digits, possibly with prefix
            elif re.match(r'^[A-Z]*\d{5,}', cell_str):
                job['job_number'] = cell_str
            
            # Skip if it's the name
            elif self.name.lower() in cell_str.lower():
                continue
            
            # Customer/Activity - longer text fields
            elif len(cell_str) > 5 and not job.get('customer'):
                job['customer'] = cell_str
            elif len(cell_str) > 5 and not job.get('activity'):
                job['activity'] = cell_str
        
        return job if len(job) >= 2 else None
    
    def parse_pdf_run_sheet(self, pdf_path: str) -> List[Dict]:
        """Parse PDF format run sheet - page by page to filter by person."""
        jobs = []
        
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Process each page separately
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                
                # Check if this page is for the specified person
                # Look in first 5 lines of page
                page_lines = page_text.split('\n')
                is_my_page = False
                for i in range(min(5, len(page_lines))):
                    if self.name.lower() in page_lines[i].lower():
                        is_my_page = True
                        break
                
                if not is_my_page:
                    continue  # Skip this page
                
                # Parse jobs from this page
                lines = page_lines
                
                # Look for "Job #" pattern which indicates start of a job
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    
                    # Found a job entry
                    if line.startswith('Job #'):
                        job = {}
                        
                        # Extract job number from this line
                        job_match = re.search(r'Job #\s*(\d+)', line)
                        if job_match:
                            job['job_number'] = job_match.group(1)
                        
                        # Look ahead for customer, activity, date in rest of page
                        for j in range(i+1, len(lines)):
                            next_line = lines[j].strip()
                            
                            # Customer - typically ends with "Limited", "Ltd", "PLC", etc.
                            if not job.get('customer'):
                                customer_match = re.search(r'^([A-Za-z0-9\s\-&()]+(?:Limited|Ltd|PLC|plc|LTD))(?:\s|$)', next_line)
                                if customer_match:
                                    customer = customer_match.group(1).strip()
                                    # Clean up common prefixes
                                    customer = re.sub(r'^Customer\s*Signature\s*', '', customer)
                                    customer = re.sub(r'^Customer\s*Print\s*', '', customer)
                                    job['customer'] = customer.strip()
                            
                            # Date - format DD/MM/YYYY
                            if not job.get('date'):
                                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', next_line)
                                if date_match:
                                    job['date'] = date_match.group(1)
                            
                            # Activity
                            if not job.get('activity'):
                                activity_patterns = [
                                    'TECH EXCHANGE',
                                    'NON TECH EXCHANGE',
                                    'REPAIR WITH PARTS',
                                    'REPAIR WITHOUT PARTS',
                                    'CONSUMABLE INSTALL',
                                    'COLLECTION',
                                    'DELIVERY',
                                    'INSTALL'
                                ]
                                for pattern in activity_patterns:
                                    if pattern in next_line.upper():
                                        job['activity'] = pattern
                                        break
                            
                            # Location - UK postcode
                            if not job.get('location'):
                                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', next_line)
                                if postcode_match:
                                    job['location'] = postcode_match.group(1)
                            
                            # Stop if we hit next job or page end
                            if next_line.startswith('Job #') or next_line.startswith('Page '):
                                break
                        
                        # Add job if valid
                        if job.get('job_number') and (job.get('customer') or job.get('activity')):
                            jobs.append(job)
                        
                        i = j if j < len(lines) else i + 1
                    else:
                        i += 1
        
        return jobs
    
    def import_run_sheet(self, file_path: Path) -> int:
        """Import a single run sheet file."""
        print(f"Processing: {file_path.name}")
        
        try:
            # Determine file type and parse
            if file_path.suffix.lower() == '.pdf':
                jobs = self.parse_pdf_run_sheet(str(file_path))
            elif file_path.suffix.lower() in ['.csv', '.txt']:
                jobs = self.parse_csv_run_sheet(str(file_path))
            else:
                print(f"  ⚠️  Unsupported file type: {file_path.suffix}")
                return 0
            
            if not jobs:
                print(f"  ⚠️  No jobs found for {self.name}")
                return 0
            
            # Insert jobs into database
            cursor = self.conn.cursor()
            imported = 0
            
            for job in jobs:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO run_sheet_jobs (
                            date, job_number, customer, activity, location, notes, source_file
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job.get('date'),
                        job.get('job_number'),
                        job.get('customer'),
                        job.get('activity'),
                        job.get('location'),
                        job.get('notes'),
                        file_path.name
                    ))
                    imported += 1
                except sqlite3.IntegrityError:
                    # Duplicate - skip
                    pass
            
            self.conn.commit()
            print(f"  ✓ Imported {imported} jobs")
            return imported
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return 0
    
    def import_all_run_sheets(self, run_sheets_dir: str = None):
        """Import all run sheet files from directory."""
        # Check multiple possible locations
        possible_dirs = [
            run_sheets_dir,
            "RunSheets",
            "docs/Run Sheets",
            "Run Sheets"
        ] if run_sheets_dir else ["RunSheets", "docs/Run Sheets", "Run Sheets"]
        
        run_sheets_path = None
        for dir_path in possible_dirs:
            if dir_path and Path(dir_path).exists():
                run_sheets_path = Path(dir_path)
                break
        
        if not run_sheets_path:
            print(f"Error: No run sheets directory found")
            print(f"Checked: {', '.join([d for d in possible_dirs if d])}")
            print(f"Creating RunSheets/ directory...")
            run_sheets_path = Path("RunSheets")
            run_sheets_path.mkdir(parents=True, exist_ok=True)
            print(f"Please add run sheet files to RunSheets/")
            return
        
        print(f"Using directory: {run_sheets_path}")
        print()
        
        # Find all supported files (including subdirectories)
        files = []
        for ext in ['*.pdf', '*.PDF', '*.csv', '*.CSV', '*.txt', '*.TXT']:
            files.extend(run_sheets_path.glob(ext))
            files.extend(run_sheets_path.glob(f'**/{ext}'))  # Check subdirectories
        
        # Remove duplicates
        files = list(set(files))
        
        if not files:
            print(f"No run sheet files found in {run_sheets_path}/")
            return
        
        print(f"Found {len(files)} run sheet files")
        print()
        
        total_imported = 0
        for file_path in sorted(files):
            total_imported += self.import_run_sheet(file_path)
        
        print()
        print("=" * 60)
        print(f"Import complete: {total_imported} jobs imported")
        
        # Show summary
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*), COUNT(DISTINCT date) FROM run_sheet_jobs")
        total_jobs, unique_dates = cursor.fetchone()
        
        print(f"Total jobs in database: {total_jobs}")
        print(f"Unique dates: {unique_dates}")
        print("=" * 60)
    
    def show_summary(self):
        """Show summary of imported run sheet data."""
        cursor = self.conn.cursor()
        
        print()
        print("=" * 60)
        print("RUN SHEET SUMMARY")
        print("=" * 60)
        
        # Total jobs
        cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs")
        total = cursor.fetchone()[0]
        print(f"Total jobs: {total}")
        
        # By customer
        cursor.execute("""
            SELECT customer, COUNT(*) as count
            FROM run_sheet_jobs
            WHERE customer IS NOT NULL
            GROUP BY customer
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print()
        print("Top 10 Customers:")
        for customer, count in cursor.fetchall():
            print(f"  {customer}: {count} jobs")
        
        # By activity
        cursor.execute("""
            SELECT activity, COUNT(*) as count
            FROM run_sheet_jobs
            WHERE activity IS NOT NULL
            GROUP BY activity
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print()
        print("Top Activities:")
        for activity, count in cursor.fetchall():
            print(f"  {activity}: {count} jobs")
        
        print("=" * 60)
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    """Run import."""
    import sys
    
    # Check for custom name argument
    name = sys.argv[1] if len(sys.argv) > 1 else "Daniel Hanson"
    
    importer = RunSheetImporter(name=name)
    
    try:
        importer.import_all_run_sheets()
        importer.show_summary()
    finally:
        importer.close()


if __name__ == "__main__":
    main()
