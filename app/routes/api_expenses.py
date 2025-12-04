"""
Expense API routes blueprint for HMRC MTD compliance.
"""

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename
from ..models.expense import ExpenseModel
from datetime import datetime
from pathlib import Path
import os

expenses_bp = Blueprint('expenses_api', __name__, url_prefix='/api/expenses')

# Configure upload settings
RECEIPT_FOLDER = 'data/receipts'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@expenses_bp.route('/categories')
def api_get_categories():
    """Get all expense categories."""
    try:
        categories = ExpenseModel.get_categories()
        return jsonify({'categories': categories})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@expenses_bp.route('/add', methods=['POST'])
def api_add_expense():
    """Add a new expense."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        required_fields = ['date', 'category_id', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
        
        expense_id = ExpenseModel.add_expense(
            date=data['date'],
            category_id=data['category_id'],
            amount=float(data['amount']),
            description=data.get('description'),
            vat_amount=float(data.get('vat_amount', 0)),
            receipt_file=data.get('receipt_file'),
            is_recurring=data.get('is_recurring', False),
            recurring_frequency=data.get('recurring_frequency')
        )
        
        return jsonify({'success': True, 'expense_id': expense_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@expenses_bp.route('/list')
def api_get_expenses():
    """Get expenses with optional filters."""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        category_id = request.args.get('category_id', type=int)
        tax_year = request.args.get('tax_year')
        
        expenses = ExpenseModel.get_expenses(
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            tax_year=tax_year
        )
        
        return jsonify({'expenses': expenses, 'count': len(expenses)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@expenses_bp.route('/<int:expense_id>')
def api_get_expense(expense_id):
    """Get a single expense by ID."""
    try:
        expense = ExpenseModel.get_expense_by_id(expense_id)
        
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
        
        return jsonify({'expense': expense})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@expenses_bp.route('/update/<int:expense_id>', methods=['PUT'])
def api_update_expense(expense_id):
    """Update an existing expense."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        success = ExpenseModel.update_expense(
            expense_id=expense_id,
            date=data.get('date'),
            category_id=data.get('category_id'),
            description=data.get('description'),
            amount=float(data['amount']) if 'amount' in data else None,
            vat_amount=float(data['vat_amount']) if 'vat_amount' in data else None,
            receipt_file=data.get('receipt_file')
        )
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Expense not found or no changes made'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@expenses_bp.route('/delete/<int:expense_id>', methods=['DELETE'])
def api_delete_expense(expense_id):
    """Delete an expense."""
    try:
        success = ExpenseModel.delete_expense(expense_id)
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Expense not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@expenses_bp.route('/summary')
def api_get_summary():
    """Get expense summary grouped by HMRC category."""
    try:
        tax_year = request.args.get('tax_year')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        summary = ExpenseModel.get_summary(
            tax_year=tax_year,
            start_date=start_date,
            end_date=end_date
        )
        
        total_expenses = sum(item['total_amount'] for item in summary)
        
        return jsonify({
            'summary': summary,
            'total_expenses': round(total_expenses, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@expenses_bp.route('/recurring')
def api_get_recurring():
    """Get all recurring expenses."""
    try:
        recurring = ExpenseModel.get_recurring_expenses()
        return jsonify({'recurring_expenses': recurring})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@expenses_bp.route('/tax-years')
def api_get_tax_years():
    """Get list of tax years with expenses."""
    try:
        tax_years = ExpenseModel.get_tax_years()
        
        # Add current tax year if not in list
        now = datetime.now()
        if now.month >= 4 and now.day >= 6:
            current_tax_year = f"{now.year}/{now.year + 1}"
        else:
            current_tax_year = f"{now.year - 1}/{now.year}"
        
        if current_tax_year not in tax_years:
            tax_years.insert(0, current_tax_year)
        
        return jsonify({'tax_years': tax_years})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@expenses_bp.route('/mtd-export')
def api_mtd_export():
    """Get MTD-formatted export for a tax year."""
    try:
        tax_year = request.args.get('tax_year')
        
        if not tax_year:
            # Use current tax year
            now = datetime.now()
            if now.month >= 4 and now.day >= 6:
                tax_year = f"{now.year}/{now.year + 1}"
            else:
                tax_year = f"{now.year - 1}/{now.year}"
        
        export_data = ExpenseModel.get_mtd_export(tax_year)
        
        return jsonify(export_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@expenses_bp.route('/upload-receipt', methods=['POST'])
def api_upload_receipt():
    """Upload a receipt file."""
    try:
        if 'receipt' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['receipt']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Allowed: PDF, JPG, PNG'}), 400
        
        # Get expense details from form data
        date = request.form.get('date', '')
        category = request.form.get('category', 'expense')
        amount = request.form.get('amount', '0')
        
        # Parse date to get tax year and month
        try:
            expense_date = datetime.strptime(date, '%d/%m/%Y')
            if expense_date.month >= 4 and expense_date.day >= 6:
                tax_year = f"{expense_date.year}-{expense_date.year + 1}"
            else:
                tax_year = f"{expense_date.year - 1}-{expense_date.year}"
            
            month_folder = f"{expense_date.month:02d}-{expense_date.strftime('%B')}"
        except:
            tax_year = "unknown"
            month_folder = "unknown"
        
        # Create directory structure: data/receipts/2024-25/12-December/
        receipt_dir = Path(RECEIPT_FOLDER) / tax_year / month_folder
        receipt_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename: DD-MM-YYYY_category_amount.ext
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        safe_category = secure_filename(category.replace(' ', '_'))
        filename = f"{date.replace('/', '-')}_{safe_category}_{amount}.{file_ext}"
        
        # Save file
        filepath = receipt_dir / filename
        file.save(str(filepath))
        
        # Return relative path for database storage
        relative_path = str(filepath.relative_to(Path('.')))
        
        return jsonify({
            'success': True,
            'filepath': relative_path,
            'filename': filename
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@expenses_bp.route('/receipt/<path:filepath>')
def api_view_receipt(filepath):
    """View a receipt file."""
    try:
        full_path = Path(filepath)
        
        if not full_path.exists():
            return jsonify({'error': 'Receipt not found'}), 404
        
        return send_file(str(full_path))
    except Exception as e:
        return jsonify({'error': str(e)}), 500
