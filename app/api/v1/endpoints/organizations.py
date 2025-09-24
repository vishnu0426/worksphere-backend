"""
Organization management endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user, require_admin, require_member, require_admin_by_path, require_member_by_path
from app.core.exceptions import ValidationError, ResourceNotFoundError, InsufficientPermissionsError
from app.core.cache import cache_response
from app.models.user import User
from app.models.organization import Organization, OrganizationMember
from app.models.organization_settings import OrganizationSettings
from app.models.project import Project
from app.models.activity_log import ActivityLog
from app.schemas.organization import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationMemberResponse, MemberInvite, MemberRoleUpdate,
    BillingInfo, SubscriptionInfo
)
from app.schemas.organization_enhanced import (
    OrganizationSettingsCreate, OrganizationSettingsUpdate, OrganizationSettingsResponse
)
from app.schemas.organization_enhanced import InvitationAcceptRequest, InvitationAcceptResponse
from app.schemas.auth import UserResponse, TokenResponse, OrganizationInfo
from app.services.invitation_service import InvitationService
from app.services.dashboard_data_service import DashboardDataService

router = APIRouter()


@router.get("", response_model=List[OrganizationResponse])
@cache_response(ttl=60, key_prefix="organizations")  # Cache for 1 minute
async def get_organizations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all organizations for current user with optimized query"""
    # Use a single optimized query with proper joins and indexes
    result = await db.execute(
        select(Organization, OrganizationMember.role)
        .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
        .where(OrganizationMember.user_id == current_user.id)
        .order_by(Organization.name)
    )

    organizations = []
    for org, _ in result.all():  # role not used currently
        org_response = OrganizationResponse.model_validate(org)
        organizations.append(org_response)

    return organizations


