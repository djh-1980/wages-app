"""
Attendance model - handles attendance tracking database operations.
Extracted from web_app.py to improve code organization.
"""

from ..database import get_db_connection, execute_query
import sqlite3


class AttendanceModel:
    """Model for attendance data operations."""
    
    @staticmethod
    def get_all_records(year='', from_date='', to_date=''):
        """Get all attendance records, optionally filtered by year or date range."""
        params = []
        conditions = []
        
        if from_date and to_date:
            # Date range filtering (DD/MM/YYYY format)
            conditions.append("""
                (SUBSTR(date, 7, 4) || '-' || 
                 SUBSTR(date, 4, 2) || '-' || 
                 SUBSTR(date, 1, 2)) BETWEEN ? AND ?
            """)
            params.extend([from_date, to_date])
        elif from_date:
            # From date only
            conditions.append("""
                (SUBSTR(date, 7, 4) || '-' || 
                 SUBSTR(date, 4, 2) || '-' || 
                 SUBSTR(date, 1, 2)) >= ?
            """)
            params.append(from_date)
        elif to_date:
            # To date only
            conditions.append("""
                (SUBSTR(date, 7, 4) || '-' || 
                 SUBSTR(date, 4, 2) || '-' || 
                 SUBSTR(date, 1, 2)) <= ?
            """)
            params.append(to_date)
        elif year:
            # Year filtering (legacy support)
            conditions.append("date LIKE ?")
            params.append(f'%/{year}')
        
        query = """
            SELECT id, date, reason, notes, created_at
            FROM attendance
        """
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY date DESC"
        
        if params:
            rows = execute_query(query, tuple(params), fetch_all=True)
        else:
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
        """Add a new attendance record and remove any runsheet for that date."""
        if not date or not reason:
            raise ValueError('Date and reason are required')
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Add the attendance record
                query = """
                    INSERT INTO attendance (date, reason, notes)
                    VALUES (?, ?, ?)
                """
                cursor.execute(query, (date, reason, notes))
                record_id = cursor.lastrowid
                
                # Remove any runsheet jobs for this date since attendance indicates no work
                delete_jobs_query = """
                    DELETE FROM run_sheet_jobs 
                    WHERE date = ?
                """
                cursor.execute(delete_jobs_query, (date,))
                deleted_jobs = cursor.rowcount
                
                # Remove any daily data for this date
                delete_daily_query = """
                    DELETE FROM runsheet_daily_data 
                    WHERE date = ?
                """
                cursor.execute(delete_daily_query, (date,))
                deleted_daily = cursor.rowcount
                
                conn.commit()
                
                # Log the cleanup action
                if deleted_jobs > 0 or deleted_daily > 0:
                    print(f"Attendance added for {date}: Removed {deleted_jobs} jobs and {deleted_daily} daily records")
                
                return record_id
        except sqlite3.IntegrityError:
            raise ValueError('Record already exists for this date')
    
    @staticmethod
    def update_record(record_id, date=None, reason=None, notes=None):
        """Update an attendance record. Only updates provided fields."""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Build dynamic query based on provided fields
                updates = []
                params = []
                
                if date is not None:
                    updates.append("date = ?")
                    params.append(date)
                if reason is not None:
                    updates.append("reason = ?")
                    params.append(reason)
                if notes is not None:
                    updates.append("notes = ?")
                    params.append(notes)
                
                if not updates:
                    return True  # No updates needed
                
                # If date is being updated, clean up runsheets for the new date
                if date is not None:
                    # Remove any runsheet jobs for the new date
                    delete_jobs_query = """
                        DELETE FROM run_sheet_jobs 
                        WHERE date = ?
                    """
                    cursor.execute(delete_jobs_query, (date,))
                    deleted_jobs = cursor.rowcount
                    
                    # Remove any daily data for the new date
                    delete_daily_query = """
                        DELETE FROM runsheet_daily_data 
                        WHERE date = ?
                    """
                    cursor.execute(delete_daily_query, (date,))
                    deleted_daily = cursor.rowcount
                    
                    if deleted_jobs > 0 or deleted_daily > 0:
                        print(f"Attendance updated for {date}: Removed {deleted_jobs} jobs and {deleted_daily} daily records")
                
                # Update the attendance record
                query = f"UPDATE attendance SET {', '.join(updates)} WHERE id = ?"
                params.append(record_id)
                cursor.execute(query, tuple(params))
                
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            raise ValueError('Record already exists for this date')
        except Exception as e:
            print(f"Error updating attendance record: {e}")
            return False
    
    @staticmethod
    def delete_record(record_id):
        """Delete an attendance record."""
        try:
            query = "DELETE FROM attendance WHERE id = ?"
            execute_query(query, (record_id,))
            return True
        except Exception as e:
            print(f"Error deleting attendance record: {e}")
            return False
    
    @staticmethod
    def get_attendance_dates():
        """Get all dates with attendance records (sick days, personal days, etc.)."""
        try:
            query = "SELECT date FROM attendance ORDER BY date DESC"
            rows = execute_query(query, fetch_all=True)
            return [row[0] for row in rows]
        except Exception as e:
            print(f"Error getting attendance dates: {e}")
            return []
    
    @staticmethod
    def clear_all_records():
        """Clear all attendance records and return count of deleted records."""
        try:
            # First get count of records to be deleted
            count_query = "SELECT COUNT(*) FROM attendance"
            count_result = execute_query(count_query, fetch_all=True)
            count = count_result[0][0] if count_result else 0
            
            # Delete all records
            delete_query = "DELETE FROM attendance"
            execute_query(delete_query)
            
            return count
        except Exception as e:
            print(f"Error clearing attendance records: {e}")
            return 0
