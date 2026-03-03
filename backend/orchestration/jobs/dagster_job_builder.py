"""
NovaSight Dagster Job Builder
==============================

Unified service for creating Dagster jobs from PySpark applications.
Replaces the separate orchestration/DAGs and PySpark modules with a single
cohesive system that:

1. Takes PySpark app configurations from the database
2. Generates PySpark code from templates
3. Creates Dagster jobs that execute spark-submit on remote servers
4. Provides scheduling, monitoring, and logging

ADR-002 Compliance: All generated code comes from pre-approved Jinja2 templates.
"""

from typing import List, Dict, Any, Optional, Callable, Tuple
from dagster import (
    job,
    op,
    In,
    Out,
    OpExecutionContext,
    AssetKey,
    DynamicOutput,
    DynamicOut,
    graph,
    schedule,
    ScheduleDefinition,
    JobDefinition,
    GraphDefinition,
    Definitions,
    RunRequest,
    SkipReason,
    sensor,
    SensorDefinition,
    RunConfig,
    Config,
)
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class SparkJobConfig:
    """Configuration for a Spark job."""
    app_id: str
    app_name: str
    tenant_id: str
    source_table: str
    target_table: str
    connection_id: str
    scd_type: str
    cdc_type: str
    cdc_column: Optional[str]
    write_mode: str
    options: Dict[str, Any]


