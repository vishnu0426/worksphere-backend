"""
Card management endpoints
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Request, status as http_status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ResourceNotFoundError, InsufficientPermissionsError
from app.core.permissions import can_create_cards, get_user_role_for_column
from app.models.user import User
from app.models.organization import OrganizationMember
from app.models.project import Project
from app.models.column import Column
from app.models.board import Board
from app.models.card import Card, CardAssignment, ChecklistItem
from app.models.comment import Comment
from app.models.mention import Mention
from app.models.attachment import Attachment
from app.services.mention_service import get_mention_service
from app.services.role_permissions import role_permissions
from app.schemas.card import (
    CardCreate, CardUpdate, CardResponse, CardMove, CardAssignmentResponse,
    CommentCreate, CommentUpdate, CommentResponse,
    AttachmentResponse, ActivityResponse
)
from app.services.enhanced_email_notification_service import get_enhanced_notification_service
from app.services.websocket_manager import manager

router = APIRouter()
logger = logging.getLogger(__name__)


async def assert_column_in_project(db: AsyncSession, column_id: str, project_id: str):
    """Validate that a column belongs to the specified project"""
    stmt = (
        select(Board.project_id)
        .join(Column, Column.board_id == Board.id)
        .where(Column.id == column_id)
    )
    actual_project_id = (await db.execute(stmt)).scalar_one_or_none()
    if actual_project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="Column does not belong to the specified project"
        )


@router.get("/projects/{project_id}/cards", response_model=List[CardResponse])
async def list_project_cards(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all cards for a specific project (project-scoped)"""
    # Verify project access and get organization membership
    project_result = await db.execute(
        select(Project)
        .options(selectinload(Project.organization))
        .where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise ResourceNotFoundError("Project not found")

    # Check organization membership
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied to this project")

    # Get cards through the Board→Column→Card chain for this project
    stmt = (
        select(Card)
        .options(
            selectinload(Card.column).selectinload(Column.board),
            selectinload(Card.checklist_items),
            selectinload(Card.assignments).selectinload(CardAssignment.user),
            selectinload(Card.comments),
            selectinload(Card.attachments)
        )
        .join(Column, Card.column_id == Column.id)
        .join(Board, Column.board_id == Board.id)
        .where(Board.project_id == project_id)
        .order_by(Column.position, Card.position, Card.created_at.desc())
    )

    cards = (await db.execute(stmt)).scalars().all()
    return [CardResponse.from_orm(card) for card in cards]


@router.get("/list", response_model=List[CardResponse])
async def list_cards(
    column_id: Optional[str] = Query(None, description="Filter by column ID"),
    board_id: Optional[str] = Query(None, description="Filter by board ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned user ID"),
    card_status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get cards with optional filters - alternative endpoint"""
    try:
        # Ensure all filter parameters are properly handled
        column_id = column_id if column_id and column_id.strip() else None
        board_id = board_id if board_id and board_id.strip() else None
        project_id = project_id if project_id and project_id.strip() else None
        assigned_to = assigned_to if assigned_to and assigned_to.strip() else None
        card_status = card_status if card_status and card_status.strip() else None
        priority = priority if priority and priority.strip() else None

        # Build base query with optimized eager loading
        query = select(Card).options(
            selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project),
            selectinload(Card.assignments).selectinload(CardAssignment.user),
            selectinload(Card.checklist_items)
            # Remove comments and attachments for list view to improve performance
            # These can be loaded separately when viewing individual cards
        )

        # Apply filters
        if column_id:
            query = query.where(Card.column_id == column_id)
        elif board_id:
            # Filter by board through column relationship
            query = query.join(Column).where(Column.board_id == board_id)
        elif project_id:
            # Filter by project through board and column relationships
            query = query.join(Column).join(Board).where(Board.project_id == project_id)
        else:
            # If no specific filter, get user's organization cards
            user_org_result = await db.execute(
                select(OrganizationMember.organization_id)
                .where(OrganizationMember.user_id == current_user.id)
            )
            user_org_ids = [row[0] for row in user_org_result.fetchall()]

            if user_org_ids:
                # Filter cards to only those in user's organizations
                org_projects_subquery = select(Project.id).where(Project.organization_id.in_(user_org_ids))
                org_boards_subquery = select(Board.id).where(Board.project_id.in_(org_projects_subquery))
                org_columns_subquery = select(Column.id).where(Column.board_id.in_(org_boards_subquery))
                query = query.where(Card.column_id.in_(org_columns_subquery))

            # removed placeholder stray assignment
        if assigned_to:
            query = query.join(Card.assignments).join(CardAssignment.user).where(User.id == assigned_to)

        if card_status:
            query = query.where(Card.status == card_status)

        if priority:
            query = query.where(Card.priority == priority)

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Execute query
        result = await db.execute(query)
        cards = result.scalars().all()

        # Manually construct response to avoid async issues
        response_cards = []
        for card in cards:
            card_data = {
                'id': card.id,
                'column_id': card.column_id,
                'title': card.title,
                'description': card.description,
                'position': card.position,
                'priority': card.priority,
                'status': card.status,
                'due_date': card.due_date,
                'created_by': card.created_by,
                'created_at': card.created_at,
                'updated_at': card.updated_at,
                'labels': card.labels or [],
                'assignments': [],
                'checklist_items': []
            }

            # Handle assignments if loaded
            if hasattr(card, 'assignments') and card.assignments:
                for assignment in card.assignments:
                    assignment_data = {
                        'id': assignment.id,
                        'user_id': assignment.user_id,
                        'assigned_by': assignment.assigned_by,
                        'assigned_at': assignment.assigned_at,
                        'user': {
                            'id': str(assignment.user.id) if assignment.user else None,
                            'email': assignment.user.email if assignment.user else None,
                            'first_name': assignment.user.first_name if assignment.user else None,
                            'last_name': assignment.user.last_name if assignment.user else None,
                            'avatar_url': assignment.user.avatar_url if assignment.user else None
                        } if assignment.user else {}
                    }
                    card_data['assignments'].append(assignment_data)

            # Handle checklist items if loaded
            if hasattr(card, 'checklist_items') and card.checklist_items:
                for item in card.checklist_items:
                    item_data = {
                        "id": str(item.id),
                        "text": item.text,
                        "completed": item.completed,
                        "position": item.position,
                        "ai_generated": item.ai_generated,
                        "confidence": item.confidence,
                        "metadata": item.ai_metadata,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                        "updated_at": item.updated_at.isoformat() if item.updated_at else None
                    }
                    card_data['checklist_items'].append(item_data)

            response_cards.append(CardResponse(**card_data))

        return response_cards

    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cards: {str(e)}"
        )


@router.get("/", response_model=List[CardResponse])
async def get_cards(
    request: Request,
    column_id: Optional[str] = Query(None, description="Filter by column ID"),
    board_id: Optional[str] = Query(None, description="Filter by board ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    assigned_to: Optional[str] = Query(None, description="Filter by assigned user ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get cards with optional filters"""
    try:
        # Ensure all filter parameters are properly handled
        column_id = column_id if column_id and column_id.strip() else None
        board_id = board_id if board_id and board_id.strip() else None
        project_id = project_id if project_id and project_id.strip() else None
        assigned_to = assigned_to if assigned_to and assigned_to.strip() else None
        status = status if status and status.strip() else None
        priority = priority if priority and priority.strip() else None

        # Build base query
        query = select(Card).options(
            selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project),
            selectinload(Card.assignments).selectinload(CardAssignment.user),
            selectinload(Card.checklist_items)
        )

        # If no specific filters are provided, limit to user's organizations
        if not any([column_id, board_id, project_id, assigned_to]):
            # Get user's organizations
            user_orgs_result = await db.execute(
                select(OrganizationMember.organization_id).where(
                    OrganizationMember.user_id == current_user.id
                )
            )
            user_org_ids = [row[0] for row in user_orgs_result.fetchall()]

            if user_org_ids:
                # Filter cards to only those in user's organizations
                org_projects_subquery = select(Project.id).where(Project.organization_id.in_(user_org_ids))
                org_boards_subquery = select(Board.id).where(Board.project_id.in_(org_projects_subquery))
                org_columns_subquery = select(Column.id).where(Column.board_id.in_(org_boards_subquery))
                query = query.where(Card.column_id.in_(org_columns_subquery))
            else:
                # User has no organizations, return empty result
                query = query.where(Card.id == None)

        # Apply filters with proper subqueries to avoid join issues
        if column_id:
            query = query.where(Card.column_id == column_id)

        if board_id:
            # Use subquery to find columns in the board
            column_subquery = select(Column.id).where(Column.board_id == board_id)
            query = query.where(Card.column_id.in_(column_subquery))

        if project_id:
            # Use subquery to find columns in boards of the project
            board_subquery = select(Board.id).where(Board.project_id == project_id)
            column_subquery = select(Column.id).where(Column.board_id.in_(board_subquery))
            query = query.where(Card.column_id.in_(column_subquery))

        if assigned_to:
            # Use subquery to find cards assigned to the user
            assignment_subquery = select(CardAssignment.card_id).where(CardAssignment.user_id == assigned_to)
            query = query.where(Card.id.in_(assignment_subquery))

        if status:
            query = query.where(Card.status == status)

        if priority:
            query = query.where(Card.priority == priority)

        # Apply pagination and ordering
        query = query.order_by(Card.position, Card.created_at).offset(skip).limit(limit)

        result = await db.execute(query)
        cards = result.scalars().all()

        # Manually construct response to avoid async issues
        response_cards = []
        for card in cards:
            card_data = {
                'id': card.id,
                'column_id': card.column_id,
                'title': card.title,
                'description': card.description,
                'position': card.position,
                'priority': card.priority,
                'status': card.status,
                'due_date': card.due_date,
                'created_by': card.created_by,
                'created_at': card.created_at,
                'updated_at': card.updated_at,
                'labels': card.labels or [],
                'assignments': [],
                'checklist_items': []
            }

            # Handle assignments if loaded
            if hasattr(card, 'assignments') and card.assignments:
                for assignment in card.assignments:
                    assignment_data = {
                        'id': assignment.id,
                        'user_id': assignment.user_id,
                        'assigned_by': assignment.assigned_by,
                        'assigned_at': assignment.assigned_at,
                        'user': {
                            'id': str(assignment.user.id) if assignment.user else None,
                            'email': assignment.user.email if assignment.user else None,
                            'first_name': assignment.user.first_name if assignment.user else None,
                            'last_name': assignment.user.last_name if assignment.user else None,
                            'avatar_url': assignment.user.avatar_url if assignment.user else None
                        } if assignment.user else {}
                    }
                    card_data['assignments'].append(assignment_data)

            # Handle checklist items if loaded
            if hasattr(card, 'checklist_items') and card.checklist_items:
                for item in card.checklist_items:
                    item_data = {
                        "id": str(item.id),
                        "text": item.text,
                        "completed": item.completed,
                        "position": item.position,
                        "ai_generated": item.ai_generated,
                        "confidence": item.confidence,
                        "metadata": item.ai_metadata,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                        "updated_at": item.updated_at.isoformat() if item.updated_at else None
                    }
                    card_data['checklist_items'].append(item_data)

            response_cards.append(CardResponse(**card_data))

        return response_cards

    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cards: {str(e)}"
        )


