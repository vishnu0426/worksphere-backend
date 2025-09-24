-- Create mentions table manually
-- Run this SQL script in your PostgreSQL database

CREATE TABLE IF NOT EXISTS mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID NOT NULL,
    mentioned_user_id UUID NOT NULL,
    mentioned_by_user_id UUID NOT NULL,
    mention_text TEXT NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Foreign key constraints
    CONSTRAINT fk_mentions_comment_id 
        FOREIGN KEY (comment_id) 
        REFERENCES comments(id) 
        ON DELETE CASCADE,
    
    CONSTRAINT fk_mentions_mentioned_user_id 
        FOREIGN KEY (mentioned_user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE,
    
    CONSTRAINT fk_mentions_mentioned_by_user_id 
        FOREIGN KEY (mentioned_by_user_id) 
        REFERENCES users(id) 
        ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS ix_mentions_comment_id ON mentions(comment_id);
CREATE INDEX IF NOT EXISTS ix_mentions_mentioned_user_id ON mentions(mentioned_user_id);
CREATE INDEX IF NOT EXISTS ix_mentions_mentioned_by_user_id ON mentions(mentioned_by_user_id);
CREATE INDEX IF NOT EXISTS ix_mentions_is_read ON mentions(is_read);
CREATE INDEX IF NOT EXISTS ix_mentions_created_at ON mentions(created_at);

-- Verify table creation
SELECT 'Mentions table created successfully!' as status;
