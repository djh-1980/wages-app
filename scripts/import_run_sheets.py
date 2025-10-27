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
                        
                        # Address collection - starts after we see a phone number (with or without +) or "MANAGER" or contact name with number
                        # Also starts after Ref 1 number (8 digits) or after a line like "1." or "1 " or "0MANAGER"
                        # NEW: Also starts after contact name like "1WILLIAM HARRIS" or "tbcWILLIAM HARRIS"
                        # But NOT store codes like "16661UK 6661UK" or "1614510810TESCO"
                        try:
                            if (re.match(r'^\d{10,}', curr_line) or 
                                re.match(r'^\+\d{10,}', curr_line) or
                                re.search(r'\d{4,}\s+\d{3,}\s+\d{3,}\s*\/\s*\d', curr_line) or  # Phone with slash like "02920 320 193 / 07741 248 780" 
                                curr_line == 'MANAGER' or
                                (re.match(r'^\d[A-Z0-9\s]+$', curr_line) and 
                                 len(curr_line) > 8 and 
                                 not re.match(r'^\d+[A-Z]+\s+\d+', curr_line) and  # Not store codes like "16661UK 6661UK"
                                 (' ' in curr_line or re.search(r'[A-Z]{3,}', curr_line))) or  # Has space OR 3+ consecutive letters
                                re.match(r'^tbc[A-Z\s]+$', curr_line) or  # e.g., "tbcWILLIAM HARRIS"
                                re.match(r'^\d+\.$', curr_line) or  # e.g., "1."
                                re.match(r'^\d+\s*$', curr_line) or  # e.g., "1 " or "1"
                                re.match(r'^\d{8,10}$', curr_line)):  # Ref 1 number (8-10 digits)
                                collecting_address = True
                                # If it's a ref number, skip it but start collecting
                                if re.match(r'^\d{8,10}$', curr_line):
                                    continue
                                # If it's a phone or contact or just number, skip it
                                continue
                        except re.error as regex_err:
                            # Skip this line if regex fails
                            print(f"  ⚠️  Regex error on line: {curr_line[:50]}")
                            continue
                        
                        # Collect address lines (between start marker and postcode)
                        if collecting_address:
                            # Skip empty lines and lines that are just dots
                            if not curr_line or re.match(r'^\.+$', curr_line):
                                continue
                            
                            # Skip lines that are clearly not address (payment info, instructions, etc.)
                            # Stop collecting if we hit instructions/notes
                            if (curr_line.startswith('PO ') or 
                                'Service Desk:' in curr_line or
                                curr_line.startswith('Home User') or
                                curr_line.startswith('Hand over') or
                                curr_line.startswith('ALONG WITH') or
                                curr_line.startswith('Country:') or
                                curr_line.startswith('Summary:') or
                                curr_line.startswith('Subject:') or
                                curr_line.startswith('Troubleshooting:') or
                                curr_line.startswith('Problem description') or
                                'engineer must' in curr_line.lower() or
                                re.search(r'\d\:\d\d', curr_line) or  # Time patterns like "9:00"
                                re.match(r'^\d[a-z]', curr_line)):  # e.g., "1Ellie" (lowercase after digit)
                                # Stop collecting address if we hit instructions
                                collecting_address = False
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
                                # Skip reference codes like "16661UK 6661UK" or "1614510810TESCO"
                                if re.match(r'^\d+[A-Z]+\s+\d+[A-Z]+$', curr_line):  # e.g., "16661UK 6661UK"
                                    continue
                                if re.match(r'^\d{10,}[A-Z]+$', curr_line):  # e.g., "1614510810TESCO"
                                    continue
                                    
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
                    # Skip RICO Depot jobs with no activity (not real jobs - just depot visits)
                    if job.get('job_number') and job.get('customer'):
                        customer = job.get('customer', '').upper()
                        activity = job.get('activity', '')
                        
                        # Skip RICO Depots without activity
                        if 'RICO' in customer and not activity:
                            continue
                        
                        jobs.append(job)
        
        return jobs
    
    def import_run_sheet(self, file_path: Path, base_path: Path = None) -> int:
        """Import a single run sheet file."""
        # Check if this file has already been imported
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs WHERE source_file = ?", (file_path.name,))
        already_imported = cursor.fetchone()[0] > 0
        
        if already_imported:
            # Skip already imported files
            return 0
        
        if base_path:
            relative_path = file_path.relative_to(base_path)
            print(f"Processing: {relative_path}")
        else:
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
                            priority, job_address, postcode, notes, source_file
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            import traceback
            print(f"  ✗ Error: {e}")
            print(f"  Traceback: {traceback.format_exc()}")
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
        
        # Group files by year/month if organized
        from collections import defaultdict
        files_by_folder = defaultdict(list)
        
        for file_path in sorted(files):
            # Check if file is in year/month structure
            parts = file_path.relative_to(run_sheets_path).parts
            if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit():
                # Organized: 2024/10/filename.pdf
                folder_key = f"{parts[0]}/{parts[1]}"
                files_by_folder[folder_key].append(file_path)
            else:
                # Root level
                files_by_folder['root'].append(file_path)
        
        total_imported = 0
        files_processed = 0
        files_skipped = 0
        total_files = len(files)
        
        print(f"\n🔍 Checking {total_files} files for new data...")
        print()
        
        # Process organized folders first
        for folder in sorted(files_by_folder.keys()):
            if folder == 'root':
                continue
            
            year, month = folder.split('/')
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            month_name = month_names[int(month) - 1]
            
            print(f"📁 {year}/{month} ({month_name}) - {len(files_by_folder[folder])} files")
            print("-" * 60)
            
            for file_path in files_by_folder[folder]:
                imported = self.import_run_sheet(file_path, run_sheets_path)
                total_imported += imported
                files_processed += 1
                if imported == 0:
                    files_skipped += 1
                
                # Show progress every 50 files
                if files_processed % 50 == 0:
                    print(f"Progress: {files_processed}/{total_files} files ({int(files_processed/total_files*100)}%) - {files_skipped} skipped, {total_imported} jobs imported")
            
            print()
        
        # Process root files
        if 'root' in files_by_folder:
            print(f"📁 Root directory - {len(files_by_folder['root'])} files")
            print("-" * 60)
            
            for file_path in files_by_folder['root']:
                imported = self.import_run_sheet(file_path, run_sheets_path)
                total_imported += imported
                files_processed += 1
                if imported == 0:
                    files_skipped += 1
                
                # Show progress every 50 files
                if files_processed % 50 == 0:
                    print(f"Progress: {files_processed}/{total_files} files ({int(files_processed/total_files*100)}%) - {files_skipped} skipped, {total_imported} jobs imported")
            
            print()
        
        print()
        print("=" * 60)
        print(f"Import complete!")
        print(f"  Files processed: {files_processed}")
        print(f"  Files skipped (already imported): {files_skipped}")
        print(f"  New jobs imported: {total_imported}")
        print("=" * 60)
        
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
    import argparse
    
    parser = argparse.ArgumentParser(description='Import run sheets from PDFs')
    parser.add_argument('--name', default='Daniel Hanson', help='Driver name to search for')
    parser.add_argument('--recent', type=int, help='Only import files modified in last N days')
    args = parser.parse_args()
    
    importer = RunSheetImporter(name=args.name)
    
    try:
        if args.recent:
            # Only import recent files
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=args.recent)
            
            print(f"Only importing files modified after {cutoff_date.strftime('%Y-%m-%d')}")
            
            # Filter files by modification time
            run_sheets_path = Path('RunSheets')
            files = []
            for ext in ['*.pdf', '*.PDF']:
                for file_path in run_sheets_path.rglob(ext):
                    if datetime.fromtimestamp(file_path.stat().st_mtime) > cutoff_date:
                        files.append(file_path)
            
            print(f"Found {len(files)} recent files")
            
            imported = 0
            for file_path in files:
                imported += importer.import_run_sheet(file_path, run_sheets_path)
            
            print(f"\nImported {imported} jobs from {len(files)} files")
        else:
            importer.import_all_run_sheets()
        
        importer.show_summary()
    finally:
        importer.close()


if __name__ == "__main__":
    main()
