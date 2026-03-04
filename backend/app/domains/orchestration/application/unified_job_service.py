"""
NovaSight Unified Job Service
==============================

Business logic for managing Dagster jobs that execute PySpark apps
on remote Spark clusters.

This service provides:
1. Job CRUD operations
2. Job execution (trigger, pause, resume)
3. Run monitoring and logging
4. Spark configuration management
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID, uuid4
import logging
import hashlib
import requests

from app.extensions import db
from app.domains.orchestration.domain.models import (
    DagConfig,
    DagStatus,
    ScheduleType,
    TaskConfig,
    TaskType,
)
from app.domains.compute.domain.models import PySparkApp, PySparkAppStatus

logger = logging.getLogger(__name__)


class UnifiedJobService:
    """
    Service for managing Dagster jobs with remote Spark execution.
    
    Replaces the separate DagService and PySparkDAGGenerator with a
    unified interface for all job management operations.
    """
    
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._dagster_url = self._get_dagster_url()
    
    def _get_dagster_url(self) -> str:
        """Get Dagster webserver URL from environment."""
        import os
        return os.environ.get("DAGSTER_URL", "http://localhost:3000")
    
    # =========================================================================
    # Job CRUD Operations
    # =========================================================================
    
    def list_jobs(
        self,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List all jobs for the tenant."""
        query = DagConfig.query.filter(
            DagConfig.tenant_id == self.tenant_id,
            DagConfig.status != DagStatus.ARCHIVED,
        )
        
        if status:
            query = query.filter(DagConfig.status == DagStatus(status))
        
        if job_type:
            # Filter by job type using tags
            query = query.filter(DagConfig.tags.contains([job_type]))
        
        total = query.count()
        dags = query.order_by(DagConfig.updated_at.desc()).offset(
            (page - 1) * per_page
        ).limit(per_page).all()
        
        # Enrich with execution status from Dagster
        jobs = []
        for dag in dags:
            job_data = self._dag_to_job_dict(dag, include_tasks=False)
            job_data["last_run"] = self._get_last_run_status(dag.dag_id)
            jobs.append(job_data)
        
        return {
            "jobs": jobs,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }
    
    def create_job(
        self,
        pyspark_app_id: str,
        schedule: Optional[str] = None,
        spark_config: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        notifications: Optional[Dict[str, Any]] = None,
        retries: int = 2,
        retry_delay_minutes: int = 5,
        created_by: str = None,
    ) -> Dict[str, Any]:
        """Create a new Dagster job for a PySpark app."""
        # Validate UUID format
        try:
            UUID(str(pyspark_app_id))
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid PySpark app ID format: {pyspark_app_id}")

        # Validate PySpark app exists
        pyspark_app = PySparkApp.query.filter(
            PySparkApp.id == pyspark_app_id,
            PySparkApp.tenant_id == self.tenant_id,
        ).first()
        
        if not pyspark_app:
            raise ValueError(f"PySpark app not found: {pyspark_app_id}")
        
        # Generate job name if not provided
        if not name:
            safe_name = pyspark_app.name.lower().replace(" ", "_").replace("-", "_")
            name = f"spark_{safe_name}"
        
        # Check for duplicate dag_id (exclude archived/deleted jobs)
        existing = DagConfig.query.filter(
            DagConfig.tenant_id == self.tenant_id,
            DagConfig.dag_id == name,
            DagConfig.status != DagStatus.ARCHIVED,
        ).first()
        if existing:
            raise ValueError(
                f"A job with the name '{name}' already exists. "
                f"Please choose a different name or edit the existing job."
            )
        
        # Determine schedule type
        schedule_type = ScheduleType.MANUAL
        schedule_cron = None
        schedule_preset = None
        
        if schedule:
            if schedule.startswith("@"):
                schedule_type = ScheduleType.PRESET
                schedule_preset = schedule
            elif schedule:
                schedule_type = ScheduleType.CRON
                schedule_cron = schedule
        
        # Create the DagConfig
        dag_config = DagConfig(
            tenant_id=self.tenant_id,
            dag_id=name,
            description=description or f"Spark job for {pyspark_app.name}",
            schedule_type=schedule_type,
            schedule_cron=schedule_cron,
            schedule_preset=schedule_preset,
            status=DagStatus.DRAFT,
            default_retries=retries,
            default_retry_delay_minutes=retry_delay_minutes,
            tags=["spark", "pyspark", str(pyspark_app_id)],
            created_by=created_by or "system",
        )
        
        # Create the spark_submit task
        task_config = TaskConfig(
            dag_config=dag_config,
            task_id=f"spark_submit_{pyspark_app.name.lower().replace(' ', '_')}",
            task_type=TaskType.SPARK_SUBMIT,
            config={
                "pyspark_app_id": pyspark_app_id,
                "spark_config": spark_config or {},
                "notifications": notifications or {},
            },
            timeout_minutes=120,
            retries=retries,
            retry_delay_minutes=retry_delay_minutes,
        )
        
        db.session.add(dag_config)
        db.session.add(task_config)
        db.session.commit()
        
        # Register with Dagster (if available)
        self._register_job_with_dagster(dag_config)
        
        return self._dag_to_job_dict(dag_config)
    
    def create_pipeline_job(
        self,
        pyspark_app_ids: List[str],
        name: str,
        description: Optional[str] = None,
        schedule: Optional[str] = None,
        parallel: bool = False,
        spark_config: Optional[Dict[str, Any]] = None,
        created_by: str = None,
    ) -> Dict[str, Any]:
        """Create a pipeline job that runs multiple PySpark apps."""
        # Validate UUID formats
        for app_id in pyspark_app_ids:
            try:
                UUID(str(app_id))
            except (ValueError, AttributeError):
                raise ValueError(f"Invalid PySpark app ID format: {app_id}")

        # Validate all PySpark apps exist
        apps = PySparkApp.query.filter(
            PySparkApp.id.in_(pyspark_app_ids),
            PySparkApp.tenant_id == self.tenant_id,
        ).all()
        
        if len(apps) != len(pyspark_app_ids):
            raise ValueError("One or more PySpark apps not found")
        
        # Generate safe name
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        dag_id = f"pipeline_{safe_name}"
        
        # Check for duplicate dag_id (exclude archived/deleted jobs)
        existing = DagConfig.query.filter(
            DagConfig.tenant_id == self.tenant_id,
            DagConfig.dag_id == dag_id,
            DagConfig.status != DagStatus.ARCHIVED,
        ).first()
        if existing:
            raise ValueError(
                f"A pipeline with the name '{name}' already exists. "
                f"Please choose a different name or edit the existing pipeline."
            )
        
        # Determine schedule type
        schedule_type = ScheduleType.MANUAL
        schedule_cron = None
        schedule_preset = None
        
        if schedule:
            if schedule.startswith("@"):
                schedule_type = ScheduleType.PRESET
                schedule_preset = schedule
            else:
                schedule_type = ScheduleType.CRON
                schedule_cron = schedule
        
        # Create the DagConfig
        dag_config = DagConfig(
            tenant_id=self.tenant_id,
            dag_id=dag_id,
            description=description or f"Pipeline executing {len(apps)} PySpark jobs",
            schedule_type=schedule_type,
            schedule_cron=schedule_cron,
            schedule_preset=schedule_preset,
            status=DagStatus.DRAFT,
            tags=["pipeline", "pyspark"] + pyspark_app_ids,
            created_by=created_by or "system",
        )
        
        db.session.add(dag_config)
        
        # Create tasks for each app
        previous_task_id = None
        for i, app in enumerate(apps):
            task_id = f"spark_{app.name.lower().replace(' ', '_')}"
            
            depends_on = []
            if not parallel and previous_task_id:
                depends_on = [previous_task_id]
            
            task_config = TaskConfig(
                dag_config=dag_config,
                task_id=task_id,
                task_type=TaskType.SPARK_SUBMIT,
                config={
                    "pyspark_app_id": str(app.id),
                    "spark_config": spark_config or {},
                },
                depends_on=depends_on,
                position_x=200 if parallel else 100,
                position_y=100 * (i + 1),
            )
            
            db.session.add(task_config)
            previous_task_id = task_id
        
        db.session.commit()
        
        # Register with Dagster
        self._register_job_with_dagster(dag_config)
        
        return self._dag_to_job_dict(dag_config)
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details by ID."""
        dag = DagConfig.query.filter(
            DagConfig.id == job_id,
            DagConfig.tenant_id == self.tenant_id,
        ).first()
        
        if not dag:
            # Try by dag_id (name)
            dag = DagConfig.query.filter(
                DagConfig.dag_id == job_id,
                DagConfig.tenant_id == self.tenant_id,
            ).first()
        
        if not dag:
            return None
        
        return self._dag_to_job_dict(dag, include_tasks=True)
    
    def update_job(
        self,
        job_id: str,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Update job configuration."""
        dag = DagConfig.query.filter(
            DagConfig.id == job_id,
            DagConfig.tenant_id == self.tenant_id,
        ).first()
        
        if not dag:
            return None
        
        # Update allowed fields
        allowed_fields = [
            "description", "schedule_type", "schedule_cron",
            "schedule_preset", "timezone", "default_retries",
            "default_retry_delay_minutes", "notification_emails",
            "email_on_failure", "email_on_success", "tags",
        ]
        
        for field in allowed_fields:
            if field in kwargs:
                value = kwargs[field]
                if field == "schedule_type" and isinstance(value, str):
                    value = ScheduleType(value)
                setattr(dag, field, value)
        
        db.session.commit()
        
        # Update Dagster registration
        self._update_job_in_dagster(dag)
        
        return self._dag_to_job_dict(dag)
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job (soft delete by archiving).
        
        The dag_id is suffixed with '__archived_<timestamp>' to free up
        the name for reuse, since the DB enforces a unique constraint
        on (tenant_id, dag_id).
        """
        dag = DagConfig.query.filter(
            DagConfig.id == job_id,
            DagConfig.tenant_id == self.tenant_id,
        ).first()
        
        if not dag:
            return False
        
        # Suffix the dag_id so the name can be reused for new jobs.
        # The unique constraint uq_tenant_dag_id prevents two rows
        # with the same (tenant_id, dag_id) regardless of status.
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        dag.dag_id = f"{dag.dag_id}__archived_{timestamp}"
        dag.status = DagStatus.ARCHIVED
        db.session.commit()
        
        # Remove from Dagster
        self._remove_job_from_dagster(dag)
        
        return True
    
    # =========================================================================
    # Job Execution
    # =========================================================================
    
    def trigger_job(
        self,
        job_id: str,
        run_config: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Trigger an immediate job run."""
        try:
            dag = DagConfig.query.filter(
                DagConfig.id == job_id,
                DagConfig.tenant_id == self.tenant_id,
            ).first()
        except Exception as e:
            logger.error(f"Database error looking up job {job_id}: {e}")
            return {
                "success": False,
                "error": "Failed to look up job",
                "error_type": "database_error",
            }
        
        if not dag:
            return None
        
        # Call Dagster API to trigger the job
        try:
            job_name = self._get_dagster_job_name(dag)
            repo_name = "__repository__"
            location_name = "novasight"
            
            response = requests.post(
                f"{self._dagster_url}/graphql",
                json={
                    "query": """
                        mutation LaunchRun($selector: JobOrPipelineSelector!, $runConfigData: RunConfigData) {
                            launchRun(executionParams: {
                                selector: $selector,
                                runConfigData: $runConfigData
                            }) {
                                __typename
                                ... on LaunchRunSuccess {
                                    run {
                                        runId
                                        status
                                    }
                                }
                                ... on RunConfigValidationInvalid {
                                    errors { message }
                                }
                                ... on PipelineNotFoundError {
                                    message
                                }
                                ... on PythonError {
                                    message
                                }
                            }
                        }
                    """,
                    "variables": {
                        "selector": {
                            "jobName": job_name,
                            "repositoryName": repo_name,
                            "repositoryLocationName": location_name,
                        },
                        "runConfigData": run_config or {},
                    },
                },
                timeout=30,
            )
            
            result = response.json()
            
            if result.get("data") and "launchRun" in result["data"]:
                launch_result = result["data"]["launchRun"]
                
                if launch_result["__typename"] == "LaunchRunSuccess":
                    return {
                        "success": True,
                        "run_id": launch_result["run"]["runId"],
                        "status": launch_result["run"]["status"],
                    }
                else:
                    error_msg = launch_result.get("message") or str(launch_result.get("errors", []))
                    return {
                        "success": False,
                        "error": error_msg,
                        "error_type": "dagster_error",
                    }
            
            return {
                "success": False,
                "error": self._extract_graphql_error(result, "Invalid response from Dagster"),
                "error_type": "dagster_error",
            }
        
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Dagster at {self._dagster_url} to trigger job {job_id}")
            return {
                "success": False,
                "error": "Cannot connect to Dagster. Please ensure the orchestration service is running.",
                "error_type": "dagster_unavailable",
            }
        
        except requests.exceptions.Timeout:
            logger.error(f"Timeout connecting to Dagster for job {job_id}")
            return {
                "success": False,
                "error": "Dagster request timed out. Please try again.",
                "error_type": "dagster_timeout",
            }
        
        except Exception as e:
            logger.error(f"Failed to trigger job {job_id}: {e}")
            return {
                "success": False,
                "error": f"Failed to trigger job: {str(e)}",
                "error_type": "unknown_error",
            }
    
    def pause_job(self, job_id: str) -> Optional[bool]:
        """Pause job scheduling."""
        dag = DagConfig.query.filter(
            DagConfig.id == job_id,
            DagConfig.tenant_id == self.tenant_id,
        ).first()
        
        if not dag:
            return None
        
        dag.status = DagStatus.PAUSED
        db.session.commit()
        
        # Update Dagster schedule
        self._pause_dagster_schedule(dag)
        
        return True
    
    def resume_job(self, job_id: str) -> Optional[bool]:
        """Resume job scheduling."""
        dag = DagConfig.query.filter(
            DagConfig.id == job_id,
            DagConfig.tenant_id == self.tenant_id,
        ).first()
        
        if not dag:
            return None
        
        dag.status = DagStatus.ACTIVE
        db.session.commit()
        
        # Update Dagster schedule
        self._resume_dagster_schedule(dag)
        
        return True
    
    # =========================================================================
    # Run History
    # =========================================================================
    
    def list_job_runs(
        self,
        job_id: str,
        page: int = 1,
        per_page: int = 25,
        status: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """List run history for a job."""
        dag = DagConfig.query.filter(
            DagConfig.id == job_id,
            DagConfig.tenant_id == self.tenant_id,
        ).first()
        
        if not dag:
            return None
        
        try:
            job_name = self._get_dagster_job_name(dag)
            
            # Query Dagster for runs
            response = requests.post(
                f"{self._dagster_url}/graphql",
                json={
                    "query": """
                        query GetRuns($filter: RunsFilter, $limit: Int) {
                            runsOrError(filter: $filter, limit: $limit) {
                                __typename
                                ... on Runs {
                                    results {
                                        runId
                                        status
                                        startTime
                                        endTime
                                        runConfigYaml
                                    }
                                    count
                                }
                            }
                        }
                    """,
                    "variables": {
                        "filter": {
                            "pipelineName": job_name,
                            "statuses": [status.upper()] if status else None,
                        },
                        "limit": per_page,
                    },
                },
                timeout=30,
            )
            
            result = response.json()
            
            if result.get("data"):
                runs_data = result["data"].get("runsOrError", {})
                if runs_data.get("__typename") == "Runs":
                    runs = runs_data.get("results", [])
                    total = runs_data.get("count", len(runs))
                    
                    return {
                        "runs": [
                            {
                                "run_id": r["runId"],
                                "status": r["status"],
                                "start_time": r.get("startTime"),
                                "end_time": r.get("endTime"),
                            }
                            for r in runs
                        ],
                        "total": total,
                        "page": page,
                        "per_page": per_page,
                    }
        
        except Exception as e:
            logger.error(f"Failed to list runs for job {job_id}: {e}")
        
        return {"runs": [], "total": 0, "page": page, "per_page": per_page}
    
    def get_job_run(self, job_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed run information."""
        try:
            response = requests.post(
                f"{self._dagster_url}/graphql",
                json={
                    "query": """
                        query GetRun($runId: ID!) {
                            runOrError(runId: $runId) {
                                __typename
                                ... on Run {
                                    runId
                                    status
                                    startTime
                                    endTime
                                    stats {
                                        ... on RunStatsSnapshot {
                                            stepsSucceeded
                                            stepsFailed
                                            materializations
                                            expectations
                                        }
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
                    """,
                    "variables": {"runId": run_id},
                },
                timeout=30,
            )
            
            result = response.json()
            
            if result.get("data"):
                run_data = result["data"].get("runOrError", {})
                if run_data.get("__typename") == "Run":
                    return {
                        "run_id": run_data["runId"],
                        "status": run_data["status"],
                        "start_time": run_data.get("startTime"),
                        "end_time": run_data.get("endTime"),
                        "stats": run_data.get("stats"),
                        "step_stats": run_data.get("stepStats", []),
                    }
        
        except Exception as e:
            logger.error(f"Failed to get run {run_id}: {e}")
        
        return None
    
    def get_job_run_logs(self, job_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """Get logs for a job run."""
        try:
            response = requests.post(
                f"{self._dagster_url}/graphql",
                json={
                    "query": """
                        query GetRunLogs($runId: ID!) {
                            logsForRun(runId: $runId) {
                                ... on EventConnection {
                                    events {
                                        ... on MessageEvent {
                                            timestamp
                                            level
                                            message
                                            stepKey
                                        }
                                    }
                                }
                            }
                        }
                    """,
                    "variables": {"runId": run_id},
                },
                timeout=30,
            )
            
            result = response.json()
            
            if result.get("data"):
                logs_data = result["data"].get("logsForRun", {})
                events = logs_data.get("events", [])
                
                return {
                    "logs": [
                        {
                            "timestamp": e.get("timestamp"),
                            "level": e.get("level"),
                            "message": e.get("message"),
                            "step": e.get("stepKey"),
                        }
                        for e in events
                        if e.get("message")
                    ]
                }
        
        except Exception as e:
            logger.error(f"Failed to get logs for run {run_id}: {e}")
        
        return None
    
    def cancel_job_run(self, job_id: str, run_id: str) -> Optional[bool]:
        """Cancel a running job."""
        try:
            response = requests.post(
                f"{self._dagster_url}/graphql",
                json={
                    "query": """
                        mutation TerminateRun($runId: String!) {
                            terminateRun(runId: $runId) {
                                __typename
                                ... on TerminateRunSuccess {
                                    run {
                                        runId
                                        status
                                    }
                                }
                            }
                        }
                    """,
                    "variables": {"runId": run_id},
                },
                timeout=30,
            )
            
            result = response.json()
            
            if result.get("data"):
                terminate_data = result["data"].get("terminateRun", {})
                return terminate_data.get("__typename") == "TerminateRunSuccess"
        
        except Exception as e:
            logger.error(f"Failed to cancel run {run_id}: {e}")
        
        return False
    

    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _dag_to_job_dict(
        self,
        dag: DagConfig,
        include_tasks: bool = False,
    ) -> Dict[str, Any]:
        """Convert DagConfig to job dictionary."""
        result = dag.to_dict(include_tasks=include_tasks)
        result["job_name"] = self._get_dagster_job_name(dag)
        tags = dag.tags or []
        result["type"] = "pipeline" if "pipeline" in tags else "spark"
        # Ensure tags is always a list in the response
        if result.get("tags") is None:
            result["tags"] = []
        return result
    
    def _get_dagster_job_name(self, dag: DagConfig) -> str:
        """
        Get the Dagster job name for a DagConfig.
        
        Must match the naming convention in DagsterJobBuilder.build_job_for_pyspark_app:
          safe_name = _make_safe_name(app_config.app_name)
          job_name  = f"spark_job_{safe_tenant}_{safe_name}"
        
        Since create_job stores dag_id = f"spark_{app_name}" we strip the
        'spark_' prefix.  For pipeline jobs (dag_id = "pipeline_...") we strip
        'pipeline_'.  Falls back to using dag_id as-is for unknown patterns.
        
        If the DagConfig has a task with a pyspark_app_id we try loading the app
        name directly — this is the most reliable path.
        """
        import re
        safe_tenant = str(dag.tenant_id).replace('-', '_')
        
        # Try to resolve app name from the PySpark app itself (most reliable)
        try:
            tasks = list(dag.tasks) if dag.tasks else []
            for task in tasks:
                app_id = (task.config or {}).get("pyspark_app_id")
                if app_id:
                    app = PySparkApp.query.get(app_id)
                    if app:
                        safe_name = re.sub(r'[^a-z0-9_]', '_', app.name.lower())[:50]
                        return f"spark_job_{safe_tenant}_{safe_name}"
        except Exception:
            pass  # Fallback to dag_id-based derivation
        
        # Fallback: derive from dag_id by stripping the prefix that create_job added
        raw_name = dag.dag_id.replace('-', '_')
        if raw_name.startswith('spark_'):
            raw_name = raw_name[len('spark_'):]
        elif raw_name.startswith('pipeline_'):
            raw_name = raw_name[len('pipeline_'):]
        
        return f"spark_job_{safe_tenant}_{raw_name}"
    
    @staticmethod
    def _extract_graphql_error(result: dict, fallback: str = "Unknown error") -> str:
        """Extract a human-readable error message from a Dagster GraphQL response."""
        errors = result.get("errors")
        if errors and isinstance(errors, list) and len(errors) > 0:
            return errors[0].get("message", fallback)
        return fallback
    
    def _get_last_run_status(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """Get last run status from Dagster."""
        # This would query Dagster API - returning None for now
        return None
    
    def _register_job_with_dagster(self, dag: DagConfig) -> bool:
        """Register job with Dagster by triggering a code location reload."""
        try:
            response = requests.post(
                f"{self._dagster_url}/graphql",
                json={
                    "query": """
                        mutation ReloadLocation($locationName: String!) {
                            reloadRepositoryLocation(
                                repositoryLocationName: $locationName
                            ) {
                                __typename
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
                            }
                        }
                    """,
                    "variables": {"locationName": "novasight"},
                },
                timeout=30,
            )
            result = response.json()
            logger.info(f"Dagster code location reload response: {result}")
            return True
        except Exception as e:
            logger.warning(f"Failed to reload Dagster code location: {e}")
            return False
    
    def _update_job_in_dagster(self, dag: DagConfig) -> bool:
        """Update job in Dagster by reloading code location."""
        return self._register_job_with_dagster(dag)
    
    def _remove_job_from_dagster(self, dag: DagConfig) -> bool:
        """Remove job from Dagster by reloading code location."""
        return self._register_job_with_dagster(dag)
    
    def _pause_dagster_schedule(self, dag: DagConfig) -> bool:
        """Pause schedule in Dagster."""
        try:
            schedule_name = f"schedule_spark_job_{str(dag.tenant_id).replace('-', '_')}_{dag.dag_id}"
            
            response = requests.post(
                f"{self._dagster_url}/graphql",
                json={
                    "query": """
                        mutation StopSchedule($scheduleName: String!) {
                            stopRunningSchedule(scheduleSelectorData: {
                                scheduleName: $scheduleName
                            }) {
                                __typename
                            }
                        }
                    """,
                    "variables": {"scheduleName": schedule_name},
                },
                timeout=30,
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to pause schedule: {e}")
            return False
    
    def _resume_dagster_schedule(self, dag: DagConfig) -> bool:
        """Resume schedule in Dagster."""
        try:
            schedule_name = f"schedule_spark_job_{str(dag.tenant_id).replace('-', '_')}_{dag.dag_id}"
            
            response = requests.post(
                f"{self._dagster_url}/graphql",
                json={
                    "query": """
                        mutation StartSchedule($scheduleName: String!) {
                            startSchedule(scheduleSelectorData: {
                                scheduleName: $scheduleName
                            }) {
                                __typename
                            }
                        }
                    """,
                    "variables": {"scheduleName": schedule_name},
                },
                timeout=30,
            )
            
            return True
        except Exception as e:
            logger.error(f"Failed to resume schedule: {e}")
            return False
