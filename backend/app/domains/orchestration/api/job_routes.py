"""
NovaSight Unified Orchestration API Routes
==========================================

Unified API endpoints for Dagster job management.

Post Spark→dlt migration the orchestrator schedules **only dlt pipelines
and dbt runs/tests**. Spark / PySpark scheduling has been removed.

Endpoints cover:

1. Creating Dagster jobs (single dlt pipeline, dlt pipeline-of-pipelines, dbt run/test)
2. Managing job schedules
3. Triggering and monitoring job runs
4. Viewing job execution history
"""

from flask import request, jsonify, Blueprint

from app.api.v1 import api_v1_bp
from app.platform.auth.identity import get_current_identity
from app.platform.auth.decorators import authenticated, require_roles, tenant_required
from app.errors import ValidationError, NotFoundError
from app.platform.audit.service import AuditService
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Dagster Job Management Endpoints
# =============================================================================

@api_v1_bp.route("/jobs", methods=["GET"])
@authenticated
@tenant_required
def list_jobs():
    """
    List all Dagster jobs for the current tenant.
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - status: Filter by status (active, paused, draft)
        - type: Filter by type (dlt, dbt, pipeline)
    
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
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin"])
def create_job():
    """
    Create a new Dagster job that runs a single dlt pipeline.

    Request Body:
        - pipeline_id: UUID of the dlt pipeline to run (required)
        - schedule: Cron expression or preset (@hourly, @daily, etc.)
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

    # Accept legacy `pyspark_app_id` for backwards compat with old clients,
    # but the canonical name is `pipeline_id`.
    pipeline_id = data.get("pipeline_id") or data.get("pyspark_app_id")
    if not pipeline_id:
        raise ValidationError("pipeline_id is required")

    from app.domains.orchestration.application.unified_job_service import UnifiedJobService

    service = UnifiedJobService(tenant_id)
    try:
        job_config = service.create_job(
            pipeline_id=pipeline_id,
            schedule=data.get("schedule"),
            name=data.get("name"),
            description=data.get("description"),
            notifications=data.get("notifications"),
            retries=data.get("retries", 2),
            retry_delay_minutes=data.get("retry_delay_minutes", 5),
            created_by=user_id,
        )
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Failed to create job: {e}", exc_info=True)
        raise

    logger.info(f"Created Dagster job for dlt pipeline {pipeline_id}")

    AuditService.log(
        action='job.created',
        resource_type='dagster_job',
        resource_id=str(job_config['id']),
        resource_name=job_config.get('dag_id', job_config.get('name', '')),
        tenant_id=tenant_id,
        extra_data={'pipeline_id': pipeline_id},
    )
    
    return jsonify({"job": job_config}), 201


@api_v1_bp.route("/jobs/pipeline", methods=["POST"])
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin"])
def create_pipeline_job():
    """
    Create a Dagster job that runs multiple dlt pipelines.

    Request Body:
        - pipeline_ids: List of dlt pipeline UUIDs to run (required)
        - name: Pipeline name (required)
        - description: Pipeline description
        - schedule: Cron expression or preset
        - parallel: Run pipelines in parallel (default: false)

    Returns:
        Created pipeline job configuration
    """
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    user_id = identity.user_id

    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")

    # Accept legacy `pyspark_app_ids` for backwards compat with old clients.
    pipeline_ids = data.get("pipeline_ids") or data.get("pyspark_app_ids")
    name = data.get("name")

    if not pipeline_ids or not isinstance(pipeline_ids, list):
        raise ValidationError("pipeline_ids must be a list of UUIDs")
    if not name:
        raise ValidationError("name is required")

    from app.domains.orchestration.application.unified_job_service import UnifiedJobService

    service = UnifiedJobService(tenant_id)
    try:
        job_config = service.create_pipeline_job(
            pipeline_ids=pipeline_ids,
            name=name,
            description=data.get("description"),
            schedule=data.get("schedule"),
            parallel=data.get("parallel", False),
            created_by=user_id,
        )
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Failed to create pipeline job: {e}", exc_info=True)
        raise

    logger.info(f"Created pipeline job '{name}' with {len(pipeline_ids)} pipelines")

    AuditService.log(
        action='pipeline.created',
        resource_type='dagster_pipeline',
        resource_id=str(job_config['id']),
        resource_name=name,
        tenant_id=tenant_id,
        extra_data={'pipeline_count': len(pipeline_ids)},
    )
    
    return jsonify({"job": job_config}), 201


