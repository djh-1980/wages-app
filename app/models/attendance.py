"""
Attendance model - handles attendance tracking database operations.
Extracted from web_app.py to improve code organization.
"""

from ..database import get_db_connection, execute_query
import sqlite3


class AttendanceModel:
    """Model for attendance data operations."""
    
    @staticmethod
    def get_all_records(year=''):
        """Get all attendance records, optionally filtered by year."""
        if year:
            query = """
                SELECT id, date, reason, notes, created_at
                FROM attendance
                WHERE date LIKE ?
                ORDER BY date DESC
            """
            rows = execute_query(query, (f'%/{year}',), fetch_all=True)
        else:
            query = """
                SELECT id, date, reason, notes, created_at
                FROM attendance
                ORDER BY date DESC
            """
            rows = execute_query(query, fetch_all=True)
        
        records = []
        for row in rows:
            records.append({
                'id': row[0],
                'date': row[1],
                'reason': row[2],
                'notes': row[3],
                'created_at': row[4]
            })
        
        return records
    
    @staticmethod
    def add_record(date, reason, notes=''):
        """Add a new attendance record."""
        if not date or not reason:
            raise ValueError('Date and reason are required')
        
        try:
            query = """
                INSERT INTO attendance (date, reason, notes)
                VALUES (?, ?, ?)
            """
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (date, reason, notes))
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError('Record already exists for this date')
    
    @staticmethod
    def delete_record(record_id):
        """Delete an attendance record."""
        query = "DELETE FROM attendance WHERE id = ?"
        rows_affected = execute_query(query, (record_id,))
        return rows_affected > 0
    
    @staticmethod
    def clear_all_records():
        """Clear all attendance records."""
        query = "DELETE FROM attendance"
        deleted = execute_query(query)
        return deleted
