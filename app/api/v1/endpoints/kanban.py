"""
Comprehensive Kanban Board API Endpoints
Handles all board, column, and card operations
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.core.exceptions import ResourceNotFoundError, InsufficientPermissionsError
from app.models.user import User
from app.models.board import Board
from app.models.column import Column as ColumnModel
from app.services.kanban_service import KanbanService

router = APIRouter()

# Pydantic models for request/response
class BoardResponse(BaseModel):
    id: str
    name: str
    description: str
    project_id: str
    columns: List[dict]
    created_at: str
    updated_at: str

class ColumnCreate(BaseModel):
    name: str
    color: str = "#E5E7EB"

class ColumnResponse(BaseModel):
    id: str
    name: str
    position: int
    color: str
    board_id: str
    created_at: str
    updated_at: str

class CardCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    assigned_to: Optional[List[str]] = None
    due_date: Optional[datetime] = None
    labels: Optional[List[dict]] = None

class CardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    labels: Optional[List[dict]] = None
    assigned_to: Optional[List[str]] = None

class CardMove(BaseModel):
    target_column_id: str
    position: Optional[int] = None

class CardResponse(BaseModel):
    id: str
    column_id: str
    title: str
    description: str
    position: int
    priority: str
    status: str
    due_date: Optional[str]
    labels: List[dict]
    created_by: str
    created_at: str
    updated_at: str
    assignments: List[dict]


@router.get("/projects/{project_id}/board", response_model=BoardResponse)
async def get_or_create_project_board(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get or create a Kanban board for a project"""
    try:
        kanban_service = KanbanService(db)
        board = await kanban_service.get_or_create_project_board(
            project_id=project_id,
            user_id=str(current_user.id)
        )
        
        # Get board with columns
        board_data = await kanban_service.get_board_with_columns(
            board_id=str(board.id),
            user_id=str(current_user.id)
        )
        
        # Return the board data directly to match BoardResponse schema
        return board_data
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error in get_or_create_project_board: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get board: {str(e)}"
        )


@router.post("/boards/{board_id}/columns", response_model=ColumnResponse)
async def create_column(
    board_id: str,
    column_data: ColumnCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new column in a board"""
    try:
        kanban_service = KanbanService(db)
        column = await kanban_service.create_column(
            board_id=board_id,
            user_id=str(current_user.id),
            name=column_data.name,
            color=column_data.color
        )
        
        # Return the column data directly to match ColumnResponse schema
        return column
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create column: {str(e)}"
        )


@router.get("/columns/{column_id}/cards")
async def get_column_cards(
    column_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all cards in a column"""
    try:
        kanban_service = KanbanService(db)
        cards = await kanban_service.get_column_cards(
            column_id=column_id,
            user_id=str(current_user.id)
        )
        
        return {
            "success": True,
            "data": cards,
            "message": "Cards retrieved successfully"
        }
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cards: {str(e)}"
        )


