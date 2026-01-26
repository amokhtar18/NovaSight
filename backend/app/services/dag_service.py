"""
NovaSight DAG Service
=====================

DAG configuration and Airflow integration.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from app.extensions import db
from app.models.dag import DagConfig, DagVersion, TaskConfig, DagStatus, ScheduleType, TaskType, TriggerRule
from app.services.airflow_client import AirflowClient
from app.services.dag_validator import DagValidator
from app.services.dag_generator import DagGenerator
import logging

logger = logging.getLogger(__name__)


class DagService:
    """Service for DAG configuration and Airflow integration."""
    
    def __init__(self, tenant_id: str):
        """
        Initialize DAG service for a specific tenant.
        
        Args:
            tenant_id: Tenant UUID
        """
        self.tenant_id = tenant_id
        self.airflow_client = AirflowClient()
        self.validator = DagValidator()
        self.generator = DagGenerator(tenant_id)
    
    def list_dags(
        self,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List DAG configurations in the tenant.
        
        Args:
            page: Page number
            per_page: Items per page
            status: Filter by status
            tag: Filter by tag
        
        Returns:
            Paginated list of DAGs
        """
        query = DagConfig.query.filter(DagConfig.tenant_id == self.tenant_id)
        
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
            }
        }
    
    def get_dag(self, dag_id: str, include_runs: bool = False) -> Optional[DagConfig]:
        """
        Get DAG configuration by ID.
        
        Args:
            dag_id: DAG identifier
            include_runs: Include recent run history from Airflow
        
        Returns:
            DagConfig object or None
        """
        dag = DagConfig.query.filter(
            DagConfig.dag_id == dag_id,
            DagConfig.tenant_id == self.tenant_id
        ).first()
        
        if dag and include_runs:
            # Fetch run history from Airflow
            try:
                runs = self.airflow_client.get_dag_runs(dag.full_dag_id, limit=10)
                dag._recent_runs = runs
            except Exception as e:
                logger.warning(f"Failed to fetch DAG runs: {e}")
                dag._recent_runs = []
        
        return dag
    
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
        created_by: str = None
    ) -> DagConfig:
        """
        Create a new DAG configuration.
        
        Args:
            dag_id: Unique DAG identifier
            tasks: List of task configurations
            description: DAG description
            schedule_type: Schedule type (manual, cron, preset)
            schedule_cron: CRON expression
            schedule_preset: Preset schedule name
            timezone: Execution timezone
            start_date: DAG start date
            tags: List of tags
            notification_emails: Email addresses for notifications
            email_on_failure: Send email on failure
            email_on_success: Send email on success
            catchup: Enable catchup
            max_active_runs: Maximum active runs
            created_by: User ID who created the DAG
        
        Returns:
            Created DagConfig object
        """
        # Check for existing DAG
        existing = self.get_dag(dag_id)
        if existing:
            raise ValueError(f"DAG with ID '{dag_id}' already exists")
        
        # Parse schedule type
        try:
            schedule_type_enum = ScheduleType(schedule_type)
        except ValueError:
            schedule_type_enum = ScheduleType.MANUAL
        
        # Parse start date
        parsed_start_date = None
        if start_date:
            try:
                parsed_start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            except ValueError:
                parsed_start_date = datetime.utcnow()
        
        # Create DAG config
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
        db.session.flush()  # Get the ID
        
        # Create tasks
        for task_data in tasks:
            task = self._create_task(dag_config.id, task_data)
            db.session.add(task)
        
        db.session.commit()
        
        # Create initial version
        self._create_version(dag_config, created_by, "Initial version")
        
        logger.info(f"Created DAG: {dag_id} in tenant {self.tenant_id}")
        
        return dag_config
    
    def _create_task(self, dag_config_id: str, task_data: Dict[str, Any]) -> TaskConfig:
        """Create a task configuration."""
        task_type = task_data.get("task_type", "python_operator")
        try:
            task_type_enum = TaskType(task_type)
        except ValueError:
            task_type_enum = TaskType.PYTHON_OPERATOR
        
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
        description: str = None
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
        
        # Update tasks if provided
        if "tasks" in kwargs:
            # Remove existing tasks
            TaskConfig.query.filter(TaskConfig.dag_config_id == dag_config.id).delete()
            
            # Create new tasks
            for task_data in kwargs.pop("tasks"):
                task = self._create_task(dag_config.id, task_data)
                db.session.add(task)
        
        # Update other fields
        allowed_fields = [
            "description", "schedule_type", "schedule_cron", "schedule_preset",
            "timezone", "start_date", "catchup", "max_active_runs",
            "default_retries", "default_retry_delay_minutes",
            "notification_emails", "email_on_failure", "email_on_success", "tags"
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
        
        # Increment version
        dag_config.current_version += 1
        
        db.session.commit()
        
        # Create new version
        self._create_version(dag_config, updated_by, kwargs.get("change_description", "Updated"))
        
        logger.info(f"Updated DAG: {dag_id} to version {dag_config.current_version}")
        
        return dag_config
    
    def delete_dag(self, dag_id: str) -> bool:
        """
        Delete a DAG configuration.
        
        Args:
            dag_id: DAG identifier
        
        Returns:
            True if successful
        """
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return False
        
        # Archive instead of hard delete
        dag_config.status = DagStatus.ARCHIVED
        db.session.commit()
        
        logger.info(f"Archived DAG: {dag_id}")
        
        return True
    
    def validate_dag(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """
        Validate DAG configuration.
        
        Args:
            dag_id: DAG identifier
        
        Returns:
            Validation result with errors and warnings
        """
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None
        
        return self.validator.validate(dag_config)
    
    def deploy_dag(self, dag_id: str, deployed_by: str = None) -> Optional[Dict[str, Any]]:
        """
        Deploy DAG to Airflow.
        
        Args:
            dag_id: DAG identifier
            deployed_by: User ID who deployed the DAG
        
        Returns:
            Deployment result
        """
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None
        
        # Validate first
        validation = self.validator.validate(dag_config)
        if validation.get("errors"):
            return {
                "success": False,
                "error": "Validation failed",
                "details": validation,
            }
        
        try:
            # Generate DAG file
            dag_file_content = self.generator.generate(dag_config)
            
            # Deploy to Airflow (write to DAGs folder or use API)
            # This is a placeholder - actual deployment depends on infrastructure
            
            # Update deployment tracking
            dag_config.deployed_at = datetime.utcnow()
            dag_config.deployed_version = dag_config.current_version
            dag_config.status = DagStatus.ACTIVE
            
            db.session.commit()
            
            logger.info(f"Deployed DAG: {dag_id} version {dag_config.current_version}")
            
            return {
                "success": True,
                "dag_id": dag_config.full_dag_id,
                "version": dag_config.deployed_version,
            }
            
        except Exception as e:
            logger.error(f"DAG deployment failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def trigger_dag(self, dag_id: str, conf: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Trigger immediate DAG run.
        
        Args:
            dag_id: DAG identifier
            conf: Optional run configuration
        
        Returns:
            Triggered run details
        """
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None
        
        try:
            run = self.airflow_client.trigger_dag(dag_config.full_dag_id, conf)
            return {
                "success": True,
                "run_id": run.run_id,
                "execution_date": run.execution_date.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to trigger DAG: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    def pause_dag(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """Pause DAG scheduling."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None
        
        try:
            self.airflow_client.pause_dag(dag_config.full_dag_id)
            dag_config.status = DagStatus.PAUSED
            db.session.commit()
            
            return {"success": True, "status": "paused"}
        except Exception as e:
            logger.error(f"Failed to pause DAG: {e}")
            return {"success": False, "error": str(e)}
    
    def unpause_dag(self, dag_id: str) -> Optional[Dict[str, Any]]:
        """Resume DAG scheduling."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None
        
        try:
            self.airflow_client.unpause_dag(dag_config.full_dag_id)
            dag_config.status = DagStatus.ACTIVE
            db.session.commit()
            
            return {"success": True, "status": "active"}
        except Exception as e:
            logger.error(f"Failed to unpause DAG: {e}")
            return {"success": False, "error": str(e)}
    
    def list_dag_runs(
        self,
        dag_id: str,
        page: int = 1,
        per_page: int = 25,
        state: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """List DAG run history."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None
        
        try:
            offset = (page - 1) * per_page
            runs = self.airflow_client.get_dag_runs(
                dag_config.full_dag_id,
                limit=per_page,
                offset=offset
            )
            
            return {
                "runs": [
                    {
                        "run_id": r.run_id,
                        "state": r.state,
                        "execution_date": r.execution_date.isoformat(),
                        "start_date": r.start_date.isoformat() if r.start_date else None,
                        "end_date": r.end_date.isoformat() if r.end_date else None,
                    }
                    for r in runs
                ],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                }
            }
        except Exception as e:
            logger.error(f"Failed to fetch DAG runs: {e}")
            return {"runs": [], "error": str(e)}
    
    def get_dag_run(self, dag_id: str, run_id: str) -> Optional[Dict[str, Any]]:
        """Get DAG run details with task instances."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None
        
        try:
            run = self.airflow_client.get_dag_run(dag_config.full_dag_id, run_id)
            tasks = self.airflow_client.get_task_instances(dag_config.full_dag_id, run_id)
            
            return {
                "run": {
                    "run_id": run.run_id,
                    "state": run.state,
                    "execution_date": run.execution_date.isoformat(),
                    "start_date": run.start_date.isoformat() if run.start_date else None,
                    "end_date": run.end_date.isoformat() if run.end_date else None,
                },
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "state": t.state,
                        "start_date": t.start_date.isoformat() if t.start_date else None,
                        "end_date": t.end_date.isoformat() if t.end_date else None,
                        "try_number": t.try_number,
                    }
                    for t in tasks
                ]
            }
        except Exception as e:
            logger.error(f"Failed to fetch DAG run: {e}")
            return None
    
    def get_task_logs(
        self,
        dag_id: str,
        run_id: str,
        task_id: str,
        try_number: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Get task execution logs."""
        dag_config = self.get_dag(dag_id)
        if not dag_config:
            return None
        
        try:
            logs = self.airflow_client.get_task_logs(
                dag_config.full_dag_id,
                run_id,
                task_id,
                try_number or 1
            )
            
            return {
                "task_id": task_id,
                "try_number": try_number or 1,
                "content": logs,
            }
        except Exception as e:
            logger.error(f"Failed to fetch task logs: {e}")
            return None
