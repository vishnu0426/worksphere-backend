"""Add support system tables

Revision ID: add_support_tables
Revises: 
Create Date: 2024-12-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_support_tables'
down_revision = None  # Replace with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Create support_categories table
    op.create_table('support_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['support_categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.UniqueConstraint('slug')
    )

    # Create support_tickets table
    op.create_table('support_tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_number', sa.String(length=20), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('assigned_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('resolution_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ticket_number')
    )

    # Create support_messages table
    op.create_table('support_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('ticket_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=False),
        sa.Column('attachments', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['support_tickets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create help_articles table
    op.create_table('help_articles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('subcategory', sa.String(length=100), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False),
        sa.Column('is_featured', sa.Boolean(), nullable=False),
        sa.Column('meta_title', sa.String(length=255), nullable=True),
        sa.Column('meta_description', sa.String(length=500), nullable=True),
        sa.Column('view_count', sa.Integer(), nullable=False),
        sa.Column('helpful_votes', sa.Integer(), nullable=False),
        sa.Column('unhelpful_votes', sa.Integer(), nullable=False),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )

    # Create contact_messages table
    op.create_table('contact_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_message', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create support_settings table
    op.create_table('support_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('auto_assign_tickets', sa.Boolean(), nullable=False),
        sa.Column('default_priority', sa.String(length=20), nullable=False),
        sa.Column('business_hours_enabled', sa.Boolean(), nullable=False),
        sa.Column('business_hours', sa.JSON(), nullable=True),
        sa.Column('response_time_low', sa.Integer(), nullable=False),
        sa.Column('response_time_medium', sa.Integer(), nullable=False),
        sa.Column('response_time_high', sa.Integer(), nullable=False),
        sa.Column('response_time_urgent', sa.Integer(), nullable=False),
        sa.Column('support_email', sa.String(length=255), nullable=True),
        sa.Column('email_notifications_enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for better performance
    op.create_index('idx_support_tickets_user_id', 'support_tickets', ['user_id'])
    op.create_index('idx_support_tickets_organization_id', 'support_tickets', ['organization_id'])
    op.create_index('idx_support_tickets_status', 'support_tickets', ['status'])
    op.create_index('idx_support_tickets_category', 'support_tickets', ['category'])
    op.create_index('idx_support_tickets_priority', 'support_tickets', ['priority'])
    op.create_index('idx_support_tickets_created_at', 'support_tickets', ['created_at'])
    
    op.create_index('idx_support_messages_ticket_id', 'support_messages', ['ticket_id'])
    op.create_index('idx_support_messages_user_id', 'support_messages', ['user_id'])
    op.create_index('idx_support_messages_created_at', 'support_messages', ['created_at'])
    
    op.create_index('idx_help_articles_category', 'help_articles', ['category'])
    op.create_index('idx_help_articles_is_published', 'help_articles', ['is_published'])
    op.create_index('idx_help_articles_is_featured', 'help_articles', ['is_featured'])
    op.create_index('idx_help_articles_created_at', 'help_articles', ['created_at'])
    
    op.create_index('idx_contact_messages_status', 'contact_messages', ['status'])
    op.create_index('idx_contact_messages_user_id', 'contact_messages', ['user_id'])
    op.create_index('idx_contact_messages_created_at', 'contact_messages', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_contact_messages_created_at', table_name='contact_messages')
    op.drop_index('idx_contact_messages_user_id', table_name='contact_messages')
    op.drop_index('idx_contact_messages_status', table_name='contact_messages')
    
    op.drop_index('idx_help_articles_created_at', table_name='help_articles')
    op.drop_index('idx_help_articles_is_featured', table_name='help_articles')
    op.drop_index('idx_help_articles_is_published', table_name='help_articles')
    op.drop_index('idx_help_articles_category', table_name='help_articles')
    
    op.drop_index('idx_support_messages_created_at', table_name='support_messages')
    op.drop_index('idx_support_messages_user_id', table_name='support_messages')
    op.drop_index('idx_support_messages_ticket_id', table_name='support_messages')
    
    op.drop_index('idx_support_tickets_created_at', table_name='support_tickets')
    op.drop_index('idx_support_tickets_priority', table_name='support_tickets')
    op.drop_index('idx_support_tickets_category', table_name='support_tickets')
    op.drop_index('idx_support_tickets_status', table_name='support_tickets')
    op.drop_index('idx_support_tickets_organization_id', table_name='support_tickets')
    op.drop_index('idx_support_tickets_user_id', table_name='support_tickets')
    
    # Drop tables
    op.drop_table('support_settings')
    op.drop_table('contact_messages')
    op.drop_table('help_articles')
    op.drop_table('support_messages')
    op.drop_table('support_tickets')
    op.drop_table('support_categories')
