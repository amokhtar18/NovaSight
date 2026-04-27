"""Restrict tasktype enum to dlt + dbt only.

Adds the new dlt/dbt task type values used by the post-Spark migration
orchestrator. Legacy values (spark_submit, sql_query, email, http_sensor,
time_sensor, python_operator, bash_operator) remain in the Postgres enum
because PostgreSQL does not support removing enum values without dropping
the type, and existing rows may still reference them. Application-level
validation now rejects them — see
``app.domains.orchestration.domain.models.TaskType``.

Revision ID: 7f2a9c1b4d83
Revises: e2f3g4h5i6j7
Create Date: 2026-04-27
"""

from typing import Sequence, Union

from alembic import op


revision: str = "7f2a9c1b4d83"
down_revision: Union[str, None] = "e2f3g4h5i6j7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Values added by this migration. SQLAlchemy stores enum *names* (upper case)
# in the Postgres enum by default, matching the existing values
# 'SPARK_SUBMIT', 'DBT_RUN', etc.
NEW_VALUES = ("DLT_RUN", "DBT_RUN_LAKE", "DBT_RUN_WAREHOUSE")


def upgrade() -> None:
    # ``ALTER TYPE ... ADD VALUE`` cannot run inside a transaction block.
    connection = op.get_bind()
    for value in NEW_VALUES:
        connection.exec_driver_sql(
            f"ALTER TYPE tasktype ADD VALUE IF NOT EXISTS '{value}'"
        )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values. Downgrade is a no-op;
    # rows referencing the new values would need to be migrated first.
    pass
