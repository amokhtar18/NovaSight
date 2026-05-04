"""
NovaSight Orchestration Domain — Asset Factory
================================================

Dynamically generates Dagster assets from pipeline configurations.

Post Spark→dlt migration the orchestrator schedules **only dlt and dbt
jobs**. Any other ``TaskType`` is rejected by the factory and surfaces a
warning rather than producing a broken asset.

Canonical location: ``app.domains.orchestration.infrastructure.asset_factory``
"""

from pathlib import Path
from typing import Callable, Dict, List
import logging
import re

from dagster import (
    asset,
    AssetKey,
    AssetExecutionContext,
    Failure,
    MaterializeResult,
    MetadataValue,
    AssetsDefinition,
)

logger = logging.getLogger(__name__)


# Task types the orchestrator is allowed to schedule.
# Keep in sync with ``TaskType`` enum in
# ``app.domains.orchestration.domain.models``.
ALLOWED_TASK_TYPES = frozenset({
    "dlt_run",
    "dbt_run",
    "dbt_test",
    "dbt_run_lake",
    "dbt_run_warehouse",
})


class AssetFactory:
    """
    Dynamically builds Dagster assets from DagConfig models.

    Only ``dlt_*`` and ``dbt_*`` task types are supported. This is enforced
    at build time so legacy task definitions (spark/sql/python/bash/email)
    cannot accidentally be deployed.
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def build_assets_from_dag_config(self, dag_config) -> List[AssetsDefinition]:
        """
        Build Dagster assets from a DagConfig model.

        Each TaskConfig becomes an asset with proper dependencies.
        Tasks whose ``task_type`` is not in ``ALLOWED_TASK_TYPES`` are
        skipped and logged as warnings.
        """
        from app.domains.orchestration.domain.models import TaskType

        builders: Dict[str, Callable] = {
            TaskType.DLT_RUN.value: self._build_dlt_asset,
            TaskType.DBT_RUN.value: self._build_dbt_asset,
            TaskType.DBT_TEST.value: self._build_dbt_test_asset,
            TaskType.DBT_RUN_LAKE.value: self._build_dbt_lake_asset,
            TaskType.DBT_RUN_WAREHOUSE.value: self._build_dbt_warehouse_asset,
        }

        assets: List[AssetsDefinition] = []
        local_task_ids = {task.task_id for task in (dag_config.tasks or [])}
        # Group name must satisfy Dagster's regex ^[A-Za-z0-9_]+$, so we
        # use the already-sanitized ``full_dag_id`` instead of mixing in
        # the tenant UUID directly (which contains hyphens).
        group_name = f"tenant_{self._resolve_full_dag_id(dag_config)}"

        for task in dag_config.tasks:
            task_type_key = (
                task.task_type.value
                if hasattr(task.task_type, "value")
                else str(task.task_type)
            )

            if task_type_key not in ALLOWED_TASK_TYPES:
                logger.warning(
                    "Skipping task %s: task_type=%s is not allowed. "
                    "Orchestrator schedules only dlt and dbt jobs.",
                    task.task_id,
                    task_type_key,
                )
                continue

            builder = builders.get(task_type_key)
            if builder is None:
                logger.warning("No builder registered for task type: %s", task_type_key)
                continue

            asset_def = builder(task, dag_config, group_name, local_task_ids)
            if asset_def:
                assets.append(asset_def)

        return assets

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_fragment(value: str) -> str:
        """Sanitize a name fragment so it can be used in an AssetKey path."""
        return re.sub(r"[^A-Za-z0-9_]", "_", (value or "")).strip("_")

    def _resolve_full_dag_id(self, dag_config, dag_id: str = None) -> str:
        """Resolve a sanitized full_dag_id for current tenant + dag_id."""
        if dag_id is None:
            full_dag_id = getattr(dag_config, "full_dag_id", None)
            if isinstance(full_dag_id, str) and full_dag_id.strip():
                return re.sub(r"[^A-Za-z0-9_]", "_", full_dag_id.strip())
            dag_id = getattr(dag_config, "dag_id", "dag")

        if not isinstance(dag_id, str):
            dag_id = str(dag_id or "dag")

        tenant_slug = ""
        try:
            tenant_slug = getattr(dag_config.tenant, "slug", "")
        except Exception:
            tenant_slug = ""

        if not tenant_slug:
            tenant_slug = str(self.tenant_id)

        raw = f"{tenant_slug}_{dag_id}"
        return re.sub(r"[^A-Za-z0-9_]", "_", raw)

    def _asset_key_for_task(self, dag_config, task_id: str, dag_id: str = None) -> AssetKey:
        """Build a globally unique AssetKey for a task in a DAG."""
        return AssetKey([self._resolve_full_dag_id(dag_config, dag_id), task_id])

    def _asset_key_prefix(self, dag_config) -> List[str]:
        """Return the key prefix used by @asset declarations in this DAG."""
        return [self._resolve_full_dag_id(dag_config)]

    def _dependency_to_asset_key(self, dep: str, dag_config, local_task_ids) -> AssetKey:
        """Parse local or external dependency strings into Dagster AssetKeys."""
        dependency = (dep or "").strip()
        if not dependency:
            return None

        if dependency.startswith("job:"):
            # Encoded cross-job dependency: job:<dag_id>:<task_id>
            parts = dependency.split(":", 2)
            if len(parts) == 3 and parts[1] and parts[2]:
                return self._asset_key_for_task(
                    dag_config,
                    task_id=parts[2],
                    dag_id=parts[1],
                )

        if dependency.startswith("asset:"):
            # Direct asset path override. Supports both '/' and '.' separators.
            raw_path = dependency[len("asset:"):].strip()
            if raw_path:
                path = [p for p in re.split(r"[/.]", raw_path) if p]
                if path:
                    return AssetKey(path)

        if dependency in local_task_ids:
            return self._asset_key_for_task(dag_config, task_id=dependency)

        # Backward-compatible fallback: treat unknown plain refs as local task ids.
        return self._asset_key_for_task(dag_config, task_id=dependency)

    def _get_asset_deps(self, task, dag_config, local_task_ids) -> List[AssetKey]:
        """Convert task dependencies to local or cross-job AssetKeys."""
        deps: List[AssetKey] = []
        for dep in (task.depends_on or []):
            dep_key = self._dependency_to_asset_key(dep, dag_config, local_task_ids)
            if dep_key:
                deps.append(dep_key)
        return deps

    @staticmethod
    def _read_dbt_log_tail(invocation, max_chars: int = 2000) -> str:
        """Best-effort tail of the dbt.log file produced by a DbtCliInvocation.

        ``DbtCliInvocation`` in current ``dagster-dbt`` versions does not
        expose ``get_stdout``/``get_stderr``. The CLI writes a structured log
        to ``<target_path>/dbt.log``; we read its tail for error reporting.
        """
        try:
            target_path = getattr(invocation, "target_path", None)
            if target_path is None:
                return ""
            log_path = Path(str(target_path)) / "dbt.log"
            if not log_path.exists():
                return ""
            data = log_path.read_text(encoding="utf-8", errors="replace")
            return data[-max_chars:]
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # dlt
    # ------------------------------------------------------------------

    def _build_dlt_asset(self, task, dag_config, group_name: str, local_task_ids) -> AssetsDefinition:
        """Build a dlt pipeline run asset."""
        config = task.config or {}
        pipeline_id = config.get("pipeline_id")
        task_id = task.task_id
        tenant_id = self.tenant_id
        dag_id = dag_config.dag_id
        deps = self._get_asset_deps(task, dag_config, local_task_ids)
        key_prefix = self._asset_key_prefix(dag_config)

        @asset(
            name=task_id,
            key_prefix=key_prefix,
            group_name=group_name,
            compute_kind="dlt",
            deps=deps,
            metadata={
                "tenant_id": tenant_id,
                "dag_id": dag_id,
                "pipeline_id": str(pipeline_id) if pipeline_id else "",
            },
            op_tags={
                "dagster/concurrency_key": "dlt_runs",
                "tenant_id": tenant_id,
            },
        )
        def _dlt_asset(context: AssetExecutionContext) -> MaterializeResult:
            from app.domains.ingestion.application.dlt_pipeline_service import (
                DltPipelineService,
            )

            context.log.info("Running dlt pipeline %s", pipeline_id)

            if not pipeline_id:
                raise ValueError(
                    f"Task {task_id} has no pipeline_id configured"
                )

            # Execute via DltPipelineService inside a Flask app context
            # so SQLAlchemy session lookup works. Dagster's run worker
            # is a separate process with no ambient app context.
            from flask import has_app_context, current_app

            service = DltPipelineService()
            if has_app_context():
                result = service.run_now(pipeline_id, tenant_id)
            else:
                from app import create_app
                app = create_app()
                with app.app_context():
                    result = service.run_now(pipeline_id, tenant_id)

            run_status = result.get("status", "unknown")

            if run_status != "success":
                stderr_tail = result.get("stderr_tail") or ""
                # Surface the most relevant ERROR/Exception line in the
                # description so it isn't drowned out by INFO log preamble
                # (Dagster's Failure description is space-constrained).
                error_line = ""
                for line in reversed(stderr_tail.splitlines()):
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if (
                        " ERROR " in stripped
                        or "Error:" in stripped
                        or "Exception" in stripped
                        or "Traceback" in stripped
                        or "failed:" in stripped.lower()
                    ):
                        error_line = stripped
                        break
                description = (error_line or stderr_tail or run_status)[-1500:]
                raise Failure(
                    description=description,
                    metadata={
                        "pipeline_id": MetadataValue.text(str(pipeline_id)),
                        "status": MetadataValue.text(run_status),
                        "exit_code": MetadataValue.text(
                            str(result.get("exit_code", ""))
                        ),
                        # Full stderr tail (up to ~4 KB) — not truncated to
                        # 500 chars like the description, so the operator can
                        # always see the underlying cause in the run page.
                        "stderr_tail": MetadataValue.md(
                            f"```\n{stderr_tail[-3500:]}\n```"
                            if stderr_tail
                            else "_(empty)_"
                        ),
                    },
                )

            return MaterializeResult(
                metadata={
                    "pipeline_id": MetadataValue.text(str(pipeline_id)),
                    "run_status": MetadataValue.text("success"),
                    "rows": MetadataValue.int(int(result.get("rows") or 0)),
                    "duration_ms": MetadataValue.int(
                        int(result.get("duration_ms") or 0)
                    ),
                    "iceberg_snapshot_id": MetadataValue.text(
                        result.get("iceberg_snapshot_id") or ""
                    ),
                    "script_path": MetadataValue.text(
                        result.get("script_path") or ""
                    ),
                }
            )

        return _dlt_asset

    # ------------------------------------------------------------------
    # dbt
    # ------------------------------------------------------------------

    def _build_dbt_asset(self, task, dag_config, group_name: str, local_task_ids) -> AssetsDefinition:
        """Build a dbt run asset (default profile)."""
        return self._build_dbt_run(
            task,
            dag_config,
            group_name,
            profile=None,
            local_task_ids=local_task_ids,
        )

    def _build_dbt_lake_asset(self, task, dag_config, group_name: str, local_task_ids) -> AssetsDefinition:
        """Build a dbt run asset against the DuckDB / lake profile."""
        return self._build_dbt_run(
            task,
            dag_config,
            group_name,
            profile="lake",
            local_task_ids=local_task_ids,
        )

    def _build_dbt_warehouse_asset(self, task, dag_config, group_name: str, local_task_ids) -> AssetsDefinition:
        """Build a dbt run asset against the ClickHouse / warehouse profile."""
        return self._build_dbt_run(
            task,
            dag_config,
            group_name,
            profile="warehouse",
            local_task_ids=local_task_ids,
        )

    def _build_dbt_run(self, task, dag_config, group_name: str, profile, local_task_ids):
        config = task.config or {}
        models = config.get("models", [])
        tags = config.get("tags", [])
        full_refresh = config.get("full_refresh", False)
        task_id = task.task_id
        tenant_id = self.tenant_id
        dag_id = dag_config.dag_id
        deps = self._get_asset_deps(task, dag_config, local_task_ids)
        key_prefix = self._asset_key_prefix(dag_config)

        # Capture tenant slug at build time so the dbt CLI invocation can
        # populate the project-level ``tenant_id`` var. The shared
        # top-level dbt project (``/app/dbt``) derives ``tenant_database``
        # from this var to route models into ``tenant_<slug>``.
        # ClickHouse database identifiers don't permit hyphens, so the
        # tenant slug is normalised to underscores for the dbt var
        # (matching the convention used elsewhere in NovaSight).
        try:
            raw_slug = dag_config.tenant.slug
        except Exception:
            raw_slug = ""
        tenant_slug = (raw_slug or "").replace("-", "_")

        if tags:
            select_arg = " ".join([f"tag:{t}" for t in tags])
        elif models:
            select_arg = " ".join(models)
        else:
            select_arg = "*"

        @asset(
            name=task_id,
            key_prefix=key_prefix,
            group_name=group_name,
            compute_kind="dbt",
            deps=deps,
            required_resource_keys={"dbt"},
            metadata={
                "tenant_id": tenant_id,
                "tenant_slug": tenant_slug,
                "dag_id": dag_id,
                "dbt_select": select_arg,
                "dbt_profile": profile or "default",
            },
            op_tags={
                "dagster/concurrency_key": "dbt_runs",
                "tenant_id": tenant_id,
            },
        )
        def _dbt_asset(context: AssetExecutionContext) -> MaterializeResult:
            context.log.info(
                "Running dbt models: %s (profile=%s)", select_arg, profile or "default"
            )
            dbt = context.resources.dbt
            cmd = ["run", "--select", select_arg]
            if profile:
                cmd.extend(["--target", profile])
            if full_refresh:
                cmd.append("--full-refresh")
            if tenant_slug:
                # Pass the tenant slug as a dbt var so the shared project's
                # ``tenant_database`` var (``tenant_{tenant_id}``) resolves
                # to the correct per-tenant ClickHouse database.
                cmd.extend(["--vars", '{"tenant_id": "' + tenant_slug + '"}'])
            # Note: don't pass context=context. dagster_dbt's context-aware
            # path expects assets generated by @dbt_assets (with manifest
            # metadata). NovaSight builds dbt ops dynamically as plain @asset,
            # so we invoke the CLI directly and surface failures explicitly.
            invocation = dbt.cli(cmd, raise_on_error=False)
            invocation.wait()
            if not invocation.is_successful():
                log_tail = self._read_dbt_log_tail(invocation)
                if log_tail:
                    context.log.error("dbt log tail:\n%s", log_tail)
                raise Exception(
                    f"dbt {' '.join(cmd)} exited with code {invocation.process.returncode}"
                )

            return MaterializeResult(
                metadata={
                    "dbt_select": MetadataValue.text(select_arg),
                    "full_refresh": MetadataValue.bool(full_refresh),
                    "dbt_profile": MetadataValue.text(profile or "default"),
                    "tenant_slug": MetadataValue.text(tenant_slug),
                }
            )

        return _dbt_asset

    def _build_dbt_test_asset(self, task, dag_config, group_name: str, local_task_ids) -> AssetsDefinition:
        """Build a dbt test asset."""
        config = task.config or {}
        select_arg = config.get("select", "*")
        task_id = task.task_id
        tenant_id = self.tenant_id
        dag_id = dag_config.dag_id
        deps = self._get_asset_deps(task, dag_config, local_task_ids)
        key_prefix = self._asset_key_prefix(dag_config)

        @asset(
            name=task_id,
            key_prefix=key_prefix,
            group_name=group_name,
            compute_kind="dbt",
            deps=deps,
            required_resource_keys={"dbt"},
            metadata={
                "tenant_id": tenant_id,
                "dag_id": dag_id,
            },
            op_tags={"dagster/concurrency_key": "dbt_runs"},
        )
        def _dbt_test_asset(context: AssetExecutionContext) -> MaterializeResult:
            context.log.info("Running dbt tests: %s", select_arg)
            dbt = context.resources.dbt
            invocation = dbt.cli(["test", "--select", select_arg], raise_on_error=False)
            invocation.wait()
            if not invocation.is_successful():
                log_tail = self._read_dbt_log_tail(invocation)
                if log_tail:
                    context.log.error("dbt log tail:\n%s", log_tail)
                raise Exception(
                    f"dbt test --select {select_arg} exited with code {invocation.process.returncode}"
                )
            return MaterializeResult(metadata={"tests_passed": MetadataValue.bool(True)})

        return _dbt_test_asset
