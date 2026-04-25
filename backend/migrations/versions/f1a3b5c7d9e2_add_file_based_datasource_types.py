"""add file-based datasource types

Revision ID: f1a3b5c7d9e2
Revises: c4a2e1f38b90
Create Date: 2026-04-20 12:00:00.000000

Adds FLATFILE, EXCEL, SQLITE to the DatabaseType enum and makes
host/port/database/username/password_encrypted nullable to support
file-based data sources.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f1a3b5c7d9e2"
down_revision = "c4a2e1f38b90"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add new enum values to the databasetype PostgreSQL enum
    # PostgreSQL requires explicit ALTER TYPE to add values
    op.execute("ALTER TYPE databasetype ADD VALUE IF NOT EXISTS 'flatfile'")
    op.execute("ALTER TYPE databasetype ADD VALUE IF NOT EXISTS 'excel'")
    op.execute("ALTER TYPE databasetype ADD VALUE IF NOT EXISTS 'sqlite'")

    # 2. Make host, port, database, username, password_encrypted nullable
    op.alter_column(
        "data_connections", "host",
        existing_type=sa.String(255),
        nullable=True,
    )
    op.alter_column(
        "data_connections", "port",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "data_connections", "database",
        existing_type=sa.String(255),
        nullable=True,
    )
    op.alter_column(
        "data_connections", "username",
        existing_type=sa.String(255),
        nullable=True,
    )
    op.alter_column(
        "data_connections", "password_encrypted",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    # Restore NOT NULL constraints (data must be cleaned first)
    op.alter_column(
        "data_connections", "host",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.alter_column(
        "data_connections", "port",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "data_connections", "database",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.alter_column(
        "data_connections", "username",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.alter_column(
        "data_connections", "password_encrypted",
        existing_type=sa.Text(),
        nullable=False,
    )
    # NOTE: PostgreSQL does not support removing enum values.
    # To fully downgrade, you would need to recreate the type.
