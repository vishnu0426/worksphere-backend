#!/usr/bin/env python3
"""
Script to create mentions table manually using Python
Run this script to create the mentions table if it doesn't exist
"""
import asyncio
import asyncpg
import sys
import os

# Database URL - update this to match your database configuration
DATABASE_URL = "postgresql://postgres:Admin@192.168.9.119:5432/agno_worksphere"

async def create_mentions_table():
    """Create mentions table with proper foreign keys and indexes"""
    try:
        # Connect to database
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected to database")
        
        # Check if mentions table already exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'mentions'
            );
        """)
        
        if table_exists:
            print("ℹ️ Mentions table already exists")
            await conn.close()
            return
        
        print("🔄 Creating mentions table...")
        
        # Create mentions table
        await conn.execute("""
            CREATE TABLE mentions (
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
        """)
        print("✅ Created mentions table")
        
        # Create indexes for better performance
        indexes = [
            ("ix_mentions_comment_id", "comment_id"),
            ("ix_mentions_mentioned_user_id", "mentioned_user_id"),
            ("ix_mentions_mentioned_by_user_id", "mentioned_by_user_id"),
            ("ix_mentions_is_read", "is_read"),
            ("ix_mentions_created_at", "created_at")
        ]
        
        for index_name, column in indexes:
            await conn.execute(f"""
                CREATE INDEX IF NOT EXISTS {index_name} ON mentions({column});
            """)
            print(f"✅ Created index {index_name}")
        
        # Verify table creation
        table_count = await conn.fetchval("SELECT COUNT(*) FROM mentions;")
        print(f"✅ Mentions table created successfully with {table_count} records")
        
        await conn.close()
        print("✅ Database connection closed")
        
    except Exception as e:
        print(f"❌ Error creating mentions table: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Starting mentions table creation...")
    asyncio.run(create_mentions_table())
    print("🎉 Mentions table setup completed!")
