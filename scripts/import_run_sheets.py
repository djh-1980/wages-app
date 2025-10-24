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
                driver TEXT,
                jobs_on_run INTEGER,
                job_number TEXT,
                customer TEXT,
                activity TEXT,
                priority TEXT,
                job_address TEXT,
                postcode TEXT,
                instructions_1 TEXT,
                instructions_2 TEXT,
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
                lines = page_text.split('\n')
                
                # Check if this page is for the specified person
                is_my_page = False
                for i in range(min(5, len(lines))):
                    if self.name.lower() in lines[i].lower():
                        is_my_page = True
                        break
                
                if not is_my_page:
                    continue
                
                # Extract header info (date, driver, jobs on run) from line 3
                # Format: "Date 25/10/2025 Depot Warrington Driver Hanson, Daniel Jobs on Run 8"
                header_date = None
                header_driver = None
                jobs_on_run = None
                
                for line in lines[:5]:
                    if 'Date' in line and 'Driver' in line and 'Jobs on Run' in line:
                        date_match = re.search(r'Date\s+(\d{2}/\d{2}/\d{4})', line)
                        if date_match:
                            header_date = date_match.group(1)
                        
                        driver_match = re.search(r'Driver\s+([^J]+?)(?:\s+Jobs)', line)
                        if driver_match:
                            header_driver = driver_match.group(1).strip()
                        
                        jobs_match = re.search(r'Jobs on Run\s+(\d+)', line)
                        if jobs_match:
                            jobs_on_run = int(jobs_match.group(1))
                        break
                
                # Find job entry
                for i, line in enumerate(lines):
                    if not line.strip().startswith('Job #'):
                        continue
                    
                    job = {
                        'date': header_date,
                        'driver': header_driver,
                        'jobs_on_run': jobs_on_run
                    }
                    
                    # Extract job number
                    job_match = re.search(r'Job #\s*(\d+)', line)
                    if job_match:
                        job['job_number'] = job_match.group(1)
                    
                    # Parse subsequent lines for job details
                    address_lines = []
                    collecting_address = False
                    
                    for j in range(i+1, min(i+40, len(lines))):
                        curr_line = lines[j].strip()
                        
                        # Customer - line starting with "Customer Signature" or "Customer Print"
                        if curr_line.startswith('Customer Signature') or curr_line.startswith('Customer Print'):
                            customer = curr_line.replace('Customer Signature', '').replace('Customer Print', '').strip()
                            if customer:
                                job['customer'] = customer
                        
                        # Activity - TECH EXCHANGE, etc.
                        if not job.get('activity'):
                            activity_patterns = ['TECH EXCHANGE', 'NON TECH EXCHANGE', 'REPAIR WITH PARTS', 
                                               'REPAIR WITHOUT PARTS', 'CONSUMABLE INSTALL', 'COLLECTION', 'DELIVERY', 'INSTALL']
                            for pattern in activity_patterns:
                                if pattern in curr_line.upper():
                                    job['activity'] = pattern
                                    break
                        
                        # Priority - 4HR, ND 1700, etc. (comes after "Priority" label or activity)
                        if not job.get('priority') and job.get('activity'):
                            priority_match = re.match(r'^(4HR|8HR|6HR|ND\s+\d+)$', curr_line)
                            if priority_match:
                                job['priority'] = priority_match.group(1)
                        
                        # Instructions 1 - lines with part numbers and descriptions (e.g., "3446536 - DT - HME Nexeo...")
                        # OR lines with // pattern (e.g., "38960886//32013//PPD")
                        # OR lines with ALT/PART pattern (e.g., "ALT1=_O2HEP3DS22AV")
                        if not job.get('instructions_1'):
                            if re.match(r'^\d{7,8}\s*-\s*DT\s*-', curr_line):
                                # Collect multiple DT instruction lines
                                inst1_lines = [curr_line]
                                # Look ahead for more instruction lines
                                for k in range(j+1, min(j+5, len(lines))):
                                    next_inst = lines[k].strip()
                                    if re.match(r'^\d{7,8}\s*-\s*DT\s*-', next_inst):
                                        inst1_lines.append(next_inst)
                                job['instructions_1'] = '; '.join(inst1_lines)
                            elif '//' in curr_line:
                                # Extract reference numbers with // pattern
                                job['instructions_1'] = curr_line
                            elif re.match(r'ALT\d+=', curr_line) or re.match(r'PART\d+=', curr_line):
                                # Collect ALT/PART lines and the part number line
                                inst1_lines = []
                                for k in range(j, min(j+10, len(lines))):
                                    line_check = lines[k].strip()
                                    if re.match(r'(ALT|PART)\d+=', line_check) and '=' in line_check:
                                        # Extract the value after =
                                        value = line_check.split('=')[1].strip()
                                        if value:
                                            inst1_lines.append(value)
                                    elif re.match(r'^[A-Z0-9_-]+\s+x\s+\d+', line_check):
                                        # Part number with quantity (e.g., "_O2HEP3DS22AV-V1-23 x 1")
                                        inst1_lines.append(line_check.split('Problem:')[0].strip())
                                        break
                                if inst1_lines:
                                    job['instructions_1'] = '; '.join(inst1_lines)
                        
                        # Instructions 2 - longer text with keywords like "Replace", "Please", "Problem:", etc.
                        if not job.get('instructions_2'):
                            # Look for instruction keywords
                            keywords = ['Replace', 'Please record', 'without fail', 'Call your depot', 
                                      'Problem:', 'Action:', '**Please sign in']
                            if any(keyword in curr_line for keyword in keywords):
                                # Collect this and following lines until we hit a blank or new section
                                inst2_lines = [curr_line]
                                for k in range(j+1, min(j+10, len(lines))):
                                    next_inst = lines[k].strip()
                                    if not next_inst or next_inst.startswith('Page ') or re.match(r'^\d{10,}', next_inst) or next_inst.startswith('Call history'):
                                        break
                                    inst2_lines.append(next_inst)
                                job['instructions_2'] = ' '.join(inst2_lines)
                        
                        # Address collection - starts after we see a phone number (with or without +) or "MANAGER" or contact name with number
                        # Also starts after Ref 1 number (8 digits) or after a line like "1." or "1 " or "0MANAGER"
                        if (re.match(r'^\d{10,}', curr_line) or 
                            re.match(r'^\+\d{10,}', curr_line) or 
                            curr_line == 'MANAGER' or
                            re.match(r'^\d[A-Za-z]+$', curr_line) or  # e.g., "1Ryan", "0MANAGER"
                            re.match(r'^\d+\.$', curr_line) or  # e.g., "1."
                            re.match(r'^\d+\s*$', curr_line) or  # e.g., "1 " or "1"
                            re.match(r'^\d{8}$', curr_line)):  # Ref 1 number
                            collecting_address = True
                            # If it's a ref number, skip it but start collecting
                            if re.match(r'^\d{8}$', curr_line):
                                continue
                            # If it's a phone or contact or just number, skip it
                            continue
                        
                        # Collect address lines (between start marker and postcode)
                        if collecting_address:
                            # Skip empty lines and lines that are just dots
                            if not curr_line or re.match(r'^\.+$', curr_line):
                                continue
                            
                            # Skip lines that are clearly not address (payment info, contact names, etc.)
                            if (curr_line.startswith('PO ') or 
                                'Service Desk:' in curr_line or
                                re.match(r'^\d[A-Za-z\s]+$', curr_line) or  # e.g., "1Ellie Fitzgerald"
                                re.match(r'^0[A-Z\s]+$', curr_line)):  # e.g., "0MASON MELLOR"
                                continue
                            
                            # UK postcode pattern
                            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', curr_line)
                            if postcode_match:
                                job['postcode'] = postcode_match.group(1)
                                # Add this line to address if it has more than just postcode
                                if len(curr_line) > len(job['postcode']) + 2:
                                    clean_line = curr_line.replace(job['postcode'], '').strip()
                                    # Remove leading dots
                                    clean_line = re.sub(r'^\.+', '', clean_line).strip()
                                    if clean_line:
                                        address_lines.append(clean_line)
                                collecting_address = False
                            elif curr_line and not curr_line.startswith('Page '):
                                # Clean leading dots
                                clean_line = re.sub(r'^\.+', '', curr_line).strip()
                                if clean_line:
                                    address_lines.append(clean_line)
                        
                        # Stop at next job or page end
                        if curr_line.startswith('Job #') or curr_line.startswith('Page '):
                            break
                    
                    # Combine address lines
                    if address_lines:
                        job['job_address'] = ', '.join([a for a in address_lines if a])
                    
                    # Add job if valid
                    if job.get('job_number') and job.get('customer'):
                        jobs.append(job)
        
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
                            date, driver, jobs_on_run, job_number, customer, activity, 
                            priority, job_address, postcode, instructions_1, instructions_2, notes, source_file
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        job.get('date'),
                        job.get('driver'),
                        job.get('jobs_on_run'),
                        job.get('job_number'),
                        job.get('customer'),
                        job.get('activity'),
                        job.get('priority'),
                        job.get('job_address'),
                        job.get('postcode'),
                        job.get('instructions_1'),
                        job.get('instructions_2'),
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
