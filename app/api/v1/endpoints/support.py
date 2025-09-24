"""
Support system API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import secrets
import string

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.support import (
    SupportTicket, SupportMessage, HelpArticle, ContactMessage,
    SupportCategory, SupportSettings
)
from app.services.organization_service import OrganizationService
from app.services.enhanced_notification_service import EnhancedNotificationService

router = APIRouter()


def generate_ticket_number():
    """Generate a unique ticket number"""
    prefix = "TKT"
    suffix = ''.join(secrets.choice(string.digits) for _ in range(6))
    return f"{prefix}-{suffix}"


@router.get("/tickets")
async def get_user_tickets(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """Get support tickets for the current user"""
    
    query = select(SupportTicket).where(SupportTicket.user_id == current_user.id)
    
    # Apply filters
    if status_filter:
        query = query.where(SupportTicket.status == status_filter)
    if category_filter:
        query = query.where(SupportTicket.category == category_filter)
    
    # Order by creation date (newest first)
    query = query.order_by(desc(SupportTicket.created_at))
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    tickets = result.scalars().all()
    
    return {
        "success": True,
        "data": [
            {
                "id": str(ticket.id),
                "ticket_number": ticket.ticket_number,
                "subject": ticket.subject,
                "description": ticket.description,
                "category": ticket.category,
                "priority": ticket.priority,
                "status": ticket.status,
                "created_at": ticket.created_at.isoformat(),
                "updated_at": ticket.updated_at.isoformat(),
                "resolution": ticket.resolution,
                "resolution_time": ticket.resolution_time.isoformat() if ticket.resolution_time else None
            }
            for ticket in tickets
        ]
    }


@router.post("/tickets")
async def create_support_ticket(
    ticket_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new support ticket"""
    
    # Get user's current organization
    org_service = OrganizationService(db)
    organization_id = await org_service.get_current_organization(str(current_user.id))
    
    # Generate unique ticket number
    ticket_number = generate_ticket_number()
    
    # Ensure ticket number is unique
    while True:
        existing = await db.execute(
            select(SupportTicket).where(SupportTicket.ticket_number == ticket_number)
        )
        if not existing.scalar_one_or_none():
            break
        ticket_number = generate_ticket_number()
    
    # Create the ticket
    ticket = SupportTicket(
        ticket_number=ticket_number,
        user_id=current_user.id,
        organization_id=UUID(organization_id) if organization_id else None,
        subject=ticket_data["subject"],
        description=ticket_data["description"],
        category=ticket_data.get("category", "general"),
        priority=ticket_data.get("priority", "medium"),
        status="open"
    )
    
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    
    # Send notification to support team (if configured)
    try:
        notification_service = EnhancedNotificationService(db)
        await notification_service.send_support_ticket_notification(
            ticket_id=str(ticket.id),
            user_id=str(current_user.id),
            organization_id=organization_id
        )
    except Exception as e:
        # Don't fail ticket creation if notification fails
        print(f"Failed to send support ticket notification: {e}")
    
    return {
        "success": True,
        "data": {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "status": ticket.status,
            "created_at": ticket.created_at.isoformat()
        },
        "message": "Support ticket created successfully"
    }


