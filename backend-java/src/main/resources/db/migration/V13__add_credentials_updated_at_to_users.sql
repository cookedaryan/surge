-- Marks the moment a user's credentials or privileges last changed.
--
-- Tokens are stateless and live for 24 hours, so resetting a password, demoting a user or
-- disabling an account had no effect on anyone already holding a token. Comparing a token's
-- issued-at against this column lets the filter reject tokens minted before the change.
--
-- Existing rows are backdated to their creation time rather than to now(), so this migration on
-- its own does not sign everybody out.
ALTER TABLE users
    ADD COLUMN credentials_updated_at TIMESTAMPTZ;

UPDATE users SET credentials_updated_at = created_at WHERE credentials_updated_at IS NULL;

ALTER TABLE users
    ALTER COLUMN credentials_updated_at SET NOT NULL,
    ALTER COLUMN credentials_updated_at SET DEFAULT CURRENT_TIMESTAMP;
