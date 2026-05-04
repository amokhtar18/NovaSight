"""
NovaSight Dagster Schedules — dbt Transformations
==================================================

Schedule definitions for dbt transformation runs.
Creates one schedule per active tenant that executes ``dbt build`` against
that tenant's isolated dbt project (lake → marts).

Schedules are produced dynamically from active tenants in the metadata DB.
"""

from __future__ import annotations

import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dagster import (
    DefaultScheduleStatus,
    JobDefinition,
    OpExecutionContext,
    RunRequest,
    ScheduleDefinition,
    job,
    op,
)

logger = logging.getLogger(__name__)


# Preset to cron mapping (matches dlt_schedules for consistency)
PRESET_TO_CRON: Dict[str, str] = {
    "hourly": "0 * * * *",
    "daily": "0 2 * * *",          # 02:00 UTC, after typical nightly dlt runs
    "weekly": "0 3 * * 0",
    "monthly": "0 3 1 * *",
    "every_6_hours": "0 */6 * * *",
    "every_12_hours": "0 */12 * * *",
}

# Default cron when a tenant has no override
DEFAULT_DBT_CRON = PRESET_TO_CRON["daily"]


def _make_safe_name(value: str) -> str:
    """Sanitize an identifier so it is safe for Dagster job/schedule names."""
    return (
        value.lower()
        .replace("-", "_")
        .replace(".", "_")
        .replace(" ", "_")
    )


def _resolve_dbt_cron(tenant: Any) -> str:
    """
    Resolve the cron expression for a tenant's dbt schedule.

    Looks up tenant settings (if available) for a ``dbt_schedule_cron`` or
    ``dbt_schedule_preset`` override; otherwise returns the default daily cron.
    """
    settings = getattr(tenant, "settings", None) or {}
    if isinstance(settings, dict):
        cron = settings.get("dbt_schedule_cron")
        if cron:
            return cron
        preset = settings.get("dbt_schedule_preset")
        if preset and preset in PRESET_TO_CRON:
            return PRESET_TO_CRON[preset]
    return DEFAULT_DBT_CRON


def _build_dbt_job_for_tenant(tenant_id: str, tenant_slug: str) -> JobDefinition:
    """
    Build a Dagster job that runs ``dbt build`` for a single tenant project.

    The op shells out to the dbt CLI against the per-tenant project directory
    produced by ``TenantDbtProjectManager``.
    """
    safe_slug = _make_safe_name(tenant_slug)
    job_name = f"dbt_build_{safe_slug}"
    op_name = f"dbt_build_op_{safe_slug}"

    _tenant_id = tenant_id
    _tenant_slug = tenant_slug

    @op(name=op_name)
    def _run_dbt_build(context) -> Dict[str, Any]:
        dbt_root = Path(os.environ.get("DBT_PROJECT_DIR", "/app/dbt"))
        project_dir = dbt_root / "tenants" / _make_safe_name(_tenant_slug)
        profiles_dir = Path(os.environ.get("DBT_PROFILES_DIR", str(dbt_root)))

        # Fall back to the shared project if the tenant project has not been
        # scaffolded yet (avoids hard-failing scheduled runs during onboarding).
        if not project_dir.exists():
            context.log.warning(
                f"Tenant dbt project not found at {project_dir}; "
                f"using shared project at {dbt_root}"
            )
            project_dir = dbt_root

        cmd = [
            "dbt",
            "build",
            "--project-dir", str(project_dir),
            "--profiles-dir", str(profiles_dir),
            "--target", os.environ.get("DBT_TARGET", "prod"),
        ]
        context.log.info(
            f"Running dbt build for tenant={_tenant_slug} cmd={' '.join(cmd)}"
        )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        context.log.info(result.stdout or "")
        if result.stderr:
            context.log.warning(result.stderr)

        if result.returncode != 0:
            raise RuntimeError(
                f"dbt build failed for tenant {_tenant_slug} "
                f"(exit={result.returncode})"
            )

        return {
            "tenant_id": _tenant_id,
            "tenant_slug": _tenant_slug,
            "exit_code": result.returncode,
            "ran_at": datetime.utcnow().isoformat(),
        }

    @job(
        name=job_name,
        tags={
            "tenant_id": tenant_id,
            "tenant_slug": tenant_slug,
            "schedule_type": "dbt_transformation",
        },
        description=f"Scheduled dbt build for tenant {tenant_slug}",
    )
    def _dbt_job() -> None:
        _run_dbt_build()

    return _dbt_job


