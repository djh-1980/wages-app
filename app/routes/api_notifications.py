"""
Notifications API routes blueprint.
Handles notification endpoints that were missing from the refactored structure.
"""

from flask import Blueprint, jsonify, request
from pathlib import Path
import json

notifications_bp = Blueprint('notifications_api', __name__, url_prefix='/api/notifications')


@notifications_bp.route('/runsheets')
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


@notifications_bp.route('/runsheets/mark-read', methods=['POST'])
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
