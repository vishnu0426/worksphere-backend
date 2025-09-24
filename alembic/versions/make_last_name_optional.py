"""Make last_name optional in users table

Revision ID: make_last_name_optional
Revises: 
Create Date: 2025-09-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'make_last_name_optional'
down_revision = None  # Update this with the actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """Make last_name column nullable in users table"""
    # Make last_name column nullable
    op.alter_column('users', 'last_name',
                    existing_type=sa.String(100),
                    nullable=True)


def downgrade():
    """Revert last_name column to non-nullable"""
    # First, update any NULL values to empty string to avoid constraint violation
    op.execute("UPDATE users SET last_name = '' WHERE last_name IS NULL")
    
    # Make last_name column non-nullable again
    op.alter_column('users', 'last_name',
                    existing_type=sa.String(100),
                    nullable=False)
