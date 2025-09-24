-- Add requires_password_reset field to users table
-- This field tracks whether a user needs to reset their password after accepting an invitation

ALTER TABLE users ADD COLUMN requires_password_reset BOOLEAN DEFAULT FALSE NOT NULL;

-- Update existing users to not require password reset by default
UPDATE users SET requires_password_reset = FALSE WHERE requires_password_reset IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN users.requires_password_reset IS 'Flag indicating if user needs to reset password after invitation acceptance';
