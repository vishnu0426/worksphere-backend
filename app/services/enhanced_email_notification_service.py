"""
Enhanced notification service that sends both in-app and email notifications
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.card import Card
from app.models.project import Project
from app.models.ai_automation import SmartNotification
from app.services.email_service import email_service
from app.services.in_app_notification_service import InAppNotificationService

logger = logging.getLogger(__name__)

class EnhancedEmailNotificationService:
    """Service for sending both in-app and email notifications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.in_app_service = InAppNotificationService(db)
    
    async def send_task_assignment_notification(
        self,
        user_id: str,
        task_id: str,
        task_title: str,
        task_description: str,
        assigner_id: str,
        project_name: str,
        organization_id: str,
        due_date: Optional[datetime] = None,
        priority: str = "medium"
    ) -> bool:
        """Send both in-app and email notifications for task assignment"""
        try:
            # Get user email and assigner details
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            assigner_result = await self.db.execute(
                select(User).where(User.id == assigner_id)
            )
            assigner = assigner_result.scalar_one_or_none()
            
            if not user or not assigner:
                logger.error(f"User or assigner not found: user_id={user_id}, assigner_id={assigner_id}")
                return False
            
            assigner_name = f"{assigner.first_name} {assigner.last_name}"
            
            # Send in-app notification
            await self.in_app_service.send_task_assignment_notification(
                user_id=user_id,
                task_title=task_title,
                task_id=task_id,
                project_name=project_name,
                assigned_by=assigner_id,
                organization_id=organization_id
            )
            
            # Send email notification
            due_date_str = due_date.strftime("%Y-%m-%d") if due_date else None
            task_url = f"http://192.168.9.119:3000/tasks/{task_id}"
            
            email_sent = await email_service.send_task_assignment_email(
                to_email=user.email,
                task_title=task_title,
                task_description=task_description or "",
                assigner_name=assigner_name,
                project_name=project_name,
                due_date=due_date_str,
                priority=priority,
                task_url=task_url
            )
            
            # Also create SmartNotification with email delivery method
            smart_notification = SmartNotification(
                organization_id=organization_id,
                user_id=user_id,
                notification_type='task_assignment',
                title=f'New Task Assigned: {task_title}',
                message=f'{assigner_name} assigned you a new task: "{task_title}"',
                priority='normal',
                context_data={
                    'task_id': str(task_id),
                    'task_title': task_title,
                    'assigner_id': str(assigner_id),
                    'assigner_name': assigner_name,
                    'action_required': 'accept_task'
                },
                ai_generated=False,
                delivery_method='email'
            )
            
            self.db.add(smart_notification)
            await self.db.commit()
            
            logger.info(f"Task assignment notification sent to {user.email}: in-app=True, email={email_sent}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send task assignment notification: {e}")
            return False
    
    async def send_comment_notification(
        self,
        user_id: str,
        task_id: str,
        task_title: str,
        comment_content: str,
        commenter_id: str,
        project_name: str,
        organization_id: str
    ) -> bool:
        """Send both in-app and email notifications for new comments"""
        try:
            # Get user email and commenter details
            user_result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            commenter_result = await self.db.execute(
                select(User).where(User.id == commenter_id)
            )
            commenter = commenter_result.scalar_one_or_none()
            
            if not user or not commenter:
                logger.error(f"User or commenter not found: user_id={user_id}, commenter_id={commenter_id}")
                return False
            
            commenter_name = f"{commenter.first_name} {commenter.last_name}"
            
            # Send in-app notification
            action_buttons = [
                {"label": "View Task", "action": "view_task", "variant": "primary"},
                {"label": "Reply", "action": "reply_comment", "variant": "secondary"}
            ]
            
            await self.in_app_service.create_in_app_notification(
                user_id=user_id,
                title=f"New Comment on {task_title}",
                message=f"{commenter_name} commented on task '{task_title}': {comment_content[:100]}{'...' if len(comment_content) > 100 else ''}",
                category="comment_mention",
                priority="normal",
                action_buttons=action_buttons,
                organization_id=organization_id,
                action_url=f"/tasks/{task_id}"
            )
            
            # Send email notification
            task_url = f"http://192.168.9.119:3000/tasks/{task_id}"
            
            email_sent = await email_service.send_comment_notification_email(
                to_email=user.email,
                commenter_name=commenter_name,
                task_title=task_title,
                comment_content=comment_content,
                project_name=project_name,
                task_url=task_url
            )
            
            # Also create SmartNotification with email delivery method
            smart_notification = SmartNotification(
                organization_id=organization_id,
                user_id=user_id,
                notification_type='comment_notification',
                title=f'New Comment on {task_title}',
                message=f'{commenter_name} commented: "{comment_content[:100]}{"..." if len(comment_content) > 100 else ""}"',
                priority='normal',
                context_data={
                    'task_id': str(task_id),
                    'task_title': task_title,
                    'commenter_id': str(commenter_id),
                    'commenter_name': commenter_name,
                    'comment_content': comment_content
                },
                ai_generated=False,
                delivery_method='email'
            )
            
            self.db.add(smart_notification)
            await self.db.commit()
            
            logger.info(f"Comment notification sent to {user.email}: in-app=True, email={email_sent}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send comment notification: {e}")
            return False

    async def send_mention_notification(
        self,
        mentioned_user_id: str,
        card_id: str,
        card_title: str,
        comment_content: str,
        mentioned_by_user_id: str,
        mentioned_by_name: str,
        project_name: str,
        organization_id: str
    ) -> bool:
        """Send both in-app and email notifications for @mentions"""
        try:
            # Get mentioned user email
            user_result = await self.db.execute(
                select(User).where(User.id == mentioned_user_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                logger.error(f"Mentioned user not found: user_id={mentioned_user_id}")
                return False

            # Create email content
            subject = f"You were mentioned in '{card_title}'"

            # Truncate comment for email
            comment_preview = comment_content[:200] + "..." if len(comment_content) > 200 else comment_content

            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #333;">You were mentioned!</h2>
                <p>Hi {user.first_name},</p>
                <p><strong>{mentioned_by_name}</strong> mentioned you in a comment on the card <strong>"{card_title}"</strong> in project <strong>{project_name}</strong>.</p>

                <div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
                    <p style="margin: 0; font-style: italic;">"{comment_preview}"</p>
                </div>

                <p>
                    <a href="{self.frontend_url}/card-details?id={card_id}"
                       style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Card
                    </a>
                </p>

                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                <p style="color: #666; font-size: 12px;">
                    This notification was sent because you were mentioned in a comment.
                    You can manage your notification preferences in your account settings.
                </p>
            </div>
            """

            # Send email
            email_sent = await self.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content
            )

            # Also create SmartNotification with email delivery method
            smart_notification = SmartNotification(
                organization_id=organization_id,
                user_id=mentioned_user_id,
                notification_type='mention_notification',
                title=f'You were mentioned in {card_title}',
                message=f'{mentioned_by_name} mentioned you: "{comment_preview}"',
                priority='normal',
                context_data={
                    'card_id': str(card_id),
                    'card_title': card_title,
                    'mentioned_by_user_id': str(mentioned_by_user_id),
                    'mentioned_by_name': mentioned_by_name,
                    'comment_content': comment_content
                },
                ai_generated=False,
                delivery_method='email'
            )

            self.db.add(smart_notification)
            await self.db.commit()

            logger.info(f"Mention notification sent to {user.email}: in-app=True, email={email_sent}")
            return True

        except Exception as e:
            logger.error(f"Failed to send mention notification: {e}")
            return False
    
    async def send_project_activity_notification(
        self,
        user_ids: List[str],
        activity_type: str,
        activity_title: str,
        activity_message: str,
        project_name: str,
        organization_id: str,
        actor_name: str,
        priority: str = "normal"
    ) -> bool:
        """Send project activity notifications to multiple users"""
        try:
            success_count = 0
            
            for user_id in user_ids:
                # Get user email
                user_result = await self.db.execute(
                    select(User).where(User.id == user_id)
                )
                user = user_result.scalar_one_or_none()
                
                if not user:
                    continue
                
                # Send in-app notification
                await self.in_app_service.create_in_app_notification(
                    user_id=user_id,
                    title=activity_title,
                    message=activity_message,
                    category="project_update",
                    priority=priority,
                    organization_id=organization_id,
                    action_url=f"/projects"
                )
                
                # Create SmartNotification with email delivery method
                smart_notification = SmartNotification(
                    organization_id=organization_id,
                    user_id=user_id,
                    notification_type='project_activity',
                    title=activity_title,
                    message=activity_message,
                    priority=priority,
                    context_data={
                        'activity_type': activity_type,
                        'project_name': project_name,
                        'actor_name': actor_name
                    },
                    ai_generated=False,
                    delivery_method='email'
                )
                
                self.db.add(smart_notification)
                success_count += 1
            
            await self.db.commit()
            
            logger.info(f"Project activity notifications sent to {success_count} users")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send project activity notifications: {e}")
            return False

# Global service instance
enhanced_notification_service = None

def get_enhanced_notification_service(db: AsyncSession) -> EnhancedEmailNotificationService:
    """Get enhanced notification service instance"""
    return EnhancedEmailNotificationService(db)
