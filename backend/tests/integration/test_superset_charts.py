"""Integration tests for the Superset Charts proxy routes (Phase 4)."""

from __future__ import annotations

import os
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
    assert resp.status_code == 200, resp.get_json()
    token = resp.get_json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _fake_superset(routes: Dict[str, Any]):
    """
    Build a side_effect function for ``httpx.Client.request`` so we can
    mock the Superset upstream without spinning a server.
    """

    def _side_effect(method, url, **kwargs):
        for (m, suffix), responder in routes.items():
            if method == m and url.endswith(suffix):
                payload = responder(kwargs) if callable(responder) else responder
                status = payload.get("_status", 200)
                return httpx.Response(
                    status,
                    json=payload.get("_json", {}),
                    request=httpx.Request(method, url),
                )
        return httpx.Response(
            404, json={"message": "no mock route"}, request=httpx.Request(method, url)
        )

    return _side_effect


def _stub_db_lookup(monkeypatch):
    """Force the proxy to skip the live database lookup."""
    from app.domains.analytics.superset import (
        _proxy_helpers,
        proxy_routes,
        sqllab_routes,
    )

    def _fake(): return 42, None
    monkeypatch.setattr(_proxy_helpers, "resolve_tenant_database_id", _fake)
    monkeypatch.setattr(proxy_routes, "resolve_tenant_database_id", _fake)
    monkeypatch.setattr(sqllab_routes, "resolve_tenant_database_id", _fake)


def test_chart_create_injects_database_id(
    integration_client, auth_headers, monkeypatch
):
    _stub_db_lookup(monkeypatch)

    captured: Dict[str, Any] = {}

    def _request(method, url, **kw):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = kw.get("json")
        return httpx.Response(
            201,
            json={"id": 7, "result": {"id": 7}},
            request=httpx.Request(method, url),
        )

    with patch("httpx.Client.request", side_effect=_request):
        resp = integration_client.post(
            "/api/v1/superset/charts",
            json={
                "name": "Demo bar",
                "chart_type": "bar",
                "source_type": "semantic_model",
                "query_config": {"dimensions": ["region"], "measures": ["m"]},
                "viz_config": {},
            },
            headers=auth_headers,
        )

    assert resp.status_code == 201, resp.get_json()
    assert captured["method"] == "POST"
    assert captured["url"].endswith("/api/v1/chart/")
    body = captured["json"]
    assert body["datasource_id"] == 42  # server injected, never trusted
    assert body["datasource_type"] == "table"


def test_chart_get_rejects_cross_tenant(
    integration_client, auth_headers, monkeypatch
):
    _stub_db_lookup(monkeypatch)

    def _request(method, url, **kw):
        if method == "GET" and url.endswith("/api/v1/chart/99"):
            return httpx.Response(
                200,
                json={"result": {"id": 99, "datasource_id": 999}},
                request=httpx.Request(method, url),
            )
        return httpx.Response(
            404, json={}, request=httpx.Request(method, url)
        )

    with patch("httpx.Client.request", side_effect=_request):
        resp = integration_client.get(
            "/api/v1/superset/charts/99", headers=auth_headers
        )
    assert resp.status_code == 403


def test_chart_create_requires_feature_flag(
    integration_client, auth_headers, monkeypatch
):
    monkeypatch.setenv("FEATURE_SUPERSET_BACKEND_DEFAULT", "false")
    resp = integration_client.post(
        "/api/v1/superset/charts",
        json={"name": "x", "chart_type": "bar", "query_config": {}},
        headers=auth_headers,
    )
    # Flag off: the route returns a static error so the legacy code path is used.
    assert resp.status_code == 404
