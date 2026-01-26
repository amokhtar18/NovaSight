-- =========================================
-- NovaSight Tenant Schema Template
-- =========================================
-- This file contains the schema template for tenant-specific tables.
-- Used by the create_tenant_schema() function.

-- =========================================
-- DATA CONNECTIONS
-- =========================================
-- Stores encrypted connection credentials for external databases

CREATE TABLE IF NOT EXISTS {schema}.data_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    db_type VARCHAR(50) NOT NULL CHECK (db_type IN ('postgresql', 'mysql', 'sqlserver', 'oracle', 'snowflake', 'bigquery', 'redshift', 's3', 'gcs')),
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    database VARCHAR(255) NOT NULL,
    schema_name VARCHAR(255),
    username VARCHAR(255) NOT NULL,
    password_encrypted TEXT NOT NULL,
    ssl_mode VARCHAR(50) CHECK (ssl_mode IN ('disable', 'require', 'verify-ca', 'verify-full')),
    ssl_cert TEXT,
    extra_params JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'error')),
    last_tested_at TIMESTAMP WITH TIME ZONE,
    last_test_result JSONB,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_{schema}_connections_status ON {schema}.data_connections(status);

-- =========================================
-- INGESTION JOBS
-- =========================================
-- Configures Spark ingestion jobs for data extraction

CREATE TABLE IF NOT EXISTS {schema}.ingestion_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    connection_id UUID NOT NULL REFERENCES {schema}.data_connections(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    source_type VARCHAR(50) NOT NULL CHECK (source_type IN ('table', 'query', 'file')),
    source_config JSONB NOT NULL,
    destination_table VARCHAR(255) NOT NULL,
    load_strategy VARCHAR(50) NOT NULL DEFAULT 'full' CHECK (load_strategy IN ('full', 'incremental', 'append')),
    incremental_column VARCHAR(255),
    partitioning JSONB DEFAULT '{}',
    schedule_cron VARCHAR(100),
    spark_config JSONB DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'error')),
    last_run_at TIMESTAMP WITH TIME ZONE,
    last_run_status VARCHAR(50),
    last_run_rows INTEGER,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_{schema}_ingestion_connection ON {schema}.ingestion_jobs(connection_id);
CREATE INDEX idx_{schema}_ingestion_status ON {schema}.ingestion_jobs(status);

-- =========================================
-- DAG CONFIGURATIONS
-- =========================================
-- Stores Airflow DAG definitions

CREATE TABLE IF NOT EXISTS {schema}.dag_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dag_id VARCHAR(64) NOT NULL UNIQUE CHECK (dag_id ~ '^[a-z][a-z0-9_]*$'),
    description TEXT,
    current_version INTEGER NOT NULL DEFAULT 1,
    schedule_type VARCHAR(50) NOT NULL DEFAULT 'manual' CHECK (schedule_type IN ('manual', 'cron', 'preset')),
    schedule_cron VARCHAR(100),
    schedule_preset VARCHAR(50) CHECK (schedule_preset IN ('hourly', 'daily', 'weekly', 'monthly')),
    timezone VARCHAR(50) NOT NULL DEFAULT 'UTC',
    start_date TIMESTAMP WITH TIME ZONE,
    catchup BOOLEAN NOT NULL DEFAULT FALSE,
    max_active_runs INTEGER NOT NULL DEFAULT 1 CHECK (max_active_runs BETWEEN 1 AND 10),
    default_retries INTEGER NOT NULL DEFAULT 1 CHECK (default_retries BETWEEN 0 AND 5),
    default_retry_delay_minutes INTEGER NOT NULL DEFAULT 5 CHECK (default_retry_delay_minutes BETWEEN 1 AND 60),
    notification_emails TEXT[] NOT NULL DEFAULT '{}',
    email_on_failure BOOLEAN NOT NULL DEFAULT TRUE,
    email_on_success BOOLEAN NOT NULL DEFAULT FALSE,
    tags TEXT[] NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'paused', 'archived')),
    deployed_at TIMESTAMP WITH TIME ZONE,
    deployed_version INTEGER,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_{schema}_dags_status ON {schema}.dag_configs(status);

-- =========================================
-- DAG VERSIONS
-- =========================================
-- Version history for DAG configurations

CREATE TABLE IF NOT EXISTS {schema}.dag_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dag_config_id UUID NOT NULL REFERENCES {schema}.dag_configs(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    config_snapshot JSONB NOT NULL,
    dag_file_content TEXT,
    change_description TEXT,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dag_version UNIQUE (dag_config_id, version)
);

CREATE INDEX idx_{schema}_dag_versions ON {schema}.dag_versions(dag_config_id);

-- =========================================
-- TASK CONFIGURATIONS
-- =========================================
-- Individual tasks within DAGs

