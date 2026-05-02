"""
Superset FAB permission lockdown
=================================

Phase 8 of the integration: prove that no end user — regardless of
their FAB role — can register, edit, or impersonate any Superset
``Database`` other than their own tenant's ClickHouse DB.

This module exposes a single idempotent function,
``apply_tenant_permission_lockdown``, that is wired into Superset via
``FLASK_APP_MUTATOR``. It runs on every Flask boot and:

1. Strips the ``can_add`` / ``can_edit`` / ``can_delete`` permissions
   on the ``Database`` view from every non-Admin role.
2. Strips ``can_csv_upload`` and ``can_excel_upload`` from every
   non-Admin role.
3. Iterates over all ``database_access`` permission-views and revokes
   them from any role whose linked tenant id does not match the
   database's ``extra.tenant_id``.

The function is tolerant of being executed during ``superset init``
(when no roles or databases yet exist) — it simply returns 0.

The module is importable without ``apache-superset`` installed: every
Superset import is performed lazily inside the function body so unit
tests can stub the FAB session.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Iterable, Optional, Set

logger = logging.getLogger(__name__)

# Permissions removed from every non-Admin role.
_ALWAYS_DENIED_DATABASE_PERMS = frozenset(
    {"can_add", "can_edit", "can_delete"}
)
_ALWAYS_DENIED_GLOBAL_PERMS = frozenset(
    {"can_csv_upload", "can_excel_upload"}
)


def _is_admin_role(role: Any) -> bool:
    name = getattr(role, "name", "") or ""
    return name.strip().lower() == "admin"


def _tenant_id_for_role(role: Any) -> Optional[str]:
    """Roles created by ``security_bridge.NovaSightSecurityManager`` are
    named ``tenant::<tenant_id>``. Anything else returns None."""
    name = getattr(role, "name", "") or ""
    if not name.startswith("tenant::"):
        return None
    return name.split("::", 1)[1] or None


def _tenant_id_from_database(database: Any) -> Optional[str]:
    extra_raw = getattr(database, "extra", None)
    if not extra_raw:
        return None
    try:
        extra = (
            extra_raw if isinstance(extra_raw, dict) else json.loads(extra_raw)
        )
    except (TypeError, ValueError):
        return None
    if not isinstance(extra, dict):
        return None
    return extra.get("tenant_id")


def apply_tenant_permission_lockdown(app: Any) -> int:
    """
    Idempotent FAB permission strip.

    Returns the number of permission-views revoked across all roles
    (useful for testing / metrics).

    Parameters
    ----------
    app:
        The Superset Flask app, as passed to ``FLASK_APP_MUTATOR``.
    """
    try:
        from superset import security_manager  # type: ignore
        from superset.models.core import Database  # type: ignore
    except Exception as exc:  # pragma: no cover — only outside Superset
        logger.debug(
            "apply_tenant_permission_lockdown: Superset not available (%s)",
            exc,
        )
        return 0

    revoked = 0
    with app.app_context():
        roles = list(security_manager.get_session.query(
            security_manager.role_model
        ).all())

        # ----- 1 + 2: deny dangerous DB-view perms for every non-Admin role.
        for role in roles:
            if _is_admin_role(role):
                continue
            revoked += _revoke_view_permissions(
                role,
                view_menu_name="Database",
                permission_names=_ALWAYS_DENIED_DATABASE_PERMS,
                security_manager=security_manager,
            )
            revoked += _revoke_view_permissions(
                role,
                view_menu_name=None,  # global perms
                permission_names=_ALWAYS_DENIED_GLOBAL_PERMS,
                security_manager=security_manager,
            )

        # ----- 3: revoke cross-tenant ``database_access`` perms.
        databases = list(
            security_manager.get_session.query(Database).all()
        )
        db_tenant_lookup = {
            f"[{db.database_name}].(id:{db.id})": _tenant_id_from_database(
                db
            )
            for db in databases
        }
        # Superset stores the view_menu name as ``[<db_name>].(id:<id>)``.

        for role in roles:
            if _is_admin_role(role):
                continue
            role_tenant_id = _tenant_id_for_role(role)
            for pv in list(role.permissions):
                if (
                    getattr(pv.permission, "name", None)
                    != "database_access"
                ):
                    continue
                vm_name = getattr(pv.view_menu, "name", "") or ""
                db_tenant_id = db_tenant_lookup.get(vm_name)
                if (
                    db_tenant_id is None
                    or role_tenant_id is None
                    or db_tenant_id != role_tenant_id
                ):
                    role.permissions.remove(pv)
                    revoked += 1

        security_manager.get_session.commit()

    if revoked:
        logger.info(
            "Superset tenant permission lockdown revoked %d permission-views",
            revoked,
        )
    return revoked


def _revoke_view_permissions(
    role: Any,
    *,
    view_menu_name: Optional[str],
    permission_names: Iterable[str],
    security_manager: Any,
) -> int:
    revoked = 0
    targets: Set[str] = set(permission_names)
    for pv in list(role.permissions):
        perm_name = getattr(pv.permission, "name", None)
        if perm_name not in targets:
            continue
        if view_menu_name is not None:
            vm_name = getattr(pv.view_menu, "name", None)
            if vm_name != view_menu_name:
                continue
        role.permissions.remove(pv)
        revoked += 1
    return revoked


def flask_app_mutator(app: Any) -> None:
    """
    Entry point registered by ``superset_config.FLASK_APP_MUTATOR``.

    Wraps ``apply_tenant_permission_lockdown`` and never raises — a
    permission-strip failure must not prevent Superset from booting.
    """
    try:
        apply_tenant_permission_lockdown(app)
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(
            "Superset permission lockdown failed but boot continues: %s",
            exc,
        )


__all__ = [
    "apply_tenant_permission_lockdown",
    "flask_app_mutator",
]
