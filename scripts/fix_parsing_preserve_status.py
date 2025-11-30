#!/usr/bin/env python3
"""
Fix Parsing While Preserving Status
Updates job parsing data (address, activity, postcode) while preserving status and other important fields.
Usage: python3 fix_parsing_preserve_status.py --date YYYY-MM-DD --job-number XXXXXXX
"""

import sys
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime
import PyPDF2
import re
from typing import Dict, List

# Import the parsing logic
sys.path.append(str(Path(__file__).parent))
from import_run_sheets import RunSheetImporter

class StatusPreservingParser:
    def __init__(self, db_path: str = "data/database/payslips.db"):
        self.db_path = Path(db_path)
        self.importer = RunSheetImporter()
    
    def backup_job_status(self, job_number: str, date: str) -> Dict:
        """Backup all the important status information for a job."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, status, pay_amount, mileage, fuel_cost, notes, 
                   completed_at, dnco_reason, manual_override
            FROM run_sheet_jobs 
            WHERE job_number = ? AND date = ?
        """, (job_number, date))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'status': result[1],
                'pay_amount': result[2],
                'mileage': result[3],
                'fuel_cost': result[4],
                'notes': result[5],
                'completed_at': result[6],
                'dnco_reason': result[7],
                'manual_override': result[8]
            }
        return None
    
    def restore_job_status(self, job_number: str, date: str, backup_data: Dict):
        """Restore the status information after re-parsing."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE run_sheet_jobs SET
                status = ?, pay_amount = ?, mileage = ?, fuel_cost = ?, 
                notes = ?, completed_at = ?, dnco_reason = ?, manual_override = ?
            WHERE job_number = ? AND date = ?
        """, (
            backup_data['status'],
            backup_data['pay_amount'],
            backup_data['mileage'],
            backup_data['fuel_cost'],
            backup_data['notes'],
            backup_data['completed_at'],
            backup_data['dnco_reason'],
            backup_data['manual_override'],
            job_number,
            date
        ))
        
        conn.commit()
        conn.close()
    
    def fix_single_job(self, job_number: str, date: str) -> bool:
        """Fix parsing for a single job while preserving status."""
        print(f"🔧 Fixing job {job_number} on {date}...")
        
        # Step 1: Backup status information
        backup = self.backup_job_status(job_number, date)
        if not backup:
            print(f"❌ Job {job_number} not found")
            return False
        
        print(f"💾 Backed up status: {backup['status']}")
        
        # Step 2: Get the current job data
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT customer, job_address, activity, postcode
            FROM run_sheet_jobs 
            WHERE job_number = ? AND date = ?
        """, (job_number, date))
        
        current_job = cursor.fetchone()
        if not current_job:
            print(f"❌ Could not find current job data")
            return False
        
        current_customer, current_address, current_activity, current_postcode = current_job
        print(f"📋 Current: {current_customer}")
        print(f"   Address: {current_address}")
        print(f"   Activity: {current_activity}")
        
        # Step 3: Re-parse the job from PDF
        pdf_date = datetime.strptime(date, "%d/%m/%Y").strftime("%Y-%m-%d")
        pdf_path = Path(f"data/documents/runsheets/{pdf_date[:4]}/{pdf_date[5:7]}-{datetime.strptime(date, '%d/%m/%Y').strftime('%B')}/DH_{pdf_date}.pdf")
        
        if not pdf_path.exists():
            print(f"❌ PDF not found: {pdf_path}")
            return False
        
        # Parse the PDF and find this specific job
        jobs = self.importer.parse_pdf_run_sheet(str(pdf_path))
        target_job = None
        
        for job in jobs:
            if job.get('job_number') == job_number:
                target_job = job
                break
        
        if not target_job:
            print(f"❌ Job {job_number} not found in PDF")
            return False
        
        # Step 4: Update only the parsing fields
        cursor.execute("""
            UPDATE run_sheet_jobs SET
                customer = ?, activity = ?, job_address = ?, postcode = ?,
                imported_at = CURRENT_TIMESTAMP
            WHERE job_number = ? AND date = ?
        """, (
            target_job.get('customer', current_customer),
            target_job.get('activity', current_activity),
            target_job.get('job_address', current_address),
            target_job.get('postcode', current_postcode),
            job_number,
            date
        ))
        
        conn.commit()
        
        # Step 5: Restore status information
        self.restore_job_status(job_number, date, backup)
        
        # Step 6: Verify the fix
        cursor.execute("""
            SELECT customer, activity, job_address, postcode, status
            FROM run_sheet_jobs 
            WHERE job_number = ? AND date = ?
        """, (job_number, date))
        
        updated_job = cursor.fetchone()
        conn.close()
        
        if updated_job:
            customer, activity, address, postcode, status = updated_job
            print(f"✅ Updated parsing:")
            print(f"   Customer: {customer}")
            print(f"   Activity: {activity}")
            print(f"   Address: {address}")
            print(f"   Postcode: {postcode}")
            print(f"💾 Status preserved: {status}")
            
            # Check if the fix worked
            if current_address != address:
                print(f"🎉 Address improved!")
            if current_activity != activity:
                print(f"🎉 Activity improved!")
            
            return True
        
        return False
    
    def fix_date_jobs(self, date: str, job_numbers: List[str] = None) -> int:
        """Fix parsing for all jobs on a date while preserving status."""
        print(f"🔧 Fixing parsing for {date}...")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get jobs to fix
        if job_numbers:
            placeholders = ','.join(['?' for _ in job_numbers])
            cursor.execute(f"""
                SELECT job_number, status 
                FROM run_sheet_jobs 
                WHERE date = ? AND job_number IN ({placeholders})
            """, [date] + job_numbers)
        else:
            cursor.execute("""
                SELECT job_number, status 
                FROM run_sheet_jobs 
                WHERE date = ?
            """, (date,))
        
        jobs_to_fix = cursor.fetchall()
        conn.close()
        
        if not jobs_to_fix:
            print(f"❌ No jobs found for {date}")
            return 0
        
        print(f"📋 Found {len(jobs_to_fix)} jobs to fix")
        
        fixed_count = 0
        for job_number, status in jobs_to_fix:
            print(f"\n--- Job {job_number} (status: {status}) ---")
            if self.fix_single_job(job_number, date):
                fixed_count += 1
        
        print(f"\n✅ Fixed {fixed_count}/{len(jobs_to_fix)} jobs")
        return fixed_count

def main():
    parser = argparse.ArgumentParser(description="Fix parsing while preserving job status")
    parser.add_argument('--date', required=True, help='Date in DD/MM/YYYY format')
    parser.add_argument('--job-number', help='Specific job number to fix')
    parser.add_argument('--all', action='store_true', help='Fix all jobs for the date')
    
    args = parser.parse_args()
    
    fixer = StatusPreservingParser()
    
    if args.job_number:
        success = fixer.fix_single_job(args.job_number, args.date)
        if success:
            print(f"\n🎉 Successfully fixed job {args.job_number}")
        else:
            print(f"\n❌ Failed to fix job {args.job_number}")
    elif args.all:
        fixed_count = fixer.fix_date_jobs(args.date)
        print(f"\n🎉 Fixed {fixed_count} jobs for {args.date}")
    else:
        print("❌ Please specify --job-number or --all")

if __name__ == "__main__":
    main()
