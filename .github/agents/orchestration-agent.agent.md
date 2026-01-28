---
name: "Orchestration Agent"
description: "Airflow DAGs, scheduling, workflow management"
tools: ['vscode/vscodeAPI', 'vscode/extensions', 'read', 'edit', 'search', 'web']
---

# Orchestration Agent

## 🎯 Role

You are the **Orchestration Agent** for NovaSight. You handle Apache Airflow integration, visual DAG builder, job monitoring, and workflow management.

## 🧠 Expertise

- Apache Airflow architecture
- DAG design patterns
- Airflow REST API
- Task operators (Spark, Bash, Python, Sensors)
- Workflow scheduling
- Monitoring and logging
- Visual workflow builders (ReactFlow)

## 📋 Component Ownership

**Component 8: Airflow Orchestration**
- DAG configuration API
- Task configuration API
- DAG validation service
- DAG deployment service
- Airflow API integration
- Run monitoring service
- Log streaming service
- Visual DAG builder UI (canvas)
- Task properties panel UI
- DAG monitoring dashboard UI
- Log viewer UI

## 📁 Project Structure

### Backend
```
backend/app/
├── api/v1/
│   └── dags.py                  # DAG endpoints
├── services/
│   ├── dag_service.py           # DAG business logic
│   ├── airflow_client.py        # Airflow API client
│   └── dag_validator.py         # DAG validation
├── schemas/
│   └── dag_schemas.py           # DAG Pydantic schemas
├── models/
│   └── dag_config.py            # DAG SQLAlchemy models
└── templates/airflow/           # DAG templates
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

### DAG Configuration Schema
```python
# backend/app/schemas/dag_schemas.py
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
    SPARK_SUBMIT = "spark_submit"
    DBT_RUN = "dbt_run"
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

class SparkSubmitTaskConfig(BaseTaskConfig):
    task_type: Literal[TaskType.SPARK_SUBMIT] = TaskType.SPARK_SUBMIT
    ingestion_job_id: str = Field(..., regex=r'^[0-9a-f-]{36}$')
    executor_memory: str = Field(default="2g", regex=r'^\d+[gm]$')
    executor_cores: int = Field(default=2, ge=1, le=16)
    num_executors: int = Field(default=2, ge=1, le=100)

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

