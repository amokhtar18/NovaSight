"""
NovaSight Dagster Definitions
==============================

Main entry point for Dagster orchestration.
Dynamically loads jobs and assets from database at startup.

This unified module handles:
1. dlt extraction pipelines (new) - loads to Iceberg on S3
2. PySpark extraction jobs (legacy) with remote spark-submit
3. DAG workflow scheduling
4. Pipeline orchestration
"""

from dagster import Definitions, EnvVar
from dagster_dbt import DbtCliResource
import os
import logging

from orchestration.resources.clickhouse_resource import ClickHouseResource, DynamicClickHouseResource
from orchestration.resources.database_resource import DatabaseResource
from orchestration.resources.remote_spark_resource import (
    DynamicRemoteSparkResource,
)
# dlt assets and schedules (new)
from orchestration.assets.dlt_builder import load_all_dlt_assets
from orchestration.schedules.dlt_schedules import load_all_dlt_schedules
# PySpark assets and schedules (legacy - to be removed in Phase 6)
from orchestration.assets.pyspark_builder import load_all_pyspark_assets
from orchestration.schedules.pyspark_schedules import load_all_pyspark_schedules
from orchestration.jobs.dagster_job_builder import (
    load_all_dagster_jobs,
    load_all_schedules as load_job_schedules,
)

logger = logging.getLogger(__name__)


def load_all_tenant_assets():
    """
    Load assets for all active DAG configurations across tenants.
    
    This runs at Dagster startup and when code location is reloaded.
    """
    all_assets = []
    
    try:
        # Import Flask app to get database access
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.extensions import db
        from app.domains.orchestration.domain.models import DagConfig, DagStatus
        from app.domains.orchestration.infrastructure.asset_factory import AssetFactory
        
        # Create Flask app context for database access
        app = create_app()
        with app.app_context():
            # Query all deployed DAGs
            deployed_dags = DagConfig.query.filter(
                DagConfig.status.in_([DagStatus.ACTIVE, DagStatus.PAUSED])
            ).all()
            
            logger.info(f"Loading assets for {len(deployed_dags)} DAG configurations")
            
            for dag in deployed_dags:
                try:
                    factory = AssetFactory(str(dag.tenant_id))
                    assets = factory.build_assets_from_dag_config(dag)
                    all_assets.extend(assets)
                    logger.info(f"Loaded {len(assets)} assets for {dag.dag_id}")
                except Exception as e:
                    logger.error(f"Failed to load assets for {dag.dag_id}: {e}")
    
    except Exception as e:
        logger.warning(f"Could not load tenant assets: {e}. Starting with empty assets.")
    
    return all_assets


def load_all_schedules():
    """
    Load schedules for all active DAG configurations.
    """
    all_schedules = []
    
    try:
        import sys
        sys.path.insert(0, '/app/backend')
        
        from app import create_app
        from app.domains.orchestration.domain.models import DagConfig, DagStatus
        from app.domains.orchestration.infrastructure.schedule_factory import ScheduleFactory
        
        app = create_app()
        with app.app_context():
            deployed_dags = DagConfig.query.filter(
                DagConfig.status.in_([DagStatus.ACTIVE, DagStatus.PAUSED])
            ).all()
            
            logger.info(f"Loading schedules for {len(deployed_dags)} DAG configurations")
            
            for dag in deployed_dags:
                try:
                    factory = ScheduleFactory(str(dag.tenant_id))
                    schedule = factory.build_schedule_from_dag_config(dag)
                    if schedule:
                        all_schedules.append(schedule)
                        logger.info(f"Loaded schedule for {dag.dag_id}")
                except Exception as e:
                    logger.error(f"Failed to load schedule for {dag.dag_id}: {e}")
    
    except Exception as e:
        logger.warning(f"Could not load schedules: {e}. Starting with no schedules.")
    
    return all_schedules


# Load assets and schedules from database
all_assets = load_all_tenant_assets()

# Load dlt assets from database (new - Iceberg/S3 pipelines)
dlt_assets = load_all_dlt_assets()
all_assets.extend(dlt_assets)
logger.info(f"Loaded {len(dlt_assets)} dlt extraction assets")

# Load PySpark assets from database (legacy - to be removed in Phase 6)
pyspark_assets = load_all_pyspark_assets()
all_assets.extend(pyspark_assets)
logger.info(f"Loaded {len(pyspark_assets)} PySpark extraction/transformation assets")

# Load DAG schedules
all_schedules = load_all_schedules()

# Load dlt schedules from database (new)
dlt_schedules = load_all_dlt_schedules()
all_schedules.extend(dlt_schedules)
logger.info(f"Loaded {len(dlt_schedules)} dlt pipeline schedules")

