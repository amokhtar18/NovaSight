-- NovaSight PostgreSQL Initialization
-- ====================================
-- This script runs on first container start

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create platform-level tables in public schema

-- Tenants table
CREATE TABLE IF NOT EXISTS public.tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'basic',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tenants_slug ON public.tenants(slug);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON public.tenants(status);

-- Platform admins table
CREATE TABLE IF NOT EXISTS public.platform_admins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Platform audit log
CREATE TABLE IF NOT EXISTS public.platform_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_id UUID REFERENCES public.platform_admins(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_platform_audit_created ON public.platform_audit_log(created_at DESC);

-- Roles table (shared across tenants)
CREATE TABLE IF NOT EXISTS public.roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '{}',
    is_system BOOLEAN DEFAULT FALSE,
    tenant_id UUID REFERENCES public.tenants(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_roles_name ON public.roles(name);

-- Users table (cross-tenant, filtered by tenant_id)
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    sso_provider VARCHAR(50),
    sso_subject VARCHAR(255),
    preferences JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_tenant_user_email UNIQUE (tenant_id, email)
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON public.users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON public.users(status);

-- User roles junction table
CREATE TABLE IF NOT EXISTS public.user_roles (
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES public.users(id),
    PRIMARY KEY (user_id, role_id)
);

-- Data connections table
CREATE TABLE IF NOT EXISTS public.data_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    db_type VARCHAR(50) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    database VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    username VARCHAR(255) NOT NULL,
    password_encrypted TEXT NOT NULL,
    ssl_mode VARCHAR(50),
    ssl_cert TEXT,
    extra_params JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    last_tested_at TIMESTAMP WITH TIME ZONE,
    last_test_result JSONB,
    created_by UUID NOT NULL REFERENCES public.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tenant_connection_name UNIQUE (tenant_id, name)
);

CREATE INDEX IF NOT EXISTS idx_connections_tenant ON public.data_connections(tenant_id);

-- DAG configurations table
CREATE TABLE IF NOT EXISTS public.dag_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    dag_id VARCHAR(64) NOT NULL,
    description TEXT,
    current_version INTEGER NOT NULL DEFAULT 1,
    schedule_type VARCHAR(50) NOT NULL DEFAULT 'manual',
    schedule_cron VARCHAR(100),
    schedule_preset VARCHAR(50),
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    start_date TIMESTAMP WITH TIME ZONE,
    catchup BOOLEAN NOT NULL DEFAULT FALSE,
    max_active_runs INTEGER NOT NULL DEFAULT 1,
    default_retries INTEGER NOT NULL DEFAULT 1,
    default_retry_delay_minutes INTEGER NOT NULL DEFAULT 5,
    notification_emails TEXT[] NOT NULL DEFAULT '{}',
    email_on_failure BOOLEAN NOT NULL DEFAULT TRUE,
    email_on_success BOOLEAN NOT NULL DEFAULT FALSE,
    tags TEXT[] NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    deployed_at TIMESTAMP WITH TIME ZONE,
    deployed_version INTEGER,
    created_by UUID NOT NULL REFERENCES public.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tenant_dag_id UNIQUE (tenant_id, dag_id)
);

CREATE INDEX IF NOT EXISTS idx_dag_configs_tenant ON public.dag_configs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_dag_configs_status ON public.dag_configs(status);

-- DAG versions table
CREATE TABLE IF NOT EXISTS public.dag_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dag_config_id UUID NOT NULL REFERENCES public.dag_configs(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    config_snapshot JSONB NOT NULL,
    dag_file_content TEXT,
    change_description TEXT,
    created_by UUID NOT NULL REFERENCES public.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dag_version UNIQUE (dag_config_id, version)
);

CREATE INDEX IF NOT EXISTS idx_dag_versions_config ON public.dag_versions(dag_config_id);

-- Task configurations table
CREATE TABLE IF NOT EXISTS public.task_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dag_config_id UUID NOT NULL REFERENCES public.dag_configs(id) ON DELETE CASCADE,
    task_id VARCHAR(64) NOT NULL,
    task_type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    timeout_minutes INTEGER NOT NULL DEFAULT 60,
    retries INTEGER NOT NULL DEFAULT 1,
    retry_delay_minutes INTEGER NOT NULL DEFAULT 5,
    trigger_rule VARCHAR(50) NOT NULL DEFAULT 'all_success',
    depends_on TEXT[] NOT NULL DEFAULT '{}',
    position_x INTEGER NOT NULL DEFAULT 0,
    position_y INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_dag_task_id UNIQUE (dag_config_id, task_id)
);

CREATE INDEX IF NOT EXISTS idx_task_configs_dag ON public.task_configs(dag_config_id);

-- Audit logs table
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID REFERENCES public.tenants(id),
    user_id UUID REFERENCES public.users(id),
    user_email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    resource_name VARCHAR(255),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(100),
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant ON public.audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON public.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON public.audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON public.audit_logs(created_at DESC);

-- Insert default system roles
INSERT INTO public.roles (name, display_name, description, is_system, permissions)
VALUES
    ('super_admin', 'Super Admin', 'Platform-level administrator with full access', TRUE, '{"all": true}'),
    ('tenant_admin', 'Tenant Admin', 'Tenant administrator with full tenant access', TRUE, '{"tenant": "all"}'),
    ('data_engineer', 'Data Engineer', 'Can manage data connections, ingestion, and DAGs', TRUE, '{"connections": "all", "dags": "all", "ingestion": "all"}'),
    ('bi_developer', 'BI Developer', 'Can create and manage dbt models and dashboards', TRUE, '{"models": "all", "dashboards": "all"}'),
    ('analyst', 'Analyst', 'Can query data and create visualizations', TRUE, '{"query": true, "visualizations": "all"}'),
    ('viewer', 'Viewer', 'Read-only access to dashboards', TRUE, '{"dashboards": "read"}')
ON CONFLICT (name) DO NOTHING;

-- Create a default development tenant
INSERT INTO public.tenants (name, slug, plan, status, settings)
VALUES ('Development Tenant', 'dev', 'enterprise', 'active', '{"theme": "light", "timezone": "UTC"}')
ON CONFLICT (slug) DO NOTHING;

-- Create a default admin user for development (password: admin123)
INSERT INTO public.users (tenant_id, email, password_hash, name, status)
SELECT 
    t.id,
    'admin@novasight.dev',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.UTq/8ACyRpKoOG',
    'Admin User',
    'active'
FROM public.tenants t
WHERE t.slug = 'dev'
ON CONFLICT DO NOTHING;

-- Assign admin role to default user
INSERT INTO public.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM public.users u, public.roles r
WHERE u.email = 'admin@novasight.dev'
  AND r.name = 'tenant_admin'
ON CONFLICT DO NOTHING;

RAISE NOTICE 'NovaSight database initialized successfully';
