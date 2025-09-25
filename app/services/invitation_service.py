"""
Email Domain-Based Invitation Service
Handle organization domain-based email invitations with temporary passwords
"""
import secrets
import string
import smtplib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)

from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.organization_settings import InvitationToken, OrganizationSettings
from app.models.project import Project
from app.models.notification import Notification
from app.core.security import hash_password, verify_password
from app.core.exceptions import ValidationError, ResourceNotFoundError
from app.config import settings
from app.services.email_service import email_service
from app.services.session_service import SessionService
from app.services.organization_service import OrganizationService
import logging

logger = logging.getLogger(__name__)


class InvitationService:
    """Service for handling email invitations with domain validation"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def send_organization_invitation(
        self,
        email: str,
        organization_id: str,
        invited_role: str,
        inviter_id: str,
        project_id: Optional[str] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send organization invitation with domain validation"""
        
        # Validate email domain
        await self._validate_email_domain(email, organization_id)
        
        # Check if user already exists
        existing_user = await self._get_user_by_email(email)
        if existing_user:
            # Check if already member
            existing_member = await self._get_organization_member(existing_user.id, organization_id)
            if existing_member:
                raise ValidationError("User is already a member of this organization")
        
        # Generate invitation token and temporary password
        token = self._generate_secure_token()
        temp_password = self._generate_temporary_password()
        
        # Create invitation record
        invitation = InvitationToken(
            token=token,
            email=email.lower().strip(),
            organization_id=organization_id,
            project_id=project_id,
            invited_role=invited_role,
            temporary_password=hash_password(temp_password),
            invited_by=inviter_id,
            invitation_message=message,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48)
        )
        
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        
        # Get organization and inviter details
        org_details = await self._get_organization_details(organization_id)
        inviter_details = await self._get_user_details(inviter_id)
        project_details = await self._get_project_details(project_id) if project_id else None
        
        # Send invitation email
        email_sent = await self._send_invitation_email(
            email=email,
            token=token,
            temp_password=temp_password,
            organization=org_details,
            inviter=inviter_details,
            project=project_details,
            role=invited_role,
            message=message
        )

        # Create notification for the invited user (if they already exist in the system)
        existing_user = await self._get_user_by_email(email)
        if existing_user:
            notification = Notification(
                user_id=existing_user.id,
                organization_id=organization_id,
                title=f"Project Invitation from {org_details['name']}",
                message=f"You've been invited to join {org_details['name']} as a {invited_role}. Check your email for details.",
                type="team_invite",
                priority="normal",
                action_url=f"/accept-invitation?token={token}",
                notification_metadata={
                    'invitation_id': str(invitation.id),
                    'organization_name': org_details['name'],
                    'inviter_name': f"{inviter_details['first_name']} {inviter_details['last_name']}",
                    'role': invited_role,
                    'project_name': project_details['name'] if project_details else None
                }
            )
            self.db.add(notification)
            await self.db.commit()

        return {
            'invitation_id': str(invitation.id),
            'token': token,
            'temporary_password': temp_password,  # In production, don't return this
            'email_sent': email_sent,
            'expires_at': invitation.expires_at.isoformat()
        }

    async def send_board_invitation(
        self,
        email: str,
        organization_id: str,
        project_id: str,
        board_id: str,
        invited_role: str,
        inviter_id: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send board-specific invitation with enhanced email template"""

        # Validate email domain
        await self._validate_email_domain(email, organization_id)

        # Check if user already exists
        existing_user = await self._get_user_by_email(email)
        if existing_user:
            # Check if already member
            existing_member = await self._get_organization_member(existing_user.id, organization_id)
            if existing_member:
                raise ValidationError("User is already a member of this organization")

        # Generate invitation token and temporary password
        token = self._generate_secure_token()
        temp_password = self._generate_temporary_password()

        # Create invitation record with board context
        invitation = InvitationToken(
            token=token,
            email=email.lower().strip(),
            organization_id=organization_id,
            project_id=project_id,
            invited_role=invited_role,
            temporary_password=hash_password(temp_password),
            invited_by=inviter_id,
            invitation_message=message,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=48)
        )

        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)

        # Get organization, project, board, and inviter details
        org_details = await self._get_organization_details(organization_id)
        inviter_details = await self._get_user_details(inviter_id)
        project_details = await self._get_project_details(project_id)
        board_details = await self._get_board_details(board_id)

        # Send board invitation email
        email_sent = await self._send_invitation_email(
            email=email,
            token=token,
            temp_password=temp_password,
            organization=org_details,
            inviter=inviter_details,
            project=project_details,
            role=invited_role,
            message=message,
            board_name=board_details['name'] if board_details else None
        )

        # Create notification for the invited user (if they already exist in the system)
        existing_user = await self._get_user_by_email(email)
        if existing_user:
            notification = Notification(
                user_id=existing_user.id,
                organization_id=organization_id,
                title=f"Board Invitation from {org_details['name']}",
                message=f"You've been invited to collaborate on the {board_details['name'] if board_details else 'board'} board as a {invited_role}. Check your email for details.",
                type="board_invite",
                priority="normal",
                action_url=f"/accept-invitation?token={token}",
                notification_metadata={
                    'invitation_id': str(invitation.id),
                    'organization_name': org_details['name'],
                    'project_name': project_details['name'] if project_details else None,
                    'board_name': board_details['name'] if board_details else None,
                    'inviter_name': f"{inviter_details['first_name']} {inviter_details['last_name']}",
                    'role': invited_role
                }
            )
            self.db.add(notification)
            await self.db.commit()

        return {
            'invitation_id': str(invitation.id),
            'token': token,
            'temporary_password': temp_password,  # In production, don't return this
            'email_sent': email_sent,
            'expires_at': invitation.expires_at.isoformat(),
            'board_name': board_details['name'] if board_details else None
        }

    async def accept_invitation(
        self,
        token: str,
        email: str,
        temp_password: str,
        new_password: str,
        first_name: str,
        last_name: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """Accept invitation and create/update user account"""
        
        # Get invitation
        invitation = await self._get_invitation_by_token(token)
        if not invitation:
            raise ValidationError("Invalid or expired invitation token")

        if invitation.is_used:
            raise ValidationError("Invitation has already been used")

        if invitation.expires_at < datetime.now(timezone.utc):
            raise ValidationError("Invitation has expired. Invitations are valid for 48 hours only.")

        # Validate that the provided email matches the invitation email
        if email.lower().strip() != invitation.email.lower().strip():
            raise ValidationError("The email address provided does not match the invitation email.")
        
        # Verify temporary password with enhanced error handling
        try:
            if not temp_password or not temp_password.strip():
                raise ValidationError("Temporary password is required")

            if not verify_password(temp_password, invitation.temporary_password):
                raise ValidationError("Invalid temporary password. Please check your invitation email for the correct temporary password.")
        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            # Handle any unexpected errors in password verification
            logger.error(f"Error verifying temporary password: {str(e)}")
            raise ValidationError("Invalid temporary password")
        
        # Check if user already exists
        existing_user = await self._get_user_by_email(invitation.email)
        
        if existing_user:
            # Update existing user's password - they've set it during invitation acceptance
            existing_user.password_hash = hash_password(new_password)
            existing_user.requires_password_reset = False  # Password was set during invitation acceptance
            user = existing_user
        else:
            # Create new user - they've already set their password during invitation acceptance
            # Handle optional last_name - use empty string if None to avoid database constraint violation
            user = User(
                email=invitation.email,
                first_name=first_name,
                last_name=last_name or "",  # Use empty string if last_name is None
                password_hash=hash_password(new_password),
                email_verified=True,
                requires_password_reset=False  # Password was set during invitation acceptance
            )
            self.db.add(user)
            await self.db.flush()  # Get user ID
        
        # Add user to organization
        existing_member = await self._get_organization_member(user.id, invitation.organization_id)
        if not existing_member:
            member = OrganizationMember(
                organization_id=invitation.organization_id,
                user_id=user.id,
                role=invitation.invited_role,
                invited_by=invitation.invited_by
            )
            self.db.add(member)
        
        # Mark invitation as used
        invitation.is_used = True
        invitation.used_at = datetime.now(timezone.utc)

        # Create welcome notification for the new member
        org_details = await self._get_organization_details(str(invitation.organization_id))
        welcome_notification = Notification(
            user_id=user.id,
            organization_id=invitation.organization_id,
            title=f"Welcome to {org_details['name']}!",
            message=f"You've successfully joined {org_details['name']} as a {invitation.invited_role}. Start exploring your new workspace!",
            type="team_invite_accepted",
            priority="normal",
            action_url="/dashboard",
            notification_metadata={
                'organization_name': org_details['name'],
                'role': invitation.invited_role,
                'project_id': str(invitation.project_id) if invitation.project_id else None
            }
        )
        self.db.add(welcome_notification)

        # Notify the inviter that invitation was accepted
        inviter_notification = Notification(
            user_id=invitation.invited_by,
            organization_id=invitation.organization_id,
            title="Invitation Accepted",
            message=f"{user.first_name} {user.last_name} ({invitation.email}) has joined {org_details['name']}",
            type="team_invite_accepted",
            priority="normal",
            action_url="/team-members",
            notification_metadata={
                'new_member_name': f"{user.first_name} {user.last_name}",
                'new_member_email': invitation.email,
                'role': invitation.invited_role,
                'organization_name': org_details['name']
            }
        )
        self.db.add(inviter_notification)

        # Create authentication session for immediate login
        try:
            session_service = SessionService(self.db)
            session = await session_service.create_session(
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_duration_hours=24
            )

            # Set up organization context
            org_service = OrganizationService(self.db)
            await org_service.switch_organization(str(user.id), str(invitation.organization_id))

            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create session or set organization context: {str(e)}")
            raise ValidationError("Failed to complete invitation acceptance. Please try again.")

        # Get organization details for response
        org_result = await self.db.execute(
            select(Organization).where(Organization.id == invitation.organization_id)
        )
        organization = org_result.scalar_one()

        # Determine redirect URL based on role
        role_dashboard_map = {
            'owner': '/dashboard/owner',
            'admin': '/dashboard/admin',
            'member': '/dashboard/member',
            'viewer': '/dashboard/viewer'
        }
        redirect_url = role_dashboard_map.get(invitation.invited_role, '/dashboard/member')

        # Get role permissions description
        role_permissions = self._get_role_permissions_description(invitation.invited_role)

        # Send welcome email (async in background)
        try:
            await self._send_welcome_email(
                user=user,
                organization=organization,
                role=invitation.invited_role,
                role_permissions=role_permissions
            )
        except Exception as e:
            logger.warning(f"Failed to send welcome email to {user.email}: {str(e)}")
            # Don't fail the invitation acceptance if email fails

        return {
            'user_id': str(user.id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'organization_id': str(invitation.organization_id),
            'role': invitation.invited_role,
            'role_permissions': role_permissions,
            'project_id': str(invitation.project_id) if invitation.project_id else None,
            'session': session,
            'organization': organization,
            'redirect_url': redirect_url,
            'welcome_message': f"Welcome to {organization.name}! You've been added as a {invitation.invited_role}."
        }
    
    async def get_pending_invitations(self, organization_id: str) -> list:
        """Get pending invitations for organization"""
        result = await self.db.execute(
            select(InvitationToken)
            .where(
                and_(
                    InvitationToken.organization_id == organization_id,
                    InvitationToken.is_used == False,
                    InvitationToken.expires_at > datetime.now(timezone.utc)
                )
            )
            .order_by(InvitationToken.created_at.desc())
        )
        
        invitations = result.scalars().all()
        return [
            {
                'id': str(inv.id),
                'email': inv.email,
                'role': inv.invited_role,
                'project_id': str(inv.project_id) if inv.project_id else None,
                'invited_by': str(inv.invited_by),
                'created_at': inv.created_at.isoformat(),
                'expires_at': inv.expires_at.isoformat()
            }
            for inv in invitations
        ]
    
    async def cancel_invitation(self, invitation_id: str, user_id: str) -> bool:
        """Cancel pending invitation"""
        result = await self.db.execute(
            select(InvitationToken)
            .where(
                and_(
                    InvitationToken.id == invitation_id,
                    InvitationToken.invited_by == user_id,
                    InvitationToken.is_used == False
                )
            )
        )
        
        invitation = result.scalar_one_or_none()
        if not invitation:
            return False
        
        await self.db.delete(invitation)
        await self.db.commit()
        return True
    
    async def _validate_email_domain(self, email: str, organization_id: str):
        """Validate email domain against organization settings"""
        email_domain = email.split('@')[1].lower()
        
        # Get organization settings
        settings_result = await self.db.execute(
            select(OrganizationSettings)
            .where(OrganizationSettings.organization_id == organization_id)
        )
        
        org_settings = settings_result.scalar_one_or_none()
        if not org_settings or not org_settings.require_domain_match:
            return  # No domain validation required
        
        # Get organization domain info
        org_result = await self.db.execute(
            select(Organization.domain, Organization.allowed_domains)
            .where(Organization.id == organization_id)
        )
        
        org_data = org_result.first()
        if not org_data:
            raise ValidationError("Organization not found")
        
        # Build allowed domains list
        allowed_domains = []
        if org_data.domain:
            allowed_domains.append(org_data.domain.lower())
        if org_data.allowed_domains:
            allowed_domains.extend([d.lower() for d in org_data.allowed_domains])
        if org_settings.allowed_invitation_domains:
            allowed_domains.extend([d.lower() for d in org_settings.allowed_invitation_domains])
        
        if allowed_domains and email_domain not in allowed_domains:
            raise ValidationError(
                f"Email domain '{email_domain}' is not allowed. "
                f"Allowed domains: {', '.join(allowed_domains)}"
            )
    
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()
    
    async def _get_organization_member(self, user_id: str, organization_id: str) -> Optional[OrganizationMember]:
        """Get organization member"""
        result = await self.db.execute(
            select(OrganizationMember)
            .where(
                and_(
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.organization_id == organization_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_invitation_by_token(self, token: str) -> Optional[InvitationToken]:
        """Get invitation by token"""
        result = await self.db.execute(
            select(InvitationToken).where(InvitationToken.token == token)
        )
        return result.scalar_one_or_none()
    
    async def _get_organization_details(self, organization_id: str) -> Dict[str, Any]:
        """Get organization details"""
        result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        org = result.scalar_one_or_none()
        return {
            'id': str(org.id),
            'name': org.name,
            'description': org.description,
            'domain': org.domain
        } if org else {}
    
    async def _get_user_details(self, user_id: str) -> Dict[str, Any]:
        """Get user details"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return {
            'id': str(user.id),
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email
        } if user else {}
    
    async def _get_project_details(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project details"""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()
        return {
            'id': str(project.id),
            'name': project.name,
            'description': project.description
        } if project else None

    async def _get_board_details(self, board_id: str) -> Optional[Dict[str, Any]]:
        """Get board details for invitation email"""
        try:
            from app.models.board import Board
            result = await self.db.execute(
                select(Board).where(Board.id == board_id)
            )
            board = result.scalar_one_or_none()
            return {
                'id': str(board.id),
                'name': board.name,
                'description': board.description
            } if board else None
        except Exception as e:
            logger.error(f"Failed to get board details: {str(e)}")
            return None

    async def _send_invitation_email(
        self,
        email: str,
        token: str,
        temp_password: str,
        organization: Dict[str, Any],
        inviter: Dict[str, Any],
        project: Optional[Dict[str, Any]],
        role: str,
        message: Optional[str],
        board_name: Optional[str] = None
    ) -> bool:
        """Send invitation email with appropriate template based on context"""
        try:
            # Create invitation URL
            invitation_url = f"http://192.168.9.119:3000/accept-invitation?token={token}"
            inviter_name = f"{inviter['first_name']} {inviter['last_name']}"
            organization_name = organization['name']

            # Determine which email template to use based on context
            if board_name and project:
                # Board-specific invitation
                return await email_service.send_board_invitation_email(
                    to_email=email,
                    inviter_name=inviter_name,
                    organization_name=organization_name,
                    project_name=project['name'],
                    board_name=board_name,
                    role=role,
                    invitation_url=invitation_url,
                    temp_password=temp_password,
                    custom_message=message
                )
            elif project:
                # Project-specific invitation
                return await email_service.send_project_invitation_email(
                    to_email=email,
                    inviter_name=inviter_name,
                    organization_name=organization_name,
                    project_name=project['name'],
                    role=role,
                    invitation_url=invitation_url,
                    temp_password=temp_password,
                    custom_message=message
                )
            else:
                # Organization-wide invitation
                return await email_service.send_organization_invitation_email(
                    to_email=email,
                    inviter_name=inviter_name,
                    organization_name=organization_name,
                    role=role,
                    invitation_url=invitation_url,
                    temp_password=temp_password,
                    custom_message=message
                )

        except Exception as e:
            print(f"❌ Failed to send invitation email: {str(e)}")
            logger.error(f"Failed to send invitation email to {email}: {str(e)}")
            return False

    def _get_role_permissions_description(self, role: str) -> Dict[str, Any]:
        """Get role permissions description"""
        permissions_map = {
            'owner': {
                'title': 'Organization Owner',
                'description': 'Full administrative access to the organization',
                'capabilities': [
                    'Manage organization settings and billing',
                    'Add and remove members',
                    'Create and manage all projects',
                    'Access all organization data',
                    'Assign roles to other members'
                ]
            },
            'admin': {
                'title': 'Administrator',
                'description': 'Administrative access with most permissions',
                'capabilities': [
                    'Manage organization members',
                    'Create and manage projects',
                    'Access most organization data',
                    'Assign member and viewer roles'
                ]
            },
            'member': {
                'title': 'Member',
                'description': 'Standard access to assigned projects',
                'capabilities': [
                    'Access assigned projects',
                    'Create and edit content in assigned projects',
                    'Collaborate with team members',
                    'View organization member list'
                ]
            },
            'viewer': {
                'title': 'Viewer',
                'description': 'Read-only access to assigned content',
                'capabilities': [
                    'View assigned projects',
                    'Read project content and discussions',
                    'Export and download permitted content'
                ]
            }
        }
        return permissions_map.get(role, permissions_map['member'])

    async def _send_welcome_email(self, user, organization, role: str, role_permissions: Dict[str, Any]):
        """Send welcome email to newly joined user"""
        try:
            from app.services.email_service import EmailService
            email_service = EmailService()

            # Create welcome email content
            subject = f"Welcome to {organization.name}! 🎉"

            html_content = self._create_welcome_email_html(
                user_name=f"{user.first_name} {user.last_name}".strip() or user.email,
                organization_name=organization.name,
                role=role,
                role_permissions=role_permissions,
                login_url="http://192.168.9.119:3000/login",
                support_email="support@agnoworksphere.com"
            )

            await email_service.send_email(
                to_email=user.email,
                subject=subject,
                html_content=html_content
            )

            logger.info(f"Welcome email sent successfully to {user.email}")

        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")
            raise

    def _create_welcome_email_html(
        self,
        user_name: str,
        organization_name: str,
        role: str,
        role_permissions: Dict[str, Any],
        login_url: str,
        support_email: str
    ) -> str:
        """Create HTML content for welcome email"""
        capabilities_html = "".join([
            f"<li style='margin-bottom: 8px; color: #4a5568;'>{cap}</li>"
            for cap in role_permissions['capabilities']
        ])

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Welcome to {organization_name}</title>
        </head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #2d3748; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center; border-radius: 12px 12px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px; font-weight: 600;">🎉 Welcome to {organization_name}!</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 16px;">You're now part of the team</p>
            </div>

            <div style="background: white; padding: 40px 30px; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 12px 12px;">
                <p style="font-size: 18px; margin-bottom: 25px;">Hi {user_name},</p>

                <p style="margin-bottom: 25px;">Congratulations! You've successfully joined <strong>{organization_name}</strong> and your account is now active.</p>

                <div style="background: #f7fafc; padding: 25px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #667eea;">
                    <h3 style="margin: 0 0 15px 0; color: #2d3748; font-size: 18px;">Your Role: {role_permissions['title']}</h3>
                    <p style="margin: 0 0 15px 0; color: #4a5568;">{role_permissions['description']}</p>

                    <h4 style="margin: 15px 0 10px 0; color: #2d3748; font-size: 16px;">What you can do:</h4>
                    <ul style="margin: 0; padding-left: 20px;">
                        {capabilities_html}
                    </ul>
                </div>

                <div style="background: #edf2f7; padding: 25px; border-radius: 8px; margin: 25px 0;">
                    <h3 style="margin: 0 0 15px 0; color: #2d3748; font-size: 18px;">🚀 Next Steps</h3>
                    <ol style="margin: 0; padding-left: 20px; color: #4a5568;">
                        <li style="margin-bottom: 8px;">Log in to your dashboard to explore your workspace</li>
                        <li style="margin-bottom: 8px;">Complete your profile setup</li>
                        <li style="margin-bottom: 8px;">Join your first project or create a new one</li>
                        <li style="margin-bottom: 8px;">Connect with your team members</li>
                    </ol>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{login_url}" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-weight: 600; display: inline-block;">Access Your Dashboard</a>
                </div>

                <div style="border-top: 1px solid #e2e8f0; padding-top: 25px; margin-top: 30px; text-align: center;">
                    <p style="color: #718096; font-size: 14px; margin-bottom: 10px;">Need help getting started?</p>
                    <p style="color: #718096; font-size: 14px; margin: 0;">
                        Contact us at <a href="mailto:{support_email}" style="color: #667eea;">{support_email}</a>
                    </p>
                </div>
            </div>

            <div style="text-align: center; padding: 20px; color: #a0aec0; font-size: 12px;">
                <p style="margin: 0;">© 2024 Agno WorkSphere. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

    def _create_invitation_email_html(
        self,
        email: str,
        token: str,
        temp_password: str,
        organization: Dict[str, Any],
        inviter: Dict[str, Any],
        project: Optional[Dict[str, Any]],
        role: str,
        message: Optional[str]
    ) -> str:
        """Create HTML email body for invitation"""
        project_info = f"<p><strong>Project:</strong> {project['name']}</p>" if project else ""
        custom_message = f"<p><strong>Message from {inviter['first_name']}:</strong><br>{message}</p>" if message else ""
        
        return f"""
        <html>
        <body>
            <h2>You're invited to join {organization['name']}!</h2>
            
            <p>Hello,</p>
            
            <p>{inviter['first_name']} {inviter['last_name']} has invited you to join <strong>{organization['name']}</strong> as a <strong>{role}</strong>.</p>
            
            {project_info}
            {custom_message}
            
            <h3>Getting Started:</h3>
            <ol>
                <li>Click the link below to accept the invitation</li>
                <li>Use the temporary password provided to log in</li>
                <li>Set up your new password</li>
                <li>Start collaborating!</li>
            </ol>
            
            <p><strong>Invitation Token:</strong> {token}</p>
            <p><strong>Temporary Password:</strong> {temp_password}</p>
            
            <p><a href="{settings.FRONTEND_URL}/accept-invitation?token={token}" 
               style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
               Accept Invitation
            </a></p>
            
            <p><small>This invitation will expire in 48 hours.</small></p>
            
            <p>Best regards,<br>The {organization['name']} Team</p>
        </body>
        </html>
        """
    
    def _generate_secure_token(self) -> str:
        """Generate secure invitation token"""
        return secrets.token_urlsafe(32)
    
    def _generate_temporary_password(self) -> str:
        """Generate temporary password"""
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(secrets.choice(alphabet) for _ in range(12))
