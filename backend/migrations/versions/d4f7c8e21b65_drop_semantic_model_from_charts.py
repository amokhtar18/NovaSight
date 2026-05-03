"""drop_semantic_model_from_charts

Revision ID: d4f7c8e21b65
Revises: e9b7c2a14d50
Create Date: 2026-05-04 09:00:00.000000

Removes the semantic-layer concept from the chart/widget source pipeline.
After this migration, Charts and Widgets source data exclusively from
Datasets (auto-synced from materialized dbt mart models) or raw SQL.

Operations:
  * Reshape the ``chartsourcetype`` enum from
    ``('SEMANTIC_MODEL','SQL_QUERY')`` (initial) and any in-flight
    ``DATASET`` value into ``('DATASET','SQL_QUERY')``.
  * Migrate any existing ``charts`` rows still on ``SEMANTIC_MODEL`` to
    ``SQL_QUERY`` (their ``sql_query`` may be NULL; admins must repoint
    them to a Dataset).
  * Drop the ``charts.semantic_model_id`` FK column.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f7c8e21b65"
down_revision: Union[str, None] = "e9b7c2a14d50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # Drop FK + column on charts.semantic_model_id (if present).
    insp = sa.inspect(bind)
    chart_fks = {fk["name"] for fk in insp.get_foreign_keys("charts")}
    chart_cols = {col["name"] for col in insp.get_columns("charts")}
    chart_indexes = {idx["name"] for idx in insp.get_indexes("charts")}

    for fk_name in chart_fks:
        if fk_name and "semantic_model" in fk_name:
            op.drop_constraint(fk_name, "charts", type_="foreignkey")

    if "ix_charts_semantic_model_id" in chart_indexes:
        op.drop_index("ix_charts_semantic_model_id", table_name="charts")

    if "semantic_model_id" in chart_cols:
        op.drop_column("charts", "semantic_model_id")

    # Reshape chartsourcetype enum -> ('DATASET','SQL_QUERY').
    # Postgres does not support DROP VALUE on an enum, so we rebuild it.
    op.execute(
        "ALTER TABLE charts ALTER COLUMN source_type TYPE text "
        "USING source_type::text"
    )
    # Migrate any leftover semantic_model rows to sql_query (data is preserved
    # but those charts won't run until repointed at a Dataset).
    op.execute(
        "UPDATE charts SET source_type = 'SQL_QUERY' "
        "WHERE source_type IN ('SEMANTIC_MODEL', 'semantic_model')"
    )
    op.execute("DROP TYPE IF EXISTS chartsourcetype")
    op.execute(
        "CREATE TYPE chartsourcetype AS ENUM ('DATASET', 'SQL_QUERY')"
    )
    # Some legacy rows may still hold lowercase values; normalise both ways.
    op.execute(
        "UPDATE charts SET source_type = 'DATASET' "
        "WHERE source_type = 'dataset'"
    )
    op.execute(
        "UPDATE charts SET source_type = 'SQL_QUERY' "
        "WHERE source_type = 'sql_query'"
    )
    op.execute(
        "ALTER TABLE charts ALTER COLUMN source_type TYPE chartsourcetype "
        "USING source_type::chartsourcetype"
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Re-add SEMANTIC_MODEL to chartsourcetype.
    op.execute(
        "ALTER TABLE charts ALTER COLUMN source_type TYPE text "
        "USING source_type::text"
    )
    op.execute("DROP TYPE IF EXISTS chartsourcetype")
    op.execute(
        "CREATE TYPE chartsourcetype AS ENUM "
        "('SEMANTIC_MODEL', 'SQL_QUERY', 'DATASET')"
    )
    op.execute(
        "ALTER TABLE charts ALTER COLUMN source_type TYPE chartsourcetype "
        "USING source_type::chartsourcetype"
    )

    # Re-add semantic_model_id column (nullable; data is not recoverable).
    insp = sa.inspect(bind)
    chart_cols = {col["name"] for col in insp.get_columns("charts")}
    if "semantic_model_id" not in chart_cols:
        op.add_column(
            "charts",
            sa.Column(
                "semantic_model_id",
                sa.dialects.postgresql.UUID(as_uuid=True),
                sa.ForeignKey("semantic_models.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_charts_semantic_model_id", "charts", ["semantic_model_id"]
        )
