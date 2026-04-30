"""add ai_agent_configs and ai_mcp_servers tables

Revision ID: f5d8a1c20b3e
Revises: e2f4a6b8c9d0
Create Date: 2026-04-30 12:55:00.000000

Adds the two tables backing the AI Workbench (`/app/query`):

    * ai_agent_configs — per-tenant agent configuration (system prompt,
      default Ollama model, enabled tools, sampling parameters).
    * ai_mcp_servers   — per-tenant registry of MCP servers the agent
      is allowed to call.

Both tables are NEW; no existing table is altered.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f5d8a1c20b3e"
down_revision: Union[str, None] = "e2f4a6b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_agent_configs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("default_model", sa.String(length=255), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column(
            "enabled_tools",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "sampling",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ai_agent_configs_tenant_id",
        "ai_agent_configs",
        ["tenant_id"],
    )

    op.create_table(
        "ai_mcp_servers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("auth_header", sa.Text(), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "tools_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id", "name", name="uq_ai_mcp_servers_tenant_name"
        ),
    )
    op.create_index(
        "ix_ai_mcp_servers_tenant_id",
        "ai_mcp_servers",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ai_mcp_servers_tenant_id", table_name="ai_mcp_servers")
    op.drop_table("ai_mcp_servers")
    op.drop_index(
        "ix_ai_agent_configs_tenant_id", table_name="ai_agent_configs"
    )
    op.drop_table("ai_agent_configs")
