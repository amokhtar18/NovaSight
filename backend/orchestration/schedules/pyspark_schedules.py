"""
NovaSight Dagster Schedules — PySpark
=======================================

Schedule definitions for PySpark extraction jobs.
Enables automated, scheduled execution of data pipelines.

Schedules are created dynamically based on DagConfig settings
associated with PySparkApp configurations.
"""

from typing import List, Optional, Dict, Any
from dagster import (
    ScheduleDefinition,
    DefaultScheduleStatus,
    define_asset_job,
    AssetSelection,
    build_schedule_from_partitioned_job,
    DailyPartitionsDefinition,
    HourlyPartitionsDefinition,
    WeeklyPartitionsDefinition,
    MonthlyPartitionsDefinition,
    ScheduleEvaluationContext,
    RunRequest,
    schedule,
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PySparkScheduleBuilder:
    """
    Builds Dagster schedules for PySpark extraction jobs.
    
    Creates schedules based on:
    1. Cron expressions from DagConfig
    2. Preset schedules (hourly, daily, weekly, monthly)
    3. CDC-based automatic scheduling
    """
    
    # Preset to cron mapping
    PRESET_TO_CRON = {
        "hourly": "0 * * * *",
        "daily": "0 0 * * *",
        "weekly": "0 0 * * 0",
        "monthly": "0 0 1 * *",
        "every_15_min": "*/15 * * * *",
        "every_30_min": "*/30 * * * *",
        "every_6_hours": "0 */6 * * *",
        "every_12_hours": "0 */12 * * *",
    }

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def build_schedule_for_pyspark_app(
        self,
        app: Any,
        dag_config: Optional[Any] = None,
    ) -> Optional[ScheduleDefinition]:
        """
        Build a Dagster schedule for a PySpark app.
        
        Args:
            app: PySparkApp model instance
            dag_config: Optional DagConfig with schedule settings
            
        Returns:
            ScheduleDefinition or None if manual scheduling
        """
        cron_schedule = self._get_cron_schedule(app, dag_config)
        if not cron_schedule:
            logger.info(f"PySpark app {app.name} has no schedule configured")
            return None
        
        # Build asset selection for this app's asset
        asset_name = f"pyspark_{app.name.lower().replace(' ', '_').replace('-', '_')}"
        safe_tenant_id = self.tenant_id.replace('-', '_')
        asset_key = ["pyspark", safe_tenant_id, asset_name]
        
        # Create job for the asset
        job = define_asset_job(
            name=f"pyspark_{str(app.id)[:8]}_job",
            selection=AssetSelection.assets(asset_key),
            description=f"Scheduled execution of {app.name}",
            tags={
                "tenant_id": self.tenant_id,
                "pyspark_app": app.name,
                "schedule_type": "pyspark_extraction",
            },
        )
        
        # Determine initial status
        initial_status = DefaultScheduleStatus.RUNNING
        if app.status.value != "active":
            initial_status = DefaultScheduleStatus.STOPPED
        
        schedule_def = ScheduleDefinition(
            name=f"pyspark_{str(app.id)[:8]}_schedule",
            cron_schedule=cron_schedule,
            job=job,
            default_status=initial_status,
            execution_timezone="UTC",
        )
        
        logger.info(f"Created schedule for {app.name}: cron={cron_schedule}")
        return schedule_def

    def _get_cron_schedule(
        self,
        app: Any,
        dag_config: Optional[Any] = None,
    ) -> Optional[str]:
        """
        Extract cron schedule from app options or DagConfig.
        """
        # First check app options
        options = app.options or {}
        
        # Direct cron expression
        if options.get("schedule_cron"):
            return options["schedule_cron"]
        
        # Preset schedule
        if options.get("schedule_preset"):
            preset = options["schedule_preset"]
            return self.PRESET_TO_CRON.get(preset)
        
        # CDC-based auto schedule
        if app.cdc_type.value != "none":
            # Default to hourly for incremental loads
            return options.get("cdc_schedule", "0 * * * *")
        
        # Check associated DagConfig
        if dag_config:
            if dag_config.schedule_type.value == "cron":
                return dag_config.schedule_cron
            elif dag_config.schedule_type.value == "preset":
                return self.PRESET_TO_CRON.get(dag_config.schedule_preset)
        
        return None

    def build_all_schedules(self) -> List[ScheduleDefinition]:
        """
        Build schedules for all active PySpark apps in the tenant.
        """
        schedules = []
        
        try:
            import sys
            if '/app' not in sys.path:
                sys.path.insert(0, '/app')
            
            from app import create_app
            from app.domains.compute.domain.models import PySparkApp, PySparkAppStatus
            
            app = create_app()
            with app.app_context():
                apps = PySparkApp.query.filter(
                    PySparkApp.tenant_id == self.tenant_id,
                    PySparkApp.status == PySparkAppStatus.ACTIVE,
                ).all()
                
                for pyspark_app in apps:
                    try:
                        schedule_def = self.build_schedule_for_pyspark_app(pyspark_app)
                        if schedule_def:
                            schedules.append(schedule_def)
                    except Exception as e:
                        logger.error(f"Failed to build schedule for {pyspark_app.name}: {e}")
        
        except Exception as e:
            logger.warning(f"Could not load PySpark schedules: {e}")
        
        return schedules


def load_all_pyspark_schedules() -> List[ScheduleDefinition]:
    """
    Load schedules for all active PySpark apps across all tenants.
    
    Called at Dagster startup.
    """
    all_schedules = []
    
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.domains.compute.domain.models import PySparkApp, PySparkAppStatus
        
        app = create_app()
        with app.app_context():
            # Get all tenants with active PySpark apps
            tenant_ids = (
                PySparkApp.query
                .filter(PySparkApp.status == PySparkAppStatus.ACTIVE)
                .with_entities(PySparkApp.tenant_id)
                .distinct()
                .all()
            )
            
            for (tenant_id,) in tenant_ids:
                builder = PySparkScheduleBuilder(str(tenant_id))
                schedules = builder.build_all_schedules()
                all_schedules.extend(schedules)
                logger.info(f"Loaded {len(schedules)} PySpark schedules for tenant {tenant_id}")
    
    except Exception as e:
        logger.warning(f"Could not load PySpark schedules: {e}")
    
    return all_schedules


def create_manual_run_schedule(
    app_id: str,
    tenant_id: str,
    run_config: Optional[Dict[str, Any]] = None,
) -> RunRequest:
    """
    Create a RunRequest for manual PySpark job execution.
    
    Used by the API to trigger on-demand runs.
    """
    return RunRequest(
        run_key=f"manual_pyspark_{app_id}_{datetime.utcnow().isoformat()}",
        tags={
            "tenant_id": tenant_id,
            "pyspark_app_id": app_id,
            "trigger_type": "manual",
        },
        run_config=run_config or {},
    )
