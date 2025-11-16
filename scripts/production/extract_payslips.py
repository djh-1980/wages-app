#!/usr/bin/env python3
"""
Extract payslip data from PDFs and store in SQLite database.
"""

import pdfplumber
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json


class PayslipExtractor:
    def __init__(self, db_path: str = "data/database/payslips.db"):
        self.db_path = db_path
        self.conn = None
        self.setup_database()
    
    def setup_database(self):
        """Create database tables if they don't exist."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()
        
        # Main payslip summary table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payslips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tax_year TEXT NOT NULL,
                week_number INTEGER NOT NULL,
                verification_number TEXT,
                utr_number TEXT,
                pay_date TEXT,
                period_end TEXT,
                vat_number TEXT,
                total_company_income REAL,
                materials REAL,
                gross_subcontractor_payment REAL,
                gross_subcontractor_payment_ytd REAL,
                net_payment REAL,
                total_paid_to_bank REAL,
                pdf_filename TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tax_year, week_number)
            )
        """)
        
        # Individual job items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payslip_id INTEGER NOT NULL,
                units REAL,
                rate REAL,
                amount REAL,
                description TEXT,
                job_number TEXT,
                client TEXT,
                location TEXT,
                job_type TEXT,
                date TEXT,
                time TEXT,
                agency TEXT,
                weekend_date TEXT,
                FOREIGN KEY (payslip_id) REFERENCES payslips(id)
            )
        """)
        
        self.conn.commit()
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all text from a PDF file using pdfplumber."""
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def parse_payslip_header(self, text: str) -> Dict:
        """Extract header information from payslip."""
        header_data = {}
        
        # Split into lines for structured parsing
        lines = text.split('\n')
        
        # pdfplumber preserves table structure better
        # Look for the header line with labels and the next line with values
        for i, line in enumerate(lines[:10]):
            if 'Verification Number' in line and 'Pay Date' in line and 'Period End' in line:
                # This is the header line, values are on the next line
                if i + 1 < len(lines):
                    values_line = lines[i + 1]
                    # Extract values in order: VAT Number, Pay Date, Periods, Period End
                    parts = values_line.split()
                    
                    # VAT Number (10 digits)
                    vat_match = re.search(r'(\d{10})', values_line)
                    if vat_match:
                        header_data['vat_number'] = vat_match.group(1)
                    
                    # Pay Date (DD/MM/YYYY)
                    pay_dates = re.findall(r'(\d{2}/\d{2}/\d{4})', values_line)
                    if len(pay_dates) >= 2:
                        header_data['pay_date'] = pay_dates[0]
                        header_data['period_end'] = pay_dates[1]
                    
                    # Verification Number (from label line or values line)
                    verif_match = re.search(r'Verification Number[:\s]*(\d+)', line + ' ' + values_line)
                    if verif_match:
                        header_data['verification_number'] = verif_match.group(1)
                    
                    # UTR Number
                    utr_match = re.search(r'UTR Number[:\s]*(\d+)', line + ' ' + values_line)
                    if utr_match:
                        header_data['utr_number'] = utr_match.group(1)
                    
                    break
        
        return header_data
    
    def parse_financial_summary(self, text: str) -> Dict:
        """Extract financial summary from payslip."""
        financial_data = {}
        
        # Extract Total Company Income
        match = re.search(r'Total Company Income\s*£\s*([\d,]+\.?\d*)', text)
        if match:
            financial_data['total_company_income'] = float(match.group(1).replace(',', ''))
        
        # Extract Materials
        match = re.search(r'Materials\s*£\s*([\d,]+\.?\d*)', text)
        if match:
            financial_data['materials'] = float(match.group(1).replace(',', ''))
        
        # Extract Gross Subcontractor Payment (not YTD)
        matches = re.findall(r'Gross Subcontractor Payment\s*£\s*([\d,]+\.?\d*)', text)
        if matches:
            financial_data['gross_subcontractor_payment'] = float(matches[0].replace(',', ''))
        
        # Extract Gross Subcontractor Payment YTD
        match = re.search(r'Gross Subcontractor Payment YTD\s*£\s*([\d,]+\.?\d*)', text)
        if match:
            financial_data['gross_subcontractor_payment_ytd'] = float(match.group(1).replace(',', ''))
        
        # Extract Net Payment
        match = re.search(r'Net Payment\s*£\s*([\d,]+\.?\d*)', text)
        if match:
            financial_data['net_payment'] = float(match.group(1).replace(',', ''))
        
        # Extract Total Paid To Your Bank
        match = re.search(r'Total Paid To Your Bank\s*£\s*([\d,]+\.?\d*)', text)
        if match:
            financial_data['total_paid_to_bank'] = float(match.group(1).replace(',', ''))
        
        return financial_data
    
    def parse_job_items(self, text: str) -> List[Dict]:
        """Extract individual job items from payslip."""
        job_items = []
        seen_descriptions = set()  # Track seen jobs to avoid duplicates
        
        # Pattern to match job entries
        # This is complex due to the varied format, so we'll use a simpler approach
        lines = text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for deduction lines first (these don't have job numbers or pipes)
            # Format: "1.00 £(4.00) Daniel Hanson: Deduction 18/10/2025" or "Daniel Hanson: Deduction Rico 26/03/2022"
            # Or: "Company Margin £ (11.00)"
            # Important: Deduction lines should NOT have a pipe character after "Daniel Hanson:"
            deduction_match = re.search(r'Daniel Hanson:\s*Deduction', line) and '|' not in line
            margin_match = re.search(r'Company Margin\s+£\s*\(([\d,]+\.?\d*)\)', line)
            
            if deduction_match or margin_match:
                job_item = {}
                job_item['description'] = line
                job_item['job_number'] = None
                
                if deduction_match:
                    job_item['client'] = 'Deduction'
                    # Format: "1.00 £(4.00) Daniel Hanson: Deduction 18/10/2025"
                    # Extract the amount in parentheses before "Daniel Hanson:"
                    amount_match = re.search(r'£\(([\d,]+\.?\d*)\)\s+Daniel Hanson:\s*Deduction', line)
                    if amount_match:
                        amount_str = amount_match.group(1).replace(',', '')
                        job_item['rate'] = -float(amount_str)
                        job_item['units'] = 1.0
                        job_item['amount'] = job_item['rate']
                elif margin_match:
                    job_item['client'] = 'Company Margin'
                    # Format: "Company Margin £ (11.00)"
                    amount_str = margin_match.group(1).replace(',', '')
                    job_item['rate'] = -float(amount_str)
                    job_item['units'] = 1.0
                    job_item['amount'] = job_item['rate']
                
                # Only add if we found an amount
                if 'amount' in job_item:
                    job_key = f"deduction|{job_item.get('client', '')}|{job_item.get('amount', 0)}"
                    if job_key not in seen_descriptions:
                        seen_descriptions.add(job_key)
                        job_items.append(job_item)
                
                i += 1
                continue
            
            # Look for job pattern - with or without job number
            # Format 2022+: "Daniel Hanson: 2609338 | Client..."
            # Format 2021: "Daniel Hanson: Client..."
            job_match = re.match(r'Daniel Hanson:\s*(?:(\d+)\s*\|)?(.+)', line)
            if job_match and '|' in line:
                job_item = {}
                if job_match.group(1):
                    job_item['job_number'] = job_match.group(1)
                else:
                    # No job number in 2021 format, use a placeholder
                    job_item['job_number'] = None
                
                # Extract full description (may span multiple lines)
                description_parts = [line]
                j = i + 1
                # Continue reading lines that are part of the description
                # Stop when we hit a line that looks like a rate (decimal number) or agency name
                while j < len(lines):
                    next_line = lines[j].strip()
                    # Stop if empty, or if it's a standalone decimal number (rate), or agency name
                    # Also stop at common separator lines like TVS, SCS, IFM, Limited
                    if (not next_line or 
                        re.match(r'^\d+\.\d+$', next_line) or 
                        next_line in ['Rico', 'TVS', 'SCS', 'IFM', 'Limited'] or
                        re.match(r'^\d{2}/\d{2}/\d{4}$', next_line)):  # Date format
                        break
                    description_parts.append(next_line)
                    j += 1
                
                job_item['description'] = ' '.join(description_parts)
                
                # Try to parse components from description
                desc = job_item['description']
                
                # Extract client (between first | and second |)
                client_match = re.search(r'\|\s*([^|]+?)\s*\|', desc)
                if client_match:
                    job_item['client'] = client_match.group(1).strip()
                else:
                    # Fallback: Try to extract client from description after job number
                    # Format: "Daniel Hanson: 4209480 | Xerox (UK) Technical***DO"
                    fallback_match = re.search(r'Daniel Hanson:\s*\d+\s*\|\s*([^|]+?)(?:\*\*\*|$)', desc)
                    if fallback_match:
                        job_item['client'] = fallback_match.group(1).strip()
                
                # Extract location (between second | and third |)
                location_match = re.search(r'\|[^|]+\|\s*([^|]+?)\s*\|', desc)
                if location_match:
                    job_item['location'] = location_match.group(1).strip()
                
                # Extract job type (after third |, before date/time info)
                job_type_match = re.search(r'\|[^|]+\|[^|]+\|\s*([^|]+?)(?:\s*-\s*(?:ND|AP|Priority|4HR|8HR|6HR|Timed)|\s*\|)', desc)
                if job_type_match:
                    job_item['job_type'] = job_type_match.group(1).strip()
                
                # Extract dates from description (format: DD/MM/YY HH:MM)
                # Pattern: 16/03/24 09:00 or 16/03/24 09:00 17/03/24 10:30
                date_matches = re.findall(r'(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2})', desc)
                if date_matches and len(date_matches) > 0:
                    # First date/time is the job start
                    job_item['date'] = date_matches[0][0]
                    job_item['time'] = date_matches[0][1]
                
                # Look forward for units and rate
                # Format varies by year:
                # 2024-2025: "1.00 £22.50 [rest]" on line i+1 or i+2
                # 2021-2023: "1.00 £22.50 Rico [rest]" on line i+3 to i+6
                units_rate_match = None
                
                # Try 2024-2025 format first (closer to job line, no Rico)
                for offset in [1, 2]:
                    if i + offset < len(lines):
                        forward_line = lines[i+offset].strip()
                        # Match: units (decimal) followed by £rate (NOT followed by Rico immediately)
                        units_rate_match = re.match(r'([\d.]+)\s+£([\d,]+\.?\d*)\s+(?!Rico)', forward_line)
                        if units_rate_match:
                            job_item['units'] = float(units_rate_match.group(1))
                            rate_str = units_rate_match.group(2).replace(',', '')
                            job_item['rate'] = float(rate_str)
                            job_item['amount'] = job_item['units'] * job_item['rate']
                            break
                
                # If not found, try 2021-2023 format (further away, with Rico)
                if not units_rate_match:
                    for offset in range(1, 8):
                        if i + offset < len(lines):
                            forward_line = lines[i+offset].strip()
                            # Match: units (decimal) followed by £rate followed by Rico (with or without text after)
                            units_rate_match = re.match(r'([\d.]+)\s+£([\d,]+\.?\d*)\s+Rico(?:\s|$)', forward_line)
                            if units_rate_match:
                                job_item['units'] = float(units_rate_match.group(1))
                                rate_str = units_rate_match.group(2).replace(',', '')
                                job_item['rate'] = float(rate_str)
                                job_item['amount'] = job_item['units'] * job_item['rate']
                                break
                
                # Look forward for agency and date
                for k in range(i+1, min(i+5, len(lines))):
                    if re.match(r'^Rico$', lines[k].strip()):
                        job_item['agency'] = 'Rico'
                        if k+1 < len(lines):
                            date_match = re.match(r'(\d{2}/\d{2}/\d{4})', lines[k+1].strip())
                            if date_match:
                                job_item['weekend_date'] = date_match.group(1)
                        break
                
                # Create a unique key for this job to detect duplicates
                # Include job_number to ensure uniqueness even if other fields match
                job_key = f"{job_item.get('job_number', '')}|{job_item.get('client', '')}|{job_item.get('location', '')}|{job_item.get('date', '')}|{job_item.get('time', '')}|{job_item.get('amount', 0)}"
                
                # Only add if we haven't seen this exact job before
                if job_key not in seen_descriptions:
                    seen_descriptions.add(job_key)
                    job_items.append(job_item)
            
            i += 1
        
        return job_items
    
    def extract_from_filename(self, filename: str) -> Dict:
        """Extract tax year and week number from filename."""
        # Try format: Week52 2021 or Week52_2021
        match = re.search(r'Week(\d+)[\s_]+(\d{4})', filename)
        if match:
            return {
                'week_number': int(match.group(1)),
                'tax_year': match.group(2)
            }
        return {}
    
    def process_payslip(self, pdf_path) -> Optional[int]:
        """Process a single payslip PDF and insert into database."""
        # Handle both Path and str types
        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)
        print(f"Processing: {pdf_path.name}")
        
        try:
            # Extract text
            text = self.extract_text_from_pdf(str(pdf_path))
            
            # Parse data
            file_data = self.extract_from_filename(pdf_path.name)
            header_data = self.parse_payslip_header(text)
            financial_data = self.parse_financial_summary(text)
            job_items = self.parse_job_items(text)
            
            # Combine all data
            payslip_data = {
                **file_data,
                **header_data,
                **financial_data,
                'pdf_filename': pdf_path.name
            }
            
            # Insert payslip summary
            cursor = self.conn.cursor()
            
            # First, check if this payslip already exists and delete its old job items
            cursor.execute("""
                DELETE FROM job_items 
                WHERE payslip_id IN (
                    SELECT id FROM payslips 
                    WHERE tax_year = ? AND week_number = ?
                )
            """, (payslip_data.get('tax_year'), payslip_data.get('week_number')))
            
            cursor.execute("""
                INSERT OR REPLACE INTO payslips (
                    tax_year, week_number, verification_number, utr_number,
                    pay_date, period_end, vat_number, total_company_income,
                    materials, gross_subcontractor_payment,
                    gross_subcontractor_payment_ytd, net_payment,
                    total_paid_to_bank, pdf_filename
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payslip_data.get('tax_year'),
                payslip_data.get('week_number'),
                payslip_data.get('verification_number'),
                payslip_data.get('utr_number'),
                payslip_data.get('pay_date'),
                payslip_data.get('period_end'),
                payslip_data.get('vat_number'),
                payslip_data.get('total_company_income'),
                payslip_data.get('materials'),
                payslip_data.get('gross_subcontractor_payment'),
                payslip_data.get('gross_subcontractor_payment_ytd'),
                payslip_data.get('net_payment'),
                payslip_data.get('total_paid_to_bank'),
                payslip_data.get('pdf_filename')
            ))
            
            payslip_id = cursor.lastrowid
            
            # Insert job items
            for job_item in job_items:
                cursor.execute("""
                    INSERT INTO job_items (
                        payslip_id, units, rate, amount, description,
                        job_number, client, location, job_type, date, time, agency, weekend_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    payslip_id,
                    job_item.get('units'),
                    job_item.get('rate'),
                    job_item.get('amount'),
                    job_item.get('description'),
                    job_item.get('job_number'),
                    job_item.get('client'),
                    job_item.get('location'),
                    job_item.get('job_type'),
                    job_item.get('date'),
                    job_item.get('time'),
                    job_item.get('agency'),
                    job_item.get('weekend_date')
                ))
            
            self.conn.commit()
            print(f"  ✓ Extracted: £{payslip_data.get('net_payment', 0):.2f}, {len(job_items)} jobs")
            return payslip_id
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return None
    
    def process_all_payslips(self, payslips_dir: str = "PaySlips"):
        """Process all payslip PDFs in the directory."""
        payslips_path = Path(payslips_dir)
        
        if not payslips_path.exists():
            print(f"Error: Directory {payslips_dir} not found")
            return
        
        # Find all PDF files
        pdf_files = sorted(payslips_path.rglob("*.pdf"))
        
        print(f"Found {len(pdf_files)} PDF files")
        print("=" * 60)
        
        success_count = 0
        for pdf_file in pdf_files:
            if self.process_payslip(pdf_file):
                success_count += 1
        
        print("=" * 60)
        print(f"Successfully processed: {success_count}/{len(pdf_files)} payslips")
        
        # Automatically sync payslip data to runsheets if any payslips were processed
        if success_count > 0:
            self._sync_to_runsheets()
    
    def _sync_to_runsheets(self):
        """Sync processed payslip data to runsheet records."""
        try:
            # Import here to avoid circular imports
            import sys
            from pathlib import Path
            
            # Add the app directory to the path
            app_path = Path(__file__).parent.parent / 'app'
            sys.path.insert(0, str(app_path))
            
            from services.runsheet_sync_service import RunsheetSyncService
            
            print("\n" + "=" * 60)
            print("SYNCING PAYSLIP DATA TO RUNSHEETS")
            print("=" * 60)
            
            result = RunsheetSyncService.sync_payslip_data_to_runsheets()
            
            if result['success']:
                # Get and display statistics
                stats = RunsheetSyncService.get_sync_statistics()
                if stats:
                    print(f"\n📊 SYNC STATISTICS:")
                    print(f"   Total runsheet jobs: {stats['total_jobs']:,}")
                    print(f"   Jobs with pay info: {stats['jobs_with_pay']:,} ({stats['pay_match_rate']:.1f}%)")
                    print(f"   Jobs with addresses: {stats['jobs_with_address']:,} ({stats['address_completion_rate']:.1f}%)")
                    print(f"   Jobs with customer info: {stats['jobs_with_customer']:,} ({stats['customer_completion_rate']:.1f}%)")
                    print(f"   Average pay per job: £{stats['avg_pay']}")
                    print(f"   Total pay tracked: £{stats['total_pay']:,}")
            else:
                print(f"❌ Sync failed: {result.get('error', 'Unknown error')}")
                
        except ImportError as e:
            print(f"⚠️  Could not import sync service: {e}")
            print("   Payslip data processed but not synced to runsheets")
        except Exception as e:
            print(f"❌ Error during sync: {e}")
            print("   Payslip data processed but sync failed")
    
    def get_summary_stats(self):
        """Print summary statistics from the database."""
        cursor = self.conn.cursor()
        
        print("\n" + "=" * 60)
        print("DATABASE SUMMARY")
        print("=" * 60)
        
        # Total payslips
        cursor.execute("SELECT COUNT(*) FROM payslips")
        total_payslips = cursor.fetchone()[0]
        print(f"Total payslips: {total_payslips}")
        
        # Total jobs
        cursor.execute("SELECT COUNT(*) FROM job_items")
        total_jobs = cursor.fetchone()[0]
        print(f"Total job items: {total_jobs}")
        
        # Total earnings
        cursor.execute("SELECT SUM(net_payment) FROM payslips")
        total_earnings = cursor.fetchone()[0] or 0
        print(f"Total net earnings: £{total_earnings:,.2f}")
        
        # By tax year
        cursor.execute("""
            SELECT tax_year, COUNT(*), SUM(net_payment)
            FROM payslips
            GROUP BY tax_year
            ORDER BY tax_year
        """)
        print("\nBy tax year:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} weeks, £{row[2]:,.2f}")
        
        # Average per week
        if total_payslips > 0:
            avg_per_week = total_earnings / total_payslips
            print(f"\nAverage per week: £{avg_per_week:,.2f}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def main():
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description='Extract payslip data from PDFs')
    parser.add_argument('--file', type=str, help='Process a single specific file')
    parser.add_argument('--recent', type=int, help='Only process files modified in last N days')
    parser.add_argument('--directory', type=str, help='Directory to process files from')
    args = parser.parse_args()
    
    extractor = PayslipExtractor()
    
    try:
        if args.file:
            # Process single file
            from pathlib import Path
            file_path = Path(args.file)
            if not file_path.exists():
                print(f"Error: File not found: {file_path}")
                sys.exit(1)
            
            print(f"Processing single file: {file_path}")
            result = extractor.process_payslip(str(file_path))
            
            if result:
                print(f"\n✓ Successfully processed {file_path.name}")
                sys.exit(0)
            else:
                print(f"\n⚠️  Failed to process {file_path.name}")
                sys.exit(1)
        else:
            # Process all payslips (with optional filters)
            if args.directory:
                extractor.process_all_payslips(args.directory)
            else:
                extractor.process_all_payslips()
            extractor.get_summary_stats()
    finally:
        extractor.close()
    
    print(f"\nDatabase saved to: {extractor.db_path}")


if __name__ == "__main__":
    main()
