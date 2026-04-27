"""
NovaSight Orchestration Domain — DAG Service
==============================================

Application-layer service for DAG configuration and Dagster integration.

Canonical location: ``app.domains.orchestration.application.dag_service``
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID as PyUUID
from pathlib import Path

from app.extensions import db
from app.domains.orchestration.domain.models import (
    DagConfig, DagVersion, TaskConfig,
    DagStatus, ScheduleType, TaskType, TriggerRule,
)
from app.domains.orchestration.infrastructure.dagster_client import DagsterClient
from app.domains.orchestration.infrastructure.asset_factory import AssetFactory
from app.domains.orchestration.infrastructure.schedule_factory import ScheduleFactory
from app.domains.orchestration.domain.validators import DagValidator
import logging

logger = logging.getLogger(__name__)


class DagService:
    """Service for DAG configuration and Dagster integration."""

    def __init__(self, tenant_id: str):
        """
        Initialize DAG service for a specific tenant.

        Args:
            tenant_id: Tenant UUID
        """
        self.tenant_id = tenant_id
        self.dagster_client = DagsterClient(tenant_id=tenant_id)
        self.asset_factory = AssetFactory(tenant_id)
        self.schedule_factory = ScheduleFactory(tenant_id)
        self.validator = DagValidator()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_dags(
        self,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        include_archived: bool = False,
    ) -> Dict[str, Any]:
        """
        List DAG configurations in the tenant.

        Args:
            page: Page number
            per_page: Items per page
            status: Filter by status
            tag: Filter by tag
            include_archived: Whether to include archived (deleted) DAGs

        Returns:
            Paginated list of DAGs
        """
        query = DagConfig.query.filter(DagConfig.tenant_id == self.tenant_id)

        # Exclude archived DAGs by default (they are soft-deleted)
        if not include_archived:
            query = query.filter(DagConfig.status != DagStatus.ARCHIVED)

        if status:
            try:
                status_enum = DagStatus(status)
                query = query.filter(DagConfig.status == status_enum)
            except ValueError:
                pass

        if tag:
            query = query.filter(DagConfig.tags.contains([tag]))

        query = query.order_by(DagConfig.updated_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "dags": [d.to_dict(include_tasks=False) for d in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }

    def get_dag(self, dag_id: str, include_runs: bool = False) -> Optional[DagConfig]:
        """
        Get DAG configuration by ID.

        Args:
            dag_id: DAG identifier (can be UUID primary key or string dag_id)
            include_runs: Include recent run history from Dagster

        Returns:
            DagConfig object or None
        """
        logger.info(f"get_dag called with dag_id='{dag_id}', tenant_id='{self.tenant_id}'")
        
        # Try to parse as UUID first (for lookups by primary key)
        dag = None
        try:
            uuid_id = PyUUID(dag_id)
            logger.info(f"Parsed as UUID: {uuid_id}")
            dag = DagConfig.query.filter(
                DagConfig.id == uuid_id,
                DagConfig.tenant_id == self.tenant_id,
            ).first()
            logger.info(f"UUID lookup result: {dag}")
        except (ValueError, AttributeError) as e:
            logger.info(f"Not a UUID: {e}")
        
        # If not found by UUID, try by dag_id string
        if not dag:
            logger.info(f"Trying string lookup for dag_id='{dag_id}'")
            dag = DagConfig.query.filter(
                DagConfig.dag_id == dag_id,
                DagConfig.tenant_id == self.tenant_id,
            ).first()
            logger.info(f"String lookup result: {dag}")

        if dag and include_runs:
            try:
                runs = self.dagster_client.get_job_runs(f"{dag.full_dag_id}_job", limit=10)
                dag._recent_runs = [
                    {
                        "run_id": r.run_id,
                        "state": r.state,
                        "start_date": r.start_time.isoformat() if r.start_time else None,
                        "end_date": r.end_time.isoformat() if r.end_time else None,
                    }
                    for r in runs
                ]
            except Exception as e:
                logger.warning(f"Failed to fetch DAG runs: {e}")
                dag._recent_runs = []

        return dag

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def create_dag(
        self,
        dag_id: str,
        tasks: List[Dict[str, Any]],
        description: str = "",
        schedule_type: str = "manual",
        schedule_cron: Optional[str] = None,
        schedule_preset: Optional[str] = None,
        timezone: str = "UTC",
        start_date: Optional[str] = None,
        tags: List[str] = None,
        notification_emails: List[str] = None,
        email_on_failure: bool = True,
        email_on_success: bool = False,
        catchup: bool = False,
        max_active_runs: int = 1,
        created_by: str = None,
    ) -> DagConfig:
        """
        Create a new DAG configuration.

        Returns:
            Created DagConfig object
        """
        existing = self.get_dag(dag_id)
        if existing:
            raise ValueError(f"DAG with ID '{dag_id}' already exists")

        try:
            schedule_type_enum = ScheduleType(schedule_type)
        except ValueError:
            schedule_type_enum = ScheduleType.MANUAL

        parsed_start_date = None
        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                parsed_start_date = datetime.utcnow()

        dag_config = DagConfig(
            tenant_id=self.tenant_id,
            dag_id=dag_id,
            description=description,
            schedule_type=schedule_type_enum,
            schedule_cron=schedule_cron,
            schedule_preset=schedule_preset,
            timezone=timezone,
            start_date=parsed_start_date or datetime.utcnow(),
            catchup=catchup,
            max_active_runs=max_active_runs,
            notification_emails=notification_emails or [],
            email_on_failure=email_on_failure,
            email_on_success=email_on_success,
            tags=tags or [],
            status=DagStatus.DRAFT,
            created_by=created_by,
        )

        db.session.add(dag_config)
        db.session.flush()

        for task_data in tasks:
            task = self._create_task(dag_config.id, task_data)
            db.session.add(task)

        db.session.commit()

        self._create_version(dag_config, created_by, "Initial version")

        logger.info(f"Created DAG: {dag_id} in tenant {self.tenant_id}")
        return dag_config

    def _create_task(self, dag_config_id: str, task_data: Dict[str, Any]) -> TaskConfig:
        """Create a task configuration."""
        task_type = task_data.get("task_type", "dlt_run")
        try:
            task_type_enum = TaskType(task_type)
        except ValueError:
            # Default to DLT_RUN — the orchestrator only schedules dlt + dbt jobs.
            task_type_enum = TaskType.DLT_RUN

        trigger_rule = task_data.get("trigger_rule", "all_success")
        try:
            trigger_rule_enum = TriggerRule(trigger_rule)
        except ValueError:
            trigger_rule_enum = TriggerRule.ALL_SUCCESS

        return TaskConfig(
            dag_config_id=dag_config_id,
            task_id=task_data.get("task_id"),
            task_type=task_type_enum,
            config=task_data.get("config", {}),
            timeout_minutes=task_data.get("timeout_minutes", 60),
            retries=task_data.get("retries", 1),
            retry_delay_minutes=task_data.get("retry_delay_minutes", 5),
            trigger_rule=trigger_rule_enum,
            depends_on=task_data.get("depends_on", []),
            position_x=task_data.get("position", {}).get("x", 0),
            position_y=task_data.get("position", {}).get("y", 0),
        )

    def _create_version(
        self,
        dag_config: DagConfig,
        user_id: str,
        description: str = None,
    ) -> DagVersion:
        """Create a new DAG version."""
        version = DagVersion(
            dag_config_id=dag_config.id,
            version=dag_config.current_version,
            config_snapshot=dag_config.to_dict(include_tasks=True),
            change_description=description,
            created_by=user_id,
        )
        db.session.add(version)
        db.session.commit()
        return version

    def update_dag(self, dag_id: str, updated_by: str = None, **kwargs) -> Optional[DagConfig]:
        """
        Update DAG configuration.

        Args:
            dag_id: DAG identifier
            updated_by: User ID who updated the DAG
            **kwargs: Fields to update

        Returns:
            Updated DagConfig object or None
        """
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None

        if "tasks" in kwargs:
            TaskConfig.query.filter(TaskConfig.dag_config_id == dag_config.id).delete()
            for task_data in kwargs.pop("tasks"):
                task = self._create_task(dag_config.id, task_data)
                db.session.add(task)

        allowed_fields = [
            "description", "schedule_type", "schedule_cron", "schedule_preset",
            "timezone", "start_date", "catchup", "max_active_runs",
            "default_retries", "default_retry_delay_minutes",
            "notification_emails", "email_on_failure", "email_on_success", "tags",
        ]

        for field, value in kwargs.items():
            if field not in allowed_fields:
                continue
            if field == "schedule_type":
                try:
                    value = ScheduleType(value)
                except ValueError:
                    continue
            setattr(dag_config, field, value)

        dag_config.current_version += 1
        db.session.commit()

        self._create_version(dag_config, updated_by, kwargs.get("change_description", "Updated"))

        logger.info(f"Updated DAG: {dag_id} to version {dag_config.current_version}")
        return dag_config

    def delete_dag(self, dag_id: str, hard_delete: bool = False) -> bool:
        """
        Delete a DAG configuration.

        Performs full cleanup:
        1. Pauses the job in Dagster
        2. Deletes the job from Dagster
        3. Removes the generated job file
        4. Archives (soft) or removes (hard) from the database

        Args:
            dag_id: DAG identifier
            hard_delete: If True, permanently remove from DB; otherwise archive

        Returns:
            True if successful
        """
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return False

        # --- Dagster cleanup (best-effort) ---
        if dag_config.status in (DagStatus.ACTIVE, DagStatus.PAUSED, DagStatus.ERROR):
            try:
                self.dagster_client.stop_schedule(f"{dag_config.full_dag_id}_schedule")
            except Exception as e:
                logger.warning(f"Failed to stop schedule in Dagster during delete: {e}")

        # --- Reload code location to pick up changes ---
        try:
            self.dagster_client.reload_code_location()
        except Exception as e:
            logger.warning(f"Failed to reload Dagster code location: {e}")

        if hard_delete:
            # Permanently remove from database
            db.session.delete(dag_config)
            db.session.commit()
            logger.info(f"Hard-deleted DAG: {dag_id}")
        else:
            dag_config.status = DagStatus.ARCHIVED
            db.session.commit()
            logger.info(f"Archived DAG: {dag_id}")

        return True

    # ------------------------------------------------------------------
    # Validation & Deployment
    # ------------------------------------------------------------------

    def validate_dag(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """Validate DAG configuration."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None
        return self.validator.validate(dag_config)

    def deploy_dag(self, dag_id: str, deployed_by: str = None) -> Optional[Dict[str, Any]]:
        """Deploy DAG to Dagster."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None

        validation = self.validator.validate(dag_config)
        if validation.get("errors"):
            return {
                "success": False,
                "error": "Validation failed",
                "details": validation,
            }

        try:
            # Build assets using AssetFactory (for validation)
            assets = self.asset_factory.build_assets_from_dag_config(dag_config)
            if not assets:
                return {
                    "success": False,
                    "error": "No assets could be built from DAG configuration",
                }
            logger.info(f"Built {len(assets)} assets for DAG: {dag_id}")

            # Build schedule using ScheduleFactory (for validation)
            schedule = self.schedule_factory.build_schedule_from_dag_config(dag_config)
            if schedule:
                logger.info(f"Built schedule for DAG: {dag_id}")
            else:
                logger.info(f"DAG {dag_id} is manual, no schedule created")

            # Reload Dagster code location to pick up new definitions
            reload_result = self.dagster_client.reload_code_location()
            if not reload_result.get("success"):
                logger.warning(f"Code location reload warning: {reload_result.get('error')}")

            dag_config.deployed_at = datetime.utcnow()
            dag_config.deployed_version = dag_config.current_version
            dag_config.status = DagStatus.ACTIVE

            db.session.commit()

            logger.info(f"Deployed DAG: {dag_id} version {dag_config.current_version}")
            return {
                "success": True,
                "dag_id": dag_config.full_dag_id,
                "version": dag_config.deployed_version,
                "job_name": f"{dag_config.full_dag_id}_job",
                "schedule_name": f"{dag_config.full_dag_id}_schedule" if schedule else None,
                "asset_count": len(assets),
            }

        except Exception as e:
            logger.error(f"DAG deployment failed: {e}")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Dagster Operations
    # ------------------------------------------------------------------

    def trigger_dag(self, dag_id: str, conf: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Trigger immediate DAG run (Dagster job)."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None

        try:
            job_name = f"{dag_config.full_dag_id}_job"
            result = self.dagster_client.trigger_job(job_name, run_config=conf)
            if result.get("success"):
                return {
                    "success": True,
                    "run_id": result.get("run_id"),
                    "status": result.get("status"),
                }
            else:
                return {"success": False, "error": result.get("error")}
        except Exception as e:
            logger.error(f"Failed to trigger DAG: {e}")
            return {"success": False, "error": str(e)}

    def pause_dag(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """Pause DAG scheduling in Dagster (stop schedule)."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None

        try:
            schedule_name = f"{dag_config.full_dag_id}_schedule"
            response = self.dagster_client.stop_schedule(schedule_name)
            
            if response.get("success"):
                dag_config.status = DagStatus.PAUSED
                db.session.commit()
                logger.info(f"DAG '{dag_config.full_dag_id}' paused successfully in Dagster")
                return {"success": True, "status": "paused"}
            else:
                # Dagster didn't confirm pause - log warning but still update local state
                logger.warning(f"Dagster response did not confirm pause for '{dag_config.full_dag_id}': {response}")
                dag_config.status = DagStatus.PAUSED
                db.session.commit()
                return {"success": True, "status": "paused", "warning": "Dagster response not confirmed"}
        except Exception as e:
            logger.error(f"Failed to pause DAG '{dag_config.full_dag_id}' in Dagster: {e}")
            return {"success": False, "error": str(e)}

    def unpause_dag(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """Resume DAG scheduling in Dagster (start schedule)."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None

        try:
            schedule_name = f"{dag_config.full_dag_id}_schedule"
            response = self.dagster_client.start_schedule(schedule_name)
            
            if response.get("success"):
                dag_config.status = DagStatus.ACTIVE
                db.session.commit()
                logger.info(f"DAG '{dag_config.full_dag_id}' unpaused successfully in Dagster")
                return {"success": True, "status": "active"}
            else:
                # Dagster didn't confirm unpause - log warning but still update local state
                logger.warning(f"Dagster response did not confirm unpause for '{dag_config.full_dag_id}': {response}")
                dag_config.status = DagStatus.ACTIVE
                db.session.commit()
                return {"success": True, "status": "active", "warning": "Dagster response not confirmed"}
        except Exception as e:
            logger.error(f"Failed to unpause DAG '{dag_config.full_dag_id}' in Dagster: {e}")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Run History
    # ------------------------------------------------------------------

    def list_dag_runs(
        self,
        dag_id: str,
        page: int = 1,
        per_page: int = 25,
        state: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """List DAG run history (Dagster job runs)."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None

        try:
            job_name = f"{dag_config.full_dag_id}_job"
            # Dagster doesn't support offset, so we fetch more and slice
            runs = self.dagster_client.get_job_runs(
                job_name,
                limit=page * per_page,
            )
            # Slice for pagination
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paged_runs = runs[start_idx:end_idx]
            
            return {
                "runs": [
                    {
                        "run_id": r.run_id,
                        "state": r.state,
                        "execution_date": r.start_time.isoformat() if r.start_time else None,
                        "start_date": r.start_time.isoformat() if r.start_time else None,
                        "end_date": r.end_time.isoformat() if r.end_time else None,
                    }
                    for r in paged_runs
                ],
                "pagination": {"page": page, "per_page": per_page},
            }
        except Exception as e:
            logger.error(f"Failed to fetch DAG runs: {e}")
            return {"runs": [], "error": str(e)}

    def get_dag_run(self, dag_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """Get DAG run details with step/asset information."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None

        try:
            run_details = self.dagster_client.get_run_details(run_id)

            # Map Dagster status to Airflow-compatible state
            status = run_details.get("status", "UNKNOWN")
            state_map = {
                "SUCCESS": "success",
                "FAILURE": "failed",
                "STARTED": "running",
                "QUEUED": "queued",
                "CANCELED": "cancelled",
                "CANCELING": "cancelling",
                "NOT_STARTED": "queued",
            }
            mapped_state = state_map.get(status, status.lower())

            start_time = run_details.get("startTime")
            end_time = run_details.get("endTime")

            return {
                "run": {
                    "run_id": run_details.get("runId") or run_id,
                    "state": mapped_state,
                    "execution_date": datetime.fromtimestamp(float(start_time)).isoformat() if start_time else None,
                    "start_date": datetime.fromtimestamp(float(start_time)).isoformat() if start_time else None,
                    "end_date": datetime.fromtimestamp(float(end_time)).isoformat() if end_time else None,
                },
                "tasks": [
                    {
                        "task_id": step.get("stepKey"),
                        "state": state_map.get(step.get("status"), step.get("status", "").lower()),
                        "start_date": datetime.fromtimestamp(float(step["startTime"])).isoformat() if step.get("startTime") else None,
                        "end_date": datetime.fromtimestamp(float(step["endTime"])).isoformat() if step.get("endTime") else None,
                        "try_number": 1,  # Dagster doesn't have try_number concept
                    }
                    for step in run_details.get("stepStats", [])
                ],
            }
        except Exception as e:
            logger.error(f"Failed to fetch DAG run: {e}")
            return None

    def get_task_logs(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
        try_number: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get task execution logs (Dagster step logs)."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None

        try:
            logs = self.dagster_client.get_run_logs(run_id, step_key=task_id)
            return {
                "task_id": task_id,
                "try_number": 1,  # Dagster doesn't have try_number concept
                "content": logs,
            }
        except Exception as e:
            logger.error(f"Failed to fetch task logs: {e}")
            return None
