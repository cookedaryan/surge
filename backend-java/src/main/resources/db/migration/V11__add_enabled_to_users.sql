-- Migration V11: Allow an administrator to suspend an account without deleting it.
--
-- Deleting a user would orphan their audit-log entries' meaning: the log records a username, and a
-- reader needs to be able to look that name up. Disabling keeps the history interpretable while
-- immediately blocking sign-in. Existing rows default to enabled so nobody is locked out by the
-- migration itself.

ALTER TABLE users ADD COLUMN IF NOT EXISTS enabled BOOLEAN NOT NULL DEFAULT TRUE;
