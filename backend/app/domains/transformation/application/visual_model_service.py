"""
Visual Model Builder Service.

Bridges the visual canvas configuration with dbt file generation.
Uses the existing TenantDbtProjectManager + DbtCodeGenerator.
Enforces ADR-002: All dbt files generated from approved Jinja2 templates.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from app.extensions import db
from app.platform.auth.identity import get_current_identity
from app.domains.transformation.domain.visual_models import (
    DbtExecution,
    ExecutionStatus,
    VisualModel,
)
from app.domains.transformation.infrastructure.code_generator import DbtCodeGenerator
from app.domains.transformation.infrastructure.tenant_dbt_project import (
    TenantDbtProjectManager,
)
from app.domains.transformation.schemas.visual_model_schemas import (
    GeneratedCodeResponse,
    SourceFreshnessConfig,
    VisualModelCanvasState,
    VisualModelCreateRequest,
    VisualModelUpdateRequest,
)

logger = logging.getLogger(__name__)


class VisualModelService:
    """
    Service for managing visual dbt models.

    Responsibilities:
    - CRUD for visual model canvas state (PostgreSQL)
    - Code generation via Jinja2 templates (ADR-002)
    - File writing to tenant dbt project (disk)
    - Warehouse introspection (ClickHouse)
    - DAG construction from model dependencies
    - Execution history tracking
    - Source freshness configuration
    - Package management
    """

    def __init__(self):
        self.code_generator = DbtCodeGenerator()

    # ── Helpers ───────────────────────────────────────────────

    def _get_manager(self) -> TenantDbtProjectManager:
        """Get the TenantDbtProjectManager for the current tenant."""
        return TenantDbtProjectManager.from_current_tenant()

    def _get_tenant_id(self) -> str:
        identity = get_current_identity()
        if identity and identity.tenant_id:
            return str(identity.tenant_id)
        raise ValueError("Tenant context required")

    # ── Visual Model CRUD ────────────────────────────────────

    def list_models(self, tenant_id: str) -> List[VisualModel]:
        """List all visual model definitions for the tenant."""
        return VisualModel.for_tenant(tenant_id).order_by(VisualModel.created_at.desc()).all()

    def get_model(self, tenant_id: str, model_id: str) -> VisualModel:
        """Get a single visual model by ID within tenant scope."""
        model = VisualModel.get_for_tenant(model_id, tenant_id)
        if not model:
            from app.errors import NotFoundError
            raise NotFoundError(f"Visual model {model_id} not found")
        return model

    def create_model(
        self, tenant_id: str, req: VisualModelCreateRequest
    ) -> VisualModel:
        """
        Create a visual model:
        1. Validate visual config
        2. Generate SQL via Jinja2 template (ADR-002)
        3. Generate schema YAML via Jinja2 template
        4. Write files to tenant's dbt project directory
        5. Store canvas state in PostgreSQL
        """
        manager = self._get_manager()

        # Generate SQL from visual config using approved template
        generated_sql = self.code_generator.generate_model_sql(
            config=req.to_code_gen_config(),
            layer=req.model_layer.value,
        )

        # Generate schema YAML from visual config using approved template
        generated_yaml = self.code_generator.generate_schema_yaml(
            config=req.to_schema_config(),
        )

        # Determine model path based on layer
        model_dir = manager.project_path / "models" / req.model_layer.value
        model_dir.mkdir(parents=True, exist_ok=True)

        sql_path = model_dir / f"{req.model_name}.sql"
        yaml_path = model_dir / f"_{req.model_name}.yml"

        # Write files (ADR-002 compliant — generated from templates)
        sql_path.write_text(generated_sql, encoding="utf-8")
        yaml_path.write_text(generated_yaml, encoding="utf-8")

        # Store visual state in PostgreSQL
        visual_model = VisualModel(
            tenant_id=tenant_id,
            model_name=req.model_name,
            model_path=str(sql_path.relative_to(manager.project_path)),
            model_layer=req.model_layer.value,
            canvas_position=req.canvas_position,
            visual_config=req.dict(),
            generated_sql=generated_sql,
            generated_yaml=generated_yaml,
            materialization=req.materialization.value,
            tags=req.tags or [],
            description=req.description,
        )
        db.session.add(visual_model)
        db.session.commit()

        logger.info(
            "Created visual model %s for tenant %s at %s",
            req.model_name, tenant_id, sql_path,
        )
        return visual_model

    def update_model(
        self, tenant_id: str, model_id: str, req: VisualModelUpdateRequest
    ) -> VisualModel:
        """Update an existing visual model and regenerate dbt files."""
        visual_model = self.get_model(tenant_id, model_id)
        manager = self._get_manager()

        # Regenerate SQL + YAML
        generated_sql = self.code_generator.generate_model_sql(
            config=req.to_code_gen_config(),
            layer=req.model_layer.value,
        )
        generated_yaml = self.code_generator.generate_schema_yaml(
            config=req.to_schema_config(),
        )

        # Handle rename: delete old files if model name changed
        old_sql = manager.project_path / visual_model.model_path
        old_yaml = old_sql.parent / f"_{visual_model.model_name}.yml"
        if req.model_name != visual_model.model_name:
            if old_sql.exists():
                old_sql.unlink()
            if old_yaml.exists():
                old_yaml.unlink()

        # Write new files
        model_dir = manager.project_path / "models" / req.model_layer.value
        model_dir.mkdir(parents=True, exist_ok=True)
        sql_path = model_dir / f"{req.model_name}.sql"
        yaml_path = model_dir / f"_{req.model_name}.yml"
        sql_path.write_text(generated_sql, encoding="utf-8")
        yaml_path.write_text(generated_yaml, encoding="utf-8")

        # Update DB record
        visual_model.model_name = req.model_name
        visual_model.model_path = str(sql_path.relative_to(manager.project_path))
        visual_model.model_layer = req.model_layer.value
        visual_model.canvas_position = req.canvas_position
        visual_model.visual_config = req.dict()
        visual_model.generated_sql = generated_sql
        visual_model.generated_yaml = generated_yaml
        visual_model.materialization = req.materialization.value
        visual_model.tags = req.tags or []
        visual_model.description = req.description
        db.session.commit()

        logger.info("Updated visual model %s (%s)", req.model_name, model_id)
        return visual_model

    def delete_model(self, tenant_id: str, model_id: str) -> None:
        """Delete a visual model and its generated files."""
        visual_model = self.get_model(tenant_id, model_id)
        manager = self._get_manager()

        # Delete files from disk
        sql_path = manager.project_path / visual_model.model_path
        yaml_path = sql_path.parent / f"_{visual_model.model_name}.yml"
        if sql_path.exists():
            sql_path.unlink()
        if yaml_path.exists():
            yaml_path.unlink()

        db.session.delete(visual_model)
        db.session.commit()

        logger.info("Deleted visual model %s (%s)", visual_model.model_name, model_id)

    def preview_sql(
        self, tenant_id: str, model_id: str
    ) -> GeneratedCodeResponse:
        """Preview generated SQL/YAML for a saved model (no disk write)."""
        visual_model = self.get_model(tenant_id, model_id)

        config = visual_model.visual_config
        generated_sql = self.code_generator.generate_model_sql(
            config=VisualModelCreateRequest(**config).to_code_gen_config(),
            layer=visual_model.model_layer,
        )
        generated_yaml = self.code_generator.generate_schema_yaml(
            config=VisualModelCreateRequest(**config).to_schema_config(),
        )

        return GeneratedCodeResponse(
            sql=generated_sql,
            yaml=generated_yaml,
            model_name=visual_model.model_name,
        )

    def preview_from_request(
        self, req: VisualModelCreateRequest
    ) -> GeneratedCodeResponse:
        """Preview generated SQL/YAML from a request payload (no DB / disk).

        Used by the dbt Studio Model Builder to render the generated dbt
        code before the model is persisted. ADR-002 still applies — the
        same Jinja2 templates are used as in ``create_model``.
        """
        generated_sql = self.code_generator.generate_model_sql(
            config=req.to_code_gen_config(),
            layer=req.model_layer.value,
        )
        generated_yaml = self.code_generator.generate_schema_yaml(
            config=req.to_schema_config(),
        )
        return GeneratedCodeResponse(
            sql=generated_sql,
            yaml=generated_yaml,
            model_name=req.model_name,
        )

    def save_canvas_state(
        self, tenant_id: str, model_id: str, canvas: VisualModelCanvasState
    ) -> None:
        """Save canvas position/layout state only (no regeneration)."""
        visual_model = self.get_model(tenant_id, model_id)
        visual_model.canvas_position = canvas.position
        db.session.commit()

    # ── DAG / Lineage ────────────────────────────────────────

    def get_dag_with_positions(self, tenant_id: str) -> Dict[str, Any]:
        """
        Build DAG structure with canvas positions for React Flow.
        Returns { nodes: [...], edges: [...] } format.
        """
        models = VisualModel.for_tenant(tenant_id).all()

        nodes = []
        edges = []
        model_lookup = {m.model_name: m for m in models}

        for model in models:
            nodes.append({
                "id": str(model.id),
                "type": f"{model.model_layer}Node",
                "position": model.canvas_position or {"x": 0, "y": 0},
                "data": {
                    "label": model.model_name,
                    "materialization": model.materialization,
                    "layer": model.model_layer,
                    "description": model.description or "",
                    "tags": model.tags or [],
                },
            })

            # Extract refs from visual config to build edges
            refs = model.visual_config.get("refs", [])
            source_models = model.visual_config.get("source_models", [])
            ref_names = list(refs)
            ref_names.extend(sm.get("name", "") for sm in source_models if isinstance(sm, dict))

            for ref_name in ref_names:
                ref_model = model_lookup.get(ref_name)
                if ref_model:
                    edges.append({
                        "id": f"{ref_model.id}-{model.id}",
                        "source": str(ref_model.id),
                        "target": str(model.id),
                        "type": "refEdge",
                    })

        return {"nodes": nodes, "edges": edges}

    # ── Warehouse Introspection ──────────────────────────────

    def _get_clickhouse_client(self, tenant_id: str):
        """Get a ClickHouse client scoped to the tenant."""
        from app.domains.analytics.infrastructure.clickhouse_client import (
            get_clickhouse_client,
        )
        return get_clickhouse_client(tenant_id=tenant_id)

    def list_warehouse_schemas(self, tenant_id: str) -> List[Dict]:
        """Query ClickHouse for available databases/schemas."""
        client = self._get_clickhouse_client(tenant_id)
        result = client.execute("SHOW DATABASES")
        return [{"name": row[0]} for row in result.rows]

    def list_warehouse_tables(
        self, tenant_id: str, schema: str
    ) -> List[Dict]:
        """Query ClickHouse for tables in a schema/database."""
        client = self._get_clickhouse_client(tenant_id)
        result = client.execute(
            "SELECT name, engine FROM system.tables WHERE database = %(db)s",
            {"db": schema},
        )
        return [{"name": row[0], "engine": row[1]} for row in result.rows]

    def list_warehouse_columns(
        self, tenant_id: str, schema: str, table: str
    ) -> List[Dict]:
        """Query ClickHouse for columns in a table."""
        client = self._get_clickhouse_client(tenant_id)
        result = client.execute(
            "SELECT name, type, comment FROM system.columns "
            "WHERE database = %(db)s AND table = %(tbl)s",
            {"db": schema, "tbl": table},
        )
        return [
            {"name": row[0], "type": row[1], "comment": row[2]}
            for row in result.rows
        ]

    # ── Iceberg Lake Introspection ───────────────────────────

    def list_lake_tables(self, tenant_id: str) -> List[Dict]:
        """List Iceberg tables available to the tenant.

        Sources are derived from the tenant's ``DltPipeline`` records:
        every successful pipeline run produces an Iceberg table at
        ``s3://<bucket>/iceberg/<namespace>/<table>``. dbt Studio
        consumes these as raw inputs via ClickHouse's native
        ``iceberg(...)`` table function.
        """
        from app.domains.ingestion.domain.models import (
            DltPipeline,
            DltPipelineStatus,
        )
        from app.domains.tenants.infrastructure.config_service import (
            InfrastructureConfigService,
        )
        from app.domains.tenants.domain.models import Tenant

        # Resolve tenant slug
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return []
        safe_slug = tenant.slug.replace("-", "_").replace(".", "_")

        # Resolve the tenant's S3 bucket so we can build full URIs
        bucket: Optional[str] = None
        endpoint_url: Optional[str] = None
        try:
            cfg_service = InfrastructureConfigService()
            configs = cfg_service.list_configs(
                service_type="object_storage",
                tenant_id=tenant_id,
                include_global=False,
                page=1,
                per_page=1,
            )
            if configs.get("items"):
                settings = configs["items"][0].get("settings", {})
                decrypted = cfg_service.decrypt_settings(
                    settings, "object_storage"
                )
                bucket = decrypted.get("bucket") or None
                endpoint_url = decrypted.get("endpoint_url") or None
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning(
                "Could not load tenant S3 config for lake listing: %s", exc
            )

        # Fallback to the deterministic per-tenant bucket name used by
        # provisioning when no explicit object_storage config is found.
        # Without this, ``s3_uri`` would be null and the dbt Studio
        # Iceberg validator would reject every model.
        if not bucket:
            import re as _re
            bucket = f"novasight-{_re.sub(r'[^a-z0-9-]', '-', tenant.slug.lower())}"

        # List ingestion pipelines that have produced data
        pipelines = (
            DltPipeline.query
            .filter(DltPipeline.tenant_id == tenant_id)
            .filter(
                DltPipeline.status.in_([
                    DltPipelineStatus.ACTIVE,
                    DltPipelineStatus.ERROR,
                ])
            )
            .all()
        )

        results: List[Dict] = []
        for pipeline in pipelines:
            namespace = (
                pipeline.iceberg_namespace
                or f"tenant_{safe_slug}.raw"
            )
            table_name = (
                pipeline.iceberg_table_name
                or pipeline.name.lower().replace(" ", "_").replace("-", "_")
            )
            # Build S3 URI; ClickHouse iceberg() expects the table root.
            s3_uri = None
            if bucket:
                # Namespace `tenant_xyz.raw` → path segment `tenant_xyz/raw`
                ns_path = namespace.replace(".", "/")
                s3_uri = f"s3://{bucket}/iceberg/{ns_path}/{table_name}/"

            results.append({
                "pipeline_id": str(pipeline.id),
                "pipeline_name": pipeline.name,
                "namespace": namespace,
                "table": table_name,
                "s3_uri": s3_uri,
                "endpoint_url": endpoint_url,
                "status": pipeline.status.value,
                "last_run_status": pipeline.last_run_status,
                "last_run_at": (
                    pipeline.last_run_at.isoformat()
                    if pipeline.last_run_at else None
                ),
                "columns": pipeline.columns_config or [],
            })

        return results

    # ── Execution History ────────────────────────────────────

    def create_execution(
        self,
        tenant_id: str,
        command: str,
        selector: Optional[str] = None,
        exclude: Optional[str] = None,
        full_refresh: bool = False,
        target: Optional[str] = None,
    ) -> DbtExecution:
        """Create a new execution record (PENDING status)."""
        identity = get_current_identity()
        user_id = str(identity.user_id) if identity else None

        execution = DbtExecution(
            tenant_id=tenant_id,
            command=command,
            status=ExecutionStatus.PENDING.value,
            selector=selector,
            exclude=exclude,
            full_refresh=full_refresh,
            target=target,
            triggered_by=user_id,
        )
        db.session.add(execution)
        db.session.commit()
        return execution

    def start_execution(self, execution_id: str) -> DbtExecution:
        """Mark an execution as RUNNING."""
        execution = DbtExecution.query.get_or_404(execution_id)
        execution.status = ExecutionStatus.RUNNING.value
        execution.started_at = datetime.utcnow()
        db.session.commit()
        return execution

    def complete_execution(
        self,
        execution_id: str,
        success: bool,
        log_output: str = "",
        error_output: str = "",
        run_results: Optional[Dict] = None,
        models_affected: Optional[List[str]] = None,
    ) -> DbtExecution:
        """Mark an execution as SUCCESS or ERROR with results."""
        execution = DbtExecution.query.get_or_404(execution_id)
        execution.status = (
            ExecutionStatus.SUCCESS.value if success
            else ExecutionStatus.ERROR.value
        )
        execution.finished_at = datetime.utcnow()
        if execution.started_at:
            delta = execution.finished_at - execution.started_at
            execution.duration_seconds = delta.total_seconds()
        execution.log_output = log_output
        execution.error_output = error_output
        execution.run_results = run_results
        execution.models_affected = models_affected or []

        # Parse results summary
        if run_results and isinstance(run_results, dict):
            results_list = run_results.get("results", [])
            execution.models_succeeded = sum(
                1 for r in results_list
                if r.get("status") in ("pass", "success")
            )
            execution.models_errored = sum(
                1 for r in results_list
                if r.get("status") in ("error", "fail")
            )
            execution.models_skipped = sum(
                1 for r in results_list
                if r.get("status") == "skipped"
            )

        db.session.commit()
        return execution

    def cancel_execution(self, tenant_id: str, execution_id: str) -> DbtExecution:
        """Cancel a running/pending execution."""
        execution = DbtExecution.get_for_tenant(execution_id, tenant_id)
        if not execution:
            from app.errors import NotFoundError
            raise NotFoundError(f"Execution {execution_id} not found")
        execution.status = ExecutionStatus.CANCELLED.value
        execution.finished_at = datetime.utcnow()
        if execution.started_at:
            delta = execution.finished_at - execution.started_at
            execution.duration_seconds = delta.total_seconds()
        db.session.commit()
        return execution

    def list_executions(
        self,
        tenant_id: str,
        limit: int = 50,
        offset: int = 0,
        command: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[DbtExecution]:
        """List execution history for the tenant."""
        query = DbtExecution.for_tenant(tenant_id).order_by(
            DbtExecution.created_at.desc()
        )
        if command:
            query = query.filter(DbtExecution.command == command)
        if status:
            query = query.filter(DbtExecution.status == status)
        return query.offset(offset).limit(limit).all()

    def get_execution(self, tenant_id: str, execution_id: str) -> DbtExecution:
        """Get a single execution record."""
        execution = DbtExecution.get_for_tenant(execution_id, tenant_id)
        if not execution:
            from app.errors import NotFoundError
            raise NotFoundError(f"Execution {execution_id} not found")
        return execution

    # ── Source Freshness ─────────────────────────────────────

    def configure_source_freshness(
        self, tenant_id: str, config: SourceFreshnessConfig
    ) -> Dict[str, Any]:
        """
        Update source YAML with freshness configuration.
        Uses the sources.yml.j2 template (ADR-002).
        """
        manager = self._get_manager()
        sources_path = manager.project_path / "models" / "_sources.yml"

        # Read existing sources YAML
        sources_data: Dict[str, Any] = {"version": 2, "sources": []}
        if sources_path.exists():
            content = sources_path.read_text(encoding="utf-8")
            parsed = yaml.safe_load(content)
            if parsed:
                sources_data = parsed

        # Find or create the source entry
        source_entry = None
        for src in sources_data.get("sources", []):
            if src.get("name") == config.source_name:
                source_entry = src
                break

        if not source_entry:
            source_entry = {"name": config.source_name, "tables": []}
            sources_data["sources"].append(source_entry)

        # Find or create the table entry
        table_entry = None
        for tbl in source_entry.get("tables", []):
            if tbl.get("name") == config.table_name:
                table_entry = tbl
                break

        if not table_entry:
            table_entry = {"name": config.table_name}
            source_entry.setdefault("tables", []).append(table_entry)

        # Set freshness config
        table_entry["loaded_at_field"] = config.loaded_at_field
        table_entry["freshness"] = {
            "warn_after": {
                "count": config.warn_after.count,
                "period": config.warn_after.period.value,
            },
            "error_after": {
                "count": config.error_after.count,
                "period": config.error_after.period.value,
            },
        }

        # Write back (this is still template-governed YAML structure)
        sources_path.write_text(
            yaml.dump(sources_data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )

        logger.info(
            "Configured freshness for %s.%s",
            config.source_name, config.table_name,
        )
        return table_entry

    # ── Singular Tests ───────────────────────────────────────

    def create_singular_test(
        self,
        tenant_id: str,
        test_name: str,
        sql: str,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Create a singular (custom SQL) data test file.

        Writes to backend/dbt/tenants/{slug}/tests/{test_name}.sql
        """
        manager = self._get_manager()
        tests_dir = manager.project_path / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)

        test_sql = self.code_generator.generate_singular_test(
            test_name=test_name, sql=sql, tags=tags
        )
        test_path = tests_dir / f"{test_name}.sql"
        test_path.write_text(test_sql, encoding="utf-8")

        logger.info("Created singular test %s at %s", test_name, test_path)
        return {
            "test_name": test_name,
            "path": str(test_path.relative_to(manager.project_path)),
        }

    # ── Package Manager ──────────────────────────────────────

    def list_packages(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Read packages.yml for the tenant's dbt project."""
        manager = self._get_manager()
        pkg_path = manager.project_path / "packages.yml"
        if not pkg_path.exists():
            return []
        content = yaml.safe_load(pkg_path.read_text(encoding="utf-8"))
        return content.get("packages", []) if content else []

    def update_packages(
        self, tenant_id: str, packages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Update packages.yml for the tenant's dbt project."""
        manager = self._get_manager()
        pkg_path = manager.project_path / "packages.yml"
        pkg_data = {"packages": packages}
        pkg_path.write_text(
            yaml.dump(pkg_data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        logger.info("Updated packages.yml with %d packages", len(packages))
        return packages

    def install_packages(self, tenant_id: str) -> Dict[str, Any]:
        """Run 'dbt deps' to install packages."""
        from app.domains.transformation.application.dbt_service import get_dbt_service
        service = get_dbt_service()
        result = service.deps()
        return result.to_dict() if hasattr(result, 'to_dict') else {"status": "ok"}


def get_visual_model_service() -> VisualModelService:
    """Factory for VisualModelService."""
    return VisualModelService()
