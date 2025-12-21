#!/usr/bin/env python3
"""
Re-import existing runsheets using Camelot table-based extraction.
This will update existing jobs with cleaner data from Camelot parsing.
"""

import sys
import sqlite3
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'testing'))

from camelot_runsheet_parser import CamelotRunsheetParser

DB_PATH = "data/database/payslips.db"


def reimport_runsheet(pdf_path: str, replace_existing: bool = False, preview_only: bool = True):
    """Re-import a single runsheet using Camelot."""
    print(f"\nProcessing: {Path(pdf_path).name}")
    
    # Parse with Camelot
    parser = CamelotRunsheetParser()
    jobs = parser.parse_pdf(pdf_path)
    
    if not jobs:
        print(f"  ⚠️  No jobs extracted")
        return 0, []
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updated = 0
    added = 0
    skipped = 0
    new_jobs = []
    
    for job in jobs:
        job_number = job.get('job_number')
        date = job.get('date')
        
        if not job_number or not date:
            continue
        
        # Check if job exists
        cursor.execute("""
            SELECT id FROM run_sheet_jobs 
            WHERE date = ? AND job_number = ?
        """, (date, job_number))
        
        existing = cursor.fetchone()
        
        if existing:
            if replace_existing and not preview_only:
                # Update existing job with Camelot data
                cursor.execute("""
                    UPDATE run_sheet_jobs SET
                        customer = ?,
                        activity = ?,
                        job_address = ?,
                        postcode = ?,
                        source_file = ?
                    WHERE id = ?
                """, (
                    job.get('customer'),
                    job.get('activity'),
                    job.get('job_address'),
                    job.get('postcode'),
                    Path(pdf_path).name,
                    existing[0]
                ))
                updated += 1
            elif replace_existing:
                updated += 1  # Count for preview
            else:
                skipped += 1
        else:
            # New job - flag for review (skip PP Audit jobs as they're not real)
            customer = job.get('customer', '')
            if 'PP Audit' not in customer:
                new_jobs.append({
                    'job_number': job_number,
                    'customer': customer,
                    'activity': job.get('activity'),
                    'address': job.get('job_address'),
                    'postcode': job.get('postcode'),
                    'date': date
                })
            
            if not preview_only:
                # Insert new job
                cursor.execute("""
                    INSERT INTO run_sheet_jobs (
                        date, driver, job_number, customer, activity,
                        job_address, postcode, source_file, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (
                    date,
                    job.get('driver', 'Daniel Hanson'),
                    job_number,
                    job.get('customer'),
                    job.get('activity'),
                    job.get('job_address'),
                    job.get('postcode'),
                    Path(pdf_path).name
                ))
            added += 1
    
    if not preview_only:
        conn.commit()
    conn.close()
    
    if preview_only and new_jobs:
        print(f"  ⚠️  Found {len(new_jobs)} NEW jobs that would be added:")
        for nj in new_jobs:
            print(f"      - Job #{nj['job_number']}: {nj['customer']} - {nj['activity']}")
    
    print(f"  ✓ Updated: {updated}, Would Add: {added}, Skipped: {skipped}")
    return updated + added, new_jobs


def reimport_month(year: str, month: str, replace_existing: bool = False, preview_only: bool = True):
    """Re-import all runsheets for a specific month."""
    runsheets_dir = Path('data/documents/runsheets')
    
    # Connect to database to check attendance
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Find all DH runsheets for this month
    pattern = f"DH_*-{month}-{year}.pdf"
    files = list(runsheets_dir.rglob(pattern))
    
    if not files:
        print(f"No runsheets found for {month}/{year}")
        conn.close()
        return
    
    mode = "PREVIEW MODE" if preview_only else "LIVE MODE"
    print(f"\n{'='*80}")
    print(f"Re-importing {len(files)} runsheets for {month}/{year} - {mode}")
    print(f"Replace existing: {replace_existing}")
    print(f"{'='*80}")
    
    total_jobs = 0
    all_new_jobs = []
    skipped_days = []
    
    for pdf_file in sorted(files):
        # Extract date from filename
        import re
        date_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', pdf_file.name)
        if not date_match:
            continue
        
        date_str = f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}"
        
        # Check if PDF exists
        if not pdf_file.exists():
            print(f"\n⚠️  Skipping {pdf_file.name} - PDF not found")
            skipped_days.append({'date': date_str, 'reason': 'PDF not found'})
            continue
        
        # Check attendance for this date
        cursor.execute("""
            SELECT reason FROM attendance 
            WHERE date = ?
        """, (date_str,))
        
        attendance = cursor.fetchone()
        
        if attendance and attendance[0] in ['Day Off', 'Holiday', 'Sick', 'Annual Leave']:
            print(f"\n⏭️  Skipping {pdf_file.name} - {attendance[0]}")
            skipped_days.append({'date': date_str, 'reason': attendance[0]})
            continue
        
        count, new_jobs = reimport_runsheet(str(pdf_file), replace_existing, preview_only)
        total_jobs += count
        all_new_jobs.extend(new_jobs)
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Files found: {len(files)}")
    print(f"Files processed: {len(files) - len(skipped_days)}")
    print(f"Files skipped: {len(skipped_days)}")
    print(f"Total jobs updated/added: {total_jobs}")
    
    if skipped_days:
        print(f"\nSkipped days:")
        for skip in skipped_days:
            print(f"  - {skip['date']}: {skip['reason']}")
    
    if all_new_jobs:
        print(f"\n⚠️  WARNING: {len(all_new_jobs)} NEW jobs found that were previously missed!")
        print(f"These jobs will be ADDED to the database if you run with --confirm")
        print(f"\nNew jobs:")
        for nj in all_new_jobs[:10]:  # Show first 10
            print(f"  - Job #{nj['job_number']} ({nj['date']}): {nj['customer']}")
        if len(all_new_jobs) > 10:
            print(f"  ... and {len(all_new_jobs) - 10} more")
    
    print(f"{'='*80}\n")
    
    if preview_only:
        print("ℹ️  This was a PREVIEW. No changes were made to the database.")
        print("   Run with --confirm to actually make these changes.\n")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Re-import runsheets using Camelot')
    parser.add_argument('--year', default='2025', help='Year (default: 2025)')
    parser.add_argument('--month', default='12', help='Month (default: 12)')
    parser.add_argument('--replace', action='store_true', help='Replace existing jobs (default: skip)')
    parser.add_argument('--confirm', action='store_true', help='Actually make changes (default: preview only)')
    parser.add_argument('--file', help='Re-import a single file')
    
    args = parser.parse_args()
    
    preview_only = not args.confirm
    
    if args.file:
        # Single file
        count, new_jobs = reimport_runsheet(args.file, args.replace, preview_only)
        if new_jobs and preview_only:
            print(f"\n⚠️  Found {len(new_jobs)} new jobs. Run with --confirm to add them.")
    else:
        # Whole month
        reimport_month(args.year, args.month, args.replace, preview_only)


if __name__ == '__main__':
    main()
