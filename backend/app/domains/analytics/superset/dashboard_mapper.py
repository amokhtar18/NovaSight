"""
NovaSight ↔ Superset dashboard payload mappers
===============================================

NovaSight dashboards use a ``react-grid-layout`` JSON structure of the
form::

    [
        {"i": "<widget_id>", "x": 0, "y": 0, "w": 6, "h": 4},
        ...
    ]

Superset dashboards use ``position_json``, a tree of typed nodes
(``ROW``, ``COLUMN``, ``CHART``…) keyed by stable string ids. To stay
lossless and let the existing NovaSight renderer keep working, the
mapper:

* flattens to a single column of ROWs in Superset (one row per RGL
  block) so the layout always reverses cleanly,
* embeds the original NovaSight RGL JSON under
  ``DASHBOARD_VERSION_KEY`` → ``meta.novasight_rgl`` so that even if
  Superset re-orders nodes we can rebuild the original layout on read.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

DASHBOARD_VERSION_KEY = "DASHBOARD_VERSION_KEY"


# ---------------------------------------------------------------------------
# NovaSight → Superset
# ---------------------------------------------------------------------------


def to_superset_payload(
    nova_dashboard: Dict[str, Any],
    *,
    tenant_id: str,
    chart_id_map: Optional[Dict[str, int]] = None,
) -> Dict[str, Any]:
    """
    Build the JSON body for ``POST /api/v1/dashboard/`` from a NovaSight
    dashboard payload.

    ``chart_id_map`` maps the NovaSight widget id (the RGL ``i`` field
    or NovaSight chart id) to the Superset slice id, so the resulting
    ``position_json`` can reference the slice. If a widget is missing
    from the map it is rendered as a placeholder ``MARKDOWN`` node so
    the layout never silently loses a tile.
    """
    if not isinstance(nova_dashboard, dict):
        raise ValueError("nova_dashboard must be a dict")

    name = nova_dashboard.get("name") or nova_dashboard.get("title")
    if not name:
        raise ValueError("nova_dashboard.name is required")

    layout = list(nova_dashboard.get("layout") or [])
    chart_id_map = dict(chart_id_map or {})

    position_json = _layout_to_position_json(
        layout=layout,
        chart_id_map=chart_id_map,
        novasight_layout=layout,
    )

    metadata = {
        "novasight": {
            "tenant_id": tenant_id,
            "rgl_layout": layout,
            "tags": list(nova_dashboard.get("tags") or []),
            "is_public": bool(nova_dashboard.get("is_public") or False),
        }
    }

    return {
        "dashboard_title": name,
        "slug": nova_dashboard.get("slug"),
        "owners": [],
        "position_json": json.dumps(
            position_json, separators=(",", ":"), sort_keys=True
        ),
        "json_metadata": json.dumps(
            metadata, separators=(",", ":"), sort_keys=True
        ),
        "published": bool(nova_dashboard.get("published") or False),
        "is_managed_externally": True,
    }


def _layout_to_position_json(
    *,
    layout: List[Dict[str, Any]],
    chart_id_map: Dict[str, int],
    novasight_layout: List[Dict[str, Any]],
) -> Dict[str, Any]:
    grid_id = "GRID_ID"
    root_id = "ROOT_ID"

    nodes: Dict[str, Any] = {
        DASHBOARD_VERSION_KEY: "v2",
        "ROOT_ID": {
            "type": "ROOT",
            "id": "ROOT_ID",
            "children": [grid_id],
        },
        grid_id: {
            "type": "GRID",
            "id": grid_id,
            "children": [],
            "parents": [root_id],
            "meta": {"novasight_rgl": novasight_layout},
        },
    }

    for block in layout:
        if not isinstance(block, dict):
            continue
        widget_id = str(block.get("i") or block.get("id") or uuid.uuid4().hex)
        row_id = f"ROW-{widget_id}"
        nodes[grid_id]["children"].append(row_id)

        chart_id = chart_id_map.get(widget_id)
        chart_node_id = f"CHART-{widget_id}"

        if chart_id is not None:
            nodes[chart_node_id] = {
                "type": "CHART",
                "id": chart_node_id,
                "children": [],
                "parents": [root_id, grid_id, row_id],
                "meta": {
                    "chartId": int(chart_id),
                    "width": int(block.get("w") or 6),
                    "height": int(block.get("h") or 4),
                    "novasight_widget_id": widget_id,
                },
            }
        else:
            # Placeholder for widgets that have no Superset slice yet.
            nodes[chart_node_id] = {
                "type": "MARKDOWN",
                "id": chart_node_id,
                "children": [],
                "parents": [root_id, grid_id, row_id],
                "meta": {
                    "code": f"_(missing slice for {widget_id})_",
                    "width": int(block.get("w") or 6),
                    "height": int(block.get("h") or 4),
                    "novasight_widget_id": widget_id,
                },
            }

        nodes[row_id] = {
            "type": "ROW",
            "id": row_id,
            "children": [chart_node_id],
            "parents": [root_id, grid_id],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }

    return nodes


# ---------------------------------------------------------------------------
# Superset → NovaSight
# ---------------------------------------------------------------------------


def from_superset_payload(
    superset_dashboard: Dict[str, Any],
) -> Dict[str, Any]:
    """Translate a Superset ``dashboard`` JSON into a NovaSight dict."""
    if not isinstance(superset_dashboard, dict):
        raise ValueError("superset_dashboard must be a dict")

    metadata = _safe_json_loads(
        superset_dashboard.get("json_metadata") or "{}", default={}
    )
    nova_meta = metadata.get("novasight") or {}

    # Prefer the original NovaSight layout if it survived round-trip;
    # otherwise rebuild it from the position_json tree.
    layout = nova_meta.get("rgl_layout")
    if not layout:
        position = _safe_json_loads(
            superset_dashboard.get("position_json") or "{}", default={}
        )
        layout = _position_json_to_layout(position)

    return {
        "id": str(superset_dashboard.get("id") or ""),
        "name": superset_dashboard.get("dashboard_title") or "",
        "slug": superset_dashboard.get("slug"),
        "layout": layout,
        "tags": list(nova_meta.get("tags") or []),
        "is_public": bool(nova_meta.get("is_public") or False),
        "tenant_id": nova_meta.get("tenant_id"),
        "published": bool(superset_dashboard.get("published") or False),
        "created_at": superset_dashboard.get("created_on"),
        "updated_at": superset_dashboard.get("changed_on"),
    }


def _position_json_to_layout(
    position: Dict[str, Any],
) -> List[Dict[str, Any]]:
    layout: List[Dict[str, Any]] = []
    for node_id, node in position.items():
        if not isinstance(node, dict):
            continue
        if node.get("type") not in ("CHART", "MARKDOWN"):
            continue
        meta = node.get("meta") or {}
        widget_id = meta.get("novasight_widget_id") or node_id
        layout.append(
            {
                "i": str(widget_id),
                "x": 0,
                "y": len(layout) * int(meta.get("height") or 4),
                "w": int(meta.get("width") or 6),
                "h": int(meta.get("height") or 4),
                "chartId": meta.get("chartId"),
            }
        )
    return layout


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
    "DASHBOARD_VERSION_KEY",
    "to_superset_payload",
    "from_superset_payload",
]
