"""
Search API routes blueprint.
Extracted from web_app.py to improve code organization.
"""

from flask import Blueprint, jsonify, request
from ..database import get_db_connection

search_bp = Blueprint('search_api', __name__, url_prefix='/api')


@search_bp.route('/search')
def api_search():
    """Search jobs."""
    try:
        query = request.args.get('q', '')
        
        if not query:
            return jsonify([])
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    p.tax_year,
                    p.week_number,
                    ji.job_number,
                    ji.client,
                    ji.location,
                    ji.job_type,
                    ji.amount,
                    ji.date,
                    ji.postcode
                FROM job_items ji
                JOIN payslips p ON ji.payslip_id = p.id
                WHERE ji.client LIKE ? OR ji.location LIKE ? OR ji.job_type LIKE ? OR ji.job_number LIKE ?
                ORDER BY p.tax_year DESC, p.week_number DESC
                LIMIT 50
            """, (f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%'))
            
            rows = [dict(row) for row in cursor.fetchall()]
            return jsonify(rows)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@search_bp.route('/search/job/<job_number>')
def api_search_job(job_number):
    """Search for a job number across run sheets and payslips."""
    try:
        results = {
            'found': False,
            'job_number': job_number,
            'runsheets': [],
            'payslips': []
        }
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Search in run sheets
            cursor.execute("""
                SELECT date, customer, job_address, job_number, activity
                FROM run_sheet_jobs
                WHERE job_number = ? OR job_number LIKE ? OR CAST(job_number AS TEXT) = ?
                ORDER BY date DESC
            """, (job_number, f'%{job_number}%', job_number))
            
            runsheets = cursor.fetchall()
            if runsheets:
                results['found'] = True
                results['runsheets'] = [
                    {
                        'date': row[0],
                        'customer': row[1],
                        'address': row[2],
                        'job_number': row[3],
                        'status': row[4]  # activity
                    }
                    for row in runsheets
                ]
            
            # Search in payslip jobs
            cursor.execute("""
                SELECT ji.job_number, ji.client, ji.location, ji.job_type, ji.amount, 
                       ji.date, ji.postcode, p.tax_year, p.week_number
                FROM job_items ji
                JOIN payslips p ON ji.payslip_id = p.id
                WHERE ji.job_number = ? OR ji.job_number LIKE ? OR CAST(ji.job_number AS TEXT) = ?
                ORDER BY p.tax_year DESC, p.week_number DESC
            """, (job_number, f'%{job_number}%', job_number))
            
            payslips = cursor.fetchall()
            if payslips:
                results['found'] = True
                results['payslips'] = [
                    {
                        'job_number': row[0],
                        'client': row[1],
                        'location': row[2],
                        'job_type': row[3],
                        'amount': row[4],
                        'date': row[5],
                        'postcode': row[6],
                        'tax_year': row[7],
                        'week_number': row[8],
                        'description': f"{row[1]} | {row[2]} | {row[3]} | £{row[4]} | {row[5]}"  # Clean description
                    }
                    for row in payslips
                ]
            
            return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e), 'found': False}), 500
