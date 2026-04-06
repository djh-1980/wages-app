-- Users and authentication tables
-- Note: users table is already in 001_initial_schema.sql
-- This migration is kept for logical separation but may be empty or contain user seed data

-- Users table already created in 001_initial_schema.sql
-- This migration can be used for default user creation or user-related extensions

-- Example: Create default admin user (commented out - set password manually)
-- INSERT OR IGNORE INTO users (id, username, password_hash, email) VALUES
-- (1, 'admin', 'CHANGE_THIS_HASH', 'admin@example.com');
