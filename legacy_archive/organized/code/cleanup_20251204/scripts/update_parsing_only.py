#!/usr/bin/env python3
"""
Update Parsing Fields Only
Updates only the parsing fields (address, activity, postcode) while preserving ALL other data.
Usage: python3 update_parsing_only.py --job-number 4298932 --date 28/11/2025
"""

import sys
import sqlite3
import argparse
from pathlib import Path
import re

def clean_hsbc_address(address: str) -> str:
    """Apply HSBC-specific cleaning to an address."""
    if not address:
        return address
    
    # Clean +44 phone numbers from start
    cleaned = re.sub(r'^\+44\d+', '', address)
    
    # Clean other phone number formats
    cleaned = re.sub(r'^[\d\s]{10,}\s*', '', cleaned)
    
    return cleaned.strip()

def extract_postcode_from_address(address: str) -> tuple:
    """Extract postcode from address string and return (clean_address, postcode)."""
    if not address:
        return address, None
    
    # Look for UK postcode pattern
    postcode_match = re.search(r'\b([A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2})\b', address)
    if postcode_match:
        postcode = postcode_match.group(1)
        
        # Format postcode properly (add space if missing)
        if len(postcode) >= 6 and ' ' not in postcode:
            postcode = postcode[:-3] + ' ' + postcode[-3:]
        
        # Remove postcode from address
        clean_address = re.sub(r'\b[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}\b', '', address).strip(' ,')
        
        return clean_address, postcode
    
    return address, None

def update_job_parsing(job_number: str, date: str):
    """Update parsing fields for a specific job while preserving all other data."""
    print(f"🔧 Updating parsing for job {job_number} on {date}...")
    
    conn = sqlite3.connect('data/database/payslips.db')
    cursor = conn.cursor()
    
    try:
        # Get current job data
        cursor.execute("""
            SELECT job_number, customer, activity, job_address, postcode, status, pay_amount
            FROM run_sheet_jobs 
            WHERE job_number = ? AND date = ?
        """, (job_number, date))
        
        job_data = cursor.fetchone()
        if not job_data:
            print(f"❌ Job {job_number} not found for date {date}")
            return False
        
        job_num, customer, activity, address, postcode, status, pay_amount = job_data
        
        print(f"📋 Current job:")
        print(f"   Customer: {customer}")
        print(f"   Activity: {activity}")
        print(f"   Address: {address}")
        print(f"   Postcode: {postcode or 'MISSING'}")
        print(f"   Status: {status} (WILL BE PRESERVED)")
        
        # Apply customer-specific improvements
        new_address = address
        new_activity = activity
        new_postcode = postcode
        
        # Extract postcode from address if missing
        if not postcode and address:
            clean_address, extracted_postcode = extract_postcode_from_address(address)
            if extracted_postcode:
                new_address = clean_address
                new_postcode = extracted_postcode
        
        if customer and 'HSBC' in customer.upper():
            print(f"🔧 Applying HSBC parser improvements...")
            new_address = clean_hsbc_address(new_address or address)
            if not new_activity:
                new_activity = 'TECH EXCHANGE'
        
        # Check if anything changed
        changes = []
        if new_address != address:
            changes.append(f"Address: '{address}' → '{new_address}'")
        if new_activity != activity:
            changes.append(f"Activity: '{activity}' → '{new_activity}'")
        if new_postcode != postcode:
            changes.append(f"Postcode: '{postcode or 'MISSING'}' → '{new_postcode}'")
        
        if not changes:
            print(f"✅ No parsing improvements needed")
            return True
        
        print(f"🔄 Applying changes:")
        for change in changes:
            print(f"   {change}")
        
        # Update only the parsing fields
        cursor.execute("""
            UPDATE run_sheet_jobs SET
                activity = ?, job_address = ?, postcode = ?, imported_at = CURRENT_TIMESTAMP
            WHERE job_number = ? AND date = ?
        """, (new_activity, new_address, new_postcode, job_number, date))
        
        conn.commit()
        
        # Verify the update
        cursor.execute("""
            SELECT customer, activity, job_address, postcode, status, pay_amount
            FROM run_sheet_jobs 
            WHERE job_number = ? AND date = ?
        """, (job_number, date))
        
        updated_job = cursor.fetchone()
        
        if updated_job:
            customer, activity, address, postcode, status, pay_amount = updated_job
            print(f"✅ Updated successfully:")
            print(f"   Customer: {customer}")
            print(f"   Activity: {activity}")
            print(f"   Address: {address}")
            print(f"   Postcode: {postcode}")
            print(f"   Status: {status} (PRESERVED)")
            print(f"   Pay: £{pay_amount or '0.00'} (PRESERVED)")
            return True
        else:
            print(f"❌ Failed to verify update")
            return False
            
    except Exception as e:
        print(f"❌ Error updating job: {e}")
        return False
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Update parsing fields while preserving status")
    parser.add_argument('--job-number', required=True, help='Job number to update')
    parser.add_argument('--date', required=True, help='Date in DD/MM/YYYY format')
    
    args = parser.parse_args()
    
    success = update_job_parsing(args.job_number, args.date)
    
    if success:
        print(f"\n🎉 Successfully updated job {args.job_number}")
    else:
        print(f"\n❌ Failed to update job {args.job_number}")

if __name__ == "__main__":
    main()
