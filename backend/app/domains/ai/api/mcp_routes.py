"""
AI MCP server registry API
===========================

Endpoints:
    GET    /api/v1/ai/mcp/servers              — list
    POST   /api/v1/ai/mcp/servers              — register / update
    DELETE /api/v1/ai/mcp/servers/<name>       — unregister
    GET    /api/v1/ai/mcp/servers/<name>/health
    POST   /api/v1/ai/mcp/servers/<name>/refresh
    POST   /api/v1/ai/mcp/<name>/invoke        — invoke a tool
"""

from __future__ import annotations

import logging

from flask import jsonify, request
from pydantic import BaseModel, Field, ValidationError

from app.api.v1 import api_v1_bp
from app.domains.ai.application.mcp_service import (
    MCPService,
    MCPServiceError,
)
from app.platform.auth.decorators import (
    authenticated,
    require_permission,
    tenant_required,
)
from app.platform.auth.identity import get_current_identity

logger = logging.getLogger(__name__)


class MCPServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    base_url: str = Field(..., min_length=1, max_length=500)
    auth_header: str | None = Field(default=None, max_length=2000)
    enabled: bool = True


class MCPInvokeRequest(BaseModel):
    tool: str = Field(..., min_length=1, max_length=200)
    arguments: dict = Field(default_factory=dict)


@api_v1_bp.route("/ai/mcp/servers", methods=["GET"])
@authenticated
@tenant_required
@require_permission("analytics.query")
def list_mcp_servers():
    identity = get_current_identity()
    servers = MCPService.list_servers(identity.tenant_id)
    return (
        jsonify({"servers": [s.to_dict() for s in servers]}),
        200,
    )


@api_v1_bp.route("/ai/mcp/servers", methods=["POST"])
@authenticated
@tenant_required
@require_permission("admin.infrastructure.update")
def create_mcp_server():
    identity = get_current_identity()
    try:
        payload = MCPServerCreate(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return (
            jsonify({"error": "Invalid request", "details": exc.errors()}),
            400,
        )
    try:
        server = MCPService.register_server(
            identity.tenant_id,
            name=payload.name,
            base_url=payload.base_url,
            auth_header=payload.auth_header,
            enabled=payload.enabled,
        )
    except MCPServiceError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(server.to_dict()), 201


@api_v1_bp.route("/ai/mcp/servers/<name>", methods=["DELETE"])
@authenticated
@tenant_required
@require_permission("admin.infrastructure.update")
def delete_mcp_server(name: str):
    identity = get_current_identity()
    deleted = MCPService.delete_server(identity.tenant_id, name)
    if not deleted:
        return jsonify({"error": "Server not found"}), 404
    return ("", 204)


@api_v1_bp.route("/ai/mcp/servers/<name>/health", methods=["GET"])
@authenticated
@tenant_required
@require_permission("analytics.query")
def mcp_server_health(name: str):
    identity = get_current_identity()
    try:
        return jsonify(MCPService.health(identity.tenant_id, name)), 200
    except MCPServiceError as exc:
        return jsonify({"error": str(exc)}), 404


@api_v1_bp.route("/ai/mcp/servers/<name>/refresh", methods=["POST"])
@authenticated
@tenant_required
@require_permission("admin.infrastructure.update")
def mcp_server_refresh(name: str):
    identity = get_current_identity()
    try:
        tools = MCPService.refresh_tools(identity.tenant_id, name)
    except MCPServiceError as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({"name": name, "tools": tools}), 200


@api_v1_bp.route("/ai/mcp/<name>/invoke", methods=["POST"])
@authenticated
@tenant_required
@require_permission("analytics.query")
def mcp_server_invoke(name: str):
    identity = get_current_identity()
    try:
        payload = MCPInvokeRequest(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return (
            jsonify({"error": "Invalid request", "details": exc.errors()}),
            400,
        )
    try:
        result = MCPService.invoke(
            identity.tenant_id, name, payload.tool, payload.arguments
        )
    except MCPServiceError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"result": result}), 200
