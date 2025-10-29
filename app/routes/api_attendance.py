"""
Attendance API routes blueprint.
Handles attendance tracking endpoints.
"""

from flask import Blueprint, jsonify, request
from ..models.attendance import AttendanceModel

attendance_bp = Blueprint('attendance_api', __name__, url_prefix='/api')


@attendance_bp.route('/attendance', methods=['GET'])
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


@attendance_bp.route('/attendance', methods=['POST'])
def api_add_attendance():
    """Add attendance record."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        date = data.get('date')
        reason = data.get('reason')
        notes = data.get('notes', '')
        
        record_id = AttendanceModel.add_record(date, reason, notes)
        return jsonify({'success': True, 'id': record_id})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/attendance/<int:record_id>', methods=['DELETE'])
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


@attendance_bp.route('/attendance/<int:record_id>', methods=['PUT'])
def api_update_attendance(record_id):
    """Update attendance record."""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Get fields that are provided (allow partial updates)
        date = data.get('date')
        reason = data.get('reason')
        notes = data.get('notes')
        
        success = AttendanceModel.update_record(record_id, date=date, reason=reason, notes=notes)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Record not found'}), 404
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@attendance_bp.route('/attendance/clear-all', methods=['DELETE'])
def api_clear_all_attendance():
    """Clear all attendance records."""
    try:
        count = AttendanceModel.clear_all_records()
        return jsonify({'success': True, 'deleted_count': count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
