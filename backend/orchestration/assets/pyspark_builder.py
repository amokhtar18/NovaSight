"""
NovaSight Dagster Assets — PySpark Builder
============================================

Dynamic asset generation for PySpark jobs.
Provides scheduled execution of PySpark extraction and transformation pipelines.

This module creates Dagster assets dynamically from PySparkApp configurations
stored in the database, enabling:
1. Scheduled PySpark job execution
2. Incremental extraction with CDC support
3. SCD Type 1 and Type 2 transformations
4. Integration with ClickHouse as the target data warehouse

All generated PySpark code comes from pre-approved Jinja2 templates
(ADR-002: Template Engine Rule compliance).
"""

from typing import List, Dict, Any, Optional
from dagster import (
    asset,
    AssetKey,
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    AssetsDefinition,
    AssetOut,
    multi_asset,
    Output,
    AutoMaterializePolicy,
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PySparkAssetBuilder:
    """
    Builds Dagster assets from PySparkApp configurations.
    
    Creates executable assets that:
    1. Generate PySpark code from templates
    2. Submit jobs to Spark cluster
    3. Track execution metadata
    4. Update high watermarks for incremental loads
    """

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    def build_assets_from_pyspark_apps(
        self,
        apps: Optional[List[Any]] = None,
    ) -> List[AssetsDefinition]:
        """
        Build Dagster assets from all active PySparkApp configurations.
        
        Args:
            apps: Optional list of PySparkApp models. If None, queries from DB.
            
        Returns:
            List of AssetsDefinition for all active PySpark apps
        """
        if apps is None:
            apps = self._load_active_apps()
        
        assets = []
        for app in apps:
            try:
                asset_def = self._build_pyspark_asset(app)
                if asset_def:
                    assets.append(asset_def)
                    logger.info(f"Built PySpark asset: {app.name}")
            except Exception as e:
                logger.error(f"Failed to build asset for {app.name}: {e}")
        
        return assets

    def _load_active_apps(self) -> List[Any]:
        """Load active PySpark apps from database."""
        try:
            from app.domains.compute.domain.models import PySparkApp, PySparkAppStatus
            
            return PySparkApp.query.filter(
                PySparkApp.tenant_id == self.tenant_id,
                PySparkApp.status == PySparkAppStatus.ACTIVE,
            ).all()
        except Exception as e:
            logger.warning(f"Could not load PySpark apps: {e}")
            return []

    def _build_pyspark_asset(self, app) -> AssetsDefinition:
        """
        Build a single Dagster asset from a PySparkApp configuration.
        
        The asset will:
        1. Generate PySpark code using the template engine
        2. Submit the job to Spark
        3. Track execution metrics
        4. Update CDC high watermarks
        """
        app_id = str(app.id)
        app_name = app.name
        tenant_id = self.tenant_id
        # Replace hyphens with underscores to make valid Dagster names
        safe_tenant_id = tenant_id.replace('-', '_')
        source_table = app.source_table or "unknown"
        target_table = app.target_table or app.name.lower().replace(" ", "_")
        
        group_name = f"pyspark_tenant_{safe_tenant_id}"
        safe_app_name = app_name.lower().replace(' ', '_').replace('-', '_')

        @asset(
            name=f"pyspark_{safe_app_name}",
            group_name=group_name,
            compute_kind="spark",
            key_prefix=["pyspark", safe_tenant_id],
            required_resource_keys={"spark_remote"},
            metadata={
                "tenant_id": tenant_id,
                "app_id": app_id,
                "app_name": app_name,
                "source_table": source_table,
                "target_table": target_table,
                "scd_type": app.scd_type.value if hasattr(app, 'scd_type') else "none",
                "cdc_type": app.cdc_type.value if hasattr(app, 'cdc_type') else "none",
            },
            op_tags={
                "dagster/concurrency_key": "spark_jobs",
                "tenant_id": tenant_id,
            },
        )
        def _pyspark_extraction_asset(context: AssetExecutionContext) -> MaterializeResult:
            """Execute PySpark extraction job."""
            start_time = datetime.utcnow()
            
            context.log.info(f"Starting PySpark job: {app_name}")
            context.log.info(f"Source: {source_table} -> Target: {target_table}")
            
            # Get resources — use spark_remote for SSH-based submission
            spark = context.resources.spark_remote
            
            try:
                # 1. Generate code from template
                code, code_hash = _generate_pyspark_code(context, app_id, tenant_id)
                
                # 2. Write code to shared volume for Spark execution
                job_path = _write_pyspark_job(context, app_id, code)
                
                # 3. Submit job to Spark
                result = spark.submit_job(
                    app_path=job_path,
                    app_args=[
                        "--app-id", app_id,
                        "--tenant-id", tenant_id,
                    ],
                    spark_config={
                        "spark.app.name": f"NovaSight_{app_name}",
                    },
                )
                
                end_time = datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                
                if not result.get("success", False):
                    context.log.error(f"Spark job failed: {result.get('stderr', 'Unknown error')}")
                    raise Exception(f"Spark job failed: {result.get('stderr', '')[:500]}")
                
                # 4. Update execution stats in database
                rows_processed = _update_execution_stats(
                    context, app_id, tenant_id, duration_ms, "success"
                )
                
                context.log.info(f"PySpark job completed: {rows_processed} rows in {duration_ms}ms")
                
                return MaterializeResult(
                    metadata={
                        "app_name": MetadataValue.text(app_name),
                        "source_table": MetadataValue.text(source_table),
                        "target_table": MetadataValue.text(target_table),
                        "rows_processed": MetadataValue.int(rows_processed),
                        "duration_ms": MetadataValue.int(duration_ms),
                        "code_hash": MetadataValue.text(code_hash),
                        "job_path": MetadataValue.text(job_path),
                        "status": MetadataValue.text("success"),
                    }
                )
                
            except Exception as e:
                end_time = datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                
                _update_execution_stats(
                    context, app_id, tenant_id, duration_ms, f"error: {str(e)[:200]}"
                )
                
                raise

        return _pyspark_extraction_asset


def _generate_pyspark_code(
    context: AssetExecutionContext,
    app_id: str,
    tenant_id: str,
) -> tuple[str, str]:
    """
    Generate PySpark code from template using the PySparkAppService.
    
    Returns:
        Tuple of (generated_code, code_hash)
    """
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.domains.compute.application.pyspark_app_service import PySparkAppService
        
        app = create_app()
        with app.app_context():
            service = PySparkAppService(tenant_id)
            code, metadata = service.generate_code(app_id)
            code_hash = metadata.get("parameters_hash", "")
            
            return code, code_hash
    except Exception as e:
        context.log.error(f"Code generation failed: {e}")
        raise Exception(f"Failed to generate PySpark code: {e}")


def _write_pyspark_job(
    context: AssetExecutionContext,
    app_id: str,
    code: str,
) -> str:
    """
    Write generated PySpark code to the shared volume.
    
    Returns:
        Path to the written job file
    """
    from pathlib import Path
    
    jobs_dir = Path("/opt/spark/jobs/generated")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    
    job_path = jobs_dir / f"{app_id}.py"
    job_path.write_text(code)
    
    context.log.info(f"Wrote PySpark job to: {job_path}")
    return str(job_path)


def _update_execution_stats(
    context: AssetExecutionContext,
    app_id: str,
    tenant_id: str,
    duration_ms: int,
    status: str,
) -> int:
    """
    Update execution statistics in database.
    
    Returns:
        Number of rows processed (from logs or metrics)
    """
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.extensions import db
        from app.domains.compute.domain.models import PySparkApp
        from datetime import datetime
        
        app = create_app()
        with app.app_context():
            pyspark_app = PySparkApp.query.get(app_id)
            if pyspark_app:
                pyspark_app.last_run_at = datetime.utcnow()
                pyspark_app.last_run_status = status
                pyspark_app.last_run_duration_ms = duration_ms
                
                # Get rows from logs if available
                rows = pyspark_app.last_run_rows or 0
                
                db.session.commit()
                
                return rows
    except Exception as e:
        context.log.warning(f"Failed to update execution stats: {e}")
    
    return 0


def load_pyspark_assets_for_tenant(tenant_id: str) -> List[AssetsDefinition]:
    """
    Load all PySpark assets for a tenant.
    
    Called by the main definitions.py to dynamically load assets.
    """
    builder = PySparkAssetBuilder(tenant_id)
    return builder.build_assets_from_pyspark_apps()


def load_all_pyspark_assets() -> List[AssetsDefinition]:
    """
    Load PySpark assets for all active tenants.
    
    Called at Dagster startup to load all assets.
    """
    all_assets = []
    
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.domains.tenants.domain.models import Tenant
        from app.domains.compute.domain.models import PySparkApp, PySparkAppStatus
        
        app = create_app()
        with app.app_context():
            # Get all tenants with active PySpark apps
            tenant_ids = (
                PySparkApp.query
                .filter(PySparkApp.status == PySparkAppStatus.ACTIVE)
                .with_entities(PySparkApp.tenant_id)
                .distinct()
                .all()
            )
            
            for (tenant_id,) in tenant_ids:
                builder = PySparkAssetBuilder(str(tenant_id))
                assets = builder.build_assets_from_pyspark_apps()
                all_assets.extend(assets)
                logger.info(f"Loaded {len(assets)} PySpark assets for tenant {tenant_id}")
    
    except Exception as e:
        logger.warning(f"Could not load PySpark assets: {e}")
    
    return all_assets
