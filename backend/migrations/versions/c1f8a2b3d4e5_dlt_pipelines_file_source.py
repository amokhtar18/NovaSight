"""dlt_pipelines: file source kind (csv/xlsx/parquet/json)

Revision ID: c1f8a2b3d4e5
Revises: b9d2e3f4a5c6
Create Date: 2026-04-27 12:30:00.000000

Adds first-class support for ingesting flat files / Excel / Parquet / JSON into
Iceberg via the dlt pipeline builder. Files are uploaded directly to the
tenant's S3 bucket under the ``raw_uploads/`` prefix and read from there.

Schema changes:
- ``dlt_pipelines.connection_id`` becomes nullable (file-source pipelines do
  not have a database connection).
- ``dlt_pipelines.source_kind`` (NOT NULL, default 'sql') — discriminator
  between SQL connections and uploaded files.
- ``dlt_pipelines.file_format`` (nullable) — csv | tsv | xlsx | parquet | json | jsonl.
- ``dlt_pipelines.file_object_key`` (nullable) — S3 key under ``raw_uploads/``.
- ``dlt_pipelines.file_options`` (jsonb, default '{}') — sheet name, delimiter,
  encoding, header row, etc.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c1f8a2b3d4e5"
down_revision = "b9d2e3f4a5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # connection_id may be null for file-source pipelines
    op.alter_column(
        "dlt_pipelines",
        "connection_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # New columns
    op.add_column(
        "dlt_pipelines",
        sa.Column(
            "source_kind",
            sa.String(length=16),
            nullable=False,
            server_default="sql",
        ),
    )
    op.add_column(
        "dlt_pipelines",
        sa.Column("file_format", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "dlt_pipelines",
        sa.Column("file_object_key", sa.String(length=1024), nullable=True),
    )
    op.add_column(
        "dlt_pipelines",
        sa.Column(
            "file_options",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    # Helpful index for listing file-source pipelines
    op.create_index(
        "ix_dlt_pipelines_source_kind",
        "dlt_pipelines",
        ["source_kind"],
    )

    # Drop the server defaults — the application controls them going forward
    op.alter_column("dlt_pipelines", "source_kind", server_default=None)
    op.alter_column("dlt_pipelines", "file_options", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_dlt_pipelines_source_kind", table_name="dlt_pipelines")
    op.drop_column("dlt_pipelines", "file_options")
    op.drop_column("dlt_pipelines", "file_object_key")
    op.drop_column("dlt_pipelines", "file_format")
    op.drop_column("dlt_pipelines", "source_kind")

    # Restore NOT NULL on connection_id. NOTE: any existing file-source rows
    # MUST have been deleted before downgrade (no automatic data preservation).
    op.alter_column(
        "dlt_pipelines",
        "connection_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
