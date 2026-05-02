"""Integration tests for the Superset SQL Lab routes (Phase 6)."""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _enable_superset(monkeypatch):
    monkeypatch.setenv("SUPERSET_ENABLED", "true")
    monkeypatch.setenv("FEATURE_SUPERSET_BACKEND_DEFAULT", "true")
    yield


@pytest.fixture
def auth_headers(integration_client, seeded_tenant) -> Dict[str, str]:
    resp = integration_client.post(
        "/api/v1/auth/login",
        json={
            "email": seeded_tenant["admin_email"],
            "password": seeded_tenant["admin_password"],
        },
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


def _stub_db_lookup(monkeypatch, db_id: int = 42):
    from app.domains.analytics.superset import (
        _proxy_helpers,
        proxy_routes,
        sqllab_routes,
    )

    fake = lambda: (db_id, None)  # noqa: E731
    monkeypatch.setattr(_proxy_helpers, "resolve_tenant_database_id", fake)
    monkeypatch.setattr(proxy_routes, "resolve_tenant_database_id", fake)
    monkeypatch.setattr(sqllab_routes, "resolve_tenant_database_id", fake)


def test_select_one_executes(
    integration_client, auth_headers, monkeypatch
):
    _stub_db_lookup(monkeypatch, db_id=42)
    captured: Dict[str, Any] = {}

    def _request(method, url, **kw):
        if method == "POST" and url.endswith("/api/v1/sqllab/execute/"):
            captured["json"] = kw.get("json")
            return httpx.Response(
                200,
                json={
                    "data": [{"x": 1}],
                    "columns": [{"name": "x", "type": "Int"}],
                    "query": {"state": "success"},
                },
                request=httpx.Request(method, url),
            )
        return httpx.Response(
            404, json={}, request=httpx.Request(method, url)
        )

    with patch("httpx.Client.request", side_effect=_request):
        resp = integration_client.post(
            "/api/v1/superset/sqllab/execute",
            json={"sql": "SELECT 1"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    # The route must inject the caller's tenant DB id, ignoring any
    # client-supplied database_id.
    assert captured["json"]["database_id"] == 42


def test_forged_database_id_is_overwritten(
    integration_client, auth_headers, monkeypatch
):
    _stub_db_lookup(monkeypatch, db_id=42)
    captured: Dict[str, Any] = {}

    def _request(method, url, **kw):
        captured["json"] = kw.get("json")
        return httpx.Response(
            200,
            json={"data": [], "columns": [], "query": {"state": "success"}},
            request=httpx.Request(method, url),
        )

    with patch("httpx.Client.request", side_effect=_request):
        resp = integration_client.post(
            "/api/v1/superset/sqllab/execute",
            json={"sql": "SELECT 1", "database_id": 999, "datasource_id": 999},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    assert captured["json"]["database_id"] == 42  # forgery overridden


def test_disabled_when_flag_off(
    integration_client, auth_headers, monkeypatch
):
    monkeypatch.setenv("FEATURE_SUPERSET_BACKEND_DEFAULT", "false")
    resp = integration_client.post(
        "/api/v1/superset/sqllab/execute",
        json={"sql": "SELECT 1"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_async_execution_passes_through(
    integration_client, auth_headers, monkeypatch
):
    _stub_db_lookup(monkeypatch, db_id=42)

    def _request(method, url, **kw):
        return httpx.Response(
            202,
            json={"query_id": 5, "status": "running"},
            request=httpx.Request(method, url),
        )

    with patch("httpx.Client.request", side_effect=_request):
        resp = integration_client.post(
            "/api/v1/superset/sqllab/execute",
            json={"sql": "SELECT 1", "runAsync": True},
            headers=auth_headers,
        )
    assert resp.status_code == 202
