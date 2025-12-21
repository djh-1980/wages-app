"""
Verbal Pay Confirmation model - handles verbal pay amount confirmations from boss.
Allows tracking of verbal amounts told on Tuesday and comparing with actual payslip 2 weeks later.
"""

from ..database import get_db_connection, execute_query
from datetime import datetime


class VerbalPayModel:
    """Model for verbal pay confirmation operations."""
    
    @staticmethod
    def add_confirmation(week_number, year, verbal_amount, notes=''):
        """Add a new verbal pay confirmation."""
        confirmation_date = datetime.now().strftime('%Y-%m-%d')
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        query = """
            INSERT INTO verbal_pay_confirmations 
            (week_number, year, verbal_amount, confirmation_date, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (week_number, year, verbal_amount, confirmation_date, notes, updated_at))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            # If duplicate, update instead
            if 'UNIQUE constraint failed' in str(e):
                update_query = """
                    UPDATE verbal_pay_confirmations
                    SET verbal_amount = ?, confirmation_date = ?, notes = ?, updated_at = ?
                    WHERE week_number = ? AND year = ?
                """
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(update_query, (verbal_amount, confirmation_date, notes, updated_at, week_number, year))
                    conn.commit()
                    return cursor.lastrowid
            raise
    
    @staticmethod
    def get_all_confirmations():
        """Get all verbal pay confirmations ordered by year and week."""
        query = """
            SELECT id, week_number, year, verbal_amount, confirmation_date, 
                   notes, payslip_id, payslip_amount, matched
            FROM verbal_pay_confirmations
            ORDER BY year DESC, week_number DESC
        """
        
        rows = execute_query(query, fetch_all=True)
        
        confirmations = []
        for row in rows:
            confirmations.append({
                'id': row[0],
                'week_number': row[1],
                'year': row[2],
                'verbal_amount': row[3],
                'confirmation_date': row[4],
                'notes': row[5],
                'payslip_id': row[6],
                'payslip_amount': row[7],
                'matched': bool(row[8])
            })
        
        return confirmations
    
    @staticmethod
    def get_confirmation(week_number, year):
        """Get verbal pay confirmation for a specific week."""
        query = """
            SELECT id, week_number, year, verbal_amount, confirmation_date, 
                   notes, payslip_id, payslip_amount, matched
            FROM verbal_pay_confirmations
            WHERE week_number = ? AND year = ?
        """
        
        row = execute_query(query, (week_number, year), fetch_one=True)
        
        if row:
            return dict(row)
        return None
    
    @staticmethod
    def match_with_payslip(week_number, year, payslip_id, gross_pay, net_pay):
        """Match a verbal confirmation with actual payslip gross pay.
        
        The verbal amount is what the boss tells you (job total before deductions).
        Standard deductions are £15 (£11 company margin + £4 PDA licence).
        We subtract these deductions from the verbal amount to match the payslip gross pay.
        """
        confirmation = VerbalPayModel.get_confirmation(week_number, year)
        
        if not confirmation:
            return False
        
        verbal_amount = confirmation['verbal_amount']
        
        # Standard weekly deductions: £11 company margin + £4 PDA licence = £15
        STANDARD_DEDUCTIONS = 15.00
        
        # Subtract deductions from verbal amount to get expected gross pay
        expected_gross = verbal_amount - STANDARD_DEDUCTIONS
        
        # Compare expected gross with actual payslip gross pay (within £0.01 tolerance)
        matched = abs(expected_gross - gross_pay) < 0.01
        
        query = """
            UPDATE verbal_pay_confirmations
            SET payslip_id = ?, payslip_amount = ?, matched = ?
            WHERE week_number = ? AND year = ?
        """
        
        # Store gross pay as payslip_amount for comparison
        execute_query(query, (payslip_id, gross_pay, matched, week_number, year))
        
        return matched
    
    @staticmethod
    def update_confirmation(confirmation_id, verbal_amount, notes=''):
        """Update an existing verbal pay confirmation."""
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        query = """
            UPDATE verbal_pay_confirmations
            SET verbal_amount = ?, notes = ?, updated_at = ?
            WHERE id = ?
        """
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (verbal_amount, notes, updated_at, confirmation_id))
            conn.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    def delete_confirmation(confirmation_id):
        """Delete a verbal pay confirmation."""
        query = "DELETE FROM verbal_pay_confirmations WHERE id = ?"
        execute_query(query, (confirmation_id,))
        return True
    
    @staticmethod
    def get_analytics():
        """Get analytics on verbal pay confirmation accuracy."""
        query = """
            SELECT 
                COUNT(*) as total_confirmations,
                SUM(CASE WHEN matched = 1 THEN 1 ELSE 0 END) as matched_count,
                SUM(CASE WHEN matched = 0 AND payslip_id IS NOT NULL THEN 1 ELSE 0 END) as mismatched_count,
                SUM(CASE WHEN payslip_id IS NULL THEN 1 ELSE 0 END) as pending_count,
                AVG(CASE WHEN matched = 1 THEN 100.0 ELSE 0.0 END) as accuracy_rate,
                AVG(CASE WHEN payslip_amount IS NOT NULL AND matched = 0 
                    THEN ABS(verbal_amount - 15.0 - payslip_amount) ELSE 0 END) as avg_difference
            FROM verbal_pay_confirmations
        """
        
        row = execute_query(query, fetch_one=True)
        
        if row:
            return {
                'total_confirmations': row[0] or 0,
                'matched_count': row[1] or 0,
                'mismatched_count': row[2] or 0,
                'pending_count': row[3] or 0,
                'accuracy_rate': round(row[4] or 0, 2),
                'avg_difference': round(row[5] or 0, 2)
            }
        return {}
    
    @staticmethod
    def bulk_import(confirmations):
        """Bulk import multiple verbal confirmations."""
        success_count = 0
        error_count = 0
        errors = []
        
        for conf in confirmations:
            try:
                week_number = int(conf.get('week_number'))
                year = int(conf.get('year'))
                verbal_amount = float(conf.get('verbal_amount'))
                notes = conf.get('notes', '')
                
                # Validate
                if week_number < 1 or week_number > 53:
                    raise ValueError(f'Week {week_number}: Invalid week number')
                if verbal_amount <= 0:
                    raise ValueError(f'Week {week_number}: Invalid amount')
                if len(notes) > 500:
                    raise ValueError(f'Week {week_number}: Notes too long')
                
                VerbalPayModel.add_confirmation(week_number, year, verbal_amount, notes)
                success_count += 1
            except Exception as e:
                error_count += 1
                errors.append({
                    'week': conf.get('week_number'),
                    'error': str(e)
                })
        
        return {
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        }
