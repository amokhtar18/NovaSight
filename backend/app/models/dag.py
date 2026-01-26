"""
NovaSight DAG Configuration Models
==================================

Apache Airflow DAG configuration and versioning models.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from app.extensions import db
import enum


class DagStatus(enum.Enum):
    """DAG status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    ERROR = "error"


class ScheduleType(enum.Enum):
    """Schedule type enumeration."""
    MANUAL = "manual"
    CRON = "cron"
    PRESET = "preset"


class TriggerRule(enum.Enum):
    """Task trigger rule enumeration."""
    ALL_SUCCESS = "all_success"
    ALL_FAILED = "all_failed"
    ALL_DONE = "all_done"
    ONE_SUCCESS = "one_success"
    ONE_FAILED = "one_failed"
    NONE_FAILED = "none_failed"
    NONE_SKIPPED = "none_skipped"


class TaskType(enum.Enum):
    """Task type enumeration."""
    SPARK_SUBMIT = "spark_submit"
    DBT_RUN = "dbt_run"
    DBT_TEST = "dbt_test"
    SQL_QUERY = "sql_query"
    EMAIL = "email"
    HTTP_SENSOR = "http_sensor"
    TIME_SENSOR = "time_sensor"
    PYTHON_OPERATOR = "python_operator"
    BASH_OPERATOR = "bash_operator"


class DagConfig(db.Model):
    """
    DAG configuration model.
    
    Stores the configuration for an Airflow DAG.
    Each configuration can have multiple versions.
    """
    
    __tablename__ = "dag_configs"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tenant association
    tenant_id = db.Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # DAG identity
    dag_id = db.Column(String(64), nullable=False, index=True)
    description = db.Column(Text, nullable=True)
    
    # Current version
    current_version = db.Column(Integer, default=1, nullable=False)
    
    # Schedule
    schedule_type = db.Column(
        SQLEnum(ScheduleType),
        default=ScheduleType.MANUAL,
        nullable=False
    )
    schedule_cron = db.Column(String(100), nullable=True)
    schedule_preset = db.Column(String(50), nullable=True)  # hourly, daily, weekly, monthly
    timezone = db.Column(String(50), default="UTC", nullable=False)
    
    # Execution settings
    start_date = db.Column(DateTime, nullable=True)
    catchup = db.Column(Boolean, default=False, nullable=False)
    max_active_runs = db.Column(Integer, default=1, nullable=False)
    
    # Default retry policy
    default_retries = db.Column(Integer, default=1, nullable=False)
    default_retry_delay_minutes = db.Column(Integer, default=5, nullable=False)
    
    # Notifications
    notification_emails = db.Column(ARRAY(String), default=list, nullable=False)
    email_on_failure = db.Column(Boolean, default=True, nullable=False)
    email_on_success = db.Column(Boolean, default=False, nullable=False)
    
    # Tags for filtering
    tags = db.Column(ARRAY(String), default=list, nullable=False)
    
    # Status
    status = db.Column(
        SQLEnum(DagStatus),
        default=DagStatus.DRAFT,
        nullable=False
    )
    
    # Deployment tracking
    deployed_at = db.Column(DateTime, nullable=True)
    deployed_version = db.Column(Integer, nullable=True)
    
    # Audit
    created_by = db.Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Unique DAG ID within tenant
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "dag_id", name="uq_tenant_dag_id"),
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="dag_configs")
    creator = relationship("User", foreign_keys=[created_by])
    versions = relationship("DagVersion", back_populates="dag_config", order_by="DagVersion.version.desc()")
    tasks = relationship("TaskConfig", back_populates="dag_config", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DagConfig {self.dag_id}>"
    
    def to_dict(self, include_tasks: bool = True, include_versions: bool = False) -> dict:
        """Convert DAG config to dictionary."""
        result = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "dag_id": self.dag_id,
            "description": self.description,
            "current_version": self.current_version,
            "schedule_type": self.schedule_type.value,
            "schedule_cron": self.schedule_cron,
            "schedule_preset": self.schedule_preset,
            "timezone": self.timezone,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "catchup": self.catchup,
            "max_active_runs": self.max_active_runs,
            "default_retries": self.default_retries,
            "default_retry_delay_minutes": self.default_retry_delay_minutes,
            "notification_emails": self.notification_emails,
            "email_on_failure": self.email_on_failure,
            "email_on_success": self.email_on_success,
            "tags": self.tags,
            "status": self.status.value,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "deployed_version": self.deployed_version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": str(self.created_by),
        }
        
        if include_tasks:
            result["tasks"] = [task.to_dict() for task in self.tasks]
        
        if include_versions:
            result["versions"] = [v.to_dict() for v in self.versions[:10]]  # Last 10 versions
        
        return result
    
    @property
    def full_dag_id(self) -> str:
        """Get tenant-prefixed DAG ID for Airflow."""
        return f"{self.tenant.slug}_{self.dag_id}"


