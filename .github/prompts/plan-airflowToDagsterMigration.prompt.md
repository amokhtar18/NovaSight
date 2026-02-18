# NovaSight: Airflow to Dagster Migration Plan

## Executive Summary

This document provides a comprehensive migration plan to replace Apache Airflow with Dagster in the NovaSight platform while maintaining the same logic, user experience, and API contracts.

---

## Current State Analysis

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        NovaSight Platform                           │
├─────────────────────────────────────────────────────────────────────┤
│  Frontend (React)                                                   │
│  ├── DagsListPage.tsx       → Lists all DAG configurations         │
│  ├── DagBuilderPage.tsx     → Visual DAG editor                    │
│  └── DagMonitorPage.tsx     → Run monitoring & logs                │
│                                                                     │
│  Backend (Flask)                                                    │
│  ├── domains/orchestration/                                         │
│  │   ├── api/dag_routes.py           → REST API endpoints          │
│  │   ├── application/dag_service.py  → Business logic              │
│  │   ├── application/pipeline_service.py → Pipeline generation     │
│  │   ├── infrastructure/                                            │
│  │   │   ├── dag_generator.py         → Generates DAG files        │
│  │   │   ├── transformation_dag_generator.py → dbt DAGs            │
│  │   │   └── airflow_client.py        → REST API client            │
│  │   ├── domain/models.py             → SQLAlchemy models          │
│  │   └── schemas/dag_schemas.py       → Pydantic validation        │
│                                                                     │
│  Airflow 3.x                                                        │
│  ├── airflow-postgres       → Metadata database                    │
│  ├── airflow-api-server     → REST API (port 8080)                 │
│  ├── airflow-dag-processor  → DAG parsing                          │
│  ├── airflow-scheduler      → Task scheduling                      │
│  └── Generated DAG files    → /opt/airflow/dags/                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Current Components Inventory

#### Backend Files to Migrate

| File | Purpose | Migration Impact |
|------|---------|------------------|
| `domains/orchestration/infrastructure/dag_generator.py` | Generates Airflow DAG Python files from Jinja2 templates | **HIGH** - Replace with Dagster asset factory |
| `domains/orchestration/infrastructure/transformation_dag_generator.py` | Generates dbt transformation DAGs | **HIGH** - Replace with dagster-dbt integration |
| `domains/orchestration/infrastructure/airflow_client.py` | REST API client for Airflow 3.x | **HIGH** - Replace with Dagster GraphQL client |
| `domains/orchestration/application/dag_service.py` | CRUD operations, deployment, triggering | **MEDIUM** - Adapt to use Dagster client |
| `domains/orchestration/application/pipeline_service.py` | Full pipeline generation (ingestion + transform) | **MEDIUM** - Adapt to Dagster asset model |
| `domains/orchestration/api/dag_routes.py` | REST API endpoints | **LOW** - Keep same API, change implementation |
| `domains/orchestration/domain/models.py` | DagConfig, TaskConfig, DagVersion models | **LOW** - Keep models, add Dagster mappings |
| `domains/orchestration/schemas/dag_schemas.py` | Pydantic validation schemas | **LOW** - Keep schemas |

#### Frontend Files (No Changes Required)

| File | Purpose |
|------|---------|
| `pages/orchestration/DagsListPage.tsx` | Lists pipelines |
| `pages/orchestration/DagBuilderPage.tsx` | Visual pipeline editor |
| `pages/orchestration/DagMonitorPage.tsx` | Run monitoring |
| `services/dagService.ts` | API client |

#### Airflow Templates (To Be Converted)

| Template | Purpose | Dagster Equivalent |
|----------|---------|-------------------|
| `dag_template.py.j2` | Generic DAG template | Asset factory with config |
| `spark_ingestion_dag.py.j2` | Spark ingestion DAG | `@asset` with Spark resource |
| `transformation_dag.py.j2` | dbt transformation DAG | `@dbt_assets` decorator |
| `pyspark_job_dag.py.j2` | PySpark job DAG | `@asset` with Spark submit |
| `ingestion_dag.py.j2` | Data ingestion DAG | Ingestion asset factory |

#### Docker/Infrastructure Changes

| Component | Current | Target |
|-----------|---------|--------|
| `docker-compose.yml` | Airflow services (5 containers) | Dagster services (3 containers) |
| `docker/airflow/Dockerfile` | Airflow 3.x image | Dagster image |
| `infrastructure/airflow/` | DAG files, plugins, Spark apps | Move to `orchestration/` |

#### Current API Endpoints

```
GET    /api/v1/dags                           → List DAGs
POST   /api/v1/dags                           → Create DAG
GET    /api/v1/dags/{dag_id}                  → Get DAG details
PUT    /api/v1/dags/{dag_id}                  → Update DAG
DELETE /api/v1/dags/{dag_id}                  → Delete DAG
POST   /api/v1/dags/{dag_id}/validate         → Validate DAG
POST   /api/v1/dags/{dag_id}/deploy           → Deploy to orchestrator
POST   /api/v1/dags/{dag_id}/trigger          → Trigger run
POST   /api/v1/dags/{dag_id}/pause            → Pause scheduling
POST   /api/v1/dags/{dag_id}/unpause          → Resume scheduling
GET    /api/v1/dags/{dag_id}/runs             → List runs
GET    /api/v1/dags/{dag_id}/runs/{run_id}    → Get run details
GET    /api/v1/dags/{dag_id}/runs/{run_id}/tasks/{task_id}/logs → Get task logs
```

---

## Migration Plan

### Phase 1: Foundation Setup (Week 1)

#### 1.1 Install Dagster Dependencies

Add to `backend/requirements.txt`:

```txt
# Dagster Core
dagster>=1.9.0
dagster-webserver>=1.9.0
dagster-graphql>=1.9.0

# Dagster Integrations
dagster-dbt>=0.25.0
dagster-postgres>=0.25.0
dagster-pyspark>=0.25.0

# GraphQL Client
gql>=3.5.0
```

#### 1.2 Create Orchestration Directory Structure

```
backend/
├── app/
│   └── domains/
│       └── orchestration/
│           ├── __init__.py
│           ├── api/
│           │   ├── __init__.py
│           │   └── dag_routes.py          # Keep existing (update implementation)
│           ├── application/
│           │   ├── __init__.py
│           │   ├── dag_service.py         # Update to use Dagster
│           │   └── pipeline_service.py    # Update to use Dagster
│           ├── domain/
│           │   ├── __init__.py
│           │   ├── models.py              # Keep existing
│           │   └── validators.py          # Keep existing
│           ├── schemas/
│           │   ├── __init__.py
│           │   └── dag_schemas.py         # Keep existing
│           └── infrastructure/
│               ├── __init__.py
│               ├── dagster_client.py      # NEW: Dagster GraphQL client
│               ├── asset_factory.py       # NEW: Dynamic asset builder
│               ├── schedule_factory.py    # NEW: Dynamic schedule builder
│               └── legacy/                # Move old files here during transition
│                   ├── dag_generator.py
│                   ├── transformation_dag_generator.py
│                   └── airflow_client.py
└── orchestration/                          # NEW: Dagster project root
    ├── __init__.py
    ├── definitions.py                      # Dagster entry point
    ├── assets/
    │   ├── __init__.py
    │   ├── ingestion_assets.py
    │   ├── dbt_assets.py
    │   └── spark_assets.py
    ├── resources/
    │   ├── __init__.py
    │   ├── spark_resource.py
    │   ├── clickhouse_resource.py
    │   └── database_resource.py
    ├── schedules/
    │   └── __init__.py
    ├── sensors/
    │   └── __init__.py
    └── config/
        ├── __init__.py
        └── pipelines.yaml                  # Dynamic pipeline config
```

