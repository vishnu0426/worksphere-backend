#!/usr/bin/env python3
"""
Test script for Google Meet integration functionality
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.google_meet_service import (
    GoogleMeetService, 
    google_meet_service,
    generate_meeting_url,
    generate_instant_meeting_url,
    validate_google_meet_url,
    get_meeting_join_info
)

async def test_google_meet_integration():
    """Test Google Meet integration functionality"""
    
    print("🧪 Testing Google Meet Integration...")
    print("=" * 60)
    
    # Test 1: Basic meeting link generation
    print("\n📋 Test 1: Basic Meeting Link Generation")
    try:
        meeting_link = google_meet_service.generate_meeting_link("standup")
        print(f"✅ Generated meeting link: {meeting_link}")
        
        # Validate the link format
        if meeting_link.startswith("https://meet.google.com/") and len(meeting_link) > 30:
            print("✅ Meeting link format is valid")
        else:
            print("❌ Meeting link format is invalid")
            
    except Exception as e:
        print(f"❌ Failed to generate meeting link: {str(e)}")
    
    # Test 2: Instant meeting generation
    print("\n📋 Test 2: Instant Meeting Generation")
    try:
        instant_link = google_meet_service.generate_instant_meeting_link()
        print(f"✅ Generated instant meeting link: {instant_link}")
        
        # Test async wrapper
        async_instant_link = await generate_instant_meeting_url()
        print(f"✅ Generated async instant meeting link: {async_instant_link}")
        
    except Exception as e:
        print(f"❌ Failed to generate instant meeting link: {str(e)}")
    
    # Test 3: Scheduled meeting with details
    print("\n📋 Test 3: Scheduled Meeting with Details")
    try:
        start_time = datetime.now() + timedelta(hours=1)
        attendees = ["user1@example.com", "user2@example.com"]
        
        scheduled_meeting = google_meet_service.generate_scheduled_meeting_link(
            title="Team Standup",
            start_time=start_time,
            duration_minutes=30,
            attendees=attendees
        )
        
        print(f"✅ Generated scheduled meeting:")
        print(f"   📅 Title: {scheduled_meeting['title']}")
        print(f"   🔗 URL: {scheduled_meeting['meeting_url']}")
        print(f"   ⏰ Start: {scheduled_meeting['start_time']}")
        print(f"   ⏱️  Duration: {scheduled_meeting['duration_minutes']} minutes")
        print(f"   👥 Attendees: {len(scheduled_meeting['attendees'])}")
        
    except Exception as e:
        print(f"❌ Failed to generate scheduled meeting: {str(e)}")
    
    # Test 4: Meeting link validation
    print("\n📋 Test 4: Meeting Link Validation")
    test_urls = [
        "https://meet.google.com/abc-defg-hij",
        "https://meet.google.com/invalid",
        "https://zoom.us/j/123456789",
        "https://meet.google.com/",
        "invalid-url"
    ]
    
    for url in test_urls:
        is_valid = google_meet_service.validate_meeting_link(url)
        status = "✅" if is_valid else "❌"
        print(f"   {status} {url}: {'Valid' if is_valid else 'Invalid'}")
    
    # Test 5: Meeting ID extraction
    print("\n📋 Test 5: Meeting ID Extraction")
    test_meeting_url = "https://meet.google.com/abc-defg-hij"
    meeting_id = google_meet_service.extract_meeting_id(test_meeting_url)
    if meeting_id == "abc-defg-hij":
        print(f"✅ Extracted meeting ID: {meeting_id}")
    else:
        print(f"❌ Failed to extract meeting ID. Got: {meeting_id}")
    
    # Test 6: Meeting info retrieval
    print("\n📋 Test 6: Meeting Info Retrieval")
    try:
        meeting_info = google_meet_service.get_meeting_info(test_meeting_url)
        print(f"✅ Meeting info retrieved:")
        print(f"   🆔 ID: {meeting_info['meeting_id']}")
        print(f"   🔗 URL: {meeting_info['meeting_url']}")
        print(f"   🖥️  Platform: {meeting_info['platform']}")
        print(f"   📱 Mobile Support: {meeting_info['mobile_support']}")
        
    except Exception as e:
        print(f"❌ Failed to get meeting info: {str(e)}")
    
    # Test 7: Join URL with parameters
    print("\n📋 Test 7: Join URL with Parameters")
    try:
        base_url = google_meet_service.generate_meeting_link("test")
        personalized_url = google_meet_service.get_join_url_with_params(
            base_url, 
            user_name="John Doe",
            organization="Test Org"
        )
        print(f"✅ Base URL: {base_url}")
        print(f"✅ Personalized URL: {personalized_url}")
        
    except Exception as e:
        print(f"❌ Failed to generate personalized URL: {str(e)}")
    
    # Test 8: Calendar integration (mock)
    print("\n📋 Test 8: Calendar Integration (Mock)")
    try:
        start_time = datetime.now() + timedelta(days=1)
        calendar_meeting = google_meet_service.create_meeting_with_calendar(
            title="Project Review Meeting",
            start_time=start_time,
            duration_minutes=60,
            attendees=["team@example.com"],
            description="Weekly project review and planning session",
            organization_domain="example.com"
        )
        
        print(f"✅ Calendar meeting created:")
        print(f"   📅 Title: {calendar_meeting['title']}")
        print(f"   🔗 Meet URL: {calendar_meeting['meeting_url']}")
        print(f"   📆 Calendar Event ID: {calendar_meeting['calendar_event_id']}")
        print(f"   📎 ICS Download: {calendar_meeting['ics_download_url']}")
        print(f"   🔔 Notifications Sent: {calendar_meeting['attendee_notifications_sent']}")
        
    except Exception as e:
        print(f"❌ Failed to create calendar meeting: {str(e)}")
    
    # Test 9: Different meeting types
    print("\n📋 Test 9: Different Meeting Types")
    meeting_types = ["standup", "planning", "review", "retrospective", "custom"]
    
    for meeting_type in meeting_types:
        try:
            url = await generate_meeting_url(meeting_type)
            print(f"✅ {meeting_type.capitalize()}: {url}")
        except Exception as e:
            print(f"❌ {meeting_type.capitalize()}: Failed - {str(e)}")
    
    # Test 10: Helper function compatibility
    print("\n📋 Test 10: Helper Function Compatibility")
    try:
        # Test the helper functions used by the existing codebase
        test_url = "https://meet.google.com/test-meet-ing"
        
        is_valid = validate_google_meet_url(test_url)
        print(f"✅ URL validation helper: {is_valid}")
        
        join_info = get_meeting_join_info(test_url, "Test User")
        print(f"✅ Join info helper: {join_info.get('platform', 'unknown')}")
        
        if 'personalized_join_url' in join_info:
            print(f"✅ Personalized join URL: {join_info['personalized_join_url']}")
        
    except Exception as e:
        print(f"❌ Helper function test failed: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🎯 Google Meet Integration Test Completed!")
    print("📝 Note: This is using mock Google Meet URLs.")
    print("📝 For production, integrate with Google Calendar API for real meetings.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_google_meet_integration())
