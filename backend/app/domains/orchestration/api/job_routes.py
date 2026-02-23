"""
NovaSight Unified Orchestration API Routes
==========================================

Merged API endpoints for Dagster job management with remote Spark execution.
This replaces the separate DAGs and PySpark orchestration endpoints with a
unified interface for:

1. Creating Dagster jobs from PySpark apps
2. Managing job schedules
3. Triggering and monitoring job runs
4. Viewing job execution history

All jobs execute spark-submit on remote Spark clusters via SSH.
"""

from flask import request, jsonify, Blueprint
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.platform.auth.identity import get_current_identity
from app.decorators import require_roles, require_tenant_context
from app.errors import ValidationError, NotFoundError
from app.services.audit_service import AuditService
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Dagster Job Management Endpoints
# =============================================================================

@api_v1_bp.route("/jobs", methods=["GET"])
@jwt_required()
@require_tenant_context
def list_jobs():
    """
    List all Dagster jobs for the current tenant.
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - status: Filter by status (active, paused, draft)
        - type: Filter by type (spark, pipeline)
    
    Returns:
        Paginated list of jobs with execution status
    """
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")
    job_type = request.args.get("type")
    
    # Import service
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    result = service.list_jobs(
        page=page,
        per_page=per_page,
        status=status,
        job_type=job_type,
    )
    
    return jsonify(result)


