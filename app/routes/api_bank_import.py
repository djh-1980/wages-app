"""
Bank Statement Import API routes
"""

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename
from ..models.bank_statement import BankStatementParser
from ..models.expense import ExpenseModel

bank_import_bp = Blueprint('bank_import_api', __name__, url_prefix='/api/bank-import')


@bank_import_bp.route('/parse', methods=['POST'])
def api_parse_statement():
    """Parse uploaded bank statement CSV."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Only CSV files are supported'}), 400
        
        # Read file content
        content = file.read().decode('utf-8')
        
        # Parse transactions
        transactions = BankStatementParser.parse_rbs_csv(content)
        
        # Get summary
        summary = BankStatementParser.get_summary(transactions)
        
        return jsonify({
            'success': True,
            'transactions': transactions,
            'summary': summary
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bank_import_bp.route('/import', methods=['POST'])
def api_import_transactions():
    """Import selected transactions as expenses."""
    try:
        data = request.get_json()
        
        if not data or 'transactions' not in data:
            return jsonify({'success': False, 'error': 'No transactions provided'}), 400
        
        transactions = data['transactions']
        imported_count = 0
        errors = []
        
        # Get category mapping (name to ID)
        categories = ExpenseModel.get_categories()
        category_map = {cat['name']: cat['id'] for cat in categories}
        
        for trans in transactions:
            try:
                # Only import if selected
                if not trans.get('selected', False):
                    continue
                
                # Get category ID
                category_name = trans.get('category')
                if not category_name or category_name not in category_map:
                    errors.append(f"Unknown category for: {trans['description']}")
                    continue
                
                category_id = category_map[category_name]
                
                # Add expense
                ExpenseModel.add_expense(
                    date=trans['date'],
                    category_id=category_id,
                    amount=trans['amount'],
                    description=trans['description'],
                    vat_amount=0,
                    receipt_file=None,
                    is_recurring=False,
                    recurring_frequency=None
                )
                
                imported_count += 1
            
            except Exception as e:
                errors.append(f"Error importing {trans['description']}: {str(e)}")
        
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'errors': errors
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
