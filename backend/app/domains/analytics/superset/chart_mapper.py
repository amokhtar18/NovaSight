"""
NovaSight ↔ Superset chart payload mappers
===========================================

NovaSight charts are stored client-side as ``ChartConfig`` objects
(see ``frontend/src/components/charts/types.ts``). When the
``FEATURE_SUPERSET_BACKEND`` flag is on, those charts are persisted as
Superset *slices* via Superset's REST API.

The shapes are very different:

* NovaSight uses a high-level ``query_config`` (dimensions, measures,
  filters) plus a ``viz_config`` (colors, labels…).
* Superset stores ``params`` — a JSON blob whose keys depend on the
  ``viz_type``.

These two pure functions translate between the two. They are
intentionally:

* **Synchronous** and side-effect-free (easy to unit-test).
* **Lossless** for the chart types currently supported by NovaSight.
* **Forgiving** for unknown fields (preserved under ``extra``) so that
  upgrades on either side do not silently drop data.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Chart type mapping
# ---------------------------------------------------------------------------

#: NovaSight chart type → Superset ``viz_type``.
_TO_SUPERSET_VIZ: Dict[str, str] = {
    "bar": "echarts_timeseries_bar",
    "line": "echarts_timeseries_line",
    "area": "echarts_area",
    "pie": "pie",
    "donut": "pie",
    "scatter": "echarts_timeseries_scatter",
    "table": "table",
    "metric": "big_number_total",
    "heatmap": "heatmap",
    "gauge": "gauge_chart",
    "treemap": "treemap_v2",
    "funnel": "funnel",
}

#: Reverse mapping (Superset viz_type → NovaSight chart_type).
_FROM_SUPERSET_VIZ: Dict[str, str] = {
    "echarts_timeseries_bar": "bar",
    "dist_bar": "bar",
    "bar": "bar",
    "echarts_timeseries_line": "line",
    "line": "line",
    "echarts_area": "area",
    "area": "area",
    "pie": "pie",
    "echarts_timeseries_scatter": "scatter",
    "scatter": "scatter",
    "table": "table",
    "big_number_total": "metric",
    "big_number": "metric",
    "heatmap": "heatmap",
    "gauge_chart": "gauge",
    "treemap_v2": "treemap",
    "treemap": "treemap",
    "funnel": "funnel",
}


def chart_type_to_viz(chart_type: str) -> str:
    """Translate a NovaSight chart type to a Superset ``viz_type``."""
    if not chart_type:
        raise ValueError("chart_type is required")
    if chart_type not in _TO_SUPERSET_VIZ:
        raise ValueError(f"Unsupported NovaSight chart type: {chart_type!r}")
    return _TO_SUPERSET_VIZ[chart_type]


def viz_to_chart_type(viz_type: str) -> str:
    """Translate a Superset ``viz_type`` to a NovaSight chart type."""
    if not viz_type:
        raise ValueError("viz_type is required")
    return _FROM_SUPERSET_VIZ.get(viz_type, "table")


# ---------------------------------------------------------------------------
# NovaSight → Superset
# ---------------------------------------------------------------------------


def to_superset_payload(
    nova_chart: Dict[str, Any],
    *,
    database_id: int,
    tenant_id: str,
) -> Dict[str, Any]:
    """
    Build the JSON body for ``POST /api/v1/chart/`` from a NovaSight
    chart create / update payload.

    Parameters
    ----------
    nova_chart:
        A dict matching ``ChartCreateRequest`` from
        ``frontend/src/services/chartService.ts``.
    database_id:
        The Superset ``database_id`` for the caller's tenant CH DB.
        Injected server-side; never read from the client payload.
    tenant_id:
        The NovaSight tenant id, mirrored into ``slice.extra`` so audit
        log correlation always works.
    """
    if not isinstance(nova_chart, dict):
        raise ValueError("nova_chart must be a dict")
    if "name" not in nova_chart or not nova_chart["name"]:
        raise ValueError("nova_chart.name is required")

    chart_type = nova_chart.get("chart_type") or nova_chart.get("chartType")
    viz_type = chart_type_to_viz(chart_type)

    query_config = (
        nova_chart.get("query_config")
        or nova_chart.get("queryConfig")
        or {}
    )
    viz_config = (
        nova_chart.get("viz_config") or nova_chart.get("vizConfig") or {}
    )

    params: Dict[str, Any] = {
        "viz_type": viz_type,
        "datasource": f"{database_id}__table",
        "groupby": list(query_config.get("dimensions") or []),
        "metrics": list(query_config.get("measures") or []),
        "row_limit": int(query_config.get("limit") or 10000),
        "adhoc_filters": _filters_to_adhoc(query_config.get("filters") or []),
        "order_desc": _first_order_desc(query_config.get("orderBy") or []),
        # carry NovaSight-specific viz tweaks under a namespaced key so
        # round-tripping never loses them
        "novasight_viz": viz_config,
    }

    extra = {
        "tenant_id": tenant_id,
        "source": "novasight",
        "novasight": {
            "source_type": (
                nova_chart.get("source_type")
                or nova_chart.get("sourceType")
                or "semantic_model"
            ),
            "semantic_model_id": nova_chart.get("semantic_model_id")
            or nova_chart.get("semanticModelId"),
            "sql_query": nova_chart.get("sql_query")
            or nova_chart.get("sqlQuery"),
            "tags": list(nova_chart.get("tags") or []),
            "folder_id": nova_chart.get("folder_id")
            or nova_chart.get("folderId"),
            "is_public": bool(
                nova_chart.get("is_public")
                or nova_chart.get("isPublic")
                or False
            ),
            "chart_type": chart_type,
        },
    }

    return {
        "slice_name": nova_chart["name"],
        "description": nova_chart.get("description") or "",
        "viz_type": viz_type,
        "datasource_id": database_id,
        "datasource_type": "table",
        "params": json.dumps(params, separators=(",", ":"), sort_keys=True),
        "query_context": "",
        "is_managed_externally": True,
        "external_url": None,
        "extra": json.dumps(extra, separators=(",", ":"), sort_keys=True),
    }


# ---------------------------------------------------------------------------
# Superset → NovaSight
# ---------------------------------------------------------------------------


def from_superset_payload(superset_slice: Dict[str, Any]) -> Dict[str, Any]:
    """Translate a Superset ``slice`` JSON into a NovaSight ``Chart``."""
    if not isinstance(superset_slice, dict):
        raise ValueError("superset_slice must be a dict")

    raw_params = superset_slice.get("params") or "{}"
    params = _safe_json_loads(raw_params, default={})

    raw_extra = superset_slice.get("extra") or "{}"
    extra = _safe_json_loads(raw_extra, default={})
    nova_extra = extra.get("novasight") or {}

    chart_type = nova_extra.get("chart_type") or viz_to_chart_type(
        superset_slice.get("viz_type") or params.get("viz_type") or "table"
    )

    query_config = {
        "dimensions": list(params.get("groupby") or []),
        "measures": list(params.get("metrics") or []),
        "filters": _adhoc_to_filters(params.get("adhoc_filters") or []),
        "orderBy": [],
        "limit": int(params.get("row_limit") or 10000),
    }

    viz_config = params.get("novasight_viz") or {}

    return {
        "id": str(superset_slice.get("id") or ""),
        "name": superset_slice.get("slice_name") or "",
        "description": superset_slice.get("description") or "",
        "chart_type": chart_type,
        "source_type": nova_extra.get("source_type") or "semantic_model",
        "semantic_model_id": nova_extra.get("semantic_model_id"),
        "sql_query": nova_extra.get("sql_query"),
        "query_config": query_config,
        "viz_config": viz_config,
        "folder_id": nova_extra.get("folder_id"),
        "tags": list(nova_extra.get("tags") or []),
        "is_public": bool(nova_extra.get("is_public") or False),
        "tenant_id": extra.get("tenant_id"),
        "created_by": (superset_slice.get("created_by") or {}).get(
            "username"
        ),
        "created_at": superset_slice.get("created_on"),
        "updated_at": superset_slice.get("changed_on"),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_OP_MAP = {
    "eq": "==",
    "ne": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "in": "IN",
    "not_in": "NOT IN",
    "like": "LIKE",
    "between": "BETWEEN",
}
_OP_REVERSE = {v: k for k, v in _OP_MAP.items()}


def _filters_to_adhoc(
    filters: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for f in filters or []:
        if not isinstance(f, dict) or "field" not in f:
            continue
        op = _OP_MAP.get(f.get("operator", "eq"), "==")
        value = f.get("value")
        if value is None and "values" in f:
            value = f.get("values")
        out.append(
            {
                "expressionType": "SIMPLE",
                "subject": f["field"],
                "operator": op,
                "comparator": value,
                "clause": "WHERE",
            }
        )
    return out


def _adhoc_to_filters(
    adhoc: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for a in adhoc or []:
        if not isinstance(a, dict):
            continue
        op = _OP_REVERSE.get(a.get("operator") or "==", "eq")
        entry: Dict[str, Any] = {
            "field": a.get("subject") or a.get("column") or "",
            "operator": op,
        }
        comparator = a.get("comparator")
        if isinstance(comparator, list):
            entry["values"] = comparator
        else:
            entry["value"] = comparator
        out.append(entry)
    return out


def _first_order_desc(order_by: List[Dict[str, Any]]) -> bool:
    if not order_by:
        return False
    first = order_by[0]
    if not isinstance(first, dict):
        return False
    return (first.get("direction") or "asc").lower() == "desc"


def _safe_json_loads(value: Any, *, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


__all__ = [
    "chart_type_to_viz",
    "viz_to_chart_type",
    "to_superset_payload",
    "from_superset_payload",
]
