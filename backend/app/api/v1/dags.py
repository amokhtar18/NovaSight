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
