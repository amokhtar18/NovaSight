# Architecture Decision Records (ADR)

## NovaSight: Self-Service End-to-End BI Solution

**Document Version:** 1.0  
**Date:** January 26, 2026  
**Status:** Approved  
**Author:** Solution Architecture Team

---

## Table of Contents

1. [ADR-001: Metadata Store Selection](#adr-001-metadata-store-selection)
2. [ADR-002: Template-Filling Architecture](#adr-002-template-filling-architecture)
3. [ADR-003: Multi-Tenant Isolation Strategy](#adr-003-multi-tenant-isolation-strategy)
4. [ADR-004: AI Integration Architecture](#adr-004-ai-integration-architecture)
5. [ADR-005: Template Catalog](#adr-005-template-catalog)

---

## ADR-001: Metadata Store Selection

### Status
**Accepted**

### Context

NovaSight requires a centralized metadata store to persist:
- Tenant configurations and settings
- User accounts, roles, and permissions
- Data connection configurations (encrypted credentials)
- Ingestion job configurations
- dbt model metadata
- DAG configurations
- Alert definitions
- Audit logs
- Session management

The metadata store must support:
- ACID transactions for configuration integrity
- Complex relational queries for permission resolution
- JSON/JSONB for flexible schema evolution
- Strong consistency for security-critical operations
- Multi-tenant isolation at the schema level

### Decision

**PostgreSQL 15+** is selected as the metadata store.

### Rationale

| Requirement | PostgreSQL Capability |
|-------------|----------------------|
| **ACID Transactions** | Full ACID compliance with strong isolation levels |
| **Relational Modeling** | Native support for complex relationships (users, roles, permissions) |
| **Flexible Schema** | JSONB columns for evolving configurations without migrations |
| **Multi-Tenant Isolation** | Schema-per-tenant with `search_path` isolation |
| **Encryption** | TDE support, pg_crypto for column-level encryption |
| **Performance** | Excellent read performance with proper indexing |
| **Ecosystem** | Rich tooling, SQLAlchemy integration, Flask-SQLAlchemy |
| **Operational Maturity** | Well-understood backup, replication, and monitoring |

### Alternatives Considered

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| **MongoDB** | Flexible schema, document model | Weaker transactions, complex joins difficult | Rejected |
| **MySQL** | Wide adoption, good performance | Limited JSON support, schema isolation weaker | Rejected |
| **CockroachDB** | Distributed, PostgreSQL-compatible | Operational complexity, cost | Deferred for future scale |
| **SQLite** | Simple, embedded | No concurrent writes, no network access | Rejected |

### Schema Strategy

```
Platform Database: novasight_platform
├── public schema (platform-level)
│   ├── tenants
│   ├── platform_admins
│   ├── subscription_plans
│   └── platform_audit_log
│
├── tenant_acme schema
│   ├── users
│   ├── roles
│   ├── user_roles
│   ├── permissions
│   ├── data_connections
│   ├── ingestion_jobs
│   ├── ingestion_job_versions
│   ├── dbt_models
│   ├── dbt_model_versions
│   ├── dag_configurations
│   ├── dag_versions
│   ├── alerts
│   ├── alert_history
│   ├── dashboards
│   ├── saved_queries
│   ├── rls_policies
│   └── audit_log
│
├── tenant_globex schema
│   └── (same structure)
│
└── ... (per tenant)
```

### Consequences

**Positive:**
- Strong consistency guarantees for security-critical operations
- Mature ecosystem with extensive Flask integration
- Schema-based multi-tenancy provides logical isolation
- JSONB enables flexible configuration storage

**Negative:**
- Requires careful connection pooling for multi-tenant scale
- Schema-per-tenant increases DDL management complexity
- May need read replicas for high-read workloads

**Mitigations:**
- Use PgBouncer for connection pooling
- Implement automated schema migration tooling
- Plan for read replica topology from initial deployment

---

## ADR-002: Template-Filling Architecture

### Status
**Accepted**

### Context

The core security requirement mandates that NovaSight **never generates arbitrary code** from user input or LLM responses. All executable artifacts must be produced by filling pre-approved, security-audited templates.

This architectural constraint exists because:
1. **Security**: Arbitrary code generation creates injection vulnerabilities
2. **Auditability**: Pre-approved templates can be security-reviewed
3. **Consistency**: All generated artifacts follow approved patterns
4. **Governance**: Changes to execution logic require explicit template updates

### Decision

Implement a **Template Engine Architecture** using Jinja2 templates with strict input validation and parameterized variable injection.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE (React)                       │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Ingestion    │  │ DAG Builder  │  │ dbt Model    │               │
│  │ Config Form  │  │ Canvas       │  │ Builder      │               │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘               │
└─────────┼─────────────────┼─────────────────┼───────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FLASK BACKEND API                               │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                   INPUT VALIDATION LAYER                        │ │
│  │  • Schema validation (Pydantic/Marshmallow)                    │ │
│  │  • SQL injection prevention                                    │ │
│  │  • Path traversal prevention                                   │ │
│  │  • Allowlist validation for identifiers                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                 TEMPLATE ENGINE SERVICE                         │ │
│  │                                                                 │ │
│  │  ┌─────────────────┐    ┌─────────────────┐                    │ │
│  │  │ Template        │    │ Parameter       │                    │ │
│  │  │ Registry        │◄───│ Injection       │                    │ │
│  │  │ (approved only) │    │ Engine (Jinja2) │                    │ │
│  │  └─────────────────┘    └─────────────────┘                    │ │
│  │           │                      │                              │ │
│  │           ▼                      ▼                              │ │
│  │  ┌─────────────────────────────────────────────────────────────┐│ │
│  │  │              ARTIFACT GENERATOR                             ││ │
│  │  │  • Renders templates with validated parameters              ││ │
│  │  │  • Writes to tenant-specific artifact directories           ││ │
│  │  │  • Stores generation metadata for audit                     ││ │
│  │  └─────────────────────────────────────────────────────────────┘│ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   PySpark Job   │ │  Airflow DAG    │ │   dbt Model     │
│   (.py file)    │ │  (.py file)     │ │   (.sql file)   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Template Categories

#### 1. PySpark Ingestion Templates

```
templates/
└── pyspark/
    ├── base_ingestion.py.j2           # Core ingestion logic
    ├── jdbc_reader.py.j2               # JDBC source reading
    ├── scd_type1.py.j2                 # SCD Type 1 merge logic
    ├── scd_type2.py.j2                 # SCD Type 2 merge logic
    ├── incremental_load.py.j2          # Watermark-based loading
    └── full_load.py.j2                 # Full table replacement
```

#### 2. Airflow DAG Templates

```
templates/
└── airflow/
    ├── dag_base.py.j2                  # DAG structure
    ├── task_spark_submit.py.j2         # Spark job submission
    ├── task_dbt_run.py.j2              # dbt execution
    ├── task_dbt_test.py.j2             # dbt testing
    ├── task_email.py.j2                # Email notification
    ├── task_http_sensor.py.j2          # HTTP sensor
    └── task_sql_query.py.j2            # SQL execution
```

#### 3. dbt Model Templates

```
templates/
└── dbt/
    ├── model_base.sql.j2               # Base model structure
    ├── model_incremental.sql.j2        # Incremental materialization
    ├── join_clause.sql.j2              # JOIN generation
    ├── cte_block.sql.j2                # CTE generation
    ├── schema.yml.j2                   # Schema/test definitions
    └── sources.yml.j2                  # Source definitions
```

### Input Validation Rules

All user inputs are validated against strict allowlists:

```python
# Example validation schema
class IngestionJobConfig(BaseModel):
    job_name: str = Field(regex=r'^[a-z][a-z0-9_]{2,63}$')
    source_connection_id: UUID
    source_table: str = Field(regex=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    target_table: str = Field(regex=r'^[a-z][a-z0-9_]{2,63}$')
    columns: List[ColumnMapping]
    write_mode: Literal['overwrite', 'append', 'merge']
    scd_type: Optional[Literal['none', 'type1', 'type2']]
    
class ColumnMapping(BaseModel):
    source_column: str = Field(regex=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    target_column: str = Field(regex=r'^[a-z][a-z0-9_]{2,63}$')
    transformation: Optional[Literal['trim', 'upper', 'lower', 'none']]
    data_type: Literal['string', 'integer', 'decimal', 'date', 'timestamp', 'boolean']
```

### Security Guarantees

| Threat | Mitigation |
|--------|------------|
| **SQL Injection** | Identifiers validated against regex, no string concatenation |
| **Code Injection** | No `eval()` or `exec()`, templates are static |
| **Path Traversal** | Output paths constructed server-side, no user paths |
| **Template Injection** | Jinja2 sandboxed, no user content in templates |
| **Privilege Escalation** | Generated code runs with job-specific credentials |

### Consequences

**Positive:**
- Security-auditable: All templates can be reviewed
- Predictable: Generated artifacts follow known patterns
- Governable: Template changes go through approval process
- Debuggable: Super Admin can view exact generated code

**Negative:**
- Flexibility constrained: Users cannot create arbitrary logic
- Template maintenance: New use cases require template development
- Initial investment: Comprehensive template library needed upfront

**Mitigations:**
- Build comprehensive template library covering 95% of use cases
- Provide "escape hatch" for enterprise tier: custom template uploads (approved by platform admin)
- Version templates with backward compatibility guarantees

---

## ADR-003: Multi-Tenant Isolation Strategy

### Status
**Accepted**

### Context

NovaSight must support multiple tenants with complete data and configuration isolation. Tenants must not be able to access each other's data under any circumstances.

### Decision

Implement **Schema-per-Tenant** isolation for PostgreSQL metadata and **Database-per-Tenant** isolation for ClickHouse analytical data.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ROUTING LAYER                                 │
│                                                                      │
│  Request: https://acme.novasight.com/api/...                        │
│                    │                                                 │
│                    ▼                                                 │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  Tenant Resolution Middleware                                   │ │
│  │  • Extract tenant from subdomain                                │ │
│  │  • Validate tenant exists and is active                        │ │
│  │  • Inject tenant context into request                          │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DATA ACCESS LAYER                                 │
│                                                                      │
│  ┌─────────────────────────┐    ┌─────────────────────────┐        │
│  │   PostgreSQL            │    │   ClickHouse            │        │
│  │   (Metadata)            │    │   (Analytics)           │        │
│  │                         │    │                         │        │
│  │  SET search_path TO     │    │  USE tenant_acme;       │        │
│  │  tenant_acme, public;   │    │                         │        │
│  │                         │    │  All queries scoped     │        │
│  │  All queries scoped     │    │  to tenant database     │        │
│  │  to tenant schema       │    │                         │        │
│  └─────────────────────────┘    └─────────────────────────┘        │
│                                                                      │
│  ┌─────────────────────────┐    ┌─────────────────────────┐        │
│  │   Airflow               │    │   dbt                   │        │
│  │                         │    │                         │        │
│  │  DAGs in:               │    │  Projects in:           │        │
│  │  /dags/tenant_acme/     │    │  /dbt/tenant_acme/      │        │
│  │                         │    │                         │        │
│  │  Execution isolated     │    │  Execution isolated     │        │
│  │  via pools & queues     │    │  via target profiles    │        │
│  └─────────────────────────┘    └─────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

### Isolation Mechanisms

| Component | Isolation Method | Enforcement |
|-----------|-----------------|-------------|
| PostgreSQL | Schema-per-tenant | `search_path` set on connection |
| ClickHouse | Database-per-tenant | Database specified in all queries |
| Airflow | Folder-per-tenant | DAGs only loaded from tenant folder |
| dbt | Project-per-tenant | Separate dbt project directories |
| File Storage | Folder-per-tenant | Path constructed with tenant ID |
| API | Tenant context injection | Middleware validates all requests |

### Consequences

**Positive:**
- Strong isolation with minimal performance overhead
- Tenant-specific backup and restore possible
- Resource usage attributable per tenant
- Compliance-friendly for data residency requirements

**Negative:**
- Schema migrations must propagate to all tenant schemas
- Connection pooling more complex (per-tenant connections)
- Platform-wide queries (super admin) require cross-schema access

---

## ADR-004: AI Integration Architecture

### Status
**Accepted**

### Context

NovaSight integrates AI capabilities using Ollama (local LLMs) for natural language data exploration. The AI must:
- Respect RLS policies
- Not leak cross-tenant data
- Generate only SELECT queries (read-only)
- Provide transparency on generated SQL

### Decision

Implement a **Constrained AI Query Generation** architecture with dynamic system prompts and server-side query execution.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AI INTERACTION FLOW                             │
│                                                                      │
│  User: "What were our top products last month?"                     │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  1. CONTEXT BUILDER                                             │ │
│  │                                                                 │ │
│  │  Builds dynamic system prompt containing:                       │ │
│  │  • Available tables/models (filtered by user's RLS)            │ │
│  │  • Column names and descriptions (from semantic layer)         │ │
│  │  • Tenant-specific business context                            │ │
│  │  • Strict instructions: SELECT only, no DDL/DML                │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  2. OLLAMA LLM                                                  │ │
│  │                                                                 │ │
│  │  Model: codellama or similar SQL-capable model                 │ │
│  │  Generates SQL query based on:                                 │ │
│  │  • System prompt (context)                                     │ │
│  │  • User question                                               │ │
│  │  • Conversation history                                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  3. SQL VALIDATOR                                               │ │
│  │                                                                 │ │
│  │  Server-side validation:                                       │ │
│  │  • Parse SQL with sqlparse                                     │ │
│  │  • Reject if not SELECT statement                              │ │
│  │  • Reject if contains subqueries to unauthorized tables        │ │
│  │  • Reject if contains forbidden functions (SLEEP, etc.)        │ │
│  │  • Apply query complexity limits                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  4. RLS INJECTION                                               │ │
│  │                                                                 │ │
│  │  Wrap generated SQL with RLS filters:                          │ │
│  │                                                                 │ │
│  │  SELECT * FROM (                                               │ │
│  │    -- LLM-generated query                                      │ │
│  │  ) AS user_query                                               │ │
│  │  WHERE {rls_conditions}                                        │ │
│  │  LIMIT 10000                                                   │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  5. QUERY EXECUTION                                             │ │
│  │                                                                 │ │
│  │  Execute against ClickHouse with:                              │ │
│  │  • Tenant database scope                                       │ │
│  │  • Read-only connection                                        │ │
│  │  • Query timeout (30 seconds)                                  │ │
│  │  • Row limit enforcement                                       │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                              │                                       │
│                              ▼                                       │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │  6. RESPONSE GENERATION                                         │ │
│  │                                                                 │ │
│  │  Return to user:                                               │ │
│  │  • Generated SQL (for transparency)                            │ │
│  │  • Query results (table)                                       │ │
│  │  • Natural language summary                                    │ │
│  │  • Suggested follow-up questions                               │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Security Controls

| Control | Implementation |
|---------|----------------|
| Query Type | Only SELECT statements allowed |
| RLS Enforcement | Server-side injection, cannot be bypassed |
| Table Access | System prompt only includes authorized tables |
| Query Limits | 30-second timeout, 10,000 row limit |
| Audit | All AI queries logged with user, question, SQL, result |
| Rate Limiting | Per-user, per-tenant query limits |

---

## ADR-005: Template Catalog

### Status
**Accepted**

### Context

This document catalogs all pre-approved templates used in the Template-Filling Architecture.

### PySpark Templates

#### `spark_ingestion_base.py.j2`

```python
"""
PySpark Ingestion Job: {{ job_name }}
Generated: {{ generated_at }}
Template Version: 1.0.0
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import lit, current_timestamp

def main():
    spark = SparkSession.builder \
        .appName("{{ tenant_id }}_{{ job_name }}") \
        .getOrCreate()
    
    # Read from source
    df = spark.read \
        .format("jdbc") \
        .option("url", "{{ source_jdbc_url }}") \
        .option("dbtable", "{{ source_table }}") \
        .option("user", "{{ source_user }}") \
        .option("password", "{{ source_password }}") \
        .load()
    
    # Select and transform columns
    df = df.select(
        {% for col in columns %}
        {{ col.transformation }}(df["{{ col.source }}"]).alias("{{ col.target }}"){{ "," if not loop.last else "" }}
        {% endfor %}
    )
    
    # Add metadata columns
    df = df.withColumn("_loaded_at", current_timestamp()) \
           .withColumn("_job_name", lit("{{ job_name }}"))
    
    {% if write_mode == 'overwrite' %}
    # Full overwrite
    df.write \
        .format("clickhouse") \
        .option("url", "{{ target_clickhouse_url }}") \
        .option("table", "{{ target_table }}") \
        .mode("overwrite") \
        .save()
    {% elif write_mode == 'append' %}
    # Append mode
    df.write \
        .format("clickhouse") \
        .option("url", "{{ target_clickhouse_url }}") \
        .option("table", "{{ target_table }}") \
        .mode("append") \
        .save()
    {% elif write_mode == 'merge' %}
    # Merge using ReplacingMergeTree
    {% include 'spark_merge_logic.py.j2' %}
    {% endif %}
    
    spark.stop()

if __name__ == "__main__":
    main()
```

#### `spark_scd_type2.py.j2`

```python
"""
SCD Type 2 Logic for: {{ job_name }}
"""
from pyspark.sql.functions import col, lit, current_timestamp, when
from pyspark.sql.window import Window

# Read existing records
existing_df = spark.read \
    .format("clickhouse") \
    .option("url", "{{ target_clickhouse_url }}") \
    .option("table", "{{ target_table }}") \
    .load() \
    .filter(col("{{ is_current_col }}") == True)

# Identify changed records
join_condition = {% for pk in primary_keys %}(df["{{ pk }}"] == existing_df["{{ pk }}"]){{ " & " if not loop.last else "" }}{% endfor %}

changes_df = df.alias("new").join(
    existing_df.alias("old"),
    join_condition,
    "left"
).filter(
    {% for track_col in tracked_columns %}
    (col("new.{{ track_col }}") != col("old.{{ track_col }}")){{ " | " if not loop.last else "" }}
    {% endfor %}
)

# Close existing records
updates_df = changes_df.select(
    {% for col in all_columns %}
    col("old.{{ col }}"),
    {% endfor %}
).withColumn("{{ effective_to_col }}", current_timestamp()) \
 .withColumn("{{ is_current_col }}", lit(False))

# Insert new versions
inserts_df = changes_df.select(
    {% for col in all_columns %}
    col("new.{{ col }}"),
    {% endfor %}
).withColumn("{{ effective_from_col }}", current_timestamp()) \
 .withColumn("{{ effective_to_col }}", lit(None)) \
 .withColumn("{{ is_current_col }}", lit(True))

# Write updates and inserts
# ... ClickHouse write logic
```

### Airflow DAG Templates

#### `dag_base.py.j2`

```python
"""
Airflow DAG: {{ dag_id }}
Generated: {{ generated_at }}
Template Version: 1.0.0
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.empty import EmptyOperator
{% for import in task_imports %}
{{ import }}
{% endfor %}

default_args = {
    'owner': '{{ tenant_id }}',
    'depends_on_past': False,
    'email': {{ notification_emails | tojson }},
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': {{ retries | default(1) }},
    'retry_delay': timedelta(minutes={{ retry_delay_minutes | default(5) }}),
}

with DAG(
    dag_id='{{ tenant_id }}_{{ dag_id }}',
    default_args=default_args,
    description='{{ description }}',
    schedule_interval='{{ schedule }}',
    start_date=datetime({{ start_date.year }}, {{ start_date.month }}, {{ start_date.day }}),
    catchup={{ catchup | default(False) }},
    max_active_runs={{ max_active_runs | default(1) }},
    tags={{ tags | tojson }},
) as dag:

    start = EmptyOperator(task_id='start')
    end = EmptyOperator(task_id='end')

    {% for task in tasks %}
    {{ task.id }} = {% include task.template %}
    {% endfor %}

    # Dependencies
    {% for dep in dependencies %}
    {{ dep.upstream }} >> {{ dep.downstream }}
    {% endfor %}
```

#### `task_spark_submit.py.j2`

```python
{{ task_id }} = SparkSubmitOperator(
    task_id='{{ task_id }}',
    application='/opt/spark/jobs/{{ tenant_id }}/{{ job_name }}.py',
    conn_id='spark_default',
    conf={
        'spark.executor.memory': '{{ executor_memory | default("2g") }}',
        'spark.executor.cores': '{{ executor_cores | default(2) }}',
    },
    execution_timeout=timedelta(minutes={{ timeout_minutes | default(60) }}),
    trigger_rule='{{ trigger_rule | default("all_success") }}',
)
```

#### `task_dbt_run.py.j2`

```python
{{ task_id }} = BashOperator(
    task_id='{{ task_id }}',
    bash_command='cd /opt/dbt/{{ tenant_id }} && dbt run {% if models %}--select {{ models | join(" ") }}{% endif %}{% if tags %}--selector tag:{{ tags | join(" tag:") }}{% endif %}{% if full_refresh %}--full-refresh{% endif %}',
    execution_timeout=timedelta(minutes={{ timeout_minutes | default(30) }}),
    trigger_rule='{{ trigger_rule | default("all_success") }}',
)
```

### dbt Model Templates

#### `model_base.sql.j2`

```sql
{{/*
  dbt Model: {{ model_name }}
  Generated: {{ generated_at }}
  Template Version: 1.0.0
*/}}

{{ "{{" }} config(
    materialized='{{ materialization }}',
    {% if materialization == 'incremental' %}
    unique_key='{{ unique_key }}',
    incremental_strategy='{{ incremental_strategy | default("delete+insert") }}',
    {% endif %}
    tags={{ tags | tojson }}
) {{ "}}" }}

{% if ctes %}
{% for cte in ctes %}
{% include 'cte_block.sql.j2' %}
{% endfor %}
{% endif %}

SELECT
    {% for column in columns %}
    {% if column.expression %}
    {{ column.expression }} AS {{ column.alias }}{{ "," if not loop.last else "" }}
    {% else %}
    {{ column.source_table }}.{{ column.source_column }}{% if column.alias %} AS {{ column.alias }}{% endif %}{{ "," if not loop.last else "" }}
    {% endif %}
    {% endfor %}
FROM {{ "{{" }} ref('{{ source_model }}') {{ "}}" }}
{% for join in joins %}
{{ join.type }} JOIN {{ "{{" }} ref('{{ join.model }}') {{ "}}" }} AS {{ join.alias }}
    ON {{ join.condition }}
{% endfor %}
{% if where_clause %}
WHERE {{ where_clause }}
{% endif %}
{% if group_by %}
GROUP BY {{ group_by | join(", ") }}
{% endif %}
```

#### `schema.yml.j2`

```yaml
version: 2

models:
  - name: {{ model_name }}
    description: {{ description }}
    columns:
      {% for column in columns %}
      - name: {{ column.name }}
        description: {{ column.description }}
        {% if column.tests %}
        tests:
          {% for test in column.tests %}
          {% if test.type == 'unique' %}
          - unique
          {% elif test.type == 'not_null' %}
          - not_null
          {% elif test.type == 'accepted_values' %}
          - accepted_values:
              values: {{ test.values | tojson }}
          {% elif test.type == 'relationships' %}
          - relationships:
              to: ref('{{ test.to_model }}')
              field: {{ test.to_field }}
          {% endif %}
          {% endfor %}
        {% endif %}
      {% endfor %}
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-26 | Architecture Team | Initial release |

---

*End of Architecture Decision Records*
