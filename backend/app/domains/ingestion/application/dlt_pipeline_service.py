"""
NovaSight Ingestion Domain — dlt Pipeline Service
===================================================

Service layer for managing dlt pipelines: CRUD, code generation, execution.
"""

import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy import func

from app.extensions import db
from app.domains.ingestion.domain.models import (
    DltPipeline,
    DltPipelineStatus,
    WriteDisposition,
    SourceType,
    IncrementalCursorType,
    DltSourceKind,
)
from app.domains.ingestion.schemas.dlt_schemas import (
    DltPipelineCreate,
    DltPipelineUpdate,
    DltPipelinePreviewRequest,
)
from app.platform.lake.iceberg_catalog import get_tenant_namespace

logger = logging.getLogger(__name__)

# Template version for tracking
TEMPLATE_VERSION = "1.0.0"

# Path for generated pipeline files
DLT_PIPELINES_PATH = os.getenv("DLT_PIPELINES_PATH", "/opt/dlt/pipelines")


class DltPipelineServiceError(Exception):
    """Base exception for dlt pipeline service."""
    pass


class DltPipelineNotFoundError(DltPipelineServiceError):
    """Pipeline not found."""
    pass


class DltPipelineValidationError(DltPipelineServiceError):
    """Validation error."""
    pass


