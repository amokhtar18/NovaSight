"""
AI Agent configuration API
===========================

Endpoints:
    GET  /api/v1/ai/agent/config   — read current tenant config
    PUT  /api/v1/ai/agent/config   — update prompt / tools / sampling
"""

from __future__ import annotations

import logging

from flask import jsonify, request
from pydantic import BaseModel, Field, ValidationError

from app.api.v1 import api_v1_bp
from app.domains.ai.application.agent_service import AgentConfigService
from app.platform.auth.decorators import (
    authenticated,
    require_permission,
    tenant_required,
)
from app.platform.auth.identity import get_current_identity

logger = logging.getLogger(__name__)


class AgentConfigUpdate(BaseModel):
    default_model: str | None = Field(default=None, max_length=255)
    embedding_model: str | None = Field(default=None, max_length=255)
    system_prompt: str | None = Field(default=None, max_length=10_000)
    enabled_tools: dict | None = None
    sampling: dict | None = None


@api_v1_bp.route("/ai/agent/config", methods=["GET"])
@authenticated
@tenant_required
@require_permission("analytics.query")
def get_agent_config():
    identity = get_current_identity()
    config = AgentConfigService.get_or_create(identity.tenant_id)
    return jsonify(config.to_dict()), 200


@api_v1_bp.route("/ai/agent/config", methods=["PUT"])
@authenticated
@tenant_required
@require_permission("analytics.query")
def update_agent_config():
    identity = get_current_identity()
    try:
        payload = AgentConfigUpdate(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return (
            jsonify({"error": "Invalid request", "details": exc.errors()}),
            400,
        )

    updates = payload.model_dump(exclude_none=True)
    config = AgentConfigService.update(identity.tenant_id, updates)
    return jsonify(config.to_dict()), 200
