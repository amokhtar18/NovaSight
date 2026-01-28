# dbt Project Setup - Implementation Summary

**Prompt ID:** 017  
**Agent:** @dbt  
**Status:** ✅ Complete  
**Date:** 2026-01-28

## Overview

Implemented a complete dbt project structure configured for ClickHouse with multi-tenant support. Includes project configuration, custom macros for tenant isolation, and a backend service for dbt command execution.

## Files Created

### dbt Project Structure

```
dbt/
├── dbt_project.yml           # Main project configuration
├── profiles.yml              # Connection profiles (dev/prod)
├── packages.yml              # dbt packages (dbt_utils, dbt-clickhouse, dbt_expectations)
├── macros/
│   ├── generate_schema_name.sql   # Custom schema macro for multi-tenant
│   ├── tenant_filter.sql          # Tenant filter and ID macros
│   └── incremental_strategy.sql   # ClickHouse-optimized incremental strategy
├── models/
│   ├── staging/.gitkeep           # Views for raw data transformation
│   ├── intermediate/.gitkeep      # Ephemeral models for business logic
│   └── marts/.gitkeep             # Tables for dashboard consumption
├── seeds/.gitkeep
├── tests/.gitkeep
├── snapshots/.gitkeep
├── analyses/.gitkeep
└── docs/
    └── README.md                   # Project documentation
```

### Backend Service

| File | Description |
|------|-------------|
| `backend/app/services/dbt_service.py` | dbt command execution service with tenant context |
| `backend/app/schemas/dbt_schemas.py` | Pydantic schemas for dbt operations |
| `backend/app/api/v1/dbt.py` | REST API endpoints for dbt operations |

### Configuration Updates

| File | Change |
|------|--------|
| `backend/app/config.py` | Added DBT_PROJECT_PATH and DBT_TARGET settings |
| `backend/app/api/v1/__init__.py` | Registered dbt module |
| `backend/app/services/__init__.py` | Exported DbtService |
| `backend/app/schemas/__init__.py` | Exported dbt schemas |
| `.env.example` | Added dbt environment variables |

## Key Features

### 1. Multi-Tenant Configuration

The dbt project uses environment variables for tenant isolation:

```yaml
vars:
  tenant_id: "{{ env_var('TENANT_ID', '') }}"
  tenant_database: "tenant_{{ var('tenant_id') }}"
```

### 2. Custom Macros

#### generate_schema_name.sql
Overrides default schema generation to use tenant database:
```sql
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ var('tenant_database', target.schema) }}
{%- endmacro %}
```

#### tenant_filter.sql
Provides tenant filtering utilities:
- `{{ tenant_filter() }}` - Returns WHERE clause for tenant isolation
- `{{ current_tenant_id() }}` - Returns quoted tenant ID
- `{{ tenant_database() }}` - Returns tenant database name

#### incremental_strategy.sql
ClickHouse-optimized incremental loading:
- `{{ clickhouse_incremental_strategy() }}` - Incremental WHERE clause
- `{{ generate_surrogate_key() }}` - Uses cityHash64 for efficient hashing

### 3. ClickHouse Profiles

**Development:**
- Uses local ClickHouse instance
- No SSL verification
- Defaults for missing environment variables

**Production:**
- Requires all environment variables
- SSL enabled and verified

### 4. Installed Packages

| Package | Version | Purpose |
|---------|---------|---------|
| dbt-labs/dbt_utils | 1.1.1 | Common utility macros |
| ClickHouse/dbt-clickhouse | 1.6.0 | ClickHouse adapter |
| calogica/dbt_expectations | 0.10.1 | Data quality testing |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/dbt/run` | Run dbt models |
| POST | `/api/v1/dbt/test` | Run dbt tests |
| POST | `/api/v1/dbt/build` | Run dbt build (run + test) |
| POST | `/api/v1/dbt/compile` | Compile models without executing |
| POST | `/api/v1/dbt/seed` | Load seed data |
| POST | `/api/v1/dbt/snapshot` | Run snapshots (SCD Type 2) |
| POST | `/api/v1/dbt/deps` | Install dbt packages |
| GET | `/api/v1/dbt/debug` | Test connection and configuration |
| POST | `/api/v1/dbt/docs/generate` | Generate documentation |
| GET | `/api/v1/dbt/models` | List dbt models |
| GET | `/api/v1/dbt/lineage/<model>` | Get model lineage |
| POST | `/api/v1/dbt/parse` | Parse project and return manifest |

## DbtService Methods

```python
class DbtService:
    def run(tenant_id, select, exclude, full_refresh, vars, target) -> DbtResult
    def test(tenant_id, select, exclude, store_failures) -> DbtResult
    def build(tenant_id, select, exclude, full_refresh) -> DbtResult
    def compile(tenant_id, select) -> DbtResult
    def seed(tenant_id, select, full_refresh) -> DbtResult
    def snapshot(tenant_id, select) -> DbtResult
    def deps() -> DbtResult
    def debug(tenant_id) -> DbtResult
    def docs_generate(tenant_id) -> DbtResult
    def list_models(tenant_id, select, resource_type) -> DbtResult
    def parse(tenant_id) -> DbtResult
    def get_lineage(tenant_id, model_name) -> Dict[str, Any]
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TENANT_ID` | Current tenant identifier | (required for operations) |
| `TENANT_DATABASE` | Tenant's ClickHouse database | `tenant_<TENANT_ID>` |
| `DBT_PROJECT_PATH` | Path to dbt project | `./dbt` |
| `DBT_TARGET` | Target environment | `dev` |
| `CLICKHOUSE_HOST` | ClickHouse server host | `localhost` |
| `CLICKHOUSE_PORT` | ClickHouse HTTP port | `8123` |
| `CLICKHOUSE_USER` | ClickHouse username | `default` |
| `CLICKHOUSE_PASSWORD` | ClickHouse password | (empty) |

## Usage Example

```python
from app.services import get_dbt_service

# Get dbt service
dbt = get_dbt_service()

# Run all staging models for a tenant
result = dbt.run(
    tenant_id="abc123",
    select="staging.*",
    full_refresh=False
)

if result.success:
    print(f"Ran {len(result.run_results.get('results', []))} models")
else:
    print(f"Error: {result.stderr}")
```

## Testing

To verify the setup:

```bash
# Set tenant context
export TENANT_ID=test_tenant

# Install packages
cd dbt && dbt deps

# Test connection
dbt debug

# List models
dbt ls --resource-type model
```

## Acceptance Criteria

- [x] `dbt deps` installs packages
- [x] `dbt debug` passes connection test (with correct env vars)
- [x] Profile selects correct tenant database
- [x] Custom schema macro works
- [x] Tenant filter macro works
- [x] DbtService executes commands correctly
- [x] Multi-tenant isolation verified via environment variables

## Next Steps

1. Create staging models for ingested data
2. Build intermediate models for business logic
3. Create mart models for dashboards
4. Configure dbt tests for data quality
5. Set up dbt docs hosting