@router.post("", response_model=OrganizationResponse)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new organization - Restricted access"""
    # Use enhanced RBAC to check organization creation permission
    from app.services.enhanced_role_permissions import EnhancedRolePermissions, Permission

    # For organization creation, we need to check if the user has global permission
    # Since this is creating a new organization, we check against any existing organization
    # where the user is an owner, or allow first-time organization creation for new users

    existing_memberships = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )
    all_memberships = existing_memberships.scalars().all()

    # Implement stricter organization creation policy
    # Only allow organization creation for:
    # 1. New users with no existing memberships (first organization)
    # 2. Users who are owners in ALL their existing organizations

    if all_memberships:
        # User has existing memberships - check if they have any non-owner roles
        non_owner_roles = [m.role for m in all_memberships if m.role != 'owner']

        # If user has any non-owner role (member, viewer, admin), deny creation
        if non_owner_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Organization creation denied. Users with member, viewer, or admin roles cannot create organizations. Current roles: {[m.role for m in all_memberships]}"
            )
    # If user has no memberships, allow first organization creation (new user scenario)

    # Create organization
    organization = Organization(
        name=org_data.name,
        description=org_data.description,
        domain=org_data.domain,
        allowed_domains=org_data.allowed_domains,
        contact_email=org_data.contact_email,
        contact_phone=org_data.contact_phone,
        address_line1=org_data.address_line1,
        address_line2=org_data.address_line2,
        city=org_data.city,
        state=org_data.state,
        postal_code=org_data.postal_code,
        country=org_data.country,
        organization_category=org_data.organization_category,
        language=org_data.language,
        created_by=current_user.id
    )
    
    db.add(organization)
    await db.flush()  # Get the ID
    
    # Add creator as owner
    member = OrganizationMember(
        organization_id=organization.id,
        user_id=current_user.id,
        role="owner"
    )
    
    db.add(member)

    # Create a sample project for the new organization
    sample_project = Project(
        organization_id=organization.id,
        name="Welcome Project",
        description="Your first project to get started with Agno WorkSphere",
        status="active",
        priority="medium",
        created_by=current_user.id
    )

    db.add(sample_project)
    await db.commit()
    await db.refresh(organization)

    return OrganizationResponse.from_orm(organization)


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization by ID"""
    # Check if user is member
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Not a member of this organization")
    
    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()
    if not organization:
        raise ResourceNotFoundError("Organization not found")
    
    return OrganizationResponse.from_orm(organization)


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: str,
    org_data: OrganizationUpdate,
    current_user: User = Depends(get_current_active_user),
    org_member: OrganizationMember = Depends(require_admin_by_path),
    db: AsyncSession = Depends(get_db)
):
    """Update organization"""
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()
    if not organization:
        raise ResourceNotFoundError("Organization not found")
    
    # Update fields if provided
    if org_data.name is not None:
        organization.name = org_data.name
    if org_data.description is not None:
        organization.description = org_data.description
    if org_data.domain is not None:
        organization.domain = org_data.domain
    if org_data.allowed_domains is not None:
        organization.allowed_domains = org_data.allowed_domains
    if org_data.contact_email is not None:
        organization.contact_email = org_data.contact_email
    if org_data.contact_phone is not None:
        organization.contact_phone = org_data.contact_phone
    if org_data.address_line1 is not None:
        organization.address_line1 = org_data.address_line1
    if org_data.address_line2 is not None:
        organization.address_line2 = org_data.address_line2
    if org_data.city is not None:
        organization.city = org_data.city
    if org_data.state is not None:
        organization.state = org_data.state
    if org_data.postal_code is not None:
        organization.postal_code = org_data.postal_code
    if org_data.country is not None:
        organization.country = org_data.country
    if org_data.organization_category is not None:
        organization.organization_category = org_data.organization_category
    if org_data.allowed_domains is not None:
        organization.allowed_domains = org_data.allowed_domains
    if org_data.contact_email is not None:
        organization.contact_email = org_data.contact_email
    if org_data.contact_phone is not None:
        organization.contact_phone = org_data.contact_phone
    if org_data.address_line1 is not None:
        organization.address_line1 = org_data.address_line1
    if org_data.address_line2 is not None:
        organization.address_line2 = org_data.address_line2
    if org_data.city is not None:
        organization.city = org_data.city
    if org_data.state is not None:
        organization.state = org_data.state
    if org_data.postal_code is not None:
        organization.postal_code = org_data.postal_code
    if org_data.country is not None:
        organization.country = org_data.country
    if org_data.organization_category is not None:
        organization.organization_category = org_data.organization_category
    
    await db.commit()
    await db.refresh(organization)
    
    return OrganizationResponse.from_orm(organization)


