"""
Shared upstream HTTP client helpers for the Superset proxy routes
==================================================================

The Phase 4–6 routes all need to:

* talk to Superset on behalf of an authenticated NovaSight user,
* know which Superset ``database_id`` belongs to the caller's tenant,
* never trust client-supplied database ids.

This module centralises that plumbing so each route file stays focused
on payload mapping.

It is also where we centralise the **error-redaction** rule: per repo
convention, every Superset proxy endpoint logs ``str(exc)`` server-side
and returns a static, non-leaking JSON body to the caller.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional, Tuple

import httpx
from flask import g, jsonify, request

from app.domains.analytics.superset.feature_flag import (
    is_superset_backend_enabled,
)

logger = logging.getLogger(__name__)


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


def superset_base_url() -> str:
    return os.getenv("SUPERSET_BASE_URL", "http://superset:8088").rstrip("/")


def filter_request_headers() -> Dict[str, str]:
    return {
        k: v
        for k, v in request.headers.items()
        if k.lower() not in _HOP_BY_HOP
    }


def feature_flag_required():
    """
    Tiny gate used by every Phase 4-6 route. Returns ``None`` if the
    flag is on for this tenant; otherwise a Flask response that signals
    the legacy code path should handle the request.
    """
    if is_superset_backend_enabled():
        return None
    # 404 keeps the legacy frontend code path happy: consumers fall back.
    return (
        jsonify(
            {
                "error": "Superset backend not enabled for this tenant",
            }
        ),
        404,
    )


def resolve_tenant_database_id() -> Tuple[Optional[int], Optional[Any]]:
    """
    Look up the Superset ``database_id`` for the current tenant.

    Returns
    -------
    (database_id, error_response)
        If the lookup succeeds, ``database_id`` is an int and
        ``error_response`` is ``None``. Otherwise, ``database_id`` is
        ``None`` and ``error_response`` is a Flask response tuple ready
        to be returned from the route.
    """
    tenant_id = getattr(g, "tenant_id", None)
    if not tenant_id:
        return None, (jsonify({"error": "Tenant context required"}), 403)

    try:
        from app.domains.tenants.domain.models import Tenant
        from app.extensions import db

        tenant = db.session.get(Tenant, tenant_id)
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("Tenant lookup failed: %s", exc)
        return None, (jsonify({"error": "Tenant lookup failed"}), 500)

    if tenant is None:
        return None, (jsonify({"error": "Tenant not found"}), 404)

    expected_name = f"tenant_{tenant.slug}_clickhouse"

    try:
        from app.domains.analytics.superset.tenant_provisioner import (
            SupersetAdminClient,
        )

        admin = SupersetAdminClient()
        with httpx.Client(
            base_url=admin.endpoint.base_url,
            timeout=admin.endpoint.timeout,
        ) as client:
            admin._login(client)  # noqa: SLF001 — internal helper
            row = admin.find_database_by_name(client, expected_name)
    except httpx.HTTPError as exc:
        logger.warning("Superset upstream error during DB lookup: %s", exc)
        return None, (
            jsonify({"error": "Superset upstream unavailable"}),
            502,
        )

    if not row:
        logger.warning(
            "No Superset Database row found for tenant %s (expected %r)",
            tenant_id,
            expected_name,
        )
        return None, (
            jsonify({"error": "Tenant analytics database not provisioned"}),
            409,
        )
    return int(row["id"]), None


def assert_caller_owns_database(database_id: int) -> Optional[Tuple[Any, int]]:
    """
    Defence-in-depth check: ensure ``database_id`` matches the caller's
    tenant ClickHouse DB. Returns ``None`` on success, or a (response,
    status) tuple on failure.
    """
    expected, err = resolve_tenant_database_id()
    if err is not None:
        return err
    if int(database_id) != int(expected):
        logger.warning(
            "Cross-tenant database_id rejected: tenant=%s requested=%s expected=%s",
            getattr(g, "tenant_id", None),
            database_id,
            expected,
        )
        return jsonify({"error": "Forbidden"}), 403
    return None


def superset_request(
    method: str,
    path: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
) -> Tuple[Optional[httpx.Response], Optional[Tuple[Any, int]]]:
    """
    Forward a single request to Superset using the caller's JWT.

    Returns ``(response, error)`` where exactly one of the two is set.
    On HTTP error from Superset we return a static error body to the
    caller, with the upstream details only in the server log.
    """
    url = f"{superset_base_url()}/api/v1{path}"
    headers = filter_request_headers()
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
            )
    except httpx.HTTPError as exc:
        logger.warning("Superset upstream HTTP error %s %s: %s", method, path, exc)
        return None, (jsonify({"error": "Superset upstream unavailable"}), 502)
    return resp, None


def safe_json(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return None


__all__ = [
    "assert_caller_owns_database",
    "feature_flag_required",
    "filter_request_headers",
    "resolve_tenant_database_id",
    "safe_json",
    "superset_base_url",
    "superset_request",
]
