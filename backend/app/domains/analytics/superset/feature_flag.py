"""
Per-tenant Superset backend feature flag
=========================================

Phases 4–6 of the Superset integration ship behind a per-tenant boolean
``FEATURE_SUPERSET_BACKEND`` so legacy and Superset-backed paths can
coexist while we migrate.

The flag is read from the tenant's ``settings`` JSONB column. The key is
``feature_superset_backend`` (lowercase, snake_case for storage).
A global env var ``FEATURE_SUPERSET_BACKEND_DEFAULT`` provides the
fallback when the tenant has not opted in either way.

Per repo convention, this module never raises on missing context — it
returns a safe default (``False``) so the legacy path stays in use.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from flask import g

logger = logging.getLogger(__name__)

_TENANT_SETTING_KEY = "feature_superset_backend"
_ENV_DEFAULT = "FEATURE_SUPERSET_BACKEND_DEFAULT"


def _global_default() -> bool:
    return os.getenv(_ENV_DEFAULT, "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _resolve_tenant(tenant_id: Optional[str]) -> Optional[Any]:
    if not tenant_id:
        return None
    try:
        from app.domains.tenants.domain.models import Tenant
        from app.extensions import db

        return db.session.get(Tenant, tenant_id)
    except Exception as exc:  # pragma: no cover — defensive
        logger.debug("Could not resolve tenant for feature flag: %s", exc)
        return None


def is_superset_backend_enabled(tenant_id: Optional[str] = None) -> bool:
    """
    Return True if the calling tenant should use the Superset-backed
    chart / dashboard / SQL Lab paths.

    Lookup order:
        1. Explicit ``tenant_id`` argument.
        2. ``flask.g.tenant_id`` if a Flask request is in flight.
        3. Global env default.
    """
    resolved_tenant_id = tenant_id or getattr(g, "tenant_id", None)
    tenant = _resolve_tenant(resolved_tenant_id)
    if tenant is not None:
        settings = getattr(tenant, "settings", None) or {}
        if isinstance(settings, dict) and _TENANT_SETTING_KEY in settings:
            return bool(settings.get(_TENANT_SETTING_KEY))
    return _global_default()


__all__ = ["is_superset_backend_enabled"]
