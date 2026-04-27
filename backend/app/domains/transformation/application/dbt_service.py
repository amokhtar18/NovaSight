"""
dbt Service for NovaSight.

Provides dbt command execution with multi-tenant context support.

Supports dual-adapter pattern (Spark → dlt migration):
- dbt-duckdb: Reads from Iceberg tables on S3 (data lake layer)
- dbt-clickhouse: Writes to ClickHouse marts (data warehouse layer)
"""

import subprocess
import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from flask import current_app

logger = logging.getLogger(__name__)


class DbtCommand(str, Enum):
    """Supported dbt commands."""
    RUN = "run"
    TEST = "test"
    BUILD = "build"
    COMPILE = "compile"
    SEED = "seed"
    SNAPSHOT = "snapshot"
    DEPS = "deps"
    DEBUG = "debug"
    DOCS_GENERATE = "docs generate"
    LS = "ls"
    PARSE = "parse"


class DbtTarget(str, Enum):
    """dbt target environments for dual-adapter pattern."""
    LAKE = "lake"          # dbt-duckdb reading from Iceberg
    WAREHOUSE = "warehouse"  # dbt-clickhouse writing to marts
    DEV = "dev"             # Legacy ClickHouse-only (backward compat)
    PROD = "prod"           # Legacy ClickHouse-only (backward compat)


@dataclass
class DbtResult:
    """Result of a dbt command execution."""
    success: bool
    command: str
    stdout: str
    stderr: str
    return_code: int
    run_results: Optional[Dict[str, Any]] = None
    manifest: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "command": self.command,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "return_code": self.return_code,
            "run_results": self.run_results,
            "manifest": self.manifest,
        }


