"""
WebSocket endpoints for real-time communication
"""
import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.websocket_manager import manager
from app.services.organization_service import OrganizationService

router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: Optional[str] = Query(None),
    organization_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time communication
    
    Query parameters:
    - token: Authentication token
    - organization_id: Optional organization ID for room subscription
    """
    
    # Authenticate user
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token required")
        return
    
    try:
        # Get database session
        async for db in get_db():
            # Verify user exists and token is valid
            # For WebSocket, we need to manually validate the token
            from app.services.session_service import SessionService
            session_service = SessionService(db)
            user = await session_service.get_user_from_token(token)
            if not user or str(user.id) != user_id:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication")
                return
            
            # Get user's organization if not provided
            if not organization_id:
                org_service = OrganizationService(db)
                organization_id = await org_service.get_current_organization(user_id)
            
            # Connect to WebSocket manager
            await manager.connect(websocket, user_id, organization_id)
            
            # Join notification room by default
            manager.join_notification_room(user_id, organization_id)
            
            # Send connection confirmation
            await websocket.send_text(json.dumps({
                "type": "connection_established",
                "user_id": user_id,
                "organization_id": organization_id,
                "timestamp": asyncio.get_event_loop().time()
            }))
            
            try:
                while True:
                    # Receive message from client
                    data = await websocket.receive_text()
                    
                    try:
                        message = json.loads(data)
                        await manager.handle_message(websocket, user_id, message)
                    except json.JSONDecodeError:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Invalid JSON format",
                            "timestamp": asyncio.get_event_loop().time()
                        }))
                    except Exception as e:
                        print(f"Error handling WebSocket message: {e}")
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "Failed to process message",
                            "timestamp": asyncio.get_event_loop().time()
                        }))
                        
            except WebSocketDisconnect:
                manager.disconnect(user_id)
                print(f"WebSocket disconnected for user {user_id}")
            except Exception as e:
                print(f"WebSocket error for user {user_id}: {e}")
                manager.disconnect(user_id)
                
    except Exception as e:
        print(f"WebSocket authentication error: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")


@router.get("/ws/stats")
async def get_websocket_stats(
    current_user: User = Depends(get_current_user)
):
    """Get WebSocket connection statistics (admin only)"""
    
    # Check if user is admin/owner (you might want to implement proper role checking)
    # For now, just return stats for any authenticated user
    
    stats = manager.get_connection_stats()
    
    return {
        "success": True,
        "data": stats
    }


@router.post("/ws/broadcast/notification")
async def broadcast_notification(
    notification_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Broadcast a notification via WebSocket (admin only)"""
    
    # Get user's organization
    org_service = OrganizationService(db)
    organization_id = await org_service.get_current_organization(str(current_user.id))
    
    # Broadcast notification
    sent_count = await manager.broadcast_notification(
        notification=notification_data,
        organization_id=organization_id,
        target_user_id=notification_data.get("target_user_id")
    )
    
    return {
        "success": True,
        "message": f"Notification broadcast to {sent_count} users",
        "sent_count": sent_count
    }


@router.post("/ws/broadcast/project-update")
async def broadcast_project_update(
    update_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Broadcast a project update via WebSocket"""
    
    project_id = update_data.get("project_id")
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id is required"
        )
    
    # Broadcast project update
    sent_count = await manager.broadcast_project_update(
        project_update=update_data,
        project_id=project_id,
        exclude_user=str(current_user.id)
    )
    
    return {
        "success": True,
        "message": f"Project update broadcast to {sent_count} users",
        "sent_count": sent_count
    }


@router.post("/ws/broadcast/task-update")
async def broadcast_task_update(
    update_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Broadcast a task update via WebSocket"""
    
    project_id = update_data.get("project_id")
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id is required"
        )
    
    # Broadcast task update
    sent_count = await manager.broadcast_task_update(
        task_update=update_data,
        project_id=project_id,
        exclude_user=str(current_user.id)
    )
    
    return {
        "success": True,
        "message": f"Task update broadcast to {sent_count} users",
        "sent_count": sent_count
    }


@router.post("/ws/send-message")
async def send_websocket_message(
    message_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a direct WebSocket message to a user"""
    
    target_user_id = message_data.get("target_user_id")
    message = message_data.get("message")
    
    if not target_user_id or not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_user_id and message are required"
        )
    
    # Send message
    success = await manager.send_personal_message(
        message={
            "type": "direct_message",
            "payload": {
                "from_user_id": str(current_user.id),
                "message": message,
                "timestamp": asyncio.get_event_loop().time()
            }
        },
        user_id=target_user_id
    )
    
    return {
        "success": success,
        "message": "Message sent successfully" if success else "Failed to send message (user not connected)"
    }


@router.post("/ws/join-project-room")
async def join_project_room(
    room_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Join a project room for real-time updates"""
    
    project_id = room_data.get("project_id")
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id is required"
        )
    
    # Join project room
    manager.join_project_room(str(current_user.id), project_id)
    
    return {
        "success": True,
        "message": f"Joined project room {project_id}"
    }


@router.post("/ws/leave-project-room")
async def leave_project_room(
    room_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Leave a project room"""
    
    project_id = room_data.get("project_id")
    if not project_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id is required"
        )
    
    # Leave project room
    manager.leave_project_room(str(current_user.id), project_id)
    
    return {
        "success": True,
        "message": f"Left project room {project_id}"
    }
