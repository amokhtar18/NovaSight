"""
Seed / upsert a ``DBT_RUN_WAREHOUSE`` TaskConfig that lands the
``revenuebyclient`` raw lake data (produced by the ``dlt_revenuebyclient``
task) into ClickHouse via the dbt model ``raw.revenuebyclient``.

Idempotent — running it multiple times converges to the same target state:
the existing dlt task is left untouched, and the warehouse task is created
or updated to depend on it.

Usage (inside the backend container)::

    docker exec novasight-backend python /app/scripts/seed_revenuebyclient_warehouse_task.py

Optional environment overrides::

    TENANT_SLUG          (default: novasight-demo)
    DAG_ID               (default: dlt_revenuebyclient)
    DBT_TASK_ID          (default: dbt_run_warehouse_revenuebyclient)
    DLT_TASK_ID          (default: <auto-detect from existing tasks>)
    DBT_MODEL            (default: revenuebyclient)
"""

from __future__ import annotations

import os
import sys

from app import create_app
from app.extensions import db
from app.domains.orchestration.domain.models import (
    DagConfig,
    DagStatus,
    TaskConfig,
    TaskType,
)


TENANT_SLUG = os.environ.get("TENANT_SLUG", "novasight-demo")
DAG_ID = os.environ.get("DAG_ID", "dlt_revenuebyclient")
DBT_TASK_ID = os.environ.get(
    "DBT_TASK_ID", "dbt_run_warehouse_revenuebyclient"
)
DBT_MODEL = os.environ.get("DBT_MODEL", "revenuebyclient")
DLT_TASK_ID_OVERRIDE = os.environ.get("DLT_TASK_ID")


def _find_dag(session) -> DagConfig:
    dag = (
        session.query(DagConfig)
        .join(DagConfig.tenant)
        .filter(
            DagConfig.dag_id == DAG_ID,
            DagConfig.status != DagStatus.ARCHIVED,
        )
        .all()
    )
    matched = [d for d in dag if d.tenant.slug == TENANT_SLUG]
    if not matched:
        raise SystemExit(
            f"No DagConfig found with dag_id={DAG_ID!r} for tenant slug "
            f"{TENANT_SLUG!r}. Run the dlt pipeline scaffolder first."
        )
    if len(matched) > 1:
        raise SystemExit(
            f"Found multiple DagConfigs with dag_id={DAG_ID!r} for tenant "
            f"slug {TENANT_SLUG!r}; refusing to guess."
        )
    return matched[0]


def _resolve_dlt_task_id(dag: DagConfig) -> str:
    if DLT_TASK_ID_OVERRIDE:
        return DLT_TASK_ID_OVERRIDE
    dlt_tasks = [t for t in dag.tasks if t.task_type == TaskType.DLT_RUN]
    if not dlt_tasks:
        raise SystemExit(
            f"DAG {dag.dag_id!r} has no DLT_RUN tasks to depend on."
        )
    if len(dlt_tasks) > 1:
        raise SystemExit(
            f"DAG {dag.dag_id!r} has multiple DLT_RUN tasks "
            f"({[t.task_id for t in dlt_tasks]}); set DLT_TASK_ID env var."
        )
    return dlt_tasks[0].task_id


def main() -> int:
    app = create_app()
    with app.app_context():
        dag = _find_dag(db.session)
        dlt_task_id = _resolve_dlt_task_id(dag)

        existing = (
            db.session.query(TaskConfig)
            .filter(
                TaskConfig.dag_config_id == dag.id,
                TaskConfig.task_id == DBT_TASK_ID,
            )
            .one_or_none()
        )

        task_config_payload = {
            "models": [DBT_MODEL],
            "tags": [],
            "full_refresh": False,
        }

        if existing is None:
            task = TaskConfig(
                dag_config_id=dag.id,
                task_id=DBT_TASK_ID,
                task_type=TaskType.DBT_RUN_WAREHOUSE,
                config=task_config_payload,
                timeout_minutes=60,
                retries=1,
                retry_delay_minutes=5,
                depends_on=[dlt_task_id],
                position_x=400,
                position_y=200,
            )
            db.session.add(task)
            action = "created"
        else:
            existing.task_type = TaskType.DBT_RUN_WAREHOUSE
            existing.config = task_config_payload
            existing.depends_on = [dlt_task_id]
            existing.timeout_minutes = 60
            action = "updated"

        # Ensure DAG is at least ACTIVE so the asset job is registered.
        if dag.status == DagStatus.DRAFT:
            dag.status = DagStatus.ACTIVE

        # Ensure tag for filtering
        tags = list(dag.tags or [])
        if "dbt_run_warehouse" not in tags:
            tags.append("dbt_run_warehouse")
            dag.tags = tags

        db.session.commit()

        print(
            f"[seed_revenuebyclient_warehouse_task] {action} task "
            f"{DBT_TASK_ID!r} on dag {dag.dag_id!r} "
            f"(tenant={TENANT_SLUG}, depends_on=[{dlt_task_id}], "
            f"model={DBT_MODEL})"
        )
        print(f"  full_dag_id = {dag.full_dag_id}")
        print(f"  Dagster job = {dag.full_dag_id}_job")
    return 0


if __name__ == "__main__":
    sys.exit(main())