#### 1.3 Create Dagster Configuration Files

Create `backend/orchestration/dagster.yaml`:

```yaml
# Dagster instance configuration
run_storage:
  module: dagster_postgres.run_storage
  class: PostgresRunStorage
  config:
    postgres_url:
      env: DAGSTER_POSTGRES_URL

event_log_storage:
  module: dagster_postgres.event_log
  class: PostgresEventLogStorage
  config:
    postgres_url:
      env: DAGSTER_POSTGRES_URL

schedule_storage:
  module: dagster_postgres.schedule_storage
  class: PostgresScheduleStorage
  config:
    postgres_url:
      env: DAGSTER_POSTGRES_URL

run_coordinator:
  module: dagster.core.run_coordinator
  class: QueuedRunCoordinator
  config:
    max_concurrent_runs: 25
    dequeue_interval_seconds: 5

concurrency:
  default_op_concurrency_limit: 15
  limits:
    - key: "spark_jobs"
      limit: 5
    - key: "dbt_runs"
      limit: 3
    - key: "database_writes"
      limit: 10
```

Create `backend/orchestration/workspace.yaml`:

```yaml
load_from:
  - python_module:
      module_name: orchestration.definitions
      location_name: novasight
      working_directory: /app
```

---

### Phase 2: Core Infrastructure (Week 2)

#### 2.1 Create Dagster GraphQL Client

Create `backend/app/domains/orchestration/infrastructure/dagster_client.py`:

