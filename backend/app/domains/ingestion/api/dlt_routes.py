"""
NovaSight Ingestion Domain — dlt Pipeline API Routes
======================================================

REST API endpoints for dlt pipeline management.
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError as PydanticValidationError

from app.platform.auth.decorators import authenticated
from app.platform.auth.identity import get_current_identity
from app.platform.tenant.context import get_current_tenant_id
from app.domains.ingestion.schemas.dlt_schemas import (
    DltPipelineCreate,
    DltPipelineUpdate,
    DltPipelineResponse,
    DltPipelineListResponse,
    DltPipelinePreviewRequest,
    DltPipelinePreviewResponse,
    DltPipelineRunResponse,
)
from app.domains.ingestion.application.dlt_pipeline_service import (
    DltPipelineService,
    DltPipelineNotFoundError,
    DltPipelineValidationError,
)
from app.errors import ValidationError, NotFoundError

import logging

logger = logging.getLogger(__name__)

dlt_pipeline_bp = Blueprint("dlt_pipelines", __name__, url_prefix="/api/v1/pipelines")


def _get_service() -> DltPipelineService:
    """Get dlt pipeline service instance."""
    return DltPipelineService()


def _get_tenant_id():
    """Get current tenant ID from context."""
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise ValidationError("Tenant context required")
    return tenant_id


def _get_user_id():
    """Get current user ID from identity."""
    identity = get_current_identity()
    return identity.user_id


# =========================================
# Pipeline CRUD Endpoints
# =========================================


@dlt_pipeline_bp.route("", methods=["GET"])
@authenticated
def list_pipelines():
    """
    List dlt pipelines for the current tenant.

    Query Parameters:
        - status: Filter by status (draft, active, inactive, error)
        - connection_id: Filter by connection UUID
        - search: Search in name/description
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)

    Returns:
        Paginated list of pipelines
    """
    tenant_id = _get_tenant_id()
    service = _get_service()

    result = service.list_pipelines(
        tenant_id=tenant_id,
        status=request.args.get("status"),
        connection_id=request.args.get("connection_id"),
        search=request.args.get("search"),
        page=request.args.get("page", 1, type=int),
        per_page=min(request.args.get("per_page", 20, type=int), 100),
    )

    return jsonify(result)


@dlt_pipeline_bp.route("/<uuid:pipeline_id>", methods=["GET"])
@authenticated
def get_pipeline(pipeline_id):
    """
    Get a specific pipeline.

    Args:
        pipeline_id: Pipeline UUID

    Returns:
        Pipeline details including generated code
    """
    tenant_id = _get_tenant_id()
    service = _get_service()

    try:
        pipeline = service.get_pipeline(pipeline_id, tenant_id)
        return jsonify(pipeline.to_dict(include_code=True))
    except DltPipelineNotFoundError as e:
        raise NotFoundError(str(e))


@dlt_pipeline_bp.route("", methods=["POST"])
@authenticated
def create_pipeline():
    """
    Create a new dlt pipeline.

    Request Body:
        DltPipelineCreate schema

    Returns:
        Created pipeline details
    """
    tenant_id = _get_tenant_id()
    user_id = _get_user_id()
    service = _get_service()

    try:
        data = DltPipelineCreate(**request.get_json())
        pipeline = service.create_pipeline(tenant_id, user_id, data)
        return jsonify(pipeline.to_dict()), 201
    except PydanticValidationError as e:
        raise ValidationError(str(e))
    except DltPipelineValidationError as e:
        raise ValidationError(str(e))


@dlt_pipeline_bp.route("/<uuid:pipeline_id>", methods=["PUT"])
@authenticated
def update_pipeline(pipeline_id):
    """
    Update a pipeline.

    Args:
        pipeline_id: Pipeline UUID

    Request Body:
        DltPipelineUpdate schema

    Returns:
        Updated pipeline details
    """
    tenant_id = _get_tenant_id()
    service = _get_service()

    try:
        data = DltPipelineUpdate(**request.get_json())
        pipeline = service.update_pipeline(pipeline_id, tenant_id, data)
        return jsonify(pipeline.to_dict())
    except DltPipelineNotFoundError as e:
        raise NotFoundError(str(e))
    except PydanticValidationError as e:
        raise ValidationError(str(e))
    except DltPipelineValidationError as e:
        raise ValidationError(str(e))


@dlt_pipeline_bp.route("/<uuid:pipeline_id>", methods=["DELETE"])
@authenticated
def delete_pipeline(pipeline_id):
    """
    Delete a pipeline.

    Args:
        pipeline_id: Pipeline UUID

    Returns:
        204 No Content on success
    """
    tenant_id = _get_tenant_id()
    service = _get_service()

    try:
        service.delete_pipeline(pipeline_id, tenant_id)
        return "", 204
    except DltPipelineNotFoundError as e:
        raise NotFoundError(str(e))


# =========================================
# Code Generation Endpoints
# =========================================


@dlt_pipeline_bp.route("/preview", methods=["POST"])
@authenticated
def preview_code():
    """
    Preview generated code without saving.

    Request Body:
        DltPipelinePreviewRequest schema

    Returns:
        Generated code and any validation errors
    """
    tenant_id = _get_tenant_id()
    service = _get_service()

    try:
        data = DltPipelinePreviewRequest(**request.get_json())
        code, errors = service.preview_code(tenant_id, data)

        # Determine template name
        if data.write_disposition == "scd2":
            template_name = "dlt/scd2_pipeline.py.j2"
        elif data.write_disposition == "merge":
            template_name = "dlt/merge_pipeline.py.j2"
        else:
            template_name = "dlt/extract_pipeline.py.j2"

        return jsonify(
            DltPipelinePreviewResponse(
                code=code,
                template_name=template_name,
                template_version="1.0.0",
                validation_errors=errors,
            ).model_dump()
        )
    except PydanticValidationError as e:
        raise ValidationError(str(e))
    except DltPipelineValidationError as e:
        raise ValidationError(str(e))


@dlt_pipeline_bp.route("/<uuid:pipeline_id>/generate", methods=["POST"])
@authenticated
def generate_code(pipeline_id):
    """
    Generate and save pipeline code.

    Args:
        pipeline_id: Pipeline UUID

    Returns:
        Generated code
    """
    tenant_id = _get_tenant_id()
    service = _get_service()

    try:
        code = service.generate_code(pipeline_id, tenant_id)
        return jsonify({"code": code})
    except DltPipelineNotFoundError as e:
        raise NotFoundError(str(e))
    except DltPipelineValidationError as e:
        raise ValidationError(str(e))


# =========================================
# Status Management Endpoints
# =========================================


@dlt_pipeline_bp.route("/<uuid:pipeline_id>/activate", methods=["POST"])
@authenticated
def activate_pipeline(pipeline_id):
    """
    Activate a pipeline (make it runnable).

    Args:
        pipeline_id: Pipeline UUID

    Returns:
        Updated pipeline details
    """
    tenant_id = _get_tenant_id()
    service = _get_service()

    try:
        pipeline = service.activate_pipeline(pipeline_id, tenant_id)
        return jsonify(pipeline.to_dict())
    except DltPipelineNotFoundError as e:
        raise NotFoundError(str(e))
    except DltPipelineValidationError as e:
        raise ValidationError(str(e))


@dlt_pipeline_bp.route("/<uuid:pipeline_id>/deactivate", methods=["POST"])
@authenticated
def deactivate_pipeline(pipeline_id):
    """
    Deactivate a pipeline.

    Args:
        pipeline_id: Pipeline UUID

    Returns:
        Updated pipeline details
    """
    tenant_id = _get_tenant_id()
    service = _get_service()

    try:
        pipeline = service.deactivate_pipeline(pipeline_id, tenant_id)
        return jsonify(pipeline.to_dict())
    except DltPipelineNotFoundError as e:
        raise NotFoundError(str(e))


# =========================================
# Execution Endpoints
# =========================================


@dlt_pipeline_bp.route("/<uuid:pipeline_id>/run", methods=["POST"])
@authenticated
def run_pipeline(pipeline_id):
    """
    Trigger immediate pipeline run.

    Args:
        pipeline_id: Pipeline UUID

    Returns:
        Run status (202 Accepted)
    """
    tenant_id = _get_tenant_id()
    service = _get_service()

    try:
        result = service.run_now(pipeline_id, tenant_id)
        return jsonify(
            DltPipelineRunResponse(**result).model_dump()
        ), 202
    except DltPipelineNotFoundError as e:
        raise NotFoundError(str(e))
    except DltPipelineValidationError as e:
        raise ValidationError(str(e))
