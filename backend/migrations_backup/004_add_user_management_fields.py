"""Add role is_default and user password_changed_at fields

Revision ID: 004_add_user_management_fields
Revises: 003_add_dashboards
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_user_management_fields'
down_revision = '003_add_dashboards'
branch_labels = None
depends_on = None


def upgrade():
    """Add new fields for user and role management."""
    
    # Add is_default column to roles table
    op.add_column(
        'roles',
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false')
    )
    
    # Add password_changed_at column to users table
    op.add_column(
        'users',
        sa.Column('password_changed_at', sa.DateTime(), nullable=True)
    )
    
    # Create index for faster role lookups by tenant and default status
    op.create_index(
        'ix_roles_tenant_default',
        'roles',
        ['tenant_id', 'is_default'],
        unique=False
    )


def downgrade():
    """Remove the added fields."""
    
    # Drop index
    op.drop_index('ix_roles_tenant_default', table_name='roles')
    
    # Drop columns
    op.drop_column('users', 'password_changed_at')
    op.drop_column('roles', 'is_default')
