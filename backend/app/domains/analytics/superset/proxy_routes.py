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
from flask import Blueprint, Response, jsonify, request

from app.platform.auth.decorators import authenticated, tenant_required

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
                    "error": "Superset upstream unavailable",
                    "details": str(exc),
                }
            ),
            502,
        )


__all__ = ["superset_proxy_bp"]
