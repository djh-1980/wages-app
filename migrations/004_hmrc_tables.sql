-- HMRC Making Tax Digital (MTD) integration tables

-- HMRC OAuth credentials
CREATE TABLE IF NOT EXISTS hmrc_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP,
    scope TEXT,
    environment TEXT DEFAULT 'sandbox',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HMRC quarterly obligations
CREATE TABLE IF NOT EXISTS hmrc_obligations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tax_year TEXT NOT NULL,
    period_id TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL,
    received_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period_id)
);

-- HMRC quarterly submissions
CREATE TABLE IF NOT EXISTS hmrc_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tax_year TEXT NOT NULL,
    period_id TEXT NOT NULL,
    submission_date TEXT,
    status TEXT DEFAULT 'pending',
    hmrc_receipt_id TEXT,
    submission_data TEXT,
    response_data TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- HMRC final declarations (crystallisation)
CREATE TABLE IF NOT EXISTS hmrc_final_declarations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tax_year TEXT NOT NULL,
    calculation_id TEXT,
    estimated_tax REAL,
    status TEXT DEFAULT 'pending',
    hmrc_receipt_id TEXT,
    submitted_at TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tax_year, calculation_id)
);
