"""fix databasetype enum: add uppercase file-based values

Revision ID: a8c1d4e6f7b2
Revises: e2f3g4h5i6j7
Create Date: 2026-04-27 09:00:00.000000

The previous migration f1a3b5c7d9e2 added lowercase values
('flatfile', 'excel', 'sqlite') to the ``databasetype`` Postgres enum.
However, SQLAlchemy ``Enum(DatabaseType)`` serializes Python enum
*member names* (i.e. uppercase: 'FLATFILE', 'EXCEL', 'SQLITE'), so
inserts fail with::

    invalid input value for enum databasetype: "FLATFILE"

This migration adds the uppercase values so the existing model works
without changes. The lowercase values remain (Postgres cannot drop
enum values without recreating the type) but are unused.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "a8c1d4e6f7b2"
down_revision = "7f2a9c1b4d83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE databasetype ADD VALUE IF NOT EXISTS 'FLATFILE'")
    op.execute("ALTER TYPE databasetype ADD VALUE IF NOT EXISTS 'EXCEL'")
    op.execute("ALTER TYPE databasetype ADD VALUE IF NOT EXISTS 'SQLITE'")


def downgrade() -> None:
    # Postgres cannot remove individual enum values without recreating
    # the type. No-op downgrade.
    pass