@api_v1_bp.route("/jobs", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def create_job():
    """
    Create a new Dagster job for a PySpark app.
    
    Request Body:
        - pyspark_app_id: UUID of the PySpark app to run (required)
        - schedule: Cron expression or preset (@hourly, @daily, etc.)
        - spark_config: Optional Spark configuration overrides
        - name: Optional custom job name
        - description: Optional job description
        - notifications: Optional notification settings
        - retries: Number of retries on failure (default: 2)
        - retry_delay_minutes: Minutes between retries (default: 5)
    
    Returns:
        Created job configuration
    """
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    user_id = identity.user_id
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    pyspark_app_id = data.get("pyspark_app_id")
    if not pyspark_app_id:
        raise ValidationError("pyspark_app_id is required")
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    job_config = service.create_job(
        pyspark_app_id=pyspark_app_id,
        schedule=data.get("schedule"),
        spark_config=data.get("spark_config"),
        name=data.get("name"),
        description=data.get("description"),
        notifications=data.get("notifications"),
        retries=data.get("retries", 2),
        retry_delay_minutes=data.get("retry_delay_minutes", 5),
        created_by=user_id,
    )
    
    logger.info(f"Created Dagster job for PySpark app {pyspark_app_id}")
    
    AuditService.log(
        action='job.created',
        resource_type='dagster_job',
        resource_id=str(job_config['id']),
        resource_name=job_config['name'],
        tenant_id=tenant_id,
        extra_data={'pyspark_app_id': pyspark_app_id},
    )
    
    return jsonify({"job": job_config}), 201


@api_v1_bp.route("/jobs/pipeline", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def create_pipeline_job():
    """
    Create a Dagster job that runs multiple PySpark apps.
    
    Request Body:
        - pyspark_app_ids: List of PySpark app UUIDs to run (required)
        - name: Pipeline name (required)
        - description: Pipeline description
        - schedule: Cron expression or preset
        - parallel: Run apps in parallel (default: false)
        - spark_config: Optional Spark configuration overrides
        
    Returns:
        Created pipeline job configuration
    """
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    user_id = identity.user_id
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    pyspark_app_ids = data.get("pyspark_app_ids")
    name = data.get("name")
    
    if not pyspark_app_ids or not isinstance(pyspark_app_ids, list):
        raise ValidationError("pyspark_app_ids must be a list of UUIDs")
    if not name:
        raise ValidationError("name is required")
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    job_config = service.create_pipeline_job(
        pyspark_app_ids=pyspark_app_ids,
        name=name,
        description=data.get("description"),
        schedule=data.get("schedule"),
        parallel=data.get("parallel", False),
        spark_config=data.get("spark_config"),
        created_by=user_id,
    )
    
    logger.info(f"Created pipeline job '{name}' with {len(pyspark_app_ids)} apps")
    
    AuditService.log(
        action='pipeline.created',
        resource_type='dagster_pipeline',
        resource_id=str(job_config['id']),
        resource_name=name,
        tenant_id=tenant_id,
        extra_data={'app_count': len(pyspark_app_ids)},
    )
    
    return jsonify({"job": job_config}), 201


@api_v1_bp.route("/jobs/<job_id>", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_job(job_id: str):
    """Get Dagster job details."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    job_config = service.get_job(job_id)
    
    if not job_config:
        raise NotFoundError("Job not found")
    
    return jsonify({"job": job_config})


@api_v1_bp.route("/jobs/<job_id>", methods=["PUT"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def update_job(job_id: str):
    """Update Dagster job configuration."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    job_config = service.update_job(job_id, **data)
    
    if not job_config:
        raise NotFoundError("Job not found")
    
    logger.info(f"Updated job {job_id}")
    
    AuditService.log(
        action='job.updated',
        resource_type='dagster_job',
        resource_id=job_id,
        tenant_id=tenant_id,
        changes={'updated_fields': list(data.keys())},
    )
    
    return jsonify({"job": job_config})


@api_v1_bp.route("/jobs/<job_id>", methods=["DELETE"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def delete_job(job_id: str):
    """Delete a Dagster job."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    success = service.delete_job(job_id)
    
    if not success:
        raise NotFoundError("Job not found")
    
    logger.info(f"Deleted job {job_id}")
    
    AuditService.log(
        action='job.deleted',
        resource_type='dagster_job',
        resource_id=job_id,
        tenant_id=tenant_id,
    )
    
    return jsonify({"message": "Job deleted successfully"})


# =============================================================================
# Job Execution Endpoints
# =============================================================================

@api_v1_bp.route("/jobs/<job_id>/trigger", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def trigger_job(job_id: str):
    """
    Trigger an immediate job run.
    
    Request Body (optional):
        - run_config: Runtime configuration overrides
        - tags: Additional run tags
    
    Returns:
        Run information including run_id
    """
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    data = request.get_json() or {}
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    result = service.trigger_job(
        job_id=job_id,
        run_config=data.get("run_config"),
        tags=data.get("tags"),
    )
    
    if not result:
        raise NotFoundError("Job not found")
    
    if not result.get("success"):
        raise ValidationError(result.get("error", "Failed to trigger job"))
    
    logger.info(f"Triggered job {job_id}: run_id={result.get('run_id')}")
    
    AuditService.log(
        action='job.triggered',
        resource_type='dagster_job',
        resource_id=job_id,
        tenant_id=tenant_id,
        extra_data={'run_id': result.get('run_id')},
    )
    
    return jsonify(result)


@api_v1_bp.route("/jobs/<job_id>/pause", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def pause_job(job_id: str):
    """Pause job scheduling."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    result = service.pause_job(job_id)
    
    if not result:
        raise NotFoundError("Job not found")
    
    logger.info(f"Paused job {job_id}")
    
    AuditService.log(
        action='job.paused',
        resource_type='dagster_job',
        resource_id=job_id,
        tenant_id=tenant_id,
    )
    
    return jsonify({"message": "Job paused", "success": True})


@api_v1_bp.route("/jobs/<job_id>/resume", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def resume_job(job_id: str):
    """Resume job scheduling."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    result = service.resume_job(job_id)
    
    if not result:
        raise NotFoundError("Job not found")
    
    logger.info(f"Resumed job {job_id}")
    
    AuditService.log(
        action='job.resumed',
        resource_type='dagster_job',
        resource_id=job_id,
        tenant_id=tenant_id,
    )
    
    return jsonify({"message": "Job resumed", "success": True})


# =============================================================================
# Job Runs / History Endpoints
# =============================================================================

@api_v1_bp.route("/jobs/<job_id>/runs", methods=["GET"])
@jwt_required()
@require_tenant_context
def list_job_runs(job_id: str):
    """
    List run history for a job.
    
    Query Parameters:
        - page: Page number
        - per_page: Items per page
        - status: Filter by run status (success, failed, running)
    """
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    status = request.args.get("status")
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    result = service.list_job_runs(
        job_id=job_id,
        page=page,
        per_page=per_page,
        status=status,
    )
    
    if result is None:
        raise NotFoundError("Job not found")
    
    return jsonify(result)


@api_v1_bp.route("/jobs/<job_id>/runs/<run_id>", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_job_run(job_id: str, run_id: str):
    """Get detailed information about a specific job run."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    result = service.get_job_run(job_id, run_id)
    
    if not result:
        raise NotFoundError("Job run not found")
    
    return jsonify(result)


@api_v1_bp.route("/jobs/<job_id>/runs/<run_id>/logs", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_job_run_logs(job_id: str, run_id: str):
    """Get execution logs for a job run."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    result = service.get_job_run_logs(job_id, run_id)
    
    if not result:
        raise NotFoundError("Job run not found")
    
    return jsonify(result)


@api_v1_bp.route("/jobs/<job_id>/runs/<run_id>/cancel", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def cancel_job_run(job_id: str, run_id: str):
    """Cancel a running job."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    result = service.cancel_job_run(job_id, run_id)
    
    if not result:
        raise NotFoundError("Job run not found")
    
    logger.info(f"Cancelled job run {run_id}")
    
    AuditService.log(
        action='job_run.cancelled',
        resource_type='dagster_job_run',
        resource_id=run_id,
        tenant_id=tenant_id,
    )
    
    return jsonify({"message": "Run cancelled", "success": True})


# =============================================================================
# Spark Configuration Endpoints
# =============================================================================

@api_v1_bp.route("/jobs/spark-config", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_spark_config():
    """Get current Spark cluster configuration."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    config = service.get_spark_config()
    
    return jsonify({"config": config})


@api_v1_bp.route("/jobs/spark-config", methods=["PUT"])
@jwt_required()
@require_tenant_context
@require_roles(["tenant_admin"])
def update_spark_config():
    """
    Update Spark cluster configuration.
    
    Request Body:
        - spark_master: Spark master URL
        - ssh_host: SSH host for remote execution
        - ssh_user: SSH username
        - ssh_key_path: Path to SSH private key
        - driver_memory: Driver memory (e.g., "2g")
        - executor_memory: Executor memory (e.g., "2g")
        - executor_cores: Executor cores
        - num_executors: Number of executors
        - additional_configs: Dict of additional Spark configs
    """
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    config = service.update_spark_config(**data)
    
    logger.info(f"Updated Spark config for tenant {tenant_id}")
    
    AuditService.log(
        action='spark_config.updated',
        resource_type='spark_config',
        tenant_id=tenant_id,
        changes={'updated_fields': list(data.keys())},
    )
    
    return jsonify({"config": config})


@api_v1_bp.route("/jobs/spark-config/test", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def test_spark_connection():
    """
    Test connection to Spark cluster.
    
    Validates SSH connectivity and Spark master availability.
    """
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    from app.domains.orchestration.application.unified_job_service import UnifiedJobService
    
    service = UnifiedJobService(tenant_id)
    result = service.test_spark_connection()
    
    return jsonify(result)