```python
"""
NovaSight Orchestration Domain — Dagster Client
=================================================

GraphQL client for Dagster API.
Replaces AirflowClient with equivalent Dagster functionality.

Canonical location: ``app.domains.orchestration.infrastructure.dagster_client``
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from flask import current_app
import logging

logger = logging.getLogger(__name__)


@dataclass
class JobRun:
    """Represents a Dagster job run (equivalent to Airflow DagRun)."""
    job_name: str
    run_id: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    
    # Map to Airflow-compatible states for frontend compatibility
    @property
    def state(self) -> str:
        state_map = {
            "SUCCESS": "success",
            "FAILURE": "failed",
            "STARTED": "running",
            "QUEUED": "queued",
            "CANCELED": "cancelled",
        }
        return state_map.get(self.status, self.status.lower())


@dataclass
class AssetMaterialization:
    """Represents a Dagster asset materialization (equivalent to TaskInstance)."""
    asset_key: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    run_id: str
    
    @property
    def task_id(self) -> str:
        """Return asset key as task_id for frontend compatibility."""
        return self.asset_key
    
    @property
    def state(self) -> str:
        state_map = {
            "MATERIALIZED": "success",
            "FAILED": "failed",
            "IN_PROGRESS": "running",
            "PENDING": "queued",
        }
        return state_map.get(self.status, self.status.lower())


class DagsterClient:
    """
    Client for Dagster GraphQL API.
    
    Provides same interface as AirflowClient for seamless migration.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        tenant_id: Optional[str] = None,
        use_infrastructure_config: bool = True,
    ):
        self._host = host
        self._port = port
        self._tenant_id = tenant_id
        self._use_infrastructure_config = use_infrastructure_config
        self._client = None
        self._config_loaded = False
        self._loaded_settings: Dict[str, Any] = {}

    def _load_infrastructure_config(self):
        """Load settings from infrastructure config service."""
        if self._config_loaded or not self._use_infrastructure_config:
            return
        try:
            from app.services.infrastructure_config_service import InfrastructureConfigService
            config_service = InfrastructureConfigService()
            self._loaded_settings = config_service.get_effective_settings("dagster", self._tenant_id)
            self._config_loaded = True
        except Exception as e:
            logger.debug(f"Could not load infrastructure config: {e}")
            self._config_loaded = True

    @property
    def graphql_url(self) -> str:
        self._load_infrastructure_config()
        host = (
            self._host
            or self._loaded_settings.get("host")
            or current_app.config.get("DAGSTER_HOST", "localhost")
        )
        port = (
            self._port
            or self._loaded_settings.get("port")
            or current_app.config.get("DAGSTER_PORT", 3000)
        )
        return f"http://{host}:{port}/graphql"

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client

    def _execute_query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute GraphQL query."""
        response = self.client.post(
            self.graphql_url,
            json={"query": query, "variables": variables or {}},
        )
        response.raise_for_status()
        result = response.json()
        
        if "errors" in result:
            raise Exception(f"GraphQL errors: {result['errors']}")
        
        return result.get("data", {})

    # -------------------------------------------------------------------------
    # Job/Pipeline Management (replaces DAG management)
    # -------------------------------------------------------------------------

    def list_jobs(self, repository_name: str = "novasight") -> List[Dict[str, Any]]:
        """List all jobs (equivalent to list_dags)."""
        query = """
        query ListJobs($repositorySelector: RepositorySelector!) {
            repositoryOrError(repositorySelector: $repositorySelector) {
                ... on Repository {
                    jobs {
                        name
                        description
                        isJob
                    }
                }
            }
        }
        """
        variables = {
            "repositorySelector": {
                "repositoryName": repository_name,
                "repositoryLocationName": repository_name,
            }
        }
        data = self._execute_query(query, variables)
        repo = data.get("repositoryOrError", {})
        return repo.get("jobs", [])

    def get_job(self, job_name: str, repository_name: str = "novasight") -> Optional[Dict[str, Any]]:
        """Get job details (equivalent to get_dag)."""
        query = """
        query GetJob($selector: PipelineSelector!) {
            pipelineOrError(params: $selector) {
                ... on Pipeline {
                    name
                    description
                    solidHandles {
                        handleID
                        solid {
                            name
                            definition {
                                description
                            }
                        }
                    }
                }
            }
        }
        """
        variables = {
            "selector": {
                "pipelineName": job_name,
                "repositoryName": repository_name,
                "repositoryLocationName": repository_name,
            }
        }
        data = self._execute_query(query, variables)
        return data.get("pipelineOrError")

    def trigger_job(
        self,
        job_name: str,
        run_config: Dict[str, Any] = None,
        repository_name: str = "novasight",
    ) -> Dict[str, Any]:
        """Trigger a job run (equivalent to trigger_dag_run)."""
        query = """
        mutation LaunchRun($executionParams: ExecutionParams!) {
            launchRun(executionParams: $executionParams) {
                ... on LaunchRunSuccess {
                    run {
                        runId
                        status
                    }
                }
                ... on PythonError {
                    message
                    stack
                }
                ... on RunConfigValidationInvalid {
                    errors {
                        message
                    }
                }
            }
        }
        """
        variables = {
            "executionParams": {
                "selector": {
                    "pipelineName": job_name,
                    "repositoryName": repository_name,
                    "repositoryLocationName": repository_name,
                },
                "runConfigData": run_config or {},
            }
        }
        data = self._execute_query(query, variables)
        result = data.get("launchRun", {})
        
        if "run" in result:
            return {
                "success": True,
                "run_id": result["run"]["runId"],
                "status": result["run"]["status"],
            }
        else:
            error = result.get("message") or str(result.get("errors", []))
            return {"success": False, "error": error}

    def get_run_status(self, run_id: str) -> Optional[str]:
        """Get run status."""
        query = """
        query GetRunStatus($runId: ID!) {
            runOrError(runId: $runId) {
                ... on Run {
                    status
                }
            }
        }
        """
        data = self._execute_query(query, {"runId": run_id})
        run = data.get("runOrError", {})
        return run.get("status")

    def get_job_runs(
        self,
        job_name: str,
        limit: int = 25,
        repository_name: str = "novasight",
    ) -> List[JobRun]:
        """Get recent runs for a job (equivalent to get_dag_runs)."""
        query = """
        query GetJobRuns($selector: PipelineSelector!, $limit: Int!) {
            pipelineOrError(params: $selector) {
                ... on Pipeline {
                    runs(limit: $limit) {
                        runId
                        status
                        startTime
                        endTime
                    }
                }
            }
        }
        """
        variables = {
            "selector": {
                "pipelineName": job_name,
                "repositoryName": repository_name,
                "repositoryLocationName": repository_name,
            },
            "limit": limit,
        }
        data = self._execute_query(query, variables)
        pipeline = data.get("pipelineOrError", {})
        runs = pipeline.get("runs", [])
        
        return [
            JobRun(
                job_name=job_name,
                run_id=r["runId"],
                status=r["status"],
                start_time=datetime.fromisoformat(r["startTime"]) if r.get("startTime") else None,
                end_time=datetime.fromisoformat(r["endTime"]) if r.get("endTime") else None,
            )
            for r in runs
        ]

    def get_run_details(self, run_id: str) -> Dict[str, Any]:
        """Get detailed run information including asset materializations."""
        query = """
        query GetRunDetails($runId: ID!) {
            runOrError(runId: $runId) {
                ... on Run {
                    runId
                    status
                    startTime
                    endTime
                    pipelineName
                    assetMaterializations {
                        assetKey {
                            path
                        }
                        timestamp
                    }
                    stepStats {
                        stepKey
                        status
                        startTime
                        endTime
                    }
                }
            }
        }
        """
        data = self._execute_query(query, {"runId": run_id})
        return data.get("runOrError", {})

    def get_run_logs(self, run_id: str, step_key: str = None) -> str:
        """Get logs for a run (equivalent to get_task_logs)."""
        query = """
        query GetRunLogs($runId: ID!) {
            logsForRun(runId: $runId) {
                ... on EventConnection {
                    events {
                        ... on MessageEvent {
                            message
                            timestamp
                            stepKey
                        }
                    }
                }
            }
        }
        """
        data = self._execute_query(query, {"runId": run_id})
        events = data.get("logsForRun", {}).get("events", [])
        
        # Filter by step if provided
        if step_key:
            events = [e for e in events if e.get("stepKey") == step_key]
        
        # Format logs
        log_lines = []
        for event in events:
            if "message" in event:
                timestamp = event.get("timestamp", "")
                step = event.get("stepKey", "")
                message = event.get("message", "")
                log_lines.append(f"[{timestamp}] [{step}] {message}")
        
        return "\n".join(log_lines)

    # -------------------------------------------------------------------------
    # Schedule Management (replaces pause/unpause)
    # -------------------------------------------------------------------------

    def get_schedule_state(self, schedule_name: str, repository_name: str = "novasight") -> str:
        """Get schedule state (RUNNING, STOPPED)."""
        query = """
        query GetScheduleState($selector: ScheduleSelector!) {
            scheduleOrError(scheduleSelector: $selector) {
                ... on Schedule {
                    scheduleState {
                        status
                    }
                }
            }
        }
        """
        variables = {
            "selector": {
                "scheduleName": schedule_name,
                "repositoryName": repository_name,
                "repositoryLocationName": repository_name,
            }
        }
        data = self._execute_query(query, variables)
        schedule = data.get("scheduleOrError", {})
        return schedule.get("scheduleState", {}).get("status", "STOPPED")

    def start_schedule(self, schedule_name: str, repository_name: str = "novasight") -> Dict[str, Any]:
        """Start a schedule (equivalent to unpause_dag)."""
        query = """
        mutation StartSchedule($selector: ScheduleSelector!) {
            startSchedule(scheduleSelector: $selector) {
                ... on ScheduleStateResult {
                    scheduleState {
                        status
                    }
                }
                ... on PythonError {
                    message
                }
            }
        }
        """
        variables = {
            "selector": {
                "scheduleName": schedule_name,
                "repositoryName": repository_name,
                "repositoryLocationName": repository_name,
            }
        }
        data = self._execute_query(query, variables)
        result = data.get("startSchedule", {})
        
        if "scheduleState" in result:
            return {"success": True, "status": result["scheduleState"]["status"]}
        else:
            return {"success": False, "error": result.get("message", "Unknown error")}

    def stop_schedule(self, schedule_name: str, repository_name: str = "novasight") -> Dict[str, Any]:
        """Stop a schedule (equivalent to pause_dag)."""
        query = """
        mutation StopSchedule($selector: ScheduleSelector!) {
            stopRunningSchedule(scheduleSelector: $selector) {
                ... on ScheduleStateResult {
                    scheduleState {
                        status
                    }
                }
                ... on PythonError {
                    message
                }
            }
        }
        """
        variables = {
            "selector": {
                "scheduleName": schedule_name,
                "repositoryName": repository_name,
                "repositoryLocationName": repository_name,
            }
        }
        data = self._execute_query(query, variables)
        result = data.get("stopRunningSchedule", {})
        
        if "scheduleState" in result:
            return {"success": True, "status": result["scheduleState"]["status"]}
        else:
            return {"success": False, "error": result.get("message", "Unknown error")}

    def reload_code_location(self, location_name: str = "novasight") -> Dict[str, Any]:
        """Reload code location to pick up new definitions."""
        query = """
        mutation ReloadCodeLocation($repositoryLocationName: String!) {
            reloadRepositoryLocation(repositoryLocationName: $repositoryLocationName) {
                ... on WorkspaceLocationEntry {
                    name
                    loadStatus
                }
                ... on ReloadNotSupported {
                    message
                }
                ... on RepositoryLocationNotFound {
                    message
                }
                ... on PythonError {
                    message
                }
            }
        }
        """
        data = self._execute_query(query, {"repositoryLocationName": location_name})
        result = data.get("reloadRepositoryLocation", {})
        
        if result.get("loadStatus") == "LOADED":
            return {"success": True}
        else:
            return {"success": False, "error": result.get("message", "Reload failed")}
```

#### 2.2 Create Asset Factory

Create `backend/app/domains/orchestration/infrastructure/asset_factory.py`:

