"""
Visual Model Builder API endpoints.

CRUD for visual canvas state, code generation from visual config,
warehouse introspection, execution history, test builder, and package manager.

All routes extend the existing transformation domain under /api/v1/dbt/*.
"""

import logging
from flask import g, jsonify, request

from app.api.v1 import api_v1_bp
from app.platform.auth.decorators import authenticated, require_roles, tenant_required
from app.platform.auth.identity import get_current_identity
from app.domains.transformation.application.visual_model_service import (
    VisualModelService,
    get_visual_model_service,
)
from app.domains.transformation.schemas.visual_model_schemas import (
    DbtExecutionRequest,
    PackagesUpdateRequest,
    SingularTestCreateRequest,
    SourceFreshnessConfig,
    VisualModelCanvasState,
    VisualModelCreateRequest,
    VisualModelUpdateRequest,
)
from app.errors import ValidationError

logger = logging.getLogger(__name__)


def _get_tenant_id() -> str:
    """Extract tenant ID from request context."""
    identity = get_current_identity()
    if identity and identity.tenant_id:
        return str(identity.tenant_id)
    raise ValidationError("Tenant context required")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Visual Model CRUD
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@api_v1_bp.route('/dbt/visual-models', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
def list_visual_models():
    """List all visual model definitions for the tenant."""
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    models = service.list_models(tenant_id)
    return jsonify([m.to_dict() for m in models])


@api_v1_bp.route('/dbt/visual-models', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def create_visual_model_route():
    """
    Create a dbt model from visual builder configuration.

    1. Validates the visual config
    2. Generates SQL via Jinja2 template (ADR-002)
    3. Generates schema YAML via Jinja2 template
    4. Writes files to tenant's dbt project directory
    5. Stores canvas state in PostgreSQL
    """
    tenant_id = _get_tenant_id()
    data = request.get_json() or {}
    try:
        req = VisualModelCreateRequest(**data)
    except Exception as e:
        raise ValidationError(str(e))

    service = get_visual_model_service()
    result = service.create_model(tenant_id, req)
    return jsonify(result.to_dict()), 201


@api_v1_bp.route('/dbt/visual-models/<model_id>', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
def get_visual_model(model_id: str):
    """Get a single visual model by ID."""
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    model = service.get_model(tenant_id, model_id)
    return jsonify(model.to_dict())


@api_v1_bp.route('/dbt/visual-models/<model_id>', methods=['PUT'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def update_visual_model(model_id: str):
    """Update an existing visual model and regenerate dbt files."""
    tenant_id = _get_tenant_id()
    data = request.get_json() or {}
    try:
        req = VisualModelUpdateRequest(**data)
    except Exception as e:
        raise ValidationError(str(e))

    service = get_visual_model_service()
    result = service.update_model(tenant_id, model_id, req)
    return jsonify(result.to_dict())


@api_v1_bp.route('/dbt/visual-models/<model_id>', methods=['DELETE'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def delete_visual_model(model_id: str):
    """Delete a visual model and its generated files."""
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    service.delete_model(tenant_id, model_id)
    return jsonify({"status": "deleted"}), 200


@api_v1_bp.route('/dbt/visual-models/<model_id>/preview', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
def preview_visual_model(model_id: str):
    """Preview generated SQL without writing to disk."""
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    generated = service.preview_sql(tenant_id, model_id)
    return jsonify(generated.dict())


@api_v1_bp.route('/dbt/visual-models/preview', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
def preview_visual_model_from_payload():
    """Preview generated SQL/YAML for an in-progress (unsaved) model.

    The request body has the same shape as ``POST /visual-models``;
    nothing is persisted and no files are written. Used by the dbt
    Studio Model Builder to show the generated dbt code before the
    user clicks Save.
    """
    _ = _get_tenant_id()  # enforce tenant context
    data = request.get_json() or {}
    try:
        req = VisualModelCreateRequest(**data)
    except Exception as e:
        raise ValidationError(str(e))
    service = get_visual_model_service()
    generated = service.preview_from_request(req)
    return jsonify(generated.dict())


@api_v1_bp.route('/dbt/visual-models/<model_id>/canvas', methods=['PUT'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def save_canvas_state(model_id: str):
    """Save canvas position/layout state (no regeneration)."""
    tenant_id = _get_tenant_id()
    data = request.get_json() or {}
    try:
        canvas = VisualModelCanvasState(**data)
    except Exception as e:
        raise ValidationError(str(e))
    service = get_visual_model_service()
    service.save_canvas_state(tenant_id, model_id, canvas)
    return jsonify({"status": "saved"})


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# DAG / Lineage
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@api_v1_bp.route('/dbt/visual-models/dag', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
def get_visual_dag():
    """
    Get the full visual DAG with canvas positions for all models.
    Used by React Flow to render the interactive lineage graph.
    """
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    dag = service.get_dag_with_positions(tenant_id)
    return jsonify(dag)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Warehouse Introspection
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@api_v1_bp.route('/dbt/warehouse/schemas', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def list_warehouse_schemas():
    """List schemas/databases from the tenant's ClickHouse."""
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    schemas = service.list_warehouse_schemas(tenant_id)
    return jsonify(schemas)


@api_v1_bp.route('/dbt/warehouse/tables', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def list_warehouse_tables():
    """List tables in a schema from the tenant's ClickHouse database."""
    tenant_id = _get_tenant_id()
    schema = request.args.get('schema', 'default')
    service = get_visual_model_service()
    tables = service.list_warehouse_tables(tenant_id, schema)
    return jsonify(tables)


@api_v1_bp.route('/dbt/warehouse/columns', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def list_warehouse_columns():
    """List columns for a table from the tenant's ClickHouse database."""
    tenant_id = _get_tenant_id()
    schema = request.args.get('schema', 'default')
    table = request.args.get('table')
    if not table:
        raise ValidationError("'table' query parameter required")
    service = get_visual_model_service()
    columns = service.list_warehouse_columns(tenant_id, schema, table)
    return jsonify(columns)


@api_v1_bp.route('/dbt/lake/tables', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def list_lake_tables():
    """List Iceberg tables on the tenant's S3 lake.

    Each entry is a candidate source for dbt Studio staging models.
    Selecting one renders the model with a ClickHouse ``iceberg('s3://...')``
    table function reference; materialization always lands in the tenant's
    ClickHouse database.
    """
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    tables = service.list_lake_tables(tenant_id)
    return jsonify(tables)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Execution History
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@api_v1_bp.route('/dbt/executions', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
def list_dbt_executions():
    """List dbt execution history for the tenant."""
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    command = request.args.get('command')
    status = request.args.get('status')
    executions = service.list_executions(
        tenant_id, limit=limit, offset=offset,
        command=command, status=status,
    )
    return jsonify([e.to_dict() for e in executions])


@api_v1_bp.route('/dbt/executions/<exec_id>', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
def get_dbt_execution(exec_id: str):
    """Get a single dbt execution detail with logs."""
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    execution = service.get_execution(tenant_id, exec_id)
    return jsonify(execution.to_dict())


@api_v1_bp.route('/dbt/executions/<exec_id>', methods=['DELETE'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def cancel_dbt_execution(exec_id: str):
    """Cancel a running/pending dbt execution."""
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    execution = service.cancel_execution(tenant_id, exec_id)
    return jsonify(execution.to_dict())


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Test Builder
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@api_v1_bp.route('/dbt/tests/singular', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def create_singular_test():
    """Create a singular (custom SQL) data test."""
    tenant_id = _get_tenant_id()
    data = request.get_json() or {}
    try:
        req = SingularTestCreateRequest(**data)
    except Exception as e:
        raise ValidationError(str(e))

    service = get_visual_model_service()
    result = service.create_singular_test(
        tenant_id=tenant_id,
        test_name=req.test_name,
        sql=req.sql,
        description=req.description,
        tags=req.tags,
    )
    return jsonify(result), 201


@api_v1_bp.route('/dbt/tests/results', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
def get_test_results():
    """Get latest test results from the most recent dbt test execution."""
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    executions = service.list_executions(
        tenant_id, limit=1, command="test",
    )
    if not executions:
        return jsonify({"results": [], "total": 0})

    latest = executions[0]
    results = []
    if latest.run_results:
        for r in latest.run_results.get("results", []):
            results.append({
                "unique_id": r.get("unique_id", ""),
                "status": r.get("status", ""),
                "message": r.get("message", ""),
                "execution_time": r.get("execution_time", 0),
                "failures": r.get("failures"),
            })

    return jsonify({
        "results": results,
        "total": len(results),
        "execution_id": str(latest.id),
        "executed_at": latest.started_at.isoformat() if latest.started_at else None,
    })


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Source Freshness
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@api_v1_bp.route('/dbt/sources/<source_name>/freshness', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def configure_freshness(source_name: str):
    """Configure source freshness for a source table."""
    tenant_id = _get_tenant_id()
    data = request.get_json() or {}
    data["source_name"] = source_name
    try:
        config = SourceFreshnessConfig(**data)
    except Exception as e:
        raise ValidationError(str(e))

    service = get_visual_model_service()
    result = service.configure_source_freshness(tenant_id, config)
    return jsonify(result)


@api_v1_bp.route('/dbt/sources/freshness/run', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def run_freshness_check():
    """Run dbt source freshness check."""
    from app.domains.transformation.application.dbt_service import get_dbt_service
    dbt_service = get_dbt_service()
    # Use the existing dbt service infrastructure
    result = dbt_service._execute(["source", "freshness"])
    return jsonify(result.to_dict() if hasattr(result, 'to_dict') else {"status": "ok"})


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Package Manager
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@api_v1_bp.route('/dbt/packages', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def list_packages():
    """List installed dbt packages from packages.yml."""
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    packages = service.list_packages(tenant_id)
    return jsonify(packages)


@api_v1_bp.route('/dbt/packages', methods=['PUT'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def update_packages():
    """Update packages.yml with new package list."""
    tenant_id = _get_tenant_id()
    data = request.get_json() or {}
    try:
        req = PackagesUpdateRequest(**data)
    except Exception as e:
        raise ValidationError(str(e))

    service = get_visual_model_service()
    packages = service.update_packages(
        tenant_id, [p.dict(exclude_none=True) for p in req.packages]
    )
    return jsonify(packages)


@api_v1_bp.route('/dbt/packages/install', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def install_packages():
    """Run dbt deps to install packages."""
    tenant_id = _get_tenant_id()
    service = get_visual_model_service()
    result = service.install_packages(tenant_id)
    return jsonify(result)


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Log Streaming (Polling Fallback)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@api_v1_bp.route('/dbt/executions/<exec_id>/logs', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
def get_execution_logs(exec_id: str):
    """
    Get execution log lines since a given offset (polling fallback).

    Query params:
    - offset: int (default 0) â€” start from this line number
    """
    from app.domains.transformation.infrastructure.websocket_stream import (
        get_logs_since,
    )
    offset = request.args.get('offset', 0, type=int)
    lines = get_logs_since(exec_id, offset)
    return jsonify({
        "execution_id": exec_id,
        "lines": lines,
        "offset": offset,
        "next_offset": offset + len(lines),
    })


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Versioning & Optimistic Locking
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@api_v1_bp.route('/dbt/visual-models/<model_id>/versioned', methods=['PUT'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def update_model_versioned(model_id: str):
    """
    Update a visual model with optimistic locking.

    Requires `version` in the request body matching the current DB version.
    """
    from app.domains.transformation.application.versioning_service import get_versioning_service

    tenant_id = _get_tenant_id()
    data = request.get_json() or {}
    expected_version = data.pop("version", None)
    if expected_version is None:
        raise ValidationError("'version' field is required for versioned update")

    service = get_versioning_service()
    user_id = str(g.user.id) if hasattr(g, 'user') and g.user else None
    model = service.update_with_lock(
        tenant_id=tenant_id,
        model_id=model_id,
        expected_version=int(expected_version),
        updates=data,
        changed_by=user_id,
        change_summary=data.get("change_summary", ""),
    )
    return jsonify(model.to_dict())


@api_v1_bp.route('/dbt/visual-models/<model_id>/soft-delete', methods=['DELETE'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def soft_delete_model(model_id: str):
    """Soft-delete a visual model (recoverable)."""
    from app.domains.transformation.application.versioning_service import get_versioning_service

    tenant_id = _get_tenant_id()
    service = get_versioning_service()
    user_id = str(g.user.id) if hasattr(g, 'user') and g.user else None
    model = service.soft_delete(tenant_id, model_id, deleted_by=user_id)
    return jsonify({"id": str(model.id), "is_deleted": True, "version": model.version})


@api_v1_bp.route('/dbt/visual-models/<model_id>/restore', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def restore_model(model_id: str):
    """Restore a soft-deleted visual model."""
    from app.domains.transformation.application.versioning_service import get_versioning_service

    tenant_id = _get_tenant_id()
    service = get_versioning_service()
    user_id = str(g.user.id) if hasattr(g, 'user') and g.user else None
    model = service.restore(tenant_id, model_id, restored_by=user_id)
    return jsonify(model.to_dict())


@api_v1_bp.route('/dbt/visual-models/<model_id>/versions', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
def get_model_versions(model_id: str):
    """Get version history for a visual model."""
    from app.domains.transformation.application.versioning_service import get_versioning_service

    tenant_id = _get_tenant_id()
    limit = request.args.get('limit', 50, type=int)
    service = get_versioning_service()
    versions = service.get_version_history(tenant_id, model_id, limit=limit)
    return jsonify([v.to_dict() for v in versions])


@api_v1_bp.route('/dbt/visual-models/<model_id>/restore-version', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def restore_model_to_version(model_id: str):
    """Restore a visual model to a specific historical version."""
    from app.domains.transformation.application.versioning_service import get_versioning_service

    tenant_id = _get_tenant_id()
    data = request.get_json() or {}
    target_version = data.get("version")
    if target_version is None:
        raise ValidationError("'version' field is required")

    service = get_versioning_service()
    user_id = str(g.user.id) if hasattr(g, 'user') and g.user else None
    model = service.restore_to_version(
        tenant_id, model_id, int(target_version), restored_by=user_id,
    )
    return jsonify(model.to_dict())


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Bulk Operations
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@api_v1_bp.route('/dbt/visual-models/bulk/delete', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def bulk_delete_models():
    """Soft-delete multiple visual models in one call."""
    from app.domains.transformation.application.bulk_operations_service import get_bulk_operations_service

    tenant_id = _get_tenant_id()
    data = request.get_json() or {}
    model_ids = data.get("model_ids", [])
    if not model_ids:
        raise ValidationError("'model_ids' list is required")

    user_id = str(g.user.id) if hasattr(g, 'user') and g.user else None
    service = get_bulk_operations_service()
    result = service.bulk_delete(tenant_id, model_ids, deleted_by=user_id)
    return jsonify(result.to_dict())


@api_v1_bp.route('/dbt/visual-models/bulk/tags', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def bulk_update_tags():
    """Bulk update tags on multiple visual models."""
    from app.domains.transformation.application.bulk_operations_service import get_bulk_operations_service

    tenant_id = _get_tenant_id()
    data = request.get_json() or {}
    model_ids = data.get("model_ids", [])
    tags = data.get("tags", [])
    mode = data.get("mode", "replace")
    if not model_ids:
        raise ValidationError("'model_ids' list is required")

    service = get_bulk_operations_service()
    result = service.bulk_update_tags(tenant_id, model_ids, tags, mode=mode)
    return jsonify(result.to_dict())


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# Export / Import
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


@api_v1_bp.route('/dbt/visual-models/export', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def export_models():
    """Export visual models as a JSON package."""
    from app.domains.transformation.application.export_import_service import get_export_import_service

    tenant_id = _get_tenant_id()
    model_ids = request.args.getlist('model_ids')
    service = get_export_import_service()
    package = service.export_models(tenant_id, model_ids=model_ids or None)
    return jsonify(package)


@api_v1_bp.route('/dbt/visual-models/import', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def import_models():
    """Import visual models from an exported JSON package."""
    from app.domains.transformation.application.export_import_service import get_export_import_service

    tenant_id = _get_tenant_id()
    data = request.get_json()
    if not data:
        raise ValidationError("Request body must contain an export package")

    on_conflict = request.args.get('on_conflict', 'skip')
    service = get_export_import_service()
    result = service.import_models(tenant_id, data, on_conflict=on_conflict)
    return jsonify(result.to_dict()), 201