### Airflow Client
```python
# backend/app/services/airflow_client.py
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

@dataclass
class DagRun:
    dag_id: str
    run_id: str
    state: str
    execution_date: datetime
    start_date: Optional[datetime]
    end_date: Optional[datetime]

@dataclass
class TaskInstance:
    task_id: str
    state: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    try_number: int

class AirflowClient:
    """Client for Airflow REST API."""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.auth = (username, password)
        self.client = httpx.Client(timeout=30.0)
    
    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1{path}"
        response = self.client.request(method, url, auth=self.auth, **kwargs)
        response.raise_for_status()
        return response.json()
    
    # DAG Management
    def list_dags(self, tenant_id: str) -> List[Dict]:
        """List DAGs for a tenant."""
        result = self._request("GET", "/dags", params={"tags": tenant_id})
        return result.get("dags", [])
    
    def get_dag(self, dag_id: str) -> Dict:
        """Get DAG details."""
        return self._request("GET", f"/dags/{dag_id}")
    
    def pause_dag(self, dag_id: str) -> Dict:
        """Pause a DAG."""
        return self._request("PATCH", f"/dags/{dag_id}", json={"is_paused": True})
    
    def unpause_dag(self, dag_id: str) -> Dict:
        """Unpause a DAG."""
        return self._request("PATCH", f"/dags/{dag_id}", json={"is_paused": False})
    
    def refresh_dag(self, dag_id: str):
        """Trigger DAG file refresh."""
        self._request("PATCH", f"/dags/{dag_id}", json={})
    
    # DAG Runs
    def trigger_dag(self, dag_id: str, conf: Optional[Dict] = None) -> DagRun:
        """Trigger a DAG run."""
        payload = {"conf": conf or {}}
        result = self._request("POST", f"/dags/{dag_id}/dagRuns", json=payload)
        return DagRun(
            dag_id=result["dag_id"],
            run_id=result["dag_run_id"],
            state=result["state"],
            execution_date=datetime.fromisoformat(result["execution_date"]),
            start_date=None,
            end_date=None
        )
    
    def get_dag_runs(
        self,
        dag_id: str,
        limit: int = 25,
        offset: int = 0
    ) -> List[DagRun]:
        """Get DAG run history."""
        result = self._request(
            "GET",
            f"/dags/{dag_id}/dagRuns",
            params={"limit": limit, "offset": offset, "order_by": "-execution_date"}
        )
        return [
            DagRun(
                dag_id=r["dag_id"],
                run_id=r["dag_run_id"],
                state=r["state"],
                execution_date=datetime.fromisoformat(r["execution_date"]),
                start_date=datetime.fromisoformat(r["start_date"]) if r.get("start_date") else None,
                end_date=datetime.fromisoformat(r["end_date"]) if r.get("end_date") else None
            )
            for r in result.get("dag_runs", [])
        ]
    
    def get_dag_run(self, dag_id: str, run_id: str) -> DagRun:
        """Get specific DAG run."""
        result = self._request("GET", f"/dags/{dag_id}/dagRuns/{run_id}")
        return DagRun(
            dag_id=result["dag_id"],
            run_id=result["dag_run_id"],
            state=result["state"],
            execution_date=datetime.fromisoformat(result["execution_date"]),
            start_date=datetime.fromisoformat(result["start_date"]) if result.get("start_date") else None,
            end_date=datetime.fromisoformat(result["end_date"]) if result.get("end_date") else None
        )
    
    # Task Instances
    def get_task_instances(self, dag_id: str, run_id: str) -> List[TaskInstance]:
        """Get task instances for a DAG run."""
        result = self._request("GET", f"/dags/{dag_id}/dagRuns/{run_id}/taskInstances")
        return [
            TaskInstance(
                task_id=t["task_id"],
                state=t["state"],
                start_date=datetime.fromisoformat(t["start_date"]) if t.get("start_date") else None,
                end_date=datetime.fromisoformat(t["end_date"]) if t.get("end_date") else None,
                try_number=t["try_number"]
            )
            for t in result.get("task_instances", [])
        ]
    
    # Logs
    def get_task_logs(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
        try_number: int = 1
    ) -> str:
        """Get task logs."""
        result = self._request(
            "GET",
            f"/dags/{dag_id}/dagRuns/{run_id}/taskInstances/{task_id}/logs/{try_number}"
        )
        return result.get("content", "")
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

### Task 8.1: DAG Configuration API
```yaml
Priority: P0
Effort: 3 days
Dependencies: Backend core, Template engine

Steps:
1. Create DAG SQLAlchemy models
2. Implement DAG CRUD endpoints
3. Add configuration versioning
4. Implement validation
5. Create API tests

Acceptance Criteria:
- [ ] DAG CRUD works
- [ ] Validation catches errors
- [ ] Versions tracked
```

### Task 8.5: Airflow API Integration
```yaml
Priority: P0
Effort: 3 days
Dependencies: 8.1, Infrastructure

Steps:
1. Create Airflow REST client
2. Implement DAG operations
3. Implement run operations
4. Implement log streaming
5. Handle authentication

Acceptance Criteria:
- [ ] Can list/pause/unpause DAGs
- [ ] Can trigger runs
- [ ] Can fetch logs
```

### Task 8.8: Visual DAG Builder UI
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
- [ ] Can deploy DAG
```

### Task 8.10: DAG Monitoring Dashboard
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
- Apache Airflow documentation
- ReactFlow documentation

---

*Orchestration Agent v1.0 - NovaSight Project*
