"""
API routes for job notes/comments functionality.
"""

from flask import Blueprint, jsonify, request
from ..database import get_db_connection
from ..utils.logging_utils import log_settings_action
import sqlite3

job_notes_bp = Blueprint('job_notes_api', __name__, url_prefix='/api/jobs')


@job_notes_bp.route('/<int:job_id>/notes', methods=['GET'])
def get_job_notes(job_id):
    """Get notes for a specific job."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT notes FROM run_sheet_jobs WHERE id = ?
            """, (job_id,))
            
            result = cursor.fetchone()
            
            if result:
                return jsonify({
                    'success': True,
                    'notes': result[0] or ''
                })
            else:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@job_notes_bp.route('/<int:job_id>/notes', methods=['POST', 'PUT'])
def update_job_notes(job_id):
    """Update notes for a specific job."""
    try:
        data = request.get_json()
        notes = data.get('notes', '')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Check if job exists
            cursor.execute("SELECT job_number, date FROM run_sheet_jobs WHERE id = ?", (job_id,))
            job = cursor.fetchone()
            
            if not job:
                return jsonify({'success': False, 'error': 'Job not found'}), 404
            
            # Update notes
            cursor.execute("""
                UPDATE run_sheet_jobs 
                SET notes = ?
                WHERE id = ?
            """, (notes, job_id))
            
            conn.commit()
            
            log_settings_action('JOB_NOTES', f'Updated notes for job {job[0]} on {job[1]}')
            
            return jsonify({
                'success': True,
                'message': 'Notes updated successfully'
            })
        
    except Exception as e:
        log_settings_action('JOB_NOTES', f'Error updating notes: {str(e)}', 'ERROR')
        return jsonify({'success': False, 'error': str(e)}), 500