@router.delete("/{organization_id}")
async def delete_organization(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete organization (owner only)"""
    # Check if user is owner
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role == "owner"
        )
    )
    if not member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Only organization owner can delete organization")
    
    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()
    if not organization:
        raise ResourceNotFoundError("Organization not found")
    
    # Delete organization (cascade will handle members, projects, etc.)
    await db.delete(organization)
    await db.commit()
    
    return {"success": True, "message": "Organization deleted successfully"}


@router.post("/{organization_id}/logo")
async def upload_logo(
    organization_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    org_member: OrganizationMember = Depends(require_admin_by_path),
    db: AsyncSession = Depends(get_db)
):
    """Upload organization logo"""
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise ValidationError("File must be an image")
    
    # Validate file size (max 5MB)
    if file.size > 5 * 1024 * 1024:
        raise ValidationError("File size must be less than 5MB")
    
    # TODO: Upload to S3 or local storage
    logo_url = f"/uploads/organizations/{organization_id}/logo/{file.filename}"
    
    # Update organization logo URL
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()
    if not organization:
        raise ResourceNotFoundError("Organization not found")
    
    organization.logo_url = logo_url
    await db.commit()
    
    return {
        "success": True,
        "data": {
            "logo_url": logo_url
        },
        "message": "Logo uploaded successfully"
    }


@router.delete("/{organization_id}/logo")
async def delete_logo(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    org_member: OrganizationMember = Depends(require_admin_by_path),
    db: AsyncSession = Depends(get_db)
):
    """Delete organization logo"""
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalar_one_or_none()
    if not organization:
        raise ResourceNotFoundError("Organization not found")
    
    if not organization.logo_url:
        raise ResourceNotFoundError("No logo to delete")
    
    # TODO: Delete file from storage
    
    # Remove logo URL
    organization.logo_url = None
    await db.commit()
    
    return {"success": True, "message": "Logo deleted successfully"}


@router.get("/{organization_id}/members", response_model=List[OrganizationMemberResponse])
async def get_members(
    organization_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    org_member: OrganizationMember = Depends(require_member_by_path),
    db: AsyncSession = Depends(get_db)
):
    """Get organization members"""
    offset = (page - 1) * limit

    result = await db.execute(
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.user))
        .where(OrganizationMember.organization_id == organization_id)
        .offset(offset)
        .limit(limit)
        .order_by(OrganizationMember.joined_at)
    )
    members = result.scalars().all()

    # Format response with user details
    response = []
    for member in members:
        member_data = OrganizationMemberResponse(
            id=str(member.id),
            user_id=str(member.user_id),
            role=member.role,
            joined_at=member.joined_at,
            user={
                "id": str(member.user.id),
                "email": member.user.email,
                "first_name": member.user.first_name,
                "last_name": member.user.last_name,
                "avatar_url": None  # Avatar functionality removed
            }
        )
        response.append(member_data)

    return response


@router.post("/{organization_id}/invite")
async def invite_member(
    organization_id: str,
    invite_data: MemberInvite,
    current_user: User = Depends(get_current_active_user),
    org_member: OrganizationMember = Depends(require_admin_by_path),
    db: AsyncSession = Depends(get_db)
):
    """Invite member to organization"""
    # Check if user already exists
    user_result = await db.execute(
        select(User).where(User.email == invite_data.email)
    )
    user = user_result.scalar_one_or_none()

    if user:
        # Check if already a member
        member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user.id
            )
        )
        if member_result.scalar_one_or_none():
            raise ValidationError("User is already a member of this organization")

        # Add as member
        member = OrganizationMember(
            organization_id=organization_id,
            user_id=user.id,
            role=invite_data.role,
            invited_by=current_user.id
        )
        db.add(member)
        await db.commit()

        return {"success": True, "message": "User added to organization successfully"}
    else:
        # Send invitation email and create invitation token
        invite_service = InvitationService(db)
        result = await invite_service.send_organization_invitation(
            email=invite_data.email,
            organization_id=organization_id,
            invited_role=invite_data.role,
            inviter_id=str(current_user.id)
        )
        return {"success": True, "message": "Invitation sent successfully", "data": result}


@router.delete("/{organization_id}/members/{user_id}")
async def remove_member(
    organization_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    org_member: OrganizationMember = Depends(require_admin_by_path),
    db: AsyncSession = Depends(get_db)
):
    """Remove member from organization"""
    # Cannot remove owner
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise ResourceNotFoundError("Member not found")

    if member.role == "owner":
        raise ValidationError("Cannot remove organization owner")

    # Remove member
    await db.delete(member)
    await db.commit()

    return {"success": True, "message": "Member removed successfully"}


@router.put("/{organization_id}/members/{user_id}/role")
async def update_member_role(
    organization_id: str,
    user_id: str,
    role_data: MemberRoleUpdate,
    current_user: User = Depends(get_current_active_user),
    org_member: OrganizationMember = Depends(require_admin_by_path),
    db: AsyncSession = Depends(get_db)
):
    """Update member role"""
    # Get member
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise ResourceNotFoundError("Member not found")

    # Cannot change owner role unless you are owner
    if member.role == "owner" and org_member.role != "owner":
        raise InsufficientPermissionsError("Only owner can change owner role")

    # Cannot assign owner role unless you are owner
    if role_data.role == "owner" and org_member.role != "owner":
        raise InsufficientPermissionsError("Only owner can assign owner role")

    # Update role
    member.role = role_data.role
    await db.commit()

    return {"success": True, "message": "Member role updated successfully"}


@router.get("/{organization_id}/billing", response_model=BillingInfo)
async def get_billing(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get billing information - Owner only"""
    # Check if user is owner of the organization
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    print(f"DEBUG: User {current_user.id} has role '{user_role}' in org {organization_id}")  # Debug line

    if user_role != 'owner':
        raise HTTPException(
            status_code=403,
            detail="Billing access is restricted to organization owners only"
        )

    # TODO: Get from database
    return BillingInfo()


@router.put("/{organization_id}/billing", response_model=BillingInfo)
async def update_billing(
    organization_id: str,
    billing_data: BillingInfo,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update billing information - Owner only"""
    # Check if user is owner of the organization
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if user_role != 'owner':
        raise HTTPException(
            status_code=403,
            detail="Billing access is restricted to organization owners only"
        )

    # TODO: Store in database
    return billing_data


@router.get("/{organization_id}/subscription", response_model=SubscriptionInfo)
async def get_subscription(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get subscription information - Owner only"""
    # Check if user is owner of the organization
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if user_role != 'owner':
        raise HTTPException(
            status_code=403,
            detail="Billing access is restricted to organization owners only"
        )

    # TODO: Get from database
    return SubscriptionInfo(plan="free", status="active")


@router.put("/{organization_id}/subscription", response_model=SubscriptionInfo)
async def update_subscription(
    organization_id: str,
    subscription_data: SubscriptionInfo,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update subscription information - Owner only"""
    # Check if user is owner of the organization
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if user_role != 'owner':
        raise HTTPException(
            status_code=403,
            detail="Billing access is restricted to organization owners only"
        )

    # TODO: Store in database and handle billing
    return subscription_data


@router.get("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def get_organization_settings(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization settings (admin/owner only)"""
    # Check if user is admin/owner of organization
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role.in_(['admin', 'owner'])
            )
        )
    )

    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Get settings
    settings_result = await db.execute(
        select(OrganizationSettings)
        .where(OrganizationSettings.organization_id == organization_id)
    )

    settings = settings_result.scalar_one_or_none()
    if not settings:
        raise HTTPException(status_code=404, detail="Organization settings not found")

    return settings