@router.post("/columns/{column_id}/cards", response_model=CardResponse)
async def create_card(
    column_id: str,
    card_data: CardCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new card in a column"""
    try:
        print(f"🔧 Creating card in column {column_id}")
        print(f"🔧 Card data: {card_data}")
        print(f"🔧 User: {current_user.email}")

        kanban_service = KanbanService(db)
        card = await kanban_service.create_card(
            column_id=column_id,
            user_id=str(current_user.id),
            title=card_data.title,
            description=card_data.description,
            priority=card_data.priority,
            assigned_to=card_data.assigned_to,
            due_date=card_data.due_date,
            labels=card_data.labels
        )

        # Send email notifications to assigned members
        if card_data.assigned_to:
            # Get column and project info for email context
            column_result = await db.execute(
                select(ColumnModel)
                .options(
                    selectinload(ColumnModel.board).selectinload(Board.project)
                )
                .where(ColumnModel.id == column_id)
            )
            column = column_result.scalar_one_or_none()

            if column and column.board and column.board.project:
                project_name = column.board.project.name
                organization_id = str(column.board.project.organization_id)

                # Import email notification service
                from app.services.enhanced_email_notification_service import get_enhanced_notification_service
                enhanced_service = get_enhanced_notification_service(db)

                # Send notifications to each assigned user
                for user_id in card_data.assigned_to:
                    background_tasks.add_task(
                        enhanced_service.send_task_assignment_notification,
                        user_id=user_id,
                        task_id=str(card["id"]),
                        task_title=card["title"],
                        task_description=card["description"] or "",
                        assigner_id=str(current_user.id),
                        project_name=project_name,
                        organization_id=organization_id,
                        due_date=card_data.due_date,
                        priority=card_data.priority or "medium"
                    )
        
        print(f"✅ Card created successfully: {card['id']}")
        
        # Return the card data directly to match CardResponse schema
        return card
        
    except ResourceNotFoundError as e:
        print(f"❌ Resource not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientPermissionsError as e:
        print(f"❌ Permission denied: {e}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error creating card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create card: {str(e)}"
        )


@router.put("/cards/{card_id}/move")
async def move_card(
    card_id: str,
    move_data: CardMove,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Move a card to a different column"""
    try:
        kanban_service = KanbanService(db)
        result = await kanban_service.move_card(
            card_id=card_id,
            target_column_id=move_data.target_column_id,
            user_id=str(current_user.id),
            position=move_data.position
        )
        
        return {
            "success": True,
            "data": result,
            "message": "Card moved successfully"
        }
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to move card: {str(e)}"
        )


@router.put("/cards/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: str,
    card_data: CardUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update card details"""
    try:
        print(f"🔧 Updating card {card_id} for user {current_user.id}")
        print(f"🔧 Card data: {card_data}")

        kanban_service = KanbanService(db)

        # Get current card assignments before update for comparison
        current_card = await kanban_service.get_card(card_id, str(current_user.id))
        current_assignments = set(assignment.get('user_id') for assignment in current_card.get('assignments', []))

        card = await kanban_service.update_card(
            card_id=card_id,
            user_id=str(current_user.id),
            title=card_data.title,
            description=card_data.description,
            priority=card_data.priority,
            due_date=card_data.due_date,
            labels=card_data.labels,
            assigned_to=card_data.assigned_to
            # checklist=card_data.checklist  # Temporarily disabled
        )

        print(f"✅ Card updated successfully: {card}")

        # Send email notifications for new assignments
        if card_data.assigned_to:
            new_assignments = set(card_data.assigned_to) - current_assignments
            if new_assignments:
                # Get card and project info for email context
                card_result = await db.execute(
                    select(ColumnModel)
                    .options(
                        selectinload(ColumnModel.board).selectinload(Board.project)
                    )
                    .where(ColumnModel.id == card.get('column_id'))
                )
                column = card_result.scalar_one_or_none()

                if column and column.board and column.board.project:
                    project_name = column.board.project.name
                    organization_id = str(column.board.project.organization_id)

                    # Import email notification service
                    from app.services.enhanced_email_notification_service import get_enhanced_notification_service
                    enhanced_service = get_enhanced_notification_service(db)

                    # Send notifications to newly assigned users
                    for user_id in new_assignments:
                        background_tasks.add_task(
                            enhanced_service.send_task_assignment_notification,
                            user_id=user_id,
                            task_id=str(card["id"]),
                            task_title=card["title"],
                            task_description=card["description"] or "",
                            assigner_id=str(current_user.id),
                            project_name=project_name,
                            organization_id=organization_id,
                            due_date=card_data.due_date,
                            priority=card_data.priority or "medium"
                        )

        return {
            "success": True,
            "data": card,
            "message": "Card updated successfully"
        }
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        print(f"❌ Error updating card {card_id}: {str(e)}")
        print(f"❌ Error type: {type(e)}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update card: {str(e)}"
        )


@router.delete("/cards/{card_id}")
async def delete_card(
    card_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a card"""
    try:
        kanban_service = KanbanService(db)
        await kanban_service.delete_card(
            card_id=card_id,
            user_id=str(current_user.id)
        )
        
        return {
            "success": True,
            "message": "Card deleted successfully"
        }
        
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except InsufficientPermissionsError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete card: {str(e)}"
        )
