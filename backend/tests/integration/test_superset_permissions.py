"""Tests for the Superset connection mutator and FAB lockdown (Phase 8)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.domains.analytics.superset import mutators


class _FakeTenant:
    def __init__(self, slug="acme"):
        self.slug = slug


def _patch_resolver(monkeypatch, tenant):
    monkeypatch.setattr(
        mutators, "_resolve_tenant_for", lambda username: tenant
    )


def test_mutator_accepts_correct_db_and_host(monkeypatch):
    _patch_resolver(monkeypatch, _FakeTenant("acme"))
    monkeypatch.setenv("CLICKHOUSE_HOST", "ch.local")
    out_uri, out_params = mutators.db_connection_mutator(
        "clickhousedb+http://u:p@ch.local:8123/tenant_acme",
        {},
        "tenant-1::user@example.com",
        MagicMock(),
        "sqllab",
    )
    assert "tenant_acme" in str(out_uri)


def test_mutator_rejects_wrong_database(monkeypatch):
    _patch_resolver(monkeypatch, _FakeTenant("acme"))
    monkeypatch.setenv("CLICKHOUSE_HOST", "ch.local")
    with pytest.raises(PermissionError):
        mutators.db_connection_mutator(
            "clickhousedb+http://u:p@ch.local:8123/tenant_other",
            {},
            "tenant-1::user@example.com",
            MagicMock(),
            "sqllab",
        )


def test_mutator_rejects_wrong_host(monkeypatch):
    _patch_resolver(monkeypatch, _FakeTenant("acme"))
    monkeypatch.setenv("CLICKHOUSE_HOST", "ch.local")
    with pytest.raises(PermissionError):
        mutators.db_connection_mutator(
            "clickhousedb+http://u:p@evil.example.com:8123/tenant_acme",
            {},
            "tenant-1::user@example.com",
            MagicMock(),
            "sqllab",
        )


def test_mutator_rejects_uri_without_database(monkeypatch):
    """
    A URI with no ``/database`` segment must not pass — without a
    database the mutator can't enforce isolation.
    """
    _patch_resolver(monkeypatch, _FakeTenant("acme"))
    monkeypatch.delenv("CLICKHOUSE_HOST", raising=False)
    with pytest.raises(PermissionError):
        mutators.db_connection_mutator(
            "clickhousedb+http://u:p@ch.local:8123/",
            {},
            "tenant-1::user@example.com",
            MagicMock(),
            "sqllab",
        )


def test_mutator_handles_query_string_database(monkeypatch):
    """``?database=`` style URIs are extracted correctly."""
    _patch_resolver(monkeypatch, _FakeTenant("acme"))
    monkeypatch.delenv("CLICKHOUSE_HOST", raising=False)
    out_uri, _ = mutators.db_connection_mutator(
        "clickhousedb+http://u:p@ch.local:8123/?database=tenant_acme",
        {},
        "tenant-1::user@example.com",
        MagicMock(),
        "sqllab",
    )
    assert "tenant_acme" in str(out_uri)


def test_mutator_passes_through_for_system_user(monkeypatch):
    """Non-tenant users (e.g. bootstrap admin) must not be locked down."""
    monkeypatch.setattr(
        mutators, "_resolve_tenant_for", lambda username: None
    )
    out_uri, _ = mutators.db_connection_mutator(
        "clickhousedb+http://u:p@ch.local:8123/anywhere",
        {},
        "admin",
        MagicMock(),
        "sqllab",
    )
    assert "anywhere" in str(out_uri)


def test_sqlalchemy_uri_mutator_rejects_empty_db():
    with pytest.raises(ValueError):
        mutators.sqlalchemy_uri_mutator(
            "clickhousedb+http://u:p@ch.local:8123/"
        )


def test_sqlalchemy_uri_mutator_accepts_query_string_db():
    out = mutators.sqlalchemy_uri_mutator(
        "clickhousedb+http://u:p@ch.local:8123/?database=tenant_acme"
    )
    assert "tenant_acme" in out


# ---------------------------------------------------------------------------
# FAB permission lockdown
# ---------------------------------------------------------------------------


def test_revoke_view_permissions_strips_dangerous_perms():
    """
    Verify the inner helper ``_revoke_view_permissions`` removes only
    the targeted (action, view) tuples and leaves benign perms alone.
    """
    from app.domains.analytics.superset import permissions as perms

    def _make_perm(action: str, view: str):
        return SimpleNamespace(
            permission=SimpleNamespace(name=action),
            view_menu=SimpleNamespace(name=view),
        )

    role = SimpleNamespace(
        name="Public",
        permissions=[
            _make_perm("can_add", "Database"),
            _make_perm("can_edit", "Database"),
            _make_perm("can_delete", "Database"),
            _make_perm("can_csv_upload", "Database"),
            _make_perm("can_excel_upload", "Database"),
            _make_perm("menu_access", "Dashboards"),  # benign
            _make_perm("can_add", "Chart"),  # different view, must stay
        ],
    )

    revoked_db = perms._revoke_view_permissions(
        role,
        view_menu_name="Database",
        permission_names={"can_add", "can_edit", "can_delete"},
        security_manager=MagicMock(),
    )
    revoked_global = perms._revoke_view_permissions(
        role,
        view_menu_name=None,
        permission_names={"can_csv_upload", "can_excel_upload"},
        security_manager=MagicMock(),
    )

    assert revoked_db == 3
    assert revoked_global == 2
    remaining = [
        (p.permission.name, p.view_menu.name) for p in role.permissions
    ]
    assert ("menu_access", "Dashboards") in remaining
    assert ("can_add", "Chart") in remaining
    assert ("can_add", "Database") not in remaining


def test_flask_app_mutator_never_raises(monkeypatch):
    """
    The mutator must swallow errors so a misconfigured permission row
    can never crash Superset boot.
    """
    from app.domains.analytics.superset import permissions as perms

    def _boom(_app):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(perms, "apply_tenant_permission_lockdown", _boom)

    # Should not raise.
    perms.flask_app_mutator(SimpleNamespace())


def test_apply_lockdown_returns_zero_when_superset_not_available():
    """When Superset is not installed (unit-test env), the function
    must short-circuit safely and return 0."""
    from app.domains.analytics.superset import permissions as perms

    # Real call — superset isn't installed in the test image so the
    # internal lazy import raises and the function returns 0.
    result = perms.apply_tenant_permission_lockdown(SimpleNamespace())
    assert isinstance(result, int)
    assert result == 0
