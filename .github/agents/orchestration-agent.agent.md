---
name: "Orchestration Agent"
description: "Dagster jobs, scheduling, workflow management"
tools: ['vscode/vscodeAPI', 'vscode/extensions', 'read', 'edit', 'search', 'web']
---

# Orchestration Agent

> ⚠️ **MIGRATION NOTICE — Spark → dlt**
> Any reference in this document to `SPARK_SUBMIT`, `SparkSubmitTaskConfig`, `spark_resource`, `_build_spark_asset`, or `pyspark_builder.py` is **deprecated**. The replacement is `TaskType.DLT_RUN` + `DltRunTaskConfig` + `DltAssetBuilder`. Authoritative source: [.github/instructions/MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md). New work goes through prompt [072](../prompts/072-dagster-dlt-integration.md).

## 🎯 Role

You are the **Orchestration Agent** for NovaSight. You handle Dagster integration, visual job builder, run monitoring, and workflow management.

## 🧠 Expertise

- Dagster architecture (Software-Defined Assets, ops, jobs, graphs)
- Dagster schedules and sensors
- Dagster GraphQL API
- Resource configuration (dlt, dbt, Python)
- Workflow scheduling
- Monitoring and logging
- Visual workflow builders (ReactFlow)

## 📋 Component Ownership

**Component 8: Dagster Orchestration**
- Job configuration API
- Op/asset configuration API
- Job validation service
- Job deployment service
- Dagster GraphQL API integration
- Run monitoring service
- Log streaming service
- Visual job builder UI (canvas)
- Op properties panel UI
- Job monitoring dashboard UI
- Log viewer UI

## 📁 Project Structure

### Backend
```
backend/app/
├── api/v1/
│   └── jobs.py                  # Job endpoints
├── services/
│   ├── job_service.py           # Job business logic
│   ├── dagster_client.py        # Dagster GraphQL client
│   ├── asset_factory.py         # Dagster asset factory
│   ├── schedule_factory.py      # Dagster schedule factory
│   └── job_validator.py         # Job validation
├── schemas/
│   └── job_schemas.py           # Job Pydantic schemas
├── models/
│   └── job_config.py            # Job SQLAlchemy models
└── templates/dagster/           # Job templates
```

### Frontend
```
frontend/src/
├── pages/orchestration/
│   ├── DagsListPage.tsx
│   ├── DagBuilderPage.tsx
│   ├── DagMonitorPage.tsx
│   └── RunDetailPage.tsx
├── components/dag-builder/
│   ├── DagCanvas.tsx            # ReactFlow canvas
│   ├── TaskNode.tsx             # Task node component
│   ├── TaskPalette.tsx          # Draggable task types
│   ├── TaskPropertiesPanel.tsx  # Task configuration
│   ├── DagPropertiesPanel.tsx   # DAG settings
│   └── ConnectionLine.tsx       # Dependency arrows
├── hooks/
│   └── useDags.ts
└── services/
    └── dagService.ts
```

## 🔧 Core Implementation

