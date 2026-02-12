"""Add charts and chart_folders tables

Revision ID: 007_add_charts
Revises: b5400357036d
Create Date: 2025-01-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

# revision identifiers, used by Alembic.
revision = '007_add_charts'
down_revision = 'b5400357036d'
branch_labels = None
depends_on = None


def upgrade():
    # Create chart_folders table
    op.create_table(
        'chart_folders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_id', UUID(as_uuid=True), sa.ForeignKey('chart_folders.id', ondelete='CASCADE'), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.text('NOW()')),
    )
    op.create_index('ix_chart_folders_tenant_id', 'chart_folders', ['tenant_id'])
    op.create_index('ix_chart_folders_parent_id', 'chart_folders', ['parent_id'])
    
    # Create charts table
    op.create_table(
        'charts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Chart type enum
        sa.Column('chart_type', sa.String(20), nullable=False),
        
        # Data source
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('semantic_model_id', UUID(as_uuid=True), sa.ForeignKey('semantic_models.id', ondelete='SET NULL'), nullable=True),
        sa.Column('sql_query', sa.Text(), nullable=True),
        
        # Configuration (JSONB)
        sa.Column('query_config', JSONB, nullable=False, server_default='{}'),
        sa.Column('viz_config', JSONB, nullable=False, server_default='{}'),
        
        # Organization
        sa.Column('folder_id', UUID(as_uuid=True), sa.ForeignKey('chart_folders.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tags', ARRAY(sa.String), nullable=False, server_default='{}'),
        
        # Ownership & sharing
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        
        # Caching
        sa.Column('cached_data', JSONB, nullable=True),
        sa.Column('cache_expires_at', sa.DateTime(), nullable=True),
        sa.Column('cache_ttl_seconds', sa.Integer(), nullable=False, server_default='300'),
        
        # Soft delete
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.text('NOW()')),
    )
    op.create_index('ix_charts_tenant_id', 'charts', ['tenant_id'])
    op.create_index('ix_charts_folder_id', 'charts', ['folder_id'])
    op.create_index('ix_charts_semantic_model_id', 'charts', ['semantic_model_id'])
    op.create_index('ix_charts_created_by', 'charts', ['created_by'])
    
    # Create dashboard_charts junction table
    op.create_table(
        'dashboard_charts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dashboard_id', UUID(as_uuid=True), sa.ForeignKey('dashboards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('chart_id', UUID(as_uuid=True), sa.ForeignKey('charts.id', ondelete='CASCADE'), nullable=False),
        
        # Grid position
        sa.Column('grid_position', JSONB, nullable=False, server_default='{}'),
        
        # Local overrides
        sa.Column('local_filters', JSONB, nullable=False, server_default='{}'),
        sa.Column('local_viz_config', JSONB, nullable=False, server_default='{}'),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, onupdate=sa.text('NOW()')),
    )
    op.create_index('ix_dashboard_charts_dashboard_id', 'dashboard_charts', ['dashboard_id'])
    op.create_index('ix_dashboard_charts_chart_id', 'dashboard_charts', ['chart_id'])
    op.create_unique_constraint('uq_dashboard_chart', 'dashboard_charts', ['dashboard_id', 'chart_id'])


def downgrade():
    # Drop tables in reverse order
    op.drop_table('dashboard_charts')
    op.drop_table('charts')
    op.drop_table('chart_folders')
