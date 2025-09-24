"""
In-App Only Notification Service
Comprehensive in-app notification system with role-based access control
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import uuid

from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.project import Project
from app.models.card import Card
from app.models.notification import Notification
from app.core.exceptions import ValidationError


class InAppNotificationService:
    """Service for managing in-app only notifications with role-based access control"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_in_app_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        category: str,
        priority: str = "normal",
        action_buttons: Optional[List[Dict[str, str]]] = None,
        organization_id: Optional[str] = None,
        action_url: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Notification:
        """Create a generic in-app notification"""
        
        # Prepare metadata with action buttons
        metadata = {}
        if action_buttons:
            metadata["action_buttons"] = action_buttons
        
        notification = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            organization_id=organization_id,
            title=title,
            message=message,
            type=category,
            priority=priority,
            action_url=action_url,
            notification_metadata=metadata,
            expires_at=expires_at
        )
        
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        
        return notification
    
    async def send_welcome_notification(
        self,
        user_id: str,
        organization_name: str,
        user_name: str,
        organization_id: str
    ) -> Notification:
        """Send welcome notification for new users"""
        
        action_buttons = [
            {"label": "Get Started", "action": "tour", "variant": "primary"},
            {"label": "View Profile", "action": "profile", "variant": "secondary"}
        ]
        
        title = f"Welcome to {organization_name}!"
        message = f"Hi {user_name}! Welcome to your new workspace. Start by exploring your dashboard and setting up your first project."
        
        return await self.create_in_app_notification(
            user_id=user_id,
            title=title,
            message=message,
            category="welcome",
            priority="high",
            action_buttons=action_buttons,
            organization_id=organization_id,
            action_url="/role-based-dashboard"
        )
    
    async def send_task_assignment_notification(
        self,
        user_id: str,
        task_title: str,
        task_id: str,
        project_name: str,
        assigned_by: str,
        organization_id: str
    ) -> Notification:
        """Send task assignment notification"""
        
        # Get assigner name
        assigner_result = await self.db.execute(
            select(User).where(User.id == assigned_by)
        )
        assigner = assigner_result.scalar_one_or_none()
        assigner_name = assigner.full_name if assigner else "Someone"
        
        action_buttons = [
            {"label": "View Task", "action": "view_task", "variant": "primary"},
            {"label": "Accept", "action": "accept_task", "variant": "success"},
            {"label": "Request Changes", "action": "request_changes", "variant": "secondary"}
        ]
        
        title = "New Task Assigned"
        message = f"{assigner_name} assigned you the task '{task_title}' in project '{project_name}'"
        
        return await self.create_in_app_notification(
            user_id=user_id,
            title=title,
            message=message,
            category="task_assigned",
            priority="high",
            action_buttons=action_buttons,
            organization_id=organization_id,
            action_url=f"/tasks/{task_id}"
        )
    
    async def send_task_reminder_notification(
        self,
        user_id: str,
        task_title: str,
        task_id: str,
        due_date: datetime,
        organization_id: str
    ) -> Notification:
        """Send task deadline reminder notification"""
        
        # Calculate time until due
        time_diff = due_date - datetime.utcnow()
        if time_diff.total_seconds() <= 3600:  # 1 hour
            urgency = "due in 1 hour"
            priority = "urgent"
        elif time_diff.days <= 1:  # 24 hours
            urgency = "due in 24 hours"
            priority = "high"
        else:
            urgency = f"due in {time_diff.days} days"
            priority = "normal"
        
        action_buttons = [
            {"label": "View Task", "action": "view_task", "variant": "primary"},
            {"label": "Mark Complete", "action": "complete_task", "variant": "success"},
            {"label": "Request Extension", "action": "request_extension", "variant": "secondary"}
        ]
        
        title = f"Task Deadline Reminder"
        message = f"Task '{task_title}' is {urgency}"
        
        return await self.create_in_app_notification(
            user_id=user_id,
            title=title,
            message=message,
            category="task_reminder",
            priority=priority,
            action_buttons=action_buttons,
            organization_id=organization_id,
            action_url=f"/tasks/{task_id}"
        )
    
    async def send_task_status_update_notification(
        self,
        user_id: str,
        task_title: str,
        task_id: str,
        old_status: str,
        new_status: str,
        updated_by: str,
        organization_id: str
    ) -> Notification:
        """Send task status update notification"""
        
        # Get updater name
        updater_result = await self.db.execute(
            select(User).where(User.id == updated_by)
        )
        updater = updater_result.scalar_one_or_none()
        updater_name = updater.full_name if updater else "Someone"
        
        action_buttons = [
            {"label": "View Task", "action": "view_task", "variant": "primary"},
            {"label": "View Changes", "action": "view_changes", "variant": "secondary"}
        ]
        
        title = "Task Status Updated"
        message = f"{updater_name} changed task '{task_title}' status from '{old_status}' to '{new_status}'"
        
        # Set priority based on status change
        priority = "high" if new_status.lower() == "complete" else "normal"
        
        return await self.create_in_app_notification(
            user_id=user_id,
            title=title,
            message=message,
            category="task_updated",
            priority=priority,
            action_buttons=action_buttons,
            organization_id=organization_id,
            action_url=f"/tasks/{task_id}"
        )
    
    async def send_project_update_notification_in_app(
        self,
        user_id: str,
        project_name: str,
        project_id: str,
        update_message: str,
        updated_by: str,
        organization_id: str
    ) -> Notification:
        """Send project update notification"""
        
        # Get updater name
        updater_result = await self.db.execute(
            select(User).where(User.id == updated_by)
        )
        updater = updater_result.scalar_one_or_none()
        updater_name = updater.full_name if updater else "Someone"
        
        action_buttons = [
            {"label": "View Project", "action": "view_project", "variant": "primary"},
            {"label": "View Changes", "action": "view_changes", "variant": "secondary"},
            {"label": "View Team", "action": "view_team", "variant": "secondary"}
        ]
        
        title = f"Project Update: {project_name}"
        message = f"{updater_name} updated project '{project_name}': {update_message}"
        
        return await self.create_in_app_notification(
            user_id=user_id,
            title=title,
            message=message,
            category="project_update",
            priority="normal",
            action_buttons=action_buttons,
            organization_id=organization_id,
            action_url=f"/projects/{project_id}"
        )
    
    async def send_project_milestone_notification(
        self,
        user_id: str,
        project_name: str,
        project_id: str,
        milestone_name: str,
        organization_id: str
    ) -> Notification:
        """Send project milestone notification"""
        
        action_buttons = [
            {"label": "View Project", "action": "view_project", "variant": "primary"},
            {"label": "View Milestone", "action": "view_milestone", "variant": "secondary"}
        ]
        
        title = f"Milestone Reached!"
        message = f"Project '{project_name}' has reached milestone: {milestone_name}"
        
        return await self.create_in_app_notification(
            user_id=user_id,
            title=title,
            message=message,
            category="project_milestone",
            priority="high",
            action_buttons=action_buttons,
            organization_id=organization_id,
            action_url=f"/projects/{project_id}"
        )
    
    async def send_team_member_added_notification(
        self,
        user_id: str,
        project_name: str,
        project_id: str,
        new_member_name: str,
        added_by: str,
        organization_id: str
    ) -> Notification:
        """Send team member added notification"""
        
        # Get adder name
        adder_result = await self.db.execute(
            select(User).where(User.id == added_by)
        )
        adder = adder_result.scalar_one_or_none()
        adder_name = adder.full_name if adder else "Someone"
        
        action_buttons = [
            {"label": "View Project", "action": "view_project", "variant": "primary"},
            {"label": "View Team", "action": "view_team", "variant": "secondary"}
        ]
        
        title = "New Team Member Added"
        message = f"{adder_name} added {new_member_name} to project '{project_name}'"
        
        return await self.create_in_app_notification(
            user_id=user_id,
            title=title,
            message=message,
            category="team_member_added",
            priority="normal",
            action_buttons=action_buttons,
            organization_id=organization_id,
            action_url=f"/projects/{project_id}/team"
        )

    async def send_system_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        priority: str = "normal",
        organization_id: Optional[str] = None,
        action_url: Optional[str] = None
    ) -> Notification:
        """Send system notification (maintenance, updates, announcements)"""

        action_buttons = [
            {"label": "View Details", "action": "view_details", "variant": "primary"},
            {"label": "Dismiss", "action": "dismiss", "variant": "secondary"}
        ]

        return await self.create_in_app_notification(
            user_id=user_id,
            title=title,
            message=message,
            category="system",
            priority=priority,
            action_buttons=action_buttons,
            organization_id=organization_id,
            action_url=action_url
        )

    async def get_user_role_in_organization(self, user_id: str, organization_id: str) -> Optional[str]:
        """Get user's role in organization for role-based notifications"""

        result = await self.db.execute(
            select(OrganizationMember.role)
            .where(
                and_(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.organization_id == organization_id
                )
            )
        )
        member = result.scalar_one_or_none()
        return member if member else None

    async def get_users_by_role(self, organization_id: str, roles: List[str]) -> List[str]:
        """Get all users with specific roles in organization"""

        result = await self.db.execute(
            select(OrganizationMember.user_id)
            .where(
                and_(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.role.in_(roles)
                )
            )
        )
        return [str(row[0]) for row in result.fetchall()]

    async def send_role_based_notification(
        self,
        organization_id: str,
        target_roles: List[str],
        title: str,
        message: str,
        category: str,
        priority: str = "normal",
        action_buttons: Optional[List[Dict[str, str]]] = None,
        action_url: Optional[str] = None
    ) -> List[Notification]:
        """Send notifications to users with specific roles"""

        # Get users with target roles
        user_ids = await self.get_users_by_role(organization_id, target_roles)

        notifications = []
        for user_id in user_ids:
            notification = await self.create_in_app_notification(
                user_id=user_id,
                title=title,
                message=message,
                category=category,
                priority=priority,
                action_buttons=action_buttons,
                organization_id=organization_id,
                action_url=action_url
            )
            notifications.append(notification)

        return notifications

    async def send_organization_wide_notification(
        self,
        organization_id: str,
        title: str,
        message: str,
        category: str,
        priority: str = "normal",
        action_buttons: Optional[List[Dict[str, str]]] = None,
        action_url: Optional[str] = None,
        exclude_roles: Optional[List[str]] = None
    ) -> List[Notification]:
        """Send notification to all organization members (with optional role exclusions)"""

        # Get all organization members
        query = select(OrganizationMember.user_id).where(
            OrganizationMember.organization_id == organization_id
        )

        if exclude_roles:
            query = query.where(~OrganizationMember.role.in_(exclude_roles))

        result = await self.db.execute(query)
        user_ids = [str(row[0]) for row in result.fetchall()]

        notifications = []
        for user_id in user_ids:
            notification = await self.create_in_app_notification(
                user_id=user_id,
                title=title,
                message=message,
                category=category,
                priority=priority,
                action_buttons=action_buttons,
                organization_id=organization_id,
                action_url=action_url
            )
            notifications.append(notification)

        return notifications

    async def mark_notification_as_read(self, notification_id: str, user_id: str) -> bool:
        """Mark a notification as read (with user verification)"""

        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            return False

        notification.read = True
        notification.read_at = datetime.utcnow()
        await self.db.commit()

        return True

    async def mark_all_notifications_as_read(self, user_id: str, organization_id: Optional[str] = None) -> int:
        """Mark all notifications as read for a user"""

        query = select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.read == False
            )
        )

        if organization_id:
            query = query.where(Notification.organization_id == organization_id)

        result = await self.db.execute(query)
        notifications = result.scalars().all()

        count = 0
        for notification in notifications:
            notification.read = True
            notification.read_at = datetime.utcnow()
            count += 1

        await self.db.commit()
        return count

    async def get_user_notifications(
        self,
        user_id: str,
        organization_id: Optional[str] = None,
        unread_only: bool = False,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Notification]:
        """Get notifications for a user with filtering options"""

        query = select(Notification).where(Notification.user_id == user_id)

        if organization_id:
            query = query.where(Notification.organization_id == organization_id)

        if unread_only:
            query = query.where(Notification.read == False)

        if category:
            query = query.where(Notification.type == category)

        # Filter out expired notifications
        query = query.where(
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > datetime.utcnow()
            )
        )

        query = query.order_by(Notification.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_unread_count(self, user_id: str, organization_id: Optional[str] = None) -> int:
        """Get count of unread notifications for a user"""

        query = select(func.count(Notification.id)).where(
            and_(
                Notification.user_id == user_id,
                Notification.read == False
            )
        )

        if organization_id:
            query = query.where(Notification.organization_id == organization_id)

        # Filter out expired notifications
        query = query.where(
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > datetime.utcnow()
            )
        )

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification (with user verification)"""

        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id
                )
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            return False

        await self.db.delete(notification)
        await self.db.commit()

        return True

    async def cleanup_expired_notifications(self) -> int:
        """Clean up expired notifications (system maintenance task)"""

        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.expires_at.is_not(None),
                    Notification.expires_at <= datetime.utcnow()
                )
            )
        )
        expired_notifications = result.scalars().all()

        count = 0
        for notification in expired_notifications:
            await self.db.delete(notification)
            count += 1

        await self.db.commit()
        return count

    async def batch_create_notifications(self, notifications_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple notifications in a single batch operation"""
        try:
            notifications = []
            for data in notifications_data:
                notification = Notification(
                    id=str(uuid.uuid4()),
                    user_id=data["user_id"],
                    title=data["title"],
                    message=data["message"],
                    category=data.get("category", "general"),
                    priority=data.get("priority", "normal"),
                    read=False,
                    delivery_channel="in_app",
                    action_buttons=data.get("action_buttons", []),
                    metadata=data.get("metadata", {}),
                    organization_id=data.get("organization_id"),
                    created_at=datetime.utcnow()
                )
                notifications.append(notification)

            self.db.add_all(notifications)
            await self.db.commit()

            return {
                "success": True,
                "created_count": len(notifications),
                "notification_ids": [n.id for n in notifications]
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to batch create notifications: {str(e)}")
            return {"success": False, "error": str(e)}

    async def batch_mark_as_read(self, notification_ids: List[str], user_id: str) -> Dict[str, Any]:
        """Mark multiple notifications as read in a single operation"""
        try:
            updated_count = await self.db.execute(
                update(Notification)
                .where(
                    and_(
                        Notification.id.in_(notification_ids),
                        Notification.user_id == user_id,
                        Notification.read == False
                    )
                )
                .values(read=True, read_at=datetime.utcnow())
            )
            await self.db.commit()

            return {
                "success": True,
                "updated_count": updated_count.rowcount
            }

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to batch mark notifications as read: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_notification_statistics(self, organization_id: str = None) -> Dict[str, Any]:
        """Get notification statistics for performance monitoring"""
        try:
            base_query = select(Notification)
            if organization_id:
                base_query = base_query.where(Notification.organization_id == organization_id)

            # Total notifications
            total_count = await self.db.scalar(
                select(func.count()).select_from(base_query.subquery())
            )

            # Unread notifications
            unread_count = await self.db.scalar(
                select(func.count()).select_from(
                    base_query.where(Notification.read == False).subquery()
                )
            )

            # Notifications by priority
            priority_stats = await self.db.execute(
                select(Notification.priority, func.count())
                .select_from(base_query.subquery())
                .group_by(Notification.priority)
            )

            # Notifications by category
            category_stats = await self.db.execute(
                select(Notification.category, func.count())
                .select_from(base_query.subquery())
                .group_by(Notification.category)
            )

            return {
                "success": True,
                "statistics": {
                    "total_notifications": total_count,
                    "unread_notifications": unread_count,
                    "read_percentage": ((total_count - unread_count) / total_count * 100) if total_count > 0 else 0,
                    "priority_breakdown": dict(priority_stats.fetchall()),
                    "category_breakdown": dict(category_stats.fetchall())
                }
            }

        except Exception as e:
            logger.error(f"Failed to get notification statistics: {str(e)}")
            return {"success": False, "error": str(e)}
