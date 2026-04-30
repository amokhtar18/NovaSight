"""
NovaSight AI domain — domain models
====================================

Adds two SQLAlchemy models used by the AI Workbench (`/app/query`):

    * ``AgentConfig`` — per-tenant configuration of the Ollama agent
      (system prompt, default model, enabled tools, sampling defaults).
    * ``MCPServer`` — per-tenant registry of MCP servers the agent is
      allowed to call (e.g. ``superset-mcp``, ``dbt-mcp``).

Both tables are NEW; no existing model is touched. The matching
Alembic migration lives at
``backend/migrations/versions/f5d8a1c20b3e_add_ai_agent_and_mcp_tables.py``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.extensions import db


# ---------------------------------------------------------------------------
# Agent configuration (one row per tenant)
# ---------------------------------------------------------------------------


class AgentConfig(db.Model):
    """Per-tenant configuration of the NovaSight AI agent."""

    __tablename__ = "ai_agent_configs"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    default_model = db.Column(String(255), nullable=True)
    embedding_model = db.Column(String(255), nullable=True)

    system_prompt = db.Column(Text, nullable=True)

    # Free-form tool toggles, e.g. {"superset-mcp": true, "dbt-mcp": false}
    enabled_tools = db.Column(JSONB, default=dict, nullable=False)

    # Sampling / runtime parameters: temperature, top_p, num_ctx, …
    sampling = db.Column(JSONB, default=dict, nullable=False)

    created_at = db.Column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at = db.Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "default_model": self.default_model,
            "embedding_model": self.embedding_model,
            "system_prompt": self.system_prompt,
            "enabled_tools": self.enabled_tools or {},
            "sampling": self.sampling or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# MCP server registry
# ---------------------------------------------------------------------------


class MCPServerConfig(db.Model):
    """An MCP server registered for a tenant's agent to call."""

    __tablename__ = "ai_mcp_servers"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = db.Column(String(120), nullable=False)
    base_url = db.Column(String(500), nullable=False)
    auth_header = db.Column(Text, nullable=True)

    enabled = db.Column(Boolean, default=True, nullable=False)

    # Snapshot of the last `tools` listing fetched from the server.
    tools_snapshot = db.Column(JSONB, default=list, nullable=False)

    created_at = db.Column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at = db.Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    __table_args__ = (
        db.UniqueConstraint(
            "tenant_id", "name", name="uq_ai_mcp_servers_tenant_name"
        ),
    )

    def to_dict(self, *, include_secrets: bool = False) -> Dict[str, Any]:
        result = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "base_url": self.base_url,
            "enabled": self.enabled,
            "tools_snapshot": self.tools_snapshot or [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_secrets:
            result["auth_header"] = self.auth_header
        else:
            result["auth_header_set"] = bool(self.auth_header)
        return result


__all__ = ["AgentConfig", "MCPServerConfig"]
