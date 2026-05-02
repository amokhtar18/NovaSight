"""
SQL Lab proxy routes
=====================

Phase 6 of the Superset integration. Forwards the NovaSight SQL Editor
to Superset's SQL Lab so result-set caching, async execution, and cost
estimation are all delivered by Superset's mature backend.

Three routes:

* ``POST /api/v1/superset/sqllab/execute``   — sync or async exec
* ``GET  /api/v1/superset/sqllab/results/<key>`` — fetch async results
* ``POST /api/v1/superset/sqllab/estimate``  — query cost estimate

All three:

* Require JWT + tenant context.
* Are gated by the per-tenant ``FEATURE_SUPERSET_BACKEND`` flag.
* Reject any request whose ``database_id`` is not the caller's tenant
  Superset database (defence-in-depth on top of the connection
  mutator).
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Blueprint, Response, jsonify, request

from app.platform.auth.decorators import authenticated, tenant_required

from app.domains.analytics.superset._proxy_helpers import (
    assert_caller_owns_database,
    feature_flag_required,
    resolve_tenant_database_id,
    safe_json,
    superset_request,
)

logger = logging.getLogger(__name__)

sqllab_bp = Blueprint("superset_sqllab", __name__, url_prefix="/superset/sqllab")


@sqllab_bp.route("/execute", methods=["POST"])
@authenticated
@tenant_required
def execute() -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    if "sql" not in payload or not str(payload.get("sql")).strip():
        return jsonify({"error": "sql is required"}), 400

    db_id, err = resolve_tenant_database_id()
    if err is not None:
        return err

    # Always force the tenant DB id, even if the client tried to send one.
    payload["database_id"] = db_id
    payload.setdefault("client_id", "novasight-sql-editor")
    payload.setdefault("runAsync", bool(payload.get("runAsync", False)))

    resp, error = superset_request(
        "POST", "/sqllab/execute/", json_body=payload
    )
    if error is not None:
        return error

    body = safe_json(resp)
    return (
        jsonify(body) if body is not None else Response("", status=resp.status_code),
        resp.status_code,
    )


@sqllab_bp.route("/results/<key>", methods=["GET"])
@authenticated
@tenant_required
def results(key: str) -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    resp, error = superset_request(
        "GET",
        "/sqllab/results/",
        params={"key": key},
    )
    if error is not None:
        return error

    body = safe_json(resp)
    return (
        jsonify(body) if body is not None else Response("", status=resp.status_code),
        resp.status_code,
    )


@sqllab_bp.route("/estimate", methods=["POST"])
@authenticated
@tenant_required
def estimate() -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    if "sql" not in payload or not str(payload.get("sql")).strip():
        return jsonify({"error": "sql is required"}), 400

    db_id, err = resolve_tenant_database_id()
    if err is not None:
        return err
    requested_db_id = payload.get("database_id")
    if requested_db_id is not None:
        denied = assert_caller_owns_database(requested_db_id)
        if denied is not None:
            return denied
    payload["database_id"] = db_id

    resp, error = superset_request(
        "POST", "/sqllab/estimate/", json_body=payload
    )
    if error is not None:
        return error

    body = safe_json(resp)
    return (
        jsonify(body) if body is not None else Response("", status=resp.status_code),
        resp.status_code,
    )


__all__ = ["sqllab_bp"]
