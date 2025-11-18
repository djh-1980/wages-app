"""
Verbal Pay Confirmation API routes.
Handles verbal pay amount confirmations from boss.
"""

from flask import Blueprint, jsonify, request
from ..models.verbal_pay import VerbalPayModel
from datetime import datetime
import re

verbal_pay_bp = Blueprint('verbal_pay_api', __name__, url_prefix='/api/verbal-pay')


@verbal_pay_bp.route('/confirmations', methods=['GET'])
def get_all_confirmations():
    """Get all verbal pay confirmations."""
    try:
        confirmations = VerbalPayModel.get_all_confirmations()
        return jsonify({
            'success': True,
            'confirmations': confirmations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@verbal_pay_bp.route('/confirmations', methods=['POST'])
def add_confirmation():
    """Add a new verbal pay confirmation."""
    try:
        data = request.json
        week_number = data.get('week_number')
        year = data.get('year')
        verbal_amount = data.get('verbal_amount')
        notes = data.get('notes', '')
        
        if not week_number or not year or not verbal_amount:
            return jsonify({'error': 'Week number, year, and verbal amount are required'}), 400
        
        # Validate inputs
        try:
            week_number = int(week_number)
            year = int(year)
            verbal_amount = float(verbal_amount)
        except ValueError:
            return jsonify({'error': 'Invalid number format'}), 400
        
        if week_number < 1 or week_number > 53:
            return jsonify({'error': 'Week number must be between 1 and 53'}), 400
        
        if verbal_amount <= 0:
            return jsonify({'error': 'Verbal amount must be positive'}), 400
        
        confirmation_id = VerbalPayModel.add_confirmation(week_number, year, verbal_amount, notes)
        
        return jsonify({
            'success': True,
            'message': f'Verbal confirmation saved for Week {week_number}, {year}',
            'id': confirmation_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@verbal_pay_bp.route('/confirmations/<int:confirmation_id>', methods=['DELETE'])
def delete_confirmation(confirmation_id):
    """Delete a verbal pay confirmation."""
    try:
        VerbalPayModel.delete_confirmation(confirmation_id)
        return jsonify({
            'success': True,
            'message': 'Confirmation deleted'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@verbal_pay_bp.route('/confirmations/week/<int:week_number>/year/<int:year>', methods=['GET'])
def get_confirmation_for_week(week_number, year):
    """Get verbal pay confirmation for a specific week."""
    try:
        confirmation = VerbalPayModel.get_confirmation(week_number, year)
        
        if confirmation:
            return jsonify({
                'success': True,
                'confirmation': confirmation
            })
        else:
            return jsonify({
                'success': True,
                'confirmation': None
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@verbal_pay_bp.route('/match-payslip', methods=['POST'])
def match_payslip():
    """Match a payslip with verbal confirmation."""
    try:
        data = request.json
        week_number = int(data.get('week_number'))
        year = int(data.get('year'))
        payslip_id = int(data.get('payslip_id'))
        gross_pay = float(data.get('gross_pay'))  # Verbal amount should match gross
        net_pay = float(data.get('net_pay'))
        
        matched = VerbalPayModel.match_with_payslip(week_number, year, payslip_id, gross_pay, net_pay)
        
        return jsonify({
            'success': True,
            'matched': matched,
            'message': 'Amounts match!' if matched else 'Amounts do not match!'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
