"""Add dashboards and widgets tables

Revision ID: 003_add_dashboards
Revises: 002_add_pyspark_apps
Create Date: 2026-01-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_dashboards'
down_revision = '002_add_pyspark_apps'
branch_labels = None
depends_on = None


def upgrade():
    # Create widget type enum
    widget_type = postgresql.ENUM(
        'bar_chart', 'line_chart', 'pie_chart', 'table', 'metric_card',
        'area_chart', 'scatter_plot', 'heatmap', 'donut_chart', 'gauge',
        'treemap', 'funnel', 'text',
        name='widgettype',
        create_type=False
    )
    widget_type.create(op.get_bind(), checkfirst=True)
    
    # Create dashboards table
    op.create_table(
        'dashboards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        
        # Identity
        sa.Column('name', sa.String(100), nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Layout configuration
        sa.Column('layout', postgresql.JSONB(), nullable=False, server_default='[]'),
        
        # Sharing settings
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('shared_with', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), 
                  nullable=False, server_default='{}'),
        
        # Global filters
        sa.Column('global_filters', postgresql.JSONB(), nullable=False, server_default='{}'),
        
        # Refresh settings
        sa.Column('auto_refresh', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('refresh_interval', sa.Integer(), nullable=True),
        
        # Theme
        sa.Column('theme', postgresql.JSONB(), nullable=False, server_default='{}'),
        
        # Tags
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        
        # Ownership
        sa.Column('created_by', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('users.id'), nullable=False),
        
        # Soft delete
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                  server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                  server_default=sa.func.current_timestamp()),
    )
    
    # Create widgets table
    op.create_table(
        'widgets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('tenants.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        sa.Column('dashboard_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('dashboards.id', ondelete='CASCADE'), 
                  nullable=False, index=True),
        
        # Identity
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('type', postgresql.ENUM(
            'bar_chart', 'line_chart', 'pie_chart', 'table', 'metric_card',
            'area_chart', 'scatter_plot', 'heatmap', 'donut_chart', 'gauge',
            'treemap', 'funnel', 'text',
            name='widgettype',
            create_type=False
        ), nullable=False),
        
        # Query configuration
        sa.Column('query_config', postgresql.JSONB(), nullable=False, server_default='{}'),
        
        # Visualization configuration
        sa.Column('viz_config', postgresql.JSONB(), nullable=False, server_default='{}'),
        
        # Grid position
        sa.Column('grid_position', postgresql.JSONB(), nullable=False, server_default='{}'),
        
        # Cache
        sa.Column('cached_data', postgresql.JSONB(), nullable=True),
        sa.Column('cache_expires_at', sa.DateTime(), nullable=True),
        
        # Local filters
        sa.Column('local_filters', postgresql.JSONB(), nullable=False, server_default='{}'),
        
        # Drilldown configuration
        sa.Column('drilldown_config', postgresql.JSONB(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False, 
                  server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, 
                  server_default=sa.func.current_timestamp()),
    )
    
    # Create indexes for efficient queries
    op.create_index(
        'ix_dashboards_created_by',
        'dashboards',
        ['created_by']
    )
    
    op.create_index(
        'ix_dashboards_is_public',
        'dashboards',
        ['is_public'],
        postgresql_where=sa.text('is_deleted = false')
    )
    
    op.create_index(
        'ix_dashboards_tenant_deleted',
        'dashboards',
        ['tenant_id', 'is_deleted']
    )
    
    op.create_index(
        'ix_widgets_type',
        'widgets',
        ['type']
    )


def downgrade():
    # Drop indexes
    op.drop_index('ix_widgets_type', table_name='widgets')
    op.drop_index('ix_dashboards_tenant_deleted', table_name='dashboards')
    op.drop_index('ix_dashboards_is_public', table_name='dashboards')
    op.drop_index('ix_dashboards_created_by', table_name='dashboards')
    
    # Drop tables
    op.drop_table('widgets')
    op.drop_table('dashboards')
    
    # Drop enum type
    op.execute('DROP TYPE IF EXISTS widgettype')
