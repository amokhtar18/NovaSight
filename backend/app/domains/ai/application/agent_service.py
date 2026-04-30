"""
Agent configuration service
============================

Read / write the per-tenant ``AgentConfig`` row used by the AI Workbench.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.domains.ai.domain import AgentConfig
from app.extensions import db

# Sensible defaults applied the first time a tenant opens the AI
# Workbench. Stored in the row on first save so they can be edited.
DEFAULT_SYSTEM_PROMPT = (
    "You are NovaSight Analyst, an AI assistant that answers business "
    "questions by querying the user's tenant ClickHouse database. You "
    "MUST use the registered MCP tools to read data — never invent "
    "numbers."
)
DEFAULT_TOOLS = {
    "superset-mcp": True,
    "dbt-mcp": True,
    "sql-runner": True,
}
DEFAULT_SAMPLING = {
    "temperature": 0.2,
    "top_p": 0.9,
    "num_ctx": 8192,
}


class AgentConfigService:
    """Application service for the per-tenant agent config."""

    @staticmethod
    def get_or_create(tenant_id: str) -> AgentConfig:
        config = (
            db.session.query(AgentConfig)
            .filter_by(tenant_id=tenant_id)
            .one_or_none()
        )
        if config is not None:
            return config

        config = AgentConfig(
            tenant_id=tenant_id,
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            enabled_tools=dict(DEFAULT_TOOLS),
            sampling=dict(DEFAULT_SAMPLING),
        )
        db.session.add(config)
        db.session.commit()
        return config

    @staticmethod
    def update(tenant_id: str, updates: Dict[str, Any]) -> AgentConfig:
        config = AgentConfigService.get_or_create(tenant_id)

        allowed = {
            "default_model",
            "embedding_model",
            "system_prompt",
            "enabled_tools",
            "sampling",
        }
        for key, value in (updates or {}).items():
            if key in allowed:
                setattr(config, key, value)

        db.session.commit()
        return config


__all__ = [
    "AgentConfigService",
    "DEFAULT_SYSTEM_PROMPT",
    "DEFAULT_TOOLS",
    "DEFAULT_SAMPLING",
]
