"""
Re-import API endpoint for runsheet testing.
Separated to avoid file editing conflicts.
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
import sys
import sqlite3
import re

# Add testing directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts' / 'testing'))

from camelot_runsheet_parser import CamelotRunsheetParser

DB_PATH = "data/database/payslips.db"

reimport_bp = Blueprint('runsheet_reimport', __name__, url_prefix='/api/runsheet-testing')


@reimport_bp.route('/reimport', methods=['POST'])
def reimport_month():
    """Re-import a month of runsheets using Camelot."""
    try:
        data = request.json
        year = data.get('year', '2025')
        month = data.get('month', '12')
        
        runsheets_dir = Path('data/documents/runsheets')
        pattern = f"DH_*-{month}-{year}.pdf"
        files = list(runsheets_dir.rglob(pattern))
        
        if not files:
            return jsonify({'error': f'No runsheets found for {month}/{year}'}), 404
        
        # Connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        total_updated = 0
        total_added = 0
        total_skipped = 0
        skipped_days = []
        files_processed = 0
        
        parser = CamelotRunsheetParser(driver_name="Daniel Hanson")
        
        for pdf_file in sorted(files):
            # Extract date from filename
            date_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', pdf_file.name)
            if not date_match:
                continue
            
            date_str = f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}"
            
            # Check attendance
            cursor.execute("""
                SELECT reason FROM attendance 
                WHERE date = ?
            """, (date_str,))
            
            attendance = cursor.fetchone()
            if attendance and attendance[0] in ['Day Off', 'Holiday', 'Sick', 'Annual Leave']:
                skipped_days.append({'date': date_str, 'reason': attendance[0]})
                continue
            
            # Parse with Camelot
            jobs = parser.parse_pdf(str(pdf_file))
            
            if not jobs:
                continue
            
            files_processed += 1
            current_filename = pdf_file.name
            
            for job in jobs:
                job_number = job.get('job_number')
                date = job.get('date')
                customer = job.get('customer', '')
                
                if not job_number or not date:
                    continue
                
                # Skip PP Audit jobs
                if 'PP Audit' in customer:
                    continue
                
                # Check if job exists
                cursor.execute("""
                    SELECT id FROM run_sheet_jobs 
                    WHERE date = ? AND job_number = ?
                """, (date, job_number))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing job
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
                        current_filename,
                        existing[0]
                    ))
                    total_updated += 1
                else:
                    # Insert new job
                    cursor.execute("""
                        INSERT INTO run_sheet_jobs (
                            date, driver, job_number, customer, activity,
                            job_address, postcode, source_file, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                    """, (
                        date,
                        'Daniel Hanson',
                        job_number,
                        job.get('customer'),
                        job.get('activity'),
                        job.get('job_address'),
                        job.get('postcode'),
                        current_filename
                    ))
                    total_added += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'files_processed': files_processed,
            'jobs_updated': total_updated,
            'jobs_added': total_added,
            'jobs_skipped': total_skipped,
            'skipped_days': skipped_days
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
