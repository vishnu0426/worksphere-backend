#!/usr/bin/env python3
"""
List all users in the database with their details
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.core.security import verify_password
from sqlalchemy import select

async def list_all_users():
    """List all users in the database"""
    print("👥 All Users in Database")
    print("=" * 30)
    
    async for db in get_db():
        try:
            # Get all users
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            print(f"Found {len(users)} users:")
            print()
            
            for i, user in enumerate(users, 1):
                print(f"{i}. {user.email}")
                print(f"   Name: {user.first_name} {user.last_name}")
                print(f"   ID: {user.id}")
                print(f"   Email Verified: {user.email_verified}")
                print(f"   Requires Password Reset: {user.requires_password_reset}")
                print(f"   Created: {user.created_at}")
                
                # Test common passwords
                test_passwords = ["Password123!", "password123", "NewPassword123!", "Password123"]
                working_password = None
                
                for pwd in test_passwords:
                    if verify_password(pwd, user.password_hash):
                        working_password = pwd
                        break
                
                if working_password:
                    print(f"   ✅ Working Password: {working_password}")
                else:
                    print(f"   ❌ No working password found from test list")
                
                # Get organization info
                org_result = await db.execute(
                    select(OrganizationMember, Organization)
                    .join(Organization, OrganizationMember.organization_id == Organization.id)
                    .where(OrganizationMember.user_id == user.id)
                )
                org_data = org_result.first()
                
                if org_data:
                    org_member, organization = org_data
                    print(f"   Organization: {organization.name}")
                    print(f"   Role: {org_member.role}")
                else:
                    print(f"   ❌ No organization membership")
                
                print()
            
            print("=" * 50)
            print("🎯 FRONTEND LOGIN CREDENTIALS:")
            print("=" * 50)
            
            # Show working credentials
            for user in users:
                test_passwords = ["Password123!", "password123", "NewPassword123!", "Password123"]
                for pwd in test_passwords:
                    if verify_password(pwd, user.password_hash):
                        print(f"✅ Email: {user.email}")
                        print(f"   Password: {pwd}")
                        print()
                        break
                        
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await db.close()

if __name__ == "__main__":
    asyncio.run(list_all_users())
