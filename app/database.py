"""
Database utilities and connection management.
Extracted from web_app.py to centralize database operations.
"""

import sqlite3
from pathlib import Path
from contextlib import contextmanager

# Database configuration
DB_PATH = "data/database/payslips.db"


def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = get_db()
        yield conn
    finally:
        if conn:
            conn.close()


def init_database():
    """Initialize all database tables."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Initialize attendance table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                reason TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Initialize settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Initialize runsheet daily data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runsheet_daily_data (
                date TEXT PRIMARY KEY,
                mileage REAL,
                fuel_cost REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()


def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Execute a database query with proper connection handling."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.rowcount


def execute_many(query, params_list):
    """Execute multiple queries with the same statement."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        return cursor.rowcount
