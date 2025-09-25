#!/usr/bin/env python3
"""
Run billing tables migration
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def run_migration():
    """Run the billing tables migration"""

    # Parse DATABASE_URL from .env
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")

    # Parse the URL: postgresql+asyncpg://postgres:Admin@192.168.9.119:5432/agno_worksphere
    # Remove the +asyncpg part for asyncpg connection
    if "+asyncpg://" in database_url:
        database_url = database_url.replace("+asyncpg://", "://")

    # Extract connection parameters
    from urllib.parse import urlparse
    parsed = urlparse(database_url)

    db_host = parsed.hostname or "192.168.9.119"
    db_port = parsed.port or 5432
    db_name = parsed.path.lstrip('/') if parsed.path else "agno_worksphere"
    db_user = parsed.username or "postgres"
    db_password = parsed.password or ""
    
    # Read migration SQL
    with open("migrations/add_billing_tables.sql", "r") as f:
        migration_sql = f.read()
    
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
        
        # Execute migration
        print("Running billing tables migration...")
        await conn.execute(migration_sql)
        
        print("✅ Billing tables migration completed successfully!")
        
        # Verify tables were created
        tables_result = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('subscriptions', 'invoices', 'invoice_items', 'payments', 'billing_history')
            ORDER BY table_name
        """)
        
        print("\n📋 Created tables:")
        for row in tables_result:
            print(f"  - {row['table_name']}")
        
        # Check if default subscriptions were created
        subscription_count = await conn.fetchval("SELECT COUNT(*) FROM subscriptions")
        print(f"\n👥 Created {subscription_count} default free subscriptions for existing users")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())
