#!/usr/bin/env python3
"""
Test script for role-based redirection after invitation acceptance
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.invitation_service import InvitationService
from app.models.organization_settings import InvitationToken
from app.models.organization import Organization, OrganizationMember
from app.models.user import User
from app.core.security import hash_password
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

async def test_role_based_redirection():
    """Test that invitation acceptance returns correct redirect URLs for different roles"""
    
    print("🧪 Testing role-based redirection after invitation acceptance...")
    
    # Get database session
    async for db in get_db():
        try:
            service = InvitationService(db)
            
            # Test data
            test_org_id = str(uuid.uuid4())
            test_user_email = "test@example.com"
            test_inviter_id = str(uuid.uuid4())
            
            # Create test organization
            test_org = Organization(
                id=test_org_id,
                name="Test Organization",
                description="Test organization for role redirection",
                contact_email="admin@test.com"
            )
            db.add(test_org)
            
            # Create test inviter user
            test_inviter = User(
                id=test_inviter_id,
                email="inviter@test.com",
                first_name="Test",
                last_name="Inviter",
                password_hash=hash_password("password123")
            )
            db.add(test_inviter)
            
            await db.commit()
            
            # Test different roles and their expected redirect URLs
            test_cases = [
                ("owner", "/dashboard/owner"),
                ("admin", "/dashboard/admin"),
                ("member", "/dashboard/member"),
                ("viewer", "/dashboard/viewer")
            ]
            
            for role, expected_redirect in test_cases:
                print(f"\n📋 Testing role: {role}")
                
                # Create invitation token
                token = f"test_token_{role}_{uuid.uuid4().hex[:8]}"
                temp_password = "temp123"
                
                invitation = InvitationToken(
                    token=token,
                    email=test_user_email,
                    organization_id=test_org_id,
                    invited_role=role,
                    temporary_password=hash_password(temp_password),
                    invited_by=test_inviter_id,
                    expires_at=datetime.utcnow() + timedelta(hours=48)
                )
                
                db.add(invitation)
                await db.commit()
                
                try:
                    # Test invitation acceptance
                    result = await service.accept_invitation(
                        token=token,
                        temp_password=temp_password,
                        new_password="newpassword123",
                        first_name="Test",
                        last_name="User",
                        ip_address="127.0.0.1",
                        user_agent="Test Agent"
                    )
                    
                    # Verify redirect URL
                    actual_redirect = result.get('redirect_url')
                    if actual_redirect == expected_redirect:
                        print(f"✅ {role.upper()}: Correct redirect URL: {actual_redirect}")
                    else:
                        print(f"❌ {role.upper()}: Expected {expected_redirect}, got {actual_redirect}")
                    
                    # Verify other response fields
                    required_fields = ['user_id', 'email', 'organization_id', 'role', 'session', 'organization']
                    for field in required_fields:
                        if field in result:
                            print(f"✅ {role.upper()}: Has {field}")
                        else:
                            print(f"❌ {role.upper()}: Missing {field}")
                    
                    # Clean up - remove the created user for next test
                    if 'user_id' in result:
                        user_result = await db.execute(
                            f"DELETE FROM users WHERE id = '{result['user_id']}'"
                        )
                        await db.execute(
                            f"DELETE FROM organization_members WHERE user_id = '{result['user_id']}'"
                        )
                        await db.commit()
                
                except Exception as e:
                    print(f"❌ {role.upper()}: Error during acceptance: {str(e)}")
                
                # Clean up invitation
                await db.execute(f"DELETE FROM invitation_tokens WHERE token = '{token}'")
                await db.commit()
            
            print("\n🎯 Role-based redirection test completed!")
            
        except Exception as e:
            print(f"❌ Test failed with error: {str(e)}")
            await db.rollback()
        finally:
            # Clean up test data
            try:
                await db.execute(f"DELETE FROM organizations WHERE id = '{test_org_id}'")
                await db.execute(f"DELETE FROM users WHERE id = '{test_inviter_id}'")
                await db.commit()
            except:
                pass
            await db.close()
        break

if __name__ == "__main__":
    asyncio.run(test_role_based_redirection())