```python
"""
NovaSight Orchestration Domain — Asset Factory
================================================

Dynamically generates Dagster assets from pipeline configurations.
Replaces DAG file generation with in-memory asset definitions.

Canonical location: ``app.domains.orchestration.infrastructure.asset_factory``
"""

from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
import yaml
import logging

from dagster import (
    asset,
    AssetKey,
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    AssetsDefinition,
    AssetSpec,
    Output,
    DynamicPartitionsDefinition,
)

from app.domains.orchestration.domain.models import (
    DagConfig, TaskConfig, TaskType, ScheduleType,
)
from app.platform.tenant.isolation import TenantIsolationService

logger = logging.getLogger(__name__)


class AssetFactory:
    """
    Dynamically builds Dagster assets from DagConfig models.
    
    This replaces the Jinja2 template-based DAG generation with
    in-memory asset definitions that Dagster loads at runtime.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._isolation = TenantIsolationService(tenant_id)
        
        # Task type to asset builder mapping
        self._builders: Dict[TaskType, Callable] = {
            TaskType.SPARK_SUBMIT: self._build_spark_asset,
            TaskType.DBT_RUN: self._build_dbt_asset,
            TaskType.DBT_TEST: self._build_dbt_test_asset,
            TaskType.SQL_QUERY: self._build_sql_asset,
            TaskType.PYTHON_OPERATOR: self._build_python_asset,
            TaskType.BASH_OPERATOR: self._build_bash_asset,
            TaskType.EMAIL: self._build_email_asset,
            TaskType.HTTP_SENSOR: self._build_sensor_asset,
            TaskType.TIME_SENSOR: self._build_time_sensor_asset,
        }

    def build_assets_from_dag_config(self, dag_config: DagConfig) -> List[AssetsDefinition]:
        """
        Build Dagster assets from a DagConfig model.
        
        Each TaskConfig becomes an asset with proper dependencies.
        """
        assets = []
        group_name = f"tenant_{self.tenant_id}_{dag_config.dag_id}"
        
        for task in dag_config.tasks:
            builder = self._builders.get(task.task_type)
            if builder:
                asset_def = builder(
                    task=task,
                    dag_config=dag_config,
                    group_name=group_name,
                )
                if asset_def:
                    assets.append(asset_def)
            else:
                logger.warning(f"No builder for task type: {task.task_type}")
        
        return assets

    def _get_asset_deps(self, task: TaskConfig) -> List[AssetKey]:
        """Convert task dependencies to AssetKeys."""
        return [AssetKey(dep) for dep in (task.depends_on or [])]

    def _build_spark_asset(
        self,
        task: TaskConfig,
        dag_config: DagConfig,
        group_name: str,
    ) -> AssetsDefinition:
        """Build a Spark submit asset."""
        config = task.config or {}
        spark_app = config.get("spark_app_path", "")
        spark_args = config.get("spark_args", {})
        
        @asset(
            name=task.task_id,
            group_name=group_name,
            compute_kind="spark",
            deps=self._get_asset_deps(task),
            metadata={
                "tenant_id": self.tenant_id,
                "dag_id": dag_config.dag_id,
                "spark_app": spark_app,
            },
            op_tags={
                "dagster/concurrency_key": "spark_jobs",
                "tenant_id": self.tenant_id,
            },
        )
        def _spark_asset(context: AssetExecutionContext) -> MaterializeResult:
            context.log.info(f"Executing Spark job: {spark_app}")
            
            # Import spark resource
            spark = context.resources.spark
            session = spark.get_session()
            
            # Execute Spark application
            # This is a placeholder - actual implementation depends on your Spark setup
            context.log.info(f"Spark args: {spark_args}")
            
            return MaterializeResult(
                metadata={
                    "spark_app": MetadataValue.text(spark_app),
                    "status": MetadataValue.text("completed"),
                }
            )
        
        return _spark_asset

    def _build_dbt_asset(
        self,
        task: TaskConfig,
        dag_config: DagConfig,
        group_name: str,
    ) -> AssetsDefinition:
        """Build a dbt run asset."""
        config = task.config or {}
        models = config.get("models", [])
        tags = config.get("tags", [])
        full_refresh = config.get("full_refresh", False)
        
        select_arg = " ".join(models) if models else "*"
        if tags:
            select_arg = " ".join([f"tag:{t}" for t in tags])
        
        @asset(
            name=task.task_id,
            group_name=group_name,
            compute_kind="dbt",
            deps=self._get_asset_deps(task),
            metadata={
                "tenant_id": self.tenant_id,
                "dag_id": dag_config.dag_id,
                "dbt_select": select_arg,
            },
            op_tags={
                "dagster/concurrency_key": "dbt_runs",
                "tenant_id": self.tenant_id,
            },
        )
        def _dbt_asset(context: AssetExecutionContext) -> MaterializeResult:
            context.log.info(f"Running dbt models: {select_arg}")
            
            dbt = context.resources.dbt
            
            # Build dbt command
            cmd = ["run", "--select", select_arg]
            if full_refresh:
                cmd.append("--full-refresh")
            
            # Execute dbt
            result = dbt.cli(cmd, context=context)
            
            return MaterializeResult(
                metadata={
                    "models": MetadataValue.text(select_arg),
                    "full_refresh": MetadataValue.bool(full_refresh),
                }
            )
        
        return _dbt_asset

    def _build_dbt_test_asset(
        self,
        task: TaskConfig,
        dag_config: DagConfig,
        group_name: str,
    ) -> AssetsDefinition:
        """Build a dbt test asset."""
        config = task.config or {}
        select_arg = config.get("select", "*")
        
        @asset(
            name=task.task_id,
            group_name=group_name,
            compute_kind="dbt",
            deps=self._get_asset_deps(task),
            metadata={
                "tenant_id": self.tenant_id,
                "dag_id": dag_config.dag_id,
            },
            op_tags={"dagster/concurrency_key": "dbt_runs"},
        )
        def _dbt_test_asset(context: AssetExecutionContext) -> MaterializeResult:
            context.log.info(f"Running dbt tests: {select_arg}")
            
            dbt = context.resources.dbt
            result = dbt.cli(["test", "--select", select_arg], context=context)
            
            return MaterializeResult(
                metadata={"tests_passed": MetadataValue.bool(True)}
            )
        
        return _dbt_test_asset

    def _build_sql_asset(
        self,
        task: TaskConfig,
        dag_config: DagConfig,
        group_name: str,
    ) -> AssetsDefinition:
        """Build a SQL query asset."""
        config = task.config or {}
        query = config.get("query", "")
        database = config.get("database", "clickhouse")
        
        @asset(
            name=task.task_id,
            group_name=group_name,
            compute_kind="sql",
            deps=self._get_asset_deps(task),
            metadata={
                "tenant_id": self.tenant_id,
                "dag_id": dag_config.dag_id,
                "database": database,
            },
        )
        def _sql_asset(context: AssetExecutionContext) -> MaterializeResult:
            context.log.info(f"Executing SQL on {database}")
            
            # Execute query using appropriate resource
            if database == "clickhouse":
                db = context.resources.clickhouse
            else:
                db = context.resources.postgres
            
            result = db.execute(query)
            
            return MaterializeResult(
                metadata={"rows_affected": MetadataValue.int(result.rowcount)}
            )
        
        return _sql_asset

    def _build_python_asset(
        self,
        task: TaskConfig,
        dag_config: DagConfig,
        group_name: str,
    ) -> AssetsDefinition:
        """Build a Python operator asset."""
        config = task.config or {}
        callable_path = config.get("python_callable", "")
        op_kwargs = config.get("op_kwargs", {})
        
        @asset(
            name=task.task_id,
            group_name=group_name,
            compute_kind="python",
            deps=self._get_asset_deps(task),
            metadata={
                "tenant_id": self.tenant_id,
                "dag_id": dag_config.dag_id,
            },
        )
        def _python_asset(context: AssetExecutionContext) -> MaterializeResult:
            context.log.info(f"Executing Python callable: {callable_path}")
            
            # Dynamically import and execute callable
            module_path, func_name = callable_path.rsplit(".", 1)
            import importlib
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)
            
            result = func(**op_kwargs)
            
            return MaterializeResult(
                metadata={"callable": MetadataValue.text(callable_path)}
            )
        
        return _python_asset

    def _build_bash_asset(
        self,
        task: TaskConfig,
        dag_config: DagConfig,
        group_name: str,
    ) -> AssetsDefinition:
        """Build a Bash operator asset."""
        config = task.config or {}
        bash_command = config.get("bash_command", "")
        
        @asset(
            name=task.task_id,
            group_name=group_name,
            compute_kind="bash",
            deps=self._get_asset_deps(task),
            metadata={
                "tenant_id": self.tenant_id,
                "dag_id": dag_config.dag_id,
            },
        )
        def _bash_asset(context: AssetExecutionContext) -> MaterializeResult:
            import subprocess
            
            context.log.info(f"Executing bash: {bash_command[:50]}...")
            
            result = subprocess.run(
                bash_command,
                shell=True,
                capture_output=True,
                text=True,
            )
            
            if result.returncode != 0:
                raise Exception(f"Bash command failed: {result.stderr}")
            
            return MaterializeResult(
                metadata={
                    "exit_code": MetadataValue.int(result.returncode),
                    "stdout": MetadataValue.text(result.stdout[:1000]),
                }
            )
        
        return _bash_asset

    def _build_email_asset(
        self,
        task: TaskConfig,
        dag_config: DagConfig,
        group_name: str,
    ) -> AssetsDefinition:
        """Build an email notification asset."""
        config = task.config or {}
        
        @asset(
            name=task.task_id,
            group_name=group_name,
            compute_kind="email",
            deps=self._get_asset_deps(task),
        )
        def _email_asset(context: AssetExecutionContext) -> MaterializeResult:
            recipients = config.get("recipients", [])
            subject = config.get("subject", "NovaSight Notification")
            
            context.log.info(f"Sending email to {recipients}")
            
            # Email sending logic here
            
            return MaterializeResult(
                metadata={"recipients": MetadataValue.text(", ".join(recipients))}
            )
        
        return _email_asset

    def _build_sensor_asset(
        self,
        task: TaskConfig,
        dag_config: DagConfig,
        group_name: str,
    ) -> Optional[AssetsDefinition]:
        """HTTP sensors become Dagster sensors, not assets."""
        # Sensors are handled separately in schedule_factory.py
        logger.info(f"HTTP sensor {task.task_id} will be converted to Dagster sensor")
        return None

    def _build_time_sensor_asset(
        self,
        task: TaskConfig,
        dag_config: DagConfig,
        group_name: str,
    ) -> Optional[AssetsDefinition]:
        """Time sensors become part of schedule configuration."""
        logger.info(f"Time sensor {task.task_id} will be converted to schedule")
        return None
```

