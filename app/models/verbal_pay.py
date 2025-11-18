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
        
        query = """
            INSERT INTO verbal_pay_confirmations 
            (week_number, year, verbal_amount, confirmation_date, notes)
            VALUES (?, ?, ?, ?, ?)
        """
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (week_number, year, verbal_amount, confirmation_date, notes))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            # If duplicate, update instead
            if 'UNIQUE constraint failed' in str(e):
                update_query = """
                    UPDATE verbal_pay_confirmations
                    SET verbal_amount = ?, confirmation_date = ?, notes = ?
                    WHERE week_number = ? AND year = ?
                """
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(update_query, (verbal_amount, confirmation_date, notes, week_number, year))
                    conn.commit()
                    return cursor.lastrowid
            raise
    
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
            return {
                'id': row[0],
                'week_number': row[1],
                'year': row[2],
                'verbal_amount': row[3],
                'confirmation_date': row[4],
                'notes': row[5],
                'payslip_id': row[6],
                'payslip_amount': row[7],
                'matched': bool(row[8])
            }
        return None
    
    @staticmethod
    def get_all_confirmations(limit=50):
        """Get all verbal pay confirmations."""
        query = """
            SELECT id, week_number, year, verbal_amount, confirmation_date, 
                   notes, payslip_id, payslip_amount, matched
            FROM verbal_pay_confirmations
            ORDER BY year DESC, week_number DESC
            LIMIT ?
        """
        
        rows = execute_query(query, (limit,), fetch_all=True)
        
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
    def match_with_payslip(week_number, year, payslip_id, gross_pay, net_pay):
        """Match a verbal confirmation with actual payslip gross pay."""
        # Verbal amount should match gross pay (before deductions)
        confirmation = VerbalPayModel.get_confirmation(week_number, year)
        
        if not confirmation:
            return False
        
        verbal_amount = confirmation['verbal_amount']
        # Compare verbal amount with gross pay (within £0.01 tolerance)
        matched = abs(verbal_amount - gross_pay) < 0.01
        
        query = """
            UPDATE verbal_pay_confirmations
            SET payslip_id = ?, payslip_amount = ?, matched = ?
            WHERE week_number = ? AND year = ?
        """
        
        # Store gross pay as payslip_amount for comparison
        execute_query(query, (payslip_id, gross_pay, matched, week_number, year))
        
        return matched
    
    @staticmethod
    def delete_confirmation(confirmation_id):
        """Delete a verbal pay confirmation."""
        query = "DELETE FROM verbal_pay_confirmations WHERE id = ?"
        execute_query(query, (confirmation_id,))
        return True
