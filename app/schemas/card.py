"""
Card schemas
"""
from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class CardCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    column_id: str  # Required column ID
    position: Optional[int] = None  # Will be auto-calculated if not provided
    priority: str = "medium"
    due_date: Optional[datetime] = None
    assigned_to: Optional[List[str]] = None  # List of user IDs
    checklist: Optional[List[Dict[str, Any]]] = None  # AI-generated checklist items
    labels: Optional[list] = None  # List of label strings or objects
    
    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Card title cannot be empty')
        return v.strip()
    
    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'medium', 'high', 'urgent']:
            raise ValueError('Priority must be low, medium, high, or urgent')
        return v
    
    @validator('position')
    def validate_position(cls, v):
        if v is not None and v < 0:
            raise ValueError('Position must be non-negative')
        return v


class CardUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    position: Optional[int] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assigned_to: Optional[List[str]] = None
    checklist: Optional[List[Dict[str, Any]]] = None
    labels: Optional[list] = None  # List of label strings or objects
    
    @validator('title')
    def validate_title(cls, v):
        if v is not None and not v.strip():
            raise ValueError('Card title cannot be empty')
        return v.strip() if v else v
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is not None and v not in ['low', 'medium', 'high', 'urgent']:
            raise ValueError('Priority must be low, medium, high, or urgent')
        return v
    
    @validator('position')
    def validate_position(cls, v):
        if v is not None and v < 0:
            raise ValueError('Position must be non-negative')
        return v


class CardMove(BaseModel):
    target_column_id: UUID
    position: Optional[int] = None

    @validator('position')
    def validate_position(cls, v):
        """Validate that the provided position is non-negative if set.

        The position field is optional when moving a card.  If provided, it must
        be a non‑negative integer.  When omitted, the API will append the card
        to the end of the target column.
        """
        if v is not None and v < 0:
            raise ValueError('Position must be non-negative')
        return v


class CardAssignmentResponse(BaseModel):
    id: UUID
    user_id: UUID
    assigned_by: Optional[UUID] = None
    assigned_at: datetime
    user: dict  # Will contain user details
    
    class Config:
        from_attributes = True


class CardResponse(BaseModel):
    id: UUID
    column_id: UUID
    title: str
    description: Optional[str] = None
    position: int
    priority: str
    status: str = "todo"  # Added missing status field
    due_date: Optional[datetime] = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    labels: Optional[list] = None
    assignments: Optional[List[CardAssignmentResponse]] = []
    checklist_items: Optional[List[Dict[str, Any]]] = []

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        # Handle the relationships manually to avoid async issues
        data = {
            'id': obj.id,
            'column_id': obj.column_id,
            'title': obj.title,
            'description': obj.description,
            'position': obj.position,
            'priority': obj.priority,
            'status': obj.status,
            'due_date': obj.due_date,
            'created_by': obj.created_by,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'labels': obj.labels or [],
            'assignments': [],
            'checklist_items': []
        }

        # Handle assignments if loaded
        if hasattr(obj, 'assignments') and obj.assignments:
            try:
                data['assignments'] = [CardAssignmentResponse.from_orm(assignment) for assignment in obj.assignments]
            except:
                data['assignments'] = []

        # Handle checklist items if loaded
        if hasattr(obj, 'checklist_items') and obj.checklist_items:
            try:
                data['checklist_items'] = [
                    {
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
                    for item in obj.checklist_items
                ]
            except:
                data['checklist_items'] = []

        return cls(**data)


class CommentCreate(BaseModel):
    content: str
    
    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Comment content cannot be empty')
        return v.strip()


class CommentUpdate(BaseModel):
    content: str
    
    @validator('content')
    def validate_content(cls, v):
        if not v.strip():
            raise ValueError('Comment content cannot be empty')
        return v.strip()


class CommentResponse(BaseModel):
    id: str
    card_id: str
    user_id: str
    content: str
    created_at: datetime
    updated_at: datetime
    user: dict  # Will contain user details

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm method to handle UUID conversion"""
        # Convert UUID objects to strings
        data = {
            'id': str(obj.id),
            'card_id': str(obj.card_id),
            'user_id': str(obj.user_id),
            'content': obj.content,
            'created_at': obj.created_at,
            'updated_at': obj.updated_at,
            'user': {
                'id': str(obj.user.id) if obj.user else None,
                'name': f"{obj.user.first_name} {obj.user.last_name}".strip() if obj.user else "Unknown User",
                'email': obj.user.email if obj.user else None,
                'avatar': "/assets/images/avatar.jpg"  # Default avatar
            } if obj.user else {}
        }
        return cls(**data)


class AttachmentResponse(BaseModel):
    id: str
    card_id: str
    filename: str
    original_name: str
    file_size: int
    mime_type: str
    file_url: str
    uploaded_by: str
    uploaded_at: datetime
    uploader: dict  # Will contain user details

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm method to handle UUID conversion"""
        # Convert UUID objects to strings
        data = {
            'id': str(obj.id),
            'card_id': str(obj.card_id),
            'filename': obj.filename,
            'original_name': obj.original_name,
            'file_size': obj.file_size,
            'mime_type': obj.mime_type,
            'file_url': obj.file_url,
            'uploaded_by': str(obj.uploaded_by),
            'uploaded_at': obj.uploaded_at,
            'uploader': {
                'id': str(obj.uploader.id) if obj.uploader else None,
                'name': f"{obj.uploader.first_name} {obj.uploader.last_name}".strip() if obj.uploader else "Unknown User",
                'email': obj.uploader.email if obj.uploader else None,
                'avatar': "/assets/images/avatar.jpg"  # Default avatar
            } if obj.uploader else {}
        }
        return cls(**data)


class ActivityResponse(BaseModel):
    id: str
    user_id: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    user: dict  # Will contain user details

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm method to handle UUID conversion"""
        # Convert UUID objects to strings
        data = {
            'id': str(obj.id),
            'user_id': str(obj.user_id),
            'action': obj.action,
            'resource_type': obj.resource_type,
            'resource_id': str(obj.resource_id) if obj.resource_id else None,
            'metadata': obj.metadata,
            'created_at': obj.created_at,
            'user': {
                'id': str(obj.user.id) if obj.user else None,
                'name': f"{obj.user.first_name} {obj.user.last_name}".strip() if obj.user else "Unknown User",
                'email': obj.user.email if obj.user else None,
                'avatar': "/assets/images/avatar.jpg"  # Default avatar
            } if obj.user else {}
        }
        return cls(**data)
