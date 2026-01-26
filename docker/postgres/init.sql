-- =========================================
-- NovaSight PostgreSQL Initialization
-- =========================================
-- This script creates the multi-tenant database structure

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =========================================
-- SHARED TABLES (public schema)
-- =========================================

-- Tenants table - core multi-tenancy
CREATE TABLE IF NOT EXISTS public.tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    plan VARCHAR(50) NOT NULL DEFAULT 'starter',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tenants_slug ON public.tenants(slug);
CREATE INDEX IF NOT EXISTS idx_tenants_status ON public.tenants(status);

-- Roles table - system and tenant roles
CREATE TABLE IF NOT EXISTS public.roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    permissions JSONB NOT NULL DEFAULT '{}',
    is_system BOOLEAN DEFAULT FALSE,
    tenant_id UUID REFERENCES public.tenants(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_role_name_tenant UNIQUE (name, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_roles_name ON public.roles(name);
CREATE INDEX IF NOT EXISTS idx_roles_tenant ON public.roles(tenant_id);

-- Users table - all tenant users
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
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_tenant_user_email UNIQUE (tenant_id, email)
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON public.users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON public.users(status);

-- User-Roles junction table
CREATE TABLE IF NOT EXISTS public.user_roles (
    user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    role_id UUID NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    assigned_by UUID REFERENCES public.users(id),
    PRIMARY KEY (user_id, role_id)
);

-- Platform admins (super admins)
CREATE TABLE IF NOT EXISTS public.platform_admins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Audit logs for compliance
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

CREATE INDEX IF NOT EXISTS idx_audit_tenant ON public.audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_user ON public.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON public.audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON public.audit_logs(created_at DESC);

-- =========================================
-- TENANT SCHEMA CREATION FUNCTION
-- =========================================

CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_slug TEXT)
RETURNS VOID AS $$
DECLARE
    schema_name TEXT;
BEGIN
    schema_name := 'tenant_' || tenant_slug;
    
    -- Create the schema
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', schema_name);
    
    -- Create tenant-specific data connections table
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.data_connections (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL UNIQUE,
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
            extra_params JSONB NOT NULL DEFAULT ''{}'',
            status VARCHAR(50) NOT NULL DEFAULT ''active'',
            last_tested_at TIMESTAMP WITH TIME ZONE,
            last_test_result JSONB,
            created_by UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )', schema_name);
    
    -- Create tenant-specific ingestion jobs table
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.ingestion_jobs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            connection_id UUID NOT NULL,
            name VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            source_type VARCHAR(50) NOT NULL,
            source_config JSONB NOT NULL,
            destination_table VARCHAR(255) NOT NULL,
            load_strategy VARCHAR(50) NOT NULL DEFAULT ''full'',
            incremental_column VARCHAR(255),
            schedule_cron VARCHAR(100),
            status VARCHAR(50) NOT NULL DEFAULT ''active'',
            last_run_at TIMESTAMP WITH TIME ZONE,
            last_run_status VARCHAR(50),
            created_by UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )', schema_name);
    
    -- Create tenant-specific DAG configs table
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.dag_configs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            dag_id VARCHAR(64) NOT NULL UNIQUE,
            description TEXT,
            current_version INTEGER NOT NULL DEFAULT 1,
            schedule_type VARCHAR(50) NOT NULL DEFAULT ''manual'',
            schedule_cron VARCHAR(100),
            schedule_preset VARCHAR(50),
            timezone VARCHAR(50) NOT NULL DEFAULT ''UTC'',
            start_date TIMESTAMP WITH TIME ZONE,
            catchup BOOLEAN NOT NULL DEFAULT FALSE,
            max_active_runs INTEGER NOT NULL DEFAULT 1,
            default_retries INTEGER NOT NULL DEFAULT 1,
            default_retry_delay_minutes INTEGER NOT NULL DEFAULT 5,
            notification_emails TEXT[] NOT NULL DEFAULT ''{}'',
            email_on_failure BOOLEAN NOT NULL DEFAULT TRUE,
            email_on_success BOOLEAN NOT NULL DEFAULT FALSE,
            tags TEXT[] NOT NULL DEFAULT ''{}'',
            status VARCHAR(50) NOT NULL DEFAULT ''draft'',
            deployed_at TIMESTAMP WITH TIME ZONE,
            deployed_version INTEGER,
            created_by UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )', schema_name);
    
    -- Create tenant-specific task configs table
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.task_configs (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            dag_config_id UUID NOT NULL,
            task_id VARCHAR(64) NOT NULL,
            task_type VARCHAR(50) NOT NULL,
            config JSONB NOT NULL DEFAULT ''{}'',
            timeout_minutes INTEGER NOT NULL DEFAULT 60,
            retries INTEGER NOT NULL DEFAULT 1,
            retry_delay_minutes INTEGER NOT NULL DEFAULT 5,
            trigger_rule VARCHAR(50) NOT NULL DEFAULT ''all_success'',
            depends_on TEXT[] NOT NULL DEFAULT ''{}'',
            position_x INTEGER NOT NULL DEFAULT 0,
            position_y INTEGER NOT NULL DEFAULT 0,
            CONSTRAINT uq_dag_task UNIQUE (dag_config_id, task_id)
        )', schema_name);
    
    -- Create tenant-specific dbt models table
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.dbt_models (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            name VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            model_type VARCHAR(50) NOT NULL DEFAULT ''transform'',
            sql_content TEXT NOT NULL,
            materialization VARCHAR(50) NOT NULL DEFAULT ''view'',
            tags TEXT[] NOT NULL DEFAULT ''{}'',
            depends_on TEXT[] NOT NULL DEFAULT ''{}'',
            columns JSONB NOT NULL DEFAULT ''[]'',
            tests JSONB NOT NULL DEFAULT ''[]'',
            status VARCHAR(50) NOT NULL DEFAULT ''draft'',
            last_run_at TIMESTAMP WITH TIME ZONE,
            last_run_status VARCHAR(50),
            created_by UUID NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )', schema_name);
    
    RAISE NOTICE 'Created tenant schema: %', schema_name;
