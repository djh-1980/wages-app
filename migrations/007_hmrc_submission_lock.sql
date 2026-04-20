-- 007_hmrc_submission_lock.sql
-- Add a lock marker to HMRC submissions so that digital records (expenses,
-- income) covering a successfully-submitted period cannot be silently edited.
--
-- MTD compliance: once a period is submitted to HMRC, the supporting records
-- must be preserved. Any correction has to go through an amendment, not a
-- silent edit of the original record.

-- Track when the lock took effect. NULL = record is not yet locked.
ALTER TABLE hmrc_submissions ADD COLUMN locked_at TIMESTAMP;

-- Store the inclusive start/end dates covered by the submission so that the
-- application can ask "is date X locked?" without re-parsing submission_data.
ALTER TABLE hmrc_submissions ADD COLUMN period_start_date TEXT;
ALTER TABLE hmrc_submissions ADD COLUMN period_end_date TEXT;

-- Back-fill locked_at for any previously-successful submissions so the lock
-- becomes active on existing records immediately.
UPDATE hmrc_submissions
   SET locked_at = COALESCE(submission_date, CURRENT_TIMESTAMP)
 WHERE status = 'submitted'
   AND locked_at IS NULL;

-- Indexes for the fast lock lookup by date.
CREATE INDEX IF NOT EXISTS idx_hmrc_submissions_locked
    ON hmrc_submissions(status, period_start_date, period_end_date);