CREATE TABLE IF NOT EXISTS {schema}.task_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dag_config_id UUID NOT NULL REFERENCES {schema}.dag_configs(id) ON DELETE CASCADE,
    task_id VARCHAR(64) NOT NULL CHECK (task_id ~ '^[a-z][a-z0-9_]*$'),
    task_type VARCHAR(50) NOT NULL CHECK (task_type IN ('spark_submit', 'dbt_run', 'dbt_test', 'sql_query', 'email', 'http_sensor', 'time_sensor', 'python')),
    config JSONB NOT NULL DEFAULT '{}',
    timeout_minutes INTEGER NOT NULL DEFAULT 60 CHECK (timeout_minutes BETWEEN 1 AND 1440),
    retries INTEGER NOT NULL DEFAULT 1 CHECK (retries BETWEEN 0 AND 5),
    retry_delay_minutes INTEGER NOT NULL DEFAULT 5 CHECK (retry_delay_minutes BETWEEN 1 AND 60),
    trigger_rule VARCHAR(50) NOT NULL DEFAULT 'all_success' CHECK (trigger_rule IN ('all_success', 'all_failed', 'all_done', 'one_success', 'one_failed', 'none_failed', 'none_skipped')),
    depends_on TEXT[] NOT NULL DEFAULT '{}',
    position_x INTEGER NOT NULL DEFAULT 0,
    position_y INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT uq_dag_task UNIQUE (dag_config_id, task_id)
);

CREATE INDEX idx_{schema}_tasks_dag ON {schema}.task_configs(dag_config_id);

-- =========================================
-- DBT MODELS
-- =========================================
-- Stores dbt model definitions

CREATE TABLE IF NOT EXISTS {schema}.dbt_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE CHECK (name ~ '^[a-z][a-z0-9_]*$'),
    description TEXT,
    model_type VARCHAR(50) NOT NULL DEFAULT 'transform' CHECK (model_type IN ('staging', 'intermediate', 'mart', 'transform')),
    sql_content TEXT NOT NULL,
    materialization VARCHAR(50) NOT NULL DEFAULT 'view' CHECK (materialization IN ('view', 'table', 'incremental', 'ephemeral')),
    tags TEXT[] NOT NULL DEFAULT '{}',
    depends_on TEXT[] NOT NULL DEFAULT '{}',
    columns JSONB NOT NULL DEFAULT '[]',
    tests JSONB NOT NULL DEFAULT '[]',
    status VARCHAR(50) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'deprecated')),
    last_run_at TIMESTAMP WITH TIME ZONE,
    last_run_status VARCHAR(50),
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_{schema}_models_type ON {schema}.dbt_models(model_type);
CREATE INDEX idx_{schema}_models_status ON {schema}.dbt_models(status);

-- =========================================
-- DBT MODEL VERSIONS
-- =========================================
-- Version history for dbt models

CREATE TABLE IF NOT EXISTS {schema}.dbt_model_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_id UUID NOT NULL REFERENCES {schema}.dbt_models(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    sql_content TEXT NOT NULL,
    config_snapshot JSONB NOT NULL,
    change_description TEXT,
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_model_version UNIQUE (model_id, version)
);

CREATE INDEX idx_{schema}_model_versions ON {schema}.dbt_model_versions(model_id);

-- =========================================
-- DASHBOARDS
-- =========================================
-- Dashboard metadata and configuration

CREATE TABLE IF NOT EXISTS {schema}.dashboards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    layout JSONB NOT NULL DEFAULT '{"columns": 12, "rows": []}',
    filters JSONB NOT NULL DEFAULT '[]',
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMP WITH TIME ZONE,
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_{schema}_dashboards_published ON {schema}.dashboards(is_published);

-- =========================================
-- WIDGETS
-- =========================================
-- Dashboard widgets/visualizations

CREATE TABLE IF NOT EXISTS {schema}.widgets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dashboard_id UUID NOT NULL REFERENCES {schema}.dashboards(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    widget_type VARCHAR(50) NOT NULL CHECK (widget_type IN ('chart', 'table', 'metric', 'text', 'filter')),
    config JSONB NOT NULL DEFAULT '{}',
    data_source JSONB NOT NULL,
    position JSONB NOT NULL DEFAULT '{"x": 0, "y": 0, "w": 6, "h": 4}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_{schema}_widgets_dashboard ON {schema}.widgets(dashboard_id);

-- =========================================
-- SAVED QUERIES
-- =========================================
-- User-saved SQL queries

CREATE TABLE IF NOT EXISTS {schema}.saved_queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    sql_content TEXT NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    tags TEXT[] NOT NULL DEFAULT '{}',
    created_by UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_{schema}_queries_creator ON {schema}.saved_queries(created_by);
