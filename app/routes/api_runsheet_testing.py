"""
API routes for runsheet extraction testing and comparison.
Allows testing different extraction methods and comparing results.
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
import sys
import sqlite3
import re
import os

# Add testing directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts' / 'testing'))

from camelot_runsheet_parser import CamelotRunsheetParser

DB_PATH = "data/database/payslips.db"

runsheet_testing_bp = Blueprint('runsheet_testing', __name__, url_prefix='/api/runsheet-testing')


@runsheet_testing_bp.route('/available-files', methods=['GET'])
def get_available_files():
    """Get list of available runsheet files for testing."""
    try:
        runsheets_dir = Path('data/documents/runsheets')
        
        # Get filter parameters
        filter_year = request.args.get('year', '2025')
        filter_month = request.args.get('month', '12')
        
        files = []
        
        # Get all PDF files recursively
        for pdf_file in runsheets_dir.rglob('*.pdf'):
            # Only show Daniel Hanson runsheets (DH_ prefix)
            if pdf_file.name.startswith('DH_'):
                relative_path = pdf_file.relative_to(runsheets_dir)
                
                # Extract date from filename if possible
                import re
                date_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', pdf_file.name)
                date_str = None
                if date_match:
                    day = date_match.group(1)
                    month = date_match.group(2)
                    year = date_match.group(3)
                    
                    # Filter by year and month
                    if year != filter_year or month != filter_month:
                        continue
                    
                    date_str = f"{day}/{month}/{year}"
                
                files.append({
                    'filename': pdf_file.name,
                    'path': str(pdf_file),
                    'relative_path': str(relative_path),
                    'date': date_str,
                    'date_obj': pdf_file.stat().st_mtime,  # For sorting
                    'size': pdf_file.stat().st_size
                })
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x['date_obj'], reverse=True)
        
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@runsheet_testing_bp.route('/extract-camelot', methods=['POST'])
def extract_with_camelot():
    """Extract jobs using Camelot table-based method."""
    try:
        data = request.json
        pdf_path = data.get('pdf_path')
        
        if not pdf_path:
            return jsonify({'error': 'pdf_path is required'}), 400
        
        # Parse with Camelot
        parser = CamelotRunsheetParser()
        jobs = parser.parse_pdf(pdf_path)
        
        # Calculate quality scores
        for job in jobs:
            job['quality_score'] = parser.calculate_quality_score(job)
        
        # Calculate statistics
        scores = [job['quality_score'] for job in jobs]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        stats = {
            'total_jobs': len(jobs),
            'avg_quality': round(avg_score, 1),
            'high_quality': sum(1 for s in scores if s >= 80),
            'medium_quality': sum(1 for s in scores if 50 <= s < 80),
            'low_quality': sum(1 for s in scores if s < 50)
        }
        
        return jsonify({
            'success': True,
            'method': 'camelot',
            'jobs': jobs,
            'stats': stats
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@runsheet_testing_bp.route('/extract-text', methods=['POST'])
def extract_with_text():
    """Extract jobs using current text-based method."""
    try:
        data = request.json
        pdf_path = data.get('pdf_path')
        
        if not pdf_path:
            return jsonify({'error': 'pdf_path is required'}), 400
        
        # Import the current text parser
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts' / 'production'))
        from import_run_sheets import RunSheetImporter
        
        # Parse with text method
        importer = RunSheetImporter(db_path=':memory:')  # Use in-memory DB for testing
        jobs = importer.parse_pdf_run_sheet(pdf_path)
        
        # Calculate quality scores
        def calc_quality(job):
            score = 0
            if job.get('job_number'): score += 20
            if job.get('customer') and len(job.get('customer', '')) > 3: score += 20
            if job.get('activity'): score += 15
            if job.get('job_address') and len(job.get('job_address', '')) > 10: score += 20
            if job.get('postcode'): score += 15
            return min(score, 100)
        
        for job in jobs:
            job['quality_score'] = calc_quality(job)
        
        # Calculate statistics
        scores = [job['quality_score'] for job in jobs]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        stats = {
            'total_jobs': len(jobs),
            'avg_quality': round(avg_score, 1),
            'high_quality': sum(1 for s in scores if s >= 80),
            'medium_quality': sum(1 for s in scores if 50 <= s < 80),
            'low_quality': sum(1 for s in scores if s < 50)
        }
        
        return jsonify({
            'success': True,
            'method': 'text',
            'jobs': jobs,
            'stats': stats
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@runsheet_testing_bp.route('/compare', methods=['POST'])
def compare_methods():
    """Compare Camelot extraction with existing database data."""
    try:
        data = request.json
        pdf_path = data.get('pdf_path')
        
        if not pdf_path:
            return jsonify({'error': 'pdf_path is required'}), 400
        
        # Extract with Camelot
        camelot_result = extract_with_camelot_internal(pdf_path)
        
        # Get existing jobs from database for the same date
        # Extract date from first job or filename
        import re
        from ..database import execute_query
        
        date_match = re.search(r'(\d{2})-(\d{2})-(\d{4})', pdf_path)
        if date_match:
            db_date = f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}"
            
            # Query database for jobs on this date
            query = """
                SELECT job_number, customer, activity, job_address, postcode, source_file
                FROM run_sheet_jobs
                WHERE date = ?
                ORDER BY job_number
            """
            db_rows = execute_query(query, (db_date,), fetch_all=True)
            
            # Extract filename from pdf_path for comparison
            import os
            current_filename = os.path.basename(pdf_path)
            
            db_jobs = []
            for row in db_rows:
                source_file = row[5] if row[5] else ''
                # Check if this job is from the current runsheet or manually added
                is_manual = source_file != current_filename
                
                db_jobs.append({
                    'job_number': row[0],
                    'customer': row[1],
                    'activity': row[2],
                    'job_address': row[3],
                    'postcode': row[4],
                    'quality_score': 0,
                    'is_manual': is_manual,
                    'source_file': source_file
                })
        else:
            db_jobs = []
        
        # Find matching jobs
        matches = []
        camelot_jobs = {j['job_number']: j for j in camelot_result['jobs']}
        db_jobs_dict = {j['job_number']: j for j in db_jobs}
        
        all_job_numbers = set(camelot_jobs.keys()) | set(db_jobs_dict.keys())
        
        for job_num in sorted(all_job_numbers):
            db_job = db_jobs_dict.get(job_num)
            is_manual_entry = db_job and db_job.get('is_manual', False)
            
            matches.append({
                'job_number': job_num,
                'camelot': camelot_jobs.get(job_num),
                'database': db_job,
                'in_both': job_num in camelot_jobs and job_num in db_jobs_dict,
                'camelot_only': job_num in camelot_jobs and job_num not in db_jobs_dict,
                'database_only': job_num in db_jobs_dict and job_num not in camelot_jobs,
                'is_manual_entry': is_manual_entry
            })
        
        # Calculate database stats
        db_stats = {
            'total_jobs': len(db_jobs),
            'avg_quality': 0,
            'high_quality': 0,
            'medium_quality': 0,
            'low_quality': 0
        }
        
        return jsonify({
            'success': True,
            'camelot_stats': camelot_result['stats'],
            'database_stats': db_stats,
            'matches': matches,
            'summary': {
                'total_unique_jobs': len(all_job_numbers),
                'in_both': sum(1 for m in matches if m['in_both']),
                'camelot_only': sum(1 for m in matches if m['camelot_only']),
                'database_only': sum(1 for m in matches if m['database_only'])
            }
        })
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


def extract_with_camelot_internal(pdf_path):
    """Internal helper for Camelot extraction."""
    parser = CamelotRunsheetParser()
    jobs = parser.parse_pdf(pdf_path)
    
    for job in jobs:
        job['quality_score'] = parser.calculate_quality_score(job)
    
    scores = [job['quality_score'] for job in jobs]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    return {
        'jobs': jobs,
        'stats': {
            'total_jobs': len(jobs),
            'avg_quality': round(avg_score, 1),
            'high_quality': sum(1 for s in scores if s >= 80),
            'medium_quality': sum(1 for s in scores if 50 <= s < 80),
            'low_quality': sum(1 for s in scores if s < 50)
        }
    }


def extract_with_text_internal(pdf_path):
    """Internal helper for text extraction."""
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts' / 'production'))
    from import_run_sheets import RunSheetImporter
    
    importer = RunSheetImporter(db_path=':memory:')
    jobs = importer.parse_pdf_run_sheet(pdf_path)
    
    def calc_quality(job):
        score = 0
        if job.get('job_number'): score += 20
        if job.get('customer') and len(job.get('customer', '')) > 3: score += 20
        if job.get('activity'): score += 15
        if job.get('job_address') and len(job.get('job_address', '')) > 10: score += 20
        if job.get('postcode'): score += 15
        return min(score, 100)
    
    for job in jobs:
        job['quality_score'] = calc_quality(job)
    
    scores = [job['quality_score'] for job in jobs]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    return {
        'jobs': jobs,
        'stats': {
            'total_jobs': len(jobs),
            'avg_quality': round(avg_score, 1),
            'high_quality': sum(1 for s in scores if s >= 80),
            'medium_quality': sum(1 for s in scores if 50 <= s < 80),
            'low_quality': sum(1 for s in scores if s < 50)
        }
    }
