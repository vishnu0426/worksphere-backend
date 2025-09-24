"""
Support system models for help desk, tickets, and knowledge base
"""
import uuid
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_number = Column(String(20), unique=True, nullable=False)  # Auto-generated ticket number
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    
    # Ticket details
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)  # general, technical, billing, feature, bug, security
    priority = Column(String(20), default='medium', nullable=False)  # low, medium, high, urgent
    status = Column(String(20), default='open', nullable=False)  # open, in_progress, resolved, closed
    
    # Assignment and tracking
    assigned_to = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # Support agent
    resolution = Column(Text, nullable=True)
    resolution_time = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    ticket_metadata = Column(JSON, nullable=True)  # Additional ticket data
    tags = Column(JSON, nullable=True)  # Tags for categorization
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="support_tickets")
    assigned_agent = relationship("User", foreign_keys=[assigned_to])
    organization = relationship("Organization")
    messages = relationship("SupportMessage", back_populates="ticket", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SupportTicket(id={self.id}, ticket_number={self.ticket_number}, subject={self.subject})>"


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey('support_tickets.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Message content
    message = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False, nullable=False)  # Internal notes vs customer-visible
    message_type = Column(String(20), default='message', nullable=False)  # message, status_update, resolution
    
    # Attachments
    attachments = Column(JSON, nullable=True)  # File attachments metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    ticket = relationship("SupportTicket", back_populates="messages")
    user = relationship("User")

    def __repr__(self):
        return f"<SupportMessage(id={self.id}, ticket_id={self.ticket_id})>"


class HelpArticle(Base):
    __tablename__ = "help_articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Article details
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False)  # URL-friendly identifier
    content = Column(Text, nullable=False)
    excerpt = Column(Text, nullable=True)  # Short summary
    
    # Categorization
    category = Column(String(100), nullable=False)
    subcategory = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)  # Tags for search and filtering
    
    # Publishing
    is_published = Column(Boolean, default=False, nullable=False)
    is_featured = Column(Boolean, default=False, nullable=False)
    
    # SEO and metadata
    meta_title = Column(String(255), nullable=True)
    meta_description = Column(String(500), nullable=True)
    
    # Analytics
    view_count = Column(Integer, default=0, nullable=False)
    helpful_votes = Column(Integer, default=0, nullable=False)
    unhelpful_votes = Column(Integer, default=0, nullable=False)
    
    # Authoring
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    author = relationship("User")

    def __repr__(self):
        return f"<HelpArticle(id={self.id}, title={self.title}, slug={self.slug})>"


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Contact details
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Optional user association
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)
    
    # Status tracking
    status = Column(String(20), default='new', nullable=False)  # new, read, responded, closed
    responded_at = Column(DateTime(timezone=True), nullable=True)
    response_message = Column(Text, nullable=True)
    
    # Metadata
    ip_address = Column(String(45), nullable=True)  # For spam prevention
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    organization = relationship("Organization")

    def __repr__(self):
        return f"<ContactMessage(id={self.id}, name={self.name}, subject={self.subject})>"


class SupportCategory(Base):
    __tablename__ = "support_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Category details
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    slug = Column(String(100), nullable=False, unique=True)
    
    # Hierarchy
    parent_id = Column(UUID(as_uuid=True), ForeignKey('support_categories.id'), nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    
    # Display settings
    icon = Column(String(50), nullable=True)  # Icon name for UI
    color = Column(String(7), nullable=True)  # Hex color code
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    parent = relationship("SupportCategory", remote_side=[id])
    children = relationship("SupportCategory")

    def __repr__(self):
        return f"<SupportCategory(id={self.id}, name={self.name})>"


class SupportSettings(Base):
    __tablename__ = "support_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    
    # Support configuration
    auto_assign_tickets = Column(Boolean, default=False, nullable=False)
    default_priority = Column(String(20), default='medium', nullable=False)
    business_hours_enabled = Column(Boolean, default=False, nullable=False)
    business_hours = Column(JSON, nullable=True)  # Business hours configuration
    
    # Response time SLAs
    response_time_low = Column(Integer, default=72, nullable=False)  # Hours
    response_time_medium = Column(Integer, default=24, nullable=False)
    response_time_high = Column(Integer, default=8, nullable=False)
    response_time_urgent = Column(Integer, default=2, nullable=False)
    
    # Email settings
    support_email = Column(String(255), nullable=True)
    email_notifications_enabled = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")

    def __repr__(self):
        return f"<SupportSettings(id={self.id}, organization_id={self.organization_id})>"
