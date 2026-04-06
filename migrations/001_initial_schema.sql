-- Initial database schema for TVS Wages
-- This migration creates all core tables

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Payslips table
CREATE TABLE IF NOT EXISTS payslips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_number INTEGER,
    period_start TEXT,
    period_end TEXT,
    gross_subcontractor_payment REAL,
    materials_deduction REAL,
    cis_deduction REAL,
    net_payment REAL,
    pdf_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Run sheet jobs table
CREATE TABLE IF NOT EXISTS run_sheet_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    job_number TEXT,
    customer TEXT,
    activity TEXT,
    location TEXT,
    postcode TEXT,
    status TEXT DEFAULT 'pending',
    notes TEXT,
    pdf_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Job items table (from payslips)
CREATE TABLE IF NOT EXISTS job_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payslip_id INTEGER,
    job_number TEXT,
    customer TEXT,
    location TEXT,
    postcode TEXT,
    pay REAL,
    FOREIGN KEY (payslip_id) REFERENCES payslips(id)
);

-- Runsheet daily data (mileage tracking)
CREATE TABLE IF NOT EXISTS runsheet_daily_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,
    mileage REAL,
    fuel_cost REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Attendance records
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Paypoint stock table
CREATE TABLE IF NOT EXISTS paypoint_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    job_number TEXT,
    location TEXT,
    stock_type TEXT,
    quantity INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gmail credentials
CREATE TABLE IF NOT EXISTS gmail_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    credentials_json TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sync log
CREATE TABLE IF NOT EXISTS sync_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT,
    files_processed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Verbal pay confirmations
CREATE TABLE IF NOT EXISTS verbal_pay_confirmations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    job_number TEXT NOT NULL,
    customer TEXT,
    location TEXT,
    confirmed_pay REAL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date, job_number)
);

-- Route optimization cache
CREATE TABLE IF NOT EXISTS route_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE NOT NULL,
    optimized_order TEXT,
    total_distance REAL,
    total_duration REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