#### 2.3 Create Schedule Factory

Create `backend/app/domains/orchestration/infrastructure/schedule_factory.py`:

```python
"""
NovaSight Orchestration Domain — Schedule Factory
===================================================

Dynamically generates Dagster schedules from DagConfig models.

Canonical location: ``app.domains.orchestration.infrastructure.schedule_factory``
"""

from typing import List, Optional
from dagster import (
    ScheduleDefinition,
    DefaultScheduleStatus,
    define_asset_job,
    AssetSelection,
    RunRequest,
    ScheduleEvaluationContext,
    schedule,
)

from app.domains.orchestration.domain.models import DagConfig, ScheduleType
import logging

logger = logging.getLogger(__name__)


class ScheduleFactory:
    """
    Builds Dagster schedules from DagConfig models.
    
    Maps Airflow schedule_interval to Dagster ScheduleDefinition.
    """

    # Airflow preset to cron mapping
    PRESET_TO_CRON = {
        "hourly": "0 * * * *",
        "daily": "0 0 * * *",
        "weekly": "0 0 * * 0",
        "monthly": "0 0 1 * *",
        "@hourly": "0 * * * *",
        "@daily": "0 0 * * *",
        "@weekly": "0 0 * * 0",
        "@monthly": "0 0 1 * *",
        "@yearly": "0 0 1 1 *",
    }

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def build_schedule_from_dag_config(
        self,
        dag_config: DagConfig,
    ) -> Optional[ScheduleDefinition]:
        """
        Build a Dagster schedule from DagConfig.
        
        Returns None for manual schedules.
        """
        if dag_config.schedule_type == ScheduleType.MANUAL:
            logger.info(f"DAG {dag_config.dag_id} is manual, no schedule created")
            return None
        
        # Determine cron expression
        cron_schedule = self._get_cron_schedule(dag_config)
        if not cron_schedule:
            logger.warning(f"Could not determine cron schedule for {dag_config.dag_id}")
            return None
        
        # Create job for this pipeline's assets
        group_name = f"tenant_{self.tenant_id}_{dag_config.dag_id}"
        job_name = f"{dag_config.full_dag_id}_job"
        
        job = define_asset_job(
            name=job_name,
            selection=AssetSelection.groups(group_name),
            description=dag_config.description or f"Job for {dag_config.dag_id}",
            tags={
                "tenant_id": self.tenant_id,
                "dag_id": dag_config.dag_id,
            },
        )
        
        # Determine initial status
        initial_status = DefaultScheduleStatus.STOPPED
        if dag_config.status.value == "active":
            initial_status = DefaultScheduleStatus.RUNNING
        
        schedule_def = ScheduleDefinition(
            name=f"{dag_config.full_dag_id}_schedule",
            cron_schedule=cron_schedule,
            job=job,
            default_status=initial_status,
            execution_timezone=dag_config.timezone or "UTC",
        )
        
        logger.info(
            f"Created schedule for {dag_config.dag_id}: "
            f"cron={cron_schedule}, status={initial_status}"
        )
        
        return schedule_def

    def _get_cron_schedule(self, dag_config: DagConfig) -> Optional[str]:
        """Extract cron schedule from DagConfig."""
        if dag_config.schedule_type == ScheduleType.CRON:
            return dag_config.schedule_cron
        
        if dag_config.schedule_type == ScheduleType.PRESET:
            preset = dag_config.schedule_preset
            return self.PRESET_TO_CRON.get(preset)
        
        return None

    def build_job_from_dag_config(self, dag_config: DagConfig):
        """Build a job definition for manual triggering."""
        group_name = f"tenant_{self.tenant_id}_{dag_config.dag_id}"
        
        return define_asset_job(
            name=f"{dag_config.full_dag_id}_job",
            selection=AssetSelection.groups(group_name),
            description=dag_config.description or f"Job for {dag_config.dag_id}",
            tags={
                "tenant_id": self.tenant_id,
                "dag_id": dag_config.dag_id,
            },
        )
```

---

### Phase 3: Service Layer Migration (Week 3)

#### 3.1 Update DagService

Replace AirflowClient usage with DagsterClient in `dag_service.py`:

