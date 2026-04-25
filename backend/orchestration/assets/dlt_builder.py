"""
NovaSight Dagster Assets — dlt Builder
=======================================

Dynamic asset generation for dlt pipelines.
Provides scheduled execution of dlt extraction pipelines that load data
into Iceberg tables on S3.

This module creates Dagster assets dynamically from DltPipeline configurations
stored in the database, enabling:
1. Scheduled dlt pipeline execution
2. Incremental extraction with cursor tracking
3. SCD Type 2 transformations
4. Integration with Iceberg on S3 as the data lake

All generated dlt code comes from pre-approved Jinja2 templates
(ADR-002: Template Engine Rule compliance).
"""

import os
import subprocess
import re
from typing import List, Dict, Any, Optional
from dagster import (
    asset,
    AssetKey,
    AssetExecutionContext,
    MaterializeResult,
    MetadataValue,
    AssetsDefinition,
    Failure,
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Path to generated dlt pipelines
DLT_PIPELINES_PATH = os.getenv("DLT_PIPELINES_PATH", "/opt/dlt/pipelines")


class DltAssetBuilder:
    """
    Builds Dagster assets from DltPipeline configurations.
    
    Creates executable assets that:
    1. Run generated dlt pipeline scripts as subprocesses
    2. Inject environment variables for tenant isolation
    3. Track execution metadata
    4. Update pipeline stats in database
    """

    def __init__(self, tenant_id: str, tenant_slug: str):
        self.tenant_id = tenant_id
        self.tenant_slug = tenant_slug

    def build_assets_from_dlt_pipelines(
        self,
        pipelines: Optional[List[Any]] = None,
    ) -> List[AssetsDefinition]:
        """
        Build Dagster assets from all active DltPipeline configurations.
        
        Args:
            pipelines: Optional list of DltPipeline models. If None, queries from DB.
            
        Returns:
            List of AssetsDefinition for all active dlt pipelines
        """
        if pipelines is None:
            pipelines = self._load_active_pipelines()
        
        assets = []
        for pipeline in pipelines:
            try:
                asset_def = self._build_dlt_asset(pipeline)
                if asset_def:
                    assets.append(asset_def)
                    logger.info(f"Built dlt asset: {pipeline.name}")
            except Exception as e:
                logger.error(f"Failed to build asset for {pipeline.name}: {e}")
        
        return assets

    def _load_active_pipelines(self) -> List[Any]:
        """Load active dlt pipelines from database."""
        try:
            from app.domains.ingestion.domain.models import DltPipeline, DltPipelineStatus
            
            return DltPipeline.query.filter(
                DltPipeline.tenant_id == self.tenant_id,
                DltPipeline.status == DltPipelineStatus.ACTIVE,
            ).all()
        except Exception as e:
            logger.warning(f"Could not load dlt pipelines: {e}")
            return []

    def _build_dlt_asset(self, pipeline) -> AssetsDefinition:
        """
        Build a single Dagster asset from a DltPipeline configuration.
        
        The asset will:
        1. Run the generated dlt pipeline script as a subprocess
        2. Inject environment variables for S3/Iceberg access
        3. Track execution metrics from stdout
        4. Update pipeline stats in database
        """
        pipeline_id = str(pipeline.id)
        pipeline_name = pipeline.name
        tenant_id = self.tenant_id
        tenant_slug = self.tenant_slug
        
        # Create safe names for Dagster
        safe_slug = tenant_slug.replace('-', '_').replace('.', '_')
        safe_pipeline_name = pipeline_name.lower().replace(' ', '_').replace('-', '_')
        
        group_name = f"tenant_{safe_slug}"
        iceberg_namespace = pipeline.iceberg_namespace or f"tenant_{safe_slug}.raw"
        iceberg_table = pipeline.iceberg_table_name or safe_pipeline_name
        source_table = pipeline.source_table or "query"
        write_disposition = pipeline.write_disposition.value if pipeline.write_disposition else "append"

        @asset(
            name=f"dlt_{safe_slug}__{safe_pipeline_name}",
            group_name=group_name,
            compute_kind="dlt",
            key_prefix=["dlt", safe_slug],
            metadata={
                "tenant_id": tenant_id,
                "tenant_slug": tenant_slug,
                "pipeline_id": pipeline_id,
                "pipeline_name": pipeline_name,
                "source_table": source_table,
                "iceberg_namespace": iceberg_namespace,
                "iceberg_table": iceberg_table,
                "write_disposition": write_disposition,
            },
            op_tags={
                "dagster/concurrency_key": "dlt_pipelines",
                "tenant_id": tenant_id,
            },
        )
        def _dlt_extraction_asset(context: AssetExecutionContext) -> MaterializeResult:
            """Execute dlt extraction pipeline."""
            start_time = datetime.utcnow()
            
            context.log.info(f"Starting dlt pipeline: {pipeline_name}")
            context.log.info(f"Target: {iceberg_namespace}.{iceberg_table}")
            context.log.info(f"Write disposition: {write_disposition}")
            
            try:
                # 1. Build environment variables
                env = _build_pipeline_env(context, tenant_id, tenant_slug, pipeline_id)
                
                # 2. Determine pipeline script path
                script_path = os.path.join(DLT_PIPELINES_PATH, tenant_slug, f"{pipeline_name}.py")
                
                if not os.path.exists(script_path):
                    raise Failure(
                        description=f"Pipeline script not found: {script_path}. "
                        "Generate the pipeline code first.",
                    )
                
                # 3. Run pipeline as subprocess
                context.log.info(f"Running: python {script_path}")
                
                result = subprocess.run(
                    ["python", script_path],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=3600,  # 1 hour timeout
                )
                
                end_time = datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                
                # Log output
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        context.log.info(line)
                
                if result.returncode != 0:
                    # Log stderr for debugging
                    stderr_excerpt = result.stderr[-2000:] if result.stderr else "No error output"
                    context.log.error(f"Pipeline failed with exit code {result.returncode}")
                    context.log.error(stderr_excerpt)
                    
                    # Update stats with error
                    _update_pipeline_stats(
                        context, pipeline_id, "error", duration_ms=duration_ms
                    )
                    
                    raise Failure(
                        description=f"dlt pipeline failed: {stderr_excerpt[:500]}",
                    )
                
                # 4. Parse metrics from stdout
                metrics = _parse_pipeline_metrics(result.stdout)
                rows = metrics.get("rows", 0)
                iceberg_snapshot = metrics.get("iceberg_snapshot_id")
                
                # 5. Update execution stats in database
                _update_pipeline_stats(
                    context, pipeline_id, "success",
                    rows=rows,
                    duration_ms=duration_ms,
                    iceberg_snapshot_id=iceberg_snapshot,
                )
                
                context.log.info(f"dlt pipeline completed: {rows} rows in {duration_ms}ms")
                
                return MaterializeResult(
                    metadata={
                        "pipeline_name": MetadataValue.text(pipeline_name),
                        "source_table": MetadataValue.text(source_table),
                        "iceberg_namespace": MetadataValue.text(iceberg_namespace),
                        "iceberg_table": MetadataValue.text(iceberg_table),
                        "write_disposition": MetadataValue.text(write_disposition),
                        "rows_processed": MetadataValue.int(rows),
                        "duration_ms": MetadataValue.int(duration_ms),
                        "status": MetadataValue.text("success"),
                    }
                )
                
            except subprocess.TimeoutExpired:
                _update_pipeline_stats(context, pipeline_id, "timeout")
                raise Failure(description="Pipeline execution timed out after 1 hour")
                
            except Failure:
                raise
                
            except Exception as e:
                end_time = datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                
                _update_pipeline_stats(
                    context, pipeline_id, f"error: {str(e)[:200]}",
                    duration_ms=duration_ms,
                )
                
                raise Failure(description=str(e))

        return _dlt_extraction_asset


def _build_pipeline_env(
    context: AssetExecutionContext,
    tenant_id: str,
    tenant_slug: str,
    pipeline_id: str,
) -> Dict[str, str]:
    """
    Build environment variables for pipeline execution.
    
    Injects tenant-specific S3 credentials and Iceberg catalog URL.
    """
    import os
    
    # Start with current environment
    env = os.environ.copy()
    
    # Add tenant context
    env["TENANT_ID"] = tenant_id
    env["TENANT_SLUG"] = tenant_slug
    env["PIPELINE_ID"] = pipeline_id
    
    # Get tenant S3 config
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.domains.tenants.infrastructure.config_service import InfrastructureConfigService
        
        app = create_app()
        with app.app_context():
            service = InfrastructureConfigService()
            configs = service.list_configs(
                service_type="object_storage",
                tenant_id=tenant_id,
                include_global=False,
                page=1,
                per_page=1,
            )
            
            if configs.get("items"):
                settings = configs["items"][0].get("settings", {})
                # Decrypt credentials
                decrypted = service.decrypt_settings(settings, "object_storage")
                
                env["TENANT_S3_BUCKET"] = decrypted.get("bucket", "")
                env["AWS_ACCESS_KEY_ID"] = decrypted.get("access_key", "")
                env["AWS_SECRET_ACCESS_KEY"] = decrypted.get("secret_key", "")
                env["S3_ENDPOINT_URL"] = decrypted.get("endpoint_url", "")
                env["AWS_REGION"] = decrypted.get("region", "us-east-1")
                
    except Exception as e:
        context.log.warning(f"Could not load S3 config: {e}")
    
    # Iceberg catalog URL
    env["ICEBERG_CATALOG_URL"] = os.getenv(
        "ICEBERG_CATALOG_URL",
        "postgresql://novasight:novasight@postgres:5432/novasight_platform"
    )
    
    # Get source connection string
    try:
        from app import create_app
        from app.domains.ingestion.domain.models import DltPipeline
        from app.domains.datasources.application.connection_service import ConnectionService
        
        app = create_app()
        with app.app_context():
            pipeline = DltPipeline.query.get(pipeline_id)
            if pipeline and pipeline.connection_id:
                conn_service = ConnectionService()
                connection = conn_service.get_connection(str(pipeline.connection_id))
                if connection:
                    # Build connection string
                    env["SOURCE_CONNECTION_STRING"] = conn_service.get_connection_string(
                        str(pipeline.connection_id)
                    )
    except Exception as e:
        context.log.warning(f"Could not load connection string: {e}")
    
    return env


def _parse_pipeline_metrics(stdout: str) -> Dict[str, Any]:
    """
    Parse metrics from pipeline stdout.
    
    Looks for lines like:
    METRICS:rows=1000
    METRICS:duration_ms=5000
    METRICS:iceberg_snapshot_id=abc123
    """
    metrics = {}
    
    for line in stdout.split('\n'):
        if line.startswith("METRICS:"):
            try:
                metric_part = line[8:]  # Remove "METRICS:"
                key, value = metric_part.split('=', 1)
                
                # Try to convert to int
                try:
                    value = int(value)
                except ValueError:
                    pass
                
                metrics[key] = value
            except Exception:
                pass
    
    return metrics


def _update_pipeline_stats(
    context: AssetExecutionContext,
    pipeline_id: str,
    status: str,
    rows: Optional[int] = None,
    duration_ms: Optional[int] = None,
    iceberg_snapshot_id: Optional[str] = None,
) -> None:
    """
    Update pipeline execution statistics in database.
    """
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.domains.ingestion.application.dlt_pipeline_service import DltPipelineService
        
        app = create_app()
        with app.app_context():
            service = DltPipelineService()
            service.update_run_stats(
                pipeline_id=pipeline_id,
                status=status,
                rows=rows,
                duration_ms=duration_ms,
                iceberg_snapshot_id=iceberg_snapshot_id,
            )
    except Exception as e:
        context.log.warning(f"Failed to update pipeline stats: {e}")


def load_dlt_assets_for_tenant(tenant_id: str, tenant_slug: str) -> List[AssetsDefinition]:
    """
    Load all dlt assets for a tenant.
    
    Called by the main definitions.py to dynamically load assets.
    """
    builder = DltAssetBuilder(tenant_id, tenant_slug)
    return builder.build_assets_from_dlt_pipelines()


def load_all_dlt_assets() -> List[AssetsDefinition]:
    """
    Load dlt assets for all active tenants.
    
    Called at Dagster startup to load all assets.
    """
    all_assets = []
    
    try:
        import sys
        if '/app' not in sys.path:
            sys.path.insert(0, '/app')
        
        from app import create_app
        from app.domains.tenants.domain.models import Tenant
        from app.domains.ingestion.domain.models import DltPipeline, DltPipelineStatus
        
        app = create_app()
        with app.app_context():
            # Get all tenants with active dlt pipelines
            results = (
                DltPipeline.query
                .join(Tenant, DltPipeline.tenant_id == Tenant.id)
                .filter(DltPipeline.status == DltPipelineStatus.ACTIVE)
                .with_entities(DltPipeline.tenant_id, Tenant.slug)
                .distinct()
                .all()
            )
            
            for tenant_id, tenant_slug in results:
                builder = DltAssetBuilder(str(tenant_id), tenant_slug)
                assets = builder.build_assets_from_dlt_pipelines()
                all_assets.extend(assets)
                logger.info(f"Loaded {len(assets)} dlt assets for tenant {tenant_slug}")
    
    except Exception as e:
        logger.warning(f"Could not load dlt assets: {e}")
    
    return all_assets
