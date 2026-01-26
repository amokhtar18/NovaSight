-- =========================================
-- NovaSight ClickHouse Initialization
-- =========================================
-- Sets up the data warehouse structure

-- =========================================
-- SYSTEM DATABASE
-- =========================================
-- Platform-level tables for monitoring and metadata

CREATE DATABASE IF NOT EXISTS novasight_system;

-- Query execution history for audit
CREATE TABLE IF NOT EXISTS novasight_system.query_log (
    event_date Date DEFAULT toDate(event_time),
    event_time DateTime DEFAULT now(),
    tenant_id String,
    user_id String,
    query_id String,
    query String,
    query_kind String,
    databases Array(String),
    tables Array(String),
    columns Array(String),
    read_rows UInt64,
    read_bytes UInt64,
    result_rows UInt64,
    result_bytes UInt64,
    memory_usage UInt64,
    query_duration_ms UInt64,
    exception String DEFAULT '',
    stack_trace String DEFAULT ''
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (tenant_id, event_time)
TTL event_date + INTERVAL 90 DAY;

-- Data lineage tracking
CREATE TABLE IF NOT EXISTS novasight_system.data_lineage (
    id UUID DEFAULT generateUUIDv4(),
    event_date Date DEFAULT toDate(event_time),
    event_time DateTime DEFAULT now(),
    tenant_id String,
    source_database String,
    source_table String,
    destination_database String,
    destination_table String,
    job_id String,
    rows_affected UInt64,
    operation String,
    metadata String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (tenant_id, event_time)
TTL event_date + INTERVAL 365 DAY;

-- Table statistics for profiling
CREATE TABLE IF NOT EXISTS novasight_system.table_stats (
    id UUID DEFAULT generateUUIDv4(),
    collected_at DateTime DEFAULT now(),
    tenant_id String,
    database_name String,
    table_name String,
    row_count UInt64,
    data_size_bytes UInt64,
    columns_count UInt32,
    partition_count UInt32,
    last_modified DateTime
) ENGINE = ReplacingMergeTree(collected_at)
ORDER BY (tenant_id, database_name, table_name);

-- =========================================
-- TENANT DATABASE CREATION FUNCTION
-- =========================================
-- Note: ClickHouse doesn't support stored procedures
-- This SQL creates a template database structure

-- Create development tenant database
CREATE DATABASE IF NOT EXISTS tenant_dev;

-- =========================================
-- STANDARD TABLES FOR TENANT DATABASES
-- =========================================
-- These tables are created in each tenant database

-- Raw ingested data (staging)
CREATE TABLE IF NOT EXISTS tenant_dev._staging_template (
    _ingested_at DateTime DEFAULT now(),
    _source_file String,
    _batch_id String,
    _row_number UInt64,
    data String
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(_ingested_at)
ORDER BY (_ingested_at, _row_number)
TTL _ingested_at + INTERVAL 7 DAY;

-- Sample dimension table template
CREATE TABLE IF NOT EXISTS tenant_dev._dim_template (
    id UUID DEFAULT generateUUIDv4(),
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now(),
    is_current UInt8 DEFAULT 1,
    valid_from DateTime DEFAULT now(),
    valid_to DateTime DEFAULT toDateTime('2099-12-31 23:59:59')
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY id;

-- Sample fact table template
CREATE TABLE IF NOT EXISTS tenant_dev._fact_template (
    id UUID DEFAULT generateUUIDv4(),
    event_date Date DEFAULT toDate(event_time),
    event_time DateTime DEFAULT now(),
    -- Dimension keys would go here
    -- Measures would go here
    _loaded_at DateTime DEFAULT now()
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, event_time);

-- =========================================
-- MATERIALIZED VIEWS FOR COMMON AGGREGATIONS
-- =========================================

-- Daily aggregation template
CREATE TABLE IF NOT EXISTS tenant_dev._daily_agg_template (
    date Date,
    dimension_key String,
    count UInt64,
    sum_value Float64,
    min_value Float64,
    max_value Float64,
    avg_value Float64
) ENGINE = SummingMergeTree()
ORDER BY (date, dimension_key);

-- =========================================
-- UTILITY FUNCTIONS
-- =========================================

-- Create a new tenant database with standard structure
-- Usage: Execute these statements with tenant_id replaced

/*
-- To create a new tenant database, run:

CREATE DATABASE IF NOT EXISTS tenant_{tenant_slug};

CREATE TABLE IF NOT EXISTS tenant_{tenant_slug}.raw_data (
    _ingested_at DateTime DEFAULT now(),
    _source String,
    _batch_id String,
    data String
) ENGINE = MergeTree()
PARTITION BY toYYYYMMDD(_ingested_at)
ORDER BY _ingested_at
TTL _ingested_at + INTERVAL 30 DAY;

GRANT SELECT, INSERT, ALTER, DROP ON tenant_{tenant_slug}.* TO novasight;
*/

-- =========================================
-- DEVELOPMENT DATA
-- =========================================

-- Sample data for testing the dev tenant
CREATE TABLE IF NOT EXISTS tenant_dev.sample_events (
    id UUID DEFAULT generateUUIDv4(),
    event_date Date DEFAULT toDate(event_time),
    event_time DateTime DEFAULT now(),
    event_type String,
    user_id String,
    properties String,
    value Float64
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, event_time, event_type);

-- Insert sample data
INSERT INTO tenant_dev.sample_events (event_type, user_id, properties, value)
SELECT 
    arrayElement(['page_view', 'click', 'purchase', 'signup'], rand() % 4 + 1),
    toString(rand() % 1000),
    '{}',
    rand() % 1000 / 10.0
FROM numbers(1000);

-- Sample customers dimension
CREATE TABLE IF NOT EXISTS tenant_dev.dim_customers (
    id UUID DEFAULT generateUUIDv4(),
    customer_id String,
    name String,
    email String,
    segment String,
    created_at DateTime DEFAULT now(),
    updated_at DateTime DEFAULT now()
) ENGINE = ReplacingMergeTree(updated_at)
ORDER BY customer_id;

-- Insert sample customers
INSERT INTO tenant_dev.dim_customers (customer_id, name, email, segment)
SELECT 
    toString(number),
    concat('Customer ', toString(number)),
    concat('customer', toString(number), '@example.com'),
    arrayElement(['Enterprise', 'SMB', 'Startup', 'Individual'], rand() % 4 + 1)
FROM numbers(100);

SELECT '========================================' AS message;
SELECT 'NovaSight ClickHouse initialized' AS message;
SELECT 'System database: novasight_system' AS message;
SELECT 'Dev tenant database: tenant_dev' AS message;
SELECT '========================================' AS message;
