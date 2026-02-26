#!/usr/bin/env python3
"""
Import daily run sheets and extract job information.
Scans for: Name, Date, Job Number, Customer, Activity
"""

import sys
import os
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import csv
import logging
import sys

# Add app to path for config import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.config import Config

# Add testing directory to path for Camelot parser
sys.path.insert(0, str(Path(__file__).parent.parent / 'testing'))
try:
    from camelot_runsheet_parser import CamelotRunsheetParser
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False


class RunSheetImporter:
    def __init__(self, db_path: str = "data/database/payslips.db", name: str = "Daniel Hanson"):
        self.db_path = db_path
        self.conn = None
        self.name = name
        self.setup_logging()
        self.setup_database()
        
        # Track dates that have been overwritten in this session
        self.overwritten_dates = set()
        
        # Enhanced activity patterns for better recognition
        self.activity_patterns = [
            'TECH EXCHANGE', 'NON TECH EXCHANGE', 'REPAIR WITH PARTS', 
            'REPAIR WITHOUT PARTS', 'CONSUMABLE INSTALL', 'COLLECTION', 
            'DELIVERY', 'INSTALL', 'MAINTENANCE', 'SURVEY', 'INSPECTION',
            'UPGRADE', 'CONFIGURATION', 'TRAINING', 'CONSULTATION'
        ]
        
        # UK postcode validation pattern
        self.postcode_pattern = re.compile(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b')
        
        # Customer name cleaning patterns
        self.customer_cleanup_patterns = [
            (r'^Customer Signature\s*', ''),
            (r'^Customer Print\s*', ''),
            (r'\*\*\*[^*]*\*\*\*', ''),  # Remove ***text***
            (r'\s+', ' '),  # Multiple spaces to single
            (r'^\s+|\s+$', ''),  # Trim whitespace
        ]
    
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
                status TEXT DEFAULT 'pending',
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, job_number)
            )
        """)
        
        # Add status column if it doesn't exist (for existing databases)
        try:
            cursor.execute("ALTER TABLE run_sheet_jobs ADD COLUMN status TEXT DEFAULT 'pending'")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Add route_order column if it doesn't exist (for route optimization)
        try:
            cursor.execute("ALTER TABLE run_sheet_jobs ADD COLUMN route_order INTEGER")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Add manually_uploaded column to protect manual uploads from auto-sync overwrites
        try:
            cursor.execute("ALTER TABLE run_sheet_jobs ADD COLUMN manually_uploaded INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        self.conn.commit()
    
    def setup_logging(self):
        """Setup logging for better debugging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def clean_customer_name(self, customer_line: str) -> str:
        """Clean customer name from various formats and artifacts."""
        customer = customer_line
        
        # Apply cleanup patterns
        for pattern, replacement in self.customer_cleanup_patterns:
            customer = re.sub(pattern, replacement, customer)
        
        # Remove common artifacts
        customer = re.sub(r'^[0-9]+\s*', '', customer)  # Remove leading numbers
        customer = re.sub(r'\s*-\s*$', '', customer)  # Remove trailing dash
        customer = re.sub(r'^[^\w]+', '', customer)  # Remove leading non-word chars
        
        return customer.strip()
    
    def extract_activity(self, line: str) -> Optional[str]:
        """Extract activity from line using enhanced pattern matching."""
        line_upper = line.upper()
        
        # Check for exact matches first
        for pattern in self.activity_patterns:
            if pattern in line_upper:
                return pattern
        
        # Check for partial matches or variations
        activity_variations = {
            'TECH': 'TECH EXCHANGE',
            'NON TECH': 'NON TECH EXCHANGE',
            'REPAIR': 'REPAIR WITH PARTS',
            'CONSUMABLE': 'CONSUMABLE INSTALL',
            'COLLECT': 'COLLECTION',
            'DELIVER': 'DELIVERY'
        }
        
        for key, activity in activity_variations.items():
            if key in line_upper:
                return activity
        
        return None
    
    def extract_postcode(self, line: str) -> Optional[str]:
        """Extract and validate UK postcode from line."""
        match = self.postcode_pattern.search(line.upper())
        if match:
            postcode = match.group(1)
            # Ensure proper spacing in postcode
            if len(postcode) >= 6 and ' ' not in postcode:
                postcode = postcode[:-3] + ' ' + postcode[-3:]
            return postcode
        return None
    
    def clean_address_line(self, line: str) -> str:
        """Clean individual address line."""
        if not line:
            return ""
        
        # Remove leading dots and numbers
        clean_line = re.sub(r'^[.\d\s]*', '', line).strip()
        
        # Remove common artifacts
        clean_line = re.sub(r'^[-,\s]+', '', clean_line)  # Leading punctuation
        clean_line = re.sub(r'[-,\s]+$', '', clean_line)  # Trailing punctuation
        
        # Remove contact names that start with numbers
        if re.match(r'^\d+[A-Z][a-z]', clean_line):  # e.g., "1Ellie"
            return ""
        
        # Skip lines that are clearly not address parts
        skip_patterns = [
            r'^\d{8,}$',  # Long numbers
            r'^[A-Z]{2,}\d+$',  # Store codes
            r'^\+?\d{10,}$',  # Phone numbers
            r'^MANAGER$',
            r'^tbc[A-Z]',  # Contact names like "tbcWILLIAM"
        ]
        
        for pattern in skip_patterns:
            if re.match(pattern, clean_line):
                return ""
        
        return clean_line
    
    def combine_address_lines(self, address_lines: List[str]) -> str:
        """Combine and clean address lines into a coherent address."""
        if not address_lines:
            return ""
        
        # Filter out empty and invalid lines
        valid_lines = [line for line in address_lines if line and len(line.strip()) > 1]
        
        if not valid_lines:
            return ""
        
        # Join with commas and clean up
        address = ', '.join(valid_lines)
        
        # Clean up common issues
        address = re.sub(r',\s*,', ',', address)  # Double commas
        address = re.sub(r'^,\s*', '', address)  # Leading comma
        address = re.sub(r'\s*,$', '', address)  # Trailing comma
        address = re.sub(r'\s+', ' ', address)  # Multiple spaces
        
        return address.strip()
    
    def validate_job(self, job: Dict) -> bool:
        """Validate job data before adding to database."""
        # Must have job number and either customer or activity
        if not job.get('job_number'):
            return False
        
        if not job.get('customer') and not job.get('activity'):
            return False
        
        # Skip RICO Depot jobs with no activity (not real jobs)
        customer = job.get('customer', '').upper()
        activity = job.get('activity', '')
        
        if 'RICO' in customer and not activity:
            return False
        
        # Skip PayPoint Van Stock Audits (zero pay jobs)
        if ('PAYPOINT' in customer.upper() and 
            ('VAN STOCK AUDIT' in customer.upper() or 'AUDIT' in activity.upper())):
            return False
        
        return True
    
    def clean_job_data(self, job: Dict) -> Dict:
        """Clean and standardize job data."""
        cleaned_job = job.copy()
        
        # Clean customer name
        if cleaned_job.get('customer'):
            cleaned_job['customer'] = self.clean_customer_name(cleaned_job['customer'])
        
        # Standardize activity
        if cleaned_job.get('activity'):
            activity = cleaned_job['activity'].upper().strip()
            # Map common variations to standard names
            activity_mapping = {
                'TECH EX': 'TECH EXCHANGE',
                'NON TECH EX': 'NON TECH EXCHANGE',
                'REPAIR W/ PARTS': 'REPAIR WITH PARTS',
                'REPAIR W/O PARTS': 'REPAIR WITHOUT PARTS',
            }
            cleaned_job['activity'] = activity_mapping.get(activity, activity)
        
        # Clean address
        if cleaned_job.get('job_address'):
            address = cleaned_job['job_address']
            # Remove excessive commas and spaces
            address = re.sub(r',\s*,+', ',', address)
            address = re.sub(r'\s+', ' ', address)
            cleaned_job['job_address'] = address.strip()
        
        # Validate and clean postcode
        if cleaned_job.get('postcode'):
            postcode = cleaned_job['postcode'].upper().strip()
            # Ensure proper format
            if len(postcode) >= 6 and ' ' not in postcode:
                postcode = postcode[:-3] + ' ' + postcode[-3:]
            cleaned_job['postcode'] = postcode
        
        return cleaned_job
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all text from a PDF file using pdfplumber for better quality."""
        try:
            import pdfplumber
            
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
            
        except ImportError:
            # Fallback to PyPDF2 if pdfplumber not available
            print("Warning: pdfplumber not installed, using PyPDF2 fallback")
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error with pdfplumber, falling back to PyPDF2: {e}")
            # Fallback to PyPDF2 on any error
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
        """Parse PDF using Camelot table extraction (with text fallback)."""
        
        # Try Camelot first (99% quality)
        if CAMELOT_AVAILABLE:
            try:
                parser = CamelotRunsheetParser(driver_name=self.name)
                jobs = parser.parse_pdf(pdf_path)
                
                if len(jobs) > 0:
                    self.logger.info(f"Camelot extracted {len(jobs)} jobs from {Path(pdf_path).name}")
                    return jobs
                else:
                    self.logger.warning(f"Camelot found no jobs, trying text parsing")
            except Exception as e:
                self.logger.warning(f"Camelot failed: {e}, falling back to text parsing")
        
        # Fallback to text parsing
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
                
                # Detect runsheet format
                is_multi_driver = self.detect_multi_driver_format(lines)
                
                if is_multi_driver:
                    # Use multi-driver parsing logic
                    page_jobs = self.parse_multi_driver_page(lines)
                else:
                    # Use single-driver parsing logic
                    page_jobs = self.parse_single_driver_page(lines)
                
                jobs.extend(page_jobs)
        
        return jobs
    
    def detect_multi_driver_format(self, lines: List[str]) -> bool:
        """Detect if this is a multi-driver runsheet format."""
        # Multi-driver runsheets have specific patterns
        for line in lines[:10]:
            if ('SLA Window' in line or 
                'Contact Name' in line or
                'Activity Contact Phone' in line):
                return True
        return False
    
    def parse_multi_driver_page(self, lines: List[str]) -> List[Dict]:
        """Parse multi-driver runsheet format with customer-specific parsing."""
        jobs = []
        
        # Extract header info (date, driver, jobs on run)
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
        
        # Find job entries
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
            
            # Get job content for customer-specific parsing
            job_lines = []
            for j in range(i+1, min(i+35, len(lines))):  # Increased from 25 to 35 to capture postcodes
                curr_line = lines[j].strip()
                if curr_line.startswith('Job #'):
                    break
                job_lines.append(curr_line)
            
            # First, get the customer to determine parsing method
            customer = self.extract_customer_from_lines(job_lines)
            if customer:
                job['customer'] = customer
                
                # Use customer-specific parsing
                if 'POSTURITE' in customer.upper():
                    self.parse_posturite_job(job, job_lines)
                elif 'EPAY' in customer.upper():
                    self.parse_epay_job(job, job_lines)
                elif 'XEROX' in customer.upper():
                    self.parse_xerox_job(job, job_lines)
                elif 'ASTRA ZENECA' in customer.upper():
                    self.parse_astra_zeneca_job(job, job_lines)
                elif 'STAR TRAINS' in customer.upper():
                    self.parse_star_trains_job(job, job_lines)
                elif 'BANKS' in customer.upper() and 'FUJITSU' in customer.upper():
                    self.parse_fujitsu_banks_job(job, job_lines)
                elif 'EE - ME' in customer.upper() and 'FUJITSU' in customer.upper():
                    self.parse_fujitsu_ee_me_job(job, job_lines)
                elif 'EE - P2PE' in customer.upper() and 'FUJITSU' in customer.upper():
                    self.parse_fujitsu_ee_p2pe_job(job, job_lines)
                elif 'EE' in customer.upper() and 'FUJITSU' in customer.upper():
                    self.parse_fujitsu_ee_job(job, job_lines)
                elif 'SPECSAVERS' in customer.upper() and 'FUJITSU' in customer.upper():
                    self.parse_specsavers_job(job, job_lines)
                elif 'HSBC' in customer.upper():
                    self.parse_hsbc_job(job, job_lines)
                elif customer.upper() == 'COMPUTACENTER LIMITED':
                    self.parse_computacenter_limited_job(job, job_lines)
                elif 'JOHN LEWIS' in customer.upper():
                    self.parse_john_lewis_job(job, job_lines)
                elif 'PAYPOINT' in customer.upper():
                    self.parse_paypoint_job(job, job_lines)
                elif 'VISTA' in customer.upper():
                    self.parse_vista_job(job, job_lines)
                elif 'KINGFISHER' in customer.upper():
                    self.parse_kingfisher_job(job, job_lines)
                elif 'SECURE RETAIL' in customer.upper():
                    self.parse_secure_retail_job(job, job_lines)
                elif 'NCR TESCO' in customer.upper():
                    self.parse_ncr_tesco_job(job, job_lines)
                elif 'DHL SUPPLY CHAIN' in customer.upper():
                    self.parse_dhl_job(job, job_lines)
                elif 'HORIZON PROJECT' in customer.upper():
                    self.parse_horizon_project_job(job, job_lines)
                elif 'SMART CT' in customer.upper():
                    self.parse_smart_ct_job(job, job_lines)
                elif 'RHENUS' in customer.upper():
                    self.parse_rhenus_job(job, job_lines)
                elif 'VERIFONE' in customer.upper():
                    self.parse_verifone_job(job, job_lines)
                elif 'COGNIZANT' in customer.upper():
                    self.parse_cognizant_job(job, job_lines)
                elif 'LEXMARK' in customer.upper() or 'FUJITSU' in customer.upper() or 'COMPUTACENTER' in customer.upper() or 'CXM' in customer.upper():
                    self.parse_tech_job(job, job_lines)
                else:
                    # Generic parsing for unknown customers
                    self.parse_generic_job(job, job_lines)
            
            # Validate and add job
            if self.validate_job(job):
                cleaned_job = self.clean_job_data(job)
                jobs.append(cleaned_job)
        
        return jobs
    
    def extract_customer_from_lines(self, job_lines: List[str]) -> str:
        """Extract customer name from job lines."""
        for line in job_lines:
            if line.startswith('Customer Signature'):
                return line.replace('Customer Signature', '').strip()
        return None
    
    def parse_posturite_job(self, job: Dict, job_lines: List[str]):
        """Parse POSTURITE jobs - furniture installation."""
        # Extract specific activity type
        for line in job_lines:
            if 'DESK INSTALL' in line:
                job['activity'] = 'DESK INSTALL'
                break
            elif 'CHAIR SP INSTALL' in line:
                job['activity'] = 'CHAIR SP INSTALL'
                break
        
        if 'activity' not in job:
            job['activity'] = 'INSTALL'  # Default fallback
        
        # Look for address in POSTURITE format
        address_parts = []
        postcode = None
        collecting_address = False
        contact_name = None
        
        for i, line in enumerate(job_lines):
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('DESK INSTALL') or line.startswith('CHAIR SP') or
                re.match(r'^[A-Z]{3}\d+$', line) or  # DEL codes
                line.startswith('ND ') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line)):  # dates
                continue
            
            # Extract contact name (after phone number)
            if re.match(r'^\d{11}[A-Z][A-Z\s]+$', line):  # e.g., "07709858783JOANNE CARR"
                contact_name = re.sub(r'^\d{11}', '', line).strip()
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines (street, area, town) - continue until postcode
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    not line.startswith('hour before arrival') and  # Skip instruction continuations
                    len(address_parts) < 6):  # Allow more address parts and continue until postcode
                    
                    clean_line = line.strip(' .,')
                    if clean_line and clean_line not in address_parts:
                        address_parts.append(clean_line)
        
        # Build final address with contact name first
        final_address_parts = []
        if contact_name:
            final_address_parts.append(contact_name)
        final_address_parts.extend(address_parts)
        
        if final_address_parts:
            job['job_address'] = ', '.join(final_address_parts)
    
    def parse_epay_job(self, job: Dict, job_lines: List[str]):
        """Parse EPAY jobs - collections."""
        job['activity'] = 'COLLECTION'
        
        # Look for store name and location
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('COLLECTION') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line)):  # dates
                continue
            
            # Start collecting address after phone number line
            if re.match(r'^\d{11}[A-Z\s]+STORE', line):  # e.g., "07873640608 FOUNDRY ARMS STORE"
                collecting_address = True
                # Extract store name from this line
                store_name = re.sub(r'^\d{11}\s*', '', line).strip()
                if store_name:
                    address_parts.append(store_name)
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines (store, street, area, town)
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    len(address_parts) < 5):  # Allow more address parts for EPAY
                    
                    clean_line = line.strip(' .,')
                    if clean_line and clean_line not in address_parts:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_tech_job(self, job: Dict, job_lines: List[str]):
        """Parse tech jobs - Lexmark, Fujitsu, Computacenter, CXM, Vista."""
        # Determine activity type - check for NON TECH EXCHANGE first
        activity_found = False
        for line in job_lines:
            if 'NON TECH EXCHANGE' in line.upper():
                job['activity'] = 'NON TECH EXCHANGE'
                activity_found = True
                break
            elif 'TECH EXCHANGE' in line.upper():
                job['activity'] = 'TECH EXCHANGE'
                activity_found = True
                break
            elif any(activity in line.upper() for activity in ['REPAIR WITH PARTS', 'REPAIR WITHOUT PARTS']):
                for activity in ['REPAIR WITH PARTS', 'REPAIR WITHOUT PARTS']:
                    if activity in line.upper():
                        job['activity'] = activity
                        activity_found = True
                        break
                if activity_found:
                    break
        
        if not activity_found:
            job['activity'] = 'TECH EXCHANGE'  # Default for tech jobs
        
        # Look for location information - different structure per customer
        address_parts = []
        postcode = None
        collecting_address = False
        
        for i, line in enumerate(job_lines):
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('TECH EXCHANGE') or line.startswith('NON TECH EXCHANGE') or
                re.match(r'^\d+$', line) or  # Pure numbers
                line.startswith('ND ') or line.startswith('Priority MC') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line)):  # dates
                continue
            
            # Start collecting address after contact name or company identifier
            if (re.match(r'^\d+[A-Z][A-Z\s]+$', line) or  # e.g., "3AISTE STATKEVICIUTE"
                'UK FOODS STORE LIMITED' in line or
                'WM MORRISON SUPERMARKETS PLC' in line or  # Specific for Computacenter
                'SUPERMARKETS PLC' in line or
                'ORANGE (' in line or
                'ERNEST JONES' in line):
                collecting_address = True
                # If this line contains company info, add it (clean phone numbers)
                if any(company in line for company in ['UK FOODS STORE LIMITED', 'WM MORRISON SUPERMARKETS PLC', 'SUPERMARKETS PLC', 'ORANGE (', 'ERNEST JONES']):
                    clean_line = re.sub(r'^[\d\s]+', '', line).strip(' .,')  # Remove phone numbers (with spaces)
                    if clean_line and clean_line not in address_parts:
                        address_parts.append(clean_line)
                # Special handling for Computacenter/Morrison format
                elif 'WM MORRISON' in line and re.search(r'^[\d\s]+', line):
                    # This is the phone number + WM MORRISON line
                    clean_line = re.sub(r'^[\d\s]+', '', line).strip(' .,')
                    if clean_line and clean_line not in address_parts:
                        address_parts.append(clean_line)
                # Special handling for Fujitsu/Orange format - clean phone numbers
                elif 'ORANGE (' in line and re.search(r'^[\d\s]+', line):
                    # This is the phone number + ORANGE line
                    clean_line = re.sub(r'^[\d\s]+', '', line).strip(' .,')
                    if clean_line and clean_line not in address_parts:
                        address_parts.append(clean_line)
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines (company, street, area, town)
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    not line.startswith('.') and  # Skip single dots
                    len(address_parts) < 5):  # Allow more address parts for tech jobs
                    
                    clean_line = line.strip(' .,')
                    if clean_line and clean_line not in address_parts:
                        # Special handling for Morrison format - combine fragments
                        if clean_line == 'SUPERMARKETS PLC' and address_parts:
                            # Check if previous line was WM MORRISON (or contains it)
                            if 'WM MORRISON' in address_parts[-1] and 'SUPERMARKETS PLC' not in address_parts[-1]:
                                # Combine with previous WM MORRISON to make full name
                                address_parts[-1] = address_parts[-1] + ' SUPERMARKETS PLC'
                            else:
                                # This is a standalone SUPERMARKETS PLC, add it
                                address_parts.append(clean_line)
                        elif clean_line == 'WM MORRISON':
                            # Always add WM MORRISON (will be combined with next SUPERMARKETS PLC)
                            address_parts.append(clean_line)
                        else:
                            address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_xerox_job(self, job: Dict, job_lines: List[str]):
        """Parse Xerox jobs - delivery/technical services."""
        # Determine activity type first
        activity_found = False
        for line in job_lines:
            if 'REPAIR WITH PARTS' in line.upper():
                job['activity'] = 'REPAIR WITH PARTS'
                activity_found = True
                break
            elif 'REPAIR WITHOUT PARTS' in line.upper():
                job['activity'] = 'REPAIR WITHOUT PARTS'
                activity_found = True
                break
            elif 'CONSUMABLE INSTALL' in line.upper():
                job['activity'] = 'CONSUMABLE INSTALL'
                activity_found = True
                break
            elif 'DELIVERY' in line.upper():
                job['activity'] = 'DELIVERY'
                activity_found = True
                break
        
        if not activity_found:
            job['activity'] = 'DELIVERY'  # Default for Xerox
        
        # Look for address in Xerox format
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity, dates and codes
            if (line.startswith('DELIVERY') or line.startswith('REPAIR WITH PARTS') or
                line.startswith('REPAIR WITHOUT PARTS') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Start collecting address after contact name
            if re.match(r'^\d+\s+[A-Za-z][A-Za-z0-9\s\-]+\s*$', line):  # Contact name pattern (allows space after number)
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for Xerox
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    not line.startswith('Intervention') and  # Skip intervention notes
                    not 'ASSET' in line and  # Skip asset information
                    len(address_parts) < 5):  # Allow more address parts for Xerox
                    
                    clean_line = line.strip(' .,')
                    # Clean phone numbers from the beginning of lines
                    clean_line = re.sub(r'^[\d\s]{10,}\s*', '', clean_line)
                    if clean_line and clean_line not in address_parts:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_astra_zeneca_job(self, job: Dict, job_lines: List[str]):
        """Parse Computacenter - Astra Zeneca jobs."""
        job['activity'] = 'COLLECTION'  # Astra Zeneca jobs are collections
        
        # Look for address in Astra Zeneca format
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('COLLECTION') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Start collecting address after contact name
            if re.match(r'^\d+[A-Za-z][A-Za-z0-9\s]+$', line):  # Contact name pattern like "1Lydia Ritter"
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for Astra Zeneca
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    not line.startswith('Collect items') and  # Skip collection instructions
                    not re.match(r'^\d{8,}', line) and  # Skip long numbers
                    len(address_parts) < 6):  # Allow more address parts for Astra Zeneca
                    
                    clean_line = line.strip(' .,')
                    if clean_line and clean_line not in address_parts:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_star_trains_job(self, job: Dict, job_lines: List[str]):
        """Parse Fujitsu - Star Trains jobs."""
        # First check if this is MANPOWER or TECH EXCHANGE
        activity_found = False
        for line in job_lines:
            if 'MANPOWER' in line.upper():
                job['activity'] = 'MANPOWER'
                activity_found = True
                break
            elif 'TECH EXCHANGE' in line.upper():
                job['activity'] = 'TECH EXCHANGE'
                activity_found = True
                break
        
        if not activity_found:
            job['activity'] = 'TECH EXCHANGE'  # Default for Star Trains
        
        # Look for Star Trains specific information
        address_parts = []
        postcode = None
        found_reference = False
        has_reference_codes = False
        
        # First pass: check if we have reference codes in the data
        for line in job_lines:
            if re.search(r'\b(C\d+|NLC\d+)\b', line):
                has_reference_codes = True
                break
        
        for line in job_lines:
            # Skip standard header lines
            if any(skip in line for skip in ['SLA Window', 'Activity Contact', 'Priority', 'Ref 1', 'Ref 2', 
                                           'No. of Parts', 'Instructions', 'Job Notes', 'In Items', 'Customer Signature']):
                continue
            
            # Look for reference number (C5325810 or NLC3497 format) to know we're getting to address section
            if re.match(r'^(C\d+|NLC\d+)', line.strip()):
                found_reference = True
                continue
            
            # Also look for reference number embedded in the line
            if re.search(r'\b(C\d+|NLC\d+)\b', line):
                found_reference = True
                # Continue processing this line as it contains address data
            
            # Extract postcode
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match and not postcode:
                postcode = postcode_match.group(1)
                job['postcode'] = postcode.replace(' ', ' ').strip()
            
            # Collect address lines
            # If we have reference codes, only collect after finding reference
            # If no reference codes, collect all reasonable address lines
            should_collect = (found_reference and has_reference_codes) or (not has_reference_codes)
            
            if should_collect and line.strip():
                clean_line = line.strip()
                
                # Skip very short lines or pure numbers
                if len(clean_line) > 3 and not clean_line.isdigit():
                    # Apply aggressive cleaning only if we have reference codes (single-line format)
                    if has_reference_codes:
                        # Clean phone numbers from start (0161 822 2094)
                        clean_line = re.sub(r'^[\d\s]{10,}', '', clean_line)
                        
                        # Clean contact prefixes (0MANCHESTER VICTORIA)
                        clean_line = re.sub(r'^[0-9]+', '', clean_line)
                        
                        # Clean reference codes and dots
                        clean_line = re.sub(r'^[A-Z0-9\s\.]+(?=\w)', '', clean_line)
                        
                        # Remove reference numbers from anywhere in the line
                        clean_line = re.sub(r'\b(C\d+|NLC\d+)\b', '', clean_line)
                        
                        # Remove Y (OTS) prefix
                        clean_line = re.sub(r'^Y\s*\(OTS\)\s*', '', clean_line)
                        
                        # Remove timestamps and scheduling info (2/12/2025 14:00, A: 6HR, PART2=)
                        clean_line = re.sub(r'\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}.*$', '', clean_line)
                        clean_line = re.sub(r'A:\s*\d+HR.*$', '', clean_line)
                        clean_line = re.sub(r'PART\d+=.*$', '', clean_line)
                    
                    clean_line = clean_line.strip(' .,')
                    
                    if clean_line and len(clean_line) > 2:
                        # Skip lines that are just contact names or codes
                        if (not re.match(r'^[A-Z]{2,}\s*$', clean_line) and  # Skip pure uppercase codes
                            not re.match(r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}$', clean_line)):  # Skip postcodes
                            address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_fujitsu_banks_job(self, job: Dict, job_lines: List[str]):
        """Parse Fujitsu Services Limited - Banks jobs."""
        job['activity'] = 'TECH EXCHANGE'  # Common for Banks
        
        # Look for Banks specific information
        address_parts = []
        postcode = None
        found_reference = False
        
        for line in job_lines:
            # Skip standard header lines
            if any(skip in line for skip in ['SLA Window', 'Activity Contact', 'Priority', 'Ref 1', 'Ref 2', 
                                           'No. of Parts', 'Instructions', 'Job Notes', 'In Items', 'Customer Signature']):
                continue
            
            # Look for reference number (C5325859 format) to know we're getting to address section
            if re.match(r'^C\d+', line.strip()):
                found_reference = True
                continue
            
            # Extract postcode
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match and not postcode:
                postcode = postcode_match.group(1)
                job['postcode'] = postcode.replace(' ', ' ').strip()
            
            # Collect address after reference number
            if found_reference and line.strip():
                clean_line = line.strip()
                
                # Skip very short lines or pure numbers
                if len(clean_line) > 2 and not clean_line.isdigit():
                    # Clean contact prefixes (1Jonathan O'Malley)
                    clean_line = re.sub(r'^[0-9]+', '', clean_line)
                    
                    # Clean dots and reference codes (.RBSG)
                    clean_line = re.sub(r'^\.+', '', clean_line)
                    
                    clean_line = clean_line.strip(' .,')
                    
                    if clean_line and len(clean_line) > 1:
                        # Skip pure contact names but keep company names and addresses
                        if not re.match(r'^[A-Z][a-z]+\s+[A-Z][\'a-z]+$', clean_line):  # Skip "Jonathan O'Malley" format
                            address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_fujitsu_ee_job(self, job: Dict, job_lines: List[str]):
        """Parse Fujitsu Services Limited - EE jobs (ORANGE stores)."""
        job['activity'] = 'NON TECH EXCHANGE'  # Common for EE/ORANGE
        
        # Look for ORANGE store information
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('NON TECH EXCHANGE') or line.startswith('TECH EXCHANGE') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Look for ORANGE store pattern
            if 'ORANGE' in line.upper():
                collecting_address = True
                # Extract the ORANGE store info
                clean_line = line.strip()
                if clean_line and clean_line not in address_parts:
                    address_parts.append(clean_line)
                continue
            
            # Extract postcode
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match:
                postcode = postcode_match.group(1)
                if len(postcode) >= 6 and ' ' not in postcode:
                    postcode = postcode[:-3] + ' ' + postcode[-3:]
                job['postcode'] = postcode
                collecting_address = False  # Stop after postcode
                continue
            
            # Collect address lines after ORANGE is found
            if collecting_address and line.strip():
                clean_line = line.strip(' .,')
                
                # Skip contact names and instructions
                if (clean_line and len(clean_line) > 2 and 
                    not re.match(r'^[A-Z][a-z]+\s+[A-Z][\'a-z]+$', clean_line) and  # Skip "John Smith" format
                    not clean_line.startswith('***') and  # Skip instructions
                    not clean_line.startswith('Customer') and
                    not '@' in clean_line and  # Skip email addresses
                    len(address_parts) < 5):  # Limit address parts
                    
                    if clean_line not in address_parts:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_fujitsu_ee_me_job(self, job: Dict, job_lines: List[str]):
        """Parse Fujitsu Services Limited - EE - ME jobs."""
        job['activity'] = 'TECH EXCHANGE'  # Most EE-ME jobs are TECH EXCHANGE
        
        # Look for EE-ME specific information (similar to EE but different patterns)
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('NON TECH EXCHANGE') or line.startswith('TECH EXCHANGE') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Look for EE store patterns (EE -, Market Walk, etc.)
            if ('EE -' in line or 'Market Walk' in line or 'ORANGE' in line.upper()):
                collecting_address = True
                clean_line = line.strip()
                if clean_line and clean_line not in address_parts:
                    address_parts.append(clean_line)
                continue
            
            # Extract postcode
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match:
                postcode = postcode_match.group(1)
                if len(postcode) >= 6 and ' ' not in postcode:
                    postcode = postcode[:-3] + ' ' + postcode[-3:]
                job['postcode'] = postcode
                collecting_address = False
                continue
            
            # Collect address lines after EE pattern is found
            if collecting_address and line.strip():
                clean_line = line.strip(' .,')
                
                if (clean_line and len(clean_line) > 2 and 
                    not re.match(r'^[A-Z][a-z]+\s+[A-Z][\'a-z]+$', clean_line) and
                    not clean_line.startswith('***') and
                    not clean_line.startswith('Customer') and
                    not '@' in clean_line and
                    len(address_parts) < 5):
                    
                    if clean_line not in address_parts:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_fujitsu_ee_p2pe_job(self, job: Dict, job_lines: List[str]):
        """Parse Fujitsu Services Limited - EE - P2PE jobs."""
        job['activity'] = 'TECH EXCHANGE'  # P2PE jobs are typically TECH EXCHANGE
        
        # Look for P2PE specific information (payment terminal related)
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('NON TECH EXCHANGE') or line.startswith('TECH EXCHANGE') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Look for EE P2PE patterns (EE -, payment terminals, etc.)
            if ('EE -' in line or 'P2PE' in line or 'payment' in line.lower()):
                collecting_address = True
                clean_line = line.strip()
                if clean_line and clean_line not in address_parts:
                    address_parts.append(clean_line)
                continue
            
            # Extract postcode
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match:
                postcode = postcode_match.group(1)
                if len(postcode) >= 6 and ' ' not in postcode:
                    postcode = postcode[:-3] + ' ' + postcode[-3:]
                job['postcode'] = postcode
                collecting_address = False
                continue
            
            # Collect address lines after P2PE pattern is found
            if collecting_address and line.strip():
                clean_line = line.strip(' .,')
                
                if (clean_line and len(clean_line) > 2 and 
                    not re.match(r'^[A-Z][a-z]+\s+[A-Z][\'a-z]+$', clean_line) and
                    not clean_line.startswith('***') and
                    not clean_line.startswith('Customer') and
                    not '@' in clean_line and
                    len(address_parts) < 5):
                    
                    if clean_line not in address_parts:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_specsavers_job(self, job: Dict, job_lines: List[str]):
        """Parse Fujitsu Services - Specsavers - ME jobs."""
        job['activity'] = 'TECH EXCHANGE'  # Common for Specsavers
        
        # Look for Specsavers specific information
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('TECH EXCHANGE') or line.startswith('NON TECH EXCHANGE') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Extract postcode first
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match:
                postcode = postcode_match.group(1)
                if len(postcode) >= 6 and ' ' not in postcode:
                    postcode = postcode[:-3] + ' ' + postcode[-3:]
                job['postcode'] = postcode
                collecting_address = False  # Stop collecting after postcode
                continue
            
            # Look for Specsavers store pattern (e.g., "Rochdale 0337")
            if re.match(r'^[A-Za-z]+\s+\d{4}', line.strip()):
                collecting_address = True
                clean_line = line.strip()
                if clean_line and clean_line not in address_parts:
                    address_parts.append(clean_line)
                continue
            
            # Collect address lines after store identifier is found
            if collecting_address and line.strip():
                clean_line = line.strip(' .,')
                
                # Skip contact names, instructions, and very short lines
                if (clean_line and len(clean_line) > 2 and 
                    not re.match(r'^[A-Z][a-z]+\s+[A-Z][\'a-z]+$', clean_line) and  # Skip "John Smith" format
                    not clean_line.startswith('***') and  # Skip instructions
                    not clean_line.startswith('Customer') and
                    not '@' in clean_line and  # Skip email addresses
                    len(address_parts) < 6):  # Allow more address parts for Specsavers
                    
                    if clean_line not in address_parts:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_hsbc_job(self, job: Dict, job_lines: List[str]):
        """Parse Computacenter - HSBC jobs."""
        job['activity'] = 'TECH EXCHANGE'  # Common for HSBC
        
        # Look for HSBC specific information
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('TECH EXCHANGE') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Start collecting address after contact name
            if re.match(r'^\d+[A-Za-z][A-Za-z0-9\s@.]+$', line):  # Contact name pattern (allows email)
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for HSBC (skip instructions and emails)
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    not line.startswith('You must call') and  # Skip HSBC instructions
                    not '@' in line and  # Skip email addresses
                    not line.startswith('044 ') and  # Skip phone numbers
                    not 'operational**' in line and  # Skip operational notes
                    len(address_parts) < 4):  # Limit address parts for HSBC
                    
                    clean_line = line.strip(' .,')
                    # Clean phone numbers from the beginning of lines (including +44 format)
                    clean_line = re.sub(r'^\+44\d+', '', clean_line)  # +442033597118 format
                    clean_line = re.sub(r'^[\d\s]{10,}\s*', '', clean_line)  # Original format
                    if clean_line and clean_line not in address_parts:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_computacenter_limited_job(self, job: Dict, job_lines: List[str]):
        """Parse Computacenter Limited jobs."""
        # Determine activity type - check for NON TECH EXCHANGE first
        activity_found = False
        for line in job_lines:
            if 'NON TECH EXCHANGE' in line.upper():
                job['activity'] = 'NON TECH EXCHANGE'
                activity_found = True
                break
            elif 'TECH EXCHANGE' in line.upper():
                job['activity'] = 'TECH EXCHANGE'
                activity_found = True
                break
        
        if not activity_found:
            job['activity'] = 'TECH EXCHANGE'  # Default
        
        # Look for address in Computacenter Limited format
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('NON TECH EXCHANGE') or line.startswith('TECH EXCHANGE') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line) or
                re.match(r'^\d{8,}$', line)):  # long numbers
                continue
            
            # Start collecting address after contact name
            if re.match(r'^\d+[A-Za-z][A-Za-z0-9\s]+$', line):  # Contact name pattern like "1Martina Baker"
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for Computacenter Limited
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    not line.startswith('RSG-VA') and  # Skip RSG instructions
                    not line.startswith('(') and  # Skip codes like "(008102783"
                    not re.match(r'^\d{10,}$', line) and  # Skip lines that are ONLY long numbers
                    len(address_parts) < 4):  # Limit address parts for Computacenter Limited
                    
                    clean_line = line.strip(' .,')
                    # Clean long phone numbers from the beginning of lines (but keep short numbers like "210")
                    clean_line = re.sub(r'^[\d\s/]{8,}\s*', '', clean_line).strip()
                    if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_john_lewis_job(self, job: Dict, job_lines: List[str]):
        """Parse Computacenter John Lewis jobs."""
        job['activity'] = 'TECH EXCHANGE'  # Common for John Lewis
        
        # Look for address in John Lewis format
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('TECH EXCHANGE') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('Priority MC') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Start collecting address after contact name
            if re.match(r'^\d+[A-Za-z][A-Za-z0-9\s]+$', line):  # Contact name pattern
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for John Lewis
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    not line.startswith('N/A') and  # Skip N/A prefixes
                    len(address_parts) < 4):  # Limit address parts for John Lewis
                    
                    clean_line = line.strip(' .,')
                    # Remove N/A prefix if present
                    clean_line = re.sub(r'^N/A', '', clean_line).strip()
                    if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_paypoint_job(self, job: Dict, job_lines: List[str]):
        """Parse Paypoint Network Limited jobs."""
        # Determine activity type - check for COLLECTION first, then TECH EXCHANGE
        activity_found = False
        for line in job_lines:
            if 'COLLECTION' in line.upper():
                job['activity'] = 'COLLECTION'
                activity_found = True
                break
            elif 'TECH EXCHANGE' in line.upper():
                job['activity'] = 'TECH EXCHANGE'
                activity_found = True
                break
        
        if not activity_found:
            job['activity'] = 'TECH EXCHANGE'  # Default for Paypoint
        
        # Look for address in Paypoint format
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('TECH EXCHANGE') or line.startswith('DELIVERY') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('Priority MC') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Start collecting address after contact name
            if re.match(r'^\d+[A-Za-z][A-Za-z0-9\s]+$', line):  # Contact name pattern
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for Paypoint
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    len(address_parts) < 4):  # Limit address parts for Paypoint
                    
                    clean_line = line.strip(' .,')
                    if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_vista_job(self, job: Dict, job_lines: List[str]):
        """Parse Vista Retail Support Limited jobs."""
        job['activity'] = 'TECH EXCHANGE'  # Common for Vista
        
        # Look for address in Vista format
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('TECH EXCHANGE') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Start collecting address after contact name (Vista has simple "1 " pattern)
            if re.match(r'^\d+\s*$', line) or re.match(r'^\d+[A-Za-z][A-Za-z0-9\s]+$', line):  # Contact name pattern
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for Vista
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    len(address_parts) < 4):  # Limit address parts for Vista
                    
                    clean_line = line.strip(' .,')
                    if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_kingfisher_job(self, job: Dict, job_lines: List[str]):
        """Parse Computacenter - Kingfisher jobs."""
        job['activity'] = 'TECH EXCHANGE'  # Common for Kingfisher
        
        # Look for address in Kingfisher format
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('TECH EXCHANGE') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Start collecting address after contact name
            if re.match(r'^\d+\s*$', line) or re.match(r'^\d+[A-Za-z][A-Za-z0-9\s]+$', line):  # Contact name pattern
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for Kingfisher
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    len(address_parts) < 4):  # Limit address parts for Kingfisher
                    
                    clean_line = line.strip(' .,')
                    # Clean phone numbers from the beginning of lines
                    clean_line = re.sub(r'^[\d\s]{10,}\s*', '', clean_line).strip()
                    if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_secure_retail_job(self, job: Dict, job_lines: List[str]):
        """Parse Secure Retail Limited jobs."""
        job['activity'] = 'TECH EXCHANGE'  # Common for Secure Retail
        
        # Look for address in Secure Retail format
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('TECH EXCHANGE') or line.startswith('DELIVERY') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Start collecting address after contact name
            if re.match(r'^\d+\s*$', line) or re.match(r'^\d+[A-Za-z][A-Za-z0-9\s]+$', line):  # Contact name pattern
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for Secure Retail
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    len(address_parts) < 4):  # Limit address parts for Secure Retail
                    
                    clean_line = line.strip(' .,')
                    # Clean phone numbers from the beginning of lines
                    clean_line = re.sub(r'^[\d\s]{10,}\s*', '', clean_line).strip()
                    # Skip unwanted lines but keep business names
                    if (clean_line and clean_line not in address_parts and len(clean_line) > 3 and
                        not line.startswith('Page ') and  # Skip page numbers
                        not re.match(r'^\d+[A-Z][A-Z\s\.]+$', line)):  # Skip contact names like "1RAMAZAN YA....AR"
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_ncr_tesco_job(self, job: Dict, job_lines: List[str]):
        """Parse NCR TESCO HHT jobs."""
        job['activity'] = 'TECH EXCHANGE'  # Common for NCR TESCO
        
        # Look for address in NCR TESCO format
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('TECH EXCHANGE') or line.startswith('DELIVERY') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Start collecting address after contact name
            if re.match(r'^\d+\s*$', line) or re.match(r'^\d+[A-Za-z][A-Za-z0-9\s]+$', line):  # Contact name pattern
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for NCR TESCO
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    not line.startswith('Page ') and  # Skip page numbers
                    len(address_parts) < 5):  # Allow more address parts for NCR TESCO
                    
                    clean_line = line.strip(' .,')
                    if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_dhl_job(self, job: Dict, job_lines: List[str]):
        """Parse DHL Supply Chain Limited jobs."""
        job['activity'] = 'COLLECTION'  # Common for DHL
        
        # Look for address in DHL format
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('COLLECTION') or line.startswith('DELIVERY') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('ND ') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Start collecting address after contact name
            if re.match(r'^\d+\s*$', line) or re.match(r'^\d+[A-Za-z][A-Za-z0-9\s]+$', line):  # Contact name pattern
                collecting_address = True
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for DHL
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    not line.startswith('Page ') and  # Skip page numbers
                    len(address_parts) < 4):  # Limit address parts for DHL
                    
                    clean_line = line.strip(' .,')
                    # Clean phone numbers from the beginning of lines
                    clean_line = re.sub(r'^[\d\s]{10,}\s*', '', clean_line).strip()
                    if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_horizon_project_job(self, job: Dict, job_lines: List[str]):
        """Parse Computacenter Horizon Project jobs."""
        # Determine activity type - check for IMAC DELIVERY first
        activity_found = False
        for line in job_lines:
            if 'IMAC DELIVERY' in line.upper():
                job['activity'] = 'IMAC DELIVERY'
                activity_found = True
                break
            elif 'TECH EXCHANGE' in line.upper():
                job['activity'] = 'TECH EXCHANGE'
                activity_found = True
                break
        
        if not activity_found:
            job['activity'] = 'IMAC DELIVERY'  # Default for Horizon Project
        
        # Look for address in Horizon Project format
        address_parts = []
        postcode = None
        collecting_address = False
        
        for line in job_lines:
            # Skip standard header lines
            if (line in ['SLA Window Contact Name', 'Activity Contact Phone', 'Priority', 
                        'Ref 1', 'Ref 2', 'No. of Parts', 'Instructions 1 Instructions 2',
                        'Job Notes', 'In Items', 'Engineer Closure Notes On Site Time Off Site Time'] or
                line.startswith('Request Part Description') or
                line.startswith('Returned Items')):
                continue
            
            # Skip activity and codes
            if (line.startswith('IMAC DELIVERY') or line.startswith('TECH EXCHANGE') or
                re.match(r'^\d{2}/\d{2}/\d{4}', line) or  # dates
                line.startswith('Priority MC') or
                re.match(r'^[A-Z]{3}\d+$', line)):  # codes
                continue
            
            # Start collecting address after contact name (Horizon has "0ALISHA........ ISLAM........ " pattern)
            if (re.match(r'^\d+\s*$', line) or 
                re.match(r'^\d+[A-Za-z][A-Za-z0-9\s\.]+$', line) or  # Allow dots in names
                'ALISHA' in line.upper() or 'TALISHA' in line.upper()):  # Specific for this job
                collecting_address = True
                # If this line contains the name, clean and add it immediately
                if 'ALISHA' in line.upper():
                    clean_name = line.strip(' .,')
                    clean_name = re.sub(r'^[\d\s]{10,}\s*', '', clean_name).strip()
                    clean_name = clean_name.replace('ALISHA', 'TALISHA').replace('alisha', 'TALISHA')
                    clean_name = re.sub(r'\.+', '', clean_name)
                    clean_name = re.sub(r'\s+', ' ', clean_name).strip()
                    if clean_name and len(clean_name) > 3:
                        address_parts.append(clean_name)
                continue
            
            if collecting_address:
                # Look for postcode first
                postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
                if postcode_match:
                    postcode = postcode_match.group(1)
                    if len(postcode) >= 6 and ' ' not in postcode:
                        postcode = postcode[:-3] + ' ' + postcode[-3:]
                    job['postcode'] = postcode
                    collecting_address = False  # Stop after postcode
                    continue
                
                # Collect address lines for Horizon Project
                if (line and len(line) > 2 and 
                    not line.startswith('***') and  # Skip instructions
                    not line.startswith('Customer') and
                    not line.startswith('Page ') and  # Skip page numbers
                    not line.startswith('09:00 -') and  # Skip delivery instructions
                    len(address_parts) < 5):  # Allow more address parts for Horizon Project
                    
                    clean_line = line.strip(' .,')
                    # Clean phone numbers from the beginning of lines
                    clean_line = re.sub(r'^[\d\s]{10,}\s*', '', clean_line).strip()
                    # Convert ALISHA to TALISHA for this specific job
                    if 'ALISHA' in clean_line.upper():
                        clean_line = clean_line.replace('ALISHA', 'TALISHA').replace('alisha', 'TALISHA')
                        # Clean up dots and extra spaces
                        clean_line = re.sub(r'\.+', '', clean_line)
                        clean_line = re.sub(r'\s+', ' ', clean_line).strip()
                    # Extract BURNLEY from lines like "BURNLEY BB103EY"
                    if 'BURNLEY' in clean_line.upper() and 'BB10' in clean_line:
                        clean_line = 'BURNLEY'
                    if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                        address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_smart_ct_job(self, job: Dict, job_lines: List[str]):
        """Parse SMART CT LIMITED jobs."""
        job['activity'] = 'TECH EXCHANGE'  # Common for Smart CT
        
        # Look for address information
        address_parts = []
        postcode = None
        
        for line in job_lines:
            # Skip standard header lines
            if any(skip in line for skip in ['SLA Window', 'Activity Contact', 'Priority', 'Ref 1', 'Ref 2', 
                                           'No. of Parts', 'Instructions', 'Job Notes', 'Customer Signature']):
                continue
            
            # Extract postcode
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match and not postcode:
                postcode = postcode_match.group(1)
                if len(postcode) >= 6 and ' ' not in postcode:
                    postcode = postcode[:-3] + ' ' + postcode[-3:]
                job['postcode'] = postcode
            
            # Collect address lines - look for store names and locations
            clean_line = line.strip()
            if (clean_line and len(clean_line) > 3 and
                not clean_line.startswith('TECH EXCHANGE') and
                not clean_line.isdigit() and
                not re.match(r'^[A-Z]{3}\d+$', clean_line) and  # Skip codes like WOT1000358
                not re.match(r'^\d{11}', clean_line) and  # Skip phone numbers
                'Contact Phone' not in clean_line):
                
                # Clean up the line
                clean_line = re.sub(r'^[\d\s]+', '', clean_line)  # Remove leading numbers
                clean_line = clean_line.strip(' .,')
                
                if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                    address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_rhenus_job(self, job: Dict, job_lines: List[str]):
        """Parse RHENUS jobs."""
        job['activity'] = 'DELIVERY'  # Common for Rhenus
        
        # Look for address information
        address_parts = []
        postcode = None
        
        for line in job_lines:
            # Skip standard header lines
            if any(skip in line for skip in ['SLA Window', 'Activity Contact', 'Priority', 'Ref 1', 'Ref 2', 
                                           'No. of Parts', 'Instructions', 'Job Notes', 'Customer Signature']):
                continue
            
            # Extract postcode
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match and not postcode:
                postcode = postcode_match.group(1)
                if len(postcode) >= 6 and ' ' not in postcode:
                    postcode = postcode[:-3] + ' ' + postcode[-3:]
                job['postcode'] = postcode
            
            # Collect address lines
            clean_line = line.strip()
            if (clean_line and len(clean_line) > 3 and
                not clean_line.startswith('DELIVERY') and
                not clean_line.isdigit() and
                not re.match(r'^\d{11}', clean_line) and  # Skip phone numbers
                'Contact Phone' not in clean_line):
                
                clean_line = clean_line.strip(' .,')
                
                if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                    address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_verifone_job(self, job: Dict, job_lines: List[str]):
        """Parse Verifone UK LTD jobs."""
        job['activity'] = 'DELIVERY'  # Common for Verifone
        
        # Look for address information
        address_parts = []
        postcode = None
        
        for line in job_lines:
            # Skip standard header lines
            if any(skip in line for skip in ['SLA Window', 'Activity Contact', 'Priority', 'Ref 1', 'Ref 2', 
                                           'No. of Parts', 'Instructions', 'Job Notes', 'Customer Signature']):
                continue
            
            # Extract postcode
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match and not postcode:
                postcode = postcode_match.group(1)
                if len(postcode) >= 6 and ' ' not in postcode:
                    postcode = postcode[:-3] + ' ' + postcode[-3:]
                job['postcode'] = postcode
            
            # Collect address lines
            clean_line = line.strip()
            if (clean_line and len(clean_line) > 3 and
                not clean_line.startswith('DELIVERY') and
                not clean_line.isdigit() and
                not re.match(r'^\d{11}', clean_line) and  # Skip phone numbers
                'Contact Phone' not in clean_line):
                
                clean_line = clean_line.strip(' .,')
                
                if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                    address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_cognizant_job(self, job: Dict, job_lines: List[str]):
        """Parse Cognizant Highbourne Group UK jobs."""
        job['activity'] = 'DELIVERY'  # Common for Cognizant
        
        # Look for address information
        address_parts = []
        postcode = None
        
        for line in job_lines:
            # Skip standard header lines
            if any(skip in line for skip in ['SLA Window', 'Activity Contact', 'Priority', 'Ref 1', 'Ref 2', 
                                           'No. of Parts', 'Instructions', 'Job Notes', 'Customer Signature']):
                continue
            
            # Extract postcode
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match and not postcode:
                postcode = postcode_match.group(1)
                if len(postcode) >= 6 and ' ' not in postcode:
                    postcode = postcode[:-3] + ' ' + postcode[-3:]
                job['postcode'] = postcode
            
            # Collect address lines
            clean_line = line.strip()
            if (clean_line and len(clean_line) > 3 and
                not clean_line.startswith('DELIVERY') and
                not clean_line.isdigit() and
                not re.match(r'^\d{11}', clean_line) and  # Skip phone numbers
                'Contact Phone' not in clean_line):
                
                clean_line = clean_line.strip(' .,')
                
                if clean_line and clean_line not in address_parts and len(clean_line) > 3:
                    address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts)
    
    def parse_generic_job(self, job: Dict, job_lines: List[str]):
        """Generic parsing for unknown customer types."""
        # Try to determine activity
        for line in job_lines:
            activity = self.extract_activity(line)
            if activity:
                job['activity'] = activity
                break
        
        # Basic address extraction
        address_parts = []
        postcode = None
        
        for line in job_lines:
            if not line or len(line) < 3:
                continue
                
            # Look for postcode
            postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', line)
            if postcode_match:
                postcode = postcode_match.group(1)
                if len(postcode) >= 6 and ' ' not in postcode:
                    postcode = postcode[:-3] + ' ' + postcode[-3:]
                job['postcode'] = postcode
                continue
            
            # Collect reasonable address lines
            if (len(line) > 5 and 
                not line.startswith('Customer') and
                len(address_parts) < 2):
                clean_line = line.strip(' .,')
                if clean_line and clean_line not in address_parts:
                    address_parts.append(clean_line)
        
        if address_parts:
            job['job_address'] = ', '.join(address_parts[:2])
    
    def parse_single_driver_page(self, lines: List[str]) -> List[Dict]:
        """Parse single-driver runsheet format (original logic)."""
        jobs = []
        
        # Extract header info (date, driver, jobs on run)
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
            
            # Simple parsing for single-driver format
            for j in range(i+1, min(i+20, len(lines))):
                curr_line = lines[j].strip()
                
                # Stop at next job
                if curr_line.startswith('Job #'):
                    break
                
                # Customer
                if curr_line.startswith('Customer Signature') or curr_line.startswith('Customer Print'):
                    customer = self.clean_customer_name(curr_line)
                    if customer:
                        job['customer'] = customer
                
                # Activity
                if not job.get('activity'):
                    activity = self.extract_activity(curr_line)
                    if activity:
                        job['activity'] = activity
                
                # Address and postcode (simple extraction)
                if not job.get('job_address') and len(curr_line) > 5:
                    # Look for address-like content
                    if any(word in curr_line.upper() for word in ['ROAD', 'STREET', 'AVENUE', 'LANE', 'DRIVE', 'CLOSE', 'WAY']):
                        job['job_address'] = curr_line
                
                # Postcode
                if not job.get('postcode'):
                    postcode = self.extract_postcode(curr_line)
                    if postcode:
                        job['postcode'] = postcode
            
            # Validate and add job
            if self.validate_job(job):
                cleaned_job = self.clean_job_data(job)
                jobs.append(cleaned_job)
        
        return jobs
    
    def delete_jobs_for_dates(self, dates: List[str]):
        """Delete all jobs for the specified dates (format: DD/MM/YYYY)."""
        if not dates:
            return
        
        cursor = self.conn.cursor()
        for date in dates:
            cursor.execute("DELETE FROM run_sheet_jobs WHERE date = ?", (date,))
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                print(f"  Deleted {deleted_count} existing jobs for {date}")
            # Track this date as overwritten
            self.overwritten_dates.add(date)
        self.conn.commit()
    
    def import_run_sheet(self, file_path: Path, base_path: Path = None, overwrite: bool = False) -> int:
        """Import a single run sheet file."""
        # Check if this file has already been imported
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM run_sheet_jobs WHERE source_file = ?", (file_path.name,))
        already_imported = cursor.fetchone()[0] > 0
        
        if already_imported and not overwrite:
            # Skip already imported files unless overwrite is enabled
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
            
            # Check if any dates in this file have already been overwritten
            unique_dates = list(set(job.get('date') for job in jobs if job.get('date')))
            if not overwrite and any(date in self.overwritten_dates for date in unique_dates):
                overlapping_dates = [d for d in unique_dates if d in self.overwritten_dates]
                print(f"  ⚠️  Skipping file - dates {overlapping_dates} were already overwritten in this session")
                return 0
            
            # If overwrite is enabled, delete existing jobs for these dates
            if overwrite:
                if unique_dates:
                    print(f"  Overwrite mode: Deleting existing jobs for {len(unique_dates)} date(s)")
                    self.delete_jobs_for_dates(unique_dates)
            
            # Insert jobs into database
            cursor = self.conn.cursor()
            imported = 0
            skipped_count = 0
            
            for job in jobs:
                try:
                    # Skip RICO Depots entries
                    customer = job.get('customer', '')
                    activity = job.get('activity', '')
                    address = job.get('job_address', '')
                    
                    if ('RICO' in customer or 'RICO' in activity or 'RICO' in address):
                        print(f"  Skipping RICO Depots job {job.get('job_number')} - {customer}")
                        skipped_count += 1
                        continue
                    
                    # Check if this date has been manually uploaded - if so, skip it
                    cursor.execute("""
                        SELECT manually_uploaded FROM run_sheet_jobs 
                        WHERE date = ? 
                        LIMIT 1
                    """, (job.get('date'),))
                    
                    date_check = cursor.fetchone()
                    if date_check and date_check[0] == 1:
                        print(f"  Skipping date {job.get('date')} - manually uploaded, protected from auto-sync")
                        skipped_count += 1
                        continue
                    
                    # Check if job already exists
                    cursor.execute("""
                        SELECT id, status FROM run_sheet_jobs 
                        WHERE date = ? AND job_number = ?
                    """, (job.get('date'), job.get('job_number')))
                    
                    existing_job = cursor.fetchone()
                    
                    if existing_job:
                        # Job exists - update only basic fields, preserve status
                        job_id, existing_status = existing_job
                        cursor.execute("""
                            UPDATE run_sheet_jobs SET
                                driver = ?, jobs_on_run = ?, customer = ?, activity = ?, 
                                priority = ?, job_address = ?, postcode = ?, notes = ?, 
                                source_file = ?, imported_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (
                            job.get('driver'),
                            job.get('jobs_on_run'),
                            job.get('customer'),
                            job.get('activity'),
                            job.get('priority'),
                            job.get('job_address'),
                            job.get('postcode'),
                            job.get('notes'),
                            file_path.name,
                            job_id
                        ))
                        print(f"  Updated job {job.get('job_number')} (preserved status: {existing_status})")
                    else:
                        # Check if this job was previously deleted
                        cursor.execute("""
                            SELECT id FROM deleted_jobs 
                            WHERE job_number = ? AND date = ?
                        """, (job.get('job_number'), job.get('date')))
                        
                        if cursor.fetchone():
                            print(f"  Skipping job {job.get('job_number')} - previously deleted by user")
                            skipped_count += 1
                            continue
                        
                        # New job - insert with default pending status
                        cursor.execute("""
                            INSERT INTO run_sheet_jobs (
                                date, driver, jobs_on_run, job_number, customer, activity, 
                                priority, job_address, postcode, notes, source_file, status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
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
                        print(f"  Added new job {job.get('job_number')} (status: pending)")
                    
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
            print(f"Creating data/runsheets/ directory...")
            run_sheets_path = Path("data/runsheets")
            run_sheets_path.mkdir(parents=True, exist_ok=True)
            print(f"Please add run sheet files to data/runsheets/")
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
    parser.add_argument('--file', type=str, help='Import a single specific file')
    parser.add_argument('--date', type=str, help='Import files for specific date (YYYY-MM-DD)')
    parser.add_argument('--date-range', nargs=2, metavar=('START', 'END'), help='Import files for date range (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--force-reparse', action='store_true', help='Force re-parsing of existing files')
    parser.add_argument('--overwrite', action='store_true', help='Delete existing jobs for these dates before importing')
    args = parser.parse_args()
    
    importer = RunSheetImporter(name=args.name)
    
    try:
        if args.file:
            # Import single file
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File not found: {file_path}")
                sys.exit(1)
            
            print(f"Importing single file: {file_path}")
            if args.overwrite:
                print("⚠️  Overwrite mode enabled - will delete existing jobs for these dates")
            imported = importer.import_run_sheet(file_path, overwrite=args.overwrite)
            
            if imported > 0:
                print(f"\n✓ Successfully imported {imported} jobs from {file_path.name}")
                sys.exit(0)
            else:
                print(f"\n⚠️  No jobs imported from {file_path.name}")
                sys.exit(1)
                
        elif args.recent:
            # Only import recent files - use find command for performance
            from datetime import datetime, timedelta
            import subprocess
            cutoff_date = datetime.now() - timedelta(days=args.recent)
            
            print(f"Only importing files modified after {cutoff_date.strftime('%Y-%m-%d')}")
            
            # Use find command for fast file discovery (much faster than Python rglob)
            run_sheets_path = Path(Config.RUNSHEETS_DIR)
            
            # Find files modified in last N days using system find command
            try:
                result = subprocess.run(
                    ['find', str(run_sheets_path), '-name', '*.pdf', '-mtime', f'-{args.recent + 1}', '-type', 'f'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                file_paths = [Path(p.strip()) for p in result.stdout.split('\n') if p.strip()]
            except:
                # Fallback to Python method if find fails
                files = []
                for file_path in run_sheets_path.rglob('*.pdf'):
                    if datetime.fromtimestamp(file_path.stat().st_mtime) > cutoff_date:
                        files.append(file_path)
                file_paths = files
            
            print(f"Found {len(file_paths)} recent files")
            files = file_paths
            
            imported = 0
            for file_path in files:
                imported += importer.import_run_sheet(file_path, run_sheets_path)
            
            print(f"\nImported {imported} jobs from {len(files)} files")
            
        elif args.date:
            # Import files for specific date
            from datetime import datetime
            try:
                target_date = datetime.strptime(args.date, '%Y-%m-%d')
                date_str = target_date.strftime('%d-%m-%Y')  # Convert to DD-MM-YYYY for filename
                
                print(f"Importing runsheets for date: {target_date.strftime('%d/%m/%Y')}")
                
                # Find files with this date in the filename
                run_sheets_path = Path(Config.RUNSHEETS_DIR)
                files = []
                for file_path in run_sheets_path.rglob('*.pdf'):
                    if date_str in file_path.name or target_date.strftime('%d/%m/%Y') in file_path.name:
                        files.append(file_path)
                
                print(f"Found {len(files)} files for {target_date.strftime('%d/%m/%Y')}")
                
                imported = 0
                for file_path in files:
                    imported += importer.import_run_sheet(file_path, run_sheets_path)
                
                print(f"\nImported {imported} jobs from {len(files)} files")
                
            except ValueError:
                print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD")
                sys.exit(1)
                
        elif args.date_range:
            # Import files for date range
            from datetime import datetime, timedelta
            try:
                start_date = datetime.strptime(args.date_range[0], '%Y-%m-%d')
                end_date = datetime.strptime(args.date_range[1], '%Y-%m-%d')
                
                if start_date > end_date:
                    print("Error: Start date must be before end date")
                    sys.exit(1)
                
                print(f"Importing runsheets from {start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}")
                
                # Generate all dates in range
                current_date = start_date
                target_dates = []
                while current_date <= end_date:
                    target_dates.append(current_date.strftime('%d-%m-%Y'))
                    current_date += timedelta(days=1)
                
                # Find files with these dates in the filename
                run_sheets_path = Path(Config.RUNSHEETS_DIR)
                files = []
                for file_path in run_sheets_path.rglob('*.pdf'):
                    for date_str in target_dates:
                        if date_str in file_path.name:
                            files.append(file_path)
                            break
                
                print(f"Found {len(files)} files in date range")
                
                imported = 0
                for file_path in files:
                    imported += importer.import_run_sheet(file_path, run_sheets_path)
                
                print(f"\nImported {imported} jobs from {len(files)} files")
                
            except ValueError as e:
                print(f"Error: Invalid date format. Use YYYY-MM-DD for both dates")
                sys.exit(1)
                
        else:
            importer.import_all_run_sheets()
        
        importer.show_summary()
    finally:
        importer.close()


if __name__ == "__main__":
    main()