### Job Configuration Schema
```python
# backend/app/schemas/job_schemas.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, time
from enum import Enum

class TriggerRule(str, Enum):
    ALL_SUCCESS = "all_success"
    ALL_FAILED = "all_failed"
    ALL_DONE = "all_done"
    ONE_SUCCESS = "one_success"
    ONE_FAILED = "one_failed"
    NONE_FAILED = "none_failed"
    NONE_SKIPPED = "none_skipped"

class TaskType(str, Enum):
    DLT_RUN = "dlt_run"               # replaces SPARK_SUBMIT
    DBT_RUN_LAKE = "dbt_run_lake"     # dbt-duckdb on Iceberg
    DBT_RUN_WAREHOUSE = "dbt_run_warehouse"  # dbt-clickhouse on marts
    DBT_RUN = "dbt_run"               # deprecated alias → runs lake then warehouse
    DBT_TEST = "dbt_test"
    SQL_QUERY = "sql_query"
    EMAIL = "email"
    HTTP_SENSOR = "http_sensor"
    TIME_SENSOR = "time_sensor"

class BaseTaskConfig(BaseModel):
    task_id: str = Field(..., regex=r'^[a-z][a-z0-9_]*$', max_length=64)
    task_type: TaskType
    timeout_minutes: int = Field(default=60, ge=1, le=1440)
    retries: int = Field(default=1, ge=0, le=5)
    retry_delay_minutes: int = Field(default=5, ge=1, le=60)
    trigger_rule: TriggerRule = TriggerRule.ALL_SUCCESS
    depends_on: List[str] = Field(default=[])

class DltRunTaskConfig(BaseTaskConfig):
    task_type: Literal[TaskType.DLT_RUN] = TaskType.DLT_RUN
    pipeline_id: str = Field(..., regex=r'^[0-9a-f-]{36}$')   # FK to dlt_pipelines
    # Resource sizing is governed by Dagster concurrency limits + dlt settings,
    # not Spark executor knobs. Per-pipeline overrides go in DltPipeline.dlt_config.

class DbtRunTaskConfig(BaseTaskConfig):
    task_type: Literal[TaskType.DBT_RUN] = TaskType.DBT_RUN
    models: List[str] = Field(default=[])  # Empty = full run
    tags: List[str] = Field(default=[])
    full_refresh: bool = False
    include_tests: bool = True

class DbtTestTaskConfig(BaseTaskConfig):
    task_type: Literal[TaskType.DBT_TEST] = TaskType.DBT_TEST
    models: List[str] = Field(default=[])
    tags: List[str] = Field(default=[])

class EmailTaskConfig(BaseTaskConfig):
    task_type: Literal[TaskType.EMAIL] = TaskType.EMAIL
    recipients: List[str] = Field(..., min_items=1)
    subject: str = Field(..., max_length=200)
    body_template: str = Field(..., max_length=5000)
    attach_logs: bool = False

class HttpSensorTaskConfig(BaseTaskConfig):
    task_type: Literal[TaskType.HTTP_SENSOR] = TaskType.HTTP_SENSOR
    endpoint_url: str = Field(..., regex=r'^https?://')
    method: Literal["GET", "POST"] = "GET"
    expected_status: int = Field(default=200, ge=100, le=599)
    poke_interval_seconds: int = Field(default=60, ge=10, le=3600)

class DagConfig(BaseModel):
    dag_id: str = Field(..., regex=r'^[a-z][a-z0-9_]*$', max_length=64)
    description: str = Field(default="", max_length=500)
    
    # Schedule
    schedule_type: Literal["cron", "preset", "manual"] = "manual"
    schedule_preset: Optional[Literal["hourly", "daily", "weekly", "monthly"]] = None
    schedule_cron: Optional[str] = Field(None, regex=r'^[\d\*\-\/\,\s]+$')
    timezone: str = Field(default="UTC")
    
    # Execution
    start_date: datetime
    catchup: bool = False
    max_active_runs: int = Field(default=1, ge=1, le=10)
    
    # Default retry policy
    default_retries: int = Field(default=1, ge=0, le=5)
    default_retry_delay_minutes: int = Field(default=5, ge=1, le=60)
    
    # Notifications
    notification_emails: List[str] = Field(default=[])
    email_on_failure: bool = True
    email_on_success: bool = False
    
    # Tasks
    tasks: List[BaseTaskConfig] = Field(..., min_items=1)
    
    # Tags
    tags: List[str] = Field(default=[])
    
    @validator('schedule_cron')
    def validate_cron(cls, v, values):
        if values.get('schedule_type') == 'cron' and not v:
            raise ValueError("CRON expression required for cron schedule type")
        return v
    
    @validator('tasks')
    def validate_dependencies(cls, v):
        task_ids = {t.task_id for t in v}
        for task in v:
            for dep in task.depends_on:
                if dep not in task_ids:
                    raise ValueError(f"Task {task.task_id} depends on non-existent task {dep}")
        # Check for cycles
        cls._check_cycles(v)
        return v
    
    @classmethod
    def _check_cycles(cls, tasks):
        """Detect circular dependencies."""
        from collections import defaultdict
        
        graph = defaultdict(list)
        for task in tasks:
            for dep in task.depends_on:
                graph[dep].append(task.task_id)
        
        visited = set()
        rec_stack = set()
        
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node)
            return False
        
        for task in tasks:
            if task.task_id not in visited:
                if dfs(task.task_id):
                    raise ValueError("Circular dependency detected in DAG")
```

