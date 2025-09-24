"""
Notifications API endpoints
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.notification import Notification, NotificationPreference
from app.models.ai_automation import SmartNotification
from app.schemas.notification import (
    NotificationCreate, NotificationUpdate, NotificationResponse,
    NotificationPreferenceCreate, NotificationPreferenceUpdate, NotificationPreferenceResponse
)
from app.services.enhanced_notification_service import EnhancedNotificationService
from app.services.in_app_notification_service import InAppNotificationService
from app.services.organization_service import OrganizationService

router = APIRouter()


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    unread_only: bool = Query(False),
    notification_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for current user"""
    try:
        # Build query
        query = select(Notification).where(Notification.user_id == current_user.id)
        
        if unread_only:
            query = query.where(Notification.read == False)
        
        if notification_type:
            query = query.where(Notification.type == notification_type)
        
        # Order by created_at desc and apply pagination
        query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        return notifications
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notifications: {str(e)}"
        )


@router.post("/", response_model=NotificationResponse)
async def create_notification(
    notification_data: NotificationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new notification"""
    try:
        # Use current user as the target user if not specified or if user doesn't have permission
        target_user_id = notification_data.user_id

        # For now, allow users to create notifications for themselves
        # In a production system, you might want to restrict this to admin users
        if target_user_id != current_user.id:
            # Check if current user has permission to create notifications for others
            # For simplicity, we'll allow it for now but log it
            pass

        notification = Notification(
            user_id=target_user_id,
            organization_id=notification_data.organization_id,
            title=notification_data.title,
            message=notification_data.message,
            type=notification_data.type,
            priority=notification_data.priority,
            action_url=notification_data.action_url,
            notification_metadata=notification_data.notification_metadata
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        return notification
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}"
        )


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read"""
    try:
        # Get notification
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == current_user.id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        # Mark as read
        notification.read = True
        notification.read_at = func.now()
        
        await db.commit()
        await db.refresh(notification)
        
        return notification
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.put("/mark-all-read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read for current user"""
    try:
        # Update all unread notifications
        await db.execute(
            Notification.__table__.update()
            .where(
                and_(
                    Notification.user_id == current_user.id,
                    Notification.read == False
                )
            )
            .values(read=True, read_at=func.now())
        )
        
        await db.commit()
        
        return {"message": "All notifications marked as read"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a notification"""
    try:
        # Get notification
        result = await db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == current_user.id
                )
            )
        )
        notification = result.scalar_one_or_none()
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        await db.delete(notification)
        await db.commit()
        
        return {"message": "Notification deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}"
        )


@router.get("/stats")
async def get_notification_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notification statistics for current user"""
    try:
        # Get total and unread counts
        total_result = await db.execute(
            select(func.count(Notification.id)).where(Notification.user_id == current_user.id)
        )
        total_count = total_result.scalar() or 0
        
        unread_result = await db.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == current_user.id,
                    Notification.read == False
                )
            )
        )
        unread_count = unread_result.scalar() or 0
        
        return {
            "total_notifications": total_count,
            "unread_notifications": unread_count,
            "read_notifications": total_count - unread_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification stats: {str(e)}"
        )


# Enhanced Notification Endpoints

