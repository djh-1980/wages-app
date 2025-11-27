"""
Mileage model for managing mileage entries and detecting missing data
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ..database import get_db_connection

class MileageModel:
    """Model for managing mileage entries."""
    
    @staticmethod
    def get_db_path():
        """Get the database path."""
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'database', 'wages.db')
    
    @staticmethod
    def init_db():
        """Initialize the mileage table if it doesn't exist."""
        db_path = MileageModel.get_db_path()
        
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS mileage_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    start_mileage REAL DEFAULT 0,
                    end_mileage REAL DEFAULT 0,
                    total_miles REAL NOT NULL,
                    fuel_cost REAL DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date)
                )
            ''')
            
            # Create index on date for faster queries
            conn.execute('CREATE INDEX IF NOT EXISTS idx_mileage_date ON mileage_entries(date)')
            conn.commit()
    
    @staticmethod
    def create_entry(date: str, start_mileage: float = 0, end_mileage: float = 0, 
                    total_miles: float = 0, fuel_cost: float = 0, notes: str = '') -> int:
        """Create a new mileage entry."""
        MileageModel.init_db()
        db_path = MileageModel.get_db_path()
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute('''
                INSERT OR REPLACE INTO mileage_entries 
                (date, start_mileage, end_mileage, total_miles, fuel_cost, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (date, start_mileage, end_mileage, total_miles, fuel_cost, notes))
            
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def get_entries(limit: int = 50, offset: int = 0, year: str = None, month: str = None) -> List[Dict]:
        """Get mileage entries with optional filtering."""
        MileageModel.init_db()
        db_path = MileageModel.get_db_path()
        
        query = '''
            SELECT id, date, start_mileage, end_mileage, total_miles, fuel_cost, notes, 
                   created_at, updated_at
            FROM mileage_entries
            WHERE 1=1
        '''
        params = []
        
        if year:
            query += ' AND date LIKE ?'
            params.append(f'{year}-%')
        
        if month:
            if year:
                query += ' AND date LIKE ?'
                params.append(f'{year}-{month:0>2}-%')
            else:
                query += ' AND substr(date, 6, 2) = ?'
                params.append(f'{month:0>2}')
        
        query += ' ORDER BY date DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            entries = []
            for row in cursor.fetchall():
                entries.append({
                    'id': row['id'],
                    'date': row['date'],
                    'start_mileage': row['start_mileage'],
                    'end_mileage': row['end_mileage'],
                    'total_miles': row['total_miles'],
                    'fuel_cost': row['fuel_cost'],
                    'notes': row['notes'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                })
            
            return entries
    
    @staticmethod
    def get_entry_by_id(entry_id: int) -> Optional[Dict]:
        """Get a specific mileage entry by ID."""
        MileageModel.init_db()
        db_path = MileageModel.get_db_path()
        
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT id, date, start_mileage, end_mileage, total_miles, fuel_cost, notes,
                       created_at, updated_at
                FROM mileage_entries
                WHERE id = ?
            ''', (entry_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row['id'],
                    'date': row['date'],
                    'start_mileage': row['start_mileage'],
                    'end_mileage': row['end_mileage'],
                    'total_miles': row['total_miles'],
                    'fuel_cost': row['fuel_cost'],
                    'notes': row['notes'],
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
            
            return None
    
    @staticmethod
    def update_entry(entry_id: int, **kwargs) -> bool:
        """Update a mileage entry."""
        MileageModel.init_db()
        db_path = MileageModel.get_db_path()
        
        # Build update query dynamically based on provided fields
        update_fields = []
        params = []
        
        for field in ['date', 'start_mileage', 'end_mileage', 'total_miles', 'fuel_cost', 'notes']:
            if field in kwargs and kwargs[field] is not None:
                update_fields.append(f'{field} = ?')
                params.append(kwargs[field])
        
        if not update_fields:
            return False
        
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        params.append(entry_id)
        
        query = f'''
            UPDATE mileage_entries 
            SET {', '.join(update_fields)}
            WHERE id = ?
        '''
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    def delete_entry(entry_id: int) -> bool:
        """Delete a mileage entry."""
        MileageModel.init_db()
        db_path = MileageModel.get_db_path()
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute('DELETE FROM mileage_entries WHERE id = ?', (entry_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    @staticmethod
    def get_missing_mileage_dates(year: str = None, month: str = None) -> List[str]:
        """Get dates that have job data but no mileage entries (same logic as weekly summary)."""
        MileageModel.init_db()
        
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            
            # Get all dates with jobs (working days) - filter out invalid dates
            job_dates_query = '''
                SELECT 
                    date,
                    COUNT(*) as jobs
                FROM run_sheet_jobs
                WHERE date IS NOT NULL 
                AND date != ''
                AND date LIKE '__/__/____'
                AND length(date) = 10
                AND substr(date, 3, 1) = '/'
                AND substr(date, 6, 1) = '/'
            '''
            job_params = []
            
            if year:
                job_dates_query += ' AND substr(date, 7, 4) = ?'
                job_params.append(year)
            
            if month:
                job_dates_query += ' AND substr(date, 4, 2) = ?'
                job_params.append(f'{int(month):02d}')
            
            job_dates_query += '''
                GROUP BY date
                HAVING COUNT(*) > 0
                ORDER BY date
            '''
            
            cursor = conn.execute(job_dates_query, job_params)
            working_days = cursor.fetchall()
            
            if not working_days:
                return []
            
            # Get dates that have mileage data (from runsheet_daily_data table)
            work_dates = [row['date'] for row in working_days]
            placeholders = ','.join('?' * len(work_dates))
            
            mileage_query = f'''
                SELECT DISTINCT date
                FROM runsheet_daily_data
                WHERE date IN ({placeholders})
                AND (mileage IS NOT NULL AND mileage > 0)
            '''
            
            cursor = conn.execute(mileage_query, work_dates)
            dates_with_mileage = set(row[0] for row in cursor.fetchall())
            
            # Also check our mileage_entries table
            mileage_entries_query = f'''
                SELECT DISTINCT date
                FROM mileage_entries
                WHERE date IN ({placeholders})
            '''
            
            try:
                cursor = conn.execute(mileage_entries_query, work_dates)
                dates_with_entries = set(row[0] for row in cursor.fetchall())
                dates_with_mileage.update(dates_with_entries)
            except sqlite3.OperationalError:
                # mileage_entries table doesn't exist yet, that's ok
                pass
            
            # Find missing dates (days with jobs but no mileage data)
            missing_dates = []
            for row in working_days:
                if row['date'] not in dates_with_mileage:
                    missing_dates.append(row['date'])
            
            return missing_dates
    
    @staticmethod
    def get_summary(year: str = None, month: str = None) -> Dict:
        """Get mileage summary statistics."""
        MileageModel.init_db()
        db_path = MileageModel.get_db_path()
        
        query = '''
            SELECT 
                COUNT(*) as total_entries,
                SUM(total_miles) as total_miles,
                SUM(fuel_cost) as total_fuel_cost,
                AVG(total_miles) as avg_miles_per_day,
                AVG(fuel_cost) as avg_fuel_per_day,
                MIN(date) as first_date,
                MAX(date) as last_date
            FROM mileage_entries
            WHERE 1=1
        '''
        params = []
        
        if year:
            query += ' AND date LIKE ?'
            params.append(f'{year}-%')
        
        if month:
            if year:
                query += ' AND date LIKE ?'
                params.append(f'{year}-{month:0>2}-%')
            else:
                query += ' AND substr(date, 6, 2) = ?'
                params.append(f'{month:0>2}')
        
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            
            if row and row['total_entries'] > 0:
                return {
                    'total_entries': row['total_entries'],
                    'total_miles': round(row['total_miles'] or 0, 1),
                    'total_fuel_cost': round(row['total_fuel_cost'] or 0, 2),
                    'avg_miles_per_day': round(row['avg_miles_per_day'] or 0, 1),
                    'avg_fuel_per_day': round(row['avg_fuel_per_day'] or 0, 2),
                    'cost_per_mile': round((row['total_fuel_cost'] or 0) / (row['total_miles'] or 1), 3),
                    'first_date': row['first_date'],
                    'last_date': row['last_date']
                }
            else:
                return {
                    'total_entries': 0,
                    'total_miles': 0,
                    'total_fuel_cost': 0,
                    'avg_miles_per_day': 0,
                    'avg_fuel_per_day': 0,
                    'cost_per_mile': 0,
                    'first_date': None,
                    'last_date': None
                }
    
    @staticmethod
    def has_mileage_for_date(date: str) -> bool:
        """Check if mileage entry exists for a specific date."""
        MileageModel.init_db()
        db_path = MileageModel.get_db_path()
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute('SELECT 1 FROM mileage_entries WHERE date = ?', (date,))
            return cursor.fetchone() is not None
