"""Add pyspark_apps table

Revision ID: 002_add_pyspark_apps
Revises: 001_initial_schema
Create Date: 2026-01-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_pyspark_apps'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    source_type = postgresql.ENUM('table', 'query', name='sourcetype', create_type=False)
    source_type.create(op.get_bind(), checkfirst=True)
    
    write_mode = postgresql.ENUM('append', 'overwrite', 'merge', name='writemode', create_type=False)
    write_mode.create(op.get_bind(), checkfirst=True)
    
    scd_type = postgresql.ENUM('none', 'type1', 'type2', name='scdtype', create_type=False)
    scd_type.create(op.get_bind(), checkfirst=True)
    
    cdc_type = postgresql.ENUM('none', 'timestamp', 'version', 'hash', name='cdctype', create_type=False)
    cdc_type.create(op.get_bind(), checkfirst=True)
    
    pyspark_app_status = postgresql.ENUM('draft', 'active', 'inactive', 'error', name='pysparkappstatus', create_type=False)
    pyspark_app_status.create(op.get_bind(), checkfirst=True)
    
    # Create pyspark_apps table
    op.create_table(
        'pyspark_apps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_connections.id'), nullable=False, index=True),
        
        # Identity
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Status
        sa.Column('status', sa.Enum('draft', 'active', 'inactive', 'error', name='pysparkappstatus'), 
                  nullable=False, server_default='draft'),
        
        # Source Configuration
        sa.Column('source_type', sa.Enum('table', 'query', name='sourcetype'), 
                  nullable=False, server_default='table'),
        sa.Column('source_schema', sa.String(255), nullable=True),
        sa.Column('source_table', sa.String(255), nullable=True),
        sa.Column('source_query', sa.Text(), nullable=True),
        
        # Column Configuration
        sa.Column('columns_config', postgresql.JSONB(), nullable=False, server_default='[]'),
        
        # Primary Key Configuration
        sa.Column('primary_key_columns', postgresql.JSONB(), nullable=False, server_default='[]'),
        
        # CDC Configuration
        sa.Column('cdc_type', sa.Enum('none', 'timestamp', 'version', 'hash', name='cdctype'), 
                  nullable=False, server_default='none'),
        sa.Column('cdc_column', sa.String(255), nullable=True),
        sa.Column('cdc_high_watermark', sa.Text(), nullable=True),
        
        # Partition Configuration
        sa.Column('partition_columns', postgresql.JSONB(), nullable=False, server_default='[]'),
        
        # SCD Configuration
        sa.Column('scd_type', sa.Enum('none', 'type1', 'type2', name='scdtype'), 
                  nullable=False, server_default='none'),
        
        # Write Mode
        sa.Column('write_mode', sa.Enum('append', 'overwrite', 'merge', name='writemode'), 
                  nullable=False, server_default='append'),
        
        # Target Configuration
        sa.Column('target_database', sa.String(255), nullable=True),
        sa.Column('target_table', sa.String(255), nullable=True),
        sa.Column('target_engine', sa.String(100), nullable=False, server_default='MergeTree'),
        
        # Additional Options
        sa.Column('options', postgresql.JSONB(), nullable=False, server_default='{}'),
        
        # Generated Artifacts
        sa.Column('generated_code', sa.Text(), nullable=True),
        sa.Column('generated_code_hash', sa.String(64), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.Column('template_version', sa.String(50), nullable=True),
        
        # Execution Stats
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_status', sa.String(50), nullable=True),
        sa.Column('last_run_rows', sa.Integer(), nullable=True),
        sa.Column('last_run_duration_ms', sa.Integer(), nullable=True),
        
        # Audit
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        # Constraints
        sa.UniqueConstraint('tenant_id', 'name', name='uq_tenant_pyspark_app_name'),
    )
    
    # Create indexes
    op.create_index('ix_pyspark_apps_status', 'pyspark_apps', ['status'])
    op.create_index('ix_pyspark_apps_created_at', 'pyspark_apps', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_pyspark_apps_created_at', table_name='pyspark_apps')
    op.drop_index('ix_pyspark_apps_status', table_name='pyspark_apps')
    
    # Drop table
    op.drop_table('pyspark_apps')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS pysparkappstatus')
    op.execute('DROP TYPE IF EXISTS cdctype')
    op.execute('DROP TYPE IF EXISTS scdtype')
    op.execute('DROP TYPE IF EXISTS writemode')
    op.execute('DROP TYPE IF EXISTS sourcetype')
