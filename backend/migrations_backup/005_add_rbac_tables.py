"""Add RBAC tables for permissions and resource permissions

Revision ID: 005_add_rbac_tables
Revises: 004_add_user_management_fields
Create Date: 2026-01-29

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_rbac_tables'
down_revision = '004_add_user_management_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Create RBAC tables."""
    
    # Create permissions table
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('category', sa.String(50), nullable=False, index=True),
        sa.Column('is_system', sa.Boolean, default=True, nullable=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now(), nullable=False),
    )
    
    # Create role_permissions association table
    op.create_table(
        'role_permissions',
        sa.Column(
            'role_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('roles.id', ondelete='CASCADE'),
            primary_key=True
        ),
        sa.Column(
            'permission_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('permissions.id', ondelete='CASCADE'),
            primary_key=True
        ),
        sa.Column('granted_at', sa.DateTime, default=sa.func.now()),
    )
    
    # Create resource_permissions table
    op.create_table(
        'resource_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            index=True
        ),
        sa.Column('resource_type', sa.String(50), nullable=False, index=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('permission', sa.String(20), nullable=False),
        sa.Column(
            'granted_by',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True
        ),
        sa.Column('granted_at', sa.DateTime, default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.UniqueConstraint(
            'user_id', 'resource_type', 'resource_id',
            name='uq_user_resource_permission'
        ),
    )
    
    # Create role_hierarchy table
    op.create_table(
        'role_hierarchy',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            'parent_role_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('roles.id', ondelete='CASCADE'),
            nullable=False
        ),
        sa.Column(
            'child_role_id',
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey('roles.id', ondelete='CASCADE'),
            nullable=False
        ),
        sa.UniqueConstraint(
            'parent_role_id', 'child_role_id',
            name='uq_role_hierarchy'
        ),
    )
    
    # Create indexes for better query performance
    op.create_index(
        'ix_resource_permissions_resource',
        'resource_permissions',
        ['resource_type', 'resource_id']
    )
    op.create_index(
        'ix_role_hierarchy_parent',
        'role_hierarchy',
        ['parent_role_id']
    )
    op.create_index(
        'ix_role_hierarchy_child',
        'role_hierarchy',
        ['child_role_id']
    )
    
    # Insert default system permissions
    op.execute("""
        INSERT INTO permissions (id, name, description, category, is_system, created_at)
        VALUES
        -- Datasources permissions
        (gen_random_uuid(), 'datasources.view', 'View data sources', 'datasources', true, NOW()),
        (gen_random_uuid(), 'datasources.create', 'Create data sources', 'datasources', true, NOW()),
        (gen_random_uuid(), 'datasources.edit', 'Edit data sources', 'datasources', true, NOW()),
        (gen_random_uuid(), 'datasources.delete', 'Delete data sources', 'datasources', true, NOW()),
        (gen_random_uuid(), 'datasources.sync', 'Sync data sources', 'datasources', true, NOW()),
        (gen_random_uuid(), 'datasources.test', 'Test data source connections', 'datasources', true, NOW()),
        
        -- Semantic permissions
        (gen_random_uuid(), 'semantic.view', 'View semantic models', 'semantic', true, NOW()),
        (gen_random_uuid(), 'semantic.create', 'Create semantic models', 'semantic', true, NOW()),
        (gen_random_uuid(), 'semantic.edit', 'Edit semantic models', 'semantic', true, NOW()),
        (gen_random_uuid(), 'semantic.delete', 'Delete semantic models', 'semantic', true, NOW()),
        (gen_random_uuid(), 'semantic.deploy', 'Deploy semantic models', 'semantic', true, NOW()),
        
        -- Analytics permissions
        (gen_random_uuid(), 'analytics.query', 'Execute queries', 'analytics', true, NOW()),
        (gen_random_uuid(), 'analytics.export', 'Export query results', 'analytics', true, NOW()),
        (gen_random_uuid(), 'analytics.schedule', 'Schedule analytics jobs', 'analytics', true, NOW()),
        
        -- Dashboard permissions
        (gen_random_uuid(), 'dashboards.view', 'View dashboards', 'dashboards', true, NOW()),
        (gen_random_uuid(), 'dashboards.create', 'Create dashboards', 'dashboards', true, NOW()),
        (gen_random_uuid(), 'dashboards.edit', 'Edit dashboards', 'dashboards', true, NOW()),
        (gen_random_uuid(), 'dashboards.delete', 'Delete dashboards', 'dashboards', true, NOW()),
        (gen_random_uuid(), 'dashboards.share', 'Share dashboards', 'dashboards', true, NOW()),
        (gen_random_uuid(), 'dashboards.publish', 'Publish dashboards', 'dashboards', true, NOW()),
        
        -- Pipeline permissions
        (gen_random_uuid(), 'pipelines.view', 'View pipelines', 'pipelines', true, NOW()),
        (gen_random_uuid(), 'pipelines.create', 'Create pipelines', 'pipelines', true, NOW()),
        (gen_random_uuid(), 'pipelines.edit', 'Edit pipelines', 'pipelines', true, NOW()),
        (gen_random_uuid(), 'pipelines.delete', 'Delete pipelines', 'pipelines', true, NOW()),
        (gen_random_uuid(), 'pipelines.deploy', 'Deploy pipelines', 'pipelines', true, NOW()),
        (gen_random_uuid(), 'pipelines.trigger', 'Trigger pipeline runs', 'pipelines', true, NOW()),
        
        -- User management permissions
        (gen_random_uuid(), 'users.view', 'View users', 'users', true, NOW()),
        (gen_random_uuid(), 'users.create', 'Create users', 'users', true, NOW()),
        (gen_random_uuid(), 'users.edit', 'Edit users', 'users', true, NOW()),
        (gen_random_uuid(), 'users.delete', 'Delete users', 'users', true, NOW()),
        (gen_random_uuid(), 'users.invite', 'Invite users', 'users', true, NOW()),
        
        -- Role management permissions
        (gen_random_uuid(), 'roles.view', 'View roles', 'roles', true, NOW()),
        (gen_random_uuid(), 'roles.create', 'Create roles', 'roles', true, NOW()),
        (gen_random_uuid(), 'roles.edit', 'Edit roles', 'roles', true, NOW()),
        (gen_random_uuid(), 'roles.delete', 'Delete roles', 'roles', true, NOW()),
        (gen_random_uuid(), 'roles.assign', 'Assign roles to users', 'roles', true, NOW()),
        
        -- Admin permissions
        (gen_random_uuid(), 'admin.settings.view', 'View admin settings', 'admin', true, NOW()),
        (gen_random_uuid(), 'admin.settings.edit', 'Edit admin settings', 'admin', true, NOW()),
        (gen_random_uuid(), 'admin.audit.view', 'View audit logs', 'admin', true, NOW()),
        (gen_random_uuid(), 'admin.tenants.view', 'View tenants', 'admin', true, NOW()),
        (gen_random_uuid(), 'admin.tenants.create', 'Create tenants', 'admin', true, NOW()),
        (gen_random_uuid(), 'admin.tenants.edit', 'Edit tenants', 'admin', true, NOW()),
        (gen_random_uuid(), 'admin.tenants.delete', 'Delete tenants', 'admin', true, NOW())
    """)


def downgrade():
    """Drop RBAC tables."""
    op.drop_index('ix_role_hierarchy_child', table_name='role_hierarchy')
    op.drop_index('ix_role_hierarchy_parent', table_name='role_hierarchy')
    op.drop_index('ix_resource_permissions_resource', table_name='resource_permissions')
    
    op.drop_table('role_hierarchy')
    op.drop_table('resource_permissions')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
