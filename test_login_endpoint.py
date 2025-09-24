#!/usr/bin/env python3
"""
Test the login endpoint directly
"""

import asyncio
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import get_db
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.core.security import verify_password, create_access_token
from sqlalchemy import select

async def test_login_endpoint():
    """Test the login endpoint with our test users"""
    print("🧪 Testing Login Endpoint")
    print("=" * 30)
    
    test_credentials = [
        {"email": "admin@test.com", "password": "Password123!", "role": "admin"},
        {"email": "member@test.com", "password": "Password123!", "role": "member"},
        {"email": "viewer@test.com", "password": "Password123!", "role": "viewer"},
    ]
    
    async for db in get_db():
        try:
            for creds in test_credentials:
                print(f"\n--- Testing {creds['email']} ---")

                try:
                    # Find user by email
                    result = await db.execute(select(User).where(User.email == creds["email"]))
                    user = result.scalar_one_or_none()

                    if not user:
                        print(f"❌ User not found: {creds['email']}")
                        continue

                    print(f"✅ User found: {user.first_name} {user.last_name}")

                    # Test password verification
                    if not verify_password(creds["password"], user.password_hash):
                        print(f"❌ Password verification failed")
                        continue

                    print(f"✅ Password verification successful")

                    # Get organization membership
                    org_result = await db.execute(
                        select(OrganizationMember, Organization)
                        .join(Organization, OrganizationMember.organization_id == Organization.id)
                        .where(OrganizationMember.user_id == user.id)
                    )
                    org_data = org_result.first()

                    if org_data:
                        org_member, organization = org_data
                        print(f"✅ Organization: {organization.name}")
                        print(f"✅ Role: {org_member.role}")
                    else:
                        print(f"❌ No organization membership found")

                    # Test token creation
                    token_data = {"sub": str(user.id), "email": user.email}
                    access_token = create_access_token(token_data)
                    print(f"✅ Token created: {access_token[:20]}...")

                    print(f"✅ Login test successful for {creds['email']}")

                except Exception as e:
                    print(f"❌ Login test failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            print(f"\n🎉 Login endpoint testing complete!")
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await db.close()

if __name__ == "__main__":
    asyncio.run(test_login_endpoint())
