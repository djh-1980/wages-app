"""
Recurring Payment Template API routes
"""

from flask import Blueprint, jsonify, request
from ..models.recurring_template import RecurringTemplateModel
from ..models.expense import ExpenseModel

recurring_bp = Blueprint('recurring_api', __name__, url_prefix='/api/recurring')


@recurring_bp.route('/templates')
def api_get_templates():
    """Get all recurring templates."""
    try:
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        templates = RecurringTemplateModel.get_templates(active_only=active_only)
        return jsonify({'success': True, 'templates': templates})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@recurring_bp.route('/templates/<int:template_id>')
def api_get_template(template_id):
    """Get a single template by ID."""
    try:
        template = RecurringTemplateModel.get_template_by_id(template_id)
        if template:
            return jsonify({'success': True, 'template': template})
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@recurring_bp.route('/templates/add', methods=['POST'])
def api_add_template():
    """Create a new recurring template."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        required_fields = ['name', 'category_id', 'expected_amount', 'frequency', 'merchant_pattern']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        template_id = RecurringTemplateModel.create_template(
            name=data['name'],
            category_id=data['category_id'],
            expected_amount=float(data['expected_amount']),
            frequency=data['frequency'],
            merchant_pattern=data['merchant_pattern'],
            day_of_month=data.get('day_of_month'),
            is_active=data.get('is_active', True),
            tolerance_amount=float(data.get('tolerance_amount', 5.0)),
            auto_import=data.get('auto_import', False)
        )
        
        return jsonify({'success': True, 'template_id': template_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@recurring_bp.route('/templates/update/<int:template_id>', methods=['PUT'])
def api_update_template(template_id):
    """Update a recurring template."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Convert numeric fields
        if 'expected_amount' in data:
            data['expected_amount'] = float(data['expected_amount'])
        if 'tolerance_amount' in data:
            data['tolerance_amount'] = float(data['tolerance_amount'])
        if 'category_id' in data:
            data['category_id'] = int(data['category_id'])
        
        success = RecurringTemplateModel.update_template(template_id, **data)
        
        if success:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@recurring_bp.route('/templates/delete/<int:template_id>', methods=['DELETE'])
def api_delete_template(template_id):
    """Delete a recurring template."""
    try:
        success = RecurringTemplateModel.delete_template(template_id)
        
        if success:
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@recurring_bp.route('/templates/due')
def api_get_due_templates():
    """Get templates that are due for payment."""
    try:
        due_templates = RecurringTemplateModel.get_due_templates()
        return jsonify({'success': True, 'due_templates': due_templates})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@recurring_bp.route('/templates/statistics')
def api_get_statistics():
    """Get recurring template statistics."""
    try:
        stats = RecurringTemplateModel.get_statistics()
        return jsonify({'success': True, 'statistics': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@recurring_bp.route('/match-transaction', methods=['POST'])
def api_match_transaction():
    """
    Try to match a transaction to a recurring template.
    
    Request body:
    {
        "description": "SANTANDER VAN FINANCE",
        "amount": 299.99,
        "date": "15/12/2024"
    }
    """
    try:
        data = request.get_json()
        
        if not data or not all(k in data for k in ['description', 'amount', 'date']):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        template_id, confidence = RecurringTemplateModel.match_transaction(
            data['description'],
            float(data['amount']),
            data['date']
        )
        
        if template_id:
            template = RecurringTemplateModel.get_template_by_id(template_id)
            return jsonify({
                'success': True,
                'matched': True,
                'template': template,
                'confidence': confidence
            })
        
        return jsonify({
            'success': True,
            'matched': False,
            'confidence': 0
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@recurring_bp.route('/create-from-template', methods=['POST'])
def api_create_from_template():
    """
    Create an expense from a recurring template.
    
    Request body:
    {
        "template_id": 1,
        "date": "15/12/2024",
        "amount": 299.99,  # Optional, uses template amount if not provided
        "description": "Optional override description"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'template_id' not in data or 'date' not in data:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        template = RecurringTemplateModel.get_template_by_id(data['template_id'])
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        # Create expense
        amount = float(data.get('amount', template['expected_amount']))
        description = data.get('description', f"{template['name']} - Recurring payment")
        
        expense_id = ExpenseModel.add_expense(
            date=data['date'],
            category_id=template['category_id'],
            amount=amount,
            description=description,
            vat_amount=0,
            receipt_file=None,
            is_recurring=True,
            recurring_frequency=template['frequency']
        )
        
        # Update template's last matched date
        RecurringTemplateModel.update_last_matched(data['template_id'], data['date'])
        
        return jsonify({
            'success': True,
            'expense_id': expense_id,
            'message': f'Created expense from template: {template["name"]}'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
