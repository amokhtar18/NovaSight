"""
DbtModelScheduleService
=======================

CRUD + Dagster-loader helpers for per-model dbt schedules.

The service validates cron expressions, normalises commands,
and returns plain dicts/ORM rows for the API and Dagster loader.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.errors import NotFoundError, ValidationError
from app.extensions import db
from app.domains.transformation.domain.dbt_model_schedule import (
    DbtModelSchedule,
    VALID_COMMANDS,
)
from app.domains.transformation.domain.visual_models import VisualModel

logger = logging.getLogger(__name__)


# Cron presets (kept in sync with orchestration/schedules/dbt_schedules.PRESET_TO_CRON).
PRESET_TO_CRON: Dict[str, str] = {
    "hourly": "0 * * * *",
    "daily": "0 2 * * *",
    "weekly": "0 3 * * 0",
    "monthly": "0 3 1 * *",
    "every_6_hours": "0 */6 * * *",
    "every_12_hours": "0 */12 * * *",
}


def _resolve_cron(cron: Optional[str], preset: Optional[str]) -> str:
    if cron:
        cron = cron.strip()
        # Minimal validation: 5 whitespace-separated fields.
        if len(cron.split()) != 5:
            raise ValidationError(
                f"Invalid cron expression '{cron}'. Expected 5 fields."
            )
        return cron
    if preset:
        if preset not in PRESET_TO_CRON:
            raise ValidationError(
                f"Unknown cron preset '{preset}'. "
                f"Valid: {sorted(PRESET_TO_CRON)}"
            )
        return PRESET_TO_CRON[preset]
    raise ValidationError("Either 'cron' or 'preset' must be provided.")


def _normalise_command(command: Optional[str]) -> str:
    cmd = (command or "run").strip().lower()
    if cmd not in VALID_COMMANDS:
        raise ValidationError(
            f"Invalid dbt command '{cmd}'. Valid: {sorted(VALID_COMMANDS)}"
        )
    return cmd


class DbtModelScheduleService:
    """Application service for ``DbtModelSchedule``."""

    # ── CRUD ────────────────────────────────────────────────────

    def list_for_model(
        self,
        tenant_id: str,
        model_name: str,
    ) -> List[DbtModelSchedule]:
        return (
            DbtModelSchedule.for_tenant(tenant_id)
            .filter(DbtModelSchedule.model_name == model_name)
            .order_by(DbtModelSchedule.command.asc())
            .all()
        )

    def list_all_for_tenant(self, tenant_id: str) -> List[DbtModelSchedule]:
        return (
            DbtModelSchedule.for_tenant(tenant_id)
            .order_by(
                DbtModelSchedule.model_name.asc(),
                DbtModelSchedule.command.asc(),
            )
            .all()
        )

    def get(self, tenant_id: str, schedule_id: str) -> DbtModelSchedule:
        row = DbtModelSchedule.get_for_tenant(schedule_id, tenant_id)
        if row is None:
            raise NotFoundError(f"Schedule {schedule_id} not found")
        return row

    def create(
        self,
        tenant_id: str,
        model_name: str,
        payload: Dict[str, Any],
    ) -> DbtModelSchedule:
        # Validate the model exists for this tenant.
        model = VisualModel.for_tenant(tenant_id).filter(
            VisualModel.model_name == model_name,
            VisualModel.is_deleted.is_(False),
        ).first()
        if model is None:
            raise NotFoundError(
                f"Visual model '{model_name}' not found for tenant"
            )

        command = _normalise_command(payload.get("command"))
        cron = _resolve_cron(payload.get("cron"), payload.get("preset"))

        existing = (
            DbtModelSchedule.for_tenant(tenant_id)
            .filter(
                DbtModelSchedule.model_name == model_name,
                DbtModelSchedule.command == command,
            )
            .first()
        )
        if existing is not None:
            raise ValidationError(
                f"Schedule for model '{model_name}' command '{command}' "
                "already exists. Update it instead."
            )

        row = DbtModelSchedule(
            tenant_id=tenant_id,
            model_name=model_name,
            command=command,
            cron=cron,
            is_active=bool(payload.get("is_active", True)),
            description=(payload.get("description") or "").strip(),
        )
        db.session.add(row)
        db.session.commit()
        logger.info(
            "Created dbt model schedule tenant=%s model=%s command=%s cron=%s",
            tenant_id, model_name, command, cron,
        )
        return row

    def update(
        self,
        tenant_id: str,
        schedule_id: str,
        payload: Dict[str, Any],
    ) -> DbtModelSchedule:
        row = self.get(tenant_id, schedule_id)

        if "command" in payload:
            row.command = _normalise_command(payload.get("command"))
        if "cron" in payload or "preset" in payload:
            row.cron = _resolve_cron(
                payload.get("cron"), payload.get("preset"),
            )
        if "is_active" in payload:
            row.is_active = bool(payload["is_active"])
        if "description" in payload:
            row.description = (payload.get("description") or "").strip()

        db.session.commit()
        return row

    def delete(self, tenant_id: str, schedule_id: str) -> None:
        row = self.get(tenant_id, schedule_id)
        db.session.delete(row)
        db.session.commit()

    # ── Dagster loader (cross-tenant) ───────────────────────────

    def list_active_for_dagster(self) -> List[DbtModelSchedule]:
        """Return all active per-model schedules across all tenants."""
        return (
            DbtModelSchedule.query.filter(
                DbtModelSchedule.is_active.is_(True)
            )
            .all()
        )


def get_dbt_model_schedule_service() -> DbtModelScheduleService:
    return DbtModelScheduleService()