def build_schedule_for_tenant(tenant: Any) -> Optional[ScheduleDefinition]:
    """
    Build a Dagster schedule that runs dbt build for the given tenant.
    """
    tenant_id = str(tenant.id)
    tenant_slug = tenant.slug
    cron = _resolve_dbt_cron(tenant)

    dbt_job = _build_dbt_job_for_tenant(tenant_id, tenant_slug)

    initial_status = (
        DefaultScheduleStatus.RUNNING
        if getattr(tenant, "is_active", True)
        else DefaultScheduleStatus.STOPPED
    )

    safe_slug = _make_safe_name(tenant_slug)
    schedule_def = ScheduleDefinition(
        name=f"dbt_build_{safe_slug}_schedule",
        cron_schedule=cron,
        job=dbt_job,
        default_status=initial_status,
        execution_timezone="UTC",
    )
    logger.info(f"Created dbt schedule for tenant {tenant_slug}: cron={cron}")
    return schedule_def


def load_all_dbt_schedules() -> List[ScheduleDefinition]:
    """
    Load dbt build schedules for all active tenants.

    Called at Dagster startup.
    """
    all_schedules: List[ScheduleDefinition] = []

    try:
        import sys
        if "/app" not in sys.path:
            sys.path.insert(0, "/app")

        from app import create_app
        from app.domains.tenants.domain.models import Tenant

        app = create_app()
        with app.app_context():
            tenants = Tenant.query.all()
            for tenant in tenants:
                try:
                    if not getattr(tenant, "is_active", True):
                        continue
                    schedule_def = build_schedule_for_tenant(tenant)
                    if schedule_def:
                        all_schedules.append(schedule_def)
                except Exception as e:
                    logger.error(
                        f"Failed to build dbt schedule for tenant "
                        f"{getattr(tenant, 'slug', '?')}: {e}"
                    )
    except Exception as e:
        logger.warning(f"Could not load dbt schedules: {e}")

    return all_schedules


def create_manual_dbt_run_request(
    tenant_id: str,
    tenant_slug: str,
    run_config: Optional[Dict[str, Any]] = None,
) -> RunRequest:
    """Create a RunRequest for an on-demand dbt build."""
    return RunRequest(
        run_key=f"manual_dbt_{tenant_id}_{datetime.utcnow().isoformat()}",
        tags={
            "tenant_id": tenant_id,
            "tenant_slug": tenant_slug,
            "trigger_type": "manual",
            "schedule_type": "dbt_transformation",
        },
        run_config=run_config or {},
    )


# ─────────────────────────────────────────────────────────────────
# Per-Model dbt schedules (run / test / build)
# ─────────────────────────────────────────────────────────────────


_VALID_MODEL_COMMANDS = {"run", "test", "build"}


def _build_dbt_op_for_model(
    tenant_id: str,
    tenant_slug: str,
    model_name: str,
    command: str,
) -> JobDefinition:
    """
    Build a Dagster job that runs ``dbt <command> --select <model>`` for
    a single tenant project + model.

    ``command`` must be one of ``run`` | ``test`` | ``build``.
    """
    if command not in _VALID_MODEL_COMMANDS:
        raise ValueError(
            f"Invalid dbt command '{command}'. "
            f"Valid: {sorted(_VALID_MODEL_COMMANDS)}"
        )

    safe_slug = _make_safe_name(tenant_slug)
    safe_model = _make_safe_name(model_name)
    job_name = f"dbt_{command}_{safe_slug}_{safe_model}"
    op_name = f"dbt_{command}_op_{safe_slug}_{safe_model}"

    _tenant_id = tenant_id
    _tenant_slug = tenant_slug
    _model_name = model_name
    _command = command

    @op(name=op_name)
    def _run_dbt_for_model(context) -> Dict[str, Any]:
        dbt_root = Path(os.environ.get("DBT_PROJECT_DIR", "/app/dbt"))
        project_dir = dbt_root / "tenants" / _make_safe_name(_tenant_slug)
        profiles_dir = Path(os.environ.get("DBT_PROFILES_DIR", str(dbt_root)))

        if not project_dir.exists():
            context.log.warning(
                f"Tenant dbt project not found at {project_dir}; "
                f"using shared project at {dbt_root}"
            )
            project_dir = dbt_root

        # Resolve the actual dbt model selector. The schedule row stores
        # whatever name the caller used (e.g. picking a visual model or a
        # schema YAML file may produce a leading-underscore name like
        # ``_admissions``). dbt only matches files of the form ``<name>.sql``,
        # so we look up the real .sql on disk and prefer that. This avoids
        # silent ``M030 NoNodesForSelectionCriteria`` runs that exit 0
        # without actually building anything.
        models_dir = project_dir / "models"
        candidates = [_model_name]
        if _model_name.startswith("_"):
            candidates.append(_model_name.lstrip("_"))
        resolved_select = _model_name
        if models_dir.exists():
            for candidate in candidates:
                matches = list(models_dir.rglob(f"{candidate}.sql"))
                if matches:
                    resolved_select = candidate
                    if candidate != _model_name:
                        context.log.warning(
                            f"Schedule model_name='{_model_name}' has no "
                            f"matching .sql file; using '{candidate}' "
                            f"(found at {matches[0]}). Update the schedule "
                            f"row to '{candidate}' to silence this warning."
                        )
                    break

        cmd = [
            "dbt",
            _command,
            "--select",
            resolved_select,
            "--project-dir",
            str(project_dir),
            "--profiles-dir",
            str(profiles_dir),
            "--target",
            os.environ.get("DBT_TARGET", "prod"),
        ]
        context.log.info(
            f"Running dbt {_command} for tenant={_tenant_slug} "
            f"model={resolved_select} cmd={' '.join(cmd)}"
        )

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout:
            context.log.info(result.stdout)
        if result.stderr:
            context.log.warning(result.stderr)

        if result.returncode != 0:
            raise RuntimeError(
                f"dbt {_command} failed for tenant {_tenant_slug} "
                f"model {resolved_select} (exit={result.returncode})"
            )

        # dbt exits 0 when the selector matches nothing — surface that as
        # an error so empty schedule runs don't appear to "succeed".
        combined_output = (result.stdout or "") + (result.stderr or "")
        if (
            "NoNodesForSelectionCriteria" in combined_output
            or "does not match any enabled nodes" in combined_output
        ):
            raise RuntimeError(
                f"dbt {_command} for tenant {_tenant_slug} matched no "
                f"nodes with --select '{resolved_select}'. Check the "
                f"DbtModelSchedule row's model_name (original value: "
                f"'{_model_name}'); it must equal a real dbt model file "
                f"stem (e.g. 'admissions' for admissions.sql), not a "
                f"schema YAML filename."
            )

        return {
            "tenant_id": _tenant_id,
            "tenant_slug": _tenant_slug,
            "model_name": resolved_select,
            "original_model_name": _model_name,
            "command": _command,
            "exit_code": result.returncode,
            "ran_at": datetime.utcnow().isoformat(),
        }

    @job(
        name=job_name,
        tags={
            "tenant_id": tenant_id,
            "tenant_slug": tenant_slug,
            "model_name": model_name,
            "dbt_command": command,
            "schedule_type": "dbt_model",
        },
        description=(
            f"Scheduled dbt {command} for model {model_name} "
            f"(tenant {tenant_slug})"
        ),
    )
    def _dbt_model_job() -> None:
        _run_dbt_for_model()

    return _dbt_model_job