@router.get("/enhanced", response_model=List[dict])
async def get_enhanced_notifications(
    organization_id: Optional[str] = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get enhanced notifications with organization context"""

    # Get organization context
    org_service = OrganizationService(db)
    if not organization_id:
        organization_id = await org_service.get_current_organization(str(current_user.id))
        if not organization_id:
            raise HTTPException(status_code=400, detail="No organization context")

    # Get notifications using enhanced service
    notification_service = EnhancedNotificationService(db)
    notifications = await notification_service.get_user_notifications(
        str(current_user.id), organization_id, unread_only, limit
    )

    return notifications


@router.post("/enhanced/{notification_id}/read")
async def mark_enhanced_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark enhanced notification as read"""

    notification_service = EnhancedNotificationService(db)
    success = await notification_service.mark_notification_read(
        notification_id, str(current_user.id)
    )

    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")

    return {"success": True, "message": "Notification marked as read"}


@router.get("/enhanced/stats/{organization_id}")
async def get_enhanced_notification_stats(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get enhanced notification statistics"""

    notification_service = EnhancedNotificationService(db)
    stats = await notification_service.get_notification_stats(
        str(current_user.id), organization_id
    )

    return stats


@router.post("/enhanced/send-role-change")
async def send_role_change_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send role change notification (admin/owner only)"""

    user_id = notification_data.get('user_id')
    organization_id = notification_data.get('organization_id')
    old_role = notification_data.get('old_role')
    new_role = notification_data.get('new_role')

    if not all([user_id, organization_id, old_role, new_role]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    notification_service = EnhancedNotificationService(db)
    await notification_service.send_role_change_notification(
        user_id, organization_id, old_role, new_role, str(current_user.id)
    )

    return {"success": True, "message": "Role change notification sent"}


@router.post("/enhanced/send-task-completion")
async def send_task_completion_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send task completion notification"""

    card_id = notification_data.get('card_id')
    organization_id = notification_data.get('organization_id')

    if not all([card_id, organization_id]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    notification_service = EnhancedNotificationService(db)
    await notification_service.send_task_completion_notification(
        card_id, str(current_user.id), organization_id
    )

    return {"success": True, "message": "Task completion notification sent"}


@router.post("/enhanced/send-project-update")
async def send_project_update_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send project update notification"""

    project_id = notification_data.get('project_id')
    update_type = notification_data.get('update_type')  # created, updated, deleted
    changes = notification_data.get('changes')

    if not all([project_id, update_type]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    notification_service = EnhancedNotificationService(db)
    await notification_service.send_project_update_notification(
        project_id, str(current_user.id), update_type, changes
    )

    return {"success": True, "message": "Project update notification sent"}


# Background task endpoints (for system use)

@router.post("/enhanced/send-meeting-reminders")
async def send_meeting_reminders(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send meeting reminder notifications (system task)"""

    notification_service = EnhancedNotificationService(db)
    await notification_service.send_meeting_reminder_notifications()

    return {"success": True, "message": "Meeting reminders sent"}


@router.post("/enhanced/send-overdue-task-notifications")
async def send_overdue_task_notifications(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send overdue task notifications (system task)"""

    notification_service = EnhancedNotificationService(db)
    await notification_service.send_overdue_task_notifications()

    return {"success": True, "message": "Overdue task notifications sent"}


# In-App Only Notification Endpoints
@router.post("/in-app/create")
async def create_in_app_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create generic in-app notification"""

    service = InAppNotificationService(db)

    notification = await service.create_in_app_notification(
        user_id=notification_data.get("user_id", str(current_user.id)),
        title=notification_data["title"],
        message=notification_data["message"],
        category=notification_data["category"],
        priority=notification_data.get("priority", "normal"),
        action_buttons=notification_data.get("action_buttons"),
        organization_id=notification_data.get("organization_id"),
        action_url=notification_data.get("action_url")
    )

    return {
        "success": True,
        "notification_id": str(notification.id),
        "message": "In-app notification created successfully"
    }


@router.post("/in-app/welcome")
async def send_welcome_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send welcome notification for new users"""

    service = InAppNotificationService(db)

    notification = await service.send_welcome_notification(
        user_id=notification_data.get("user_id", str(current_user.id)),
        organization_name=notification_data["organization_name"],
        user_name=notification_data["user_name"],
        organization_id=notification_data["organization_id"]
    )

    return {
        "success": True,
        "notification_id": str(notification.id),
        "message": "Welcome notification sent successfully"
    }


@router.post("/in-app/task-assignment")
async def send_task_assignment_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send task assignment notification"""

    service = InAppNotificationService(db)

    notification = await service.send_task_assignment_notification(
        user_id=notification_data["user_id"],
        task_title=notification_data["task_title"],
        task_id=notification_data["task_id"],
        project_name=notification_data["project_name"],
        assigned_by=notification_data.get("assigned_by", str(current_user.id)),
        organization_id=notification_data["organization_id"]
    )

    return {
        "success": True,
        "notification_id": str(notification.id),
        "message": "Task assignment notification sent successfully"
    }


@router.post("/in-app/task-reminder")
async def send_task_reminder_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send task deadline reminder notification"""

    service = InAppNotificationService(db)

    from datetime import datetime
    due_date = datetime.fromisoformat(notification_data["due_date"].replace('Z', '+00:00'))

    notification = await service.send_task_reminder_notification(
        user_id=notification_data["user_id"],
        task_title=notification_data["task_title"],
        task_id=notification_data["task_id"],
        due_date=due_date,
        organization_id=notification_data["organization_id"]
    )

    return {
        "success": True,
        "notification_id": str(notification.id),
        "message": "Task reminder notification sent successfully"
    }


@router.post("/in-app/task-status-update")
async def send_task_status_update_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send task status update notification"""

    service = InAppNotificationService(db)

    notification = await service.send_task_status_update_notification(
        user_id=notification_data["user_id"],
        task_title=notification_data["task_title"],
        task_id=notification_data["task_id"],
        old_status=notification_data["old_status"],
        new_status=notification_data["new_status"],
        updated_by=notification_data.get("updated_by", str(current_user.id)),
        organization_id=notification_data["organization_id"]
    )

    return {
        "success": True,
        "notification_id": str(notification.id),
        "message": "Task status update notification sent successfully"
    }


@router.post("/in-app/project-update")
async def send_project_update_notification_in_app(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send project update notification"""

    service = InAppNotificationService(db)

    notification = await service.send_project_update_notification_in_app(
        user_id=notification_data["user_id"],
        project_name=notification_data["project_name"],
        project_id=notification_data["project_id"],
        update_message=notification_data["update_message"],
        updated_by=notification_data.get("updated_by", str(current_user.id)),
        organization_id=notification_data["organization_id"]
    )

    return {
        "success": True,
        "notification_id": str(notification.id),
        "message": "Project update notification sent successfully"
    }


@router.post("/in-app/project-milestone")
async def send_project_milestone_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send project milestone notification"""

    service = InAppNotificationService(db)

    notification = await service.send_project_milestone_notification(
        user_id=notification_data["user_id"],
        project_name=notification_data["project_name"],
        project_id=notification_data["project_id"],
        milestone_name=notification_data["milestone_name"],
        organization_id=notification_data["organization_id"]
    )

    return {
        "success": True,
        "notification_id": str(notification.id),
        "message": "Project milestone notification sent successfully"
    }


@router.post("/in-app/team-member-added")
async def send_team_member_added_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send team member added notification"""

    service = InAppNotificationService(db)

    notification = await service.send_team_member_added_notification(
        user_id=notification_data["user_id"],
        project_name=notification_data["project_name"],
        project_id=notification_data["project_id"],
        new_member_name=notification_data["new_member_name"],
        added_by=notification_data.get("added_by", str(current_user.id)),
        organization_id=notification_data["organization_id"]
    )

    return {
        "success": True,
        "notification_id": str(notification.id),
        "message": "Team member added notification sent successfully"
    }


@router.post("/in-app/system")
async def send_system_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send system notification (maintenance, updates, announcements)"""

    service = InAppNotificationService(db)

    notification = await service.send_system_notification(
        user_id=notification_data.get("user_id", str(current_user.id)),
        title=notification_data["title"],
        message=notification_data["message"],
        priority=notification_data.get("priority", "normal"),
        organization_id=notification_data.get("organization_id"),
        action_url=notification_data.get("action_url")
    )

    return {
        "success": True,
        "notification_id": str(notification.id),
        "message": "System notification sent successfully"
    }


@router.post("/in-app/role-based")
async def send_role_based_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send notifications to users with specific roles"""

    service = InAppNotificationService(db)

    notifications = await service.send_role_based_notification(
        organization_id=notification_data["organization_id"],
        target_roles=notification_data["target_roles"],
        title=notification_data["title"],
        message=notification_data["message"],
        category=notification_data["category"],
        priority=notification_data.get("priority", "normal"),
        action_buttons=notification_data.get("action_buttons"),
        action_url=notification_data.get("action_url")
    )

    return {
        "success": True,
        "notification_count": len(notifications),
        "message": f"Role-based notifications sent to {len(notifications)} users"
    }


@router.post("/in-app/organization-wide")
async def send_organization_wide_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send notification to all organization members"""

    service = InAppNotificationService(db)

    notifications = await service.send_organization_wide_notification(
        organization_id=notification_data["organization_id"],
        title=notification_data["title"],
        message=notification_data["message"],
        category=notification_data["category"],
        priority=notification_data.get("priority", "normal"),
        action_buttons=notification_data.get("action_buttons"),
        action_url=notification_data.get("action_url"),
        exclude_roles=notification_data.get("exclude_roles")
    )

    return {
        "success": True,
        "notification_count": len(notifications),
        "message": f"Organization-wide notifications sent to {len(notifications)} users"
    }


@router.put("/in-app/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark a notification as read"""

    service = InAppNotificationService(db)

    success = await service.mark_notification_as_read(notification_id, str(current_user.id))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied"
        )

    return {
        "success": True,
        "message": "Notification marked as read"
    }


@router.put("/in-app/mark-all-read")
async def mark_all_notifications_as_read(
    organization_id: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark all notifications as read for current user"""

    service = InAppNotificationService(db)

    count = await service.mark_all_notifications_as_read(str(current_user.id), organization_id)

    return {
        "success": True,
        "marked_count": count,
        "message": f"Marked {count} notifications as read"
    }


@router.get("/in-app/user-notifications")
async def get_user_notifications(
    organization_id: Optional[str] = Query(None),
    unread_only: bool = Query(False),
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notifications for current user with filtering"""

    service = InAppNotificationService(db)

    notifications = await service.get_user_notifications(
        user_id=str(current_user.id),
        organization_id=organization_id,
        unread_only=unread_only,
        category=category,
        limit=limit,
        offset=offset
    )

    # Convert to response format
    notification_data = []
    for notification in notifications:
        notification_data.append({
            "id": str(notification.id),
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "priority": notification.priority,
            "read": notification.read,
            "action_url": notification.action_url,
            "notification_metadata": notification.notification_metadata,
            "created_at": notification.created_at.isoformat(),
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
            "expires_at": notification.expires_at.isoformat() if notification.expires_at else None
        })

    return {
        "success": True,
        "notifications": notification_data,
        "count": len(notification_data)
    }


@router.get("/in-app/unread-count")
async def get_unread_count(
    organization_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get count of unread notifications for current user"""

    service = InAppNotificationService(db)

    count = await service.get_unread_count(str(current_user.id), organization_id)

    return {
        "success": True,
        "unread_count": count
    }


@router.delete("/in-app/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a notification"""

    service = InAppNotificationService(db)

    success = await service.delete_notification(notification_id, str(current_user.id))

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or access denied"
        )

    return {
        "success": True,
        "message": "Notification deleted successfully"
    }


@router.post("/in-app/cleanup-expired")
async def cleanup_expired_notifications(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Clean up expired notifications (admin/system task)"""

    service = InAppNotificationService(db)

    count = await service.cleanup_expired_notifications()

    return {
        "success": True,
        "cleaned_count": count,
        "message": f"Cleaned up {count} expired notifications"
    }


# Performance Optimization Endpoints

@router.post("/in-app/batch-create")
async def batch_create_notifications(
    notifications_data: List[Dict[str, Any]],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create multiple notifications in batch"""
    service = InAppNotificationService(db)
    result = await service.batch_create_notifications(notifications_data)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return result

@router.put("/in-app/batch-mark-read")
async def batch_mark_notifications_as_read(
    notification_ids: List[str],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Mark multiple notifications as read"""
    service = InAppNotificationService(db)
    result = await service.batch_mark_as_read(notification_ids, str(current_user.id))

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return result

@router.get("/in-app/statistics")
async def get_notification_statistics(
    organization_id: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notification statistics"""
    service = InAppNotificationService(db)
    result = await service.get_notification_statistics(organization_id)

    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])

    return result
