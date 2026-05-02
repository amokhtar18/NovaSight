"""
Thin proxy from NovaSight to Superset
======================================

Mounted at ``/api/v1/superset/*``. The proxy:

    * verifies the caller's NovaSight JWT and tenant context,
    * forwards the request to the Superset sidecar,
    * passes the original ``Authorization`` header through so the
      ``NovaSightSecurityManager`` on Superset's side can mirror the
      user without prompting for credentials,
    * streams the response back unchanged.

This blueprint exists so the React frontend can keep using NovaSight
URLs (``/api/v1/superset/chart/``, ``/api/v1/superset/sqllab/execute``,
…) without learning Superset's hostname or auth model.

The blueprint is registered in ``app/api/v1/__init__.py`` only when
``SUPERSET_ENABLED=true``, so disabled environments do not expose the
endpoint at all.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from flask import Blueprint, Response, g, jsonify, request

from app.platform.auth.decorators import authenticated, tenant_required

from app.domains.analytics.superset import chart_mapper, dashboard_mapper
from app.domains.analytics.superset._proxy_helpers import (
    assert_caller_owns_database,
    feature_flag_required,
    resolve_tenant_database_id,
    safe_json,
    superset_request,
)

logger = logging.getLogger(__name__)

superset_proxy_bp = Blueprint(
    "superset_proxy", __name__, url_prefix="/superset"
)

# Headers that should never be forwarded verbatim.
_HOP_BY_HOP = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "upgrade",
}


def _superset_base_url() -> str:
    return os.getenv("SUPERSET_BASE_URL", "http://superset:8088").rstrip("/")


def _filter_request_headers() -> dict:
    return {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }


def _filter_response_headers(headers: Any) -> list:
    return [
        (k, v)
        for k, v in headers.items()
        if k.lower() not in _HOP_BY_HOP
    ]


# ---------------------------------------------------------------------------
# Phase 4 — Charts (tenant-scoped, feature-flag gated)
# ---------------------------------------------------------------------------


@superset_proxy_bp.route("/enabled", methods=["GET"])
@authenticated
@tenant_required
def feature_flag_status() -> Any:
    """Expose the per-tenant ``FEATURE_SUPERSET_BACKEND`` flag to the UI."""
    from app.domains.analytics.superset.feature_flag import (
        is_superset_backend_enabled,
    )

    return jsonify({"enabled": bool(is_superset_backend_enabled())}), 200


@superset_proxy_bp.route("/charts", methods=["GET"])
@authenticated
@tenant_required
def list_charts() -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    db_id, err = resolve_tenant_database_id()
    if err is not None:
        return err

    rison_filter = (
        "(filters:!((col:datasource_id,opr:eq,value:" + str(db_id) + ")))"
    )
    resp, error = superset_request(
        "GET", "/chart/", params={"q": rison_filter}
    )
    if error is not None:
        return error

    body = safe_json(resp) or {}
    items = [
        chart_mapper.from_superset_payload(s)
        for s in (body.get("result") or [])
    ]
    return jsonify({"items": items, "total": len(items)}), resp.status_code


@superset_proxy_bp.route("/charts", methods=["POST"])
@authenticated
@tenant_required
def create_chart() -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    payload = request.get_json(silent=True) or {}
    db_id, err = resolve_tenant_database_id()
    if err is not None:
        return err

    superset_body = chart_mapper.to_superset_payload(
        payload, database_id=db_id, tenant_id=str(g.tenant_id)
    )
    resp, error = superset_request(
        "POST", "/chart/", json_body=superset_body
    )
    if error is not None:
        return error

    body = safe_json(resp) or {}
    if resp.status_code >= 400:
        logger.warning("Superset rejected chart create: %s", body)
        return jsonify({"error": "Could not create chart"}), resp.status_code

    chart_id = body.get("id") or (body.get("result") or {}).get("id")
    return jsonify({"id": str(chart_id)}), 201


@superset_proxy_bp.route("/charts/<int:chart_id>", methods=["GET"])
@authenticated
@tenant_required
def get_chart(chart_id: int) -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    resp, error = superset_request("GET", f"/chart/{chart_id}")
    if error is not None:
        return error
    if resp.status_code == 404:
        return jsonify({"error": "Chart not found"}), 404

    body = safe_json(resp) or {}
    raw = body.get("result") or {}

    denied = _assert_chart_belongs_to_tenant(raw)
    if denied is not None:
        return denied

    return jsonify(chart_mapper.from_superset_payload(raw)), resp.status_code


@superset_proxy_bp.route("/charts/<int:chart_id>", methods=["PUT"])
@authenticated
@tenant_required
def update_chart(chart_id: int) -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    db_id, err = resolve_tenant_database_id()
    if err is not None:
        return err

    # Ownership check before write.
    current, error = superset_request("GET", f"/chart/{chart_id}")
    if error is not None:
        return error
    if current.status_code == 404:
        return jsonify({"error": "Chart not found"}), 404
    raw = (safe_json(current) or {}).get("result") or {}
    denied = _assert_chart_belongs_to_tenant(raw)
    if denied is not None:
        return denied

    payload = request.get_json(silent=True) or {}
    superset_body = chart_mapper.to_superset_payload(
        payload, database_id=db_id, tenant_id=str(g.tenant_id)
    )
    resp, error = superset_request(
        "PUT", f"/chart/{chart_id}", json_body=superset_body
    )
    if error is not None:
        return error

    if resp.status_code >= 400:
        logger.warning(
            "Superset rejected chart update id=%s: %s",
            chart_id,
            safe_json(resp),
        )
        return jsonify({"error": "Could not update chart"}), resp.status_code
    return jsonify({"id": str(chart_id)}), resp.status_code


@superset_proxy_bp.route("/charts/<int:chart_id>", methods=["DELETE"])
@authenticated
@tenant_required
def delete_chart(chart_id: int) -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    current, error = superset_request("GET", f"/chart/{chart_id}")
    if error is not None:
        return error
    if current.status_code == 404:
        return jsonify({"error": "Chart not found"}), 404
    raw = (safe_json(current) or {}).get("result") or {}
    denied = _assert_chart_belongs_to_tenant(raw)
    if denied is not None:
        return denied

    resp, error = superset_request("DELETE", f"/chart/{chart_id}")
    if error is not None:
        return error
    return jsonify({"deleted": True}), resp.status_code


@superset_proxy_bp.route("/charts/<int:chart_id>/data", methods=["POST"])
@authenticated
@tenant_required
def chart_data(chart_id: int) -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    current, error = superset_request("GET", f"/chart/{chart_id}")
    if error is not None:
        return error
    if current.status_code == 404:
        return jsonify({"error": "Chart not found"}), 404
    raw = (safe_json(current) or {}).get("result") or {}
    denied = _assert_chart_belongs_to_tenant(raw)
    if denied is not None:
        return denied

    body = request.get_json(silent=True) or {}
    resp, error = superset_request(
        "POST",
        f"/chart/{chart_id}/data/",
        json_body=body,
    )
    if error is not None:
        return error
    return (
        jsonify(safe_json(resp) or {}),
        resp.status_code,
    )


def _assert_chart_belongs_to_tenant(raw: dict) -> Any:
    """Return an error tuple if the slice is not owned by the caller's
    tenant ClickHouse DB; otherwise None."""
    if not raw:
        return jsonify({"error": "Chart not found"}), 404
    datasource_id = raw.get("datasource_id") or raw.get("datasource", {}).get("id")
    if datasource_id is None:
        # Some Superset payloads encode it as ``"<id>__table"`` in
        # ``datasource``. Extract defensively.
        ds = raw.get("datasource")
        if isinstance(ds, str) and "__" in ds:
            try:
                datasource_id = int(ds.split("__", 1)[0])
            except ValueError:
                datasource_id = None
    if datasource_id is None:
        return jsonify({"error": "Forbidden"}), 403
    return assert_caller_owns_database(int(datasource_id))


# ---------------------------------------------------------------------------
# Phase 5 — Dashboards (tenant-scoped, feature-flag gated)
# ---------------------------------------------------------------------------


@superset_proxy_bp.route("/dashboards", methods=["GET"])
@authenticated
@tenant_required
def list_dashboards() -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    resp, error = superset_request("GET", "/dashboard/")
    if error is not None:
        return error
    body = safe_json(resp) or {}
    items = [
        dashboard_mapper.from_superset_payload(d)
        for d in (body.get("result") or [])
        if _dashboard_belongs_to_tenant(d)
    ]
    return jsonify({"items": items, "total": len(items)}), resp.status_code


@superset_proxy_bp.route("/dashboards", methods=["POST"])
@authenticated
@tenant_required
def create_dashboard() -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    payload = request.get_json(silent=True) or {}
    superset_body = dashboard_mapper.to_superset_payload(
        payload,
        tenant_id=str(g.tenant_id),
        chart_id_map=_extract_chart_id_map(payload),
    )
    resp, error = superset_request(
        "POST", "/dashboard/", json_body=superset_body
    )
    if error is not None:
        return error

    if resp.status_code >= 400:
        logger.warning(
            "Superset rejected dashboard create: %s", safe_json(resp)
        )
        return (
            jsonify({"error": "Could not create dashboard"}),
            resp.status_code,
        )
    body = safe_json(resp) or {}
    dashboard_id = body.get("id") or (body.get("result") or {}).get("id")
    return jsonify({"id": str(dashboard_id)}), 201


@superset_proxy_bp.route("/dashboards/<int:dashboard_id>", methods=["GET"])
@authenticated
@tenant_required
def get_dashboard(dashboard_id: int) -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    resp, error = superset_request("GET", f"/dashboard/{dashboard_id}")
    if error is not None:
        return error
    if resp.status_code == 404:
        return jsonify({"error": "Dashboard not found"}), 404

    body = safe_json(resp) or {}
    raw = body.get("result") or {}
    if not _dashboard_belongs_to_tenant(raw):
        return jsonify({"error": "Forbidden"}), 403

    return (
        jsonify(dashboard_mapper.from_superset_payload(raw)),
        resp.status_code,
    )


@superset_proxy_bp.route("/dashboards/<int:dashboard_id>", methods=["PUT"])
@authenticated
@tenant_required
def update_dashboard(dashboard_id: int) -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    current, error = superset_request("GET", f"/dashboard/{dashboard_id}")
    if error is not None:
        return error
    if current.status_code == 404:
        return jsonify({"error": "Dashboard not found"}), 404
    raw = (safe_json(current) or {}).get("result") or {}
    if not _dashboard_belongs_to_tenant(raw):
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    superset_body = dashboard_mapper.to_superset_payload(
        payload,
        tenant_id=str(g.tenant_id),
        chart_id_map=_extract_chart_id_map(payload),
    )
    resp, error = superset_request(
        "PUT", f"/dashboard/{dashboard_id}", json_body=superset_body
    )
    if error is not None:
        return error
    if resp.status_code >= 400:
        return jsonify({"error": "Could not update dashboard"}), resp.status_code
    return jsonify({"id": str(dashboard_id)}), resp.status_code


@superset_proxy_bp.route(
    "/dashboards/<int:dashboard_id>", methods=["DELETE"]
)
@authenticated
@tenant_required
def delete_dashboard(dashboard_id: int) -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    current, error = superset_request("GET", f"/dashboard/{dashboard_id}")
    if error is not None:
        return error
    if current.status_code == 404:
        return jsonify({"error": "Dashboard not found"}), 404
    raw = (safe_json(current) or {}).get("result") or {}
    if not _dashboard_belongs_to_tenant(raw):
        return jsonify({"error": "Forbidden"}), 403

    resp, error = superset_request(
        "DELETE", f"/dashboard/{dashboard_id}"
    )
    if error is not None:
        return error
    return jsonify({"deleted": True}), resp.status_code


@superset_proxy_bp.route(
    "/dashboards/<int:dashboard_id>/charts", methods=["GET"]
)
@authenticated
@tenant_required
def dashboard_charts(dashboard_id: int) -> Any:
    gate = feature_flag_required()
    if gate is not None:
        return gate

    resp, error = superset_request(
        "GET", f"/dashboard/{dashboard_id}/charts"
    )
    if error is not None:
        return error
    body = safe_json(resp) or {}
    return (
        jsonify({"items": body.get("result") or []}),
        resp.status_code,
    )


def _dashboard_belongs_to_tenant(raw: dict) -> bool:
    if not isinstance(raw, dict):
        return False
    import json as _json

    metadata = raw.get("json_metadata") or "{}"
    if isinstance(metadata, str):
        try:
            metadata = _json.loads(metadata)
        except (TypeError, ValueError):
            return False
    if not isinstance(metadata, dict):
        return False
    tenant_id = (metadata.get("novasight") or {}).get("tenant_id")
    return tenant_id == str(getattr(g, "tenant_id", ""))


def _extract_chart_id_map(payload: dict) -> dict:
    """Pull the ``layout[i].chartId`` references into the mapper-friendly map."""
    out = {}
    for block in payload.get("layout") or []:
        if not isinstance(block, dict):
            continue
        chart_id = block.get("chartId") or block.get("chart_id")
        if chart_id is None:
            continue
        widget_id = block.get("i") or block.get("id")
        if widget_id is None:
            continue
        try:
            out[str(widget_id)] = int(chart_id)
        except (TypeError, ValueError):
            continue
    return out


# ---------------------------------------------------------------------------
# Catch-all passthrough — kept for the AI Workbench / Phase 7 use cases.
# ---------------------------------------------------------------------------


@superset_proxy_bp.route(
    "/<path:subpath>",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
@authenticated
@tenant_required
def proxy(subpath: str):
    """Forward a single request to Superset."""
    try:
        url = f"{_superset_base_url()}/api/v1/{subpath}"
        with httpx.Client(timeout=60.0) as client:
            upstream = client.request(
                method=request.method,
                url=url,
                headers=_filter_request_headers(),
                params=request.args,
                content=request.get_data(),
            )
        return Response(
            upstream.content,
            status=upstream.status_code,
            headers=_filter_response_headers(upstream.headers),
        )
    except httpx.HTTPError as exc:
        logger.warning("Superset proxy error for %s: %s", subpath, exc)
        return (
            jsonify(
                {
                    "error": "Superset upstream unavailable; check server logs",
                }
            ),
            502,
        )


__all__ = ["superset_proxy_bp"]
