"""
AI Ollama runtime configuration API
====================================

Endpoints:
    GET  /api/v1/ai/ollama/config           — base URL + default model
    PUT  /api/v1/ai/ollama/config           — update default / embedding model
    POST /api/v1/ai/ollama/models/pull      — pull a new Ollama model

The Ollama base URL itself is sourced from the global infrastructure
config table (already managed by ``/api/v1/admin/infrastructure``); the
per-tenant default model lives on ``AgentConfig`` so different tenants
can pin different models.
"""

from __future__ import annotations

import logging
import os

from flask import jsonify, request
from pydantic import BaseModel, Field, ValidationError

from app.api.v1 import api_v1_bp
from app.domains.ai.application.agent_service import AgentConfigService
from app.platform.async_utils import async_route
from app.platform.auth.decorators import (
    authenticated,
    require_permission,
    tenant_required,
)
from app.platform.auth.identity import get_current_identity

import httpx

logger = logging.getLogger(__name__)


class OllamaConfigUpdate(BaseModel):
    default_model: str | None = Field(default=None, max_length=255)
    embedding_model: str | None = Field(default=None, max_length=255)


class OllamaModelPullRequest(BaseModel):
    model: str = Field(..., min_length=1, max_length=255)


def _ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")


@api_v1_bp.route("/ai/ollama/config", methods=["GET"])
@authenticated
@tenant_required
@require_permission("analytics.query")
def get_ollama_config():
    identity = get_current_identity()
    config = AgentConfigService.get_or_create(identity.tenant_id)
    return (
        jsonify(
            {
                "base_url": _ollama_base_url(),
                "default_model": config.default_model,
                "embedding_model": config.embedding_model,
            }
        ),
        200,
    )


@api_v1_bp.route("/ai/ollama/config", methods=["PUT"])
@authenticated
@tenant_required
@require_permission("admin.infrastructure.update")
def update_ollama_config():
    identity = get_current_identity()
    try:
        payload = OllamaConfigUpdate(**(request.get_json(silent=True) or {}))
    except ValidationError as exc:
        return (
            jsonify({"error": "Invalid request", "details": exc.errors()}),
            400,
        )

    config = AgentConfigService.update(
        identity.tenant_id, payload.model_dump(exclude_none=True)
    )
    return (
        jsonify(
            {
                "base_url": _ollama_base_url(),
                "default_model": config.default_model,
                "embedding_model": config.embedding_model,
            }
        ),
        200,
    )


@api_v1_bp.route("/ai/ollama/models/pull", methods=["POST"])
@authenticated
@tenant_required
@require_permission("admin.infrastructure.update")
@async_route
async def pull_ollama_model():
    try:
        payload = OllamaModelPullRequest(
            **(request.get_json(silent=True) or {})
        )
    except ValidationError as exc:
        return (
            jsonify({"error": "Invalid request", "details": exc.errors()}),
            400,
        )

    client = httpx.AsyncClient(base_url=_ollama_base_url(), timeout=600.0)
    try:
        # Ollama's pull endpoint streams progress events. We swallow the
        # body and return once the connection completes.
        async with client:
            resp = await client.post(
                "/api/pull",
                json={"name": payload.model, "stream": False},
            )
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Ollama pull failed: %s", exc)
        return jsonify({"error": str(exc)}), 502
    return jsonify({"status": "ok", "model": payload.model}), 200
