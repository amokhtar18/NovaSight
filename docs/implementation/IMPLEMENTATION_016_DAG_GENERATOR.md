# Implementation 016: Ingestion DAG Generator

## Overview

This document describes the implementation of the Ingestion DAG Generator (Prompt 016), which creates Airflow DAGs to orchestrate pre-defined PySpark jobs.

## Completed Components

### 1. PySparkDAGGenerator Service

**File:** [backend/app/services/dag_generator.py](../../backend/app/services/dag_generator.py)

The `PySparkDAGGenerator` class provides:

- `generate_dag_for_pyspark_app()` - Generate DAG for a single PySpark app
- `generate_dag_for_multiple_apps()` - Generate pipeline DAG for multiple apps
- `update_dag_schedule()` - Update DAG schedule without regenerating
- `delete_dag()` - Delete DAG and associated job files
- `list_dags_for_tenant()` - List all DAGs for current tenant
- `get_dag_info()` - Get detailed DAG information

Key features:
- ADR-002 compliant: Only orchestrates pre-generated PySpark code
- Tenant isolation enforced via DAG ID prefixes
- Default Spark configuration with override support
- Notification support (email on failure)

### 2. Jinja2 Templates

**Single App DAG Template:** [backend/app/templates/airflow/pyspark_job_dag.py.j2](../../backend/app/templates/airflow/pyspark_job_dag.py.j2)

Features:
- SparkSubmitOperator for job execution
- Configurable schedule (cron or preset)
- Dynamic Spark configuration
- Completion logging task
- Tenant and SCD type tags

**Pipeline DAG Template:** [backend/app/templates/airflow/pyspark_pipeline_dag.py.j2](../../backend/app/templates/airflow/pyspark_pipeline_dag.py.j2)

Features:
- Multiple SparkSubmitOperator tasks
- Parallel or sequential execution modes
- Unified logging for pipeline completion
- Per-app configuration

### 3. API Endpoints

**File:** [backend/app/api/v1/dags.py](../../backend/app/api/v1/dags.py)

New endpoints added:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/dags/pyspark/generate` | Generate DAG for single PySpark app |
| POST | `/api/v1/dags/pyspark/generate-pipeline` | Generate pipeline DAG for multiple apps |
| GET | `/api/v1/dags/pyspark` | List all PySpark DAGs for tenant |
| GET | `/api/v1/dags/pyspark/<dag_id>` | Get DAG details |
| DELETE | `/api/v1/dags/pyspark/<dag_id>` | Delete DAG and job files |
| PATCH | `/api/v1/dags/pyspark/<dag_id>/schedule` | Update DAG schedule |

### 4. Unit Tests

**File:** [backend/tests/unit/test_dag_generator.py](../../backend/tests/unit/test_dag_generator.py)

Added comprehensive tests for `PySparkDAGGenerator`:
- DAG generation for single and multiple apps
- Error handling (app not found, no generated code)
- Schedule update functionality
- DAG deletion
- Tenant isolation verification
- Spark configuration defaults and overrides

## Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  PySpark App        │────▶│  PySparkDAGGenerator │────▶│  Airflow DAG    │
│  Builder (017)      │     │  Service (016)       │     │  Files          │
│  - Generates code   │     │  - Creates DAGs      │     │  - Schedules    │
│  - Stores config    │     │  - Sets schedule     │     │  - Submits jobs │
└─────────────────────┘     └──────────────────────┘     └─────────────────┘
                                      │
                                      ▼
                            ┌──────────────────────┐
                            │  Spark Cluster       │
                            │  - Runs PySpark jobs │
                            └──────────────────────┘
```

## Workflow Example

```
1. User creates PySpark app via PySpark App Builder UI
   → POST /api/v1/pyspark-apps
   
2. User generates code for the app
   → POST /api/v1/pyspark-apps/{id}/generate
   
3. User schedules the app via DAG Generator
   → POST /api/v1/dags/pyspark/generate
   {
     "pyspark_app_id": "...",
     "schedule": "@hourly"
   }
   
4. Airflow runs the DAG on schedule
   → SparkSubmitOperator submits the pre-generated PySpark code
   
5. Spark cluster executes the job
   → Data flows from source to ClickHouse
```

## API Usage Examples

### Generate Single App DAG

```bash
curl -X POST http://localhost:5000/api/v1/dags/pyspark/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pyspark_app_id": "550e8400-e29b-41d4-a716-446655440000",
    "schedule": "@hourly",
    "spark_config": {
      "spark.executor.memory": "4g",
      "spark.executor.cores": "4"
    },
    "notifications": {
      "email": "alerts@example.com",
      "email_on_failure": true
    }
  }'
```

### Generate Pipeline DAG

```bash
curl -X POST http://localhost:5000/api/v1/dags/pyspark/generate-pipeline \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "pyspark_app_ids": [
      "550e8400-e29b-41d4-a716-446655440000",
      "550e8400-e29b-41d4-a716-446655440001"
    ],
    "dag_name": "daily_data_pipeline",
    "schedule": "@daily",
    "parallel": false,
    "description": "Daily data ingestion pipeline"
  }'
```

### Update Schedule

```bash
curl -X PATCH http://localhost:5000/api/v1/dags/pyspark/pyspark_tenant123_app1/schedule \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"schedule": "@daily"}'
```

## File Structure

```
backend/app/
├── services/
│   └── dag_generator.py              # DagGenerator + PySparkDAGGenerator
├── api/v1/
│   └── dags.py                       # API endpoints (extended)
└── templates/airflow/
    ├── pyspark_job_dag.py.j2         # Single app DAG template
    └── pyspark_pipeline_dag.py.j2    # Multi-app pipeline template

infrastructure/airflow/
├── dags/                             # Generated DAG files
│   ├── pyspark_{tenant}_{app_id}.py
│   └── pipeline_{tenant}_{name}.py
└── spark_apps/
    └── jobs/                         # Pre-generated PySpark code
        ├── pyspark_{tenant}_{app_id}.py
        └── pipeline_{tenant}_{name}_{app_id}.py
```

## Security Considerations

1. **ADR-002 Compliance**: The DAG generator only orchestrates execution of pre-generated PySpark code. No arbitrary code generation occurs.

2. **Tenant Isolation**: DAG IDs are prefixed with tenant ID. All operations verify the DAG belongs to the current tenant.

3. **JWT Authentication**: All endpoints require valid JWT tokens.

4. **Role-Based Access**: Modification endpoints require `data_engineer` or `tenant_admin` roles.

## Dependencies

- Prompt 011: Airflow Templates (base templates)
- Prompt 013: Template Engine (rendering)
- Prompt 017: PySpark App Builder (generates the PySpark code)

## Acceptance Criteria Status

- [x] DAG generation only works for PySpark apps with generated code
- [x] DAGs reference pre-generated PySpark files (no inline code generation)
- [x] Generated DAGs use Jinja2 templates (pass Airflow syntax check)
- [x] DAGs submit to Spark cluster via SparkSubmitOperator
- [x] DAGs tagged with tenant and SCD type for Airflow UI
- [x] Pipeline DAGs support both parallel and sequential execution
- [x] Schedule updates work without regenerating code
- [x] Delete removes both DAG and associated PySpark files
- [x] Tenant isolation enforced
- [x] API endpoints secured with JWT
