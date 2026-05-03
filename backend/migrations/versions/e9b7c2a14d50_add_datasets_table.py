"""add_datasets_table_for_charts_and_dashboards

Revision ID: e9b7c2a14d50
Revises: f5d8a1c20b3e
Create Date: 2026-05-03 09:00:00.000000

Introduces the Superset-inspired ``Dataset`` model for use by Charts
and Dashboards, plus FK columns on ``charts`` and ``widgets`` so the
new abstraction can be adopted incrementally without breaking existing
``semantic_model_id`` consumers.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e9b7c2a14d50"
down_revision: Union[str, None] = "f5d8a1c20b3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_DATASET_KIND = postgresql.ENUM(
    "physical", "virtual", name="dataset_kind", create_type=False
)
_DATASET_SOURCE = postgresql.ENUM(
    "dbt", "manual", "sql_lab", name="dataset_source", create_type=False
)
_DBT_MAT = postgresql.ENUM(
    "table",
    "view",
    "incremental",
    "materialized_view",
    name="dbt_materialization",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    _DATASET_KIND.create(bind, checkfirst=True)
    _DATASET_SOURCE.create(bind, checkfirst=True)
    _DBT_MAT.create(bind, checkfirst=True)

    op.create_table(
        "datasets",
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
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "kind",
            _DATASET_KIND,
            nullable=False,
            server_default="physical",
        ),
        sa.Column(
            "source",
            _DATASET_SOURCE,
            nullable=False,
            server_default="manual",
        ),
        sa.Column("database_name", sa.String(length=250), nullable=True),
        sa.Column("schema", sa.String(length=250), nullable=True),
        sa.Column("table_name", sa.String(length=250), nullable=True),
        sa.Column("sql", sa.Text(), nullable=True),
        sa.Column("dbt_unique_id", sa.String(length=500), nullable=True),
        sa.Column("dbt_materialization", _DBT_MAT, nullable=True),
        sa.Column("dbt_meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("main_dttm_col", sa.String(length=250), nullable=True),
        sa.Column("default_endpoint", sa.String(length=500), nullable=True),
        sa.Column("cache_timeout_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "is_managed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_featured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'::varchar[]"),
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("tenant_id", "name", name="uq_dataset_tenant_name"),
        sa.UniqueConstraint(
            "tenant_id",
            "dbt_unique_id",
            name="uq_dataset_tenant_dbt_unique_id",
        ),
    )
    op.create_index("ix_datasets_tenant_id", "datasets", ["tenant_id"])
    op.create_index("ix_datasets_kind", "datasets", ["kind"])
    op.create_index("ix_datasets_source", "datasets", ["source"])
    op.create_index("ix_datasets_database_name", "datasets", ["database_name"])
    op.create_index("ix_datasets_schema", "datasets", ["schema"])
    op.create_index("ix_datasets_table_name", "datasets", ["table_name"])
    op.create_index("ix_datasets_dbt_unique_id", "datasets", ["dbt_unique_id"])
    op.create_index("ix_datasets_is_managed", "datasets", ["is_managed"])
    op.create_index("ix_datasets_is_deleted", "datasets", ["is_deleted"])
    op.create_index("ix_datasets_owner_id", "datasets", ["owner_id"])

    op.create_table(
        "dataset_columns",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("column_name", sa.String(length=250), nullable=False),
        sa.Column("verbose_name", sa.String(length=1024), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expression", sa.Text(), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=True),
        sa.Column(
            "is_dttm",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "groupby",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "filterable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_hidden",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("python_date_format", sa.String(length=255), nullable=True),
        sa.Column(
            "column_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "dataset_id", "column_name", name="uq_dataset_column_name"
        ),
    )
    op.create_index(
        "ix_dataset_columns_dataset_id", "dataset_columns", ["dataset_id"]
    )

    op.create_table(
        "dataset_metrics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_name", sa.String(length=250), nullable=False),
        sa.Column("verbose_name", sa.String(length=1024), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("metric_type", sa.String(length=64), nullable=True),
        sa.Column("d3format", sa.String(length=128), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("warning_text", sa.Text(), nullable=True),
        sa.Column(
            "is_restricted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_hidden",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "dataset_id", "metric_name", name="uq_dataset_metric_name"
        ),
    )
    op.create_index(
        "ix_dataset_metrics_dataset_id", "dataset_metrics", ["dataset_id"]
    )

    # Add dataset_id FK columns to charts and widgets so the new abstraction
    # can be referenced without breaking the existing semantic_model_id path.
    op.add_column(
        "charts",
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_charts_dataset_id", "charts", ["dataset_id"])

    op.add_column(
        "widgets",
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_widgets_dataset_id", "widgets", ["dataset_id"])


def downgrade() -> None:
    op.drop_index("ix_widgets_dataset_id", table_name="widgets")
    op.drop_column("widgets", "dataset_id")
    op.drop_index("ix_charts_dataset_id", table_name="charts")
    op.drop_column("charts", "dataset_id")

    op.drop_index("ix_dataset_metrics_dataset_id", table_name="dataset_metrics")
    op.drop_table("dataset_metrics")

    op.drop_index("ix_dataset_columns_dataset_id", table_name="dataset_columns")
    op.drop_table("dataset_columns")

    for idx in (
        "ix_datasets_owner_id",
        "ix_datasets_is_deleted",
        "ix_datasets_is_managed",
        "ix_datasets_dbt_unique_id",
        "ix_datasets_table_name",
        "ix_datasets_schema",
        "ix_datasets_database_name",
        "ix_datasets_source",
        "ix_datasets_kind",
        "ix_datasets_tenant_id",
    ):
        op.drop_index(idx, table_name="datasets")
    op.drop_table("datasets")

    bind = op.get_bind()
    _DBT_MAT.drop(bind, checkfirst=True)
    _DATASET_SOURCE.drop(bind, checkfirst=True)
    _DATASET_KIND.drop(bind, checkfirst=True)
