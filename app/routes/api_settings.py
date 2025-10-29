"""
Settings API routes blueprint.
Extracted from web_app.py to improve code organization.
"""

from flask import Blueprint, jsonify, request
from ..models.settings import SettingsModel
from ..models.attendance import AttendanceModel
from ..utils.logging_utils import log_settings_action
from pathlib import Path
import json
import os

settings_bp = Blueprint('settings_api', __name__, url_prefix='/api/settings')


@settings_bp.route('/groups', methods=['GET', 'POST'])
def api_settings_groups():
    """Manage client and job type groupings."""
    try:
        if request.method == 'POST':
            # Save groupings
            data = request.json
            SettingsModel.save_groupings(data)
            return jsonify({'success': True})
        else:
            # Get groupings
            groupings = SettingsModel.get_groupings()
            return jsonify(groupings)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/test-gmail')
def api_test_gmail():
    """Test Gmail OAuth connection."""
    try:
        token_path = Path('token.json')
        creds_path = Path('credentials.json')
        
        result = {
            'token_exists': token_path.exists(),
            'credentials_exists': creds_path.exists(),
            'connected': False,
            'message': ''
        }
        
        if not creds_path.exists():
            result['message'] = 'credentials.json not found. Please set up Gmail OAuth first.'
            return jsonify(result)
        
        if not token_path.exists():
            result['message'] = 'token.json not found. Please authorize Gmail access first.'
            return jsonify(result)
        
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            
            creds = Credentials.from_authorized_user_file('token.json')
            
            if creds and creds.valid:
                result['connected'] = True
                result['message'] = 'Gmail connection successful! OAuth token is valid.'
            elif creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                result['connected'] = True
                result['message'] = 'Gmail connection successful! Token was refreshed.'
            else:
                result['message'] = 'OAuth token is invalid. Please re-authorize.'
        except Exception as e:
            result['message'] = f'Error testing connection: {str(e)}'
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/sync-status')
def api_sync_status():
    """Get auto-sync status."""
    try:
        from datetime import datetime
        
        log_path = Path('logs/runsheet_sync.log')
        
        result = {
            'active': False,
            'last_sync': None,
            'log_exists': log_path.exists()
        }
        
        if log_path.exists():
            result['active'] = True
            # Get last modified time of log
            mtime = os.path.getmtime(log_path)
            result['last_sync'] = datetime.fromtimestamp(mtime).isoformat()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/logs', methods=['GET'])
def api_get_settings_logs():
    """Get recent settings logs."""
    try:
        log_file = Path('logs/settings.log')
        if not log_file.exists():
            return jsonify({
                'success': True,
                'logs': [],
                'message': 'No logs yet'
            })
        
        # Read last 100 lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines
        
        return jsonify({
            'success': True,
            'logs': recent_lines,
            'total_lines': len(lines)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Attendance API endpoints
@settings_bp.route('/attendance', methods=['GET'])
def api_get_attendance():
    """Get all attendance records with optional date range filtering."""
    try:
        year = request.args.get('year', '')
        from_date = request.args.get('from_date', '')
        to_date = request.args.get('to_date', '')
        
        records = AttendanceModel.get_all_records(
            year=year, 
            from_date=from_date, 
            to_date=to_date
        )
        return jsonify(records)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/attendance', methods=['POST'])
def api_add_attendance():
    """Add attendance record."""
    try:
        data = request.json
        date = data.get('date')
        reason = data.get('reason')
        notes = data.get('notes', '')
        
        record_id = AttendanceModel.add_record(date, reason, notes)
        return jsonify({'success': True, 'id': record_id})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/attendance/<int:record_id>', methods=['DELETE'])
def api_delete_attendance(record_id):
    """Delete attendance record."""
    try:
        success = AttendanceModel.delete_record(record_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Record not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Notification endpoints
@settings_bp.route('/notifications/runsheets')
def get_runsheet_notifications():
    """Get new run sheet notifications."""
    try:
        notification_file = Path('data/new_runsheets.json')
        
        if not notification_file.exists():
            return jsonify({'has_new': False, 'count': 0})
        
        try:
            with open(notification_file, 'r') as f:
                notification = json.load(f)
            
            return jsonify({
                'has_new': not notification.get('read', False),
                'count': notification.get('count', 0),
                'date': notification.get('date', ''),
                'timestamp': notification.get('timestamp', '')
            })
        except:
            return jsonify({'has_new': False, 'count': 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/notifications/runsheets/mark-read', methods=['POST'])
def mark_runsheet_notifications_read():
    """Mark run sheet notifications as read."""
    try:
        notification_file = Path('data/new_runsheets.json')
        
        if notification_file.exists():
            try:
                with open(notification_file, 'r') as f:
                    notification = json.load(f)
                
                notification['read'] = True
                
                with open(notification_file, 'w') as f:
                    json.dump(notification, f)
                
                return jsonify({'success': True})
            except:
                return jsonify({'success': False, 'error': 'Failed to update notification'})
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
