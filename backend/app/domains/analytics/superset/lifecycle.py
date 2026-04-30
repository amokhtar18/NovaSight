"""
Tenant lifecycle hook for the Superset integration
====================================================

Subscribes to NovaSight tenant lifecycle events and asks the
``tenant_provisioner`` to keep the Superset side in sync. Importing
this module has **no side effects** until ``register()`` is called from
the application factory — which itself only fires when the integration
is enabled.

This is the only file in the integration that touches an existing
domain, and it does so via SQLAlchemy events on the ``Tenant`` model
rather than by editing tenant business logic.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from sqlalchemy import event

logger = logging.getLogger(__name__)

_REGISTERED = False
_LOCK = threading.Lock()


def register() -> None:
    """
    Idempotently subscribe to ``Tenant`` model lifecycle events.

    Safe to call multiple times — only the first call wires up the
    listeners.
    """
    global _REGISTERED
    with _LOCK:
        if _REGISTERED:
            return

        from app.domains.tenants.domain.models import Tenant

        @event.listens_for(Tenant, "after_insert")
        def _on_tenant_insert(_mapper, _conn, target: Any) -> None:
            _safe_provision(target, "after_insert")

        @event.listens_for(Tenant, "after_update")
        def _on_tenant_update(_mapper, _conn, target: Any) -> None:
            _safe_provision(target, "after_update")

        _REGISTERED = True
        logger.info(
            "Registered Superset provisioning hooks on Tenant model"
        )


def _safe_provision(tenant: Any, source: str) -> None:
    """Run the provisioner without ever raising into the SQLAlchemy event."""
    try:
        # Imported lazily to avoid pulling httpx into module import time.
        from app.domains.analytics.superset.tenant_provisioner import (
            ensure_superset_database_for_tenant,
        )

        # Only act on active tenants — suspended / archived tenants are
        # left in place so dashboards keep loading historical data.
        status = getattr(tenant, "status", None)
        status_value = getattr(status, "value", None) or str(status or "")
        if status_value.lower() != "active":
            return

        ensure_superset_database_for_tenant(tenant)
    except Exception as exc:  # noqa: BLE001 — never crash the host txn
        logger.warning(
            "Superset provisioning skipped for tenant=%s (source=%s): %s",
            getattr(tenant, "slug", tenant),
            source,
            exc,
        )


__all__ = ["register"]
