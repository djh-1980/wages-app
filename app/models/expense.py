"""
Expense model - handles all expense-related database operations for HMRC MTD compliance.
"""

from ..database import get_db_connection, execute_query
from datetime import datetime


class ExpenseModel:
    """Model for expense data operations."""
    
    @staticmethod
    def get_categories(active_only=True):
        """Get all expense categories."""
        query = """
            SELECT id, name, hmrc_box, hmrc_box_number, description, is_active
            FROM expense_categories
        """
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY hmrc_box_number, name"
        
        rows = execute_query(query, fetch_all=True)
        return [dict(row) for row in rows]
    
    @staticmethod
    def transaction_exists(date, description, amount):
        """Check if a transaction already exists in expenses (duplicate detection)."""
        query = """
            SELECT COUNT(*) as count
            FROM expenses
            WHERE date = ? AND description = ? AND amount = ?
        """
        result = execute_query(query, (date, description, amount), fetch_one=True)
        return result['count'] > 0
    
    @staticmethod
    def add_expense(date, category_id, amount, description=None, vat_amount=0, 
                   receipt_file=None, is_recurring=False, recurring_frequency=None):
        """Add a new expense."""
        # Calculate tax year (April 6 - April 5)
        expense_date = datetime.strptime(date, '%d/%m/%Y')
        if expense_date.month >= 4 and expense_date.day >= 6:
            tax_year = f"{expense_date.year}/{expense_date.year + 1}"
        else:
            tax_year = f"{expense_date.year - 1}/{expense_date.year}"
        
        query = """
            INSERT INTO expenses 
            (date, category_id, description, amount, vat_amount, receipt_file, 
             is_recurring, recurring_frequency, tax_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (date, category_id, description, amount, vat_amount, 
                                  receipt_file, is_recurring, recurring_frequency, tax_year))
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def get_expenses(start_date=None, end_date=None, category_id=None, tax_year=None):
        """Get expenses with optional filters."""
        query = """
            SELECT 
                e.id, e.date, e.description, e.amount, e.vat_amount, 
                e.receipt_file, e.is_recurring, e.recurring_frequency, e.tax_year,
                c.name as category_name, c.hmrc_box, c.hmrc_box_number,
                e.created_at, e.updated_at
            FROM expenses e
            JOIN expense_categories c ON e.category_id = c.id
            WHERE 1=1
        """
        params = []
        
        if start_date:
            query += " AND e.date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND e.date <= ?"
            params.append(end_date)
        
        if category_id:
            query += " AND e.category_id = ?"
            params.append(category_id)
        
        if tax_year:
            query += " AND e.tax_year = ?"
            params.append(tax_year)
        
        query += " ORDER BY e.date DESC, e.created_at DESC"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_expense_by_id(expense_id):
        """Get a single expense by ID."""
        query = """
            SELECT 
                e.id, e.date, e.category_id, e.description, e.amount, e.vat_amount,
                e.receipt_file, e.is_recurring, e.recurring_frequency, e.tax_year,
                c.name as category_name, c.hmrc_box, c.hmrc_box_number
            FROM expenses e
            JOIN expense_categories c ON e.category_id = c.id
            WHERE e.id = ?
        """
        row = execute_query(query, (expense_id,), fetch_one=True)
        return dict(row) if row else None
    
    @staticmethod
    def update_expense(expense_id, date=None, category_id=None, description=None, 
                      amount=None, vat_amount=None, receipt_file=None):
        """Update an existing expense."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            updates = []
            params = []
            
            if date is not None:
                updates.append("date = ?")
                params.append(date)
                
                # Recalculate tax year
                expense_date = datetime.strptime(date, '%d/%m/%Y')
                if expense_date.month >= 4 and expense_date.day >= 6:
                    tax_year = f"{expense_date.year}/{expense_date.year + 1}"
                else:
                    tax_year = f"{expense_date.year - 1}/{expense_date.year}"
                updates.append("tax_year = ?")
                params.append(tax_year)
            
            if category_id is not None:
                updates.append("category_id = ?")
                params.append(category_id)
            
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            
            if amount is not None:
                updates.append("amount = ?")
                params.append(amount)
            
            if vat_amount is not None:
                updates.append("vat_amount = ?")
                params.append(vat_amount)
            
            if receipt_file is not None:
                updates.append("receipt_file = ?")
                params.append(receipt_file)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(expense_id)
            
            query = f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    def delete_expense(expense_id):
        """Delete an expense."""
        query = "DELETE FROM expenses WHERE id = ?"
        rows_affected = execute_query(query, (expense_id,))
        return rows_affected > 0
    
    @staticmethod
    def get_summary(tax_year=None, start_date=None, end_date=None):
        """Get expense summary grouped by HMRC category."""
        query = """
            SELECT 
                c.hmrc_box,
                c.hmrc_box_number,
                c.name as category_name,
                COUNT(e.id) as expense_count,
                ROUND(SUM(e.amount), 2) as total_amount,
                ROUND(SUM(e.vat_amount), 2) as total_vat
            FROM expense_categories c
            LEFT JOIN expenses e ON c.id = e.category_id
        """
        
        where_conditions = []
        params = []
        
        if tax_year:
            where_conditions.append("e.tax_year = ?")
            params.append(tax_year)
        
        if start_date:
            where_conditions.append("e.date >= ?")
            params.append(start_date)
        
        if end_date:
            where_conditions.append("e.date <= ?")
            params.append(end_date)
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        query += """
            GROUP BY c.hmrc_box, c.hmrc_box_number, c.name
            HAVING total_amount > 0
            ORDER BY c.hmrc_box_number
        """
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_recurring_expenses():
        """Get all recurring expenses."""
        query = """
            SELECT 
                e.id, e.date, e.description, e.amount, e.recurring_frequency,
                c.name as category_name, c.id as category_id
            FROM expenses e
            JOIN expense_categories c ON e.category_id = c.id
            WHERE e.is_recurring = 1
            ORDER BY e.date DESC
            LIMIT 1
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_tax_years():
        """Get list of tax years with expenses."""
        query = """
            SELECT DISTINCT tax_year
            FROM expenses
            WHERE tax_year IS NOT NULL
            ORDER BY tax_year DESC
        """
        rows = execute_query(query, fetch_all=True)
        return [row[0] for row in rows]
    
    @staticmethod
    def get_mtd_export(tax_year):
        """Get MTD-formatted export for a tax year."""
        summary = ExpenseModel.get_summary(tax_year=tax_year)
        
        # Get total income from payslips for this tax year
        income_query = """
            SELECT ROUND(SUM(total_pay), 2) as total_income
            FROM payslips
            WHERE tax_year = ?
        """
        income_row = execute_query(income_query, (tax_year.split('/')[0],), fetch_one=True)
        total_income = income_row['total_income'] if income_row and income_row['total_income'] else 0
        
        total_expenses = sum(item['total_amount'] for item in summary)
        
        return {
            'tax_year': tax_year,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_profit': total_income - total_expenses,
            'expense_breakdown': summary
        }
    
    @staticmethod
    def clear_all_expenses():
        """Delete all expenses from the database."""
        query = "DELETE FROM expenses"
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM expenses")
            count = cursor.fetchone()['count']
            cursor.execute(query)
            conn.commit()
            return count
