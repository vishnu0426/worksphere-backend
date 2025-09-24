"""
Dashboard Data Service - Ensures users have initial notifications and activities
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.notification import Notification
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.models.organization import OrganizationMember


class DashboardDataService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_user_has_initial_data(self, user_id: str, organization_id: str = None):
        """
        Ensure user has some initial notifications and activities for better UX
        Only creates data if user has no existing notifications
        """
        try:
            # Check if user already has notifications
            existing_notifications = await self.db.execute(
                select(func.count(Notification.id)).where(Notification.user_id == user_id)
            )
            notification_count = existing_notifications.scalar()

            # If user has no notifications, create welcome notifications
            if notification_count == 0:
                await self._create_welcome_notifications(user_id, organization_id)

            # Check if organization has any activities
            if organization_id:
                existing_activities = await self.db.execute(
                    select(func.count(ActivityLog.id)).where(ActivityLog.organization_id == organization_id)
                )
                activity_count = existing_activities.scalar()

                # If organization has no activities, create initial activities
                if activity_count == 0:
                    await self._create_initial_activities(user_id, organization_id)

            await self.db.commit()
            return True

        except Exception as e:
            print(f"Error ensuring initial data: {e}")
            await self.db.rollback()
            return False

    async def _create_welcome_notifications(self, user_id: str, organization_id: str = None):
        """Create welcome notifications for new users"""
        notifications = [
            {
                "title": "Welcome to Agno WorkSphere!",
                "message": "Your account has been successfully created. Start by exploring your dashboard and creating your first project.",
                "type": "welcome",
                "priority": "high"
            },
            {
                "title": "Complete Your Profile",
                "message": "Add your profile information to help your team members get to know you better.",
                "type": "profile_update",
                "priority": "medium"
            },
            {
                "title": "Invite Team Members",
                "message": "Collaborate better by inviting your team members to join your organization.",
                "type": "team_invitation",
                "priority": "medium"
            }
        ]

        for notif_data in notifications:
            notification = Notification(
                user_id=user_id,
                title=notif_data["title"],
                message=notif_data["message"],
                type=notif_data["type"],
                priority=notif_data["priority"],
                read=False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(notification)

    async def _create_initial_activities(self, user_id: str, organization_id: str):
        """Create initial activities for new organizations"""
        # Get user info for activities
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            return

        activities = [
            {
                "action_type": "organization_created",
                "description": "Organization was created and set up successfully",
                "entity_type": "organization",
                "entity_name": "Organization Setup"
            },
            {
                "action_type": "user_joined",
                "description": f"{user.first_name} {user.last_name} joined the organization".strip() or f"{user.email.split('@')[0]} joined the organization",
                "entity_type": "user",
                "entity_name": "Team Management"
            },
            {
                "action_type": "dashboard_accessed",
                "description": "Dashboard was accessed for the first time",
                "entity_type": "system",
                "entity_name": "System Activity"
            }
        ]

        for activity_data in activities:
            activity = ActivityLog(
                user_id=user_id,
                organization_id=organization_id,
                action_type=activity_data["action_type"],
                description=activity_data["description"],
                entity_type=activity_data["entity_type"],
                entity_name=activity_data["entity_name"],
                created_at=datetime.now() - timedelta(minutes=len(activities) * 10)  # Spread activities over time
            )
            self.db.add(activity)

    async def create_activity_log(self, user_id: str, organization_id: str, action_type: str, description: str, entity_type: str = None, entity_name: str = None):
        """Create a new activity log entry"""
        try:
            activity = ActivityLog(
                user_id=user_id,
                organization_id=organization_id,
                action_type=action_type,
                description=description,
                entity_type=entity_type,
                entity_name=entity_name,
                created_at=datetime.now()
            )
            self.db.add(activity)
            await self.db.commit()
            return activity
        except Exception as e:
            print(f"Error creating activity log: {e}")
            await self.db.rollback()
            return None

    async def create_notification(self, user_id: str, title: str, message: str, notification_type: str = "info", priority: str = "medium"):
        """Create a new notification"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                priority=priority,
                read=False,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.db.add(notification)
            await self.db.commit()
            return notification
        except Exception as e:
            print(f"Error creating notification: {e}")
            await self.db.rollback()
            return None
