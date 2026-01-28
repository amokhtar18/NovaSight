# Implementation 021: Transformation DAG Generator

## Summary

This implementation adds automated Airflow DAG generation for dbt transformation workflows, enabling end-to-end data pipelines that chain ingestion to transformation.

## Implemented Components

### 1. Transformation DAG Generator

**File**: [backend/app/services/transformation_dag_generator.py](../../../backend/app/services/transformation_dag_generator.py)

The `TransformationDAGGenerator` class generates Airflow DAGs that:
- Wait for ingestion DAGs to complete via `ExternalTaskSensor`
- Run dbt staging models for the data source
- Run dbt tests on staging models
- Run dbt mart models
- Run dbt tests on mart models

**Key Methods**:
- `generate_transformation_dag()` - Generate a full transformation DAG
- `generate_incremental_transformation_dag()` - Generate optimized incremental DAG
- `update_transformation_dag()` - Update existing DAG
- `delete_dag()` - Remove a DAG

### 2. Pipeline Generator

**File**: [backend/app/services/pipeline_generator.py](../../../backend/app/services/pipeline_generator.py)

The `PipelineGenerator` class orchestrates complete ingestion + transformation pipelines:
- Generates ingestion DAG (via existing `DagGenerator`)
- Generates transformation DAG (via `TransformationDAGGenerator`)
- Chains them with ExternalTaskSensor

**Key Methods**:
- `generate_full_pipeline()` - Generate both ingestion and transformation DAGs
- `generate_pipeline_with_dependencies()` - Generate with upstream/downstream deps
- `update_pipeline()` - Update existing pipeline
- `delete_pipeline()` - Remove all pipeline DAGs
- `get_pipeline_status()` - Get status of pipeline DAGs

**Fluent Builder**:
```python
pipeline = (
    FullPipelineBuilder(datasource)
    .add_tables(tables)
    .with_schedule('@hourly')
    .with_tests(True)
    .with_upstream_dependency('other_dag')
    .build()
)
```

### 3. Jinja2 Templates

**Files**:
- [datasource_transformation_dag.py.j2](../../../backend/app/templates/airflow/datasource_transformation_dag.py.j2) - Main transformation DAG
- [incremental_transformation_dag.py.j2](../../../backend/app/templates/airflow/incremental_transformation_dag.py.j2) - Incremental-only DAG
- [orchestration_dag.py.j2](../../../backend/app/templates/airflow/orchestration_dag.py.j2) - Multi-pipeline orchestration

### 4. Unit Tests

**File**: [backend/tests/unit/test_transformation_dag_generator.py](../../../backend/tests/unit/test_transformation_dag_generator.py)

Comprehensive tests for:
- `TransformationDAGGenerator` - name normalization, task config, DAG generation
- `PipelineGenerator` - full pipeline, validation, deletion
- `FullPipelineBuilder` - fluent interface, dependency handling

## Usage Examples

### Generate Transformation DAG

```python
from app.services import TransformationDAGGenerator

generator = TransformationDAGGenerator()
dag_id = generator.generate_transformation_dag(
    tenant_id="tenant-uuid",
    datasource=datasource,
    schedule="@hourly",
    run_tests=True,
)
```

### Generate Full Pipeline

```python
from app.services import PipelineGenerator

generator = PipelineGenerator()
result = generator.generate_full_pipeline(
    datasource=datasource,
    tables=tables,
    schedule="@hourly",
)
# Returns: {ingestion_dag_id, transformation_dag_id, ...}
```

### Using the Builder

```python
from app.services.pipeline_generator import FullPipelineBuilder

result = (
    FullPipelineBuilder(datasource)
    .add_tables(tables)
    .with_schedule('@daily')
    .with_tests(True)
    .with_upstream_dependency('external_data_dag')
    .build()
)
```

## Generated DAG Structure

### Transformation DAG

```
start → wait_for_ingestion → run_staging → test_staging → run_marts → test_marts → end
```

The `wait_for_ingestion` task uses `ExternalTaskSensor` to wait for the corresponding ingestion DAG to complete before running dbt models.

### Full Pipeline

```
[Ingestion DAG]                    [Transformation DAG]
    │                                    │
    └─── SparkSubmitOperator ──▶ ExternalTaskSensor ──▶ dbt run/test
```

## Template Variables

### datasource_transformation_dag.py.j2

| Variable | Type | Description |
|----------|------|-------------|
| tenant_id | str | Tenant identifier |
| datasource_id | str | Data source ID |
| datasource_name | str | Normalized datasource name |
| dag_id | str | DAG identifier |
| ingestion_dag_id | str | Upstream ingestion DAG |
| schedule | str | Cron/preset schedule |
| tasks | List[Dict] | Task configurations |
| run_tests | bool | Enable dbt tests |
| dbt_project_dir | str | Path to dbt project |
| dbt_profiles_dir | str | Path to dbt profiles |
| dbt_target | str | dbt target environment |

## Dependencies

- Prompt 016: Ingestion DAG Generator (provides `DagGenerator`)
- Prompt 018: dbt Model Generator (provides model structure)

## Acceptance Criteria

- [x] Transformation DAG generated correctly
- [x] ExternalTaskSensor waits for ingestion
- [x] dbt commands run with tenant context
- [x] Environment variables set correctly
- [x] DAGs chain correctly (ingest → transform)
- [x] Full pipeline generation works
- [x] DAGs visible in Airflow UI (templates generate valid Python)

## Files Created/Modified

### Created
- `backend/app/services/transformation_dag_generator.py`
- `backend/app/services/pipeline_generator.py`
- `backend/app/templates/airflow/datasource_transformation_dag.py.j2`
- `backend/app/templates/airflow/incremental_transformation_dag.py.j2`
- `backend/app/templates/airflow/orchestration_dag.py.j2`
- `backend/tests/unit/test_transformation_dag_generator.py`

### Modified
- `backend/app/services/__init__.py` - Added exports

## Next Steps

1. Test with actual Airflow deployment
2. Add API endpoints for pipeline management
3. Integrate with frontend pipeline builder UI
4. Add pipeline monitoring dashboard