# Load PySpark schedules from database (legacy - to be removed in Phase 6)
pyspark_schedules = load_all_pyspark_schedules()
all_schedules.extend(pyspark_schedules)
logger.info(f"Loaded {len(pyspark_schedules)} PySpark job schedules")

# Load Dagster jobs (new unified job system)
all_jobs = load_all_dagster_jobs()
logger.info(f"Loaded {len(all_jobs)} Dagster jobs for remote spark-submit")

# Load job schedules
job_schedules = load_job_schedules()
all_schedules.extend(job_schedules)
logger.info(f"Loaded {len(job_schedules)} job schedules")

# ── Seed Spark resource fields from infrastructure DB config ──────────
# Read the DB config at startup so the Dagster UI displays the real
# values (master URL, ssh_host, rest_url, etc.) instead of static
# env-var defaults.  At runtime _get_dynamic_config() still fetches
# fresh DB values so hot-reload continues to work.
_spark_resource_kwargs: dict = {
    "ssh_host": os.environ.get("SPARK_SSH_HOST", ""),
    "spark_master": os.environ.get("SPARK_MASTER_URL", "spark://spark-master:7077"),
    "spark_rest_url": "http://spark-master:6066",
    "execution_mode": os.environ.get("SPARK_EXECUTION_MODE", "docker"),
    "docker_container": os.environ.get("SPARK_MASTER_CONTAINER", "novasight-spark-master"),
}

try:
    import sys as _sys
    if '/app' not in _sys.path:
        _sys.path.insert(0, '/app')
    from app import create_app as _create_app
    from app.platform.infrastructure import InfrastructureConfigProvider as _ICP

    _flask_app = _create_app()
    with _flask_app.app_context():
        _spark_cfg = _ICP().get_spark_config()
        if _spark_cfg:
            _infra_host = _spark_cfg.host or "spark-master"
            _spark_resource_kwargs.update({
                "spark_master": _spark_cfg.master_url,
                "ssh_host": getattr(_spark_cfg, 'ssh_host', '') or "",
                "spark_home": getattr(_spark_cfg, 'spark_home', '/opt/spark'),
                "deploy_mode": getattr(_spark_cfg, 'deploy_mode', 'client'),
                "driver_memory": _spark_cfg.driver_memory,
                "executor_memory": _spark_cfg.executor_memory,
                "executor_cores": _spark_cfg.executor_cores,
                "num_executors": getattr(_spark_cfg, 'num_executors', 2),
                "remote_jobs_dir": getattr(_spark_cfg, 'remote_jobs_dir', '/opt/spark/jobs'),
                "spark_rest_url": (
                    getattr(_spark_cfg, 'rest_url', '') or ""
                ) or os.environ.get("SPARK_REST_URL", "") or "http://spark-master:6066",
            })
            logger.info(
                "Seeded spark_remote resource from DB: master=%s, host=%s",
                _spark_resource_kwargs["spark_master"],
                _infra_host,
            )
except Exception as _e:
    logger.warning("Could not seed spark_remote from DB, using env defaults: %s", _e)

# Resource definitions
# All Spark resources use DynamicRemoteSparkResource which reads
# the master URL exclusively from the infrastructure config database.
# Static SparkResource and DynamicSparkResource are intentionally
# excluded to enforce a single source of truth for cluster connection.
resources = {
    "dbt": DbtCliResource(
        project_dir=os.environ.get("DBT_PROJECT_DIR", "/app/dbt"),
        profiles_dir=os.environ.get("DBT_PROFILES_DIR", "/app/dbt"),
    ),
    # Dynamic Remote Spark resource — single source of truth.
    # Fields are seeded from DB at startup (above) so the Dagster UI
    # matches the real infra config. _get_dynamic_config() still
    # fetches fresh values at job run time.
    "spark_remote": DynamicRemoteSparkResource(**_spark_resource_kwargs),
    # Static ClickHouse resource (uses environment config)
    "clickhouse": ClickHouseResource(
        host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
        port=int(os.environ.get("CLICKHOUSE_PORT", "9000")),
    ),
    # Dynamic ClickHouse resource (uses database config per tenant)
    "clickhouse_dynamic": DynamicClickHouseResource(
        fallback_host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
        fallback_port=int(os.environ.get("CLICKHOUSE_PORT", "9000")),
    ),
    "postgres": DatabaseResource(
        connection_string=os.environ.get("DATABASE_URL", ""),
    ),
}

# Create Dagster definitions
defs = Definitions(
    assets=all_assets,
    jobs=all_jobs,
    schedules=all_schedules,
    sensors=[],  # Can be extended with sensors later
    resources=resources,
)
