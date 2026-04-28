-- 008_performance_indexes.sql
-- Additional indexes to speed up report queries, expense lookups,
-- HMRC submission de-duplication, and recurring template matching.
-- All IF NOT EXISTS so this is idempotent.

-- expenses: ordering by date, MTD export by tax_year, summary by category
CREATE INDEX IF NOT EXISTS idx_expenses_date
    ON expenses(date);
CREATE INDEX IF NOT EXISTS idx_expenses_tax_year
    ON expenses(tax_year);
CREATE INDEX IF NOT EXISTS idx_expenses_category
    ON expenses(category_id);

-- recurring_templates: the /due endpoint filters by is_active + sorts by next_expected_date
CREATE INDEX IF NOT EXISTS idx_recurring_active_next
    ON recurring_templates(is_active, next_expected_date);

-- hmrc_submissions: dup-check in submit_period() is by (tax_year, period_id, nino, status)
CREATE INDEX IF NOT EXISTS idx_hmrc_submissions_lookup
    ON hmrc_submissions(tax_year, period_id, nino, status);

-- run_sheet_jobs: many reports filter by status AND date together
CREATE INDEX IF NOT EXISTS idx_runsheet_date_status
    ON run_sheet_jobs(date, status);

-- job_items: payslip joins are the dominant access pattern. The original
-- 008 used job_items(client), which exists in production (loaded by
-- scripts/production/extract_payslips.py) but not in the migration-001
-- schema used by tests, so the migration aborted on a fresh DB and
-- blocked all later migrations. payslip_id is present in both schemas
-- and is the column that actually drives the JOIN in api_reports.
CREATE INDEX IF NOT EXISTS idx_job_items_payslip_id
    ON job_items(payslip_id);

-- verbal_pay_confirmations is queried by week/year
CREATE INDEX IF NOT EXISTS idx_verbal_pay_week_year
    ON verbal_pay_confirmations(week_number, year);

-- email_audit_log is queried by job_number for history
CREATE INDEX IF NOT EXISTS idx_email_audit_job_number
    ON email_audit_log(job_number);
