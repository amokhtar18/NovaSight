"""Unit tests for the Superset chart payload mapper."""

from __future__ import annotations

import json

import pytest

from app.domains.analytics.superset import chart_mapper


SUPPORTED_TYPES = [
    "bar",
    "line",
    "area",
    "pie",
    "table",
    "metric",
    "scatter",
    "treemap",
]


@pytest.mark.parametrize("chart_type", SUPPORTED_TYPES)
def test_chart_type_to_viz_round_trip(chart_type):
    viz = chart_mapper.chart_type_to_viz(chart_type)
    back = chart_mapper.viz_to_chart_type(viz)
    # ``metric`` round-trips through ``big_number_total``; allow either.
    assert back == chart_type or (chart_type == "metric" and back == "metric")


def test_to_superset_payload_minimum_fields():
    payload = chart_mapper.to_superset_payload(
        {
            "name": "Sales by Region",
            "chart_type": "bar",
            "source_type": "semantic_model",
            "query_config": {
                "dimensions": ["region"],
                "measures": ["revenue"],
                "limit": 100,
            },
            "viz_config": {"showLegend": True},
        },
        database_id=42,
        tenant_id="tenant-abc",
    )

    assert payload["slice_name"] == "Sales by Region"
    assert payload["datasource_id"] == 42
    assert payload["datasource_type"] == "table"
    params = json.loads(payload["params"])
    assert params["viz_type"] == "echarts_timeseries_bar"
    assert params["groupby"] == ["region"]
    assert params["metrics"] == ["revenue"]
    assert params["row_limit"] == 100
    assert params["novasight_viz"] == {"showLegend": True}

    extra = json.loads(payload["extra"])
    assert extra["tenant_id"] == "tenant-abc"
    assert extra["novasight"]["chart_type"] == "bar"


def test_to_superset_rejects_unknown_type():
    with pytest.raises(ValueError):
        chart_mapper.to_superset_payload(
            {"name": "x", "chart_type": "ufo", "query_config": {}},
            database_id=1,
            tenant_id="t",
        )


def test_to_superset_requires_name():
    with pytest.raises(ValueError):
        chart_mapper.to_superset_payload(
            {"chart_type": "bar"}, database_id=1, tenant_id="t"
        )


def test_filters_round_trip():
    nova = {
        "name": "x",
        "chart_type": "table",
        "query_config": {
            "dimensions": ["region"],
            "measures": ["revenue"],
            "filters": [
                {"field": "region", "operator": "in", "values": ["NA", "EU"]},
                {"field": "revenue", "operator": "gt", "value": 100},
            ],
        },
        "viz_config": {},
    }
    payload = chart_mapper.to_superset_payload(
        nova, database_id=1, tenant_id="t"
    )

    slice_payload = {
        "id": 7,
        "slice_name": "x",
        "viz_type": payload["viz_type"],
        "datasource_id": 1,
        "params": payload["params"],
        "extra": payload["extra"],
    }
    back = chart_mapper.from_superset_payload(slice_payload)

    assert back["chart_type"] == "table"
    assert back["query_config"]["dimensions"] == ["region"]
    assert back["query_config"]["measures"] == ["revenue"]
    filters = back["query_config"]["filters"]
    by_field = {f["field"]: f for f in filters}
    assert by_field["region"]["operator"] == "in"
    assert by_field["region"]["values"] == ["NA", "EU"]
    assert by_field["revenue"]["operator"] == "gt"
    assert by_field["revenue"]["value"] == 100


def test_round_trip_for_every_supported_type():
    for chart_type in SUPPORTED_TYPES:
        nova = {
            "name": f"chart-{chart_type}",
            "chart_type": chart_type,
            "source_type": "semantic_model",
            "semantic_model_id": "model-1",
            "query_config": {
                "dimensions": ["d"],
                "measures": ["m"],
                "limit": 50,
            },
            "viz_config": {"animate": True},
            "tags": ["finance"],
            "is_public": False,
        }
        payload = chart_mapper.to_superset_payload(
            nova, database_id=10, tenant_id="t-1"
        )
        slice_payload = {
            "id": 1,
            "slice_name": nova["name"],
            "viz_type": payload["viz_type"],
            "datasource_id": 10,
            "params": payload["params"],
            "extra": payload["extra"],
        }
        back = chart_mapper.from_superset_payload(slice_payload)
        assert back["chart_type"] == chart_type
        assert back["query_config"]["dimensions"] == ["d"]
        assert back["query_config"]["measures"] == ["m"]
        assert back["query_config"]["limit"] == 50
        assert back["viz_config"] == {"animate": True}
        assert back["tags"] == ["finance"]


def test_from_superset_handles_missing_extra():
    raw = {
        "id": 1,
        "slice_name": "test",
        "viz_type": "table",
        "params": json.dumps({"groupby": [], "metrics": []}),
    }
    out = chart_mapper.from_superset_payload(raw)
    assert out["chart_type"] == "table"
    assert out["query_config"]["dimensions"] == []


def test_from_superset_rejects_non_dict():
    with pytest.raises(ValueError):
        chart_mapper.from_superset_payload("not a dict")  # type: ignore
