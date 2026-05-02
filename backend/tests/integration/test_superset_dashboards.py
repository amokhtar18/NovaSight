"""Integration tests for the Superset Dashboards proxy routes (Phase 5)."""

from __future__ import annotations

import json
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


def _stub_db_lookup(monkeypatch):
    from app.domains.analytics.superset import (
        _proxy_helpers,
        proxy_routes,
        sqllab_routes,
    )

    fake = lambda: (42, None)  # noqa: E731
    monkeypatch.setattr(_proxy_helpers, "resolve_tenant_database_id", fake)
    monkeypatch.setattr(proxy_routes, "resolve_tenant_database_id", fake)
    monkeypatch.setattr(sqllab_routes, "resolve_tenant_database_id", fake)


def test_dashboard_list_filters_by_tenant(
    integration_client, auth_headers, monkeypatch, seeded_tenant
):
    _stub_db_lookup(monkeypatch)

    own_tid = seeded_tenant["tenant_id"]
    other_tid = "deadbeef-0000-0000-0000-000000000000"

    def _request(method, url, **kw):
        if method == "GET" and "/api/v1/dashboard/" in url:
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "id": 1,
                            "dashboard_title": "mine",
                            "json_metadata": json.dumps(
                                {"novasight": {"tenant_id": own_tid}}
                            ),
                            "position_json": "{}",
                        },
                        {
                            "id": 2,
                            "dashboard_title": "theirs",
                            "json_metadata": json.dumps(
                                {"novasight": {"tenant_id": other_tid}}
                            ),
                            "position_json": "{}",
                        },
                    ],
                    "count": 2,
                },
                request=httpx.Request(method, url),
            )
        return httpx.Response(
            404, json={}, request=httpx.Request(method, url)
        )

    with patch("httpx.Client.request", side_effect=_request):
        resp = integration_client.get(
            "/api/v1/superset/dashboards", headers=auth_headers
        )

    assert resp.status_code == 200
    items = resp.get_json()["items"]
    titles = [i["name"] for i in items]
    assert "mine" in titles
    assert "theirs" not in titles


def test_dashboard_get_cross_tenant_is_forbidden(
    integration_client, auth_headers, monkeypatch
):
    _stub_db_lookup(monkeypatch)

    def _request(method, url, **kw):
        return httpx.Response(
            200,
            json={
                "result": {
                    "id": 9,
                    "dashboard_title": "other",
                    "json_metadata": json.dumps(
                        {"novasight": {"tenant_id": "other-tenant"}}
                    ),
                    "position_json": "{}",
                }
            },
            request=httpx.Request(method, url),
        )

    with patch("httpx.Client.request", side_effect=_request):
        resp = integration_client.get(
            "/api/v1/superset/dashboards/9", headers=auth_headers
        )
    assert resp.status_code == 403


def test_dashboard_create_stamps_tenant(
    integration_client, auth_headers, monkeypatch
):
    _stub_db_lookup(monkeypatch)
    captured: Dict[str, Any] = {}

    def _request(method, url, **kw):
        if method == "POST" and url.endswith("/api/v1/dashboard/"):
            captured["json"] = kw.get("json")
            return httpx.Response(
                201,
                json={"id": 1, "result": {"id": 1}},
                request=httpx.Request(method, url),
            )
        return httpx.Response(
            404, json={}, request=httpx.Request(method, url)
        )

    with patch("httpx.Client.request", side_effect=_request):
        resp = integration_client.post(
            "/api/v1/superset/dashboards",
            json={"name": "K", "layout": []},
            headers=auth_headers,
        )

    assert resp.status_code == 201
    body = captured["json"]
    meta = json.loads(body["json_metadata"])
    assert "tenant_id" in meta["novasight"]
