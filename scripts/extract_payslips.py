#!/usr/bin/env python3
"""
Extract payslip data from PDFs and store in SQLite database.
"""

import PyPDF2
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json


class PayslipExtractor:
    def __init__(self, db_path: str = "data/payslips.db"):
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
        """Extract all text from a PDF file."""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    def parse_payslip_header(self, text: str) -> Dict:
        """Extract header information from payslip."""
        header_data = {}
        
        # Extract verification number
        match = re.search(r'Verification Number\s*(\d+)', text)
        if match:
            header_data['verification_number'] = match.group(1)
        
        # Extract UTR number
        match = re.search(r'UTR Number\s*(\d+)', text)
        if match:
            header_data['utr_number'] = match.group(1)
        
        # Extract pay date
        match = re.search(r'Pay Date\s*(\d{2}/\d{2}/\d{4})', text)
        if match:
            header_data['pay_date'] = match.group(1)
        
        # Extract period end
        match = re.search(r'Period End\s*(\d{2}/\d{2}/\d{4})', text)
        if match:
            header_data['period_end'] = match.group(1)
        
        # Extract VAT number
        match = re.search(r'VAT Number\s*(\d+)', text)
        if match:
            header_data['vat_number'] = match.group(1)
        
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
                    if not next_line or re.match(r'^\d+\.\d+$', next_line) or next_line == 'Rico':
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
                
                # Look backwards for units and rate
                if i > 0:
                    prev_line = lines[i-1].strip()
                    rate_match = re.match(r'£\(?([\d,]+\.?\d*)\)?', prev_line)
                    if rate_match:
                        rate_str = rate_match.group(1).replace(',', '')
                        job_item['rate'] = float(rate_str) if not prev_line.startswith('£(') else -float(rate_str)
                        
                        if i > 1:
                            units_match = re.match(r'([\d.]+)', lines[i-2].strip())
                            if units_match:
                                job_item['units'] = float(units_match.group(1))
                                job_item['amount'] = job_item['units'] * job_item['rate']
                
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
                job_key = f"{job_item.get('client', '')}|{job_item.get('location', '')}|{job_item.get('date', '')}|{job_item.get('time', '')}|{job_item.get('amount', 0)}"
                
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
    
    def process_payslip(self, pdf_path: Path) -> Optional[int]:
        """Process a single payslip PDF and insert into database."""
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
    extractor = PayslipExtractor()
    
    try:
        extractor.process_all_payslips()
        extractor.get_summary_stats()
    finally:
        extractor.close()
    
    print(f"\nDatabase saved to: {extractor.db_path}")


if __name__ == "__main__":
    main()
