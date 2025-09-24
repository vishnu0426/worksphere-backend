"""
Mention service for handling @mentions in comments
"""
import re
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.comment import Comment
from app.models.mention import Mention
from app.models.card import Card
from app.models.column import Column
from app.models.board import Board
from app.models.project import Project
from app.services.enhanced_email_notification_service import get_enhanced_notification_service

logger = logging.getLogger(__name__)


class MentionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def extract_mentions_from_text(self, text: str, organization_id: str) -> List[Dict[str, Any]]:
        """
        Extract @mentions from text and return user information
        Format: @username or @first.last
        """
        # Find all @mentions in the text
        mention_pattern = r'@([a-zA-Z0-9._-]+)'
        mentions = re.findall(mention_pattern, text)
        
        if not mentions:
            return []

        # Get organization members
        org_members_result = await self.db.execute(
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.user))
            .where(OrganizationMember.organization_id == organization_id)
        )
        org_members = org_members_result.scalars().all()

        # Create a mapping of possible usernames to users
        user_mapping = {}
        for member in org_members:
            user = member.user
            # Add various username formats
            username_formats = [
                user.email.split('@')[0],  # email prefix
                f"{user.first_name.lower()}.{user.last_name.lower()}",  # first.last
                f"{user.first_name.lower()}{user.last_name.lower()}",  # firstlast
                user.first_name.lower(),  # first name only
            ]
            
            for username_format in username_formats:
                if username_format not in user_mapping:
                    user_mapping[username_format] = user

        # Match mentions to actual users
        valid_mentions = []
        for mention in mentions:
            mention_lower = mention.lower()
            if mention_lower in user_mapping:
                user = user_mapping[mention_lower]
                valid_mentions.append({
                    'mention_text': f'@{mention}',
                    'user_id': str(user.id),
                    'user_name': f"{user.first_name} {user.last_name}",
                    'user_email': user.email
                })

        return valid_mentions

    async def create_mentions(
        self, 
        comment_id: str, 
        mentioned_by_user_id: str, 
        mentions: List[Dict[str, Any]]
    ) -> List[Mention]:
        """Create mention records in the database"""
        mention_objects = []
        
        for mention_data in mentions:
            mention = Mention(
                comment_id=comment_id,
                mentioned_user_id=mention_data['user_id'],
                mentioned_by_user_id=mentioned_by_user_id,
                mention_text=mention_data['mention_text']
            )
            self.db.add(mention)
            mention_objects.append(mention)
        
        await self.db.flush()  # Get IDs
        return mention_objects

    async def send_mention_notifications(
        self, 
        comment_id: str, 
        mentions: List[Dict[str, Any]], 
        mentioned_by_user_id: str
    ):
        """Send email notifications for mentions"""
        try:
            # Get comment and card details
            comment_result = await self.db.execute(
                select(Comment)
                .options(
                    selectinload(Comment.card)
                    .selectinload(Card.column)
                    .selectinload(Column.board)
                    .selectinload(Board.project),
                    selectinload(Comment.user)
                )
                .where(Comment.id == comment_id)
            )
            comment = comment_result.scalar_one_or_none()
            
            if not comment:
                logger.error(f"Comment {comment_id} not found for mention notifications")
                return

            card = comment.card
            project = card.column.board.project
            organization_id = str(project.organization_id)
            
            # Get the user who made the mention
            mentioned_by_result = await self.db.execute(
                select(User).where(User.id == mentioned_by_user_id)
            )
            mentioned_by_user = mentioned_by_result.scalar_one_or_none()
            
            if not mentioned_by_user:
                logger.error(f"User {mentioned_by_user_id} not found for mention notifications")
                return

            # Send notifications to each mentioned user
            notification_service = get_enhanced_notification_service(self.db)
            
            for mention in mentions:
                await notification_service.send_mention_notification(
                    mentioned_user_id=mention['user_id'],
                    card_id=str(card.id),
                    card_title=card.title,
                    comment_content=comment.content,
                    mentioned_by_user_id=str(mentioned_by_user.id),
                    mentioned_by_name=f"{mentioned_by_user.first_name} {mentioned_by_user.last_name}",
                    project_name=project.name,
                    organization_id=organization_id
                )

            logger.info(f"Sent mention notifications for {len(mentions)} mentions in comment {comment_id}")

        except Exception as e:
            logger.error(f"Failed to send mention notifications: {e}")

    async def get_organization_members_for_autocomplete(self, organization_id: str, search_term: str = "") -> List[Dict[str, Any]]:
        """Get organization members for mention autocomplete"""
        query = select(OrganizationMember).options(
            selectinload(OrganizationMember.user)
        ).where(OrganizationMember.organization_id == organization_id)
        
        if search_term:
            # Search in user's name and email
            query = query.join(User).where(
                (User.first_name.ilike(f"%{search_term}%")) |
                (User.last_name.ilike(f"%{search_term}%")) |
                (User.email.ilike(f"%{search_term}%"))
            )
        
        result = await self.db.execute(query.limit(10))  # Limit for autocomplete
        members = result.scalars().all()
        
        autocomplete_data = []
        for member in members:
            user = member.user
            # Generate possible username formats
            username_formats = [
                user.email.split('@')[0],
                f"{user.first_name.lower()}.{user.last_name.lower()}",
                user.first_name.lower()
            ]
            
            autocomplete_data.append({
                'id': str(user.id),
                'name': f"{user.first_name} {user.last_name}",
                'email': user.email,
                'username_suggestions': username_formats,
                'primary_username': username_formats[0]  # Use email prefix as primary
            })
        
        return autocomplete_data


def get_mention_service(db: AsyncSession) -> MentionService:
    """Factory function to get mention service instance"""
    return MentionService(db)
