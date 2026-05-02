"""Inspect the existing dlt_revenuebyclient DagConfig (read-only)."""

from app import create_app
from app.extensions import db
from app.domains.orchestration.domain.models import DagConfig, TaskConfig

app = create_app()
with app.app_context():
    dags = (
        db.session.query(DagConfig)
        .filter(DagConfig.dag_id.ilike("%revenuebyclient%"))
        .all()
    )
    for dag in dags:
        print("=" * 60)
        print(f"DAG  id={dag.id}  dag_id={dag.dag_id}  tenant_id={dag.tenant_id}")
        print(f"     full_dag_id={dag.full_dag_id}  status={dag.status.value}")
        print(f"     tags={dag.tags}")
        for t in dag.tasks:
            print(
                f"  TASK id={t.id} task_id={t.task_id} type={t.task_type.value} "
                f"depends_on={t.depends_on} config={t.config}"
            )
