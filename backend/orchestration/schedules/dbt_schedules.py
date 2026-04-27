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
    def _run_dbt_build(context: OpExecutionContext) -> Dict[str, Any]:
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
