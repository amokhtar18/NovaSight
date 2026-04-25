"""
NovaSight Dagster Schedules — dlt Pipelines
=============================================

Schedule definitions for dlt extraction pipelines.
Enables automated, scheduled execution of data pipelines that
load data into Iceberg tables on S3.

Schedules are created dynamically based on DltPipeline configurations
stored in the database.
"""

from typing import List, Optional, Dict, Any
from dagster import (
    ScheduleDefinition,
    DefaultScheduleStatus,
    define_asset_job,
    AssetSelection,
    RunRequest,
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DltScheduleBuilder:
    """
    Builds Dagster schedules for dlt extraction pipelines.
    
    Creates schedules based on:
    1. Cron expressions from pipeline options
    2. Preset schedules (hourly, daily, weekly, monthly)
    3. Write disposition-based automatic scheduling
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

    def __init__(self, tenant_id: str, tenant_slug: str):
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug

    def build_schedule_for_dlt_pipeline(
        self,
        pipeline: Any,
    ) -> Optional[ScheduleDefinition]:
        """
        Build a Dagster schedule for a dlt pipeline.
        
        Args:
            pipeline: DltPipeline model instance
            
        Returns:
            ScheduleDefinition or None if manual scheduling
        """
        cron_schedule = self._get_cron_schedule(pipeline)
        if not cron_schedule:
            logger.info(f"dlt pipeline {pipeline.name} has no schedule configured")
            return None
        
        # Build asset selection for this pipeline's asset
        safe_slug = self.tenant_slug.replace('-', '_').replace('.', '_')
        safe_pipeline_name = pipeline.name.lower().replace(' ', '_').replace('-', '_')
        asset_key = ["dlt", safe_slug, f"dlt_{safe_slug}__{safe_pipeline_name}"]
        
        # Create job for the asset
        job = define_asset_job(
            name=f"dlt_{str(pipeline.id)[:8]}_job",
            selection=AssetSelection.assets(asset_key),
            description=f"Scheduled execution of {pipeline.name}",
            tags={
                "tenant_id": self.tenant_id,
                "tenant_slug": self.tenant_slug,
                "dlt_pipeline": pipeline.name,
                "schedule_type": "dlt_extraction",
            },
        )
        
        # Determine initial status
        initial_status = DefaultScheduleStatus.RUNNING
        if pipeline.status.value != "active":
            initial_status = DefaultScheduleStatus.STOPPED
        
        schedule_def = ScheduleDefinition(
            name=f"dlt_{str(pipeline.id)[:8]}_schedule",
            cron_schedule=cron_schedule,
            job=job,
            default_status=initial_status,
            execution_timezone="UTC",
        )
        
        logger.info(f"Created schedule for {pipeline.name}: cron={cron_schedule}")
        return schedule_def

    def _get_cron_schedule(self, pipeline: Any) -> Optional[str]:
        """
        Extract cron schedule from pipeline options.
        """
        options = pipeline.options or {}
        
        # Direct cron expression
        if options.get("schedule_cron"):
            return options["schedule_cron"]
        
        # Preset schedule
        if options.get("schedule_preset"):
            preset = options["schedule_preset"]
            return self.PRESET_TO_CRON.get(preset)
        
        # Incremental pipelines default to hourly
        if pipeline.incremental_cursor_column:
            return options.get("incremental_schedule", "0 * * * *")
        
        # SCD2 pipelines default to daily
        if pipeline.write_disposition.value == "scd2":
            return options.get("scd2_schedule", "0 0 * * *")
        
        return None

    def build_all_schedules(self) -> List[ScheduleDefinition]:
        """
        Build schedules for all active dlt pipelines in the tenant.
        """
        schedules = []
        
        try:
            import sys
            if '/app' not in sys.path:
                sys.path.insert(0, '/app')
            
            from app import create_app
            from app.domains.ingestion.domain.models import DltPipeline, DltPipelineStatus
            
            app = create_app()
            with app.app_context():
                pipelines = DltPipeline.query.filter(
                    DltPipeline.tenant_id == self.tenant_id,
                    DltPipeline.status == DltPipelineStatus.ACTIVE,
                ).all()
                
                for pipeline in pipelines:
                    try:
                        schedule_def = self.build_schedule_for_dlt_pipeline(pipeline)
                        if schedule_def:
                            schedules.append(schedule_def)
                    except Exception as e:
                        logger.error(f"Failed to build schedule for {pipeline.name}: {e}")
        
        except Exception as e:
            logger.warning(f"Could not load dlt schedules: {e}")
        
        return schedules


def load_all_dlt_schedules() -> List[ScheduleDefinition]:
    """
    Load schedules for all active dlt pipelines across all tenants.
    
    Called at Dagster startup.
    """
    all_schedules = []
    
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.domains.tenants.domain.models import Tenant
        from app.domains.ingestion.domain.models import DltPipeline, DltPipelineStatus
        
        app = create_app()
        with app.app_context():
            # Get all tenants with active dlt pipelines
            results = (
                DltPipeline.query
                .join(Tenant, DltPipeline.tenant_id == Tenant.id)
                .filter(DltPipeline.status == DltPipelineStatus.ACTIVE)
                .with_entities(DltPipeline.tenant_id, Tenant.slug)
                .distinct()
                .all()
            )
            
            for tenant_id, tenant_slug in results:
                builder = DltScheduleBuilder(str(tenant_id), tenant_slug)
                schedules = builder.build_all_schedules()
                all_schedules.extend(schedules)
                logger.info(f"Loaded {len(schedules)} dlt schedules for tenant {tenant_slug}")
    
    except Exception as e:
        logger.warning(f"Could not load dlt schedules: {e}")
    
    return all_schedules


def create_manual_run_request(
    pipeline_id: str,
    tenant_id: str,
    tenant_slug: str,
    run_config: Optional[Dict[str, Any]] = None,
) -> RunRequest:
    """
    Create a RunRequest for manual dlt pipeline execution.
    
    Used by the API to trigger on-demand runs.
    """
    return RunRequest(
        run_key=f"manual_dlt_{pipeline_id}_{datetime.utcnow().isoformat()}",
        tags={
            "tenant_id": tenant_id,
            "tenant_slug": tenant_slug,
            "dlt_pipeline_id": pipeline_id,
            "trigger_type": "manual",
        },
        run_config=run_config or {},
    )
