#!/usr/bin/env python3
"""
Create test notifications for development
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import async_session_factory
from app.models.notification import Notification
from app.models.user import User
from sqlalchemy import select

async def create_test_notifications():
    """Create test notifications for development"""
    
    async with async_session_factory() as db:
        try:
            # Get the first user from the database
            result = await db.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            
            if not user:
                print("❌ No users found in database. Please create a user first.")
                return
            
            print(f"✅ Found user: {user.email} (ID: {user.id})")
            
            # Create test notifications
            test_notifications = [
                {
                    "title": "Welcome to WorkSphere!",
                    "message": "Get started by creating your first project and inviting team members.",
                    "type": "welcome",
                    "priority": "normal",
                    "category": "system"
                },
                {
                    "title": "New Task Assigned",
                    "message": "You have been assigned to 'Update user interface' in Project Alpha.",
                    "type": "task_assignment",
                    "priority": "high",
                    "category": "task",
                    "action_url": "/projects/1/tasks/1"
                },
                {
                    "title": "Project Milestone Reached",
                    "message": "Project Beta has reached the 'Design Phase Complete' milestone.",
                    "type": "project_milestone",
                    "priority": "normal",
                    "category": "project"
                },
                {
                    "title": "Team Member Added",
                    "message": "John Doe has joined your organization as a Developer.",
                    "type": "team_member_added",
                    "priority": "low",
                    "category": "team"
                },
                {
                    "title": "Task Reminder",
                    "message": "Don't forget: 'Review code changes' is due tomorrow.",
                    "type": "task_reminder",
                    "priority": "high",
                    "category": "task",
                    "action_url": "/tasks/reminder"
                }
            ]
            
            created_count = 0
            for notification_data in test_notifications:
                # Create notification
                notification = Notification(
                    id=uuid4(),
                    user_id=user.id,
                    title=notification_data["title"],
                    message=notification_data["message"],
                    type=notification_data["type"],
                    priority=notification_data["priority"],
                    action_url=notification_data.get("action_url"),
                    read=False,
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=30)
                )
                
                db.add(notification)
                created_count += 1
            
            await db.commit()
            print(f"✅ Created {created_count} test notifications for user {user.email}")
            
            # Show current notification count
            result = await db.execute(
                select(Notification).where(Notification.user_id == user.id)
            )
            total_notifications = len(result.scalars().all())

            result = await db.execute(
                select(Notification).where(
                    Notification.user_id == user.id,
                    Notification.read == False
                )
            )
            unread_notifications = len(result.scalars().all())
            
            print(f"📊 Total notifications: {total_notifications}")
            print(f"📊 Unread notifications: {unread_notifications}")
            
        except Exception as e:
            print(f"❌ Error creating test notifications: {e}")
            await db.rollback()
            raise

if __name__ == "__main__":
    print("🔔 Creating test notifications...")
    asyncio.run(create_test_notifications())
    print("✅ Done!")
