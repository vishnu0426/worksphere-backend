#!/usr/bin/env python3
"""
Clear avatar data from the database
This script removes all avatar_url values from the users table to ensure consistency
after avatar functionality removal.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db_engine, get_db
from app.models.user import User


async def clear_avatar_data():
    """Clear all avatar_url data from users table"""
    print("🧹 Starting avatar data cleanup...")
    
    try:
        # Get database engine
        engine = get_db_engine()
        
        # Create async session
        async with AsyncSession(engine) as session:
            # Update all users to set avatar_url to NULL
            result = await session.execute(
                text("UPDATE users SET avatar_url = NULL WHERE avatar_url IS NOT NULL")
            )
            
            # Commit the changes
            await session.commit()
            
            rows_affected = result.rowcount
            print(f"✅ Successfully cleared avatar data from {rows_affected} users")
            
            # Verify the cleanup
            verification_result = await session.execute(
                text("SELECT COUNT(*) FROM users WHERE avatar_url IS NOT NULL")
            )
            remaining_avatars = verification_result.scalar()
            
            if remaining_avatars == 0:
                print("✅ Verification passed: No avatar URLs remain in the database")
            else:
                print(f"⚠️  Warning: {remaining_avatars} users still have avatar URLs")
                
    except Exception as e:
        print(f"❌ Error during avatar data cleanup: {str(e)}")
        raise
    
    print("🎉 Avatar data cleanup completed successfully!")


async def main():
    """Main function"""
    print("Avatar Data Cleanup Script")
    print("=" * 50)
    
    # Confirm with user
    response = input("This will remove all avatar URLs from the database. Continue? (y/N): ")
    if response.lower() != 'y':
        print("Operation cancelled.")
        return
    
    try:
        await clear_avatar_data()
    except Exception as e:
        print(f"❌ Script failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
