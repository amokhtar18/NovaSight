"""
NovaSight ↔ superset-mcp client
================================

Thin HTTP client that lets the AI Workbench (`/app/query`) invoke tools
exposed by the `Aptro/superset-mcp <https://github.com/aptro/superset-mcp>`_
server. The MCP server in turn calls Superset's REST API to fetch /
manipulate datasets, charts, dashboards, and SQL Lab queries.

This module is intentionally minimal — full MCP protocol handling is
delegated to the ``mcp`` Python SDK (installed via
``requirements-superset.txt``). When that SDK is not available we fall
back to a plain JSON-RPC over HTTP shim so unit tests can run.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Server registry (configured from the AI Workbench UI / DB table)
# ---------------------------------------------------------------------------


@dataclass
class MCPServer:
    """Runtime view of a registered MCP server."""

    name: str
    base_url: str
    auth_header: Optional[str] = None
    enabled: bool = True
    tools: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class MCPClient:
    """
    Tiny client that calls a single MCP server.

    Two operations are exposed because that is everything the AI
    Workbench needs:

        * ``health()`` — returns ``True`` if the server responds to a
          ``ping`` (or ``/health``) within ``timeout`` seconds.
        * ``invoke(tool, args)`` — calls a single tool synchronously
          and returns the JSON result.
    """

    def __init__(
        self,
        server: MCPServer,
        *,
        timeout: float = 10.0,
    ) -> None:
        self.server = server
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health(self) -> bool:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    f"{self.server.base_url.rstrip('/')}/health",
                    headers=self._auth_headers(),
                )
            return 200 <= resp.status_code < 300
        except httpx.HTTPError as exc:
            logger.debug(
                "MCP health check failed for %s: %s", self.server.name, exc
            )
            return False

    # ------------------------------------------------------------------
    # Tool invocation
    # ------------------------------------------------------------------

    def list_tools(self) -> List[str]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    f"{self.server.base_url.rstrip('/')}/tools",
                    headers=self._auth_headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, dict) and "tools" in data:
                    return [t["name"] for t in data["tools"]]
                if isinstance(data, list):
                    return list(data)
        except httpx.HTTPError as exc:
            logger.warning(
                "MCP list_tools failed for %s: %s", self.server.name, exc
            )
        return []

    def invoke(self, tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
        if not self.server.enabled:
            raise RuntimeError(
                f"MCP server {self.server.name!r} is disabled"
            )

        url = f"{self.server.base_url.rstrip('/')}/tools/{tool}/invoke"
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                url, headers=self._auth_headers(), json={"arguments": args}
            )
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _auth_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.server.auth_header:
            headers["Authorization"] = self.server.auth_header
        return headers


# ---------------------------------------------------------------------------
# Default Superset MCP from environment (used as a fallback when nothing has
# been registered through the AI Workbench yet).
# ---------------------------------------------------------------------------


def default_superset_mcp() -> Optional[MCPServer]:
    base_url = os.getenv("SUPERSET_MCP_URL")
    if not base_url:
        return None
    auth = os.getenv("SUPERSET_MCP_AUTH_HEADER")
    return MCPServer(
        name="superset-mcp",
        base_url=base_url,
        auth_header=auth,
        enabled=True,
    )


__all__ = ["MCPServer", "MCPClient", "default_superset_mcp"]
