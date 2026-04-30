"""
Superset connection mutators
=============================

These hooks are registered in ``superset_config.py`` and called by
Superset every time it builds a SQLAlchemy connection. They are the
*last line of defence* that forces every query — whether triggered from
SQL Lab, an Explore chart, or a saved query — to run against the
caller's tenant ClickHouse database **only**.

Three layers are stacked together to lock the datasource down:

1. **Provisioning** — ``tenant_provisioner.py`` is the only piece of
   code allowed to create / update Superset ``Database`` rows. Every
   provisioned row is tagged with ``extra.tenant_id`` and ``managed``.
2. **Mutation** — the functions in this file reject any URI that does
   not target the caller's tenant CH DB.
3. **FAB permission strip** — implemented in ``security_bridge.py``;
   non-admin users never see the "Add database" UI in the first place.

Both functions in this module are intentionally tolerant of being
called outside a Flask request context (e.g. during Superset CLI
``superset init``): when no tenant can be resolved they return the URI
unchanged so that bootstrap commands still work.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_tenant_for(username: Optional[str]) -> Optional[Any]:
    """
    Look up the NovaSight tenant for a Superset username.

    Superset usernames mirrored by ``NovaSightSecurityManager`` use the
    canonical form ``<tenant_id>::<email>``. Anything else is treated
    as a system / bootstrap user and returns ``None`` (no lockdown).
    """
    if not username or "::" not in username:
        return None

    tenant_id, _ = username.split("::", 1)
    try:
        # Imported lazily so this module stays importable from contexts
        # where the NovaSight app context is not yet set up.
        from app.domains.tenants.domain.models import Tenant
        from app.extensions import db

        return db.session.get(Tenant, tenant_id)
    except Exception as exc:  # pragma: no cover — defensive
        logger.debug(
            "Could not resolve tenant '%s' from URI mutator: %s",
            tenant_id,
            exc,
        )
        return None


def _expected_clickhouse_db(tenant: Any) -> str:
    """
    Compute the ClickHouse database name a tenant is allowed to query.

    NovaSight's ``ProvisioningService`` creates one CH database per
    tenant named ``tenant_<slug>``. The same convention is mirrored by
    the per-tenant Superset ``Database`` row created by
    ``tenant_provisioner.ensure_superset_database_for_tenant``.
    """
    return f"tenant_{tenant.slug}"


def _uri_targets_database(uri: str, expected_db: str) -> bool:
    """
    Best-effort check that the SQLAlchemy URI's path component matches
    the expected database name. Works for any dialect.
    """
    try:
        parsed = urlparse(str(uri))
        # urlparse path includes the leading slash (e.g. "/tenant_acme")
        actual = re.sub(r"^/", "", parsed.path or "")
        # Some clickhouse URIs include the database as a query param.
        if not actual:
            actual = parsed.query.split("database=")[-1].split("&")[0]
        return actual == expected_db
    except Exception:  # pragma: no cover — defensive
        return False


# ---------------------------------------------------------------------------
# Public Superset hooks
# ---------------------------------------------------------------------------


def db_connection_mutator(
    uri: Any,
    params: dict,
    username: Optional[str],
    security_manager: Any,
    source: Optional[str],
) -> Tuple[Any, dict]:
    """
    Superset hook: ``DB_CONNECTION_MUTATOR``.

    Called for every SQL Lab / chart / explore connection. We use it to
    guarantee the URI targets the caller's tenant ClickHouse DB.
    """
    tenant = _resolve_tenant_for(username)
    if tenant is None:
        # No NovaSight identity (bootstrap, CLI, system tasks) — let
        # Superset run with the URI it already validated upstream.
        return uri, params

    expected_db = _expected_clickhouse_db(tenant)
    if not _uri_targets_database(str(uri), expected_db):
        # We deliberately raise a generic ``Exception`` here instead of
        # importing ``SupersetSecurityException`` so this module stays
        # importable without Superset installed (unit tests, lint).
        raise PermissionError(
            f"Cross-tenant database access denied for user "
            f"{username!r}: expected '{expected_db}', got URI {uri!r}"
        )

    return uri, params


def sqlalchemy_uri_mutator(uri: str) -> str:
    """
    Superset hook: ``SQLALCHEMY_URI_MUTATOR``.

    Pre-process URIs at the moment a database row is saved. We currently
    only enforce a non-empty database segment so that a tenant URI can
    never be persisted as a server-wide connection.
    """
    parsed = urlparse(str(uri))
    db_segment = re.sub(r"^/", "", parsed.path or "")
    if not db_segment and "database=" not in (parsed.query or ""):
        raise ValueError(
            "NovaSight policy: every Superset database must specify a "
            "ClickHouse database in the URI; server-only URIs are not "
            "allowed."
        )
    return str(uri)


__all__ = ["db_connection_mutator", "sqlalchemy_uri_mutator"]