class DbtService:
    """Service for executing dbt commands with tenant context."""
    
    def __init__(self, dbt_project_path: Optional[str] = None):
        """
        Initialize the dbt service.
        
        Args:
            dbt_project_path: Path to the dbt project directory.
                            Defaults to configured path or ./dbt
        """
        if dbt_project_path:
            self.project_path = Path(dbt_project_path)
        else:
            # Try to get from Flask config, fallback to default
            try:
                self.project_path = Path(current_app.config.get(
                    'DBT_PROJECT_PATH',
                    './dbt'
                ))
            except RuntimeError:
                # Outside Flask context
                self.project_path = Path('./dbt')
        
        self.profiles_dir = self.project_path
    
    def run(
        self,
        tenant_id: str,
        select: Optional[str] = None,
        exclude: Optional[str] = None,
        full_refresh: bool = False,
        vars: Optional[Dict[str, Any]] = None,
        target: Optional[str] = None,
    ) -> DbtResult:
        """
        Run dbt models.
        
        Args:
            tenant_id: Tenant identifier for context
            select: Model selection criteria (e.g., "staging.customers+")
            exclude: Models to exclude
            full_refresh: Force full refresh of incremental models
            vars: Additional dbt variables
            target: Target environment (dev, prod)
            
        Returns:
            DbtResult with execution details
        """
        cmd = ['dbt', 'run']
        
        if select:
            cmd.extend(['--select', select])
        if exclude:
            cmd.extend(['--exclude', exclude])
        if full_refresh:
            cmd.append('--full-refresh')
        if vars:
            cmd.extend(['--vars', json.dumps(vars)])
        if target:
            cmd.extend(['--target', target])
        
        return self._execute(cmd, tenant_id)
    
    def test(
        self,
        tenant_id: str,
        select: Optional[str] = None,
        exclude: Optional[str] = None,
        store_failures: bool = False,
    ) -> DbtResult:
        """
        Run dbt tests.
        
        Args:
            tenant_id: Tenant identifier for context
            select: Test selection criteria
            exclude: Tests to exclude
            store_failures: Store test failures in database
            
        Returns:
            DbtResult with execution details
        """
        cmd = ['dbt', 'test']
        
        if select:
            cmd.extend(['--select', select])
        if exclude:
            cmd.extend(['--exclude', exclude])
        if store_failures:
            cmd.append('--store-failures')
        
        return self._execute(cmd, tenant_id)
    
    def build(
        self,
        tenant_id: str,
        select: Optional[str] = None,
        exclude: Optional[str] = None,
        full_refresh: bool = False,
    ) -> DbtResult:
        """
        Run dbt build (run + test in DAG order).
        
        Args:
            tenant_id: Tenant identifier for context
            select: Selection criteria
            exclude: Items to exclude
            full_refresh: Force full refresh
            
        Returns:
            DbtResult with execution details
        """
        cmd = ['dbt', 'build']
        
        if select:
            cmd.extend(['--select', select])
        if exclude:
            cmd.extend(['--exclude', exclude])
        if full_refresh:
            cmd.append('--full-refresh')
        
        return self._execute(cmd, tenant_id)
    
    def compile(
        self,
        tenant_id: str,
        select: Optional[str] = None,
    ) -> DbtResult:
        """
        Compile dbt models without executing.
        
        Args:
            tenant_id: Tenant identifier for context
            select: Model selection criteria
            
        Returns:
            DbtResult with compiled SQL
        """
        cmd = ['dbt', 'compile']
        
        if select:
            cmd.extend(['--select', select])
        
        return self._execute(cmd, tenant_id)
    
    def seed(
        self,
        tenant_id: str,
        select: Optional[str] = None,
        full_refresh: bool = False,
    ) -> DbtResult:
        """
        Load seed data.
        
        Args:
            tenant_id: Tenant identifier for context
            select: Seed selection criteria
            full_refresh: Drop and recreate seeds
            
        Returns:
            DbtResult with execution details
        """
        cmd = ['dbt', 'seed']
        
        if select:
            cmd.extend(['--select', select])
        if full_refresh:
            cmd.append('--full-refresh')
        
        return self._execute(cmd, tenant_id)
    
    def snapshot(
        self,
        tenant_id: str,
        select: Optional[str] = None,
    ) -> DbtResult:
        """
        Run dbt snapshots (SCD Type 2).
        
        Args:
            tenant_id: Tenant identifier for context
            select: Snapshot selection criteria
            
        Returns:
            DbtResult with execution details
        """
        cmd = ['dbt', 'snapshot']
        
        if select:
            cmd.extend(['--select', select])
        
        return self._execute(cmd, tenant_id)
    
    def deps(self) -> DbtResult:
        """
        Install dbt packages.
        
        Returns:
            DbtResult with execution details
        """
        cmd = ['dbt', 'deps']
        return self._execute(cmd, tenant_id='system')
    
    def debug(self, tenant_id: str) -> DbtResult:
        """
        Test dbt connection and configuration.
        
        Args:
            tenant_id: Tenant identifier for context
            
        Returns:
            DbtResult with debug information
        """
        cmd = ['dbt', 'debug']
        return self._execute(cmd, tenant_id)
    
    def docs_generate(self, tenant_id: str) -> DbtResult:
        """
        Generate dbt documentation.
        
        Args:
            tenant_id: Tenant identifier for context
            
        Returns:
            DbtResult with execution details
        """
        cmd = ['dbt', 'docs', 'generate']
        return self._execute(cmd, tenant_id)
    
    def list_models(
        self,
        tenant_id: str,
        select: Optional[str] = None,
        resource_type: str = "model",
    ) -> DbtResult:
        """
        List dbt resources.
        
        Args:
            tenant_id: Tenant identifier for context
            select: Selection criteria
            resource_type: Type of resource (model, test, source, etc.)
            
        Returns:
            DbtResult with list of resources
        """
        cmd = ['dbt', 'ls', '--resource-type', resource_type, '--output', 'json']
        
        if select:
            cmd.extend(['--select', select])
        
        return self._execute(cmd, tenant_id)
    
    def parse(self, tenant_id: str) -> DbtResult:
        """
        Parse dbt project and build manifest.
        
        Args:
            tenant_id: Tenant identifier for context
            
        Returns:
            DbtResult with manifest
        """
        cmd = ['dbt', 'parse']
        result = self._execute(cmd, tenant_id)
        
        # Try to load manifest if parse succeeded
        if result.success:
            manifest_path = self.project_path / 'target' / 'manifest.json'
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    result.manifest = json.load(f)
        
        return result
    
    def get_lineage(
        self,
        tenant_id: str,
        model_name: str,
        upstream_depth: int = 3,
        downstream_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Get lineage information for a model with configurable depth.
        
        Args:
            tenant_id: Tenant identifier for context
            model_name: Name of the model
            upstream_depth: How many levels of upstream dependencies to include
            downstream_depth: How many levels of downstream dependencies to include
            
        Returns:
            Dictionary with root node, upstream, downstream, and edges
        """
        # First parse to get manifest
        parse_result = self.parse(tenant_id)
        
        if not parse_result.success or not parse_result.manifest:
            return {
                "error": "Failed to parse project",
                "details": parse_result.stderr
            }
        
        manifest = parse_result.manifest
        nodes = manifest.get('nodes', {})
        sources = manifest.get('sources', {})
        all_nodes = {**nodes, **sources}
        
        # Find the model
        model_key = None
        for key, node in nodes.items():
            if node.get('name') == model_name and node.get('resource_type') == 'model':
                model_key = key
                break
        
        if not model_key:
            return {"error": f"Model '{model_name}' not found"}
        
        model_node = nodes[model_key]
        child_map = manifest.get('child_map', {})
        
        # Helper to extract node info
        def node_info(key: str, node: Dict) -> Dict[str, Any]:
            # Infer layer from path or fqn
            layer = None
            fqn = node.get('fqn', [])
            if len(fqn) > 1:
                layer_candidate = fqn[1] if len(fqn) > 1 else None
                if layer_candidate in ('staging', 'intermediate', 'marts', 'source'):
                    layer = layer_candidate
            return {
                "id": key,
                "name": node.get('name'),
                "resource_type": node.get('resource_type'),
                "layer": layer,
                "materialization": node.get('config', {}).get('materialized', 'view'),
                "description": node.get('description'),
                "tags": node.get('tags', []),
            }
        
        # BFS to get upstream
        upstream = []
        upstream_visited = set()
        upstream_queue = [(model_key, 0)]
        edges = []
        
        while upstream_queue:
            current_key, depth = upstream_queue.pop(0)
            if depth >= upstream_depth:
                continue
            current_node = all_nodes.get(current_key, {})
            for dep_key in current_node.get('depends_on', {}).get('nodes', []):
                if dep_key not in upstream_visited and dep_key in all_nodes:
                    upstream_visited.add(dep_key)
                    dep_node = all_nodes[dep_key]
                    upstream.append(node_info(dep_key, dep_node))
                    edges.append({"source": dep_key, "target": current_key})
                    upstream_queue.append((dep_key, depth + 1))
        
        # BFS to get downstream
        downstream = []
        downstream_visited = set()
        downstream_queue = [(model_key, 0)]
        
        while downstream_queue:
            current_key, depth = downstream_queue.pop(0)
            if depth >= downstream_depth:
                continue
            for child_key in child_map.get(current_key, []):
                if child_key not in downstream_visited and child_key in all_nodes:
                    downstream_visited.add(child_key)
                    child_node = all_nodes[child_key]
                    downstream.append(node_info(child_key, child_node))
                    edges.append({"source": current_key, "target": child_key})
                    downstream_queue.append((child_key, depth + 1))
        
        return {
            "root": node_info(model_key, model_node),
            "upstream": upstream,
            "downstream": downstream,
            "edges": edges,
        }
    
    def get_impact_analysis(self, tenant_id: str, model_name: str) -> Dict[str, Any]:
        """
        Get impact analysis for a model - counts of downstream dependents.
        
        Args:
            tenant_id: Tenant identifier
            model_name: Name of the model
            
        Returns:
            Dictionary with affected counts and model names
        """
        lineage = self.get_lineage(
            tenant_id, model_name,
            upstream_depth=0,
            downstream_depth=10  # Deep traversal for impact
        )
        
        if "error" in lineage:
            return lineage
        
        downstream = lineage.get("downstream", [])
        
        models = [n for n in downstream if n.get("resource_type") == "model"]
        tests = [n for n in downstream if n.get("resource_type") == "test"]
        exposures = [n for n in downstream if n.get("resource_type") == "exposure"]
        
        return {
            "affected_models": len(models),
            "affected_tests": len(tests),
            "affected_exposures": len(exposures),
            "model_names": [m.get("name") for m in models[:10]],  # First 10 names
        }
    
    def _build_env(self, tenant_id: str, tenant_slug: Optional[str] = None) -> Dict[str, str]:
        """
        Build environment variables for dbt execution.
        
        Args:
            tenant_id: Tenant identifier
            tenant_slug: Optional tenant slug for database naming
            
        Returns:
            Environment dictionary
        """
        env = os.environ.copy()
        
        # Tenant context
        env['TENANT_ID'] = tenant_id
        
        # Get tenant slug for database name if not provided
        if tenant_slug:
            db_name = f'tenant_{tenant_slug}'
        else:
            # Try to fetch tenant slug from database
            try:
                from app.domains.tenants.domain.models import Tenant
                tenant = Tenant.query.filter(Tenant.id == tenant_id).first()
                if tenant:
                    db_name = f'tenant_{tenant.slug}'
                else:
                    db_name = f'tenant_{tenant_id}'
            except Exception:
                db_name = f'tenant_{tenant_id}'
        
        env['TENANT_DATABASE'] = db_name
        
        # ClickHouse connection (use existing env vars or defaults)
        if 'CLICKHOUSE_HOST' not in env:
            env['CLICKHOUSE_HOST'] = 'localhost'
        # dbt-clickhouse adapter speaks the HTTP protocol (port 8123 by
        # default), while the rest of the platform (clickhouse-driver) uses
        # the native protocol on port 9000. The container env typically sets
        # CLICKHOUSE_PORT=9000 for the app — we must override it here so dbt
        # connects on the HTTP port. Allow explicit DBT_CLICKHOUSE_PORT to
        # win if a deployment ever needs a custom HTTP port.
        env['CLICKHOUSE_PORT'] = env.get('DBT_CLICKHOUSE_PORT', '8123')
        if 'CLICKHOUSE_USER' not in env:
            env['CLICKHOUSE_USER'] = 'default'
        if 'CLICKHOUSE_PASSWORD' not in env:
            env['CLICKHOUSE_PASSWORD'] = ''
        
        # dbt target
        if 'DBT_TARGET' not in env:
            env['DBT_TARGET'] = 'dev'
        
        return env
    
    def _execute(self, cmd: List[str], tenant_id: str) -> DbtResult:
        """
        Execute dbt command with tenant context.
        
        Args:
            cmd: Command and arguments
            tenant_id: Tenant identifier
            
        Returns:
            DbtResult with execution details
        """
        env = self._build_env(tenant_id)
        full_cmd = ' '.join(cmd)
        
        logger.info(f"Executing dbt command: {full_cmd} for tenant: {tenant_id}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            
            dbt_result = DbtResult(
                success=result.returncode == 0,
                command=full_cmd,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
            
            # Try to load run_results.json if it exists
            run_results_path = self.project_path / 'target' / 'run_results.json'
            if run_results_path.exists():
                try:
                    with open(run_results_path, 'r') as f:
                        dbt_result.run_results = json.load(f)
                except json.JSONDecodeError:
                    pass
            
            if dbt_result.success:
                logger.info(f"dbt command succeeded: {full_cmd}")
            else:
                logger.warning(f"dbt command failed: {full_cmd}\n{result.stderr}")
            
            return dbt_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"dbt command timed out: {full_cmd}")
            return DbtResult(
                success=False,
                command=full_cmd,
                stdout="",
                stderr="Command timed out after 300 seconds",
                return_code=-1,
            )
        except Exception as e:
            logger.error(f"dbt command error: {full_cmd} - {str(e)}")
            return DbtResult(
                success=False,
                command=full_cmd,
                stdout="",
                stderr=str(e),
                return_code=-1,
            )

    # =========================================================================
    # Dual-Adapter Pattern Methods (Spark → dlt migration)
    # =========================================================================

    def run_lake(
        self,
        tenant_id: str,
        tenant_slug: str,
        select: Optional[str] = None,
        exclude: Optional[str] = None,
        full_refresh: bool = False,
        vars: Optional[Dict[str, Any]] = None,
    ) -> DbtResult:
        """
        Run dbt models against the Iceberg data lake using dbt-duckdb.
        
        This reads from Iceberg tables on S3 and produces intermediate
        tables (views, ephemeral models) used by the warehouse layer.
        
        Args:
            tenant_id: Tenant identifier
            tenant_slug: Tenant slug for S3 bucket and namespace resolution
            select: Model selection criteria (defaults to staging+intermediate)
            exclude: Models to exclude
            full_refresh: Force full refresh
            vars: Additional dbt variables
            
        Returns:
            DbtResult with execution details
        """
        cmd = ['dbt', 'run', '--target', 'lake']
        
        # Default to staging and intermediate layers for lake
        if select is None:
            select = "staging+ intermediate+"
        
        cmd.extend(['--select', select])
        
        if exclude:
            cmd.extend(['--exclude', exclude])
        if full_refresh:
            cmd.append('--full-refresh')
        if vars:
            cmd.extend(['--vars', json.dumps(vars)])
        
        return self._execute_lake(cmd, tenant_id, tenant_slug)

    def run_warehouse(
        self,
        tenant_id: str,
        tenant_slug: str,
        select: Optional[str] = None,
        exclude: Optional[str] = None,
        full_refresh: bool = False,
        vars: Optional[Dict[str, Any]] = None,
    ) -> DbtResult:
        """
        Run dbt models against ClickHouse warehouse using dbt-clickhouse.
        
        This reads from the lake layer (via dbt-duckdb refs) and produces
        materialized mart tables in ClickHouse for analytics queries.
        
        Args:
            tenant_id: Tenant identifier
            tenant_slug: Tenant slug for database naming
            select: Model selection criteria (defaults to marts)
            exclude: Models to exclude
            full_refresh: Force full refresh
            vars: Additional dbt variables
            
        Returns:
            DbtResult with execution details
        """
        cmd = ['dbt', 'run', '--target', 'warehouse']
        
        # Default to marts layer for warehouse
        if select is None:
            select = "marts+"
        
        cmd.extend(['--select', select])
        
        if exclude:
            cmd.extend(['--exclude', exclude])
        if full_refresh:
            cmd.append('--full-refresh')
        if vars:
            cmd.extend(['--vars', json.dumps(vars)])
        
        return self._execute_warehouse(cmd, tenant_id, tenant_slug)

    def _execute_lake(
        self,
        cmd: List[str],
        tenant_id: str,
        tenant_slug: str,
    ) -> DbtResult:
        """
        Execute dbt command for lake layer (dbt-duckdb).
        
        Injects S3/Iceberg environment variables.
        """
        env = self._build_lake_env(tenant_id, tenant_slug)
        full_cmd = ' '.join(cmd)
        
        logger.info(f"Executing dbt lake command: {full_cmd} for tenant: {tenant_slug}")
        
        return self._run_subprocess(cmd, env, full_cmd)

    def _execute_warehouse(
        self,
        cmd: List[str],
        tenant_id: str,
        tenant_slug: str,
    ) -> DbtResult:
        """
        Execute dbt command for warehouse layer (dbt-clickhouse).
        
        Injects ClickHouse environment variables.
        """
        env = self._build_warehouse_env(tenant_id, tenant_slug)
        full_cmd = ' '.join(cmd)
        
        logger.info(f"Executing dbt warehouse command: {full_cmd} for tenant: {tenant_slug}")
        
        return self._run_subprocess(cmd, env, full_cmd)

    def _build_lake_env(self, tenant_id: str, tenant_slug: str) -> Dict[str, str]:
        """
        Build environment variables for dbt-duckdb lake execution.
        
        Sets up S3 credentials and Iceberg configuration.
        """
        env = os.environ.copy()
        
        # Tenant context
        env['TENANT_ID'] = tenant_id
        env['TENANT_SLUG'] = tenant_slug
        env['DBT_TARGET'] = 'lake'
        
        # Iceberg namespace
        safe_slug = tenant_slug.lower().replace('-', '_').replace('.', '_')
        env['ICEBERG_NAMESPACE'] = f"tenant_{safe_slug}.raw"
        
        # Get S3 config for this tenant
        try:
            from app.domains.tenants.infrastructure.config_service import InfrastructureConfigService
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
                decrypted = service.decrypt_settings(settings, "object_storage")
                
                env['S3_BUCKET'] = decrypted.get("bucket", "")
                env['AWS_ACCESS_KEY_ID'] = decrypted.get("access_key", "")
                env['AWS_SECRET_ACCESS_KEY'] = decrypted.get("secret_key", "")
                env['S3_ENDPOINT_URL'] = decrypted.get("endpoint_url", "")
                env['AWS_REGION'] = decrypted.get("region", "us-east-1")
                
        except Exception as e:
            logger.warning(f"Could not load S3 config for lake env: {e}")
        
        # DuckDB settings
        env['DUCKDB_MEMORY_LIMIT'] = os.getenv('DUCKDB_MEMORY_LIMIT', '4GB')
        env['DUCKDB_THREADS'] = os.getenv('DUCKDB_THREADS', '4')
        
        return env

    def _build_warehouse_env(self, tenant_id: str, tenant_slug: str) -> Dict[str, str]:
        """
        Build environment variables for dbt-clickhouse warehouse execution.
        """
        # Start with the standard env builder
        env = self._build_env(tenant_id, tenant_slug)
        env['DBT_TARGET'] = 'warehouse'
        
        return env

    def _run_subprocess(
        self,
        cmd: List[str],
        env: Dict[str, str],
        full_cmd: str,
    ) -> DbtResult:
        """
        Run a subprocess and return DbtResult.
        
        Shared by both lake and warehouse execution paths.
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
            )
            
            dbt_result = DbtResult(
                success=result.returncode == 0,
                command=full_cmd,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )
            
            # Try to load run_results.json
            run_results_path = self.project_path / 'target' / 'run_results.json'
            if run_results_path.exists():
                try:
                    with open(run_results_path, 'r') as f:
                        dbt_result.run_results = json.load(f)
                except json.JSONDecodeError:
                    pass
            
            if dbt_result.success:
                logger.info(f"dbt command succeeded: {full_cmd}")
            else:
                logger.warning(f"dbt command failed: {full_cmd}\n{result.stderr}")
            
            return dbt_result
            
        except subprocess.TimeoutExpired:
            logger.error(f"dbt command timed out: {full_cmd}")
            return DbtResult(
                success=False,
                command=full_cmd,
                stdout="",
                stderr="Command timed out after 300 seconds",
                return_code=-1,
            )
        except Exception as e:
            logger.error(f"dbt command error: {full_cmd} - {str(e)}")
            return DbtResult(
                success=False,
                command=full_cmd,
                stdout="",
                stderr=str(e),
                return_code=-1,
            )


# Singleton instance
_dbt_service: Optional[DbtService] = None


def get_dbt_service(project_path: Optional[str] = None) -> DbtService:
    """
    Get or create the dbt service instance.
    
    Args:
        project_path: Optional path to dbt project
        
    Returns:
        DbtService instance
    """
    global _dbt_service
    if _dbt_service is None or project_path:
        _dbt_service = DbtService(project_path)
    return _dbt_service
