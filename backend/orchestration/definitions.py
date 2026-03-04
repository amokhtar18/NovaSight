"""
NovaSight Dagster Definitions
==============================

Main entry point for Dagster orchestration.
Dynamically loads jobs and assets from database at startup.

This unified module handles:
1. PySpark extraction jobs with remote spark-submit
2. DAG workflow scheduling
3. Pipeline orchestration
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

# Load PySpark assets from database
pyspark_assets = load_all_pyspark_assets()
all_assets.extend(pyspark_assets)
logger.info(f"Loaded {len(pyspark_assets)} PySpark extraction/transformation assets")

# Load DAG schedules
all_schedules = load_all_schedules()

# Load PySpark schedules from database
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
    # Dynamic Remote Spark resource — single source of truth
    # Reads master URL from DB infrastructure config at runtime.
    # Env var is only used as initial fallback until admin configures via UI.
    "spark_remote": DynamicRemoteSparkResource(
        ssh_host=os.environ.get("SPARK_SSH_HOST", ""),
        spark_master=os.environ.get("SPARK_MASTER_URL", "spark://spark-master:7077"),
    ),
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