@api_v1_bp.route("/jobs/dbt", methods=["POST"])
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin"])
def create_dbt_job():
    """
    Create a Dagster job that runs dbt (run or test).

    Request Body:
        - kind: 'run' or 'test' (required)
        - profile: 'default' | 'lake' | 'warehouse' (default: 'default')
        - name: Optional custom job name
        - description: Optional job description
        - schedule: Cron expression or preset (@hourly, @daily, ...)
        - select: Optional dbt --select expression (models or tests)
        - tags: Optional list of dbt tag selectors (run only)
        - full_refresh: Run with --full-refresh (run only, default: false)
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

    kind = (data.get("kind") or "").lower()
    if kind not in ("run", "test"):
        raise ValidationError("kind must be 'run' or 'test'")

    profile = (data.get("profile") or "default").lower()
    if profile not in ("default", "lake", "warehouse"):
        raise ValidationError("profile must be one of: default, lake, warehouse")

    from app.domains.orchestration.application.unified_job_service import UnifiedJobService

    service = UnifiedJobService(tenant_id)
    try:
        job_config = service.create_dbt_job(
            kind=kind,
            profile=profile,
            name=data.get("name"),
            description=data.get("description"),
            schedule=data.get("schedule"),
            select=data.get("select"),
            tags=data.get("tags"),
            full_refresh=bool(data.get("full_refresh", False)),
            retries=data.get("retries", 2),
            retry_delay_minutes=data.get("retry_delay_minutes", 5),
            created_by=user_id,
        )
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        logger.error(f"Failed to create dbt job: {e}", exc_info=True)
        raise

    logger.info(f"Created dbt {kind} job '{job_config.get('dag_id')}' (profile={profile})")

    AuditService.log(
        action='job.created',
        resource_type='dagster_job',
        resource_id=str(job_config['id']),
        resource_name=job_config.get('dag_id', ''),
        tenant_id=tenant_id,
        extra_data={'kind': f'dbt_{kind}', 'profile': profile},
    )

    return jsonify({"job": job_config}), 201


@api_v1_bp.route("/jobs/<job_id>", methods=["GET"])
@authenticated
@tenant_required
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
@authenticated
@tenant_required
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
@authenticated
@tenant_required
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
@authenticated
@tenant_required
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
        error_type = result.get("error_type", "unknown_error")
        error_msg = result.get("error", "Failed to trigger job")
        
        if error_type in ("dagster_unavailable", "dagster_timeout"):
            from app.errors import DagsterAPIError
            raise DagsterAPIError(error_msg)
        else:
            raise ValidationError(error_msg)
    
    logger.info(f"Triggered job {job_id}: run_id={result.get('run_id')}")
    
    AuditService.log(
        action='job.triggered',
        resource_type='dagster_job',
        resource_id=job_id,
        tenant_id=tenant_id,
        extra_data={'run_id': result.get('run_id')},
    )
    
    # Remove internal error_type field before sending response
    result.pop('error_type', None)
    return jsonify(result)


@api_v1_bp.route("/jobs/<job_id>/pause", methods=["POST"])
@authenticated
@tenant_required
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
@authenticated
@tenant_required
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
@authenticated
@tenant_required
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
@authenticated
@tenant_required
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
@authenticated
@tenant_required
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
@authenticated
@tenant_required
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

