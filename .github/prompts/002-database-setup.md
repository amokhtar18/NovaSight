# 002 - Database Setup

## Metadata

```yaml
prompt_id: "002"
phase: 1
agent: "@infrastructure"
model: "sonnet 4.5"
priority: P0
estimated_effort: "1 day"
dependencies: ["001"]
```

## Objective

Configure PostgreSQL for multi-tenant schema isolation and ClickHouse for tenant-specific databases.

## Task Description

### PostgreSQL Configuration

1. Create base schema structure:
   - `public` schema for shared tables (tenants, users, roles, permissions)
   - Template for tenant schemas (`tenant_{slug}`)

2. Create initial tables in public schema:
   ```sql
   -- Tenants table
   CREATE TABLE public.tenants (
       id UUID PRIMARY KEY,
       name VARCHAR(100) NOT NULL,
       slug VARCHAR(50) UNIQUE NOT NULL,
       plan VARCHAR(20) DEFAULT 'starter',
       settings JSONB DEFAULT '{}',
       is_active BOOLEAN DEFAULT true,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   
   -- Users table
   CREATE TABLE public.users (
       id UUID PRIMARY KEY,
       tenant_id UUID REFERENCES tenants(id),
       email VARCHAR(255) NOT NULL,
       password_hash VARCHAR(255) NOT NULL,
       name VARCHAR(100),
       is_active BOOLEAN DEFAULT true,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

3. Create function for tenant schema creation

### ClickHouse Configuration

1. Configure users and access control
2. Create function for tenant database creation
3. Set up default table engines (MergeTree)

## Requirements

### PostgreSQL Initialization Script

```sql
-- init-postgres.sql
-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tenants table
-- Create users table
-- Create roles table
-- Create permissions table
-- Create user_roles junction table

-- Function to create tenant schema
CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_slug TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS tenant_%s', tenant_slug);
    -- Create tenant-specific tables
END;
$$ LANGUAGE plpgsql;
```

### ClickHouse Initialization

```sql
-- Create default user with limited permissions
-- Set up row-level security policies
```

## Expected Output

```
novasight/
├── docker/
│   ├── postgres/
│   │   ├── init.sql
│   │   └── tenant-schema.sql
│   └── clickhouse/
│       ├── users.xml
│       └── init.sql
└── backend/
    └── migrations/
        └── versions/
            └── 001_initial_schema.py
```

## Acceptance Criteria

- [ ] PostgreSQL starts with initial schema
- [ ] Tenant schema creation function works
- [ ] ClickHouse accepts connections
- [ ] Alembic migrations configured
- [ ] Test tenant can be created

## Reference Documents

- [Multi-Tenant DB Skill](../skills/multi-tenant-db/SKILL.md)
- [Architecture Decisions - ADR-003](../../docs/requirements/Architecture_Decisions.md)
