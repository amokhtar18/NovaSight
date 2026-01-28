"""
NovaSight DAG Management Endpoints
==================================

Apache Airflow DAG configuration and monitoring.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_v1_bp
from app.services.dag_service import DagService
from app.decorators import require_roles, require_tenant_context
from app.errors import ValidationError, NotFoundError, AirflowAPIError
import logging

logger = logging.getLogger(__name__)


@api_v1_bp.route("/dags", methods=["GET"])
@jwt_required()
@require_tenant_context
def list_dags():
    """
    List all DAG configurations for current tenant.
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - status: Filter by status (active, paused, draft)
        - tag: Filter by tag
    
    Returns:
        Paginated list of DAG configurations
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")
    tag = request.args.get("tag")
    
    dag_service = DagService(tenant_id)
    result = dag_service.list_dags(page=page, per_page=per_page, status=status, tag=tag)
    
    return jsonify(result)


@api_v1_bp.route("/dags", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def create_dag():
    """
    Create a new DAG configuration.
    
    Request Body:
        - dag_id: Unique DAG identifier
        - description: DAG description
        - schedule_type: Schedule type (cron, preset, manual)
        - schedule_cron: CRON expression (if schedule_type is cron)
        - schedule_preset: Preset schedule (hourly, daily, weekly, monthly)
        - timezone: Execution timezone
        - start_date: DAG start date
        - tasks: List of task configurations
        - tags: List of tags
        - notification_emails: Email addresses for notifications
        - email_on_failure: Send email on task failure
        - email_on_success: Send email on DAG success
    
    Returns:
        Created DAG configuration
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    user_id = identity.get("user_id")
    data = request.get_json()
    
    if not data:
        raise ValidationError("Request body required")
    
    required_fields = ["dag_id", "tasks"]
    for field in required_fields:
        if not data.get(field):
            raise ValidationError(f"Field '{field}' is required")
    
    # Validate DAG ID format
    dag_id = data["dag_id"]
    if not dag_id.replace("_", "").isalnum() or not dag_id[0].isalpha():
        raise ValidationError("DAG ID must start with a letter and contain only alphanumeric characters and underscores")
    
    dag_service = DagService(tenant_id)
    dag_config = dag_service.create_dag(
        dag_id=dag_id,
        description=data.get("description", ""),
        schedule_type=data.get("schedule_type", "manual"),
        schedule_cron=data.get("schedule_cron"),
        schedule_preset=data.get("schedule_preset"),
        timezone=data.get("timezone", "UTC"),
        start_date=data.get("start_date"),
        tasks=data["tasks"],
        tags=data.get("tags", []),
        notification_emails=data.get("notification_emails", []),
        email_on_failure=data.get("email_on_failure", True),
        email_on_success=data.get("email_on_success", False),
        catchup=data.get("catchup", False),
        max_active_runs=data.get("max_active_runs", 1),
        created_by=user_id,
    )
    
    logger.info(f"DAG '{dag_id}' created in tenant {tenant_id}")
    
    return jsonify({"dag": dag_config.to_dict()}), 201


@api_v1_bp.route("/dags/<dag_id>", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_dag(dag_id: str):
    """
    Get DAG configuration details.
    
    Args:
        dag_id: DAG identifier
    
    Query Parameters:
        - include_runs: Include recent run history (default: false)
    
    Returns:
        DAG configuration details
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    include_runs = request.args.get("include_runs", "false").lower() == "true"
    
    dag_service = DagService(tenant_id)
    dag_config = dag_service.get_dag(dag_id, include_runs=include_runs)
    
    if not dag_config:
        raise NotFoundError("DAG not found")
    
    return jsonify({"dag": dag_config.to_dict()})


@api_v1_bp.route("/dags/<dag_id>", methods=["PUT"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def update_dag(dag_id: str):
    """
    Update DAG configuration (creates new version).
    
    Args:
        dag_id: DAG identifier
    
    Request Body:
        Full DAG configuration (replaces current)
    
    Returns:
        Updated DAG configuration
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    user_id = identity.get("user_id")
    data = request.get_json()
    
    if not data:
        raise ValidationError("Request body required")
    
    dag_service = DagService(tenant_id)
    dag_config = dag_service.update_dag(dag_id, updated_by=user_id, **data)
    
    if not dag_config:
        raise NotFoundError("DAG not found")
    
    logger.info(f"DAG '{dag_id}' updated in tenant {tenant_id}")
    
    return jsonify({"dag": dag_config.to_dict()})


@api_v1_bp.route("/dags/<dag_id>", methods=["DELETE"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def delete_dag(dag_id: str):
    """
    Delete DAG configuration.
    
    Args:
        dag_id: DAG identifier
    
    Returns:
        Success message
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    dag_service = DagService(tenant_id)
    success = dag_service.delete_dag(dag_id)
    
    if not success:
        raise NotFoundError("DAG not found")
    
    logger.info(f"DAG '{dag_id}' deleted from tenant {tenant_id}")
    
    return jsonify({"message": "DAG deleted successfully"})


@api_v1_bp.route("/dags/<dag_id>/validate", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def validate_dag(dag_id: str):
    """
    Validate DAG configuration.
    
    Args:
        dag_id: DAG identifier
    
    Returns:
        Validation results (errors, warnings)
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    dag_service = DagService(tenant_id)
    result = dag_service.validate_dag(dag_id)
    
    if result is None:
        raise NotFoundError("DAG not found")
    
    return jsonify(result)


@api_v1_bp.route("/dags/<dag_id>/deploy", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def deploy_dag(dag_id: str):
    """
    Deploy DAG to Airflow.
    
    Args:
        dag_id: DAG identifier
    
    Returns:
        Deployment result
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    user_id = identity.get("user_id")
    
    dag_service = DagService(tenant_id)
    result = dag_service.deploy_dag(dag_id, deployed_by=user_id)
    
    if result is None:
        raise NotFoundError("DAG not found")
    
    if not result.get("success"):
        raise AirflowAPIError(result.get("error", "Deployment failed"))
    
    logger.info(f"DAG '{dag_id}' deployed to Airflow by user {user_id}")
    
    return jsonify(result)


@api_v1_bp.route("/dags/<dag_id>/trigger", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def trigger_dag(dag_id: str):
    """
    Trigger immediate DAG run.
    
    Args:
        dag_id: DAG identifier
    
    Request Body:
        - conf: Optional run configuration parameters
    
    Returns:
        Triggered run details
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    data = request.get_json() or {}
    
    dag_service = DagService(tenant_id)
    result = dag_service.trigger_dag(dag_id, conf=data.get("conf", {}))
    
    if result is None:
        raise NotFoundError("DAG not found")
    
    if not result.get("success"):
        raise AirflowAPIError(result.get("error", "Failed to trigger DAG"))
    
    logger.info(f"DAG '{dag_id}' triggered in tenant {tenant_id}")
    
    return jsonify(result)


@api_v1_bp.route("/dags/<dag_id>/pause", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def pause_dag(dag_id: str):
    """
    Pause DAG scheduling.
    
    Args:
        dag_id: DAG identifier
    
    Returns:
        Updated DAG status
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    dag_service = DagService(tenant_id)
    result = dag_service.pause_dag(dag_id)
    
    if result is None:
        raise NotFoundError("DAG not found")
    
    logger.info(f"DAG '{dag_id}' paused in tenant {tenant_id}")
    
    return jsonify(result)


@api_v1_bp.route("/dags/<dag_id>/unpause", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def unpause_dag(dag_id: str):
    """
    Resume DAG scheduling.
    
    Args:
        dag_id: DAG identifier
    
    Returns:
        Updated DAG status
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    dag_service = DagService(tenant_id)
    result = dag_service.unpause_dag(dag_id)
    
    if result is None:
        raise NotFoundError("DAG not found")
    
    logger.info(f"DAG '{dag_id}' unpaused in tenant {tenant_id}")
    
    return jsonify(result)


@api_v1_bp.route("/dags/<dag_id>/runs", methods=["GET"])
@jwt_required()
@require_tenant_context
def list_dag_runs(dag_id: str):
    """
    List DAG run history.
    
    Args:
        dag_id: DAG identifier
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 25)
        - state: Filter by run state
    
    Returns:
        Paginated list of DAG runs
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    state = request.args.get("state")
    
    dag_service = DagService(tenant_id)
    result = dag_service.list_dag_runs(dag_id, page=page, per_page=per_page, state=state)
    
    if result is None:
        raise NotFoundError("DAG not found")
    
    return jsonify(result)


@api_v1_bp.route("/dags/<dag_id>/runs/<run_id>", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_dag_run(dag_id: str, run_id: str):
    """
    Get DAG run details with task instances.
    
    Args:
        dag_id: DAG identifier
        run_id: Run identifier
    
    Returns:
        DAG run details with task instances
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    dag_service = DagService(tenant_id)
    result = dag_service.get_dag_run(dag_id, run_id)
    
    if result is None:
        raise NotFoundError("DAG run not found")
    
    return jsonify(result)


@api_v1_bp.route("/dags/<dag_id>/runs/<run_id>/tasks/<task_id>/logs", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_task_logs(dag_id: str, run_id: str, task_id: str):
    """
    Get task execution logs.
    
    Args:
        dag_id: DAG identifier
        run_id: Run identifier
        task_id: Task identifier
    
    Query Parameters:
        - try_number: Attempt number (default: latest)
    
    Returns:
        Task execution logs
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    try_number = request.args.get("try_number", type=int)
    
    dag_service = DagService(tenant_id)
    result = dag_service.get_task_logs(dag_id, run_id, task_id, try_number)
    
    if result is None:
        raise NotFoundError("Task logs not found")
    
    return jsonify(result)


# ============================================================================
# PySpark DAG Generator Endpoints (Prompt 016)
# ============================================================================
# These endpoints generate Airflow DAGs to orchestrate pre-defined PySpark jobs
# created via the PySpark App Builder. All PySpark code comes from pre-approved
# templates (ADR-002 compliant).

from app.services.dag_generator import PySparkDAGGenerator


def _get_pyspark_dag_generator(tenant_id: str) -> PySparkDAGGenerator:
    """Create PySparkDAGGenerator instance for tenant."""
    return PySparkDAGGenerator(tenant_id)


@api_v1_bp.route("/dags/pyspark/generate", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def generate_pyspark_dag():
    """
    Generate a DAG for a PySpark app.
    
    Creates an Airflow DAG that schedules and runs a pre-defined PySpark
    application created via the PySpark App Builder.
    
    Request Body:
        - pyspark_app_id: UUID of the PySpark app (required)
        - schedule: Cron expression or preset (@hourly, @daily, etc.)
        - spark_config: Optional Spark configuration overrides
        - notifications: Optional notification settings
            - email: Email address for notifications
            - email_on_failure: Send email on failure
        - retries: Number of retries on failure (default: 2)
        - retry_delay_minutes: Minutes between retries (default: 5)
    
    Returns:
        - dag_id: Generated DAG identifier
        - message: Success message
    
    Example:
        {
            "pyspark_app_id": "550e8400-e29b-41d4-a716-446655440000",
            "schedule": "@hourly",
            "spark_config": {
                "spark.executor.memory": "4g",
                "spark.executor.cores": "4"
            },
            "notifications": {
                "email": "alerts@example.com",
                "email_on_failure": true
            }
        }
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    pyspark_app_id = data.get("pyspark_app_id")
    if not pyspark_app_id:
        raise ValidationError("pyspark_app_id is required")
    
    generator = _get_pyspark_dag_generator(tenant_id)
    
    dag_id = generator.generate_dag_for_pyspark_app(
        pyspark_app_id=pyspark_app_id,
        schedule=data.get("schedule", "@hourly"),
        spark_config=data.get("spark_config"),
        notifications=data.get("notifications"),
        retries=data.get("retries", 2),
        retry_delay_minutes=data.get("retry_delay_minutes", 5),
    )
    
    logger.info(f"Generated PySpark DAG '{dag_id}' for tenant {tenant_id}")
    
    return jsonify({
        "dag_id": dag_id,
        "message": "DAG generated successfully",
    }), 201


@api_v1_bp.route("/dags/pyspark/generate-pipeline", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def generate_pyspark_pipeline_dag():
    """
    Generate a DAG that runs multiple PySpark apps.
    
    Creates a single Airflow DAG that orchestrates multiple pre-defined
    PySpark applications, either in parallel or sequential order.
    
    Request Body:
        - pyspark_app_ids: List of PySpark app UUIDs to run (required)
        - dag_name: Name for the combined DAG (required)
        - schedule: Cron expression or preset (@daily, @hourly, etc.)
        - parallel: If true, run apps in parallel; if false, sequential
        - spark_config: Optional Spark configuration overrides
        - notifications: Optional notification settings
        - description: Optional pipeline description
        - retries: Number of retries on failure (default: 2)
        - retry_delay_minutes: Minutes between retries (default: 5)
    
    Returns:
        - dag_id: Generated DAG identifier
        - message: Success message
    
    Example:
        {
            "pyspark_app_ids": [
                "550e8400-e29b-41d4-a716-446655440000",
                "550e8400-e29b-41d4-a716-446655440001"
            ],
            "dag_name": "daily_data_pipeline",
            "schedule": "@daily",
            "parallel": false,
            "description": "Daily data ingestion pipeline"
        }
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    pyspark_app_ids = data.get("pyspark_app_ids")
    dag_name = data.get("dag_name")
    
    if not pyspark_app_ids or not isinstance(pyspark_app_ids, list):
        raise ValidationError("pyspark_app_ids must be a list of UUIDs")
    if not dag_name:
        raise ValidationError("dag_name is required")
    if len(dag_name) > 64:
        raise ValidationError("dag_name must be 64 characters or less")
    
    generator = _get_pyspark_dag_generator(tenant_id)
    
    dag_id = generator.generate_dag_for_multiple_apps(
        pyspark_app_ids=pyspark_app_ids,
        dag_name=dag_name,
        schedule=data.get("schedule", "@daily"),
        parallel=data.get("parallel", False),
        spark_config=data.get("spark_config"),
        notifications=data.get("notifications"),
        description=data.get("description"),
        retries=data.get("retries", 2),
        retry_delay_minutes=data.get("retry_delay_minutes", 5),
    )
    
    logger.info(f"Generated pipeline DAG '{dag_id}' for tenant {tenant_id}")
    
    return jsonify({
        "dag_id": dag_id,
        "message": "Pipeline DAG generated successfully",
    }), 201


@api_v1_bp.route("/dags/pyspark", methods=["GET"])
@jwt_required()
@require_tenant_context
def list_pyspark_dags():
    """
    List all PySpark DAGs for the current tenant.
    
    Returns a list of all Airflow DAGs generated for PySpark apps
    belonging to the current tenant.
    
    Returns:
        - dags: List of DAG metadata
            - dag_id: DAG identifier
            - file_path: Path to DAG file
            - is_pipeline: True if this is a multi-app pipeline DAG
            - created_at: Creation timestamp
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    generator = _get_pyspark_dag_generator(tenant_id)
    dags = generator.list_dags_for_tenant()
    
    return jsonify({"dags": dags})


@api_v1_bp.route("/dags/pyspark/<dag_id>", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_pyspark_dag(dag_id: str):
    """
    Get detailed information about a PySpark DAG.
    
    Args:
        dag_id: DAG identifier
    
    Returns:
        DAG information including schedule and job count
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    generator = _get_pyspark_dag_generator(tenant_id)
    dag_info = generator.get_dag_info(dag_id)
    
    if not dag_info:
        raise NotFoundError(f"DAG {dag_id} not found")
    
    return jsonify({"dag": dag_info})


@api_v1_bp.route("/dags/pyspark/<dag_id>", methods=["DELETE"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def delete_pyspark_dag(dag_id: str):
    """
    Delete a PySpark DAG and its associated job files.
    
    Args:
        dag_id: DAG identifier
    
    Returns:
        Success message
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    generator = _get_pyspark_dag_generator(tenant_id)
    generator.delete_dag(dag_id)
    
    logger.info(f"Deleted PySpark DAG '{dag_id}' from tenant {tenant_id}")
    
    return jsonify({"message": f"DAG {dag_id} deleted successfully"})


@api_v1_bp.route("/dags/pyspark/<dag_id>/schedule", methods=["PATCH"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def update_pyspark_dag_schedule(dag_id: str):
    """
    Update the schedule of a PySpark DAG.
    
    Args:
        dag_id: DAG identifier
    
    Request Body:
        - schedule: New schedule expression (cron or preset)
    
    Returns:
        Success message
    
    Example:
        {
            "schedule": "@daily"
        }
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    new_schedule = data.get("schedule")
    if not new_schedule:
        raise ValidationError("schedule is required")
    
    generator = _get_pyspark_dag_generator(tenant_id)
    generator.update_dag_schedule(dag_id, new_schedule)
    
    logger.info(f"Updated schedule for DAG '{dag_id}' to '{new_schedule}'")
    
    return jsonify({"message": f"Schedule updated to {new_schedule}"})