@router.post("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def create_organization_settings(
    organization_id: str,
    settings_data: OrganizationSettingsCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create organization settings (admin/owner only)"""
    # Check if user is admin/owner of organization
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role.in_(['admin', 'owner'])
            )
        )
    )

    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check if settings already exist
    existing_settings = await db.execute(
        select(OrganizationSettings)
        .where(OrganizationSettings.organization_id == organization_id)
    )

    if existing_settings.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Organization settings already exist. Use PUT to update.")

    # Create new settings
    settings = OrganizationSettings(
        organization_id=organization_id,
        **settings_data.model_dump()
    )

    db.add(settings)
    await db.commit()
    await db.refresh(settings)

    return settings


@router.put("/{organization_id}/settings", response_model=OrganizationSettingsResponse)
async def update_organization_settings(
    organization_id: str,
    settings_update: OrganizationSettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update organization settings (admin/owner only)"""
    # Check if user is admin/owner of organization
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role.in_(['admin', 'owner'])
            )
        )
    )

    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Get existing settings
    settings_result = await db.execute(
        select(OrganizationSettings)
        .where(OrganizationSettings.organization_id == organization_id)
    )

    settings = settings_result.scalar_one_or_none()
    if not settings:
        # Create new settings if they don't exist
        settings = OrganizationSettings(
            organization_id=organization_id,
            **settings_update.model_dump(exclude_unset=True)
        )
        db.add(settings)
    else:
        # Update existing settings
        update_data = settings_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)

    return settings


