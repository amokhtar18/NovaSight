"""
NovaSight Orchestration Domain — DAG Schemas
==============================================

Pydantic schemas for DAG configuration validation.

Canonical location: ``app.domains.orchestration.schemas.dag_schemas``
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class TriggerRule(str, Enum):
    """Task trigger rule enumeration."""
    ALL_SUCCESS = "all_success"
    ALL_FAILED = "all_failed"
    ALL_DONE = "all_done"
    ONE_SUCCESS = "one_success"
    ONE_FAILED = "one_failed"
    NONE_FAILED = "none_failed"
    NONE_SKIPPED = "none_skipped"


class TaskType(str, Enum):
    """
    Task type enumeration.

    Orchestrator schedules **only dlt and dbt jobs**. Keep in sync with the
    SQLAlchemy ``TaskType`` enum in
    ``app.domains.orchestration.domain.models``.
    """
    DLT_RUN = "dlt_run"
    DBT_RUN = "dbt_run"
    DBT_TEST = "dbt_test"
    DBT_RUN_LAKE = "dbt_run_lake"
    DBT_RUN_WAREHOUSE = "dbt_run_warehouse"


class TaskConfigCreate(BaseModel):
    """Task configuration creation schema."""

    task_id: str = Field(..., min_length=1, max_length=64, pattern=r'^[a-z][a-z0-9_]*$')
    task_type: TaskType
    config: Dict[str, Any] = Field(default_factory=dict)
    timeout_minutes: int = Field(default=60, ge=1, le=1440)
    retries: int = Field(default=1, ge=0, le=5)
    retry_delay_minutes: int = Field(default=5, ge=1, le=60)
    trigger_rule: TriggerRule = TriggerRule.ALL_SUCCESS
    depends_on: List[str] = Field(default_factory=list)
    position: Optional[Dict[str, int]] = Field(default=None)


class DltRunTaskConfig(TaskConfigCreate):
    """dlt pipeline run task configuration."""

    task_type: Literal[TaskType.DLT_RUN] = TaskType.DLT_RUN
    config: Dict[str, Any] = Field(
        ...,
        description="dlt configuration including pipeline_id, notifications, etc.",
    )


class DbtRunTaskConfig(TaskConfigCreate):
    """dbt run task configuration."""

    task_type: Literal[TaskType.DBT_RUN] = TaskType.DBT_RUN
    config: Dict[str, Any] = Field(
        default_factory=lambda: {"models": [], "tags": [], "full_refresh": False}
    )


class DbtTestTaskConfig(TaskConfigCreate):
    """dbt test task configuration."""

    task_type: Literal[TaskType.DBT_TEST] = TaskType.DBT_TEST
    config: Dict[str, Any] = Field(
        default_factory=lambda: {"select": "*"},
    )


class DagConfigCreate(BaseModel):
    """DAG configuration creation schema."""

    dag_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r'^[a-z][a-z0-9_]*$',
        description="Unique DAG identifier",
    )
    description: str = Field(default="", max_length=500)

    # Schedule
    schedule_type: Literal["cron", "preset", "manual"] = "manual"
    schedule_preset: Optional[Literal["hourly", "daily", "weekly", "monthly"]] = None
    schedule_cron: Optional[str] = Field(None, pattern=r'^[\d\*\-\/\,\s]+$')
    timezone: str = Field(default="UTC")

    # Execution
    start_date: Optional[datetime] = None
    catchup: bool = False
    max_active_runs: int = Field(default=1, ge=1, le=10)

    # Default retry policy
    default_retries: int = Field(default=1, ge=0, le=5)
    default_retry_delay_minutes: int = Field(default=5, ge=1, le=60)

    # Notifications
    notification_emails: List[str] = Field(default_factory=list)
    email_on_failure: bool = True
    email_on_success: bool = False

    # Tasks
    tasks: List[TaskConfigCreate] = Field(..., min_length=1)

    # Tags
    tags: List[str] = Field(default_factory=list)

    @field_validator('schedule_cron')
    @classmethod
    def validate_cron(cls, v, info):
        if info.data.get('schedule_type') == 'cron' and not v:
            raise ValueError("CRON expression required for cron schedule type")
        return v

    @field_validator('tasks')
    @classmethod
    def validate_tasks(cls, v):
        task_ids = [t.task_id for t in v]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Task IDs must be unique")
        for task in v:
            for dep in task.depends_on:
                if dep not in task_ids:
                    raise ValueError(
                        f"Task {task.task_id} depends on non-existent task {dep}"
                    )
        return v


class DagConfigUpdate(BaseModel):
    """DAG configuration update schema."""

    description: Optional[str] = Field(None, max_length=500)

    # Schedule
    schedule_type: Optional[Literal["cron", "preset", "manual"]] = None
    schedule_preset: Optional[Literal["hourly", "daily", "weekly", "monthly"]] = None
    schedule_cron: Optional[str] = Field(None, pattern=r'^[\d\*\-\/\,\s]+$')
    timezone: Optional[str] = None

    # Execution
    start_date: Optional[datetime] = None
    catchup: Optional[bool] = None
    max_active_runs: Optional[int] = Field(None, ge=1, le=10)

    # Retry policy
    default_retries: Optional[int] = Field(None, ge=0, le=5)
    default_retry_delay_minutes: Optional[int] = Field(None, ge=1, le=60)

    # Notifications
    notification_emails: Optional[List[str]] = None
    email_on_failure: Optional[bool] = None
    email_on_success: Optional[bool] = None

    # Tasks (optional, full replacement if provided)
    tasks: Optional[List[TaskConfigCreate]] = None

    # Tags
    tags: Optional[List[str]] = None

    # Change description for versioning
    change_description: Optional[str] = None


class DagConfigResponse(BaseModel):
    """DAG configuration response schema."""

    id: str
    tenant_id: str
    dag_id: str
    description: str
    current_version: int
    schedule_type: str
    schedule_cron: Optional[str]
    schedule_preset: Optional[str]
    timezone: str
    start_date: Optional[datetime]
    catchup: bool
    max_active_runs: int
    default_retries: int
    default_retry_delay_minutes: int
    notification_emails: List[str]
    email_on_failure: bool
    email_on_success: bool
    tags: List[str]
    status: str
    deployed_at: Optional[datetime]
    deployed_version: Optional[int]
    created_at: datetime
    updated_at: datetime
    created_by: str
    tasks: List[Dict[str, Any]]
