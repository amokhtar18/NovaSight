"""Initial schema with multi-tenant support

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-01-27
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create initial NovaSight schema.
    
    This migration creates:
    - Core multi-tenant tables (tenants, users, roles)
    - Data connection management
    - DAG configuration storage
    - Audit logging
    - Helper functions for tenant schema management
    """
    
    # Create UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    
    # =========================================
    # TENANTS TABLE
    # =========================================
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('plan', sa.String(50), server_default='starter', nullable=False),
        sa.Column('status', sa.String(50), server_default='active', nullable=False),
        sa.Column('settings', postgresql.JSONB, server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        schema='public'
    )
    op.create_index('idx_tenants_slug', 'tenants', ['slug'], schema='public')
    op.create_index('idx_tenants_status', 'tenants', ['status'], schema='public')
    
    # =========================================
    # ROLES TABLE
    # =========================================
    op.create_table(
        'roles',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('permissions', postgresql.JSONB, server_default='{}', nullable=False),
        sa.Column('is_system', sa.Boolean, server_default='false'),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.tenants.id', ondelete='CASCADE')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('name', 'tenant_id', name='uq_role_name_tenant'),
        schema='public'
    )
    op.create_index('idx_roles_name', 'roles', ['name'], schema='public')
    op.create_index('idx_roles_tenant', 'roles', ['tenant_id'], schema='public')
    
    # =========================================
    # USERS TABLE
    # =========================================
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('status', sa.String(50), server_default='active', nullable=False),
        sa.Column('sso_provider', sa.String(50)),
        sa.Column('sso_subject', sa.String(255)),
        sa.Column('preferences', postgresql.JSONB, server_default='{}', nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('tenant_id', 'email', name='uq_tenant_user_email'),
        schema='public'
    )
    op.create_index('idx_users_tenant', 'users', ['tenant_id'], schema='public')
    op.create_index('idx_users_email', 'users', ['email'], schema='public')
    op.create_index('idx_users_status', 'users', ['status'], schema='public')
    
    # =========================================
    # USER_ROLES JUNCTION TABLE
    # =========================================
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.roles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('assigned_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.users.id')),
        schema='public'
    )
    
    # =========================================
    # PLATFORM_ADMINS TABLE
    # =========================================
    op.create_table(
        'platform_admins',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('status', sa.String(50), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        schema='public'
    )
    
    # =========================================
    # DATA_CONNECTIONS TABLE
    # =========================================
    op.create_table(
        'data_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('db_type', sa.String(50), nullable=False),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer, nullable=False),
        sa.Column('database', sa.String(255), nullable=False),
        sa.Column('schema_name', sa.String(255)),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('password_encrypted', sa.Text, nullable=False),
        sa.Column('ssl_mode', sa.String(50)),
        sa.Column('ssl_cert', sa.Text),
        sa.Column('extra_params', postgresql.JSONB, server_default='{}', nullable=False),
        sa.Column('status', sa.String(50), server_default='active', nullable=False),
        sa.Column('last_tested_at', sa.DateTime(timezone=True)),
        sa.Column('last_test_result', postgresql.JSONB),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_tenant_connection_name'),
        schema='public'
    )
    op.create_index('idx_connections_tenant', 'data_connections', ['tenant_id'], schema='public')
    op.create_index('idx_connections_status', 'data_connections', ['status'], schema='public')
    
    # =========================================
    # DAG_CONFIGS TABLE
    # =========================================
    op.create_table(
        'dag_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dag_id', sa.String(64), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('current_version', sa.Integer, server_default='1', nullable=False),
        sa.Column('schedule_type', sa.String(50), server_default='manual', nullable=False),
        sa.Column('schedule_cron', sa.String(100)),
        sa.Column('schedule_preset', sa.String(50)),
        sa.Column('timezone', sa.String(50), server_default='UTC', nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True)),
        sa.Column('catchup', sa.Boolean, server_default='false', nullable=False),
        sa.Column('max_active_runs', sa.Integer, server_default='1', nullable=False),
        sa.Column('default_retries', sa.Integer, server_default='1', nullable=False),
        sa.Column('default_retry_delay_minutes', sa.Integer, server_default='5', nullable=False),
        sa.Column('notification_emails', postgresql.ARRAY(sa.Text), server_default='{}', nullable=False),
        sa.Column('email_on_failure', sa.Boolean, server_default='true', nullable=False),
        sa.Column('email_on_success', sa.Boolean, server_default='false', nullable=False),
        sa.Column('tags', postgresql.ARRAY(sa.Text), server_default='{}', nullable=False),
        sa.Column('status', sa.String(50), server_default='draft', nullable=False),
        sa.Column('deployed_at', sa.DateTime(timezone=True)),
        sa.Column('deployed_version', sa.Integer),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('tenant_id', 'dag_id', name='uq_tenant_dag_id'),
        schema='public'
    )
    op.create_index('idx_dag_configs_tenant', 'dag_configs', ['tenant_id'], schema='public')
    op.create_index('idx_dag_configs_status', 'dag_configs', ['status'], schema='public')
    
    # =========================================
    # DAG_VERSIONS TABLE
    # =========================================
    op.create_table(
        'dag_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('dag_config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.dag_configs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version', sa.Integer, nullable=False),
        sa.Column('config_snapshot', postgresql.JSONB, nullable=False),
        sa.Column('dag_file_content', sa.Text),
        sa.Column('change_description', sa.Text),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.UniqueConstraint('dag_config_id', 'version', name='uq_dag_version'),
        schema='public'
    )
    op.create_index('idx_dag_versions_config', 'dag_versions', ['dag_config_id'], schema='public')
    
    # =========================================
    # TASK_CONFIGS TABLE
    # =========================================
    op.create_table(
        'task_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('dag_config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.dag_configs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('task_id', sa.String(64), nullable=False),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('config', postgresql.JSONB, server_default='{}', nullable=False),
        sa.Column('timeout_minutes', sa.Integer, server_default='60', nullable=False),
        sa.Column('retries', sa.Integer, server_default='1', nullable=False),
        sa.Column('retry_delay_minutes', sa.Integer, server_default='5', nullable=False),
        sa.Column('trigger_rule', sa.String(50), server_default='all_success', nullable=False),
        sa.Column('depends_on', postgresql.ARRAY(sa.Text), server_default='{}', nullable=False),
        sa.Column('position_x', sa.Integer, server_default='0', nullable=False),
        sa.Column('position_y', sa.Integer, server_default='0', nullable=False),
        sa.UniqueConstraint('dag_config_id', 'task_id', name='uq_dag_task_id'),
        schema='public'
    )
    op.create_index('idx_task_configs_dag', 'task_configs', ['dag_config_id'], schema='public')
    
    # =========================================
    # AUDIT_LOGS TABLE
    # =========================================
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), primary_key=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.tenants.id')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('public.users.id')),
        sa.Column('user_email', sa.String(255)),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50)),
        sa.Column('resource_id', sa.String(255)),
        sa.Column('resource_name', sa.String(255)),
        sa.Column('old_values', postgresql.JSONB),
        sa.Column('new_values', postgresql.JSONB),
        sa.Column('ip_address', postgresql.INET),
        sa.Column('user_agent', sa.Text),
        sa.Column('request_id', sa.String(100)),
        sa.Column('success', sa.Boolean, server_default='true', nullable=False),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        schema='public'
    )
    op.create_index('idx_audit_logs_tenant', 'audit_logs', ['tenant_id'], schema='public')
    op.create_index('idx_audit_logs_user', 'audit_logs', ['user_id'], schema='public')
    op.create_index('idx_audit_logs_action', 'audit_logs', ['action'], schema='public')
    op.create_index('idx_audit_logs_created', 'audit_logs', [sa.text('created_at DESC')], schema='public')
    
    # =========================================
    # TENANT SCHEMA CREATION FUNCTION
    # =========================================
    op.execute("""
        CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_slug TEXT)
        RETURNS VOID AS $$
        DECLARE
            schema_name TEXT;
        BEGIN
            schema_name := 'tenant_' || tenant_slug;
            EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', schema_name);
            RAISE NOTICE 'Created tenant schema: %', schema_name;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE OR REPLACE FUNCTION drop_tenant_schema(tenant_slug TEXT)
        RETURNS VOID AS $$
        DECLARE
            schema_name TEXT;
        BEGIN
            schema_name := 'tenant_' || tenant_slug;
            EXECUTE format('DROP SCHEMA IF EXISTS %I CASCADE', schema_name);
            RAISE NOTICE 'Dropped tenant schema: %', schema_name;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # =========================================
    # UPDATED_AT TRIGGER FUNCTION
    # =========================================
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Apply updated_at triggers
    for table in ['tenants', 'users', 'roles', 'data_connections', 'dag_configs']:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
                BEFORE UPDATE ON public.{table}
                FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
    
    # =========================================
    # SEED DATA: System Roles
    # =========================================
    op.execute("""
        INSERT INTO public.roles (name, display_name, description, is_system, permissions)
        VALUES
            ('super_admin', 'Super Admin', 'Platform-level administrator', TRUE, '{"platform": true, "tenants": "all"}'),
            ('tenant_admin', 'Tenant Admin', 'Tenant administrator with full access', TRUE, '{"tenant": "all"}'),
            ('data_engineer', 'Data Engineer', 'Manages data connections and DAGs', TRUE, '{"connections": "all", "dags": "all"}'),
            ('bi_developer', 'BI Developer', 'Creates models and dashboards', TRUE, '{"models": "all", "dashboards": "all"}'),
            ('analyst', 'Analyst', 'Queries data and creates visualizations', TRUE, '{"query": true, "visualizations": "all"}'),
            ('viewer', 'Viewer', 'Read-only dashboard access', TRUE, '{"dashboards": "read"}')
        ON CONFLICT DO NOTHING;
    """)
    
    # =========================================
    # SEED DATA: Development Tenant
    # =========================================
    op.execute("""
        INSERT INTO public.tenants (name, slug, plan, status, settings)
        VALUES ('Development Tenant', 'dev', 'enterprise', 'active', '{"theme": "light", "timezone": "UTC"}')
        ON CONFLICT (slug) DO NOTHING;
    """)
    
    op.execute("SELECT create_tenant_schema('dev')")
    
    # Create default admin user (password: admin123)
    op.execute("""
        INSERT INTO public.users (tenant_id, email, password_hash, name, status)
        SELECT t.id, 'admin@novasight.dev', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.UTq/8ACyRpKoOG', 'Admin User', 'active'
        FROM public.tenants t WHERE t.slug = 'dev'
        ON CONFLICT DO NOTHING;
    """)
    
    op.execute("""
        INSERT INTO public.user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM public.users u, public.roles r
        WHERE u.email = 'admin@novasight.dev' AND r.name = 'tenant_admin'
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    """Drop all NovaSight schema objects."""
    
    # Drop triggers
    for table in ['tenants', 'users', 'roles', 'data_connections', 'dag_configs']:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON public.{table}")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.execute("DROP FUNCTION IF EXISTS drop_tenant_schema(TEXT)")
    op.execute("DROP FUNCTION IF EXISTS create_tenant_schema(TEXT)")
    
    # Drop tenant schemas
    op.execute("SELECT drop_tenant_schema('dev')")
    
    # Drop tables in reverse order
    op.drop_table('audit_logs', schema='public')
    op.drop_table('task_configs', schema='public')
    op.drop_table('dag_versions', schema='public')
    op.drop_table('dag_configs', schema='public')
    op.drop_table('data_connections', schema='public')
    op.drop_table('platform_admins', schema='public')
    op.drop_table('user_roles', schema='public')
    op.drop_table('users', schema='public')
    op.drop_table('roles', schema='public')
    op.drop_table('tenants', schema='public')
    
    # Drop extensions
    op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
