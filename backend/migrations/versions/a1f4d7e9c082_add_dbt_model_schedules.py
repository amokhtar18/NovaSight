"""add dbt_model_schedules table

Revision ID: a1f4d7e9c082
Revises: d4f7c8e21b65
Create Date: 2026-04-01 12:00:00.000000

Adds the ``dbt_model_schedules`` table that stores per-model dbt
run / test / build schedules consumed by Dagster.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a1f4d7e9c082"
down_revision = "d4f7c8e21b65"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dbt_model_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column(
            "command",
            sa.String(length=20),
            nullable=False,
            server_default="run",
        ),
        sa.Column("cron", sa.String(length=100), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("description", sa.Text(), nullable=True, server_default=""),
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
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "model_name",
            "command",
            name="uq_dbt_model_schedule_tenant_model_command",
        ),
    )
    op.create_index(
        "ix_dbt_model_schedules_tenant_id",
        "dbt_model_schedules",
        ["tenant_id"],
    )
    op.create_index(
        "ix_dbt_model_schedules_model_name",
        "dbt_model_schedules",
        ["model_name"],
    )
    op.create_index(
        "ix_dbt_model_schedules_is_active",
        "dbt_model_schedules",
        ["is_active"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_dbt_model_schedules_is_active",
        table_name="dbt_model_schedules",
    )
    op.drop_index(
        "ix_dbt_model_schedules_model_name",
        table_name="dbt_model_schedules",
    )
    op.drop_index(
        "ix_dbt_model_schedules_tenant_id",
        table_name="dbt_model_schedules",
    )
    op.drop_table("dbt_model_schedules")