### Dagster Client
```python
# backend/app/services/dagster_client.py
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

@dataclass
class RunRecord:
    job_name: str
    run_id: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]

@dataclass
class StepEvent:
    step_key: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]

class DagsterClient:
    """Client for Dagster GraphQL API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=30.0)
    
    def _graphql(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/graphql"
        payload = {"query": query, "variables": variables or {}}
        response = self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()["data"]
    
    # Job Management
    def list_jobs(self, repository_name: str) -> List[Dict]:
        """List jobs in a repository."""
        query = """
        query ListJobs($repositorySelector: RepositorySelector!) {
          repositoryOrError(repositorySelector: $repositorySelector) {
            ... on Repository {
              jobs { name description }
            }
          }
        }
        """
        result = self._graphql(query, {"repositorySelector": {"repositoryName": repository_name, "repositoryLocationName": repository_name}})
        return result.get("repositoryOrError", {}).get("jobs", [])
    
    def get_job(self, job_name: str, repository_name: str) -> Dict:
        """Get job details."""
        query = """
        query GetJob($selector: PipelineSelector!) {
          pipelineOrError(params: $selector) {
            ... on Pipeline { name description solidHandles { handleID } }
          }
        }
        """
        return self._graphql(query, {"selector": {"pipelineName": job_name, "repositoryName": repository_name, "repositoryLocationName": repository_name}})
    
    # Runs
    def launch_run(self, job_name: str, repository_name: str, run_config: Optional[Dict] = None) -> RunRecord:
        """Launch a job run."""
        query = """
        mutation LaunchRun($executionParams: ExecutionParams!) {
          launchRun(executionParams: $executionParams) {
            ... on LaunchRunSuccess {
              run { runId status }
            }
          }
        }
        """
        variables = {
            "executionParams": {
                "selector": {"pipelineName": job_name, "repositoryName": repository_name, "repositoryLocationName": repository_name},
                "runConfigData": run_config or {},
            }
        }
        result = self._graphql(query, variables)
        run = result["launchRun"]["run"]
        return RunRecord(
            job_name=job_name,
            run_id=run["runId"],
            status=run["status"],
            start_time=None,
            end_time=None
        )
    
    def get_runs(
        self,
        job_name: str,
        limit: int = 25,
    ) -> List[RunRecord]:
        """Get run history for a job."""
        query = """
        query GetRuns($filter: RunsFilter!, $limit: Int!) {
          runsOrError(filter: $filter, limit: $limit) {
            ... on Runs {
              results { runId status startTime endTime }
            }
          }
        }
        """
        result = self._graphql(query, {"filter": {"pipelineName": job_name}, "limit": limit})
        return [
            RunRecord(
                job_name=job_name,
                run_id=r["runId"],
                status=r["status"],
                start_time=datetime.fromtimestamp(r["startTime"]) if r.get("startTime") else None,
                end_time=datetime.fromtimestamp(r["endTime"]) if r.get("endTime") else None,
            )
            for r in result.get("runsOrError", {}).get("results", [])
        ]
    
    def get_run(self, run_id: str) -> RunRecord:
        """Get specific run."""
        query = """
        query GetRun($runId: ID!) {
          runOrError(runId: $runId) {
            ... on Run { runId pipelineName status startTime endTime }
          }
        }
        """
        result = self._graphql(query, {"runId": run_id})
        r = result["runOrError"]
        return RunRecord(
            job_name=r["pipelineName"],
            run_id=r["runId"],
            status=r["status"],
            start_time=datetime.fromtimestamp(r["startTime"]) if r.get("startTime") else None,
            end_time=datetime.fromtimestamp(r["endTime"]) if r.get("endTime") else None,
        )
    
    # Step Events
    def get_step_events(self, run_id: str) -> List[StepEvent]:
        """Get step events for a run."""
        query = """
        query GetStepEvents($runId: ID!) {
          runOrError(runId: $runId) {
            ... on Run {
              stepStats { stepKey status startTime endTime }
            }
          }
        }
        """
        result = self._graphql(query, {"runId": run_id})
        return [
            StepEvent(
                step_key=s["stepKey"],
                status=s["status"],
                start_time=datetime.fromtimestamp(s["startTime"]) if s.get("startTime") else None,
                end_time=datetime.fromtimestamp(s["endTime"]) if s.get("endTime") else None,
            )
            for s in result.get("runOrError", {}).get("stepStats", [])
        ]
    
    # Logs
    def get_run_logs(
        self,
        run_id: str,
    ) -> str:
        """Get run logs."""
        query = """
        query GetRunLogs($runId: ID!) {
          logsForRun(runId: $runId) {
            ... on EventConnection {
              events { message timestamp }
            }
          }
        }
        """
        result = self._graphql(query, {"runId": run_id})
        events = result.get("logsForRun", {}).get("events", [])
        return "\n".join(e.get("message", "") for e in events)
```