class DltPipelineService:
    """Service for managing dlt pipelines."""

    def __init__(self):
        self._template_engine = None

    @property
    def template_engine(self):
        """Lazy load template engine."""
        if self._template_engine is None:
            from app.services.template_engine import template_engine
            self._template_engine = template_engine()
        return self._template_engine

    # =========================================
    # CRUD Operations
    # =========================================

    def list_pipelines(
        self,
        tenant_id: UUID,
        status: Optional[str] = None,
        connection_id: Optional[UUID] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """
        List pipelines for a tenant.

        Args:
            tenant_id: Tenant UUID
            status: Filter by status
            connection_id: Filter by connection
            search: Search in name/description
            page: Page number
            per_page: Items per page

        Returns:
            Paginated pipeline list
        """
        query = DltPipeline.query.filter(DltPipeline.tenant_id == tenant_id)

        if status:
            try:
                status_enum = DltPipelineStatus(status)
                query = query.filter(DltPipeline.status == status_enum)
            except ValueError:
                pass

        if connection_id:
            query = query.filter(DltPipeline.connection_id == connection_id)

        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                db.or_(
                    DltPipeline.name.ilike(search_filter),
                    DltPipeline.description.ilike(search_filter),
                )
            )

        # Order by updated_at descending
        query = query.order_by(DltPipeline.updated_at.desc())

        # Paginate
        total = query.count()
        pages = (total + per_page - 1) // per_page
        items = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "items": [p.to_dict() for p in items],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }

    def get_pipeline(self, pipeline_id: UUID, tenant_id: UUID) -> DltPipeline:
        """
        Get a pipeline by ID.

        Args:
            pipeline_id: Pipeline UUID
            tenant_id: Tenant UUID (for ownership check)

        Returns:
            DltPipeline model

        Raises:
            DltPipelineNotFoundError: If pipeline not found
        """
        pipeline = DltPipeline.query.filter(
            DltPipeline.id == pipeline_id,
            DltPipeline.tenant_id == tenant_id,
        ).first()

        if not pipeline:
            raise DltPipelineNotFoundError(f"Pipeline {pipeline_id} not found")

        return pipeline

    def create_pipeline(
        self,
        tenant_id: UUID,
        user_id: UUID,
        data: DltPipelineCreate,
    ) -> DltPipeline:
        """
        Create a new pipeline.

        Args:
            tenant_id: Tenant UUID
            user_id: Creator user UUID
            data: Pipeline creation data

        Returns:
            Created DltPipeline model
        """
        # Get tenant slug for namespace
        from app.domains.tenants.domain.models import Tenant
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            raise DltPipelineValidationError("Tenant not found")

        # Auto-generate namespace and table name if not provided
        iceberg_namespace = data.iceberg_namespace or get_tenant_namespace(tenant.slug)

        is_file = data.source_kind == DltSourceKind.FILE.value
        # For file pipelines we derive the table name from the pipeline name
        # (or the uploaded file name) since there is no source table.
        default_table_seed = (
            data.iceberg_table_name
            or (None if is_file else data.source_table)
            or data.name
        )
        iceberg_table_name = data.iceberg_table_name or self._generate_table_name(
            default_table_seed
        )

        # Convert columns_config to dict
        columns_config = [col.model_dump() for col in data.columns_config]

        pipeline = DltPipeline(
            tenant_id=tenant_id,
            connection_id=data.connection_id if not is_file else None,
            name=data.name,
            description=data.description,
            status=DltPipelineStatus.DRAFT,
            source_kind=data.source_kind,
            source_type=SourceType(data.source_type),
            source_schema=data.source_schema,
            source_table=data.source_table,
            source_query=data.source_query,
            file_format=data.file_format if is_file else None,
            file_object_key=data.file_object_key if is_file else None,
            file_options=(data.file_options or {}) if is_file else {},
            columns_config=columns_config,
            primary_key_columns=data.primary_key_columns,
            incremental_cursor_column=data.incremental_cursor_column,
            incremental_cursor_type=IncrementalCursorType(data.incremental_cursor_type),
            write_disposition=WriteDisposition(data.write_disposition),
            partition_columns=data.partition_columns,
            iceberg_namespace=iceberg_namespace,
            iceberg_table_name=iceberg_table_name,
            options=data.options,
            created_by=user_id,
        )

        # Validate configuration
        errors = pipeline.validate_config()
        if errors:
            raise DltPipelineValidationError("; ".join(errors))

        db.session.add(pipeline)
        db.session.commit()

        logger.info(
            "Created dlt pipeline %s for tenant %s",
            pipeline.name,
            tenant.slug,
        )

        return pipeline

    def update_pipeline(
        self,
        pipeline_id: UUID,
        tenant_id: UUID,
        data: DltPipelineUpdate,
    ) -> DltPipeline:
        """
        Update a pipeline.

        Args:
            pipeline_id: Pipeline UUID
            tenant_id: Tenant UUID
            data: Update data

        Returns:
            Updated DltPipeline model
        """
        pipeline = self.get_pipeline(pipeline_id, tenant_id)

        # Update fields if provided
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if field == "columns_config" and value is not None:
                value = [col.model_dump() if hasattr(col, 'model_dump') else col for col in value]
            if field == "source_type" and value is not None:
                value = SourceType(value)
            if field == "write_disposition" and value is not None:
                value = WriteDisposition(value)
            if field == "incremental_cursor_type" and value is not None:
                value = IncrementalCursorType(value)

            setattr(pipeline, field, value)

        # Validate configuration
        errors = pipeline.validate_config()
        if errors:
            raise DltPipelineValidationError("; ".join(errors))

        # Clear generated code if config changed
        pipeline.generated_code = None
        pipeline.generated_code_hash = None
        pipeline.generated_at = None

        db.session.commit()

        logger.info("Updated dlt pipeline %s", pipeline.name)

        return pipeline

    def delete_pipeline(self, pipeline_id: UUID, tenant_id: UUID) -> None:
        """
        Delete a pipeline.

        Args:
            pipeline_id: Pipeline UUID
            tenant_id: Tenant UUID
        """
        pipeline = self.get_pipeline(pipeline_id, tenant_id)

        # Remove generated file if exists
        self._remove_generated_file(pipeline)

        db.session.delete(pipeline)
        db.session.commit()

        logger.info("Deleted dlt pipeline %s", pipeline_id)

    # =========================================
    # Code Generation
    # =========================================

    def generate_code(self, pipeline_id: UUID, tenant_id: UUID) -> str:
        """
        Generate pipeline code from template.

        Args:
            pipeline_id: Pipeline UUID
            tenant_id: Tenant UUID

        Returns:
            Generated code string
        """
        pipeline = self.get_pipeline(pipeline_id, tenant_id)
        code = self._render_pipeline_code(pipeline)

        # Store generated code
        pipeline.generated_code = code
        pipeline.generated_code_hash = hashlib.sha256(code.encode()).hexdigest()
        pipeline.generated_at = datetime.utcnow()
        pipeline.template_name = pipeline.get_template_name()
        pipeline.template_version = TEMPLATE_VERSION

        # Write to file
        self._write_generated_file(pipeline, code)

        db.session.commit()

        logger.info("Generated code for pipeline %s", pipeline.name)

        return code

    def preview_code(
        self,
        tenant_id: UUID,
        data: DltPipelinePreviewRequest,
    ) -> Tuple[str, List[str]]:
        """
        Preview generated code without saving.

        Args:
            tenant_id: Tenant UUID
            data: Preview request data

        Returns:
            Tuple of (code, validation_errors)
        """
        from app.domains.tenants.domain.models import Tenant
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            raise DltPipelineValidationError("Tenant not found")

        source_kind = data.source_kind or DltSourceKind.SQL.value
        is_file = source_kind == DltSourceKind.FILE.value

        # Build context
        context = self._build_template_context(
            tenant=tenant,
            pipeline_id="preview",
            pipeline_name="preview_pipeline",
            connection_id=data.connection_id if not is_file else None,
            source_kind=source_kind,
            source_type=data.source_type,
            source_schema=data.source_schema,
            source_table=data.source_table,
            source_query=data.source_query,
            file_format=data.file_format if is_file else None,
            file_object_key=data.file_object_key if is_file else None,
            file_options=(data.file_options or {}) if is_file else {},
            columns=[col.name for col in data.columns_config if col.include],
            primary_key_columns=data.primary_key_columns,
            incremental_cursor_column=data.incremental_cursor_column,
            write_disposition=data.write_disposition,
            iceberg_table_name=data.iceberg_table_name or self._generate_table_name(
                (data.source_table if not is_file else None) or "preview"
            ),
        )

        # Determine template
        if is_file:
            template_name = "dlt/file_pipeline.py.j2"
        elif data.write_disposition == "scd2":
            template_name = "dlt/scd2_pipeline.py.j2"
        elif data.write_disposition == "merge":
            template_name = "dlt/merge_pipeline.py.j2"
        else:
            template_name = "dlt/extract_pipeline.py.j2"

        # Render template
        code = self.template_engine.render(template_name, context)

        # Validate code
        errors = self._validate_generated_code(code, tenant.slug)

        return code, errors

    # =========================================
    # Status Management
    # =========================================

    def activate_pipeline(self, pipeline_id: UUID, tenant_id: UUID) -> DltPipeline:
        """
        Activate a pipeline (make it runnable).

        Args:
            pipeline_id: Pipeline UUID
            tenant_id: Tenant UUID

        Returns:
            Updated DltPipeline model
        """
        pipeline = self.get_pipeline(pipeline_id, tenant_id)

        # Generate code if not already generated
        if not pipeline.generated_code:
            self.generate_code(pipeline_id, tenant_id)
            pipeline = self.get_pipeline(pipeline_id, tenant_id)

        pipeline.status = DltPipelineStatus.ACTIVE
        db.session.commit()

        logger.info("Activated pipeline %s", pipeline.name)

        return pipeline

    def deactivate_pipeline(self, pipeline_id: UUID, tenant_id: UUID) -> DltPipeline:
        """
        Deactivate a pipeline.

        Args:
            pipeline_id: Pipeline UUID
            tenant_id: Tenant UUID

        Returns:
            Updated DltPipeline model
        """
        pipeline = self.get_pipeline(pipeline_id, tenant_id)
        pipeline.status = DltPipelineStatus.INACTIVE
        db.session.commit()

        logger.info("Deactivated pipeline %s", pipeline.name)

        return pipeline

    # =========================================
    # Execution
    # =========================================

    def run_now(self, pipeline_id: UUID, tenant_id: UUID) -> Dict[str, Any]:
        """
        Trigger immediate pipeline run via Dagster.

        Args:
            pipeline_id: Pipeline UUID
            tenant_id: Tenant UUID

        Returns:
            Run status dict
        """
        pipeline = self.get_pipeline(pipeline_id, tenant_id)

        # Allow runs for ACTIVE pipelines and for pipelines that previously
        # failed (ERROR). A manual/scheduled trigger is itself the user's
        # "retry" signal — they don't need to re-activate first.
        runnable_states = {DltPipelineStatus.ACTIVE, DltPipelineStatus.ERROR}
        if pipeline.status not in runnable_states:
            raise DltPipelineValidationError(
                f"Pipeline must be active to run (current status: "
                f"{pipeline.status.value}). Activate the pipeline first."
            )

        # Resolve tenant slug for script path lookup
        from app.domains.tenants.domain.models import Tenant
        tenant = Tenant.query.get(pipeline.tenant_id)
        if tenant is None:
            raise DltPipelineServiceError(f"Tenant {pipeline.tenant_id} not found")

        # Mark pipeline as running so the UI can show progress immediately
        pipeline.last_run_at = datetime.utcnow()
        pipeline.last_run_status = "running"
        db.session.commit()

        # Execute the generated script in a subprocess
        from app.domains.ingestion.application.dlt_runner import execute_pipeline_script
        timeout = int(os.getenv("DLT_RUN_TIMEOUT", "3600"))
        result = execute_pipeline_script(
            pipeline_id=str(pipeline.id),
            tenant_id=str(pipeline.tenant_id),
            tenant_slug=tenant.slug,
            pipeline_name=pipeline.name,
            timeout_seconds=timeout,
            logger=logger,
        )

        # Persist final run stats (also transitions status to ERROR on failure)
        self.update_run_stats(
            pipeline_id=pipeline.id,
            status=result["status"],
            rows=result.get("rows"),
            duration_ms=result.get("duration_ms"),
            iceberg_snapshot_id=result.get("iceberg_snapshot_id"),
        )

        return {
            "pipeline_id": str(pipeline.id),
            "run_id": None,
            "status": result["status"],
            "rows": result.get("rows"),
            "duration_ms": result.get("duration_ms"),
            "iceberg_snapshot_id": result.get("iceberg_snapshot_id"),
            "exit_code": result.get("exit_code"),
            "stdout_tail": result.get("stdout_tail", ""),
            "stderr_tail": result.get("stderr_tail", ""),
            "script_path": result.get("script_path"),
        }

    def update_run_stats(
        self,
        pipeline_id: UUID,
        status: str,
        rows: Optional[int] = None,
        duration_ms: Optional[int] = None,
        iceberg_snapshot_id: Optional[str] = None,
    ) -> None:
        """
        Update pipeline run statistics.

        Called by Dagster after pipeline execution.
        """
        pipeline = DltPipeline.query.get(pipeline_id)
        if not pipeline:
            logger.warning("Pipeline %s not found for stats update", pipeline_id)
            return

        pipeline.last_run_at = datetime.utcnow()
        pipeline.last_run_status = status
        pipeline.last_run_rows = rows
        pipeline.last_run_duration_ms = duration_ms
        pipeline.last_run_iceberg_snapshot_id = iceberg_snapshot_id

        if status == "error":
            pipeline.status = DltPipelineStatus.ERROR

        db.session.commit()

    # =========================================
    # Private Helpers
    # =========================================

    def _generate_table_name(self, source_name: str) -> str:
        """Generate a valid Iceberg table name from source name."""
        # Convert to lowercase, replace invalid chars with underscores
        name = re.sub(r'[^a-z0-9_]', '_', source_name.lower())
        # Ensure starts with letter
        if name and not name[0].isalpha():
            name = "t_" + name
        # Truncate if too long
        return name[:100]

    def _render_pipeline_code(self, pipeline: DltPipeline) -> str:
        """Render pipeline code from template."""
        from app.domains.tenants.domain.models import Tenant
        tenant = Tenant.query.get(pipeline.tenant_id)

        context = self._build_template_context(
            tenant=tenant,
            pipeline_id=str(pipeline.id),
            pipeline_name=pipeline.name,
            connection_id=pipeline.connection_id,
            source_kind=pipeline.source_kind or DltSourceKind.SQL.value,
            source_type=pipeline.source_type.value if pipeline.source_type else "table",
            source_schema=pipeline.source_schema,
            source_table=pipeline.source_table,
            source_query=pipeline.source_query,
            file_format=pipeline.file_format,
            file_object_key=pipeline.file_object_key,
            file_options=pipeline.file_options or {},
            columns=pipeline.get_column_names(),
            primary_key_columns=pipeline.primary_key_columns,
            incremental_cursor_column=pipeline.incremental_cursor_column,
            write_disposition=pipeline.write_disposition.value,
            iceberg_table_name=pipeline.iceberg_table_name,
        )

        template_name = pipeline.get_template_name()
        return self.template_engine.render(template_name, context)

    def _build_template_context(
        self,
        tenant,
        pipeline_id: str,
        pipeline_name: str,
        connection_id: Optional[UUID],
        source_kind: str = "sql",
        source_type: str = "table",
        source_schema: Optional[str] = None,
        source_table: Optional[str] = None,
        source_query: Optional[str] = None,
        file_format: Optional[str] = None,
        file_object_key: Optional[str] = None,
        file_options: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        primary_key_columns: Optional[List[str]] = None,
        incremental_cursor_column: Optional[str] = None,
        write_disposition: str = "append",
        iceberg_table_name: str = "",
    ) -> Dict[str, Any]:
        """Build template rendering context."""
        # Connection string is injected at runtime via the SOURCE_CONNECTION_STRING
        # environment variable. The default rendered into the generated code is
        # intentionally empty (a non-shell-expanding placeholder) so it does not
        # trip the template engine's injection-pattern security check.
        source_connection_string = ""

        # Get S3 config
        s3_config = self._get_tenant_s3_config(tenant.id)

        return {
            "tenant_id": str(tenant.id),
            "tenant_slug": tenant.slug,
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline_name,
            "generated_at": datetime.utcnow().isoformat(),
            # S3 / Iceberg config
            "s3_bucket": s3_config.get("bucket", f"tenant-{tenant.slug}"),
            "s3_endpoint_url": s3_config.get("endpoint_url", ""),
            "s3_region": s3_config.get("region", "us-east-1"),
            "iceberg_catalog_url": os.getenv(
                "ICEBERG_CATALOG_URL",
                "postgresql://novasight:novasight@postgres:5432/novasight_platform"
            ),
            "iceberg_namespace": get_tenant_namespace(tenant.slug),
            "iceberg_table_name": iceberg_table_name,
            # Source kind discriminator
            "source_kind": source_kind,
            # SQL-source config
            "source_connection_string": source_connection_string,
            "source_type": source_type,
            "source_schema": source_schema or "",
            "source_table": source_table or "",
            "source_query": source_query or "",
            # File-source config
            "file_format": file_format or "",
            "file_object_key": file_object_key or "",
            "file_options": file_options or {},
            # Column config
            "columns": columns or [],
            "primary_key_columns": primary_key_columns or [],
            "incremental_cursor_column": incremental_cursor_column,
            # Write config
            "write_disposition": write_disposition,
        }

    def _get_tenant_s3_config(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get S3 configuration for tenant."""
        try:
            from app.domains.tenants.infrastructure.config_service import InfrastructureConfigService
            service = InfrastructureConfigService()
            configs = service.list_configs(
                service_type="object_storage",
                tenant_id=str(tenant_id),
                include_global=False,
                page=1,
                per_page=1,
            )
            if configs.get("items"):
                return configs["items"][0].get("settings", {})
        except Exception as e:
            logger.warning("Could not get S3 config for tenant %s: %s", tenant_id, e)

        return {}

    def _validate_generated_code(self, code: str, tenant_slug: str) -> List[str]:
        """Validate generated code for security issues."""
        errors = []

        # Check namespace ownership. Tenant slugs may contain hyphens,
        # but Iceberg namespaces / Python identifiers use underscores
        # (see ``get_tenant_namespace``), so sanitize before matching.
        safe_slug = re.sub(r"[^a-z0-9_]", "_", tenant_slug.lower())
        expected_namespace = f"tenant_{safe_slug}"
        if expected_namespace not in code:
            errors.append(f"Generated code does not reference expected namespace {expected_namespace}")

        # Check for forbidden patterns
        forbidden_patterns = [
            (r'\bos\.system\b', "os.system() is not allowed"),
            (r'\bsubprocess\.(?!run\b)', "Only subprocess.run() is allowed"),
            (r'\beval\s*\(', "eval() is not allowed"),
            (r'\bexec\s*\(', "exec() is not allowed"),
            (r'\b__import__\s*\(', "__import__() is not allowed"),
            (r'AKIA[0-9A-Z]{16}', "Potential AWS access key detected"),
            (r'["\'][a-zA-Z0-9/+]{40}["\']', "Potential secret key detected"),
        ]

        for pattern, message in forbidden_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                errors.append(message)

        return errors

    def _write_generated_file(self, pipeline: DltPipeline, code: str) -> None:
        """Write generated pipeline to file."""
        from app.domains.tenants.domain.models import Tenant
        tenant = Tenant.query.get(pipeline.tenant_id)

        # Create directory structure
        tenant_dir = Path(DLT_PIPELINES_PATH) / tenant.slug
        tenant_dir.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path = tenant_dir / f"{pipeline.name}.py"
        file_path.write_text(code)

        logger.debug("Wrote pipeline code to %s", file_path)

    def _remove_generated_file(self, pipeline: DltPipeline) -> None:
        """Remove generated pipeline file."""
        from app.domains.tenants.domain.models import Tenant
        tenant = Tenant.query.get(pipeline.tenant_id)

        file_path = Path(DLT_PIPELINES_PATH) / tenant.slug / f"{pipeline.name}.py"
        if file_path.exists():
            file_path.unlink()
            logger.debug("Removed pipeline file %s", file_path)
