"""
Sync API routes - Handle synchronization between different data sources.
"""

from flask import Blueprint, jsonify, request
from ..services.runsheet_sync_service import RunsheetSyncService
import subprocess
import sys
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta
from app.config import Config

sync_bp = Blueprint('sync_api', __name__, url_prefix='/api/sync')

@sync_bp.route('/missing-runsheets', methods=['GET'])
def get_missing_runsheets():
    """Get list of missing runsheet dates in the last 30 days."""
    try:
        db_path = Path(Config.DATABASE_PATH)
        if not db_path.exists():
            return jsonify({'error': 'Database not found'}), 500
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Get all dates that have run sheet jobs
        cursor.execute("""
            SELECT DISTINCT date 
            FROM run_sheet_jobs 
            WHERE date IS NOT NULL 
            AND date != ''
        """)
        
        existing_dates = {row[0] for row in cursor.fetchall()}
        
        # Get all dates with attendance records (days off)
        cursor.execute("""
            SELECT DISTINCT date 
            FROM attendance 
            WHERE date IS NOT NULL 
            AND date != ''
        """)
        
        attendance_dates = {row[0] for row in cursor.fetchall()}
        
        conn.close()
        
        # Generate all dates in the last 30 days + tomorrow (including all 7 days)
        end_date = datetime.now() + timedelta(days=1)  # Include tomorrow
        start_date = end_date - timedelta(days=30)
        
        expected_dates = []
        current_date = start_date
        
        while current_date <= end_date:
            # Include all days (user works 7 days a week)
            date_str = current_date.strftime('%d/%m/%Y')
            # Only add if not in attendance (day off)
            if date_str not in attendance_dates:
                expected_dates.append({
                    'date': date_str,
                    'missing': date_str not in existing_dates
                })
            current_date += timedelta(days=1)
        
        # Filter to only missing dates
        missing_dates = [d['date'] for d in expected_dates if d['missing']]
        
        return jsonify({
            'success': True,
            'missing_count': len(missing_dates),
            'missing_dates': missing_dates
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@sync_bp.route('/payslip-to-runsheets', methods=['POST'])
def api_sync_payslip_to_runsheets():
    """Manually trigger sync of payslip data to runsheets."""
    try:
        result = RunsheetSyncService.sync_payslip_data_to_runsheets()
        
        if result['success']:
            # Get updated statistics
            stats = RunsheetSyncService.get_sync_statistics()
            
            return jsonify({
                'success': True,
                'message': 'Payslip data synced to runsheets successfully',
                'pay_updated': result['pay_updated'],
                'address_updated': result['address_updated'],
                'statistics': stats
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'pay_updated': 0,
                'address_updated': 0
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'pay_updated': 0,
            'address_updated': 0
        }), 500


@sync_bp.route('/statistics', methods=['GET'])
def api_sync_statistics():
    """Get current synchronization statistics."""
    try:
        stats = RunsheetSyncService.get_sync_statistics()
        
        if stats:
            return jsonify({
                'success': True,
                'statistics': stats
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Could not retrieve statistics'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
