"""
DbtModelSchedule
================

Per-model dbt run / test / build schedule. Each row maps a saved
visual model (or any dbt model name) to a cron expression so Dagster
can run ``dbt run --select <model>``, ``dbt test --select <model>``,
or ``dbt build --select <model>`` against that tenant's project on
the configured schedule.

Layered databases are produced automatically by
``dbt/macros/generate_schema_name.sql`` (custom_schema_name → suffix).
"""

import uuid
from enum import Enum

from sqlalchemy import Boolean, Column, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin


class DbtCommand(str, Enum):
    """Valid dbt commands for a per-model schedule."""

    RUN = "run"
    TEST = "test"
    BUILD = "build"


VALID_COMMANDS = {c.value for c in DbtCommand}


class DbtModelSchedule(TenantMixin, TimestampMixin, db.Model):
    """
    Persistent definition of a recurring dbt invocation against a
    specific model.

    The cron is executed by Dagster (see
    ``orchestration/schedules/dbt_schedules.py::load_all_dbt_model_schedules``).
    """

    __tablename__ = "dbt_model_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(String(100), nullable=False, index=True)
    command = Column(String(20), nullable=False, default=DbtCommand.RUN.value)
    cron = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    description = Column(Text, nullable=True, default="")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "model_name",
            "command",
            name="uq_dbt_model_schedule_tenant_model_command",
        ),
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "model_name": self.model_name,
            "command": self.command,
            "cron": self.cron,
            "is_active": self.is_active,
            "description": self.description or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
