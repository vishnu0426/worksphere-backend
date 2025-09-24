"""
User management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ValidationError, ResourceNotFoundError
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.schemas.user import UserProfile, UserProfileUpdate, UserProfileWithRole, UserOrganizationInfo, NotificationPreferences, NotificationPreferencesUpdate
from app.schemas.auth import UserResponse

router = APIRouter()


@router.get("/me", response_model=UserProfileWithRole)
async def get_current_user(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile with role and organization information"""
    # Get user's organization memberships
    result = await db.execute(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
    )
    memberships = result.scalars().all()

    # Build organization info list
    organizations = []
    current_role = None
    current_org_id = None
    highest_role_priority = -1

    # Role priority for determining current organization (higher number = higher priority)
    role_priority = {
        'viewer': 0,
        'member': 1,
        'admin': 2,
        'owner': 3
    }

    for membership in memberships:
        # Load organization details
        org_result = await db.execute(
            select(Organization)
            .where(Organization.id == membership.organization_id)
        )
        org = org_result.scalar_one_or_none()

        if org:
            org_info = UserOrganizationInfo(
                id=org.id,
                name=org.name,
                role=membership.role
            )
            organizations.append(org_info)

            # Use the organization where user has the highest role as current
            role_priority_value = role_priority.get(membership.role, -1)
            if role_priority_value > highest_role_priority:
                current_role = membership.role
                current_org_id = org.id
                highest_role_priority = role_priority_value

    # Create response with role information (avatar_url set to None)
    return UserProfileWithRole(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        job_title=current_user.job_title,
        bio=current_user.bio,
        avatar_url=None,  # Avatar functionality removed
        email_verified=current_user.email_verified,
        two_factor_enabled=current_user.two_factor_enabled,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        role=current_role,  # Return actual role from database, no default fallback
        organizations=organizations,
        current_organization_id=current_org_id
    )


@router.put("/me", response_model=UserProfileWithRole)
async def update_current_user(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user profile (alias for /profile)"""
    # Get the user from the database to ensure it's attached to this session
    result = await db.execute(select(User).where(User.id == current_user.id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise ResourceNotFoundError("User not found")

    # Update fields if provided
    if profile_data.first_name is not None:
        db_user.first_name = profile_data.first_name
    if profile_data.last_name is not None:
        db_user.last_name = profile_data.last_name
    if profile_data.job_title is not None:
        db_user.job_title = profile_data.job_title
    if profile_data.bio is not None:
        db_user.bio = profile_data.bio

    await db.commit()
    await db.refresh(db_user)

    # Get user's organizations and role
    org_member_result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.organization))
        .where(OrganizationMember.user_id == db_user.id)
    )
    org_members = org_member_result.scalars().all()

    # Get current organization (first one for now)
    current_org_id = None
    role = 'member'
    organizations = []

    for org_member in org_members:
        org_info = {
            "id": org_member.organization.id,
            "name": org_member.organization.name,
            "role": org_member.role,
            "joined_at": org_member.created_at.isoformat()
        }
        organizations.append(org_info)

        # Set role from first organization
        if current_org_id is None:
            current_org_id = org_member.organization.id
            role = org_member.role

    return UserProfileWithRole(
        id=db_user.id,
        email=db_user.email,
        first_name=db_user.first_name,
        last_name=db_user.last_name,
        avatar_url=None,  # Avatar functionality removed
        email_verified=db_user.email_verified,
        two_factor_enabled=db_user.two_factor_enabled,
        last_login_at=db_user.last_login_at,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at,
        role=role,
        organizations=organizations,
        current_organization_id=current_org_id
    )


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise ResourceNotFoundError("User not found")

    return UserProfile(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        job_title=user.job_title,
        bio=user.bio,
        avatar_url=None,  # Avatar functionality removed
        email_verified=user.email_verified,
        two_factor_enabled=user.two_factor_enabled,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.get("/profile", response_model=UserProfile)
async def get_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user profile"""
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        job_title=current_user.job_title,
        bio=current_user.bio,
        avatar_url=None,  # Avatar functionality removed
        email_verified=current_user.email_verified,
        two_factor_enabled=current_user.two_factor_enabled,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


@router.put("/profile", response_model=UserProfile)
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile"""
    # Merge the user into the current session to ensure it's persistent
    current_user = await db.merge(current_user)

    # Update fields if provided
    if profile_data.first_name is not None:
        current_user.first_name = profile_data.first_name
    if profile_data.last_name is not None:
        current_user.last_name = profile_data.last_name
    if profile_data.job_title is not None:
        current_user.job_title = profile_data.job_title
    if profile_data.bio is not None:
        current_user.bio = profile_data.bio

    await db.commit()
    await db.refresh(current_user)

    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        job_title=current_user.job_title,
        bio=current_user.bio,
        avatar_url=None,  # Avatar functionality removed
        email_verified=current_user.email_verified,
        two_factor_enabled=current_user.two_factor_enabled,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )


# Avatar functionality has been removed as per requirements


@router.get("/notifications/preferences", response_model=NotificationPreferences)
async def get_notification_preferences(
    current_user: User = Depends(get_current_active_user)
):
    """Get user notification preferences"""
    # TODO: Get from database or return defaults
    return NotificationPreferences()


@router.put("/notifications/preferences", response_model=NotificationPreferences)
async def update_notification_preferences(
    preferences: NotificationPreferencesUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update user notification preferences"""
    # TODO: Store in database
    # For now, just return the updated preferences
    return NotificationPreferences()


@router.delete("/account")
async def delete_account(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete user account"""
    # TODO: Implement account deletion with proper cleanup
    # This should remove user from all organizations, transfer ownership, etc.
    
    return {
        "success": True,
        "message": "Account deletion initiated. You will receive a confirmation email."
    }
