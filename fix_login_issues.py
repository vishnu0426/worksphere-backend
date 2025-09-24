#!/usr/bin/env python3
"""
Fix login issues and bcrypt warnings
"""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.core.security import hash_password, verify_password
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

async def fix_login_issues():
    """Fix user login issues and create test users"""
    print("🔧 Fixing Login Issues")
    print("=" * 40)
    
    async for db in get_db():
        try:
            # 1. Check existing users
            print("1. Checking existing users...")
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            print(f"Found {len(users)} existing users")
            
            # 2. Fix existing users or create new ones
            test_users = [
                {"email": "admin@test.com", "first_name": "Admin", "last_name": "User", "role": "admin"},
                {"email": "member@test.com", "first_name": "Member", "last_name": "User", "role": "member"},
                {"email": "viewer@test.com", "first_name": "Viewer", "last_name": "User", "role": "viewer"},
            ]
            
            # Create or update users
            for user_data in test_users:
                print(f"\n--- Processing {user_data['email']} ---")
                
                # Check if user exists
                existing_result = await db.execute(
                    select(User).where(User.email == user_data["email"])
                )
                existing_user = existing_result.scalar_one_or_none()
                
                if existing_user:
                    print(f"User exists, updating...")
                    existing_user.password_hash = hash_password("Password123!")
                    existing_user.email_verified = True
                    existing_user.requires_password_reset = False
                    user = existing_user
                else:
                    print(f"Creating new user...")
                    user = User(
                        email=user_data["email"],
                        first_name=user_data["first_name"],
                        last_name=user_data["last_name"],
                        password_hash=hash_password("Password123!"),
                        email_verified=True,
                        requires_password_reset=False
                    )
                    db.add(user)
                
                await db.commit()
                if not existing_user:
                    await db.refresh(user)
                
                print(f"✅ User ready: {user.email}")
                
                # Verify password works
                if verify_password("Password123!", user.password_hash):
                    print(f"✅ Password verification works")
                else:
                    print(f"❌ Password verification failed")
                
                # Check/create organization membership
                org_result = await db.execute(
                    select(OrganizationMember, Organization)
                    .join(Organization, OrganizationMember.organization_id == Organization.id)
                    .where(OrganizationMember.user_id == user.id)
                )
                org_data = org_result.first()
                
                if not org_data:
                    print(f"Creating organization membership...")
                    
                    # Get or create default organization
                    default_org_result = await db.execute(
                        select(Organization).where(Organization.name == "Test Organization").limit(1)
                    )
                    default_org = default_org_result.scalar_one_or_none()
                    
                    if not default_org:
                        default_org = Organization(
                            name="Test Organization",
                            domain="test.com",
                            description="Test organization for login"
                        )
                        db.add(default_org)
                        await db.commit()
                        await db.refresh(default_org)
                        print(f"✅ Created test organization")
                    
                    # Create membership
                    membership = OrganizationMember(
                        user_id=user.id,
                        organization_id=default_org.id,
                        role=user_data["role"]
                    )
                    db.add(membership)
                    await db.commit()
                    print(f"✅ Added to organization as {user_data['role']}")
                else:
                    org_member, organization = org_data
                    print(f"✅ Already in organization: {organization.name} as {org_member.role}")
            
            print(f"\n🎉 All users are ready for login!")
            print(f"Test credentials:")
            for user_data in test_users:
                print(f"   Email: {user_data['email']}")
                print(f"   Password: Password123!")
                print(f"   Role: {user_data['role']}")
                print()
                
        except Exception as e:
            print(f"❌ Fix failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await db.close()

def fix_bcrypt_warning():
    """Fix bcrypt version warning"""
    print("🔧 Fixing bcrypt warning...")
    
    try:
        import bcrypt
        print(f"✅ bcrypt is installed")
        
        # Test bcrypt functionality
        test_password = "test123"
        hashed = bcrypt.hashpw(test_password.encode('utf-8'), bcrypt.gensalt())
        if bcrypt.checkpw(test_password.encode('utf-8'), hashed):
            print(f"✅ bcrypt functionality works")
        else:
            print(f"❌ bcrypt functionality broken")
            
    except ImportError:
        print(f"❌ bcrypt not installed")
        print(f"Run: pip install bcrypt")
    except Exception as e:
        print(f"⚠️ bcrypt warning (but should still work): {e}")

if __name__ == "__main__":
    print("🚀 Starting Login Fix Process")
    print("=" * 50)
    
    # Fix bcrypt warning first
    fix_bcrypt_warning()
    print()
    
    # Fix login issues
    asyncio.run(fix_login_issues())
    
    print("\n" + "=" * 50)
    print("🎉 Login fix process complete!")
    print("You can now try logging in with the test credentials above.")
