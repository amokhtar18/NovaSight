"""
NovaSight Orchestration Domain — Schedule Factory
===================================================

Dynamically generates Dagster schedules from DagConfig models.

Canonical location: ``app.domains.orchestration.infrastructure.schedule_factory``
"""

from typing import Optional
from dagster import (
    ScheduleDefinition,
    DefaultScheduleStatus,
    define_asset_job,
    AssetSelection,
)
import re
import logging

logger = logging.getLogger(__name__)


class ScheduleFactory:
    """
    Builds Dagster schedules from DagConfig models.
    
    Maps cron schedule expressions to Dagster ScheduleDefinition.
    """

    # Preset to cron mapping
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
        "@once": None,  # One-time runs don't need schedules
    }

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def _resolve_full_dag_id(self, dag_config) -> str:
        """Resolve/sanitize full DAG id for Dagster-safe names."""
        full_dag_id = getattr(dag_config, "full_dag_id", None)
        if isinstance(full_dag_id, str) and full_dag_id.strip():
            raw = full_dag_id.strip()
        else:
            dag_id = getattr(dag_config, "dag_id", "dag")
            raw = f"{self.tenant_id}_{dag_id}"
        return re.sub(r"[^A-Za-z0-9_]", "_", str(raw))

    def build_schedule_from_dag_config(
        self,
        dag_config,
    ) -> Optional[ScheduleDefinition]:
        """
        Build a Dagster schedule from DagConfig.
        
        Returns None for manual schedules.
        """
        from app.domains.orchestration.domain.models import ScheduleType
        
        if dag_config.schedule_type == ScheduleType.MANUAL:
            logger.info(f"DAG {dag_config.dag_id} is manual, no schedule created")
            return None
        
        # Determine cron expression
        cron_schedule = self._get_cron_schedule(dag_config)
        if not cron_schedule:
            logger.warning(f"Could not determine cron schedule for {dag_config.dag_id}")
            return None
        
        # Create job for this pipeline's assets
        safe_full_dag_id = self._resolve_full_dag_id(dag_config)
        group_name = f"tenant_{safe_full_dag_id}"
        job_name = f"{safe_full_dag_id}_job"
        selection = AssetSelection.groups(group_name).upstream()
        
        job = define_asset_job(
            name=job_name,
            selection=selection,
            description=dag_config.description or f"Job for {dag_config.dag_id}",
            tags={
                "tenant_id": self.tenant_id,
                "dag_id": dag_config.dag_id,
            },
        )
        
        # Determine initial status
        initial_status = DefaultScheduleStatus.STOPPED
        if hasattr(dag_config.status, 'value'):
            if dag_config.status.value == "active":
                initial_status = DefaultScheduleStatus.RUNNING
        elif str(dag_config.status) == "active":
            initial_status = DefaultScheduleStatus.RUNNING
        
        schedule_def = ScheduleDefinition(
            name=f"{safe_full_dag_id}_schedule",
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

    def _get_cron_schedule(self, dag_config) -> Optional[str]:
        """Extract cron schedule from DagConfig."""
        from app.domains.orchestration.domain.models import ScheduleType
        
        if dag_config.schedule_type == ScheduleType.CRON:
            return dag_config.schedule_cron
        
        if dag_config.schedule_type == ScheduleType.PRESET:
            preset = dag_config.schedule_preset
            return self.PRESET_TO_CRON.get(preset)
        
        return None

    def build_job_from_dag_config(self, dag_config):
        """Build a job definition for manual triggering."""
        safe_full_dag_id = self._resolve_full_dag_id(dag_config)
        group_name = f"tenant_{safe_full_dag_id}"
        selection = AssetSelection.groups(group_name).upstream()
        
        return define_asset_job(
            name=f"{safe_full_dag_id}_job",
            selection=selection,
            description=dag_config.description or f"Job for {dag_config.dag_id}",
            tags={
                "tenant_id": self.tenant_id,
                "dag_id": dag_config.dag_id,
            },
        )
