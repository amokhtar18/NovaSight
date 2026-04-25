"""add_dlt_pipelines_table

Revision ID: e2f3g4h5i6j7
Revises: d1e2f3a4b5c6
Create Date: 2026-04-25 21:00:00.000000

Phase 2 of Spark → dlt migration: Create dlt_pipelines table
for dlt-based data ingestion pipelines.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e2f3g4h5i6j7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the dlt_pipelines table."""
    
    # Create enum types
    op.execute("CREATE TYPE source_type AS ENUM ('table', 'query')")
    op.execute("CREATE TYPE write_disposition AS ENUM ('append', 'replace', 'merge', 'scd2')")
    op.execute("CREATE TYPE incremental_cursor_type AS ENUM ('none', 'timestamp', 'version')")
    op.execute("CREATE TYPE dlt_pipeline_status AS ENUM ('draft', 'active', 'inactive', 'error')")
    
    # Create the dlt_pipelines table
    op.create_table(
        'dlt_pipelines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('draft', 'active', 'inactive', 'error', name='dlt_pipeline_status', create_type=False), nullable=False, server_default='draft'),
        
        # Source configuration
        sa.Column('source_type', postgresql.ENUM('table', 'query', name='source_type', create_type=False), nullable=False, server_default='table'),
        sa.Column('source_schema', sa.String(length=255), nullable=True),
        sa.Column('source_table', sa.String(length=255), nullable=True),
        sa.Column('source_query', sa.Text(), nullable=True),
        
        # Column configuration
        sa.Column('columns_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        
        # Key configuration
        sa.Column('primary_key_columns', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        
        # Incremental configuration
        sa.Column('incremental_cursor_column', sa.String(length=255), nullable=True),
        sa.Column('incremental_cursor_type', postgresql.ENUM('none', 'timestamp', 'version', name='incremental_cursor_type', create_type=False), nullable=False, server_default='none'),
        
        # Write configuration
        sa.Column('write_disposition', postgresql.ENUM('append', 'replace', 'merge', 'scd2', name='write_disposition', create_type=False), nullable=False, server_default='append'),
        
        # Partition configuration
        sa.Column('partition_columns', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        
        # Iceberg target configuration
        sa.Column('iceberg_namespace', sa.String(length=255), nullable=True),
        sa.Column('iceberg_table_name', sa.String(length=255), nullable=True),
        
        # Additional options
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        
        # Generated artifacts
        sa.Column('generated_code', sa.Text(), nullable=True),
        sa.Column('generated_code_hash', sa.String(length=64), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('template_name', sa.String(length=100), nullable=True),
        sa.Column('template_version', sa.String(length=50), nullable=True),
        
        # Execution stats
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_status', sa.String(length=50), nullable=True),
        sa.Column('last_run_rows', sa.Integer(), nullable=True),
        sa.Column('last_run_duration_ms', sa.Integer(), nullable=True),
        sa.Column('last_run_iceberg_snapshot_id', sa.String(length=64), nullable=True),
        
        # Audit
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['connection_id'], ['data_connections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_tenant_dlt_pipeline_name'),
    )
    
    # Create indexes
    op.create_index('ix_dlt_pipelines_tenant_id', 'dlt_pipelines', ['tenant_id'])
    op.create_index('ix_dlt_pipelines_connection_id', 'dlt_pipelines', ['connection_id'])
    op.create_index('ix_dlt_pipelines_status', 'dlt_pipelines', ['status'])
    op.create_index('ix_dlt_pipelines_updated_at', 'dlt_pipelines', ['updated_at'])


def downgrade() -> None:
    """Drop the dlt_pipelines table."""
    
    # Drop indexes
    op.drop_index('ix_dlt_pipelines_updated_at')
    op.drop_index('ix_dlt_pipelines_status')
    op.drop_index('ix_dlt_pipelines_connection_id')
    op.drop_index('ix_dlt_pipelines_tenant_id')
    
    # Drop table
    op.drop_table('dlt_pipelines')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS dlt_pipeline_status")
    op.execute("DROP TYPE IF EXISTS incremental_cursor_type")
    op.execute("DROP TYPE IF EXISTS write_disposition")
    op.execute("DROP TYPE IF EXISTS source_type")
