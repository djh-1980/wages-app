-- 010_periods_of_account.sql
-- Track the trader's accounting period (Period of Account) per tax year.
--
-- HMRC's Business Details API v2.0 (Periods of Account endpoints) lets a
-- sole trader declare the start/end dates of the period they are using
-- for that tax year. For a "standard" tax-year-aligned trader (Daniel's
-- profile) this is simply 6 April YYYY -> 5 April YYYY+1. Non-standard
-- traders may use a different window (e.g. April to March, calendar
-- year, etc.).
--
-- We store one row per tax year (with a soft-delete column so HMRC's
-- DELETE semantic can be reflected without losing history).

CREATE TABLE IF NOT EXISTS periods_of_account (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT,
    period_id TEXT,
    tax_year TEXT NOT NULL,
    period_start_date TEXT NOT NULL,
    period_end_date TEXT NOT NULL,
    period_type TEXT NOT NULL DEFAULT 'standard',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_periods_of_account_business_year
    ON periods_of_account(business_id, tax_year);

CREATE INDEX IF NOT EXISTS idx_periods_of_account_tax_year_active
    ON periods_of_account(tax_year, deleted_at);