def build_schedule_for_model_schedule(
    schedule_row: Any,
    tenant: Any,
) -> Optional[ScheduleDefinition]:
    """
    Build a Dagster ScheduleDefinition for a single
    ``DbtModelSchedule`` row + its owning tenant.
    """
    tenant_id = str(tenant.id)
    tenant_slug = tenant.slug
    model_name = schedule_row.model_name
    command = schedule_row.command
    cron = schedule_row.cron

    dbt_job = _build_dbt_op_for_model(
        tenant_id, tenant_slug, model_name, command,
    )

    initial_status = (
        DefaultScheduleStatus.RUNNING
        if schedule_row.is_active and getattr(tenant, "is_active", True)
        else DefaultScheduleStatus.STOPPED
    )

    safe_slug = _make_safe_name(tenant_slug)
    safe_model = _make_safe_name(model_name)
    schedule_def = ScheduleDefinition(
        name=f"dbt_{command}_{safe_slug}_{safe_model}_schedule",
        cron_schedule=cron,
        job=dbt_job,
        default_status=initial_status,
        execution_timezone="UTC",
    )
    logger.info(
        f"Created per-model dbt schedule tenant={tenant_slug} "
        f"model={model_name} command={command} cron={cron}"
    )
    return schedule_def


def load_all_dbt_model_schedules() -> List[ScheduleDefinition]:
    """
    Load per-model dbt schedules for all active tenants.

    Reads ``dbt_model_schedules`` rows where ``is_active = true`` and
    builds one ScheduleDefinition per row. Called at Dagster startup.
    """
    all_schedules: List[ScheduleDefinition] = []

    try:
        import sys
        if "/app" not in sys.path:
            sys.path.insert(0, "/app")

        from app import create_app
        from app.domains.tenants.domain.models import Tenant
        from app.domains.transformation.domain.dbt_model_schedule import (
            DbtModelSchedule,
        )

        app = create_app()
        with app.app_context():
            rows = DbtModelSchedule.query.filter(
                DbtModelSchedule.is_active.is_(True)
            ).all()

            if not rows:
                return all_schedules

            tenant_ids = {r.tenant_id for r in rows}
            tenants_by_id = {
                str(t.id): t
                for t in Tenant.query.filter(Tenant.id.in_(tenant_ids)).all()
            }

            for row in rows:
                tenant = tenants_by_id.get(str(row.tenant_id))
                if tenant is None or not getattr(tenant, "is_active", True):
                    continue
                try:
                    schedule_def = build_schedule_for_model_schedule(
                        row, tenant,
                    )
                    if schedule_def:
                        all_schedules.append(schedule_def)
                except Exception as e:
                    logger.error(
                        f"Failed to build per-model dbt schedule "
                        f"id={row.id} model={row.model_name}: {e}"
                    )
    except Exception as e:
        logger.warning(f"Could not load per-model dbt schedules: {e}")

    return all_schedules
