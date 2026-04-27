"""
NovaSight Orchestration Domain — Asset Factory
================================================

Dynamically generates Dagster assets from pipeline configurations.

Post Spark→dlt migration the orchestrator schedules **only dlt and dbt
jobs**. Any other ``TaskType`` is rejected by the factory and surfaces a
warning rather than producing a broken asset.

Canonical location: ``app.domains.orchestration.infrastructure.asset_factory``
"""

from typing import Callable, Dict, List
import logging

from dagster import (
    asset,
    AssetKey,
    AssetExecutionContext,
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
        # Group name must satisfy Dagster's regex ^[A-Za-z0-9_]+$, so we
        # use the already-sanitized ``full_dag_id`` instead of mixing in
        # the tenant UUID directly (which contains hyphens).
        group_name = f"tenant_{dag_config.full_dag_id}"

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

            asset_def = builder(task, dag_config, group_name)
            if asset_def:
                assets.append(asset_def)

        return assets

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_asset_deps(self, task) -> List[AssetKey]:
        """Convert task dependencies to AssetKeys."""
        return [AssetKey(dep) for dep in (task.depends_on or [])]

    # ------------------------------------------------------------------
    # dlt
    # ------------------------------------------------------------------

    def _build_dlt_asset(self, task, dag_config, group_name: str) -> AssetsDefinition:
        """Build a dlt pipeline run asset."""
        config = task.config or {}
        pipeline_id = config.get("pipeline_id")
        task_id = task.task_id
        tenant_id = self.tenant_id
        dag_id = dag_config.dag_id
        deps = self._get_asset_deps(task)

        @asset(
            name=task_id,
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

            return MaterializeResult(
                metadata={
                    "pipeline_id": MetadataValue.text(str(pipeline_id)),
                    "run_status": MetadataValue.text(
                        str(result.get("status", "unknown"))
                    ),
                }
            )

        return _dlt_asset

    # ------------------------------------------------------------------
    # dbt
    # ------------------------------------------------------------------

    def _build_dbt_asset(self, task, dag_config, group_name: str) -> AssetsDefinition:
        """Build a dbt run asset (default profile)."""
        return self._build_dbt_run(task, dag_config, group_name, profile=None)

    def _build_dbt_lake_asset(self, task, dag_config, group_name: str) -> AssetsDefinition:
        """Build a dbt run asset against the DuckDB / lake profile."""
        return self._build_dbt_run(task, dag_config, group_name, profile="lake")

    def _build_dbt_warehouse_asset(self, task, dag_config, group_name: str) -> AssetsDefinition:
        """Build a dbt run asset against the ClickHouse / warehouse profile."""
        return self._build_dbt_run(task, dag_config, group_name, profile="warehouse")

    def _build_dbt_run(self, task, dag_config, group_name: str, profile):
        config = task.config or {}
        models = config.get("models", [])
        tags = config.get("tags", [])
        full_refresh = config.get("full_refresh", False)
        task_id = task.task_id
        tenant_id = self.tenant_id
        dag_id = dag_config.dag_id
        deps = self._get_asset_deps(task)

        if tags:
            select_arg = " ".join([f"tag:{t}" for t in tags])
        elif models:
            select_arg = " ".join(models)
        else:
            select_arg = "*"

        @asset(
            name=task_id,
            group_name=group_name,
            compute_kind="dbt",
            deps=deps,
            metadata={
                "tenant_id": tenant_id,
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
            dbt.cli(cmd, context=context)

            return MaterializeResult(
                metadata={
                    "dbt_select": MetadataValue.text(select_arg),
                    "full_refresh": MetadataValue.bool(full_refresh),
                    "dbt_profile": MetadataValue.text(profile or "default"),
                }
            )

        return _dbt_asset

    def _build_dbt_test_asset(self, task, dag_config, group_name: str) -> AssetsDefinition:
        """Build a dbt test asset."""
        config = task.config or {}
        select_arg = config.get("select", "*")
        task_id = task.task_id
        tenant_id = self.tenant_id
        dag_id = dag_config.dag_id
        deps = self._get_asset_deps(task)

        @asset(
            name=task_id,
            group_name=group_name,
            compute_kind="dbt",
            deps=deps,
            metadata={
                "tenant_id": tenant_id,
                "dag_id": dag_id,
            },
            op_tags={"dagster/concurrency_key": "dbt_runs"},
        )
        def _dbt_test_asset(context: AssetExecutionContext) -> MaterializeResult:
            context.log.info("Running dbt tests: %s", select_arg)
            dbt = context.resources.dbt
            dbt.cli(["test", "--select", select_arg], context=context)
            return MaterializeResult(metadata={"tests_passed": MetadataValue.bool(True)})

        return _dbt_test_asset
