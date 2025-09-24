"""Add mentions table

Revision ID: add_mentions_table
Revises: add_support_tables
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_mentions_table'
down_revision = 'add_support_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create mentions table
    op.create_table('mentions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('comment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mentioned_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mentioned_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('mention_text', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mentioned_by_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['mentioned_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better performance
    op.create_index('ix_mentions_comment_id', 'mentions', ['comment_id'])
    op.create_index('ix_mentions_mentioned_user_id', 'mentions', ['mentioned_user_id'])
    op.create_index('ix_mentions_mentioned_by_user_id', 'mentions', ['mentioned_by_user_id'])
    op.create_index('ix_mentions_is_read', 'mentions', ['is_read'])
    op.create_index('ix_mentions_created_at', 'mentions', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_mentions_created_at', table_name='mentions')
    op.drop_index('ix_mentions_is_read', table_name='mentions')
    op.drop_index('ix_mentions_mentioned_by_user_id', table_name='mentions')
    op.drop_index('ix_mentions_mentioned_user_id', table_name='mentions')
    op.drop_index('ix_mentions_comment_id', table_name='mentions')
    
    # Drop table
    op.drop_table('mentions')