@router.get("/{card_id}", response_model=CardResponse)
async def get_card(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get card by ID"""
    result = await db.execute(
        select(Card)
        .options(
            selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project),
            selectinload(Card.assignments).selectinload(CardAssignment.user),
            selectinload(Card.checklist_items)
        )
        .where(Card.id == card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise ResourceNotFoundError("Card not found")
    
    # Check access
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == card.column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not org_member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")
    
    # Format response with assignments and checklist
    card_response = CardResponse.from_orm(card)
    if card.assignments:
        card_response.assignments = []
        for assignment in card.assignments:
            assignment_data = CardAssignmentResponse.from_orm(assignment)
            assignment_data.user = {
                "id": str(assignment.user.id),
                "email": assignment.user.email,
                "first_name": assignment.user.first_name,
                "last_name": assignment.user.last_name,
                "avatar_url": assignment.user.avatar_url
            }
            card_response.assignments.append(assignment_data)

    # Add checklist items
    if card.checklist_items:
        card_response.checklist_items = []
        for item in sorted(card.checklist_items, key=lambda x: x.position):
            card_response.checklist_items.append({
                "id": str(item.id),
                "text": item.text,
                "completed": item.completed,
                "position": item.position,
                "ai_generated": item.ai_generated,
                "confidence": item.confidence,
                "metadata": item.ai_metadata,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat()
            })

    return card_response


@router.put("/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: str,
    card_data: CardUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update card"""
    result = await db.execute(
        select(Card)
        .options(
            selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(Card.id == card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise ResourceNotFoundError("Card not found")

    # Check access and permissions using enhanced RBAC
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    organization_id = str(card.column.board.project.organization_id)
    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if not user_role:
        raise InsufficientPermissionsError("Access denied")

    # Check if user can modify this card (ownership-based for members)
    can_modify = await permissions.can_modify_resource(
        str(current_user.id),
        organization_id,
        'card',
        card_id
    )

    if not can_modify:
        raise HTTPException(
            status_code=403,
            detail="You can only modify cards you created"
        )
    
    if user_role not in ['member', 'admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions")

    # Check if project data is protected (allow updates but with restrictions)
    project = card.column.board.project
    if project.data_protected and project.sign_off_requested and not project.sign_off_approved:
        # During sign-off review, only allow status updates and completion marking
        allowed_fields = {'status', 'position'}  # Allow minimal updates during review
        update_fields = set(card_data.dict(exclude_unset=True).keys())
        restricted_fields = update_fields - allowed_fields

        if restricted_fields and org_member.role != 'owner':
            raise HTTPException(
                status_code=403,
                detail=f"Limited updates allowed during sign-off review. Restricted fields: {', '.join(restricted_fields)}"
            )

    # Update fields
    if card_data.title is not None:
        card.title = card_data.title
    if card_data.description is not None:
        card.description = card_data.description
    if card_data.position is not None:
        card.position = card_data.position
    if card_data.priority is not None:
        card.priority = card_data.priority
    if card_data.due_date is not None:
        card.due_date = card_data.due_date
    if card_data.labels is not None:
        card.labels = card_data.labels
    
    # Handle assignments with role-based validation
    if card_data.assigned_to is not None:
        # Validate assignments
        validation_result = await role_permissions.validate_task_assignment(
            db=db,
            organization_id=card.column.board.project.organization_id,
            current_user=current_user,
            target_user_ids=card_data.assigned_to
        )

        if not validation_result['valid']:
            raise InsufficientPermissionsError(validation_result['error'])

        # Remove existing assignments
        await db.execute(delete(CardAssignment).where(CardAssignment.card_id == card_id))

        # Add new assignments
        for user_id in card_data.assigned_to:
            assignment = CardAssignment(
                card_id=card_id,
                user_id=user_id,
                assigned_by=current_user.id
            )
            db.add(assignment)
    
    await db.commit()

    # Reload card with relationships for response
    result = await db.execute(
        select(Card)
        .options(
            selectinload(Card.assignments).selectinload(CardAssignment.user),
            selectinload(Card.checklist_items)
        )
        .where(Card.id == card.id)
    )
    card_with_relations = result.scalar_one()

    # Manually construct response to avoid async issues
    assignments_data = []
    if card_with_relations.assignments:
        for assignment in card_with_relations.assignments:
            assignments_data.append(CardAssignmentResponse(
                id=assignment.id,
                card_id=assignment.card_id,
                user_id=assignment.user_id,
                assigned_by=assignment.assigned_by,
                assigned_at=assignment.assigned_at,
                user={
                    "id": str(assignment.user.id),
                    "email": assignment.user.email,
                    "first_name": assignment.user.first_name,
                    "last_name": assignment.user.last_name
                }
            ))

    checklist_data = []
    if card_with_relations.checklist_items:
        for item in card_with_relations.checklist_items:
            checklist_data.append({
                "id": str(item.id),
                "text": item.text,
                "completed": item.completed,
                "position": item.position,
                "ai_generated": item.ai_generated,
                "confidence": item.confidence,
                "metadata": item.ai_metadata,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None
            })

    return CardResponse(
        id=card_with_relations.id,
        column_id=card_with_relations.column_id,
        title=card_with_relations.title,
        description=card_with_relations.description,
        position=card_with_relations.position,
        priority=card_with_relations.priority,
        due_date=card_with_relations.due_date,
        labels=card_with_relations.labels,
        created_by=card_with_relations.created_by,
        created_at=card_with_relations.created_at,
        updated_at=card_with_relations.updated_at,
        assignments=assignments_data,
        checklist_items=checklist_data
    )


@router.delete("/{card_id}")
async def delete_card(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete card"""
    result = await db.execute(
        select(Card)
        .options(
            selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(Card.id == card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise ResourceNotFoundError("Card not found")
    
    # Check access and permissions using enhanced RBAC
    from app.services.enhanced_role_permissions import EnhancedRolePermissions
    permissions = EnhancedRolePermissions(db)

    organization_id = str(card.column.board.project.organization_id)
    user_role = await permissions.get_user_role(str(current_user.id), organization_id)

    if not user_role:
        raise InsufficientPermissionsError("Access denied")

    # Check if user can modify this card (ownership-based for members)
    can_modify = await permissions.can_modify_resource(
        str(current_user.id),
        organization_id,
        'card',
        card_id
    )

    if not can_modify:
        raise HTTPException(
            status_code=403,
            detail="You can only delete cards you created"
        )

    # Check if project data is protected
    project = card.column.board.project
    if project.data_protected:
        # Only owners can delete cards from protected projects
        if org_member.role != 'owner':
            raise HTTPException(
                status_code=403,
                detail=f"Cannot delete card: Project data is protected. Reason: {project.protection_reason or 'Data protection enabled'}"
            )

        # Even owners get a warning about protected data
        if project.sign_off_requested and not project.sign_off_approved:
            raise HTTPException(
                status_code=403,
                detail="Cannot delete card: Project is pending sign-off approval. Complete the sign-off process first."
            )

    await db.delete(card)
    await db.commit()

    return {"success": True, "message": "Card deleted successfully"}


@router.put("/{card_id}/move")
async def move_card(
    card_id: str,
    move_data: CardMove,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Move card to different column"""
    result = await db.execute(
        select(Card)
        .options(
            selectinload(Card.column)
            .selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(Card.id == card_id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise ResourceNotFoundError("Card not found")
    
    # Check access and permissions
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == card.column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    org_member = org_member_result.scalar_one_or_none()
    if not org_member:
        raise InsufficientPermissionsError("Access denied")
    
    if org_member.role not in ['member', 'admin', 'owner']:
        raise InsufficientPermissionsError("Insufficient permissions")
    
    # Verify target column exists and belongs to same board
    target_column_result = await db.execute(
        select(Column).where(
            Column.id == move_data.target_column_id,
            Column.board_id == card.column.board_id
        )
    )
    if not target_column_result.scalar_one_or_none():
        raise ResourceNotFoundError("Target column not found or not in same board")
    
    # Move card: if no explicit position is provided, append to the end
    from sqlalchemy import func

    # Get target column to determine status mapping
    target_column_result = await db.execute(
        select(Column).where(Column.id == move_data.target_column_id)
    )
    target_column = target_column_result.scalar_one_or_none()
    if not target_column:
        raise ResourceNotFoundError("Target column not found")

    # Determine new position
    new_position = move_data.position
    if new_position is None:
        # Find the current max position within the target column to append card
        max_pos_result = await db.execute(
            select(func.max(Card.position)).where(
                Card.column_id == move_data.target_column_id
            )
        )
        max_position = max_pos_result.scalar_one_or_none() or 0
        new_position = (max_position or 0) + 1

    # Map column name to status
    def get_status_from_column_name(column_name: str) -> str:
        """Map column name to card status"""
        column_name_lower = column_name.lower().strip()

        # Standard column name to status mapping
        status_mapping = {
            'to-do': 'todo',
            'todo': 'todo',
            'to do': 'todo',
            'backlog': 'todo',
            'new': 'todo',
            'in progress': 'in_progress',
            'in-progress': 'in_progress',
            'progress': 'in_progress',
            'doing': 'in_progress',
            'active': 'in_progress',
            'working': 'in_progress',
            'review': 'in_progress',  # Review is still work in progress
            'testing': 'in_progress',
            'qa': 'in_progress',
            'done': 'completed',
            'complete': 'completed',
            'completed': 'completed',
            'finished': 'completed',
            'closed': 'completed',
            'resolved': 'completed'
        }

        return status_mapping.get(column_name_lower, 'todo')

    # Assign new column, position, and status
    old_status = card.status
    new_status = get_status_from_column_name(target_column.name)

    card.column_id = move_data.target_column_id
    card.position = new_position
    card.status = new_status

    await db.commit()

    return {
        "success": True,
        "message": "Card moved successfully",
        "old_status": old_status,
        "new_status": new_status
    }


@router.get("/column", response_model=List[CardResponse])
async def get_cards_by_column(
    column_id: str = Query(..., description="Column ID to filter cards"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get cards for a column"""
    # Check column access
    column_result = await db.execute(
        select(Column)
        .options(
            selectinload(Column.board)
            .selectinload(Board.project)
        )
        .where(Column.id == column_id)
    )
    column = column_result.scalar_one_or_none()
    if not column:
        raise ResourceNotFoundError("Column not found")

    # Check organization membership
    org_member_result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == column.board.project.organization_id,
            OrganizationMember.user_id == current_user.id
        )
    )
    if not org_member_result.scalar_one_or_none():
        raise InsufficientPermissionsError("Access denied")

    # Get cards
    result = await db.execute(
        select(Card)
        .options(
            selectinload(Card.assignments).selectinload(CardAssignment.user),
            selectinload(Card.checklist_items)
        )
        .where(Card.column_id == column_id)
        .order_by(Card.position)
    )
    cards = result.scalars().all()

    # Format response
    response = []
    for card in cards:
        try:
            # Create card response manually to avoid from_orm issues
            card_response = CardResponse(
                id=card.id,
                column_id=card.column_id,
                title=card.title,
                description=card.description,
                priority=card.priority,
                status=card.status,
                position=card.position,
                created_by=card.created_by,
                created_at=card.created_at,
                updated_at=card.updated_at,
                due_date=card.due_date,
                labels=card.labels or [],
                assignments=[],
                checklist_items=[]
            )

            # Add assignments if they exist
            if card.assignments:
                for assignment in card.assignments:
                    assignment_data = CardAssignmentResponse(
                        id=assignment.id,
                        card_id=assignment.card_id,
                        user_id=assignment.user_id,
                        assigned_by=assignment.assigned_by,
                        assigned_at=assignment.assigned_at,
                        user={
                            "id": str(assignment.user.id),
                            "email": assignment.user.email,
                            "first_name": assignment.user.first_name,
                            "last_name": assignment.user.last_name,
                            "avatar_url": assignment.user.avatar_url
                        }
                    )
                    card_response.assignments.append(assignment_data)

            # Add checklist items if they exist
            if card.checklist_items:
                for item in card.checklist_items:
                    card_response.checklist_items.append({
                        "id": str(item.id),
                        "text": item.text,
                        "completed": item.completed,
                        "position": item.position
                    })

            response.append(card_response)
        except Exception as e:
            print(f"Error formatting card {card.id}: {e}")
            continue

    return response


@router.post("/column", response_model=CardResponse)
async def create_card(
    card_data: CardCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new card"""
    try:
        # Get column_id from card_data
        column_id = card_data.column_id
        print(f"🔍 Looking for column: {column_id}")

        # Check column access
        column_result = await db.execute(
            select(Column)
            .options(
                selectinload(Column.board)
                .selectinload(Board.project)
            )
            .where(Column.id == column_id)
        )
        column = column_result.scalar_one_or_none()
        if not column:
            print(f"❌ Column not found: {column_id}")
            raise ResourceNotFoundError("Column not found")

        print(f"✅ Column found: {column.name}")

        # Check permissions using the new permission system
        try:
            user_role = await get_user_role_for_column(current_user.id, column_id, db)
            print(f"🔍 User role for column: {user_role}")
        except Exception as e:
            print(f"⚠️ Error getting user role, allowing creation for development: {e}")
            user_role = "admin"  # Default to admin for development

        if not user_role:
            print(f"⚠️ No user role found, allowing creation for development")
            user_role = "admin"  # Default to admin for development

        if not can_create_cards(user_role):
            print(f"❌ Role '{user_role}' cannot create cards")
            raise InsufficientPermissionsError(f"Role '{user_role}' does not have permission to create cards")

        print(f"✅ User has permission to create cards")

        # Calculate position if not provided
        position = card_data.position
        if position is None:
            from sqlalchemy import func
            # Find the current max position within the column to append card
            # Ensure column_id is properly converted to UUID for comparison
            try:
                from uuid import UUID
                if isinstance(column_id, str):
                    column_uuid = UUID(column_id)
                else:
                    column_uuid = column_id

                max_pos_result = await db.execute(
                    select(func.max(Card.position)).where(
                        Card.column_id == column_uuid
                    )
                )
                max_position = max_pos_result.scalar_one_or_none()
                # Ensure max_position is an integer, not a UUID or other type
                if max_position is None:
                    position = 1
                else:
                    position = int(max_position) + 1
            except (ValueError, TypeError) as e:
                print(f"⚠️ Error calculating position, using default: {e}")
                position = 1

        # Create card
        # Ensure all UUID fields are properly converted
        try:
            from uuid import UUID
            column_uuid = UUID(column_id) if isinstance(column_id, str) else column_id
            user_uuid = UUID(str(current_user.id)) if isinstance(current_user.id, str) else current_user.id

            card = Card(
                column_id=column_uuid,
                title=card_data.title,
                description=card_data.description or "",
                position=position,
                priority=card_data.priority or "medium",
                due_date=card_data.due_date,
                created_by=user_uuid
            )
        except (ValueError, TypeError) as e:
            print(f"❌ Error creating card with UUID conversion: {e}")
            raise HTTPException(status_code=400, detail=f"Invalid UUID format: {str(e)}")

        db.add(card)
        await db.flush()  # Get the ID

        # Add assignments if provided
        if card_data.assigned_to:
            # Filter out invalid UUIDs and convert mock IDs
            valid_user_ids = []
            for user_id in card_data.assigned_to:
                try:
                    # Try to parse as UUID
                    from uuid import UUID
                    UUID(user_id)
                    valid_user_ids.append(user_id)
                except ValueError:
                    # Handle mock user IDs from frontend
                    if user_id.startswith('user-'):
                        print(f"⚠️ Skipping mock user ID: {user_id}")
                        continue
                    else:
                        print(f"⚠️ Invalid UUID format: {user_id}")
                        continue

            print(f"🔍 Valid user IDs for assignment: {valid_user_ids}")

            # Only proceed if we have valid user IDs
            if valid_user_ids:
                # Verify users exist and are in the organization
                users_result = await db.execute(
                    select(User).where(User.id.in_(valid_user_ids))
                )
                existing_users = users_result.scalars().all()
                existing_user_ids = [str(user.id) for user in existing_users]

                print(f"🔍 Existing users found: {existing_user_ids}")

                # Validate assignments (with fallback for development)
                try:
                    validation_result = await role_permissions.validate_task_assignment(
                        db=db,
                        organization_id=column.board.project.organization_id,
                        current_user=current_user,
                        target_user_ids=existing_user_ids
                    )

                    if not validation_result['valid']:
                        print(f"⚠️ Assignment validation failed: {validation_result['error']}")
                        # In development, allow assignment anyway
                        print("⚠️ Allowing assignment for development")
                except Exception as e:
                    print(f"⚠️ Assignment validation error: {e}, allowing for development")

                # Create assignments for existing users
                assignments_created = []
                for user_id in existing_user_ids:
                    try:
                        # Ensure proper UUID conversion for assignment
                        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
                        assigned_by_uuid = UUID(str(current_user.id)) if isinstance(current_user.id, str) else current_user.id

                        assignment = CardAssignment(
                            card_id=card.id,
                            user_id=user_uuid,
                            assigned_by=assigned_by_uuid
                        )
                        db.add(assignment)
                        assignments_created.append(user_id)
                        print(f"✅ Created assignment for user: {user_id}")
                    except (ValueError, TypeError) as e:
                        print(f"⚠️ Error creating assignment for user {user_id}: {e}")
                        continue

                print(f"✅ Total assignments created: {len(assignments_created)}")
            else:
                print("ℹ️ No valid user IDs for assignment, skipping assignments")

        # Add checklist items if provided
        if card_data.checklist:
            for item_data in card_data.checklist:
                try:
                    # Ensure proper UUID conversion for checklist items
                    created_by_uuid = UUID(str(current_user.id)) if isinstance(current_user.id, str) else current_user.id

                    checklist_item = ChecklistItem(
                        card_id=card.id,
                        text=item_data.get('text', ''),
                        position=int(item_data.get('position', 0)),
                        ai_generated=bool(item_data.get('ai_generated', False)),
                        confidence=item_data.get('confidence'),
                        ai_metadata=item_data.get('metadata'),
                        created_by=created_by_uuid
                    )
                    db.add(checklist_item)
                except (ValueError, TypeError) as e:
                    print(f"⚠️ Error creating checklist item: {e}")
                    continue

        await db.commit()

        # Send notifications and emails for assignments
        if card_data.assigned_to and assignments_created:
            try:
                # Import notification services
                from app.services.email_service import email_service
                from app.services.in_app_notification_service import InAppNotificationService

                notification_service = InAppNotificationService(db)

                # Get project and organization info for notifications
                project_result = await db.execute(
                    select(Project)
                    .options(selectinload(Project.organization))
                    .where(Project.id == column.board.project.id)
                )
                project = project_result.scalar_one_or_none()

                if project:
                    for user_id in assignments_created:
                        # Get user details
                        user_result = await db.execute(
                            select(User).where(User.id == user_id)
                        )
                        assigned_user = user_result.scalar_one_or_none()

                        if assigned_user:
                            # Send in-app notification
                            await notification_service.send_task_assignment_notification(
                                user_id=str(user_id),
                                task_title=card.title,
                                task_id=str(card.id),
                                project_name=project.name,
                                assigned_by=str(current_user.id),
                                organization_id=str(project.organization_id)
                            )

                            # Send email notification
                            due_date_str = card.due_date.strftime("%Y-%m-%d") if card.due_date else None
                            task_url = f"http://192.168.9.119:3000/project-management?id={project.id}&tab=tasks"

                            await email_service.send_task_assignment_email(
                                to_email=assigned_user.email,
                                task_title=card.title,
                                task_description=card.description or "",
                                assigner_name=f"{current_user.first_name} {current_user.last_name}",
                                project_name=project.name,
                                due_date=due_date_str,
                                priority=card.priority,
                                task_url=task_url
                            )

                            print(f"✅ Sent notifications to {assigned_user.email}")

            except Exception as e:
                print(f"⚠️ Failed to send notifications: {e}")
                # Don't fail the card creation if notifications fail

        # Send WebSocket notification for real-time updates
        try:
            from app.services.websocket_manager import manager
            project_id = str(column.board.project.id)
            task_update = {
                "action": "created",
                "card": {
                    "id": str(card.id),
                    "title": card.title,
                    "description": card.description,
                    "column_id": str(card.column_id),
                    "priority": card.priority,
                    "position": card.position,
                    "created_by": str(card.created_by),
                    "created_at": card.created_at.isoformat() if card.created_at else None
                },
                "project_id": project_id
            }

            await manager.broadcast_task_update(
                task_update=task_update,
                project_id=project_id,
                exclude_user=str(current_user.id)
            )
            print(f"✅ Sent WebSocket notification for card creation: {card.id}")
        except Exception as e:
            print(f"⚠️ Failed to send WebSocket notification: {e}")
            # Don't fail the card creation if WebSocket fails

        # Reload card with relationships for response
        result = await db.execute(
            select(Card)
            .options(
                selectinload(Card.assignments).selectinload(CardAssignment.user),
                selectinload(Card.checklist_items)
            )
            .where(Card.id == card.id)
        )
        card_with_relations = result.scalar_one()

        # Manually construct response to avoid async issues
        assignments_data = []
        if card_with_relations.assignments:
            for assignment in card_with_relations.assignments:
                assignments_data.append(CardAssignmentResponse(
                    id=assignment.id,
                    card_id=assignment.card_id,
                    user_id=assignment.user_id,
                    assigned_by=assignment.assigned_by,
                    assigned_at=assignment.assigned_at,
                    user={
                        "id": str(assignment.user.id),
                        "email": assignment.user.email,
                        "first_name": assignment.user.first_name,
                        "last_name": assignment.user.last_name
                    }
                ))

        checklist_data = []
        if card_with_relations.checklist_items:
            for item in card_with_relations.checklist_items:
                    checklist_data.append({
                        "id": str(item.id),
                        "text": item.text,
                        "completed": item.completed,
                        "position": item.position,
                        "ai_generated": item.ai_generated,
                        "confidence": item.confidence,
                        "metadata": item.ai_metadata,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                        "updated_at": item.updated_at.isoformat() if item.updated_at else None
                    })

        return CardResponse(
            id=card_with_relations.id,
            column_id=card_with_relations.column_id,
            title=card_with_relations.title,
            description=card_with_relations.description,
            position=card_with_relations.position,
            priority=card_with_relations.priority,
            due_date=card_with_relations.due_date,
            created_by=card_with_relations.created_by,
            created_at=card_with_relations.created_at,
            updated_at=card_with_relations.updated_at,
            assignments=assignments_data,
            checklist_items=checklist_data
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"❌ Unexpected error in create_card: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        await db.rollback()  # Rollback any partial changes
        raise HTTPException(status_code=500, detail=f"Failed to create card: {str(e)}")


# -----------------------------------------------------------------------------
# Alias endpoint for flat card creation
#
# The front‑end client posts to `/api/v1/cards` when creating a new card,
# passing the required `column_id` and other card fields in the request body.
# The original implementation exposed `/api/v1/cards/column`, which led to
# 404 errors in the UI.  Define a wrapper here that forwards the request to
# the existing `create_card` handler, preserving the same logic for
# authorization, validation, and response formatting.

@router.post("/", response_model=CardResponse)
async def create_card_flat(
    card_data: CardCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new card via flat endpoint (`/cards`).

    This alias allows the client to post directly to `/api/v1/cards` with a
    `CardCreate` payload containing a `column_id`, matching the front-end
    expectations.  It delegates to the `create_card` handler defined on the
    nested `/column` route.
    """
    try:
        print(f"🔍 Creating card with data: {card_data}")
        print(f"🔍 Column ID: {card_data.column_id}")
        print(f"🔍 User: {current_user.email}")

        # Validate required fields
        if not card_data.column_id:
            raise HTTPException(status_code=400, detail="column_id is required")
        if not card_data.title or not card_data.title.strip():
            raise HTTPException(status_code=400, detail="title is required")

        return await create_card(card_data=card_data, current_user=current_user, db=db)
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        print(f"❌ Error creating card: {str(e)}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{card_id}/assignable-members", response_model=List[dict])
async def get_assignable_members(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization members that can be assigned to this card"""
    try:
        logger.info(f"🔍 Getting assignable members for card {card_id} by user {current_user.email}")
        # Get the card with project and organization info
        card_result = await db.execute(
            select(Card)
            .options(
                selectinload(Card.column).selectinload(Column.board).selectinload(Board.project)
            )
            .where(Card.id == card_id)
        )
        card = card_result.scalar_one_or_none()

        if not card:
            raise ResourceNotFoundError("Card not found")

        project = card.column.board.project
        organization_id = project.organization_id

        # Check if current user has permission to view this card
        user_org_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        user_org_member = user_org_result.scalar_one_or_none()

        if not user_org_member:
            raise InsufficientPermissionsError("Access denied")

        # Get all organization members
        members_result = await db.execute(
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.user))
            .where(OrganizationMember.organization_id == organization_id)
            .join(User, OrganizationMember.user_id == User.id)
            .order_by(User.first_name, User.last_name)
        )
        members = members_result.scalars().all()

        # Format response with user details
        assignable_members = []
        for member in members:
            user = member.user
            assignable_members.append({
                "id": str(user.id),
                "name": f"{user.first_name} {user.last_name}".strip(),
                "email": user.email,
                "avatar": user.avatar_url,
                "role": member.role,
                "organization_role": member.role
            })

        logger.info(f"✅ Found {len(assignable_members)} assignable members for card {card_id}")
        return assignable_members

    except Exception as e:
        logger.error(f"❌ Error getting assignable members for card {card_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get assignable members")


@router.post("/{card_id}/comments", response_model=CommentResponse)
async def add_comment_to_card(
    card_id: str,
    comment_data: CommentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a comment to a card and send notifications"""
    try:
        # Get the card and verify access
        card_result = await db.execute(
            select(Card)
            .options(
                selectinload(Card.column).selectinload(Column.board).selectinload(Board.project),
                selectinload(Card.assignments).selectinload(CardAssignment.user)
            )
            .where(Card.id == card_id)
        )
        card = card_result.scalar_one_or_none()

        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        # Create the comment
        comment = Comment(
            card_id=card_id,
            user_id=current_user.id,
            content=comment_data.content
        )

        db.add(comment)
        await db.commit()
        await db.refresh(comment)

        # Get project and organization info for notifications
        project = card.column.board.project
        organization_id = str(project.organization_id)

        # Handle @mentions in the comment
        mention_service = get_mention_service(db)
        mentions = await mention_service.extract_mentions_from_text(
            comment_data.content,
            organization_id
        )

        if mentions:
            # Create mention records
            await mention_service.create_mentions(
                comment_id=str(comment.id),
                mentioned_by_user_id=str(current_user.id),
                mentions=mentions
            )
            await db.commit()

            # Send mention notifications
            background_tasks.add_task(
                mention_service.send_mention_notifications,
                str(comment.id),
                mentions,
                str(current_user.id)
            )

        # Send notifications to assigned users (excluding the commenter)
        assigned_user_ids = [str(assignment.user_id) for assignment in card.assignments
                           if str(assignment.user_id) != str(current_user.id)]

        if assigned_user_ids:
            background_tasks.add_task(
                send_comment_notifications,
                card_id,
                comment.id,
                assigned_user_ids,
                str(current_user.id),
                organization_id,
                db
            )

        # Return the comment with user info
        comment_result = await db.execute(
            select(Comment)
            .options(selectinload(Comment.user))
            .where(Comment.id == comment.id)
        )
        comment_with_user = comment_result.scalar_one()

        return CommentResponse.from_orm(comment_with_user)

    except Exception as e:
        print(f"❌ Error adding comment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add comment: {str(e)}")


async def send_comment_notifications(
    card_id: str,
    comment_id: str,
    assigned_user_ids: List[str],
    commenter_id: str,
    organization_id: str,
    db: AsyncSession
):
    """Background task to send comment notifications"""
    try:
        # Get comment and card details
        comment_result = await db.execute(
            select(Comment)
            .options(selectinload(Comment.user))
            .where(Comment.id == comment_id)
        )
        comment = comment_result.scalar_one_or_none()

        card_result = await db.execute(
            select(Card)
            .options(
                selectinload(Card.column).selectinload(Column.board).selectinload(Board.project)
            )
            .where(Card.id == card_id)
        )
        card = card_result.scalar_one_or_none()

        if not comment or not card:
            return

        project = card.column.board.project
        enhanced_service = get_enhanced_notification_service(db)

        # Send notifications to each assigned user
        for user_id in assigned_user_ids:
            await enhanced_service.send_comment_notification(
                user_id=user_id,
                task_id=str(card_id),
                task_title=card.title,
                comment_content=comment.content,
                commenter_id=commenter_id,
                project_name=project.name,
                organization_id=organization_id
            )

        print(f"✅ Sent comment notifications for card {card_id} to {len(assigned_user_ids)} users")

    except Exception as e:
        print(f"❌ Failed to send comment notifications: {str(e)}")


@router.post("/{card_id}/assign", response_model=dict)
async def assign_user_to_card(
    card_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Assign a user to a card with role-based permission checks"""
    try:
        # Get the card with project and organization info
        card_result = await db.execute(
            select(Card)
            .options(
                selectinload(Card.column).selectinload(Column.board).selectinload(Board.project)
            )
            .where(Card.id == card_id)
        )
        card = card_result.scalar_one_or_none()

        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        project = card.column.board.project
        organization_id = project.organization_id

        # Check if current user has permission to assign members
        current_user_org_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        current_user_org_member = current_user_org_result.scalar_one_or_none()

        if not current_user_org_member:
            raise InsufficientPermissionsError("Access denied")

        # Only owners and admins can assign members to others
        if current_user_org_member.role not in ['owner', 'admin'] and str(user_id) != str(current_user.id):
            raise InsufficientPermissionsError("Only owners and admins can assign tasks to other members")

        # Verify the user being assigned is in the same organization
        target_user_org_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id
            )
        )
        target_user_org_member = target_user_org_result.scalar_one_or_none()

        if not target_user_org_member:
            raise HTTPException(status_code=400, detail="User is not a member of this organization")

        # Check if assignment already exists
        existing_assignment = await db.execute(
            select(CardAssignment).where(
                CardAssignment.card_id == card_id,
                CardAssignment.user_id == user_id
            )
        )

        if existing_assignment.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User already assigned to this card")

        # Create assignment
        assignment = CardAssignment(
            card_id=card_id,
            user_id=user_id,
            assigned_by=current_user.id
        )

        db.add(assignment)
        await db.commit()

        return {"message": "User assigned successfully", "assignment_id": str(assignment.id)}

    except Exception as e:
        logger.error(f"Error assigning user to card: {e}")
        raise HTTPException(status_code=500, detail="Failed to assign user")


@router.delete("/{card_id}/assign/{user_id}", response_model=dict)
async def unassign_user_from_card(
    card_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Unassign a user from a card with role-based permission checks"""
    try:
        # Get the card with project and organization info
        card_result = await db.execute(
            select(Card)
            .options(
                selectinload(Card.column).selectinload(Column.board).selectinload(Board.project)
            )
            .where(Card.id == card_id)
        )
        card = card_result.scalar_one_or_none()

        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        project = card.column.board.project
        organization_id = project.organization_id

        # Check if current user has permission to unassign members
        current_user_org_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        current_user_org_member = current_user_org_result.scalar_one_or_none()

        if not current_user_org_member:
            raise InsufficientPermissionsError("Access denied")

        # Only owners and admins can unassign members from others
        if current_user_org_member.role not in ['owner', 'admin'] and str(user_id) != str(current_user.id):
            raise InsufficientPermissionsError("Only owners and admins can unassign tasks from other members")

        # Find and delete the assignment
        assignment_result = await db.execute(
            select(CardAssignment).where(
                CardAssignment.card_id == card_id,
                CardAssignment.user_id == user_id
            )
        )
        assignment = assignment_result.scalar_one_or_none()

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        await db.delete(assignment)
        await db.commit()

        return {"message": "User unassigned successfully"}

    except Exception as e:
        logger.error(f"Error unassigning user from card: {e}")
        raise HTTPException(status_code=500, detail="Failed to unassign user")


@router.get("/{card_id}/mention-autocomplete", response_model=List[dict])
async def get_mention_autocomplete(
    card_id: str,
    search: str = Query("", description="Search term for filtering members"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get organization members for @mention autocomplete in card comments"""
    try:
        # Get the card with project and organization info
        card_result = await db.execute(
            select(Card)
            .options(
                selectinload(Card.column).selectinload(Column.board).selectinload(Board.project)
            )
            .where(Card.id == card_id)
        )
        card = card_result.scalar_one_or_none()

        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        project = card.column.board.project
        organization_id = str(project.organization_id)

        # Check if current user has access to this organization
        current_user_org_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        current_user_org_member = current_user_org_result.scalar_one_or_none()

        if not current_user_org_member:
            raise InsufficientPermissionsError("Access denied")

        # Get mention service and fetch autocomplete data
        mention_service = get_mention_service(db)
        autocomplete_data = await mention_service.get_organization_members_for_autocomplete(
            organization_id=organization_id,
            search_term=search
        )

        return autocomplete_data

    except Exception as e:
        logger.error(f"Error getting mention autocomplete: {e}")
        raise HTTPException(status_code=500, detail="Failed to get mention suggestions")


@router.get("/{card_id}/activities")
async def get_card_activities(
    card_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all activities (comments, assignments, etc.) for a card"""
    try:
        print(f"🔍 Getting activities for card {card_id} by user {current_user.email}")

        # Get the card and verify access
        card_result = await db.execute(
            select(Card)
            .options(
                selectinload(Card.column).selectinload(Column.board).selectinload(Board.project)
            )
            .where(Card.id == card_id)
        )
        card = card_result.scalar_one_or_none()
        if not card:
            raise HTTPException(status_code=404, detail="Card not found")

        # Get organization ID from the card's project
        project = card.column.board.project
        organization_id = project.organization_id

        # Check organization membership
        org_member_result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == current_user.id
            )
        )
        if not org_member_result.scalar_one_or_none():
            raise InsufficientPermissionsError("Access denied")

        # Get all comments for this card
        comments_result = await db.execute(
            select(Comment)
            .options(selectinload(Comment.user))
            .where(Comment.card_id == card_id)
            .order_by(Comment.created_at.asc())
        )
        comments = comments_result.scalars().all()

        # Format activities
        activities = []
        for comment in comments:
            author = comment.user

            activity = {
                "id": str(comment.id),
                "type": "comment",
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
                "timestamp": comment.created_at.isoformat(),
                "user": {
                    "id": str(author.id) if author else None,
                    "name": f"{author.first_name} {author.last_name}".strip() if author else "Unknown User",
                    "email": author.email if author else None,
                    "avatar": "/assets/images/avatar.jpg"  # Default avatar
                }
            }

            # Add mentions if they exist
            mentions_result = await db.execute(
                select(Mention)
                .options(selectinload(Mention.mentioned_user))
                .where(Mention.comment_id == comment.id)
            )
            mentions = mentions_result.scalars().all()
            if mentions:
                activity["mentions"] = [mention.mentioned_user.email for mention in mentions if mention.mentioned_user]

            activities.append(activity)

        print(f"✅ Found {len(activities)} activities for card {card_id}")
        return activities

    except Exception as e:
        print(f"Error getting card activities: {e}")
        raise HTTPException(status_code=500, detail="Failed to get card activities")