```python
# Key changes in dag_service.py

from app.domains.orchestration.infrastructure.dagster_client import DagsterClient
from app.domains.orchestration.infrastructure.asset_factory import AssetFactory
from app.domains.orchestration.infrastructure.schedule_factory import ScheduleFactory

class DagService:
    """Service for DAG configuration and Dagster integration."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.dagster_client = DagsterClient(tenant_id=tenant_id)  # Changed
        self.asset_factory = AssetFactory(tenant_id)  # New
        self.schedule_factory = ScheduleFactory(tenant_id)  # New
        self.validator = DagValidator()

    def deploy_dag(self, dag_id: str, deployed_by: str = None) -> Optional[Dict[str, Any]]:
        """
        Deploy DAG configuration to Dagster.
        
        Instead of writing DAG files, we:
        1. Update the pipeline config YAML
        2. Reload the Dagster code location
        """
        dag = self.get_dag(dag_id)
        if not dag:
            return None
        
        try:
            # Build assets and schedules (validation)
            assets = self.asset_factory.build_assets_from_dag_config(dag)
            schedule = self.schedule_factory.build_schedule_from_dag_config(dag)
            
            # Update config file for Dagster to pick up
            self._update_pipeline_config(dag)
            
            # Reload Dagster code location
            result = self.dagster_client.reload_code_location()
            
            if result.get("success"):
                # Update deployment tracking
                dag.deployed_at = datetime.utcnow()
                dag.deployed_version = dag.current_version
                dag.status = DagStatus.ACTIVE
                db.session.commit()
                
                return {
                    "success": True,
                    "message": f"DAG {dag_id} deployed to Dagster",
                    "job_name": f"{dag.full_dag_id}_job",
                    "schedule_name": f"{dag.full_dag_id}_schedule" if schedule else None,
                }
            else:
                return {"success": False, "error": result.get("error")}
                
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            return {"success": False, "error": str(e)}

    def trigger_dag(self, dag_id: str, conf: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Trigger a Dagster job run."""
        dag = self.get_dag(dag_id)
        if not dag:
            return None
        
        job_name = f"{dag.full_dag_id}_job"
        result = self.dagster_client.trigger_job(job_name, run_config=conf)
        
        return result

    def pause_dag(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """Stop the Dagster schedule."""
        dag = self.get_dag(dag_id)
        if not dag:
            return None
        
        schedule_name = f"{dag.full_dag_id}_schedule"
        result = self.dagster_client.stop_schedule(schedule_name)
        
        if result.get("success"):
            dag.status = DagStatus.PAUSED
            db.session.commit()
        
        return result

    def unpause_dag(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """Start the Dagster schedule."""
        dag = self.get_dag(dag_id)
        if not dag:
            return None
        
        schedule_name = f"{dag.full_dag_id}_schedule"
        result = self.dagster_client.start_schedule(schedule_name)
        
        if result.get("success"):
            dag.status = DagStatus.ACTIVE
            db.session.commit()
        
        return result

    def get_dag_runs(self, dag_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get recent runs from Dagster."""
        dag = self.get_dag(dag_id)
        if not dag:
            return []
        
        job_name = f"{dag.full_dag_id}_job"
        runs = self.dagster_client.get_job_runs(job_name, limit=limit)
        
        # Convert to dict format expected by frontend
        return [
            {
                "run_id": r.run_id,
                "dag_id": dag_id,
                "state": r.state,
                "execution_date": r.start_time.isoformat() if r.start_time else None,
                "start_date": r.start_time.isoformat() if r.start_time else None,
                "end_date": r.end_time.isoformat() if r.end_time else None,
            }
            for r in runs
        ]

    def get_task_logs(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
        try_number: int = 1,
    ) -> Optional[str]:
        """Get logs for a specific task/asset from Dagster."""
        return self.dagster_client.get_run_logs(run_id, step_key=task_id)
```

---

### Phase 4: Dagster Definitions (Week 3)

#### 4.1 Create Main Definitions Entry Point

Create `backend/orchestration/definitions.py`:

```python
"""
NovaSight Dagster Definitions
==============================

Main entry point for Dagster orchestration.
Dynamically loads pipelines from database at startup.
"""

from dagster import Definitions, EnvVar
from dagster_dbt import DbtCliResource
from dagster_postgres import PostgresResource
import os

from orchestration.resources.spark_resource import SparkResource
from orchestration.resources.clickhouse_resource import ClickHouseResource
from orchestration.assets import load_all_tenant_assets
from orchestration.schedules import load_all_schedules
from orchestration.sensors import all_sensors

# Load assets and schedules from database
all_assets = load_all_tenant_assets()
all_schedules = load_all_schedules()
all_jobs = []  # Jobs are created with schedules

# Resource definitions
resources = {
    "dbt": DbtCliResource(
        project_dir=EnvVar("DBT_PROJECT_DIR").get_value() or "/app/dbt",
        profiles_dir=EnvVar("DBT_PROFILES_DIR").get_value() or "/app/dbt",
    ),
    "spark": SparkResource(
        master=EnvVar("SPARK_MASTER").get_value() or "spark://spark-master:7077",
        app_name="NovaSight",
    ),
    "clickhouse": ClickHouseResource(
        host=EnvVar("CLICKHOUSE_HOST").get_value() or "clickhouse",
        port=int(EnvVar("CLICKHOUSE_PORT").get_value() or "9000"),
    ),
    "postgres": PostgresResource(
        connection_string=EnvVar("DATABASE_URL").get_value(),
    ),
}

defs = Definitions(
    assets=all_assets,
    schedules=all_schedules,
    sensors=all_sensors,
    resources=resources,
)
```

#### 4.2 Create Dynamic Asset Loader

Create `backend/orchestration/assets/__init__.py`:

```python
"""
Dynamic asset loader for NovaSight tenants.
"""

from typing import List
from dagster import AssetsDefinition
import logging

logger = logging.getLogger(__name__)


def load_all_tenant_assets() -> List[AssetsDefinition]:
    """
    Load assets for all active DAG configurations across tenants.
    
    This runs at Dagster startup and when code location is reloaded.
    """
    from app import create_app
    from app.extensions import db
    from app.domains.orchestration.domain.models import DagConfig, DagStatus
    from app.domains.orchestration.infrastructure.asset_factory import AssetFactory
    
    all_assets = []
    
    # Create Flask app context for database access
    app = create_app()
    with app.app_context():
        # Query all deployed DAGs
        deployed_dags = DagConfig.query.filter(
            DagConfig.status.in_([DagStatus.ACTIVE, DagStatus.PAUSED])
        ).all()
        
        logger.info(f"Loading assets for {len(deployed_dags)} DAG configurations")
        
        for dag in deployed_dags:
            try:
                factory = AssetFactory(str(dag.tenant_id))
                assets = factory.build_assets_from_dag_config(dag)
                all_assets.extend(assets)
                logger.info(f"Loaded {len(assets)} assets for {dag.dag_id}")
            except Exception as e:
                logger.error(f"Failed to load assets for {dag.dag_id}: {e}")
    
    return all_assets
```

---

### Phase 5: Docker Infrastructure (Week 4)

#### 5.1 Create Dagster Dockerfile

Create `docker/dagster/Dockerfile`:

```dockerfile
# NovaSight Dagster Dockerfile
# =============================
# Custom Dagster image with NovaSight dependencies

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    default-jdk \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set JAVA_HOME for Spark
ENV JAVA_HOME=/usr/lib/jvm/default-java
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Dagster packages
RUN pip install --no-cache-dir \
    dagster \
    dagster-webserver \
    dagster-graphql \
    dagster-postgres \
    dagster-dbt \
    dagster-pyspark \
    gql

# Copy application code
COPY backend/ /app/backend/
COPY dbt/ /app/dbt/

# Set environment
ENV DAGSTER_HOME=/app/dagster_home
ENV PYTHONPATH=/app/backend

# Create dagster home
RUN mkdir -p $DAGSTER_HOME

# Copy Dagster configuration
COPY backend/orchestration/dagster.yaml $DAGSTER_HOME/dagster.yaml
COPY backend/orchestration/workspace.yaml $DAGSTER_HOME/workspace.yaml

EXPOSE 3000

CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000"]
```

#### 5.2 Update docker-compose.yml

Replace Airflow services with Dagster:

```yaml
# Remove these services:
# - airflow-postgres
# - airflow-init
# - airflow-api-server
# - airflow-dag-processor
# - airflow-scheduler

# Add these services:
services:
  # ... existing services (postgres, clickhouse, redis, etc.)

  # ============================================
  # Dagster - Orchestration (replaces Airflow)
  # ============================================
  
  dagster-postgres:
    image: postgres:15-alpine
    container_name: novasight-dagster-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${DAGSTER_POSTGRES_USER:-dagster}
      POSTGRES_PASSWORD: ${DAGSTER_POSTGRES_PASSWORD:-dagster}
      POSTGRES_DB: ${DAGSTER_POSTGRES_DB:-dagster}
    volumes:
      - dagster_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DAGSTER_POSTGRES_USER:-dagster}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - novasight-network

  dagster-webserver:
    build:
      context: .
      dockerfile: docker/dagster/Dockerfile
    image: novasight-dagster:latest
    container_name: novasight-dagster-webserver
    restart: unless-stopped
    depends_on:
      dagster-postgres:
        condition: service_healthy
      spark-master:
        condition: service_healthy
    ports:
      - "3000:3000"
    environment:
      DAGSTER_POSTGRES_URL: postgresql://${DAGSTER_POSTGRES_USER:-dagster}:${DAGSTER_POSTGRES_PASSWORD:-dagster}@dagster-postgres/${DAGSTER_POSTGRES_DB:-dagster}
      DATABASE_URL: postgresql://${POSTGRES_USER:-novasight}:${POSTGRES_PASSWORD:-novasight}@postgres/${POSTGRES_DB:-novasight_platform}
      CLICKHOUSE_HOST: clickhouse
      CLICKHOUSE_PORT: 9000
      SPARK_MASTER: spark://spark-master:7077
      DBT_PROJECT_DIR: /app/dbt
      DBT_PROFILES_DIR: /app/dbt
    volumes:
      - ./backend:/app/backend
      - ./dbt:/app/dbt
      - dagster_home:/app/dagster_home
    command: ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000", "-w", "/app/dagster_home/workspace.yaml"]
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:3000/server_info"]
      interval: 30s
      timeout: 10s
      retries: 5
    networks:
      - novasight-network

  dagster-daemon:
    build:
      context: .
      dockerfile: docker/dagster/Dockerfile
    image: novasight-dagster:latest
    container_name: novasight-dagster-daemon
    restart: unless-stopped
    depends_on:
      dagster-webserver:
        condition: service_healthy
    environment:
      DAGSTER_POSTGRES_URL: postgresql://${DAGSTER_POSTGRES_USER:-dagster}:${DAGSTER_POSTGRES_PASSWORD:-dagster}@dagster-postgres/${DAGSTER_POSTGRES_DB:-dagster}
      DATABASE_URL: postgresql://${POSTGRES_USER:-novasight}:${POSTGRES_PASSWORD:-novasight}@postgres/${POSTGRES_DB:-novasight_platform}
      CLICKHOUSE_HOST: clickhouse
      CLICKHOUSE_PORT: 9000
      SPARK_MASTER: spark://spark-master:7077
      DBT_PROJECT_DIR: /app/dbt
      DBT_PROFILES_DIR: /app/dbt
    volumes:
      - ./backend:/app/backend
      - ./dbt:/app/dbt
      - dagster_home:/app/dagster_home
    command: ["dagster-daemon", "run", "-w", "/app/dagster_home/workspace.yaml"]
    networks:
      - novasight-network

volumes:
  dagster_postgres_data:
  dagster_home:
```

#### 5.3 Update Environment Variables

Add to `.env`:

```env
# Dagster Configuration
DAGSTER_POSTGRES_USER=dagster
DAGSTER_POSTGRES_PASSWORD=dagster
DAGSTER_POSTGRES_DB=dagster
DAGSTER_HOST=dagster-webserver
DAGSTER_PORT=3000
```

---

### Phase 6: Testing & Validation (Week 5)

#### 6.1 Create Migration Tests

Create `backend/tests/domains/orchestration/test_dagster_migration.py`:

```python
"""
Tests for Dagster migration.
Verifies that all Airflow functionality is preserved.
"""

import pytest
from unittest.mock import Mock, patch

from app.domains.orchestration.infrastructure.dagster_client import DagsterClient
from app.domains.orchestration.infrastructure.asset_factory import AssetFactory
from app.domains.orchestration.infrastructure.schedule_factory import ScheduleFactory


class TestDagsterClient:
    """Test DagsterClient methods match AirflowClient interface."""

    def test_trigger_job(self):
        client = DagsterClient(host="localhost", port=3000)
        # Mock GraphQL response
        with patch.object(client, '_execute_query') as mock_query:
            mock_query.return_value = {
                "launchRun": {
                    "run": {"runId": "test-run-123", "status": "STARTED"}
                }
            }
            result = client.trigger_job("test_job")
            assert result["success"] is True
            assert result["run_id"] == "test-run-123"

    def test_get_job_runs(self):
        client = DagsterClient(host="localhost", port=3000)
        with patch.object(client, '_execute_query') as mock_query:
            mock_query.return_value = {
                "pipelineOrError": {
                    "runs": [
                        {
                            "runId": "run-1",
                            "status": "SUCCESS",
                            "startTime": "2026-01-01T00:00:00",
                            "endTime": "2026-01-01T00:10:00",
                        }
                    ]
                }
            }
            runs = client.get_job_runs("test_job")
            assert len(runs) == 1
            assert runs[0].state == "success"


class TestAssetFactory:
    """Test asset generation from DagConfig."""

    def test_build_spark_asset(self):
        from app.domains.orchestration.domain.models import (
            DagConfig, TaskConfig, TaskType, ScheduleType, DagStatus
        )
        
        factory = AssetFactory("test-tenant")
        
        # Create mock DagConfig
        dag_config = Mock(spec=DagConfig)
        dag_config.dag_id = "test_dag"
        dag_config.tasks = [
            Mock(
                task_id="spark_task",
                task_type=TaskType.SPARK_SUBMIT,
                config={"spark_app_path": "/app/spark/job.py"},
                depends_on=[],
            )
        ]
        
        assets = factory.build_assets_from_dag_config(dag_config)
        assert len(assets) == 1

    def test_build_dbt_asset(self):
        factory = AssetFactory("test-tenant")
        
        dag_config = Mock()
        dag_config.dag_id = "dbt_pipeline"
        dag_config.tasks = [
            Mock(
                task_id="dbt_run",
                task_type=TaskType.DBT_RUN,
                config={"models": ["stg_orders"]},
                depends_on=[],
            )
        ]
        
        assets = factory.build_assets_from_dag_config(dag_config)
        assert len(assets) == 1


class TestScheduleFactory:
    """Test schedule generation from DagConfig."""

    def test_cron_schedule(self):
        factory = ScheduleFactory("test-tenant")
        
        dag_config = Mock()
        dag_config.dag_id = "scheduled_dag"
        dag_config.full_dag_id = "test-tenant_scheduled_dag"
        dag_config.schedule_type = ScheduleType.CRON
        dag_config.schedule_cron = "0 6 * * *"
        dag_config.status = Mock(value="active")
        dag_config.timezone = "UTC"
        dag_config.description = "Test DAG"
        
        schedule = factory.build_schedule_from_dag_config(dag_config)
        assert schedule is not None
        assert schedule.cron_schedule == "0 6 * * *"

    def test_manual_schedule_returns_none(self):
        factory = ScheduleFactory("test-tenant")
        
        dag_config = Mock()
        dag_config.dag_id = "manual_dag"
        dag_config.schedule_type = ScheduleType.MANUAL
        
        schedule = factory.build_schedule_from_dag_config(dag_config)
        assert schedule is None
```

