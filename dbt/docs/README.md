# dbt Documentation

This directory contains additional documentation for the NovaSight dbt project.

## Project Overview

NovaSight uses dbt for data transformations in a multi-tenant ClickHouse environment.

### Key Concepts

1. **Multi-Tenant Isolation**: Each tenant has their own database (`tenant_<id>`)
2. **Materialization Patterns**:
   - `staging/`: Views for raw data cleaning
   - `intermediate/`: Ephemeral models for business logic
   - `marts/`: Tables for dashboard consumption

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TENANT_ID` | Current tenant identifier | (required) |
| `TENANT_DATABASE` | Tenant's ClickHouse database | `tenant_<TENANT_ID>` |
| `DBT_TARGET` | Target environment | `dev` |
| `CLICKHOUSE_HOST` | ClickHouse server host | `localhost` |
| `CLICKHOUSE_PORT` | ClickHouse HTTP port | `8123` |
| `CLICKHOUSE_USER` | ClickHouse username | `default` |
| `CLICKHOUSE_PASSWORD` | ClickHouse password | (empty) |

### Running dbt

```bash
# Set tenant context
export TENANT_ID=abc123

# Install packages
dbt deps

# Run all models
dbt run

# Run specific models
dbt run --select staging.customers

# Run tests
dbt test

# Generate docs
dbt docs generate
dbt docs serve
```
