-- HMRC Sandbox Test Users table
-- Stores test user credentials and business details for sandbox testing

CREATE TABLE IF NOT EXISTS sandbox_test_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    password TEXT NOT NULL,
    nino TEXT NOT NULL UNIQUE,
    sa_utr TEXT,
    business_id TEXT,
    trading_name TEXT,
    accounting_type TEXT,
    commencement_date TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_sandbox_nino ON sandbox_test_users(nino);
CREATE INDEX IF NOT EXISTS idx_sandbox_active ON sandbox_test_users(is_active);
