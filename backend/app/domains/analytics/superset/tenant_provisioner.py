"""
Per-tenant Superset Database provisioner
=========================================

For every NovaSight tenant we want exactly ONE Superset ``Database``
row pointing at that tenant's ClickHouse database (created by
``app.domains.tenants.infrastructure.provisioning.ProvisioningService``).

This module exposes a single idempotent function,
``ensure_superset_database_for_tenant``, that the tenant lifecycle hook
in ``lifecycle.py`` calls whenever a tenant is created, activated or
its credentials change.

The function never imports Superset internals: it talks to Superset via
its public REST API. That keeps NovaSight's Flask process decoupled
from Superset's Flask process (which may run in a sidecar container).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SupersetEndpoint:
    """Connection info for talking to the Superset REST API."""

    base_url: str
    admin_username: str
    admin_password: str
    timeout: float = 15.0


def _endpoint_from_env() -> SupersetEndpoint:
    return SupersetEndpoint(
        base_url=os.getenv(
            "SUPERSET_BASE_URL", "http://superset:8088"
        ).rstrip("/"),
        admin_username=os.getenv("SUPERSET_ADMIN_USERNAME", "admin"),
        admin_password=os.getenv("SUPERSET_ADMIN_PASSWORD", "admin"),
    )


# ---------------------------------------------------------------------------
# Tiny REST client (we only need a handful of endpoints)
# ---------------------------------------------------------------------------


class SupersetAdminClient:
    """Minimal admin client for the Superset REST API."""

    def __init__(self, endpoint: Optional[SupersetEndpoint] = None) -> None:
        self.endpoint = endpoint or _endpoint_from_env()
        self._access_token: Optional[str] = None
        self._csrf_token: Optional[str] = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _login(self, client: httpx.Client) -> None:
        resp = client.post(
            "/api/v1/security/login",
            json={
                "username": self.endpoint.admin_username,
                "password": self.endpoint.admin_password,
                "provider": "db",
                "refresh": True,
            },
        )
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]

        csrf = client.get(
            "/api/v1/security/csrf_token/",
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        csrf.raise_for_status()
        self._csrf_token = csrf.json().get("result")

    def _headers(self) -> Dict[str, str]:
        headers = {"Authorization": f"Bearer {self._access_token}"}
        if self._csrf_token:
            headers["X-CSRFToken"] = self._csrf_token
            headers["Referer"] = self.endpoint.base_url
        return headers

    # ------------------------------------------------------------------
    # Database CRUD (the only verbs we need)
    # ------------------------------------------------------------------

    def find_database_by_name(
        self, client: httpx.Client, name: str
    ) -> Optional[Dict[str, Any]]:
        params = {
            "q": (
                "(filters:!((col:database_name,opr:eq,value:'"
                + name.replace("'", "\\'")
                + "')))"
            )
        }
        resp = client.get(
            "/api/v1/database/", headers=self._headers(), params=params
        )
        resp.raise_for_status()
        result = resp.json().get("result", [])
        return result[0] if result else None

    def upsert_database(
        self,
        database_name: str,
        sqlalchemy_uri: str,
        extra: Dict[str, Any],
    ) -> int:
        """
        Create a Database row, or update it if it already exists.

        Returns the Superset database_id.
        """
        with httpx.Client(
            base_url=self.endpoint.base_url,
            timeout=self.endpoint.timeout,
        ) as client:
            self._login(client)

            existing = self.find_database_by_name(client, database_name)
            payload = {
                "database_name": database_name,
                "sqlalchemy_uri": sqlalchemy_uri,
                "expose_in_sqllab": True,
                "allow_run_async": True,
                "allow_dml": False,
                "extra": _dump_json(extra),
            }

            if existing:
                db_id = existing["id"]
                resp = client.put(
                    f"/api/v1/database/{db_id}",
                    headers=self._headers(),
                    json=payload,
                )
                resp.raise_for_status()
                logger.info(
                    "Updated Superset database row id=%s name=%s",
                    db_id,
                    database_name,
                )
                return db_id

            resp = client.post(
                "/api/v1/database/", headers=self._headers(), json=payload
            )
            resp.raise_for_status()
            db_id = resp.json()["id"]
            logger.info(
                "Created Superset database row id=%s name=%s", db_id, database_name
            )
            return db_id


def _dump_json(value: Dict[str, Any]) -> str:
    """Superset's REST API expects the ``extra`` field as a JSON string."""
    import json

    return json.dumps(value, separators=(",", ":"), sort_keys=True)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def ensure_superset_database_for_tenant(
    tenant: Any,
    *,
    client: Optional[SupersetAdminClient] = None,
) -> Optional[int]:
    """
    Idempotently register / update the tenant's Superset Database row.

    Returns the Superset database_id on success, or ``None`` if the
    integration is disabled (``SUPERSET_ENABLED!=true``) or the
    Superset endpoint is unreachable.
    """
    from app.domains.analytics.superset import is_enabled

    if not is_enabled():
        logger.debug(
            "Superset integration disabled — skipping provisioning for %s",
            getattr(tenant, "slug", tenant),
        )
        return None

    ch_host = os.getenv("CLICKHOUSE_HOST", "clickhouse")
    ch_port = os.getenv("CLICKHOUSE_PORT", "8123")
    ch_user = os.getenv("CLICKHOUSE_TENANT_USER", "default")
    ch_password = os.getenv("CLICKHOUSE_TENANT_PASSWORD", "")
    ch_database = f"tenant_{tenant.slug}"

    sqlalchemy_uri = (
        f"clickhousedb+connect://{ch_user}:{ch_password}"
        f"@{ch_host}:{ch_port}/{ch_database}"
    )

    extra = {
        "tenant_id": str(tenant.id),
        "tenant_slug": tenant.slug,
        "managed": True,
        "locked": True,
        "metadata_params": {},
        "engine_params": {},
    }

    admin = client or SupersetAdminClient()
    try:
        return admin.upsert_database(
            database_name=f"tenant_{tenant.slug}_clickhouse",
            sqlalchemy_uri=sqlalchemy_uri,
            extra=extra,
        )
    except httpx.HTTPError as exc:
        logger.warning(
            "Could not provision Superset database for tenant %s: %s",
            tenant.slug,
            exc,
        )
        return None


__all__ = [
    "SupersetAdminClient",
    "SupersetEndpoint",
    "ensure_superset_database_for_tenant",
]
