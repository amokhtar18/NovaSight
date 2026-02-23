"""Add infrastructure configurations table

Revision ID: 006
Revises: 005_add_rbac_tables
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005_add_rbac_tables'
branch_labels = None
depends_on = None


def upgrade():
    """Create infrastructure_configs table."""
    op.create_table(
        'infrastructure_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_type', sa.String(50), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_system_default', sa.Boolean(), nullable=False, default=False),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('settings', postgresql.JSONB(), nullable=False, default=dict),
        sa.Column('credential_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('last_test_at', sa.DateTime(), nullable=True),
        sa.Column('last_test_success', sa.Boolean(), nullable=True),
        sa.Column('last_test_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['tenant_id'], 
            ['public.tenants.id'],
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    
    # Create indexes
    op.create_index(
        'ix_infrastructure_configs_service_type',
        'infrastructure_configs',
        ['service_type'],
        schema='public'
    )
    op.create_index(
        'ix_infrastructure_configs_tenant_id',
        'infrastructure_configs',
        ['tenant_id'],
        schema='public'
    )
    op.create_index(
        'ix_infrastructure_configs_active',
        'infrastructure_configs',
        ['service_type', 'tenant_id', 'is_active'],
        schema='public'
    )


def downgrade():
    """Drop infrastructure_configs table."""
    op.drop_index('ix_infrastructure_configs_active', table_name='infrastructure_configs', schema='public')
    op.drop_index('ix_infrastructure_configs_tenant_id', table_name='infrastructure_configs', schema='public')
    op.drop_index('ix_infrastructure_configs_service_type', table_name='infrastructure_configs', schema='public')
    op.drop_table('infrastructure_configs', schema='public')