END;
$$ LANGUAGE plpgsql;

-- =========================================
-- DROP TENANT SCHEMA FUNCTION
-- =========================================

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

-- =========================================
-- UPDATED_AT TRIGGER FUNCTION
-- =========================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON public.tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at
    BEFORE UPDATE ON public.roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================
-- DEFAULT SYSTEM ROLES
-- =========================================

INSERT INTO public.roles (name, display_name, description, is_system, permissions)
VALUES
    ('super_admin', 'Super Admin', 'Platform-level administrator with full access', TRUE, 
     '{"platform": true, "tenants": "all", "users": "all"}'),
    ('tenant_admin', 'Tenant Admin', 'Tenant administrator with full tenant access', TRUE, 
     '{"tenant": "all", "users": "all", "connections": "all", "dags": "all", "models": "all", "dashboards": "all"}'),
    ('data_engineer', 'Data Engineer', 'Can manage data connections, ingestion, and DAGs', TRUE, 
     '{"connections": "all", "dags": "all", "ingestion": "all", "models": "read"}'),
    ('bi_developer', 'BI Developer', 'Can create and manage dbt models and dashboards', TRUE, 
     '{"models": "all", "dashboards": "all", "connections": "read", "query": true}'),
    ('analyst', 'Analyst', 'Can query data and create visualizations', TRUE, 
     '{"query": true, "visualizations": "all", "dashboards": "read"}'),
    ('viewer', 'Viewer', 'Read-only access to dashboards', TRUE, 
     '{"dashboards": "read"}')
ON CONFLICT DO NOTHING;

-- =========================================
-- DEFAULT DEV TENANT AND USER
-- =========================================

-- Create default development tenant
INSERT INTO public.tenants (name, slug, plan, status, settings)
VALUES (
    'Development Tenant', 
    'dev', 
    'enterprise', 
    'active', 
    '{"theme": "light", "timezone": "UTC", "features": {"nlq": true, "spark": true}}'
)
ON CONFLICT (slug) DO NOTHING;

-- Create dev tenant schema
SELECT create_tenant_schema('dev');

-- Create default admin user (password: admin123)
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

-- Assign tenant_admin role to default user
INSERT INTO public.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM public.users u
CROSS JOIN public.roles r
WHERE u.email = 'admin@novasight.dev'
  AND r.name = 'tenant_admin'
ON CONFLICT DO NOTHING;

DO $$ BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'NovaSight PostgreSQL initialized';
    RAISE NOTICE 'Default tenant: dev';
    RAISE NOTICE 'Default user: admin@novasight.dev';
    RAISE NOTICE 'Default password: admin123';
    RAISE NOTICE '========================================';
END $$;