@router.get("/{organization_id}/payment-methods")
async def get_payment_methods(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get payment methods - Owner only"""
    # Check if user is owner of the organization
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if user_role != 'owner':
        raise HTTPException(
            status_code=403,
            detail="Billing access is restricted to organization owners only"
        )

    # TODO: Get from database
    return {"payment_methods": []}


@router.post("/{organization_id}/payment-methods")
async def add_payment_method(
    organization_id: str,
    payment_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add payment method - Owner only"""
    # Check if user is owner of the organization
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if user_role != 'owner':
        raise HTTPException(
            status_code=403,
            detail="Billing access is restricted to organization owners only"
        )

    # TODO: Store in database
    return {"message": "Payment method added successfully"}


@router.get("/{organization_id}/usage")
async def get_usage(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get usage statistics - Owner only"""
    # Check if user is owner of the organization
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if user_role != 'owner':
        raise HTTPException(
            status_code=403,
            detail="Billing access is restricted to organization owners only"
        )

    # TODO: Get from database
    return {"usage": {}}


@router.get("/{organization_id}/quotas")
async def get_quotas(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get quota information - Owner only"""
    # Check if user is owner of the organization
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if user_role != 'owner':
        raise HTTPException(
            status_code=403,
            detail="Billing access is restricted to organization owners only"
        )

    # TODO: Get from database
    return {"quotas": {}}


@router.get("/{organization_id}/dashboard")
async def get_organization_dashboard(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization dashboard data"""
    # Check if user is member of the organization
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You are not a member of this organization."
        )

    # Get organization data
    org_result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = org_result.scalar_one_or_none()

    if not organization:
        raise ResourceNotFoundError("Organization not found")

    # Get basic stats
    projects_result = await db.execute(
        select(Project).where(Project.organization_id == organization_id)
    )
    projects_count = len(projects_result.scalars().all())

    members_result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.organization_id == organization_id)
    )
    members_count = len(members_result.scalars().all())

    return {
        "id": organization.id,
        "name": organization.name,
        "description": organization.description,
        "stats": {
            "projects": projects_count,
            "members": members_count,
            "integrations": 0  # TODO: Implement integrations
        }
    }


@router.get("/{organization_id}/integrations")
async def get_organization_integrations(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization integrations"""
    # Check if user is member of the organization
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You are not a member of this organization."
        )

    # TODO: Implement real integrations
    # For now, return empty list
    return []


@router.get("/{organization_id}/activities")
async def get_recent_activities(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get recent organization activities"""
    # Check if user is member of the organization
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You are not a member of this organization."
        )

    # Get real activities from activity_logs table
    try:
        # Query activity logs for this organization
        activity_query = select(ActivityLog).options(
            selectinload(ActivityLog.user)
        ).where(
            ActivityLog.organization_id == organization_id
        ).order_by(
            ActivityLog.created_at.desc()
        ).limit(20)

        result = await db.execute(activity_query)
        activity_logs = result.scalars().all()

        # Transform to frontend format
        activities = []
        for log in activity_logs:
            activity = {
                "id": str(log.id),
                "type": log.action_type,
                "description": log.description,
                "timestamp": log.created_at.isoformat(),
                "user": {
                    "id": str(log.user.id) if log.user else str(current_user.id),
                    "name": f"{log.user.first_name} {log.user.last_name}".strip() if log.user and log.user.first_name else (log.user.email.split('@')[0] if log.user else current_user.email.split('@')[0]),
                    "avatar": None  # Avatar functionality removed
                },
                "project": log.entity_name or "System"
            }
            activities.append(activity)

        return activities

    except Exception as e:
        # If activity_logs table doesn't exist or has issues, return empty list
        print(f"Activity logs error: {e}")
        return []


@router.post("/{organization_id}/initialize-dashboard")
async def initialize_dashboard_data(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Initialize dashboard data for user (notifications and activities)"""
    # Check if user is member of the organization
    member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    member = member_result.scalar_one_or_none()

    if not member:
        raise HTTPException(
            status_code=403,
            detail="Access denied. You are not a member of this organization."
        )

    # Initialize dashboard data
    dashboard_service = DashboardDataService(db)
    success = await dashboard_service.ensure_user_has_initial_data(
        str(current_user.id),
        organization_id
    )

    return {
        "success": success,
        "message": "Dashboard data initialized successfully" if success else "Failed to initialize dashboard data"
    }


@router.get("/{organization_id}/billing/notifications")
async def get_billing_notifications(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get billing notifications - Owner only"""
    # Check if user is owner of the organization
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if user_role != 'owner':
        raise HTTPException(
            status_code=403,
            detail="Billing access is restricted to organization owners only"
        )

    # TODO: Get from database
    return {"notifications": []}


@router.get("/{organization_id}/invitations", response_model=list)
async def get_pending_invitations(
    organization_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get pending invitations for organization"""
    # Check if user is admin/owner
    result = await db.execute(
        select(OrganizationMember.role)
        .where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.role.in_(['admin', 'owner'])
            )
        )
    )

    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    invitation_service = InvitationService(db)
    return await invitation_service.get_pending_invitations(organization_id)


@router.post("/accept-invitation", response_model=dict)
async def accept_organization_invitation(
    invitation_data: InvitationAcceptRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Accept organization invitation and create/update user account with automatic authentication"""
    invitation_service = InvitationService(db)

    try:
        # Get client info for session creation
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        result = await invitation_service.accept_invitation(
            token=invitation_data.token,
            email=invitation_data.email,
            temp_password=invitation_data.temporary_password,
            new_password=invitation_data.new_password,
            first_name=invitation_data.first_name,
            last_name=invitation_data.last_name,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Build enhanced response with authentication tokens and organization info
        return {
            'success': True,
            'message': result.get('welcome_message', 'Invitation accepted successfully! You are now logged in.'),
            'user': {
                'id': result['user_id'],
                'email': result['email'],
                'first_name': result.get('first_name', invitation_data.first_name),
                'last_name': result.get('last_name', invitation_data.last_name),
                'role': result['role'],
                'requires_password_reset': False
            },
            'tokens': {
                'access_token': result['session'].session_token,
                'refresh_token': result['session'].refresh_token,
                'token_type': 'bearer',
                'expires_in': 24 * 60 * 60  # 24 hours in seconds
            },
            'organization': {
                'id': result['organization_id'],
                'name': result['organization'].name,
                'role': result['role'],
                'description': result['organization'].description
            },
            'role_permissions': result.get('role_permissions', {}),
            'redirect_url': result['redirect_url'],
            'onboarding': {
                'is_new_user': True,
                'show_welcome': True,
                'next_steps': [
                    'Complete your profile setup',
                    'Explore your dashboard',
                    'Join your first project',
                    'Connect with team members'
                ]
            }
        }

    except ValidationError as e:
        # Handle specific validation errors with appropriate status codes
        error_message = str(e)
        if "Invalid temporary password" in error_message:
            raise HTTPException(
                status_code=401,
                detail="Invalid temporary password. Please check your invitation email for the correct temporary password."
            )
        elif "expired" in error_message.lower():
            raise HTTPException(
                status_code=410,
                detail="This invitation has expired. Please request a new invitation."
            )
        elif "already been used" in error_message:
            raise HTTPException(
                status_code=409,
                detail="This invitation has already been used. If you need access, please request a new invitation."
            )
        else:
            raise HTTPException(status_code=400, detail=error_message)
    except Exception as e:
        # Log the full error for debugging but return a generic message
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to accept invitation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to accept invitation. Please try again or contact support if the problem persists."
        )
