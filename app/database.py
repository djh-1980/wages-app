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
        
        # Initialize verbal pay confirmations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS verbal_pay_confirmations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_number INTEGER NOT NULL,
                year INTEGER NOT NULL,
                verbal_amount REAL NOT NULL,
                confirmation_date TEXT NOT NULL,
                notes TEXT,
                payslip_id INTEGER,
                payslip_amount REAL,
                matched BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(week_number, year)
            )
        """)
        
        # Add updated_at column if it doesn't exist (for existing databases)
        try:
            cursor.execute("SELECT updated_at FROM verbal_pay_confirmations LIMIT 1")
        except sqlite3.OperationalError:
            # SQLite doesn't support CURRENT_TIMESTAMP as default in ALTER TABLE
            cursor.execute("ALTER TABLE verbal_pay_confirmations ADD COLUMN updated_at TIMESTAMP")
            # Update existing rows to set updated_at = created_at
            cursor.execute("UPDATE verbal_pay_confirmations SET updated_at = created_at WHERE updated_at IS NULL")
        
        # Initialize expense categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expense_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                hmrc_box TEXT NOT NULL,
                hmrc_box_number INTEGER,
                description TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Initialize expenses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                vat_amount REAL DEFAULT 0,
                receipt_file TEXT,
                is_recurring BOOLEAN DEFAULT 0,
                recurring_frequency TEXT,
                tax_year TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES expense_categories(id)
            )
        """)
        
        # Insert default HMRC expense categories
        cursor.execute("""
            INSERT OR IGNORE INTO expense_categories (name, hmrc_box, hmrc_box_number, description) VALUES
            ('Vehicle Costs', 'Vehicle costs', 20, 'Van loan, insurance, tax, MOT, repairs, tyres'),
            ('Fuel', 'Vehicle costs', 20, 'Fuel and oil for business vehicle'),
            ('Travel Costs', 'Travel costs', 21, 'Parking, tolls, public transport'),
            ('Home Office', 'Premises costs', 22, 'Home office allowance (£6/week simplified or actual costs)'),
            ('Premises Costs', 'Premises costs', 22, 'Rent, rates, power, insurance (if applicable)'),
            ('Admin Costs', 'Admin costs', 23, 'Phone, internet, stationery, postage'),
            ('Advertising', 'Advertising', 24, 'Marketing and advertising costs'),
            ('Interest', 'Interest', 25, 'Bank and loan interest'),
            ('Financial Charges', 'Financial charges', 26, 'Bank charges, card fees'),
            ('Professional Fees', 'Professional fees', 27, 'Accountant, legal, subscriptions'),
            ('Depreciation', 'Depreciation', 28, 'Equipment depreciation'),
            ('Other Expenses', 'Other expenses', 29, 'Tools, clothing, training, software')
        """)
        
        # Initialize recurring templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recurring_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                expected_amount REAL NOT NULL,
                frequency TEXT NOT NULL,
                merchant_pattern TEXT NOT NULL,
                day_of_month INTEGER,
                is_active BOOLEAN DEFAULT 1,
                tolerance_amount REAL DEFAULT 5.0,
                auto_import BOOLEAN DEFAULT 0,
                next_expected_date TEXT,
                last_matched_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES expense_categories(id)
            )
        """)
        
        # Initialize email audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_number TEXT NOT NULL,
                customer TEXT,
                location TEXT,
                agreed_rate REAL NOT NULL,
                job_date TEXT,
                sent_to TEXT NOT NULL,
                cc_to TEXT,
                user_name TEXT,
                email_subject TEXT,
                message_id TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'sent'
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
