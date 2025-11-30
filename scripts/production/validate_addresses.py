#!/usr/bin/env python3
"""
Address Validation and Cleanup Script

Automatically validates and cleans up addresses after runsheet imports.
Fixes common parsing issues like phone numbers, duplicates, and formatting problems.

Usage:
    python validate_addresses.py --date 29/11/2025    # Validate specific date
    python validate_addresses.py --recent 7           # Validate last 7 days
    python validate_addresses.py --all                # Validate all addresses
"""

import sqlite3
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add the project root to the path so we can import modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class AddressValidator:
    def __init__(self, db_path='data/database/payslips.db'):
        self.db_path = Path(project_root) / db_path
        self.fixes_applied = 0
        self.issues_found = 0
        self.validation_report = []
        
    def connect_db(self):
        """Connect to the database."""
        return sqlite3.connect(self.db_path)
    
    def get_jobs_to_validate(self, date_filter=None, recent_days=None):
        """Get jobs that need address validation."""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        if date_filter:
            # Validate specific date (excluding RICO)
            cursor.execute("""
                SELECT id, job_number, date, customer, job_address, postcode
                FROM run_sheet_jobs 
                WHERE date = ?
                AND customer NOT LIKE '%RICO%'
                AND (job_address IS NULL OR job_address NOT LIKE '%RICO%')
                ORDER BY job_number
            """, (date_filter,))
        elif recent_days:
            # Validate recent days (excluding RICO)
            cursor.execute("""
                SELECT id, job_number, date, customer, job_address, postcode
                FROM run_sheet_jobs 
                WHERE date >= date('now', '-{} days')
                AND customer NOT LIKE '%RICO%'
                AND (job_address IS NULL OR job_address NOT LIKE '%RICO%')
                ORDER BY date DESC, job_number
            """.format(recent_days))
        else:
            # Validate all jobs (excluding RICO)
            cursor.execute("""
                SELECT id, job_number, date, customer, job_address, postcode
                FROM run_sheet_jobs 
                WHERE customer NOT LIKE '%RICO%'
                AND (job_address IS NULL OR job_address NOT LIKE '%RICO%')
                ORDER BY date DESC, job_number
            """)
        
        jobs = cursor.fetchall()
        conn.close()
        return jobs
    
    def clean_phone_numbers(self, address):
        """Remove phone numbers from the beginning of addresses."""
        if not address:
            return address, False
        
        original = address
        
        # Remove phone numbers at the start (various formats)
        patterns = [
            r'^[\d\s]{10,}\s*',           # 10+ digits with spaces
            r'^\d{11}\s*',                # 11 digits (UK mobile)
            r'^\d{10}\s*',                # 10 digits
            r'^0\d{10}\s*',               # UK landline format
            r'^\d{5,}\s*,\s*\d{5,}\s*',   # Multiple phone numbers
            r'^[\d\s,]{15,}\s*',          # Long string of digits/spaces/commas
        ]
        
        for pattern in patterns:
            if re.match(pattern, address):
                cleaned = re.sub(pattern, '', address)
                if cleaned != address:
                    return cleaned.strip(), True
        
        return address, False
    
    def remove_duplicate_names(self, address, customer):
        """Remove duplicate company names from addresses."""
        if not address or not customer:
            return address, False
        
        original = address
        
        # Extract main company name from customer field
        company_parts = []
        if 'John Lewis' in customer:
            company_parts = ['JOHN LEWIS', 'JOHN LEWIS PLC']
        elif 'Waitrose' in customer:
            company_parts = ['WAITROSE', 'WAITROSE LTD']
        elif 'Paypoint' in customer:
            # Extract the actual store name after the last dash
            if ' - ' in customer:
                store_name = customer.split(' - ')[-1].upper()
                company_parts = [store_name]
        elif 'CXM' in customer:
            # Look for hotel/venue names in the address
            if 'HOTEL' in address.upper():
                company_parts = ['HOTEL']
        
        # Remove duplicates
        for part in company_parts:
            # Count occurrences
            count = address.upper().count(part)
            if count > 1:
                # Remove first occurrence if it's at the start
                if address.upper().startswith(part):
                    address = address[len(part):].lstrip(', ')
                    return address, True
        
        return address, False
    
    def remove_prefixes(self, address):
        """Remove common unwanted prefixes."""
        if not address:
            return address, False
        
        original = address
        prefixes_to_remove = [
            'n/a',
            'N/A',
            'tbc',
            'TBC',
            'pending',
            'PENDING'
        ]
        
        for prefix in prefixes_to_remove:
            if address.startswith(prefix):
                cleaned = address[len(prefix):].lstrip(', ')
                if cleaned:
                    return cleaned, True
        
        return address, False
    
    def validate_postcode(self, postcode):
        """Check if postcode looks valid."""
        if not postcode:
            return False, "Missing postcode"
        
        # UK postcode pattern
        uk_postcode_pattern = r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}$'
        if not re.match(uk_postcode_pattern, postcode.upper()):
            return False, f"Invalid postcode format: {postcode}"
        
        return True, None
    
    def validate_address_length(self, address):
        """Check if address is too short or suspicious."""
        if not address:
            return False, "Empty address"
        
        if len(address) < 10:
            return False, f"Address too short ({len(address)} chars): {address}"
        
        # Check for parsing artifacts
        artifacts = ['SLA', 'Contact', 'Window', 'Priority', 'Instructions']
        for artifact in artifacts:
            if artifact in address:
                return False, f"Contains parsing artifact '{artifact}': {address}"
        
        return True, None
    
    def fix_address(self, job_id, job_number, customer, address, postcode):
        """Apply automatic fixes to an address."""
        original_address = address
        fixed = False
        fixes_applied = []
        
        # Apply fixes in order
        address, phone_fixed = self.clean_phone_numbers(address)
        if phone_fixed:
            fixes_applied.append("Removed phone numbers")
            fixed = True
        
        address, prefix_fixed = self.remove_prefixes(address)
        if prefix_fixed:
            fixes_applied.append("Removed prefix")
            fixed = True
        
        address, duplicate_fixed = self.remove_duplicate_names(address, customer)
        if duplicate_fixed:
            fixes_applied.append("Removed duplicates")
            fixed = True
        
        # Clean up extra spaces and commas
        if address:
            cleaned_address = re.sub(r'\s+', ' ', address)  # Multiple spaces
            cleaned_address = re.sub(r',\s*,', ',', cleaned_address)  # Double commas
            cleaned_address = cleaned_address.strip(', ')  # Leading/trailing commas
            
            if cleaned_address != address:
                address = cleaned_address
                fixes_applied.append("Cleaned formatting")
                fixed = True
        
        # Update database if fixes were applied
        if fixed and address != original_address:
            conn = self.connect_db()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE run_sheet_jobs 
                SET job_address = ?
                WHERE id = ?
            """, (address, job_id))
            conn.commit()
            conn.close()
            
            self.fixes_applied += 1
            print(f"✅ Fixed Job {job_number}: {' + '.join(fixes_applied)}")
            print(f"   Before: {original_address}")
            print(f"   After:  {address}")
            print()
        
        return address, fixed, fixes_applied
    
    def validate_job(self, job_id, job_number, date, customer, address, postcode):
        """Validate a single job's address."""
        issues = []
        
        # Apply automatic fixes first
        fixed_address, was_fixed, fixes = self.fix_address(job_id, job_number, customer, address, postcode)
        
        # Validate the (potentially fixed) address
        address_valid, address_issue = self.validate_address_length(fixed_address)
        if not address_valid:
            issues.append(address_issue)
        
        postcode_valid, postcode_issue = self.validate_postcode(postcode)
        if not postcode_valid:
            issues.append(postcode_issue)
        
        # Record issues that couldn't be automatically fixed
        if issues:
            self.issues_found += 1
            self.validation_report.append({
                'job_number': job_number,
                'date': date,
                'customer': customer,
                'address': fixed_address,
                'postcode': postcode,
                'issues': issues,
                'auto_fixed': was_fixed
            })
            
            if not was_fixed:  # Only print if we didn't already print the fix
                print(f"⚠️  Job {job_number} ({date}): {', '.join(issues)}")
    
    def run_validation(self, date_filter=None, recent_days=None, validate_all=False):
        """Run the validation process."""
        print("🔍 Starting address validation...")
        print()
        
        # Get jobs to validate
        if validate_all:
            jobs = self.get_jobs_to_validate()
            print(f"Validating all {len(jobs)} jobs...")
        elif date_filter:
            jobs = self.get_jobs_to_validate(date_filter=date_filter)
            print(f"Validating {len(jobs)} jobs for {date_filter}...")
        elif recent_days:
            jobs = self.get_jobs_to_validate(recent_days=recent_days)
            print(f"Validating {len(jobs)} jobs from last {recent_days} days...")
        else:
            print("❌ No validation criteria specified")
            return
        
        print()
        
        # Validate each job
        for job_id, job_number, date, customer, address, postcode in jobs:
            self.validate_job(job_id, job_number, date, customer, address, postcode)
        
        # Print summary
        print("=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Jobs validated: {len(jobs)}")
        print(f"Fixes applied: {self.fixes_applied}")
        print(f"Issues found: {self.issues_found}")
        print()
        
        # Print detailed report of remaining issues
        if self.validation_report:
            print("📋 REMAINING ISSUES:")
            print("-" * 40)
            for issue in self.validation_report:
                if not issue['auto_fixed']:  # Only show issues that weren't fixed
                    print(f"Job {issue['job_number']} ({issue['date']})")
                    print(f"  Customer: {issue['customer']}")
                    print(f"  Address: {issue['address']}")
                    print(f"  Issues: {', '.join(issue['issues'])}")
                    print()
        
        if self.fixes_applied > 0:
            print(f"✅ Successfully applied {self.fixes_applied} automatic fixes!")
        
        if self.issues_found == 0:
            print("🎉 All addresses look good!")
        elif self.issues_found > self.fixes_applied:
            remaining = self.issues_found - self.fixes_applied
            print(f"⚠️  {remaining} issues require manual review")

def main():
    parser = argparse.ArgumentParser(description='Validate and clean up job addresses')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--date', help='Validate specific date (DD/MM/YYYY)')
    group.add_argument('--recent', type=int, help='Validate last N days')
    group.add_argument('--all', action='store_true', help='Validate all addresses')
    
    args = parser.parse_args()
    
    validator = AddressValidator()
    
    if args.date:
        validator.run_validation(date_filter=args.date)
    elif args.recent:
        validator.run_validation(recent_days=args.recent)
    elif args.all:
        validator.run_validation(validate_all=True)

if __name__ == '__main__':
    main()