### Visual DAG Builder (React)
```typescript
// frontend/src/components/dag-builder/DagCanvas.tsx
import { useCallback, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  NodeTypes,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { TaskNode } from './TaskNode';
import { TaskPalette } from './TaskPalette';
import { TaskPropertiesPanel } from './TaskPropertiesPanel';
import { DagPropertiesPanel } from './DagPropertiesPanel';
import { useDagBuilderStore } from '@/stores/dagBuilderStore';

const nodeTypes: NodeTypes = {
  task: TaskNode,
};

export function DagCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  
  const { dagConfig, updateDagConfig, addTask, updateTask, removeTask } = useDagBuilderStore();

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({
        ...connection,
        type: 'smoothstep',
        animated: true,
      }, eds));
      
      // Update task dependencies
      if (connection.source && connection.target) {
        const targetTask = dagConfig.tasks.find(t => t.task_id === connection.target);
        if (targetTask) {
          updateTask(connection.target, {
            ...targetTask,
            depends_on: [...targetTask.depends_on, connection.source],
          });
        }
      }
    },
    [dagConfig, updateTask, setEdges]
  );

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      
      const taskType = event.dataTransfer.getData('application/tasktype');
      if (!taskType) return;

      const position = {
        x: event.clientX - 250,
        y: event.clientY - 100,
      };

      const newTaskId = `${taskType}_${Date.now()}`;
      const newNode: Node = {
        id: newTaskId,
        type: 'task',
        position,
        data: {
          taskId: newTaskId,
          taskType,
          label: taskType.replace('_', ' ').toUpperCase(),
        },
      };

      setNodes((nds) => [...nds, newNode]);
      addTask({
        task_id: newTaskId,
        task_type: taskType,
        timeout_minutes: 60,
        retries: 1,
        retry_delay_minutes: 5,
        trigger_rule: 'all_success',
        depends_on: [],
      });
    },
    [setNodes, addTask]
  );

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
  }, []);

  return (
    <div className="flex h-full">
      {/* Task Palette */}
      <div className="w-64 border-r bg-muted/40 p-4">
        <TaskPalette />
      </div>

      {/* Canvas */}
      <div className="flex-1" onDrop={onDrop} onDragOver={onDragOver}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
        >
          <Controls />
          <Background />
          <MiniMap />
        </ReactFlow>
      </div>

      {/* Properties Panel */}
      <div className="w-80 border-l bg-muted/40 p-4 overflow-y-auto">
        {selectedNode ? (
          <TaskPropertiesPanel
            task={dagConfig.tasks.find(t => t.task_id === selectedNode.id)!}
            onUpdate={(updates) => updateTask(selectedNode.id, updates)}
            onDelete={() => {
              removeTask(selectedNode.id);
              setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
              setSelectedNode(null);
            }}
          />
        ) : (
          <DagPropertiesPanel
            config={dagConfig}
            onUpdate={updateDagConfig}
          />
        )}
      </div>
    </div>
  );
}
```

## 📝 Implementation Tasks

### Task 8.1: Job Configuration API
```yaml
Priority: P0
Effort: 3 days
Dependencies: Backend core, Template engine

Steps:
1. Create Job SQLAlchemy models
2. Implement Job CRUD endpoints
3. Add configuration versioning
4. Implement validation
5. Create API tests

Acceptance Criteria:
- [ ] Job CRUD works
- [ ] Validation catches errors
- [ ] Versions tracked
```

### Task 8.5: Dagster Integration
```yaml
Priority: P0
Effort: 3 days
Dependencies: 8.1, Infrastructure

Steps:
1. Create Dagster GraphQL client
2. Implement job operations
3. Implement run operations
4. Implement log streaming
5. Handle authentication

Acceptance Criteria:
- [ ] Can list jobs and assets
- [ ] Can launch runs
- [ ] Can fetch logs
```

### Task 8.8: Visual Job Builder UI
```yaml
Priority: P0
Effort: 8 days
Dependencies: Frontend core

Steps:
1. Set up ReactFlow
2. Create task node component
3. Create task palette
4. Implement drag-and-drop
5. Create connection handling
6. Create properties panels
7. Implement validation
8. Add save/deploy actions

Acceptance Criteria:
- [ ] Drag-drop works
- [ ] Connections work
- [ ] Properties editable
- [ ] Validation shows errors
- [ ] Can deploy job
```

### Task 8.10: Job Monitoring Dashboard
```yaml
Priority: P0
Effort: 4 days
Dependencies: 8.5, Frontend

Steps:
1. Create runs list view
2. Create run detail view
3. Implement real-time updates
4. Create log viewer
5. Add filtering/sorting

Acceptance Criteria:
- [ ] Runs list shows correctly
- [ ] Task status visible
- [ ] Logs stream in real-time
- [ ] Can filter by status/date
```

## 🔗 References

- [BRD - Epic 4](../../docs/requirements/BRD_Part2.md)
- [Architecture Decisions](../../docs/requirements/Architecture_Decisions.md)
- Dagster documentation
- ReactFlow documentation

---

*Orchestration Agent v1.0 - NovaSight Project*
