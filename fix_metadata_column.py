#!/usr/bin/env python3
"""
Fix metadata column name in billing_history table
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

async def fix_metadata_column():
    """Fix the metadata column name conflict"""
    
    # Parse DATABASE_URL from .env
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")
    
    # Remove the +asyncpg part for asyncpg connection
    if "+asyncpg://" in database_url:
        database_url = database_url.replace("+asyncpg://", "://")
    
    # Extract connection parameters
    parsed = urlparse(database_url)
    
    db_host = parsed.hostname or "192.168.9.119"
    db_port = parsed.port or 5432
    db_name = parsed.path.lstrip('/') if parsed.path else "agno_worksphere"
    db_user = parsed.username or "postgres"
    db_password = parsed.password or ""
    
    try:
        # Connect to database
        print(f"Connecting to database: {db_host}:{db_port}/{db_name} as {db_user}")
        conn = await asyncpg.connect(
            host=db_host,
            port=int(db_port),
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        print("Connected to database successfully")
        
        # Check if the column exists
        column_check = await conn.fetchval("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'billing_history' 
            AND column_name = 'metadata'
        """)
        
        if column_check:
            print("Renaming 'metadata' column to 'event_metadata'...")
            await conn.execute("""
                ALTER TABLE billing_history 
                RENAME COLUMN metadata TO event_metadata;
            """)
            print("✅ Column renamed successfully!")
        else:
            print("ℹ️ Column 'metadata' not found, checking for 'event_metadata'...")
            event_metadata_check = await conn.fetchval("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'billing_history' 
                AND column_name = 'event_metadata'
            """)
            
            if event_metadata_check:
                print("✅ Column 'event_metadata' already exists!")
            else:
                print("❌ Neither 'metadata' nor 'event_metadata' column found!")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Fix failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(fix_metadata_column())
