"""
Google Meet Integration Service
Handles Google Meet link generation and meeting management
"""
import secrets
import string
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class GoogleMeetService:
    """Service for Google Meet integration"""
    
    def __init__(self):
        self.base_url = "https://meet.google.com"
    
    def generate_meeting_link(self, meeting_type: str = "general") -> str:
        """
        Generate a Google Meet link
        In production, this would use Google Calendar API to create actual meetings
        For now, we generate realistic-looking meeting URLs
        """
        try:
            # Generate a realistic meeting ID (Google Meet format: xxx-xxxx-xxx)
            meeting_id = self._generate_meeting_id()
            meeting_url = f"{self.base_url}/{meeting_id}"
            
            logger.info(f"Generated Google Meet link: {meeting_url}")
            return meeting_url
            
        except Exception as e:
            logger.error(f"Failed to generate Google Meet link: {str(e)}")
            # Fallback to basic URL
            fallback_id = str(uuid.uuid4())[:10]
            return f"{self.base_url}/{fallback_id}"
    
    def generate_instant_meeting_link(self) -> str:
        """Generate an instant Google Meet link"""
        return self.generate_meeting_link("instant")
    
    def generate_scheduled_meeting_link(
        self, 
        title: str,
        start_time: datetime,
        duration_minutes: int = 60,
        attendees: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a scheduled Google Meet link with meeting details
        In production, this would create a Google Calendar event with Meet link
        """
        try:
            meeting_id = self._generate_meeting_id()
            meeting_url = f"{self.base_url}/{meeting_id}"
            
            meeting_details = {
                "meeting_url": meeting_url,
                "meeting_id": meeting_id,
                "title": title,
                "start_time": start_time.isoformat(),
                "end_time": (start_time + timedelta(minutes=duration_minutes)).isoformat(),
                "duration_minutes": duration_minutes,
                "attendees": attendees or [],
                "platform": "google_meet",
                "status": "scheduled",
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Generated scheduled Google Meet: {meeting_url} for '{title}'")
            return meeting_details
            
        except Exception as e:
            logger.error(f"Failed to generate scheduled Google Meet: {str(e)}")
            raise
    
    def validate_meeting_link(self, meeting_url: str) -> bool:
        """Validate if a URL is a valid Google Meet link"""
        try:
            return (
                meeting_url.startswith(self.base_url) and
                len(meeting_url) > len(self.base_url) + 5
            )
        except Exception:
            return False
    
    def extract_meeting_id(self, meeting_url: str) -> Optional[str]:
        """Extract meeting ID from Google Meet URL"""
        try:
            if not self.validate_meeting_link(meeting_url):
                return None
            
            # Extract ID from URL (everything after the base URL)
            meeting_id = meeting_url.replace(f"{self.base_url}/", "")
            return meeting_id if meeting_id else None
            
        except Exception:
            return None
    
    def get_meeting_info(self, meeting_url: str) -> Dict[str, Any]:
        """Get meeting information from URL"""
        meeting_id = self.extract_meeting_id(meeting_url)
        
        if not meeting_id:
            raise ValueError("Invalid Google Meet URL")
        
        return {
            "meeting_id": meeting_id,
            "meeting_url": meeting_url,
            "platform": "google_meet",
            "join_instructions": "Click the link to join the Google Meet",
            "browser_support": True,
            "mobile_support": True,
            "dial_in_available": False  # Would be true with actual Google Calendar integration
        }
    
    def create_meeting_with_calendar(
        self,
        title: str,
        start_time: datetime,
        duration_minutes: int,
        attendees: List[str],
        description: str = "",
        organization_domain: str = None
    ) -> Dict[str, Any]:
        """
        Create a Google Meet with Google Calendar integration
        This is a placeholder for actual Google Calendar API integration
        """
        try:
            # In production, this would:
            # 1. Use Google Calendar API to create an event
            # 2. Automatically generate a Meet link
            # 3. Send invitations to attendees
            # 4. Return the actual calendar event details
            
            meeting_details = self.generate_scheduled_meeting_link(
                title, start_time, duration_minutes, attendees
            )
            
            # Add calendar-specific details
            meeting_details.update({
                "calendar_event_id": f"cal_{uuid.uuid4().hex[:16]}",
                "calendar_link": f"https://calendar.google.com/calendar/event?eid={uuid.uuid4().hex}",
                "ics_download_url": f"/api/v1/meetings/{meeting_details['meeting_id']}/calendar.ics",
                "description": description,
                "organization_domain": organization_domain,
                "auto_recording": False,  # Would be configurable
                "waiting_room": True,
                "attendee_notifications_sent": True
            })
            
            logger.info(f"Created Google Meet with calendar integration: {meeting_details['meeting_url']}")
            return meeting_details
            
        except Exception as e:
            logger.error(f"Failed to create Google Meet with calendar: {str(e)}")
            raise
    
    def _generate_meeting_id(self) -> str:
        """Generate a realistic Google Meet meeting ID"""
        # Google Meet IDs typically follow pattern: xxx-xxxx-xxx
        part1 = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(3))
        part2 = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(4))
        part3 = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(3))
        
        return f"{part1}-{part2}-{part3}"
    
    def get_join_url_with_params(
        self, 
        meeting_url: str, 
        user_name: str = None,
        organization: str = None
    ) -> str:
        """Generate join URL with user parameters"""
        try:
            params = []
            
            if user_name:
                # URL encode the name
                encoded_name = user_name.replace(" ", "%20")
                params.append(f"usp=0&user={encoded_name}")
            
            if organization:
                encoded_org = organization.replace(" ", "%20")
                params.append(f"org={encoded_org}")
            
            if params:
                separator = "&" if "?" in meeting_url else "?"
                return f"{meeting_url}{separator}{'&'.join(params)}"
            
            return meeting_url
            
        except Exception as e:
            logger.error(f"Failed to generate join URL with params: {str(e)}")
            return meeting_url


# Global instance
google_meet_service = GoogleMeetService()


# Helper functions for backward compatibility
async def generate_meeting_url(meeting_type: str) -> str:
    """Generate meeting URL based on type"""
    return google_meet_service.generate_meeting_link(meeting_type)


async def generate_instant_meeting_url() -> str:
    """Generate instant meeting URL"""
    return google_meet_service.generate_instant_meeting_link()


def validate_google_meet_url(url: str) -> bool:
    """Validate Google Meet URL"""
    return google_meet_service.validate_meeting_link(url)


def get_meeting_join_info(meeting_url: str, user_name: str = None) -> Dict[str, Any]:
    """Get meeting join information"""
    try:
        info = google_meet_service.get_meeting_info(meeting_url)
        
        if user_name:
            info["personalized_join_url"] = google_meet_service.get_join_url_with_params(
                meeting_url, user_name
            )
        
        return info
        
    except Exception as e:
        logger.error(f"Failed to get meeting join info: {str(e)}")
        return {
            "meeting_url": meeting_url,
            "platform": "unknown",
            "error": str(e)
        }
