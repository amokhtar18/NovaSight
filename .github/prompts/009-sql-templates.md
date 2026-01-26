# 009 - SQL Templates

## Metadata

```yaml
prompt_id: "009"
phase: 2
agent: "@template-engine"
model: "opus 4.5"
priority: P0
estimated_effort: "2 days"
dependencies: ["008"]
```

## Objective

Create Jinja2 templates for PostgreSQL table creation with multi-tenant support.

## Task Description

Implement SQL templates that generate properly structured PostgreSQL DDL with tenant isolation.

## Requirements

### Create Table Template

```jinja2
{# templates/sql/create_table.sql.j2 #}
{# 
  Parameters:
    - table_name: str - Name of the table
    - columns: List[Column] - Column definitions
    - tenant_aware: bool - Whether to add tenant_id
    - indexes: List[Index] - Index definitions
    - schema: str - Schema name (default: current schema)
#}
{% set schema_prefix = schema ~ '.' if schema else '' %}

CREATE TABLE IF NOT EXISTS {{ schema_prefix }}{{ table_name | sql_safe }} (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
{% if tenant_aware %}
    tenant_id UUID NOT NULL REFERENCES public.tenants(id),
{% endif %}
{% for column in columns %}
    {{ column.name | sql_safe }} {{ column.type }}
    {%- if not column.nullable %} NOT NULL{% endif %}
    {%- if column.default is defined %} DEFAULT {{ column.default }}{% endif %}
    {%- if not loop.last %},{% endif %}

{% endfor %}
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add updated_at trigger
CREATE OR REPLACE TRIGGER update_{{ table_name }}_updated_at
    BEFORE UPDATE ON {{ schema_prefix }}{{ table_name | sql_safe }}
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

{% if tenant_aware %}
-- Tenant index for query performance
CREATE INDEX IF NOT EXISTS idx_{{ table_name }}_tenant_id 
    ON {{ schema_prefix }}{{ table_name | sql_safe }} (tenant_id);

-- Row-level security policy
ALTER TABLE {{ schema_prefix }}{{ table_name | sql_safe }} ENABLE ROW LEVEL SECURITY;

CREATE POLICY {{ table_name }}_tenant_isolation
    ON {{ schema_prefix }}{{ table_name | sql_safe }}
    USING (tenant_id = current_setting('app.tenant_id')::UUID);
{% endif %}

{% for index in indexes %}
CREATE INDEX IF NOT EXISTS idx_{{ table_name }}_{{ index.name }} 
    ON {{ schema_prefix }}{{ table_name | sql_safe }} ({{ index.columns | join(', ') }});
{% endfor %}
```

### Tenant Schema Template

```jinja2
{# templates/sql/tenant_schema.sql.j2 #}
{#
  Parameters:
    - tenant_slug: str - URL-safe tenant identifier
#}
{% set schema_name = 'tenant_' ~ (tenant_slug | sql_safe) %}

-- Create tenant schema
CREATE SCHEMA IF NOT EXISTS {{ schema_name }};

-- Set default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA {{ schema_name }}
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO novasight_app;

-- Create tenant-specific tables (if any)
-- These are tables that store tenant-specific data that doesn't go in ClickHouse
```

### Create Index Template

```jinja2
{# templates/sql/create_index.sql.j2 #}
{#
  Parameters:
    - table_name: str
    - index_name: str
    - columns: List[str]
    - unique: bool
    - schema: str
#}
{% set schema_prefix = schema ~ '.' if schema else '' %}

CREATE {% if unique %}UNIQUE {% endif %}INDEX IF NOT EXISTS {{ index_name | sql_safe }}
    ON {{ schema_prefix }}{{ table_name | sql_safe }} ({{ columns | map('sql_safe') | join(', ') }});
```

### Foreign Key Template

```jinja2
{# templates/sql/add_foreign_key.sql.j2 #}
{#
  Parameters:
    - table_name: str
    - constraint_name: str
    - column: str
    - references_table: str
    - references_column: str
    - on_delete: str (CASCADE, SET NULL, RESTRICT)
#}
ALTER TABLE {{ table_name | sql_safe }}
    ADD CONSTRAINT {{ constraint_name | sql_safe }}
    FOREIGN KEY ({{ column | sql_safe }})
    REFERENCES {{ references_table | sql_safe }} ({{ references_column | sql_safe }})
    ON DELETE {{ on_delete | upper }};
```

## Expected Output

```
backend/templates/sql/
├── create_table.sql.j2
├── tenant_schema.sql.j2
├── create_index.sql.j2
├── add_foreign_key.sql.j2
├── drop_table.sql.j2
└── alter_table_add_column.sql.j2
```

## Acceptance Criteria

- [ ] Templates render valid PostgreSQL SQL
- [ ] Tenant isolation policies applied correctly
- [ ] SQL identifiers properly escaped
- [ ] Indexes created correctly
- [ ] Updated_at trigger works
- [ ] Row-level security policies valid
- [ ] SQL passes PostgreSQL syntax validation

## Reference Documents

- [Template Engine Core](./008-template-engine-core.md)
- [Multi-Tenant DB Skill](../skills/multi-tenant-db/SKILL.md)
