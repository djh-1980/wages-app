-- Add NINO tracking to HMRC tables
-- Links OAuth tokens, submissions, and final declarations to specific test users

-- Track which NINO the OAuth token was issued for
ALTER TABLE hmrc_credentials ADD COLUMN nino TEXT;

-- Track which NINO each submission was made against
ALTER TABLE hmrc_submissions ADD COLUMN nino TEXT;

-- Track which NINO each final declaration belongs to
ALTER TABLE hmrc_final_declarations ADD COLUMN nino TEXT;

-- Backfill: set NINO on active credential from active sandbox test user
UPDATE hmrc_credentials
SET nino = (SELECT nino FROM sandbox_test_users WHERE is_active = 1 LIMIT 1)
WHERE is_active = 1 AND nino IS NULL;

-- Backfill: set NINO on existing submitted records from active sandbox test user
UPDATE hmrc_submissions
SET nino = (SELECT nino FROM sandbox_test_users WHERE is_active = 1 LIMIT 1)
WHERE nino IS NULL;

UPDATE hmrc_final_declarations
SET nino = (SELECT nino FROM sandbox_test_users WHERE is_active = 1 LIMIT 1)
WHERE nino IS NULL;
