"""
NovaSight Dataset API
=====================

REST endpoints for the Superset-inspired :class:`Dataset` model:

* CRUD on datasets, columns, metrics
* Auto-sync from materialized dbt models
* Lightweight preview of dataset rows
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from flask import jsonify, request
from pydantic import ValidationError

from app.api.v1 import api_v1_bp
from app.domains.analytics.application.dataset_service import (
    DatasetNotFoundError,
    DatasetService,
    DatasetServiceError,
    DatasetValidationError,
    DbtManifestNotFoundError,
)
from app.domains.analytics.schemas.dataset_schemas import (
    DatasetColumnSchema,
    DatasetCreateSchema,
    DatasetMetricSchema,
    DatasetSyncDbtSchema,
    DatasetUpdateSchema,
)
from app.platform.auth.decorators import (
    authenticated,
    require_permission,
    tenant_required,
)
from app.platform.auth.identity import get_current_identity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _identity():
    identity = get_current_identity()
    if identity is None:
        raise PermissionError("No authenticated identity")
    return identity


def _error(exc: Exception, status: int = 400):
    return jsonify({"error": str(exc), "type": exc.__class__.__name__}), status


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@api_v1_bp.route("/datasets", methods=["GET"])
@authenticated
@tenant_required
@require_permission("charts.view")
def list_datasets():
    """List datasets for the current tenant."""
    identity = _identity()
    page = max(1, int(request.args.get("page", 1)))
    per_page = min(int(request.args.get("per_page", 50)), 200)
    try:
        items, total = DatasetService.list_for_tenant(
            tenant_id=identity.tenant_id,
            kind=request.args.get("kind"),
            source=request.args.get("source"),
            search=request.args.get("search"),
            include_deleted=request.args.get("include_deleted") == "true",
            limit=per_page,
            offset=(page - 1) * per_page,
        )
    except DatasetServiceError as exc:
        return _error(exc)

    return jsonify(
        {
            "items": [d.to_dict() for d in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if per_page else 0,
        }
    )


@api_v1_bp.route("/datasets/<dataset_id>", methods=["GET"])
@authenticated
@tenant_required
@require_permission("charts.view")
def get_dataset(dataset_id: str):
    identity = _identity()
    try:
        ds = DatasetService.get(identity.tenant_id, dataset_id)
    except DatasetNotFoundError as exc:
        return _error(exc, 404)
    return jsonify(ds.to_dict(include_columns=True))


@api_v1_bp.route("/datasets", methods=["POST"])
@authenticated
@tenant_required
@require_permission("charts.create")
def create_dataset():
    identity = _identity()
    try:
        payload = DatasetCreateSchema.model_validate(request.get_json() or {})
    except ValidationError as exc:
        return jsonify({"error": "validation", "details": exc.errors()}), 400
    try:
        ds = DatasetService.create(
            tenant_id=identity.tenant_id,
            owner_id=identity.user_id,
            payload=payload.to_payload(),
        )
    except DatasetValidationError as exc:
        return _error(exc, 400)
    except DatasetServiceError as exc:
        return _error(exc, 500)
    return jsonify(ds.to_dict(include_columns=True)), 201


@api_v1_bp.route("/datasets/<dataset_id>", methods=["PATCH", "PUT"])
@authenticated
@tenant_required
@require_permission("charts.create")
def update_dataset(dataset_id: str):
    identity = _identity()
    try:
        payload = DatasetUpdateSchema.model_validate(request.get_json() or {})
    except ValidationError as exc:
        return jsonify({"error": "validation", "details": exc.errors()}), 400
    body = payload.model_dump(by_alias=True, exclude_none=True)
    if payload.force:
        body["_force"] = True
    try:
        ds = DatasetService.update(
            tenant_id=identity.tenant_id,
            dataset_id=dataset_id,
            payload=body,
        )
    except DatasetNotFoundError as exc:
        return _error(exc, 404)
    except DatasetValidationError as exc:
        return _error(exc, 400)
    return jsonify(ds.to_dict(include_columns=True))


@api_v1_bp.route("/datasets/<dataset_id>", methods=["DELETE"])
@authenticated
@tenant_required
@require_permission("charts.create")
def delete_dataset(dataset_id: str):
    identity = _identity()
    hard = request.args.get("hard") == "true"
    try:
        DatasetService.delete(identity.tenant_id, dataset_id, hard=hard)
    except DatasetNotFoundError as exc:
        return _error(exc, 404)
    return ("", 204)


# ---------------------------------------------------------------------------
# columns / metrics
# ---------------------------------------------------------------------------


def _validate_list(items: Any, schema_cls) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        raise ValidationError.from_exception_data("payload", [])  # type: ignore[arg-type]
    return [schema_cls.model_validate(it).model_dump() for it in items]


@api_v1_bp.route("/datasets/<dataset_id>/columns", methods=["PUT"])
@authenticated
@tenant_required
@require_permission("charts.create")
def replace_dataset_columns(dataset_id: str):
    identity = _identity()
    try:
        cols = _validate_list(
            (request.get_json() or {}).get("columns"), DatasetColumnSchema
        )
    except ValidationError as exc:
        return jsonify({"error": "validation", "details": exc.errors()}), 400
    try:
        ds = DatasetService.replace_columns(
            identity.tenant_id, dataset_id, cols
        )
    except DatasetNotFoundError as exc:
        return _error(exc, 404)
    return jsonify(ds.to_dict(include_columns=True))


@api_v1_bp.route("/datasets/<dataset_id>/metrics", methods=["PUT"])
@authenticated
@tenant_required
@require_permission("charts.create")
def replace_dataset_metrics(dataset_id: str):
    identity = _identity()
    try:
        metrics = _validate_list(
            (request.get_json() or {}).get("metrics"), DatasetMetricSchema
        )
    except ValidationError as exc:
        return jsonify({"error": "validation", "details": exc.errors()}), 400
    try:
        ds = DatasetService.replace_metrics(
            identity.tenant_id, dataset_id, metrics
        )
    except DatasetNotFoundError as exc:
        return _error(exc, 404)
    return jsonify(ds.to_dict(include_columns=True))


# ---------------------------------------------------------------------------
# preview & dbt sync
# ---------------------------------------------------------------------------


@api_v1_bp.route("/datasets/<dataset_id>/preview", methods=["GET"])
@authenticated
@tenant_required
@require_permission("charts.view")
def preview_dataset(dataset_id: str):
    identity = _identity()
    limit = min(int(request.args.get("limit", 100)), 1000)
    try:
        result = DatasetService.execute_preview(
            identity.tenant_id, dataset_id, limit=limit
        )
    except DatasetNotFoundError as exc:
        return _error(exc, 404)
    except DatasetValidationError as exc:
        return _error(exc, 400)
    except DatasetServiceError as exc:
        return _error(exc, 500)
    return jsonify(result)


@api_v1_bp.route("/datasets/mart/tables", methods=["GET"])
@authenticated
@tenant_required
@require_permission("charts.create")
def list_mart_tables():
    """List tables in the tenant's curated mart database.

    The dataset creation wizard is intentionally restricted to this
    single database — the dbt *marts* layer for the current tenant —
    so analysts cannot publish charts on top of raw / staging tables.
    """
    identity = _identity()
    try:
        result = DatasetService.list_mart_tables(tenant_id=identity.tenant_id)
    except DatasetServiceError as exc:
        return _error(exc, 500)
    return jsonify(result)


@api_v1_bp.route("/datasets/sync-dbt", methods=["POST"])
@authenticated
@tenant_required
@require_permission("charts.create")
def sync_datasets_from_dbt():
    """Discover materialized dbt models and upsert them as Datasets."""
    identity = _identity()
    try:
        body = DatasetSyncDbtSchema.model_validate(request.get_json() or {})
    except ValidationError as exc:
        return jsonify({"error": "validation", "details": exc.errors()}), 400
    try:
        result = DatasetService.sync_from_dbt(
            tenant_id=identity.tenant_id,
            owner_id=identity.user_id,
            manifest_path=body.manifest_path,
            deactivate_missing=body.deactivate_missing,
        )
    except DbtManifestNotFoundError as exc:
        return _error(exc, 404)
    except DatasetServiceError as exc:
        return _error(exc, 500)
    return jsonify(result.to_dict())
