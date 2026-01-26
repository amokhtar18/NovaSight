# 012 - ClickHouse Templates

## Metadata

```yaml
prompt_id: "012"
phase: 2
agent: "@template-engine"
model: "opus 4.5"
priority: P0
estimated_effort: "2 days"
dependencies: ["008"]
```

## Objective

Create Jinja2 templates for ClickHouse table creation optimized for OLAP workloads.

## Task Description

Implement templates for generating ClickHouse DDL with proper MergeTree configurations.

## Requirements

### ClickHouse Table Template

```jinja2
{# templates/clickhouse/create_table.sql.j2 #}
{#
  Parameters:
    - database: str
    - table_name: str
    - columns: List[ColumnDef]
    - engine: str (MergeTree, ReplacingMergeTree, etc.)
    - partition_by: str
    - order_by: List[str]
    - primary_key: Optional[List[str]]
    - settings: Dict[str, Any]
    - ttl: Optional[str]
#}
CREATE TABLE IF NOT EXISTS {{ database }}.{{ table_name | sql_safe }}
(
{% for col in columns %}
    {{ col.name | sql_safe }} {{ col.type }}
    {%- if col.default is defined %} DEFAULT {{ col.default }}{% endif %}
    {%- if col.codec %} CODEC({{ col.codec }}){% endif %}
    {%- if col.comment %} COMMENT '{{ col.comment }}'{% endif %}
    {%- if not loop.last %},{% endif %}

{% endfor %}
)
ENGINE = {{ engine }}
{% if engine == 'ReplacingMergeTree' and ver_column %}
({{ ver_column }})
{% endif %}
{% if partition_by %}
PARTITION BY {{ partition_by }}
{% endif %}
ORDER BY ({{ order_by | join(', ') }})
{% if primary_key %}
PRIMARY KEY ({{ primary_key | join(', ') }})
{% endif %}
{% if ttl %}
TTL {{ ttl }}
{% endif %}
{% if settings %}
SETTINGS
{% for key, value in settings.items() %}
    {{ key }} = {{ value }}{% if not loop.last %},{% endif %}

{% endfor %}
{% endif %}
;
```

### Materialized View Template

```jinja2
{# templates/clickhouse/materialized_view.sql.j2 #}
{#
  Parameters:
    - database: str
    - view_name: str
    - target_table: str
    - source_table: str
    - select_columns: List[str]
    - aggregations: List[AggDef]
    - group_by: List[str]
    - where_clause: Optional[str]
#}
CREATE MATERIALIZED VIEW IF NOT EXISTS {{ database }}.{{ view_name | sql_safe }}
TO {{ database }}.{{ target_table | sql_safe }}
AS SELECT
{% for col in select_columns %}
    {{ col }}{% if not loop.last or aggregations %},{% endif %}

{% endfor %}
{% for agg in aggregations %}
    {{ agg.func }}({{ agg.column }}) AS {{ agg.alias }}{% if not loop.last %},{% endif %}

{% endfor %}
FROM {{ database }}.{{ source_table | sql_safe }}
{% if where_clause %}
WHERE {{ where_clause }}
{% endif %}
{% if group_by %}
GROUP BY {{ group_by | join(', ') }}
{% endif %}
;
```

### Tenant Database Template

```jinja2
{# templates/clickhouse/tenant_database.sql.j2 #}
{#
  Parameters:
    - tenant_id: str
    - tenant_slug: str
#}
{% set db_name = 'tenant_' ~ (tenant_slug | sql_safe) %}

-- Create tenant database
CREATE DATABASE IF NOT EXISTS {{ db_name }}
ENGINE = Atomic
COMMENT 'NovaSight tenant database for {{ tenant_slug }}';

-- Create base tables for tenant
CREATE TABLE IF NOT EXISTS {{ db_name }}.events
(
    event_id UUID DEFAULT generateUUIDv4(),
    event_type LowCardinality(String),
    event_timestamp DateTime64(3),
    event_date Date DEFAULT toDate(event_timestamp),
    user_id String,
    session_id String,
    properties String CODEC(ZSTD(3)),
    created_at DateTime DEFAULT now()
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_type, event_timestamp, event_id)
TTL event_date + INTERVAL 2 YEAR
SETTINGS index_granularity = 8192;

-- Create ingestion buffer table
CREATE TABLE IF NOT EXISTS {{ db_name }}.events_buffer
AS {{ db_name }}.events
ENGINE = Buffer(
    '{{ db_name }}', 'events',
    16,      -- num_layers
    10, 100, -- min/max time (seconds)
    10000, 1000000,  -- min/max rows
    10000000, 100000000  -- min/max bytes
);
```

### Dictionary Template

```jinja2
{# templates/clickhouse/dictionary.sql.j2 #}
{#
  Parameters:
    - database: str
    - dict_name: str
    - source_type: str (clickhouse, postgresql, http)
    - source_config: Dict
    - structure: List[ColumnDef]
    - layout: str (flat, hashed, complex_key_hashed, etc.)
    - lifetime: Dict (min, max)
#}
CREATE DICTIONARY IF NOT EXISTS {{ database }}.{{ dict_name | sql_safe }}
(
{% for col in structure %}
    {{ col.name }} {{ col.type }}{% if col.is_key %} IS KEY{% endif %}{% if col.default is defined %} DEFAULT {{ col.default }}{% endif %}{% if not loop.last %},{% endif %}

{% endfor %}
)
PRIMARY KEY {{ structure | selectattr('is_key') | map(attribute='name') | join(', ') }}
SOURCE(
{% if source_type == 'clickhouse' %}
    CLICKHOUSE(
        HOST '{{ source_config.host }}'
        PORT {{ source_config.port | default(9000) }}
        USER '{{ source_config.user }}'
        PASSWORD '{{ source_config.password }}'
        DB '{{ source_config.database }}'
        TABLE '{{ source_config.table }}'
    )
{% elif source_type == 'postgresql' %}
    POSTGRESQL(
        HOST '{{ source_config.host }}'
        PORT {{ source_config.port | default(5432) }}
        USER '{{ source_config.user }}'
        PASSWORD '{{ source_config.password }}'
        DB '{{ source_config.database }}'
        TABLE '{{ source_config.table }}'
    )
{% endif %}
)
LAYOUT({{ layout | upper }}())
LIFETIME(MIN {{ lifetime.min | default(300) }} MAX {{ lifetime.max | default(600) }})
;
```

## Expected Output

```
backend/templates/clickhouse/
├── create_table.sql.j2
├── materialized_view.sql.j2
├── tenant_database.sql.j2
├── dictionary.sql.j2
├── alter_table.sql.j2
└── projections.sql.j2
```

## Acceptance Criteria

- [ ] Templates generate valid ClickHouse SQL
- [ ] MergeTree configurations optimized
- [ ] Partitioning strategy correct
- [ ] TTL expressions valid
- [ ] Materialized views work
- [ ] Dictionaries load correctly
- [ ] Tenant isolation maintained

## Reference Documents

- [Template Engine Agent](../agents/template-engine-agent.agent.md)
- [Multi-Tenant DB Skill](../skills/multi-tenant-db/SKILL.md)
