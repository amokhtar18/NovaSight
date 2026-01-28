"""
dbt API endpoints.

Provides REST API for dbt operations with multi-tenant support.
"""

from flask import g, jsonify, request
from flask_jwt_extended import jwt_required

from app.api.v1 import api_v1_bp
from app.decorators import require_roles, require_tenant_context
from app.services.dbt_service import get_dbt_service
from app.schemas.dbt_schemas import (
    DbtRunRequest,
    DbtTestRequest,
    DbtBuildRequest,
    DbtCompileRequest,
    DbtSeedRequest,
    DbtSnapshotRequest,
    DbtListRequest,
    DbtResultResponse,
    DbtLineageResponse,
)
from app.errors import ValidationError


def get_tenant_id() -> str:
    """Get current tenant ID from request context."""
    if hasattr(g, 'tenant_id') and g.tenant_id:
        return g.tenant_id
    raise ValidationError("Tenant context required", details={"field": "tenant_id"})


@api_v1_bp.route('/dbt/run', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_roles(['admin', 'data_engineer'])
def dbt_run_models():
    """
    Run dbt models.
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    requestBody:
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/DbtRunRequest'
    responses:
      200:
        description: dbt run result
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DbtResultResponse'
    """
    tenant_id = get_tenant_id()
    data = request.get_json() or {}
    
    req = DbtRunRequest(**data)
    dbt_service = get_dbt_service()
    
    result = dbt_service.run(
        tenant_id=tenant_id,
        select=req.select,
        exclude=req.exclude,
        full_refresh=req.full_refresh,
        vars=req.vars,
        target=req.target,
    )
    
    return jsonify(result.to_dict()), 200 if result.success else 500


@api_v1_bp.route('/dbt/test', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_roles(['admin', 'data_engineer'])
def dbt_run_tests():
    """
    Run dbt tests.
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    requestBody:
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/DbtTestRequest'
    responses:
      200:
        description: dbt test result
    """
    tenant_id = get_tenant_id()
    data = request.get_json() or {}
    
    req = DbtTestRequest(**data)
    dbt_service = get_dbt_service()
    
    result = dbt_service.test(
        tenant_id=tenant_id,
        select=req.select,
        exclude=req.exclude,
        store_failures=req.store_failures,
    )
    
    return jsonify(result.to_dict()), 200 if result.success else 500


@api_v1_bp.route('/dbt/build', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_roles(['admin', 'data_engineer'])
def dbt_build():
    """
    Run dbt build (run + test in DAG order).
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    requestBody:
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/DbtBuildRequest'
    responses:
      200:
        description: dbt build result
    """
    tenant_id = get_tenant_id()
    data = request.get_json() or {}
    
    req = DbtBuildRequest(**data)
    dbt_service = get_dbt_service()
    
    result = dbt_service.build(
        tenant_id=tenant_id,
        select=req.select,
        exclude=req.exclude,
        full_refresh=req.full_refresh,
    )
    
    return jsonify(result.to_dict()), 200 if result.success else 500


@api_v1_bp.route('/dbt/compile', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_roles(['admin', 'data_engineer', 'analyst'])
def dbt_compile_models():
    """
    Compile dbt models without executing.
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    requestBody:
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/DbtCompileRequest'
    responses:
      200:
        description: Compiled SQL
    """
    tenant_id = get_tenant_id()
    data = request.get_json() or {}
    
    req = DbtCompileRequest(**data)
    dbt_service = get_dbt_service()
    
    result = dbt_service.compile(
        tenant_id=tenant_id,
        select=req.select,
    )
    
    return jsonify(result.to_dict()), 200 if result.success else 500


@api_v1_bp.route('/dbt/seed', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_roles(['admin', 'data_engineer'])
def dbt_seed():
    """
    Load dbt seed data.
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    requestBody:
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/DbtSeedRequest'
    responses:
      200:
        description: Seed result
    """
    tenant_id = get_tenant_id()
    data = request.get_json() or {}
    
    req = DbtSeedRequest(**data)
    dbt_service = get_dbt_service()
    
    result = dbt_service.seed(
        tenant_id=tenant_id,
        select=req.select,
        full_refresh=req.full_refresh,
    )
    
    return jsonify(result.to_dict()), 200 if result.success else 500


@api_v1_bp.route('/dbt/snapshot', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_roles(['admin', 'data_engineer'])
def dbt_snapshot():
    """
    Run dbt snapshots (SCD Type 2).
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    requestBody:
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/DbtSnapshotRequest'
    responses:
      200:
        description: Snapshot result
    """
    tenant_id = get_tenant_id()
    data = request.get_json() or {}
    
    req = DbtSnapshotRequest(**data)
    dbt_service = get_dbt_service()
    
    result = dbt_service.snapshot(
        tenant_id=tenant_id,
        select=req.select,
    )
    
    return jsonify(result.to_dict()), 200 if result.success else 500


@api_v1_bp.route('/dbt/deps', methods=['POST'])
@jwt_required()
@require_roles(['admin'])
def dbt_install_deps():
    """
    Install dbt packages.
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    responses:
      200:
        description: Deps result
    """
    dbt_service = get_dbt_service()
    result = dbt_service.deps()
    
    return jsonify(result.to_dict()), 200 if result.success else 500


@api_v1_bp.route('/dbt/debug', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_roles(['admin', 'data_engineer', 'analyst'])
def dbt_debug():
    """
    Test dbt connection and configuration.
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    responses:
      200:
        description: Debug result
    """
    tenant_id = get_tenant_id()
    dbt_service = get_dbt_service()
    result = dbt_service.debug(tenant_id)
    
    # Parse debug output for structured response
    output = result.stdout.lower()
    response = {
        "success": result.success,
        "connection_ok": "connection ok" in output or "all checks passed" in output,
        "deps_ok": "dependencies" not in result.stderr.lower(),
        "config_ok": "config file" not in result.stderr.lower(),
        "details": result.stdout if result.success else result.stderr,
    }
    
    return jsonify(response), 200


@api_v1_bp.route('/dbt/docs/generate', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_roles(['admin', 'data_engineer', 'analyst'])
def dbt_generate_docs():
    """
    Generate dbt documentation.
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    responses:
      200:
        description: Docs generation result
    """
    tenant_id = get_tenant_id()
    dbt_service = get_dbt_service()
    result = dbt_service.docs_generate(tenant_id)
    
    return jsonify(result.to_dict()), 200 if result.success else 500


@api_v1_bp.route('/dbt/models', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_roles(['admin', 'data_engineer', 'analyst'])
def dbt_list_models():
    """
    List dbt models.
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    parameters:
      - name: select
        in: query
        schema:
          type: string
        description: Selection criteria
      - name: resource_type
        in: query
        schema:
          type: string
          default: model
        description: Resource type
    responses:
      200:
        description: List of models
    """
    tenant_id = get_tenant_id()
    select = request.args.get('select')
    resource_type = request.args.get('resource_type', 'model')
    
    dbt_service = get_dbt_service()
    result = dbt_service.list_models(
        tenant_id=tenant_id,
        select=select,
        resource_type=resource_type,
    )
    
    # Parse JSON output from dbt ls
    models = []
    if result.success and result.stdout:
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                try:
                    import json
                    models.append(json.loads(line))
                except json.JSONDecodeError:
                    # Plain text output
                    models.append({"name": line.strip()})
    
    return jsonify({
        "models": models,
        "count": len(models),
    }), 200


@api_v1_bp.route('/dbt/lineage/<model_name>', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_roles(['admin', 'data_engineer', 'analyst'])
def dbt_get_lineage(model_name: str):
    """
    Get lineage information for a model.
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    parameters:
      - name: model_name
        in: path
        required: true
        schema:
          type: string
        description: Model name
    responses:
      200:
        description: Model lineage
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/DbtLineageResponse'
    """
    tenant_id = get_tenant_id()
    dbt_service = get_dbt_service()
    
    lineage = dbt_service.get_lineage(tenant_id, model_name)
    
    if "error" in lineage:
        return jsonify(lineage), 404
    
    return jsonify(lineage), 200


@api_v1_bp.route('/dbt/parse', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_roles(['admin', 'data_engineer', 'analyst'])
def dbt_parse_project():
    """
    Parse dbt project and return manifest.
    
    ---
    tags:
      - dbt
    security:
      - BearerAuth: []
    responses:
      200:
        description: Parsed manifest
    """
    tenant_id = get_tenant_id()
    dbt_service = get_dbt_service()
    result = dbt_service.parse(tenant_id)
    
    return jsonify(result.to_dict()), 200 if result.success else 500
