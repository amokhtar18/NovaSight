"""
MCP server registry service
============================

CRUD + health-check + tool invocation for a tenant's MCP servers.
Backed by the ``ai_mcp_servers`` table and the
``app.domains.analytics.superset.mcp_client.MCPClient`` HTTP client.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domains.ai.domain import MCPServerConfig
from app.domains.analytics.superset.mcp_client import MCPClient, MCPServer
from app.extensions import db


class MCPServiceError(RuntimeError):
    """Raised on logical / validation errors in this service.

    All error messages constructed here are author-controlled (no
    upstream stack-trace data is propagated), so callers can safely
    surface ``error.user_message`` to the client.
    """

    @property
    def user_message(self) -> str:
        return self.args[0] if self.args else "MCP service error"


class MCPService:
    """Application service for the per-tenant MCP server registry."""

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @staticmethod
    def list_servers(tenant_id: str) -> List[MCPServerConfig]:
        return (
            db.session.query(MCPServerConfig)
            .filter_by(tenant_id=tenant_id)
            .order_by(MCPServerConfig.name)
            .all()
        )

    @staticmethod
    def get_by_name(
        tenant_id: str, name: str
    ) -> Optional[MCPServerConfig]:
        return (
            db.session.query(MCPServerConfig)
            .filter_by(tenant_id=tenant_id, name=name)
            .one_or_none()
        )

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    @staticmethod
    def register_server(
        tenant_id: str,
        name: str,
        base_url: str,
        *,
        auth_header: Optional[str] = None,
        enabled: bool = True,
    ) -> MCPServerConfig:
        if not name or not base_url:
            raise MCPServiceError("name and base_url are required")

        existing = MCPService.get_by_name(tenant_id, name)
        if existing:
            existing.base_url = base_url
            if auth_header is not None:
                existing.auth_header = auth_header
            existing.enabled = enabled
            db.session.commit()
            return existing

        server = MCPServerConfig(
            tenant_id=tenant_id,
            name=name,
            base_url=base_url,
            auth_header=auth_header,
            enabled=enabled,
        )
        db.session.add(server)
        db.session.commit()
        return server

    @staticmethod
    def delete_server(tenant_id: str, name: str) -> bool:
        server = MCPService.get_by_name(tenant_id, name)
        if not server:
            return False
        db.session.delete(server)
        db.session.commit()
        return True

    # ------------------------------------------------------------------
    # Runtime helpers
    # ------------------------------------------------------------------

    @staticmethod
    def health(tenant_id: str, name: str) -> Dict[str, Any]:
        server = MCPService.get_by_name(tenant_id, name)
        if not server:
            raise MCPServiceError(f"MCP server {name!r} not registered")
        client = MCPClient(_to_runtime(server))
        return {"name": name, "healthy": client.health()}

    @staticmethod
    def refresh_tools(tenant_id: str, name: str) -> List[str]:
        server = MCPService.get_by_name(tenant_id, name)
        if not server:
            raise MCPServiceError(f"MCP server {name!r} not registered")
        client = MCPClient(_to_runtime(server))
        tools = client.list_tools()
        server.tools_snapshot = list(tools)
        db.session.commit()
        return tools

    @staticmethod
    def invoke(
        tenant_id: str, name: str, tool: str, args: Dict[str, Any]
    ) -> Dict[str, Any]:
        server = MCPService.get_by_name(tenant_id, name)
        if not server:
            raise MCPServiceError(f"MCP server {name!r} not registered")
        if not server.enabled:
            raise MCPServiceError(f"MCP server {name!r} is disabled")
        client = MCPClient(_to_runtime(server))
        return client.invoke(tool, args)


def _to_runtime(server: MCPServerConfig) -> MCPServer:
    return MCPServer(
        name=server.name,
        base_url=server.base_url,
        auth_header=server.auth_header,
        enabled=server.enabled,
        tools=list(server.tools_snapshot or []),
    )


__all__ = ["MCPService", "MCPServiceError"]
