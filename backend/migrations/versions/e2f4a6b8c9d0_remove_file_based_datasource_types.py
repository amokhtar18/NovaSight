"""remove file-based datasource types

Revision ID: e2f4a6b8c9d0
Revises: d1e3f5a7b2c8
Create Date: 2026-04-27 00:00:00.000000

Phase C — Destructive cleanup of FLATFILE / EXCEL / SQLITE connection
types now that file ingestion is handled by the dlt pipeline builder
(``source_kind = 'file'``).

This migration is destructive:

1. Deletes ``dlt_pipelines`` rows whose ``connection_id`` references a
   data_connection of type FLATFILE / EXCEL / SQLITE.
2. Deletes the matching ``data_connections`` rows.
3. Recreates the ``databasetype`` Postgres enum without those values.
   Postgres does not support ``ALTER TYPE ... DROP VALUE``, so the enum
   is rebuilt by:
     - renaming the old type
     - creating a new type with the reduced value set
     - altering the column to use the new type
     - dropping the old type
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e2f4a6b8c9d0"
down_revision = "d1e3f5a7b2c8"
branch_labels = None
depends_on = None


REMOVED_VALUES = ("flatfile", "excel", "sqlite", "FLATFILE", "EXCEL", "SQLITE")
# Postgres enum values must match the names SQLAlchemy serializes
# ``db.Enum(DatabaseType)`` writes (member ``.name``, i.e. UPPERCASE),
# AND the lowercase ``.value`` form that some legacy migrations
# inserted. We keep both so existing rows survive the column rebuild.
KEEP_VALUES = (
    "postgresql", "oracle", "sqlserver", "mysql", "clickhouse",
    "POSTGRESQL", "ORACLE", "SQLSERVER", "MYSQL", "CLICKHOUSE",
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Delete dependent dlt_pipelines rows. We have to do this before
    #    deleting connections because dlt_pipelines.connection_id has a
    #    foreign key to data_connections.id.
    bind.execute(sa.text(
        """
        DELETE FROM dlt_pipelines
        WHERE connection_id IN (
            SELECT id FROM data_connections
            WHERE db_type::text IN :values
        )
        """
    ).bindparams(sa.bindparam("values", expanding=True)), {"values": list(REMOVED_VALUES)})

    # 2. Delete the data_connections themselves.
    bind.execute(sa.text(
        "DELETE FROM data_connections WHERE db_type::text IN :values"
    ).bindparams(sa.bindparam("values", expanding=True)), {"values": list(REMOVED_VALUES)})

    # 3. Rebuild the enum without FLATFILE / EXCEL / SQLITE.
    op.execute("ALTER TYPE databasetype RENAME TO databasetype_old")
    op.execute(
        "CREATE TYPE databasetype AS ENUM ("
        + ", ".join(f"'{v}'" for v in KEEP_VALUES)
        + ")"
    )
    op.execute(
        "ALTER TABLE data_connections "
        "ALTER COLUMN db_type TYPE databasetype "
        "USING db_type::text::databasetype"
    )
    op.execute("DROP TYPE databasetype_old")


def downgrade() -> None:
    # Re-add the values to the existing enum. This does NOT restore the
    # deleted rows — those are gone for good.
    op.execute("ALTER TYPE databasetype ADD VALUE IF NOT EXISTS 'flatfile'")
    op.execute("ALTER TYPE databasetype ADD VALUE IF NOT EXISTS 'excel'")
    op.execute("ALTER TYPE databasetype ADD VALUE IF NOT EXISTS 'sqlite'")