@router.get("/tickets/{ticket_id}")
async def get_support_ticket(
    ticket_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific support ticket with messages"""
    
    # Get ticket with messages
    query = select(SupportTicket).options(
        selectinload(SupportTicket.messages)
    ).where(
        and_(
            SupportTicket.id == ticket_id,
            SupportTicket.user_id == current_user.id
        )
    )
    
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    return {
        "success": True,
        "data": {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "subject": ticket.subject,
            "description": ticket.description,
            "category": ticket.category,
            "priority": ticket.priority,
            "status": ticket.status,
            "resolution": ticket.resolution,
            "created_at": ticket.created_at.isoformat(),
            "updated_at": ticket.updated_at.isoformat(),
            "messages": [
                {
                    "id": str(msg.id),
                    "message": msg.message,
                    "is_internal": msg.is_internal,
                    "message_type": msg.message_type,
                    "created_at": msg.created_at.isoformat(),
                    "user_id": str(msg.user_id)
                }
                for msg in ticket.messages
                if not msg.is_internal  # Only show customer-visible messages
            ]
        }
    }


@router.put("/tickets/{ticket_id}")
async def update_support_ticket(
    ticket_id: UUID,
    update_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a support ticket (limited fields for users)"""
    
    # Get ticket
    query = select(SupportTicket).where(
        and_(
            SupportTicket.id == ticket_id,
            SupportTicket.user_id == current_user.id
        )
    )
    
    result = await db.execute(query)
    ticket = result.scalar_one_or_none()
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support ticket not found"
        )
    
    # Users can only update certain fields
    allowed_fields = ["priority"]
    
    for field, value in update_data.items():
        if field in allowed_fields:
            setattr(ticket, field, value)
    
    ticket.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(ticket)
    
    return {
        "success": True,
        "data": {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "status": ticket.status,
            "updated_at": ticket.updated_at.isoformat()
        },
        "message": "Support ticket updated successfully"
    }


@router.post("/contact")
async def send_contact_message(
    message_data: Dict[str, Any],
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a contact message"""
    
    # Get user's current organization
    org_service = OrganizationService(db)
    organization_id = await org_service.get_current_organization(str(current_user.id))
    
    # Create contact message
    contact_message = ContactMessage(
        name=message_data["name"],
        email=message_data["email"],
        subject=message_data["subject"],
        message=message_data["message"],
        user_id=current_user.id,
        organization_id=UUID(organization_id) if organization_id else None,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    db.add(contact_message)
    await db.commit()
    
    # Send notification to support team
    try:
        notification_service = EnhancedNotificationService(db)
        await notification_service.send_contact_message_notification(
            message_id=str(contact_message.id),
            user_id=str(current_user.id),
            organization_id=organization_id
        )
    except Exception as e:
        print(f"Failed to send contact message notification: {e}")
    
    return {
        "success": True,
        "message": "Contact message sent successfully. We'll get back to you soon!"
    }


@router.get("/help-articles")
async def get_help_articles(
    category: Optional[str] = None,
    search: Optional[str] = None,
    featured_only: bool = False,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get published help articles"""
    
    query = select(HelpArticle).where(HelpArticle.is_published == True)
    
    # Apply filters
    if category:
        query = query.where(HelpArticle.category == category)
    if featured_only:
        query = query.where(HelpArticle.is_featured == True)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                HelpArticle.title.ilike(search_term),
                HelpArticle.content.ilike(search_term),
                HelpArticle.excerpt.ilike(search_term)
            )
        )
    
    # Order by featured first, then by creation date
    query = query.order_by(desc(HelpArticle.is_featured), desc(HelpArticle.created_at))
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    articles = result.scalars().all()
    
    return {
        "success": True,
        "data": [
            {
                "id": str(article.id),
                "title": article.title,
                "slug": article.slug,
                "excerpt": article.excerpt,
                "category": article.category,
                "subcategory": article.subcategory,
                "is_featured": article.is_featured,
                "view_count": article.view_count,
                "helpful_votes": article.helpful_votes,
                "unhelpful_votes": article.unhelpful_votes,
                "created_at": article.created_at.isoformat(),
                "updated_at": article.updated_at.isoformat()
            }
            for article in articles
        ]
    }


@router.get("/help-articles/{article_id}")
async def get_help_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific help article"""
    
    query = select(HelpArticle).where(
        and_(
            HelpArticle.id == article_id,
            HelpArticle.is_published == True
        )
    )
    
    result = await db.execute(query)
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Help article not found"
        )
    
    # Increment view count
    article.view_count += 1
    await db.commit()
    
    return {
        "success": True,
        "data": {
            "id": str(article.id),
            "title": article.title,
            "slug": article.slug,
            "content": article.content,
            "excerpt": article.excerpt,
            "category": article.category,
            "subcategory": article.subcategory,
            "tags": article.tags,
            "is_featured": article.is_featured,
            "view_count": article.view_count,
            "helpful_votes": article.helpful_votes,
            "unhelpful_votes": article.unhelpful_votes,
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat()
        }
    }
