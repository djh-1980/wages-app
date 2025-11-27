"""
Mileage API routes for managing mileage entries and detecting missing data
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
import sqlite3
import os
from app.models.mileage import MileageModel

mileage_bp = Blueprint('api_mileage', __name__)

@mileage_bp.route('/entries', methods=['GET'])
def get_mileage_entries():
    """Get mileage entries with optional filtering and pagination."""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        year = request.args.get('year')
        month = request.args.get('month')
        
        entries = MileageModel.get_entries(limit=limit, offset=offset, year=year, month=month)
        
        return jsonify({
            'success': True,
            'entries': entries,
            'count': len(entries)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/entries', methods=['POST'])
def create_mileage_entry():
    """Create a new mileage entry."""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['date', 'total_miles']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create the entry
        entry_id = MileageModel.create_entry(
            date=data['date'],
            start_mileage=data.get('start_mileage', 0),
            end_mileage=data.get('end_mileage', data['total_miles']),
            total_miles=data['total_miles'],
            fuel_cost=data.get('fuel_cost', 0),
            notes=data.get('notes', '')
        )
        
        return jsonify({
            'success': True,
            'message': 'Mileage entry created successfully',
            'id': entry_id
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/entries/<int:entry_id>', methods=['GET'])
def get_mileage_entry(entry_id):
    """Get a specific mileage entry."""
    try:
        entry = MileageModel.get_entry_by_id(entry_id)
        
        if not entry:
            return jsonify({
                'success': False,
                'error': 'Mileage entry not found'
            }), 404
        
        return jsonify({
            'success': True,
            'entry': entry
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/entries/<int:entry_id>', methods=['PUT'])
def update_mileage_entry(entry_id):
    """Update a mileage entry."""
    try:
        data = request.json
        
        success = MileageModel.update_entry(
            entry_id=entry_id,
            date=data.get('date'),
            start_mileage=data.get('start_mileage'),
            end_mileage=data.get('end_mileage'),
            total_miles=data.get('total_miles'),
            fuel_cost=data.get('fuel_cost'),
            notes=data.get('notes')
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Mileage entry updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Mileage entry not found'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/entries/<int:entry_id>', methods=['DELETE'])
def delete_mileage_entry(entry_id):
    """Delete a mileage entry."""
    try:
        success = MileageModel.delete_entry(entry_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Mileage entry deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Mileage entry not found'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/missing-report', methods=['GET'])
def get_missing_mileage_report():
    """Get report of dates with missing mileage data."""
    try:
        year = request.args.get('year')
        month = request.args.get('month')
        
        missing_dates = MileageModel.get_missing_mileage_dates(year=year, month=month)
        
        return jsonify({
            'success': True,
            'missing_days': missing_dates,
            'count': len(missing_dates)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mileage_bp.route('/summary', methods=['GET'])
def get_mileage_summary():
    """Get mileage summary statistics."""
    try:
        year = request.args.get('year')
        month = request.args.get('month')
        
        summary = MileageModel.get_summary(year=year, month=month)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