class DagsterJobBuilder:
    """
    Builds Dagster jobs from PySpark app configurations.
    
    This is the main entry point for the merged orchestration system.
    It creates executable Dagster jobs that:
    1. Generate PySpark code from templates
    2. Copy code to remote Spark cluster
    3. Execute spark-submit via SSH
    4. Track execution and update CDC watermarks
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._jobs: List[JobDefinition] = []
        self._schedules: List[ScheduleDefinition] = []
        self._sensors: List[SensorDefinition] = []
    
    def build_job_for_pyspark_app(
        self,
        app_id: str,
        schedule_cron: Optional[str] = None,
        spark_config: Optional[Dict[str, Any]] = None,
    ) -> JobDefinition:
        """
        Build a Dagster job for a single PySpark app.
        
        Args:
            app_id: UUID of the PySpark app
            schedule_cron: Optional cron expression for scheduling
            spark_config: Optional Spark configuration overrides
        
        Returns:
            Dagster JobDefinition ready for registration
        """
        # Load app configuration from database
        app_config = self._load_pyspark_app(app_id)
        if not app_config:
            raise ValueError(f"PySpark app not found: {app_id}")
        
        # Create safe identifier for Dagster
        safe_name = self._make_safe_name(app_config.app_name)
        safe_tenant = self.tenant_id.replace('-', '_')
        job_name = f"spark_job_{safe_tenant}_{safe_name}"
        
        # Build the job using closure-based ops with baked-in parameters.
        # In Dagster's @job composition context, you cannot pass plain Python
        # values — only outputs from other ops. We create unique ops per job
        # that capture app_id and tenant_id via closure.
        _app_id = app_id
        _tenant_id = self.tenant_id
        _spark_config = spark_config or {}

        @op(name=f"{job_name}__generate_code", out={"code": Out(str), "code_hash": Out(str)})
        def _generate_code(context: OpExecutionContext) -> Tuple[str, str]:
            context.log.info(f"Generating PySpark code for app {_app_id}")
            try:
                import sys
                if '/app' not in sys.path:
                    sys.path.insert(0, '/app')
                from app import create_app
                from app.domains.compute.application.pyspark_app_service import PySparkAppService
                flask_app = create_app()
                with flask_app.app_context():
                    service = PySparkAppService(_tenant_id)
                    code, metadata = service.generate_code(_app_id)
                    code_hash = metadata.get("parameters_hash", hashlib.sha256(code.encode()).hexdigest()[:16])
                    context.log.info(f"Generated {len(code)} bytes, hash: {code_hash}")
                    return code, code_hash
            except Exception as e:
                context.log.error(f"Code generation failed: {e}")
                raise

        @op(name=f"{job_name}__write_file", out=Out(str))
        def _write_file(context: OpExecutionContext, code: str, code_hash: str) -> str:
            jobs_dir = Path("/tmp/spark_jobs")
            jobs_dir.mkdir(parents=True, exist_ok=True)
            job_filename = f"{_app_id}_{code_hash}.py"
            job_path = jobs_dir / job_filename
            job_path.write_text(code)
            context.log.info(f"Wrote job to: {job_path}")
            return str(job_path)

        @op(name=f"{job_name}__copy_remote", out=Out(str), required_resource_keys={"spark_remote"})
        def _copy_remote(context: OpExecutionContext, local_path: str) -> str:
            spark = context.resources.spark_remote
            try:
                remote_path = spark.copy_job_to_remote(local_path)
                context.log.info(f"Copied job to remote: {remote_path}")
                return remote_path
            except Exception as e:
                context.log.warning(f"Failed to copy to remote: {e}")
                # Fallback: copy to the shared volume manually
                import shutil
                dest = f"/opt/spark/jobs/{Path(local_path).name}"
                try:
                    Path("/opt/spark/jobs").mkdir(parents=True, exist_ok=True)
                    shutil.copy2(local_path, dest)
                    context.log.info(f"Fallback copy to shared volume: {dest}")
                except Exception as copy_err:
                    context.log.error(f"Fallback copy also failed: {copy_err}")
                return dest

        @op(
            name=f"{job_name}__spark_submit",
            out={"success": Out(bool), "application_id": Out(str), "duration_ms": Out(int), "stdout": Out(str), "stderr": Out(str)},
            required_resource_keys={"spark_remote"},
        )
        def _spark_submit(context: OpExecutionContext, remote_path: str) -> Tuple[bool, str, int, str, str]:
            context.log.info(f"Submitting Spark job: {remote_path}")
            spark = context.resources.spark_remote
            result = spark.submit_job(
                app_path=remote_path,
                app_args=["--app-id", _app_id],
                spark_config=_spark_config,
                copy_to_remote=False,
            )
            success = result.get("success", False)
            app_id_result = result.get("application_id", "unknown")
            duration_ms = result.get("duration_ms", 0)
            stdout = result.get("stdout", "")
            stderr = result.get("stderr", "")
            if not success:
                context.log.error(f"Spark job failed: {stderr[:500]}")
                raise Exception(f"Spark job failed: {stderr[:200]}")
            context.log.info(f"Spark job completed: app_id={app_id_result}, duration={duration_ms}ms")
            return success, app_id_result, duration_ms, stdout, stderr

        @op(name=f"{job_name}__update_stats")
        def _update_stats(context: OpExecutionContext, success: bool, application_id: str, duration_ms: int, stdout: str, stderr: str) -> None:
            try:
                import sys
                if '/app' not in sys.path:
                    sys.path.insert(0, '/app')
                from app import create_app
                from app.extensions import db as flask_db
                from app.domains.compute.domain.models import PySparkApp
                flask_app = create_app()
                with flask_app.app_context():
                    pyspark_app = PySparkApp.query.get(_app_id)
                    if pyspark_app:
                        pyspark_app.last_run_at = datetime.utcnow()
                        pyspark_app.last_run_status = "success" if success else "failed"
                        pyspark_app.last_run_duration_ms = duration_ms
                        rows = _parse_rows_from_output(stdout)
                        if rows:
                            pyspark_app.last_run_rows = rows
                        flask_db.session.commit()
                        context.log.info(f"Updated stats for {_app_id}: {pyspark_app.last_run_status}")
            except Exception as e:
                context.log.warning(f"Failed to update stats: {e}")

        @job(
            name=job_name,
            tags={
                "tenant_id": self.tenant_id,
                "app_id": app_id,
                "app_name": app_config.app_name,
                "source_table": app_config.source_table,
                "target_table": app_config.target_table,
            },
            description=f"PySpark extraction job: {app_config.source_table} -> {app_config.target_table}",
        )
        def _spark_job():
            code, code_hash = _generate_code()
            local_path = _write_file(code, code_hash)
            remote_path = _copy_remote(local_path)
            success, application_id, duration_ms, stdout, stderr = _spark_submit(remote_path)
            _update_stats(success, application_id, duration_ms, stdout, stderr)
        
        self._jobs.append(_spark_job)
        
        # Create schedule if cron expression provided
        if schedule_cron:
            schedule_def = self._create_schedule(
                job_def=_spark_job,
                cron_schedule=schedule_cron,
                schedule_name=f"schedule_{job_name}",
            )
            self._schedules.append(schedule_def)
        
        return _spark_job
    
    def build_pipeline_job(
        self,
        app_ids: List[str],
        pipeline_name: str,
        parallel: bool = False,
        schedule_cron: Optional[str] = None,
        spark_config: Optional[Dict[str, Any]] = None,
    ) -> JobDefinition:
        """
        Build a Dagster job that runs multiple PySpark apps.
        
        Args:
            app_ids: List of PySpark app UUIDs to run
            pipeline_name: Name for the combined pipeline
            parallel: If True, run apps in parallel; otherwise sequential
            schedule_cron: Optional cron expression for scheduling
            spark_config: Optional Spark configuration overrides
        
        Returns:
            Dagster JobDefinition for the pipeline
        """
        safe_name = self._make_safe_name(pipeline_name)
        safe_tenant = self.tenant_id.replace('-', '_')
        job_name = f"pipeline_{safe_tenant}_{safe_name}"
        
        # Load all app configurations
        apps = []
        for app_id in app_ids:
            config = self._load_pyspark_app(app_id)
            if config:
                apps.append((app_id, config))
        
        if not apps:
            raise ValueError("No valid PySpark apps found for pipeline")
        
        @job(
            name=job_name,
            tags={
                "tenant_id": self.tenant_id,
                "pipeline": pipeline_name,
                "app_count": str(len(apps)),
            },
            description=f"Pipeline '{pipeline_name}' executing {len(apps)} PySpark jobs",
        )
        def _pipeline_job():
            if parallel:
                # Run all apps in parallel
                results = []
                for app_id, config in apps:
                    code_result = generate_pyspark_code(app_id, self.tenant_id)
                    write_result = write_job_to_file(code_result, app_id)
                    copy_result = copy_to_remote_spark(write_result, app_id)
                    submit_result = execute_remote_spark_submit(copy_result, app_id, spark_config or {})
                    results.append(submit_result)
                
                # Aggregate results
                aggregate_pipeline_results(results, pipeline_name)
            else:
                # Run sequentially - each depends on previous
                previous_result = None
                for app_id, config in apps:
                    code_result = generate_pyspark_code(app_id, self.tenant_id)
                    write_result = write_job_to_file(code_result, app_id)
                    copy_result = copy_to_remote_spark(write_result, app_id)
                    submit_result = execute_remote_spark_submit(
                        copy_result, app_id, spark_config or {},
                        depends_on=previous_result
                    )
                    update_stats(submit_result, app_id, self.tenant_id)
                    previous_result = submit_result
        
        self._jobs.append(_pipeline_job)
        
        if schedule_cron:
            schedule_def = self._create_schedule(
                job_def=_pipeline_job,
                cron_schedule=schedule_cron,
                schedule_name=f"schedule_{job_name}",
            )
            self._schedules.append(schedule_def)
        
        return _pipeline_job
    
    def _load_pyspark_app(self, app_id: str) -> Optional[SparkJobConfig]:
        """Load PySpark app configuration from database."""
        try:
            import sys
            if '/app' not in sys.path:
                sys.path.insert(0, '/app')
            
            from app import create_app
            from app.domains.compute.domain.models import PySparkApp
            
            app = create_app()
            with app.app_context():
                pyspark_app = PySparkApp.query.get(app_id)
                if not pyspark_app:
                    return None
                
                return SparkJobConfig(
                    app_id=str(pyspark_app.id),
                    app_name=pyspark_app.name,
                    tenant_id=str(pyspark_app.tenant_id),
                    source_table=pyspark_app.source_table or "",
                    target_table=pyspark_app.target_table or "",
                    connection_id=str(pyspark_app.connection_id),
                    scd_type=pyspark_app.scd_type.value if pyspark_app.scd_type else "none",
                    cdc_type=pyspark_app.cdc_type.value if pyspark_app.cdc_type else "none",
                    cdc_column=pyspark_app.cdc_column,
                    write_mode=pyspark_app.write_mode.value if pyspark_app.write_mode else "append",
                    options=pyspark_app.options or {},
                )
        except Exception as e:
            logger.error(f"Failed to load PySpark app {app_id}: {e}")
            return None
    
    def _make_safe_name(self, name: str) -> str:
        """Convert a name to a safe Dagster identifier."""
        import re
        safe = re.sub(r'[^a-z0-9_]', '_', name.lower())
        # Ensure it starts with a letter
        if safe and not safe[0].isalpha():
            safe = 'job_' + safe
        return safe[:50]  # Limit length
    
    def _create_schedule(
        self,
        job_def: JobDefinition,
        cron_schedule: str,
        schedule_name: str,
    ) -> ScheduleDefinition:
        """Create a schedule for a job."""
        @schedule(
            cron_schedule=cron_schedule,
            job=job_def,
            name=schedule_name,
            default_status="RUNNING",
        )
        def _schedule(context):
            return RunRequest(
                run_key=f"{schedule_name}_{datetime.utcnow().isoformat()}",
                tags={
                    "scheduled": "true",
                    "schedule_time": datetime.utcnow().isoformat(),
                },
            )
        
        return _schedule
    
    def get_definitions(self) -> Definitions:
        """Get all Dagster definitions (jobs, schedules, sensors)."""
        from orchestration.resources.remote_spark_resource import DynamicRemoteSparkResource
        
        return Definitions(
            jobs=self._jobs,
            schedules=self._schedules,
            sensors=self._sensors,
            resources={
                "spark_remote": DynamicRemoteSparkResource(),
            },
        )


# =============================================================================
# Dagster Operations (Ops) for Spark Job Execution
# =============================================================================

@op(
    description="Generate PySpark code from template",
    out={
        "code": Out(str, description="Generated PySpark code"),
        "code_hash": Out(str, description="Hash of the generated code"),
    },
)
def generate_pyspark_code(context: OpExecutionContext, app_id: str, tenant_id: str) -> Tuple[str, str]:
    """Generate PySpark code from template using the template engine."""
    context.log.info(f"Generating PySpark code for app {app_id}")
    
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.domains.compute.application.pyspark_app_service import PySparkAppService
        
        app = create_app()
        with app.app_context():
            service = PySparkAppService(tenant_id)
            code, metadata = service.generate_code(app_id)
            code_hash = metadata.get("parameters_hash", hashlib.sha256(code.encode()).hexdigest()[:16])
            
            context.log.info(f"Generated {len(code)} bytes of code, hash: {code_hash}")
            return code, code_hash
    
    except Exception as e:
        context.log.error(f"Code generation failed: {e}")
        raise


@op(
    description="Write generated PySpark code to local file",
    out=Out(str, description="Path to the written job file"),
)
def write_job_to_file(
    context: OpExecutionContext,
    code_result: tuple,
    app_id: str,
) -> str:
    """Write PySpark code to a local file for later submission."""
    code, code_hash = code_result
    
    # Create jobs directory
    jobs_dir = Path("/tmp/spark_jobs")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    
    # Write code to file
    job_filename = f"{app_id}_{code_hash}.py"
    job_path = jobs_dir / job_filename
    job_path.write_text(code)
    
    context.log.info(f"Wrote job to: {job_path}")
    return str(job_path)


@op(
    description="Copy PySpark job to remote Spark server",
    out=Out(str, description="Remote path of the job file"),
    required_resource_keys={"spark_remote"},
)
def copy_to_remote_spark(
    context: OpExecutionContext,
    local_path: str,
    app_id: str,
) -> str:
    """Copy the generated PySpark job to the remote Spark cluster."""
    spark = context.resources.spark_remote
    
    try:
        remote_path = spark.copy_job_to_remote(local_path)
        context.log.info(f"Copied job to remote: {remote_path}")
        return remote_path
    except Exception as e:
        context.log.warning(f"Failed to copy to remote, assuming exists: {e}")
        # Return expected remote path
        return f"/opt/spark/jobs/{Path(local_path).name}"


@op(
    description="Execute spark-submit on remote server",
    out={
        "success": Out(bool, description="Whether the job succeeded"),
        "application_id": Out(str, description="Spark application ID"),
        "duration_ms": Out(int, description="Execution duration in milliseconds"),
        "stdout": Out(str, description="Standard output"),
        "stderr": Out(str, description="Standard error"),
    },
    required_resource_keys={"spark_remote"},
)
def execute_remote_spark_submit(
    context: OpExecutionContext,
    remote_path: str,
    app_id: str,
    spark_config: Dict[str, Any],
    depends_on: Optional[Any] = None,
) -> Tuple[bool, str, int, str, str]:
    """Execute spark-submit on the remote Spark cluster."""
    context.log.info(f"Submitting Spark job: {remote_path}")
    
    spark = context.resources.spark_remote
    
    result = spark.submit_job(
        app_path=remote_path,
        app_args=["--app-id", app_id],
        spark_config=spark_config,
        copy_to_remote=False,  # Already copied
    )
    
    success = result.get("success", False)
    app_id_result = result.get("application_id", "unknown")
    duration_ms = result.get("duration_ms", 0)
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    
    if not success:
        context.log.error(f"Spark job failed: {stderr[:500]}")
        raise Exception(f"Spark job failed: {stderr[:200]}")
    
    context.log.info(f"Spark job completed: app_id={app_id_result}, duration={duration_ms}ms")
    
    return success, app_id_result, duration_ms, stdout, stderr


@op(
    description="Update execution statistics in database",
)
def update_stats(
    context: OpExecutionContext,
    submit_result: tuple,
    app_id: str,
    tenant_id: str,
) -> None:
    """Update PySpark app execution statistics in database."""
    success, application_id, duration_ms, stdout, stderr = submit_result
    
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.extensions import db
        from app.domains.compute.domain.models import PySparkApp
        
        app = create_app()
        with app.app_context():
            pyspark_app = PySparkApp.query.get(app_id)
            if pyspark_app:
                pyspark_app.last_run_at = datetime.utcnow()
                pyspark_app.last_run_status = "success" if success else "failed"
                pyspark_app.last_run_duration_ms = duration_ms
                
                # Parse rows processed from stdout if available
                rows = _parse_rows_from_output(stdout)
                if rows:
                    pyspark_app.last_run_rows = rows
                
                db.session.commit()
                context.log.info(f"Updated stats for {app_id}: {pyspark_app.last_run_status}")
    
    except Exception as e:
        context.log.warning(f"Failed to update stats: {e}")


@op(
    description="Aggregate results from parallel pipeline execution",
)
def aggregate_pipeline_results(
    context: OpExecutionContext,
    results: List[tuple],
    pipeline_name: str,
) -> Dict[str, Any]:
    """Aggregate results from multiple parallel Spark jobs."""
    total_duration = 0
    all_success = True
    app_ids = []
    
    for result in results:
        success, app_id, duration_ms, _, _ = result
        all_success = all_success and success
        total_duration += duration_ms
        app_ids.append(app_id)
    
    context.log.info(
        f"Pipeline '{pipeline_name}' completed: "
        f"success={all_success}, jobs={len(results)}, total_duration={total_duration}ms"
    )
    
    return {
        "pipeline_name": pipeline_name,
        "success": all_success,
        "job_count": len(results),
        "total_duration_ms": total_duration,
        "application_ids": app_ids,
    }


def _parse_rows_from_output(stdout: str) -> Optional[int]:
    """Parse rows processed from Spark job output."""
    import re
    
    # Look for common patterns
    patterns = [
        r"Processed (\d+) rows",
        r"Rows written: (\d+)",
        r"Total rows: (\d+)",
        r"(\d+) records processed",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, stdout, re.IGNORECASE)
        if match:
            return int(match.group(1))
    
    return None


# =============================================================================
# Factory Functions
# =============================================================================

def load_all_dagster_jobs() -> List[JobDefinition]:
    """
    Load all Dagster jobs for all tenants with active PySpark apps.
    
    Called at Dagster startup.
    """
    all_jobs = []
    
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.domains.compute.domain.models import PySparkApp, PySparkAppStatus
        from app.domains.orchestration.domain.models import DagConfig, DagStatus
        
        app = create_app()
        with app.app_context():
            # Get all active PySpark apps with schedules
            active_apps = (
                PySparkApp.query
                .filter(PySparkApp.status == PySparkAppStatus.ACTIVE)
                .all()
            )
            
            # Group by tenant
            tenant_apps: Dict[str, List[Any]] = {}
            for pyspark_app in active_apps:
                tid = str(pyspark_app.tenant_id)
                if tid not in tenant_apps:
                    tenant_apps[tid] = []
                tenant_apps[tid].append(pyspark_app)
            
            # Build jobs for each tenant
            for tenant_id, apps in tenant_apps.items():
                builder = DagsterJobBuilder(tenant_id)
                
                for pyspark_app in apps:
                    # Check if there's a schedule configured
                    dag_config = DagConfig.query.filter(
                        DagConfig.tenant_id == tenant_id,
                        DagConfig.tags.contains([str(pyspark_app.id)]),
                        DagConfig.status.in_([DagStatus.ACTIVE, DagStatus.DRAFT]),
                    ).first()
                    
                    schedule_cron = None
                    if dag_config and dag_config.schedule_type.value == "cron":
                        schedule_cron = dag_config.schedule_cron
                    
                    try:
                        job = builder.build_job_for_pyspark_app(
                            app_id=str(pyspark_app.id),
                            schedule_cron=schedule_cron,
                        )
                        all_jobs.append(job)
                        logger.info(f"Loaded job for PySpark app: {pyspark_app.name}")
                    except Exception as e:
                        logger.error(f"Failed to build job for {pyspark_app.name}: {e}")
    
    except Exception as e:
        logger.warning(f"Could not load Dagster jobs: {e}")
    
    return all_jobs


def load_all_schedules() -> List[ScheduleDefinition]:
    """Load all schedules for active jobs."""
    all_schedules = []
    
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.domains.orchestration.domain.models import DagConfig, DagStatus, ScheduleType
        
        app = create_app()
        with app.app_context():
            # Get all active DAGs with cron schedules
            active_dags = DagConfig.query.filter(
                DagConfig.status == DagStatus.ACTIVE,
                DagConfig.schedule_type == ScheduleType.CRON,
            ).all()
            
            for dag in active_dags:
                try:
                    # Build schedule (this is handled by the job builder)
                    pass
                except Exception as e:
                    logger.error(f"Failed to create schedule for {dag.dag_id}: {e}")
    
    except Exception as e:
        logger.warning(f"Could not load schedules: {e}")
    
    return all_schedules
