"""
NovaSight DAG Generator
=======================

Generates Airflow DAG Python files from configuration.
Uses templates for security (no arbitrary code generation).
"""

from typing import Dict, Any
from datetime import datetime
from jinja2 import Environment, PackageLoader, select_autoescape
from app.models.dag import DagConfig, TaskConfig, ScheduleType
import logging

logger = logging.getLogger(__name__)


class DagGenerator:
    """Generates Airflow DAG files from configuration."""
    
    def __init__(self, tenant_id: str):
        """
        Initialize DAG generator.
        
        Args:
            tenant_id: Tenant UUID for DAG namespacing
        """
        self.tenant_id = tenant_id
        
        # Initialize Jinja2 environment with templates
        self.env = Environment(
            loader=PackageLoader('app', 'templates/airflow'),
            autoescape=select_autoescape(['py']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
    
    def generate(self, dag_config: DagConfig) -> str:
        """
        Generate Airflow DAG file content.
        
        Args:
            dag_config: DAG configuration
        
        Returns:
            Generated Python DAG file content
        """
        template = self.env.get_template('dag_template.py.j2')
        
        # Prepare template context
        context = {
            "dag_id": dag_config.full_dag_id,
            "description": dag_config.description or "",
            "schedule": self._get_schedule_string(dag_config),
            "start_date": self._format_start_date(dag_config.start_date),
            "catchup": dag_config.catchup,
            "max_active_runs": dag_config.max_active_runs,
            "default_args": {
                "retries": dag_config.default_retries,
                "retry_delay_minutes": dag_config.default_retry_delay_minutes,
                "email": dag_config.notification_emails,
                "email_on_failure": dag_config.email_on_failure,
                "email_on_success": dag_config.email_on_success,
            },
            "tags": [dag_config.tenant.slug] + dag_config.tags,
            "tasks": [self._prepare_task(t) for t in dag_config.tasks],
            "generated_at": datetime.utcnow().isoformat(),
            "version": dag_config.current_version,
        }
        
        return template.render(**context)
    
    def _get_schedule_string(self, dag_config: DagConfig) -> str:
        """Get schedule string for DAG."""
        if dag_config.schedule_type == ScheduleType.MANUAL:
            return "None"
        elif dag_config.schedule_type == ScheduleType.CRON:
            return f'"{dag_config.schedule_cron}"'
        elif dag_config.schedule_type == ScheduleType.PRESET:
            preset_map = {
                "hourly": '"@hourly"',
                "daily": '"@daily"',
                "weekly": '"@weekly"',
                "monthly": '"@monthly"',
            }
            return preset_map.get(dag_config.schedule_preset, "None")
        return "None"
    
    def _format_start_date(self, start_date: datetime) -> str:
        """Format start date for template."""
        if not start_date:
            return "datetime(2024, 1, 1)"
        return f"datetime({start_date.year}, {start_date.month}, {start_date.day})"
    
    def _prepare_task(self, task: TaskConfig) -> Dict[str, Any]:
        """Prepare task configuration for template."""
        return {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "config": task.config,
            "timeout_minutes": task.timeout_minutes,
            "retries": task.retries,
            "retry_delay_minutes": task.retry_delay_minutes,
            "trigger_rule": task.trigger_rule.value,
            "depends_on": task.depends_on,
        }