#### 6.2 API Compatibility Tests

```python
"""
Test that API responses remain compatible after migration.
"""

import pytest
from app import create_app


class TestAPICompatibility:
    """Verify API contract is maintained."""

    @pytest.fixture
    def client(self):
        app = create_app(testing=True)
        with app.test_client() as client:
            yield client

    def test_list_dags_response_format(self, client, auth_headers):
        response = client.get("/api/v1/dags", headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        
        assert "dags" in data
        assert "pagination" in data

    def test_trigger_dag_response_format(self, client, auth_headers, deployed_dag):
        response = client.post(
            f"/api/v1/dags/{deployed_dag.dag_id}/trigger",
            headers=auth_headers,
            json={},
        )
        
        # Should return run_id even with Dagster backend
        data = response.json
        assert "success" in data
        if data["success"]:
            assert "run_id" in data

    def test_get_runs_response_format(self, client, auth_headers, deployed_dag):
        response = client.get(
            f"/api/v1/dags/{deployed_dag.dag_id}/runs",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json
        
        assert "runs" in data
        for run in data["runs"]:
            # Verify Airflow-compatible field names
            assert "run_id" in run
            assert "state" in run
            assert "execution_date" in run
```

---

### Phase 7: Cutover & Cleanup (Week 6)

#### 7.1 Migration Checklist

```markdown
## Pre-Migration Checklist

- [ ] All tests passing
- [ ] Dagster services healthy in staging
- [ ] All existing DAGs converted to Dagster assets
- [ ] All schedules verified working
- [ ] Frontend pages working with new backend
- [ ] Monitoring/alerting configured
- [ ] Team trained on Dagster UI
- [ ] Runbooks updated

## Migration Steps

1. [ ] Deploy Dagster services alongside Airflow
2. [ ] Configure backend to use Dagster client
3. [ ] Re-deploy all existing DAGs to Dagster
4. [ ] Verify all runs executing correctly
5. [ ] Switch frontend to use Dagster URLs (if any direct links)
6. [ ] Pause all Airflow DAGs
7. [ ] Monitor for 48 hours
8. [ ] Decommission Airflow services

## Rollback Plan

If issues occur:
1. Re-enable Airflow services
2. Revert backend to use AirflowClient
3. Resume Airflow DAGs
4. Investigate issues
```

#### 7.2 Files to Delete After Migration

```
# Delete after successful migration:
backend/app/domains/orchestration/infrastructure/legacy/
├── dag_generator.py
├── transformation_dag_generator.py
└── airflow_client.py

backend/app/templates/airflow/
├── dag_template.py.j2
├── spark_ingestion_dag.py.j2
├── transformation_dag.py.j2
├── pyspark_job_dag.py.j2
├── ... (all Jinja2 templates)

docker/airflow/
├── Dockerfile
├── Dockerfile.optimized
├── plugins/
├── dags/
└── scripts/

infrastructure/airflow/
├── dags/
├── plugins/
├── spark_apps/
└── logs/
```

#### 7.3 Update Scripts

Update `scripts/start-dev.bat`:

```batch
@echo off
REM Start Dagster services (replaces Airflow)

echo Starting Dagster services...
docker-compose up -d dagster-postgres
timeout /t 5 >nul
docker-compose up -d dagster-webserver dagster-daemon %BUILD_FLAG%

echo   Dagster UI:      http://localhost:3000
```

Update `scripts/deploy.sh`:

```bash
# Start Dagster
print_info "Starting Dagster services..."
$compose_cmd up -d dagster-postgres
sleep 5
$compose_cmd up -d dagster-webserver dagster-daemon

print_info "  Dagster:      http://localhost:3000"
```

---

## API Mapping Reference

| Airflow API | Dagster Equivalent | Notes |
|-------------|-------------------|-------|
| `GET /api/v2/dags` | GraphQL `repositoryOrError.jobs` | List pipelines |
| `POST /api/v2/dags/{id}/dagRuns` | GraphQL `launchRun` | Trigger run |
| `GET /api/v2/dags/{id}/dagRuns` | GraphQL `pipelineOrError.runs` | List runs |
| `PATCH /api/v2/dags/{id}` (pause) | GraphQL `stopRunningSchedule` | Pause schedule |
| `GET /api/v2/dagRuns/{id}/taskInstances` | GraphQL `runOrError.stepStats` | Task status |
| `GET /api/v2/taskInstances/{}/logs` | GraphQL `logsForRun` | Get logs |

---

## Timeline Summary

| Week | Phase | Deliverables |
|------|-------|-------------|
| 1 | Foundation | Dependencies, project structure, configs |
| 2 | Infrastructure | DagsterClient, AssetFactory, ScheduleFactory |
| 3 | Services | Updated DagService, PipelineService, definitions.py |
| 4 | Docker | Dagster containers, docker-compose updates |
| 5 | Testing | Migration tests, API compatibility tests |
| 6 | Cutover | Parallel run, validation, Airflow decommission |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Data loss during migration | Keep DagConfig in DB, only change orchestrator |
| API breaking changes | Maintain same response format, add compatibility layer |
| Schedule drift | Verify schedules in staging before cutover |
| Spark job failures | Test Spark integration thoroughly |
| dbt integration issues | Use dagster-dbt's native integration |

---

## Success Criteria

1. **Functional Parity**: All existing DAGs can be created, deployed, triggered, and monitored
2. **API Compatibility**: Frontend works without modification
3. **Performance**: No degradation in job execution time
4. **Reliability**: 99.9% schedule execution success rate
5. **Observability**: Full run history and logs available

---

## Post-Migration Benefits

- ✅ Asset-based lineage and observability
- ✅ Better dbt integration with `@dbt_assets`
- ✅ Faster code location reloads (no DAG file parsing)
- ✅ Reduced infrastructure (3 containers vs 5)
- ✅ Built-in asset caching and memoization
- ✅ Modern Python-first development experience
