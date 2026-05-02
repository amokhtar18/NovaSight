"""Unit tests for the Superset dashboard payload mapper."""

from __future__ import annotations

import json

import pytest

from app.domains.analytics.superset import dashboard_mapper


REPRESENTATIVE_LAYOUTS = [
    # 1) Simple two-tile dashboard.
    [
        {"i": "w1", "x": 0, "y": 0, "w": 6, "h": 4, "chartId": 11},
        {"i": "w2", "x": 6, "y": 0, "w": 6, "h": 4, "chartId": 12},
    ],
    # 2) Mixed sizes / 3 rows.
    [
        {"i": "kpi", "x": 0, "y": 0, "w": 12, "h": 2, "chartId": 21},
        {"i": "trend", "x": 0, "y": 2, "w": 8, "h": 6, "chartId": 22},
        {"i": "ratio", "x": 8, "y": 2, "w": 4, "h": 6, "chartId": 23},
    ],
    # 3) Widget without a chartId (placeholder).
    [
        {"i": "tile-only", "x": 0, "y": 0, "w": 4, "h": 3},
        {"i": "with-chart", "x": 4, "y": 0, "w": 8, "h": 3, "chartId": 99},
    ],
]


@pytest.mark.parametrize("layout", REPRESENTATIVE_LAYOUTS)
def test_layout_round_trip(layout):
    chart_id_map = {b["i"]: b["chartId"] for b in layout if "chartId" in b}
    payload = dashboard_mapper.to_superset_payload(
        {"name": "ops", "layout": layout},
        tenant_id="t-1",
        chart_id_map=chart_id_map,
    )

    raw = {
        "id": 99,
        "dashboard_title": "ops",
        "json_metadata": payload["json_metadata"],
        "position_json": payload["position_json"],
    }
    back = dashboard_mapper.from_superset_payload(raw)
    assert back["name"] == "ops"
    assert back["tenant_id"] == "t-1"
    # The mapper preserves the original RGL layout under metadata so the
    # round-trip is lossless even with placeholder tiles.
    assert back["layout"] == layout


def test_to_superset_requires_name():
    with pytest.raises(ValueError):
        dashboard_mapper.to_superset_payload(
            {"layout": []}, tenant_id="t"
        )


def test_position_json_includes_chart_nodes():
    layout = [
        {"i": "w1", "x": 0, "y": 0, "w": 4, "h": 3, "chartId": 5},
    ]
    payload = dashboard_mapper.to_superset_payload(
        {"name": "x", "layout": layout},
        tenant_id="t",
        chart_id_map={"w1": 5},
    )
    position = json.loads(payload["position_json"])
    chart_nodes = [
        n for n in position.values()
        if isinstance(n, dict) and n.get("type") == "CHART"
    ]
    assert len(chart_nodes) == 1
    assert chart_nodes[0]["meta"]["chartId"] == 5


def test_from_superset_handles_missing_metadata():
    raw = {
        "id": 1,
        "dashboard_title": "noname",
        "json_metadata": "",
        "position_json": "",
    }
    out = dashboard_mapper.from_superset_payload(raw)
    assert out["name"] == "noname"
    assert out["layout"] == []


def test_from_superset_rebuilds_layout_when_meta_missing():
    """When the round-trip metadata is gone (e.g. Superset CLI export),
    the mapper must fall back to scanning ``position_json``."""
    layout = [{"i": "wA", "w": 6, "h": 4, "chartId": 5}]
    payload = dashboard_mapper.to_superset_payload(
        {"name": "x", "layout": layout},
        tenant_id="t",
        chart_id_map={"wA": 5},
    )
    raw = {
        "id": 1,
        "dashboard_title": "x",
        # metadata stripped on purpose
        "json_metadata": json.dumps({"novasight": {"tenant_id": "t"}}),
        "position_json": payload["position_json"],
    }
    out = dashboard_mapper.from_superset_payload(raw)
    # Should at least surface one widget with the right chart id.
    chart_ids = [b.get("chartId") for b in out["layout"]]
    assert 5 in chart_ids
