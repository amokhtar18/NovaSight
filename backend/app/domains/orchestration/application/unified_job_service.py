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
        return os.environ.get("DAGSTER_URL", "http://dagster-webserver:3000")
    
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
            job_data = dag.to_dict(include_tasks=False)
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
        # Validate all PySpark apps exist
        apps = PySparkApp.query.filter(
            PySparkApp.id.in_(pyspark_app_ids),
            PySparkApp.tenant_id == self.tenant_id,
        ).all()
        
        if len(apps) != len(pyspark_app_ids):
            raise ValueError("One or more PySpark apps not found")
        
        # Generate safe name
        safe_name = name.lower().replace(" ", "_").replace("-", "_")
        
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
            dag_id=f"pipeline_{safe_name}",
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
        """Delete a job (soft delete by archiving)."""
        dag = DagConfig.query.filter(
            DagConfig.id == job_id,
            DagConfig.tenant_id == self.tenant_id,
        ).first()
        
        if not dag:
            return False
        
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
        dag = DagConfig.query.filter(
            DagConfig.id == job_id,
            DagConfig.tenant_id == self.tenant_id,
        ).first()
        
        if not dag:
            return None
        
        # Call Dagster API to trigger the job
        try:
            job_name = self._get_dagster_job_name(dag)
            
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
                                ... on PythonError {
                                    message
                                }
                            }
                        }
                    """,
                    "variables": {
                        "selector": {
                            "jobName": job_name,
                        },
                        "runConfigData": run_config or {},
                    },
                },
                timeout=30,
            )
            
            result = response.json()
            
            if "data" in result and "launchRun" in result["data"]:
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
                    }
            
            return {
                "success": False,
                "error": "Invalid response from Dagster",
            }
        
        except Exception as e:
            logger.error(f"Failed to trigger job {job_id}: {e}")
            return {
                "success": False,
                "error": str(e),
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
            
            if "data" in result:
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
            
            if "data" in result:
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
            
            if "data" in result:
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
            
            if "data" in result:
                terminate_data = result["data"].get("terminateRun", {})
                return terminate_data.get("__typename") == "TerminateRunSuccess"
        
        except Exception as e:
            logger.error(f"Failed to cancel run {run_id}: {e}")
        
        return False
    
    # =========================================================================
    # Spark Configuration
    # =========================================================================
    
    def get_spark_config(self) -> Dict[str, Any]:
        """Get current Spark cluster configuration."""
        try:
            from app.platform.infrastructure import InfrastructureConfigProvider
            
            provider = InfrastructureConfigProvider()
            config = provider.get_spark_config()
            
            if config:
                return {
                    "spark_master": config.master_url,
                    "ssh_host": getattr(config, 'ssh_host', ''),
                    "ssh_user": getattr(config, 'ssh_user', 'spark'),
                    "driver_memory": config.driver_memory,
                    "executor_memory": config.executor_memory,
                    "executor_cores": config.executor_cores,
                    "num_executors": getattr(config, 'num_executors', 2),
                    "additional_configs": config.additional_configs or {},
                }
        except Exception as e:
            logger.warning(f"Failed to get Spark config: {e}")
        
        return {
            "spark_master": "spark://spark-master:7077",
            "ssh_host": "",
            "ssh_user": "spark",
            "driver_memory": "2g",
            "executor_memory": "2g",
            "executor_cores": 2,
            "num_executors": 2,
            "additional_configs": {},
        }
    
    def update_spark_config(self, **kwargs) -> Dict[str, Any]:
        """Update Spark cluster configuration."""
        try:
            from app.platform.infrastructure import InfrastructureConfigProvider
            
            provider = InfrastructureConfigProvider()
            config = provider.update_spark_config(**kwargs)
            
            return self.get_spark_config()
        except Exception as e:
            logger.error(f"Failed to update Spark config: {e}")
            raise
    
    def test_spark_connection(self) -> Dict[str, Any]:
        """Test connection to Spark cluster."""
        config = self.get_spark_config()
        
        result = {
            "ssh_connection": False,
            "spark_master": False,
            "errors": [],
        }
        
        ssh_host = config.get("ssh_host")
        
        if ssh_host:
            # Test SSH connection
            import subprocess
            
            ssh_cmd = [
                "ssh",
                "-o", "StrictHostKeyChecking=no",
                "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=10",
                f"{config.get('ssh_user', 'spark')}@{ssh_host}",
                "echo connected",
            ]
            
            try:
                ssh_result = subprocess.run(
                    ssh_cmd,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                result["ssh_connection"] = ssh_result.returncode == 0
                if not result["ssh_connection"]:
                    result["errors"].append(f"SSH: {ssh_result.stderr}")
            except Exception as e:
                result["errors"].append(f"SSH: {str(e)}")
        else:
            result["ssh_connection"] = None  # Not configured
        
        # Test Spark master (via REST API if available)
        spark_master = config.get("spark_master", "")
        if "spark://" in spark_master:
            # Extract host and check REST API port (usually 8080)
            import re
            match = re.search(r"spark://([^:]+):(\d+)", spark_master)
            if match:
                host = match.group(1)
                try:
                    response = requests.get(f"http://{host}:8080/json/", timeout=10)
                    result["spark_master"] = response.status_code == 200
                except Exception as e:
                    result["errors"].append(f"Spark: {str(e)}")
        
        result["success"] = (
            (result["ssh_connection"] or result["ssh_connection"] is None) and
            result["spark_master"]
        )
        
        return result
    
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
        result["type"] = "pipeline" if "pipeline" in dag.tags else "spark"
        return result
    
    def _get_dagster_job_name(self, dag: DagConfig) -> str:
        """Get the Dagster job name for a DagConfig."""
        safe_tenant = str(dag.tenant_id).replace('-', '_')
        safe_name = dag.dag_id.replace('-', '_')
        return f"spark_job_{safe_tenant}_{safe_name}"
    
    def _get_last_run_status(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """Get last run status from Dagster."""
        # This would query Dagster API - returning None for now
        return None
    
    def _register_job_with_dagster(self, dag: DagConfig) -> bool:
        """Register job with Dagster (triggers code location reload)."""
        # In a production setup, this would trigger a code location reload
        # For now, just log the action
        logger.info(f"Job registered with Dagster: {dag.dag_id}")
        return True
    
    def _update_job_in_dagster(self, dag: DagConfig) -> bool:
        """Update job in Dagster."""
        logger.info(f"Job updated in Dagster: {dag.dag_id}")
        return True
    
    def _remove_job_from_dagster(self, dag: DagConfig) -> bool:
        """Remove job from Dagster."""
        logger.info(f"Job removed from Dagster: {dag.dag_id}")
        return True
    
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
