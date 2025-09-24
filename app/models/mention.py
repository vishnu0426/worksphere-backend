"""
Mention model for tracking @mentions in comments
"""
from sqlalchemy import Column, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Mention(Base):
    __tablename__ = "mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    comment_id = Column(UUID(as_uuid=True), ForeignKey('comments.id', ondelete='CASCADE'), nullable=False)
    mentioned_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    mentioned_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    mention_text = Column(Text, nullable=False)  # The actual @username text
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    comment = relationship("Comment", back_populates="mentions")
    mentioned_user = relationship("User", foreign_keys=[mentioned_user_id])
    mentioned_by_user = relationship("User", foreign_keys=[mentioned_by_user_id])

    def __repr__(self):
        return f"<Mention(id={self.id}, mentioned_user_id={self.mentioned_user_id})>"
