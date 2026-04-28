-- 009_hmrc_submission_type.sql
-- Track which HMRC API was used to submit each row in hmrc_submissions.
--
-- Self-Employment Business (MTD) v5.0 deprecated the per-quarter
-- POST /period endpoint in favour of cumulative period summaries
-- (POST /period/cumulative/{taxYear}). We need to be able to tell the
-- two flavours apart in storage so the UI can show the correct
-- breakdown and the duplicate-check logic can be relaxed for
-- cumulative submissions (where Q2 is expected to "overwrite" Q1).

ALTER TABLE hmrc_submissions
    ADD COLUMN submission_type TEXT NOT NULL DEFAULT 'period';

-- Existing rows pre-date the cumulative endpoint, so they all stay
-- as 'period'. New cumulative rows will write 'cumulative'.

CREATE INDEX IF NOT EXISTS idx_hmrc_submissions_type_year
    ON hmrc_submissions(submission_type, tax_year, status);