class DagVersion(db.Model):
    """
    DAG version history model.
    
    Stores historical versions of DAG configurations for auditing
    and rollback capabilities.
    """
    
    __tablename__ = "dag_versions"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Parent DAG config
    dag_config_id = db.Column(UUID(as_uuid=True), ForeignKey("dag_configs.id"), nullable=False, index=True)
    
    # Version number
    version = db.Column(Integer, nullable=False)
    
    # Snapshot of configuration at this version
    config_snapshot = db.Column(JSONB, nullable=False)
    
    # Generated DAG file content
    dag_file_content = db.Column(Text, nullable=True)
    
    # Change description
    change_description = db.Column(Text, nullable=True)
    
    # Audit
    created_by = db.Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Unique version per DAG
    __table_args__ = (
        db.UniqueConstraint("dag_config_id", "version", name="uq_dag_version"),
    )
    
    # Relationships
    dag_config = relationship("DagConfig", back_populates="versions")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<DagVersion {self.dag_config_id} v{self.version}>"
    
    def to_dict(self) -> dict:
        """Convert version to dictionary."""
        return {
            "id": str(self.id),
            "dag_config_id": str(self.dag_config_id),
            "version": self.version,
            "change_description": self.change_description,
            "created_at": self.created_at.isoformat(),
            "created_by": str(self.created_by),
        }


class TaskConfig(db.Model):
    """
    Task configuration model.
    
    Stores configuration for individual tasks within a DAG.
    """
    
    __tablename__ = "task_configs"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Parent DAG config
    dag_config_id = db.Column(UUID(as_uuid=True), ForeignKey("dag_configs.id"), nullable=False, index=True)
    
    # Task identity
    task_id = db.Column(String(64), nullable=False)
    
    # Task type
    task_type = db.Column(
        SQLEnum(TaskType),
        nullable=False
    )
    
    # Task-specific configuration
    config = db.Column(JSONB, default=dict, nullable=False)
    
    # Execution settings
    timeout_minutes = db.Column(Integer, default=60, nullable=False)
    retries = db.Column(Integer, default=1, nullable=False)
    retry_delay_minutes = db.Column(Integer, default=5, nullable=False)
    
    # Trigger rule
    trigger_rule = db.Column(
        SQLEnum(TriggerRule),
        default=TriggerRule.ALL_SUCCESS,
        nullable=False
    )
    
    # Dependencies (list of task_ids)
    depends_on = db.Column(ARRAY(String), default=list, nullable=False)
    
    # Visual position for DAG builder
    position_x = db.Column(Integer, default=0, nullable=False)
    position_y = db.Column(Integer, default=0, nullable=False)
    
    # Unique task ID within DAG
    __table_args__ = (
        db.UniqueConstraint("dag_config_id", "task_id", name="uq_dag_task_id"),
    )
    
    # Relationships
    dag_config = relationship("DagConfig", back_populates="tasks")
    
    def __repr__(self):
        return f"<TaskConfig {self.task_id}>"
    
    def to_dict(self) -> dict:
        """Convert task config to dictionary."""
        return {
            "id": str(self.id),
            "dag_config_id": str(self.dag_config_id),
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "config": self.config,
            "timeout_minutes": self.timeout_minutes,
            "retries": self.retries,
            "retry_delay_minutes": self.retry_delay_minutes,
            "trigger_rule": self.trigger_rule.value,
            "depends_on": self.depends_on,
            "position": {
                "x": self.position_x,
                "y": self.position_y,
            },
        }
