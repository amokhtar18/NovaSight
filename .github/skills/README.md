# NovaSight Skills Index

This document provides an index of all reusable skills in the NovaSight multi-agent framework.

---

## 🧰 Skills Overview

| Skill | Purpose | Key Patterns |
|-------|---------|--------------|
| [Flask API](#flask-api) | REST API development | Blueprints, endpoints, validation |
| [React Components](#react-components) | UI development | Components, forms, tables |
| [Template Engine](#template-engine) | Code generation | Templates, schemas, sandboxing |
| [dlt + Iceberg](#dlt--iceberg) | Tenant-isolated ingestion | dlt pipelines, Iceberg-on-S3, per-tenant lake |
| [Multi-Tenant DB](#multi-tenant-db) | Database isolation | Schema isolation, RLS |
| [Airflow DAGs](#airflow-dags) | Pipeline orchestration | DAG creation, scheduling |

---

## 📁 Skill Files

### Flask API
**File:** `flask-api/SKILL.md`

Patterns for building Flask REST APIs with multi-tenant support.

**Key Patterns:**
- Blueprint structure with versioning
- CRUD endpoint implementation
- Pydantic request validation
- Standard response format
- Error handling middleware
- Permission decorators

**Usage:**
```python
@bp.route('/', methods=['POST'])
@jwt_required()
@require_permission('resource.create')
def create_resource():
    data = ResourceCreate(**request.json)
    # ... implementation
```

---

### React Components
**File:** `react-components/SKILL.md`

Patterns for building React components with TypeScript and Shadcn/UI.

**Key Patterns:**
- Component structure with props
- Form handling with React Hook Form + Zod
- DataTable with TanStack Table
- Query hooks with TanStack Query
- Page layout patterns

**Usage:**
```typescript
const form = useForm<FormData>({
  resolver: zodResolver(formSchema),
  defaultValues: { ... }
});
```

---

### Template Engine
**File:** `template-engine/SKILL.md`

Patterns for secure code generation using Jinja2 templates.

**Key Patterns:**
- Template registry
- Pydantic validation schemas
- Sandboxed Jinja2 environment
- Forbidden pattern detection
- Artifact generation service

**⚠️ CRITICAL:** Enforces Template Engine Rule.

**Usage:**
```python
config = DltExtractDefinition(
    pipeline_name="orders_load",
    tenant_slug="acme",
    source_table="public.orders",
    iceberg_namespace="tenant_acme.raw",
    iceberg_table_name="orders",
    write_disposition="replace",
    columns=[...],
)
artifact_service.generate_dlt_pipeline(config, credentials, tenant_id)
```

---

### dlt + Iceberg
**File:** `dlt-iceberg/SKILL.md`

Patterns for tenant-isolated ingestion using **dlt** writing into **Apache Iceberg** tables on **per-tenant S3 buckets**, with a Postgres-backed Iceberg SQL catalog.

**Key Patterns:**
- Per-tenant S3 bucket + namespace `tenant_{slug}.raw`
- `iceberg_catalog.get_catalog_for_tenant()` helper
- Three pipeline templates: `extract` (append/replace), `merge`, `scd2`
- Plain-language wizard → `write_disposition` mapping
- Dagster `DltAssetBuilder` subprocess runner
- Forbidden-pattern validators (no hard-coded creds, no `os.system`, namespace must match tenant)

**⚠️ CRITICAL:** Replaces all PySpark ingestion. See [.github/instructions/MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md).

---

### Multi-Tenant DB
**File:** `multi-tenant-db/SKILL.md`

Patterns for multi-tenant database isolation.

**Key Patterns:**
- PostgreSQL schema-per-tenant
- ClickHouse database-per-tenant
- Row-Level Security (RLS)
- Tenant-aware model mixin
- Tenant provisioning

**Usage:**
```python
class Connection(db.Model, TenantMixin):
    __tablename__ = 'connections'
    # ...

connections = Connection.query_for_tenant().all()
```

---

### Airflow DAGs
**File:** `airflow-dags/SKILL.md`

Patterns for creating Airflow DAGs.

**Key Patterns:**
- DAG configuration schemas
- DAG template with Jinja2
- DAG service for CRUD
- Airflow REST client
- Pipeline monitoring

**Usage:**
```python
dag_config = DagConfig(
    dag_id="daily_orders_pipeline",
    schedule_interval=ScheduleInterval.DAILY,
    tasks=[
        DltRunTaskConfig(task_id="load_orders", pipeline_id="..."),
        DbtRunTaskConfig(task_id="transform_orders", models=["orders"])
    ]
)
dag_service.create_dag(dag_config)
```

---

## 🔧 Using Skills

### In Agent Conversations

Reference a skill when implementing a feature:

```
@backend Create the ConnectionService following the Flask API skill patterns 
for service layer implementation.
```

### In Prompts

Skills are referenced in prompts for context:

```
Follow the react-components skill patterns for form handling.
Use the multi-tenant-db skill for tenant isolation.
```

### Reading Skills

Before implementing, read the relevant skill file:

```
Read the template-engine skill to understand code generation patterns.
```

---

## 📋 Skill Structure

Each skill file follows this structure:

```markdown
# Skill Name

## Description
What the skill covers and when to use it.

## Trigger
Keywords/phrases that indicate this skill should be used.

## Instructions
Detailed implementation patterns with code examples.

## Reference Files
Links to related agents and documentation.
```

---

## 🆕 Adding New Skills

To add a new skill:

1. Create directory: `.github/skills/[skill-name]/`
2. Create `SKILL.md` with standard structure
3. Add to this index
4. Reference in relevant agents

---

## 🔗 Related Resources

- [Agents Index](../agents/README.md)
- [Prompts Collection](../prompts/PROMPTS.md)
- [Instructions](../instructions/INSTRUCTIONS.md)

---

*NovaSight Skills Index v1.0*
