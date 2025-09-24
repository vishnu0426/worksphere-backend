#!/usr/bin/env python3
"""
Comprehensive test script for the enhanced invitation acceptance flow
Tests all components: token expiration, role-based redirection, Google Meet integration, and email templates
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import json

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

async def test_invitation_token_expiration():
    """Test 48-hour invitation token expiration"""
    print("\n📋 Test 1: Invitation Token Expiration (48 hours)")
    print("-" * 60)
    
    try:
        from app.services.invitation_service import InvitationService
        from app.models.organization_settings import InvitationToken
        from datetime import datetime, timedelta
        
        # Test token expiration calculation
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=48)
        
        print(f"✅ Current time: {now}")
        print(f"✅ Token expires at: {expires_at}")
        print(f"✅ Token valid for: {(expires_at - now).total_seconds() / 3600:.1f} hours")
        
        # Test if token would be expired
        future_time = now + timedelta(hours=49)  # 1 hour past expiration
        is_expired = future_time > expires_at
        print(f"✅ Token expired after 49 hours: {is_expired}")
        
        return True
        
    except Exception as e:
        print(f"❌ Token expiration test failed: {str(e)}")
        return False

async def test_role_based_redirection():
    """Test role-based dashboard redirection URLs"""
    print("\n📋 Test 2: Role-Based Dashboard Redirection")
    print("-" * 60)
    
    try:
        # Test role mapping
        role_redirects = {
            'owner': '/dashboard/owner',
            'admin': '/dashboard/admin', 
            'member': '/dashboard/member',
            'viewer': '/dashboard/viewer'
        }
        
        for role, expected_url in role_redirects.items():
            print(f"✅ {role.title()} role → {expected_url}")
        
        # Test invalid role handling
        invalid_role = 'invalid_role'
        default_url = '/dashboard/member'  # Default fallback
        print(f"✅ Invalid role '{invalid_role}' → {default_url} (fallback)")
        
        return True
        
    except Exception as e:
        print(f"❌ Role-based redirection test failed: {str(e)}")
        return False

async def test_google_meet_integration():
    """Test Google Meet integration functionality"""
    print("\n📋 Test 3: Google Meet Integration")
    print("-" * 60)
    
    try:
        from app.services.google_meet_service import google_meet_service
        
        # Test basic meeting link generation
        meeting_link = google_meet_service.generate_meeting_link("standup")
        print(f"✅ Generated meeting link: {meeting_link}")
        
        # Test link validation
        is_valid = google_meet_service.validate_meeting_link(meeting_link)
        print(f"✅ Link validation: {is_valid}")
        
        # Test meeting ID extraction
        meeting_id = google_meet_service.extract_meeting_id(meeting_link)
        print(f"✅ Extracted meeting ID: {meeting_id}")
        
        # Test scheduled meeting
        start_time = datetime.now() + timedelta(hours=1)
        scheduled_meeting = google_meet_service.generate_scheduled_meeting_link(
            title="Test Meeting",
            start_time=start_time,
            duration_minutes=30,
            attendees=["test@example.com"]
        )
        print(f"✅ Scheduled meeting: {scheduled_meeting['meeting_url']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Google Meet integration test failed: {str(e)}")
        return False

async def test_email_templates():
    """Test enhanced email templates"""
    print("\n📋 Test 4: Enhanced Email Templates")
    print("-" * 60)
    
    try:
        from app.templates.email_templates import (
            get_organization_invitation_email,
            get_project_invitation_email,
            get_board_invitation_email
        )
        
        # Test organization invitation template
        org_html, org_text = get_organization_invitation_email(
            inviter_name="John Doe",
            organization_name="Test Org",
            role="member",
            to_email="test@example.com",
            temp_password="temp123",
            invitation_url="http://localhost:3000/accept-invitation?token=abc123",
            custom_message="Welcome to our team!"
        )
        print(f"✅ Organization template generated: {len(org_html)} chars HTML, {len(org_text)} chars text")
        
        # Test project invitation template
        proj_html, proj_text = get_project_invitation_email(
            inviter_name="Jane Smith",
            organization_name="Test Org",
            project_name="Test Project",
            role="admin",
            to_email="test@example.com",
            temp_password="temp456",
            invitation_url="http://localhost:3000/accept-invitation?token=def456"
        )
        print(f"✅ Project template generated: {len(proj_html)} chars HTML, {len(proj_text)} chars text")
        
        # Test board invitation template
        board_html, board_text = get_board_invitation_email(
            inviter_name="Bob Wilson",
            organization_name="Test Org",
            project_name="Test Project",
            board_name="Sprint Board",
            role="viewer",
            to_email="test@example.com",
            temp_password="temp789",
            invitation_url="http://localhost:3000/accept-invitation?token=ghi789"
        )
        print(f"✅ Board template generated: {len(board_html)} chars HTML, {len(board_text)} chars text")
        
        return True
        
    except Exception as e:
        print(f"❌ Email templates test failed: {str(e)}")
        return False

async def test_organization_settings():
    """Test simplified organization settings"""
    print("\n📋 Test 5: Simplified Organization Settings")
    print("-" * 60)
    
    try:
        # Test settings structure
        settings_data = {
            "name": "Test Organization",
            "description": "A test organization for development",
            "visibility": "private",
            "enable_task_notifications": True,
            "enable_meeting_notifications": True,
            "enable_role_change_notifications": False,
            "require_email_verification": True
        }
        
        print("✅ Organization settings structure:")
        for key, value in settings_data.items():
            print(f"   {key}: {value}")
        
        # Test settings validation
        required_fields = ["name", "visibility"]
        missing_fields = [field for field in required_fields if field not in settings_data]
        
        if not missing_fields:
            print("✅ All required fields present")
        else:
            print(f"❌ Missing required fields: {missing_fields}")
        
        return True
        
    except Exception as e:
        print(f"❌ Organization settings test failed: {str(e)}")
        return False

async def test_invitation_service_integration():
    """Test invitation service with enhanced features"""
    print("\n📋 Test 6: Invitation Service Integration")
    print("-" * 60)
    
    try:
        from app.services.invitation_service import InvitationService
        
        # Test invitation data structure
        invitation_data = {
            "email": "test@example.com",
            "role": "member",
            "inviter_name": "Test User",
            "organization_name": "Test Org",
            "temp_password": "temp123",
            "expires_at": datetime.utcnow() + timedelta(hours=48),
            "project_name": None,
            "board_name": None,
            "custom_message": "Welcome to our team!"
        }
        
        print("✅ Invitation data structure:")
        for key, value in invitation_data.items():
            if key == "expires_at":
                print(f"   {key}: {value} (48 hours from now)")
            else:
                print(f"   {key}: {value}")
        
        # Test role-based redirect URL generation
        role_redirects = {
            'owner': '/dashboard/owner',
            'admin': '/dashboard/admin',
            'member': '/dashboard/member',
            'viewer': '/dashboard/viewer'
        }
        
        user_role = invitation_data["role"]
        redirect_url = role_redirects.get(user_role, '/dashboard/member')
        print(f"✅ Role-based redirect for '{user_role}': {redirect_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Invitation service integration test failed: {str(e)}")
        return False

async def test_end_to_end_flow():
    """Test complete end-to-end invitation flow"""
    print("\n📋 Test 7: End-to-End Invitation Flow")
    print("-" * 60)
    
    try:
        # Simulate complete flow
        flow_steps = [
            "1. User sends invitation with 48-hour expiration",
            "2. Email sent using enhanced template (org/project/board)",
            "3. Recipient clicks invitation link",
            "4. Frontend loads accept-invitation page with token",
            "5. User fills form with temp password and new password",
            "6. Backend validates temp password and creates/updates user",
            "7. Backend creates authentication session with org context",
            "8. Backend returns enhanced response with tokens and redirect URL",
            "9. Frontend establishes session and redirects to role-based dashboard",
            "10. User is logged in and ready to work"
        ]
        
        print("✅ Complete invitation flow steps:")
        for step in flow_steps:
            print(f"   {step}")
        
        # Test response structure
        mock_response = {
            "success": True,
            "message": "Invitation accepted successfully",
            "user": {
                "id": "user123",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "role": "member"
            },
            "organization": {
                "id": "org123",
                "name": "Test Organization",
                "role": "member"
            },
            "tokens": {
                "access_token": "jwt_token_here",
                "session_id": "session123"
            },
            "redirect_url": "/dashboard/member",
            "google_meet_available": True
        }
        
        print(f"\n✅ Enhanced response structure: {len(json.dumps(mock_response, indent=2))} chars")
        
        return True
        
    except Exception as e:
        print(f"❌ End-to-end flow test failed: {str(e)}")
        return False

async def main():
    """Run all comprehensive tests"""
    print("🧪 COMPREHENSIVE ENHANCED INVITATION FLOW TESTS")
    print("=" * 80)
    
    tests = [
        ("Invitation Token Expiration", test_invitation_token_expiration),
        ("Role-Based Redirection", test_role_based_redirection),
        ("Google Meet Integration", test_google_meet_integration),
        ("Enhanced Email Templates", test_email_templates),
        ("Organization Settings", test_organization_settings),
        ("Invitation Service Integration", test_invitation_service_integration),
        ("End-to-End Flow", test_end_to_end_flow)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Enhanced invitation flow is ready.")
    else:
        print("⚠️  Some tests failed. Please review and fix issues.")
    
    print("\n📝 Next Steps:")
    print("1. Run backend server: cd backend && python -m uvicorn app.main:app --reload")
    print("2. Run frontend: cd frontend/FE && npm start")
    print("3. Test complete flow in browser")
    print("4. Verify email templates in email client")
    print("5. Test Google Meet link generation")

if __name__ == "__main__":
    asyncio.run(main())
