"""
WebSocket connection manager for real-time notifications and updates
"""
import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from uuid import UUID
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.organization import OrganizationMember
from app.services.organization_service import OrganizationService


class ConnectionManager:
    def __init__(self):
        # Active connections by user ID
        self.active_connections: Dict[str, WebSocket] = {}
        
        # User to organization mapping
        self.user_organizations: Dict[str, str] = {}
        
        # Organization rooms (users subscribed to org notifications)
        self.organization_rooms: Dict[str, Set[str]] = {}
        
        # Project rooms (users subscribed to project notifications)
        self.project_rooms: Dict[str, Set[str]] = {}
        
        # Notification rooms (users subscribed to notification updates)
        self.notification_rooms: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, organization_id: Optional[str] = None):
        """Accept a WebSocket connection and register the user"""
        await websocket.accept()
        
        # Store the connection
        self.active_connections[user_id] = websocket
        
        # Store user's organization
        if organization_id:
            self.user_organizations[user_id] = organization_id
            
            # Add user to organization room
            if organization_id not in self.organization_rooms:
                self.organization_rooms[organization_id] = set()
            self.organization_rooms[organization_id].add(user_id)
        
        print(f"WebSocket connected: user {user_id}, organization {organization_id}")

    def disconnect(self, user_id: str):
        """Remove a user's WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Remove from organization room
        if user_id in self.user_organizations:
            org_id = self.user_organizations[user_id]
            if org_id in self.organization_rooms:
                self.organization_rooms[org_id].discard(user_id)
                if not self.organization_rooms[org_id]:
                    del self.organization_rooms[org_id]
            del self.user_organizations[user_id]
        
        # Remove from project rooms
        for project_id, users in list(self.project_rooms.items()):
            users.discard(user_id)
            if not users:
                del self.project_rooms[project_id]
        
        # Remove from notification rooms
        for room_id, users in list(self.notification_rooms.items()):
            users.discard(user_id)
            if not users:
                del self.notification_rooms[room_id]
        
        print(f"WebSocket disconnected: user {user_id}")

    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to a specific user"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            try:
                await websocket.send_text(json.dumps(message))
                return True
            except Exception as e:
                print(f"Error sending message to user {user_id}: {e}")
                # Remove broken connection
                self.disconnect(user_id)
                return False
        return False

    async def send_to_organization(self, message: dict, organization_id: str, exclude_user: Optional[str] = None):
        """Send a message to all users in an organization"""
        if organization_id not in self.organization_rooms:
            return 0
        
        sent_count = 0
        users_to_remove = []
        
        for user_id in self.organization_rooms[organization_id]:
            if exclude_user and user_id == exclude_user:
                continue
                
            if await self.send_personal_message(message, user_id):
                sent_count += 1
            else:
                users_to_remove.append(user_id)
        
        # Clean up broken connections
        for user_id in users_to_remove:
            self.disconnect(user_id)
        
        return sent_count

    async def send_to_project(self, message: dict, project_id: str, exclude_user: Optional[str] = None):
        """Send a message to all users subscribed to a project"""
        if project_id not in self.project_rooms:
            return 0
        
        sent_count = 0
        users_to_remove = []
        
        for user_id in self.project_rooms[project_id]:
            if exclude_user and user_id == exclude_user:
                continue
                
            if await self.send_personal_message(message, user_id):
                sent_count += 1
            else:
                users_to_remove.append(user_id)
        
        # Clean up broken connections
        for user_id in users_to_remove:
            self.disconnect(user_id)
        
        return sent_count

    def join_project_room(self, user_id: str, project_id: str):
        """Add a user to a project room"""
        if project_id not in self.project_rooms:
            self.project_rooms[project_id] = set()
        self.project_rooms[project_id].add(user_id)
        print(f"User {user_id} joined project room {project_id}")

    def leave_project_room(self, user_id: str, project_id: str):
        """Remove a user from a project room"""
        if project_id in self.project_rooms:
            self.project_rooms[project_id].discard(user_id)
            if not self.project_rooms[project_id]:
                del self.project_rooms[project_id]
        print(f"User {user_id} left project room {project_id}")

    def join_notification_room(self, user_id: str, organization_id: Optional[str] = None):
        """Add a user to notification room"""
        room_id = organization_id or "global"
        if room_id not in self.notification_rooms:
            self.notification_rooms[room_id] = set()
        self.notification_rooms[room_id].add(user_id)
        print(f"User {user_id} joined notification room {room_id}")

    def leave_notification_room(self, user_id: str, organization_id: Optional[str] = None):
        """Remove a user from notification room"""
        room_id = organization_id or "global"
        if room_id in self.notification_rooms:
            self.notification_rooms[room_id].discard(user_id)
            if not self.notification_rooms[room_id]:
                del self.notification_rooms[room_id]
        print(f"User {user_id} left notification room {room_id}")

    async def broadcast_notification(self, notification: dict, organization_id: Optional[str] = None, target_user_id: Optional[str] = None):
        """Broadcast a notification to appropriate users"""
        message = {
            "type": "notification",
            "payload": notification,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        sent_count = 0
        
        if target_user_id:
            # Send to specific user
            if await self.send_personal_message(message, target_user_id):
                sent_count += 1
        elif organization_id:
            # Send to organization notification room
            room_id = organization_id
            if room_id in self.notification_rooms:
                for user_id in self.notification_rooms[room_id]:
                    if await self.send_personal_message(message, user_id):
                        sent_count += 1
        else:
            # Send to global notification room
            room_id = "global"
            if room_id in self.notification_rooms:
                for user_id in self.notification_rooms[room_id]:
                    if await self.send_personal_message(message, user_id):
                        sent_count += 1
        
        return sent_count

    async def broadcast_project_update(self, project_update: dict, project_id: str, exclude_user: Optional[str] = None):
        """Broadcast a project update to subscribed users"""
        message = {
            "type": "project_update",
            "payload": project_update,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_to_project(message, project_id, exclude_user)

    async def broadcast_task_update(self, task_update: dict, project_id: str, exclude_user: Optional[str] = None):
        """Broadcast a task update to project subscribers"""
        message = {
            "type": "task_update",
            "payload": task_update,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_to_project(message, project_id, exclude_user)

    async def send_typing_indicator(self, typing_data: dict, project_id: str, exclude_user: Optional[str] = None):
        """Send typing indicator to project subscribers"""
        message = {
            "type": "typing_indicator",
            "payload": typing_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_to_project(message, project_id, exclude_user)

    async def send_user_status_update(self, status_data: dict, organization_id: str, exclude_user: Optional[str] = None):
        """Send user status update to organization members"""
        message = {
            "type": "user_status_update",
            "payload": status_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return await self.send_to_organization(message, organization_id, exclude_user)

    def get_connection_stats(self):
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "organization_rooms": {org_id: len(users) for org_id, users in self.organization_rooms.items()},
            "project_rooms": {proj_id: len(users) for proj_id, users in self.project_rooms.items()},
            "notification_rooms": {room_id: len(users) for room_id, users in self.notification_rooms.items()}
        }

    async def handle_message(self, websocket: WebSocket, user_id: str, message: dict):
        """Handle incoming WebSocket messages"""
        message_type = message.get("type")
        payload = message.get("payload", {})
        
        try:
            if message_type == "join_project":
                project_id = payload.get("projectId")
                if project_id:
                    self.join_project_room(user_id, project_id)
                    
            elif message_type == "leave_project":
                project_id = payload.get("projectId")
                if project_id:
                    self.leave_project_room(user_id, project_id)
                    
            elif message_type == "join_notifications":
                organization_id = payload.get("organizationId")
                self.join_notification_room(user_id, organization_id)
                
            elif message_type == "leave_notifications":
                organization_id = payload.get("organizationId")
                self.leave_notification_room(user_id, organization_id)
                
            elif message_type == "typing_indicator":
                project_id = payload.get("projectId")
                if project_id:
                    await self.send_typing_indicator(payload, project_id, user_id)
                    
            elif message_type == "user_status_update":
                organization_id = self.user_organizations.get(user_id)
                if organization_id:
                    await self.send_user_status_update(payload, organization_id, user_id)
                    
            elif message_type == "ping":
                # Respond to ping with pong
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.utcnow().isoformat()}))
                
        except Exception as e:
            print(f"Error handling WebSocket message from user {user_id}: {e}")
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Failed to process message",
                "timestamp": datetime.utcnow().isoformat()
            }))


# Global connection manager instance
manager = ConnectionManager()
