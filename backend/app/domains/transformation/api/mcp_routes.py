"""
dbt-MCP API endpoints.

Provides REST API for dbt-MCP server interactions including:
- Semantic layer queries
- Model introspection
- Lineage exploration
- Visual model building
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Dict

from flask import jsonify, request

from app.api.v1 import api_v1_bp
from app.platform.auth.decorators import authenticated, require_roles, tenant_required
from app.platform.auth.identity import get_current_identity
from app.errors import ValidationError, NovaSightException

from app.domains.transformation.infrastructure.dbt_mcp_adapter import (
    get_mcp_adapter,
    DbtMCPAdapter,
    MCPError,
    MCPConnectionError,
    MCPQueryError,
    MCPTimeoutError,
)
from app.domains.transformation.schemas.mcp_schemas import (
    MCPQueryRequest,
    MCPQueryResponse,
    MCPModelListRequest,
    MCPModelListResponse,
    MCPModelResponse,
    MCPMetricListRequest,
    MCPMetricListResponse,
    MCPDimensionListRequest,
    MCPDimensionListResponse,
    MCPLineageRequest,
    MCPLineageResponse,
    MCPLineageNode,
    MCPLineageEdge,
    MCPTestResultsResponse,
    VisualModelCreateRequest,
    VisualModelCreateResponse,
)

logger = logging.getLogger(__name__)


def get_tenant_id() -> str:
    """Get current tenant ID from request context."""
    identity = get_current_identity()
    if identity and identity.tenant_id:
        return identity.tenant_id
    raise ValidationError("Tenant context required", details={"field": "tenant_id"})


def run_async(coro):
    """Run an async coroutine in Flask sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def async_route(f):
    """Decorator to run async route handlers."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        return run_async(f(*args, **kwargs))
    return wrapper


def get_adapter() -> DbtMCPAdapter:
    """Get MCP adapter for current tenant."""
    tenant_id = get_tenant_id()
    return get_mcp_adapter(tenant_id)


# ============================================================================
# Semantic Layer Query Endpoints
# ============================================================================

@api_v1_bp.route('/dbt/mcp/query', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
@async_route
async def mcp_query():
    """
    Execute a semantic layer query via MCP.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/MCPQueryRequest'
    responses:
      200:
        description: Query results
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MCPQueryResponse'
      400:
        description: Invalid request
      500:
        description: Query execution failed
    """
    data = request.get_json() or {}
    
    try:
        req = MCPQueryRequest(**data)
    except Exception as e:
        raise ValidationError(f"Invalid request: {e}")
    
    adapter = get_adapter()
    
    try:
        # Ensure server is running
        if not adapter.is_running:
            await adapter.start()
        
        # Build filter dict from filter objects
        filters = None
        if req.filters:
            filters = {}
            for f in req.filters:
                if f.operator.value == '=':
                    filters[f.dimension] = f.value
                else:
                    filters[f.dimension] = {
                        'operator': f.operator.value,
                        'value': f.value
                    }
        
        if req.compile_only:
            # Just compile, don't execute
            compiled_sql = await adapter.compile_query(
                metrics=req.metrics,
                dimensions=req.dimensions,
                filters=filters,
            )
            
            response = MCPQueryResponse(
                success=True,
                compiled_sql=compiled_sql,
            )
        else:
            # Execute query
            result = await adapter.query_metrics(
                metrics=req.metrics,
                dimensions=req.dimensions,
                filters=filters,
                order_by=req.order_by,
                limit=req.limit,
            )
            
            response = MCPQueryResponse(
                success=result.success,
                data=result.data,
                columns=result.columns,
                row_count=result.row_count,
                query_id=result.query_id,
                compiled_sql=result.compiled_sql,
                execution_time_ms=result.execution_time_ms,
                error=result.error,
            )
        
        return jsonify(response.model_dump()), 200 if response.success else 400
        
    except MCPConnectionError as e:
        logger.error(f"MCP connection error: {e}")
        raise NovaSightException("MCP server connection failed", status_code=503)
    except MCPTimeoutError as e:
        logger.error(f"MCP timeout: {e}")
        raise NovaSightException("Query timed out", status_code=504)
    except MCPQueryError as e:
        logger.error(f"MCP query error: {e}")
        return jsonify(MCPQueryResponse(
            success=False,
            error=str(e)
        ).model_dump()), 400


@api_v1_bp.route('/dbt/mcp/compile', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
@async_route
async def mcp_compile_query():
    """
    Compile a semantic query to SQL without executing.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/MCPQueryRequest'
    responses:
      200:
        description: Compiled SQL
    """
    data = request.get_json() or {}
    
    try:
        req = MCPQueryRequest(**data)
    except Exception as e:
        raise ValidationError(f"Invalid request: {e}")
    
    adapter = get_adapter()
    
    try:
        if not adapter.is_running:
            await adapter.start()
        
        filters = None
        if req.filters:
            filters = {f.dimension: f.value for f in req.filters}
        
        compiled_sql = await adapter.compile_query(
            metrics=req.metrics,
            dimensions=req.dimensions,
            filters=filters,
        )
        
        return jsonify({
            "success": True,
            "compiled_sql": compiled_sql,
        }), 200
        
    except MCPError as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 400


# ============================================================================
# Model Introspection Endpoints
# ============================================================================

@api_v1_bp.route('/dbt/mcp/models', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
@async_route
async def mcp_list_models():
    """
    List all dbt models via MCP.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    parameters:
      - name: resource_type
        in: query
        schema:
          type: string
          enum: [model, source, seed, snapshot]
      - name: tags
        in: query
        schema:
          type: string
        description: Comma-separated tags to filter by
    responses:
      200:
        description: List of models
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MCPModelListResponse'
    """
    resource_type = request.args.get('resource_type')
    tags_str = request.args.get('tags')
    tags = tags_str.split(',') if tags_str else None
    
    adapter = get_adapter()
    
    try:
        if not adapter.is_running:
            await adapter.start()
        
        models = await adapter.list_models(
            resource_type=resource_type,
            tags=tags,
        )
        
        response = MCPModelListResponse(
            models=[
                MCPModelResponse(
                    name=m.name,
                    unique_id=m.unique_id,
                    resource_type=m.resource_type,
                    description=m.description,
                    schema_name=m.schema_name,
                    database=m.database,
                    materialization=m.materialization,
                    depends_on=m.depends_on,
                    tags=m.tags,
                    meta=m.meta,
                )
                for m in models
            ],
            total_count=len(models),
        )
        
        return jsonify(response.model_dump()), 200
        
    except MCPError as e:
        logger.error(f"Error listing models: {e}")
        raise NovaSightException(f"Failed to list models: {e}")


@api_v1_bp.route('/dbt/mcp/models/<path:model_name>', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
@async_route
async def mcp_get_model(model_name: str):
    """
    Get detailed model information via MCP.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    parameters:
      - name: model_name
        in: path
        required: true
        schema:
          type: string
        description: Model name or unique_id
    responses:
      200:
        description: Model details
      404:
        description: Model not found
    """
    adapter = get_adapter()
    
    try:
        if not adapter.is_running:
            await adapter.start()
        
        model = await adapter.get_model(model_name)
        
        if not model:
            raise NovaSightException(f"Model '{model_name}' not found", status_code=404)
        
        response = MCPModelResponse(
            name=model.name,
            unique_id=model.unique_id,
            resource_type=model.resource_type,
            description=model.description,
            schema_name=model.schema_name,
            database=model.database,
            materialization=model.materialization,
            depends_on=model.depends_on,
            tags=model.tags,
            meta=model.meta,
        )
        
        return jsonify(response.model_dump()), 200
        
    except MCPError as e:
        logger.error(f"Error getting model: {e}")
        raise NovaSightException(f"Failed to get model: {e}")


@api_v1_bp.route('/dbt/mcp/models/<path:model_name>/sql', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
@async_route
async def mcp_get_model_sql(model_name: str):
    """
    Get compiled SQL for a model.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    parameters:
      - name: model_name
        in: path
        required: true
        schema:
          type: string
    responses:
      200:
        description: Compiled SQL
    """
    adapter = get_adapter()
    
    try:
        if not adapter.is_running:
            await adapter.start()
        
        sql = await adapter.get_model_sql(model_name)
        
        if sql is None:
            raise NovaSightException(f"Model '{model_name}' not found", status_code=404)
        
        return jsonify({
            "model_name": model_name,
            "sql": sql,
        }), 200
        
    except MCPError as e:
        logger.error(f"Error getting model SQL: {e}")
        raise NovaSightException(f"Failed to get model SQL: {e}")


# ============================================================================
# Semantic Layer Metadata Endpoints
# ============================================================================

@api_v1_bp.route('/dbt/mcp/metrics', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
@async_route
async def mcp_list_metrics():
    """
    List semantic layer metrics.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    responses:
      200:
        description: List of metrics
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MCPMetricListResponse'
    """
    adapter = get_adapter()
    
    try:
        if not adapter.is_running:
            await adapter.start()
        
        metrics = await adapter.list_metrics()
        
        response = MCPMetricListResponse(
            metrics=[
                {
                    "name": m.name,
                    "unique_id": m.unique_id,
                    "description": m.description,
                    "type": m.type,
                    "type_params": m.type_params,
                    "filter": m.filter,
                    "dimensions": m.dimensions,
                }
                for m in metrics
            ]
        )
        
        return jsonify(response.model_dump()), 200
        
    except MCPError as e:
        logger.error(f"Error listing metrics: {e}")
        raise NovaSightException(f"Failed to list metrics: {e}")


@api_v1_bp.route('/dbt/mcp/dimensions', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
@async_route
async def mcp_list_dimensions():
    """
    List semantic layer dimensions.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    parameters:
      - name: metric
        in: query
        schema:
          type: string
        description: Filter dimensions for a specific metric
    responses:
      200:
        description: List of dimensions
    """
    metric_name = request.args.get('metric')
    
    adapter = get_adapter()
    
    try:
        if not adapter.is_running:
            await adapter.start()
        
        dimensions = await adapter.list_dimensions(metric_name)
        
        response = MCPDimensionListResponse(
            dimensions=[
                {
                    "name": d.name,
                    "unique_id": d.unique_id,
                    "description": d.description,
                    "type": d.type,
                    "expr": d.expr,
                    "is_partition": d.is_partition,
                }
                for d in dimensions
            ]
        )
        
        return jsonify(response.model_dump()), 200
        
    except MCPError as e:
        logger.error(f"Error listing dimensions: {e}")
        raise NovaSightException(f"Failed to list dimensions: {e}")


# ============================================================================
# Lineage Endpoints
# ============================================================================

@api_v1_bp.route('/dbt/mcp/lineage/<path:model_name>', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
@async_route
async def mcp_get_lineage(model_name: str):
    """
    Get lineage graph for a model.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    parameters:
      - name: model_name
        in: path
        required: true
        schema:
          type: string
      - name: upstream
        in: query
        schema:
          type: boolean
          default: true
      - name: downstream
        in: query
        schema:
          type: boolean
          default: true
      - name: depth
        in: query
        schema:
          type: integer
          default: 10
    responses:
      200:
        description: Lineage graph
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MCPLineageResponse'
    """
    upstream = request.args.get('upstream', 'true').lower() == 'true'
    downstream = request.args.get('downstream', 'true').lower() == 'true'
    depth = int(request.args.get('depth', 10))
    
    adapter = get_adapter()
    
    try:
        if not adapter.is_running:
            await adapter.start()
        
        lineage = await adapter.get_lineage(
            model_name=model_name,
            upstream=upstream,
            downstream=downstream,
            depth=depth,
        )
        
        # Determine layer from model name/schema
        def get_layer(node):
            if 'staging' in node.name or node.name.startswith('stg_'):
                return 'staging'
            elif 'intermediate' in node.name or node.name.startswith('int_'):
                return 'intermediate'
            elif 'marts' in node.schema_name or node.name.startswith('fct_') or node.name.startswith('dim_'):
                return 'marts'
            return None
        
        response = MCPLineageResponse(
            nodes=[
                MCPLineageNode(
                    unique_id=n.unique_id,
                    name=n.name,
                    resource_type=n.resource_type,
                    package_name=n.package_name,
                    schema_name=n.schema_name,
                    database=n.database,
                    layer=get_layer(n),
                )
                for n in lineage.nodes
            ],
            edges=[
                MCPLineageEdge(source=e['source'], target=e['target'])
                for e in lineage.edges
            ],
            root_model=model_name,
        )
        
        return jsonify(response.model_dump()), 200
        
    except MCPError as e:
        logger.error(f"Error getting lineage: {e}")
        raise NovaSightException(f"Failed to get lineage: {e}")


@api_v1_bp.route('/dbt/mcp/lineage', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
@async_route
async def mcp_get_full_dag():
    """
    Get the complete project DAG.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    responses:
      200:
        description: Full project lineage graph
    """
    adapter = get_adapter()
    
    try:
        if not adapter.is_running:
            await adapter.start()
        
        lineage = await adapter.get_full_dag()
        
        def get_layer(node):
            if 'staging' in node.name or node.name.startswith('stg_'):
                return 'staging'
            elif 'intermediate' in node.name or node.name.startswith('int_'):
                return 'intermediate'
            elif 'marts' in node.schema_name or node.name.startswith('fct_') or node.name.startswith('dim_'):
                return 'marts'
            return None
        
        response = MCPLineageResponse(
            nodes=[
                MCPLineageNode(
                    unique_id=n.unique_id,
                    name=n.name,
                    resource_type=n.resource_type,
                    package_name=n.package_name,
                    schema_name=n.schema_name,
                    database=n.database,
                    layer=get_layer(n),
                )
                for n in lineage.nodes
            ],
            edges=[
                MCPLineageEdge(source=e['source'], target=e['target'])
                for e in lineage.edges
            ],
        )
        
        return jsonify(response.model_dump()), 200
        
    except MCPError as e:
        logger.error(f"Error getting DAG: {e}")
        raise NovaSightException(f"Failed to get DAG: {e}")


# ============================================================================
# Test Results Endpoints
# ============================================================================

@api_v1_bp.route('/dbt/mcp/tests', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
@async_route
async def mcp_list_tests():
    """
    List dbt tests.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    parameters:
      - name: model
        in: query
        schema:
          type: string
        description: Filter tests for a specific model
    responses:
      200:
        description: List of tests
    """
    model_name = request.args.get('model')
    
    adapter = get_adapter()
    
    try:
        if not adapter.is_running:
            await adapter.start()
        
        tests = await adapter.list_tests(model_name)
        
        return jsonify({
            "tests": tests,
            "total_count": len(tests),
        }), 200
        
    except MCPError as e:
        logger.error(f"Error listing tests: {e}")
        raise NovaSightException(f"Failed to list tests: {e}")


@api_v1_bp.route('/dbt/mcp/tests/results', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer', 'analyst'])
@async_route
async def mcp_get_test_results():
    """
    Get latest test results.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    parameters:
      - name: model
        in: query
        schema:
          type: string
        description: Filter results for a specific model
    responses:
      200:
        description: Test results
    """
    model_name = request.args.get('model')
    
    adapter = get_adapter()
    
    try:
        if not adapter.is_running:
            await adapter.start()
        
        results = await adapter.get_test_results(model_name)
        
        # Calculate summary
        passed = sum(1 for r in results if r.get('status') == 'pass')
        failed = sum(1 for r in results if r.get('status') == 'fail')
        warned = sum(1 for r in results if r.get('status') == 'warn')
        errored = sum(1 for r in results if r.get('status') == 'error')
        skipped = sum(1 for r in results if r.get('status') == 'skipped')
        
        response = MCPTestResultsResponse(
            results=[
                {
                    "unique_id": r.get('unique_id', ''),
                    "name": r.get('name', ''),
                    "status": r.get('status', ''),
                    "execution_time": r.get('execution_time'),
                    "failures": r.get('failures'),
                    "message": r.get('message'),
                    "model": r.get('model'),
                    "column": r.get('column'),
                }
                for r in results
            ],
            total_tests=len(results),
            passed=passed,
            failed=failed,
            warned=warned,
            errored=errored,
            skipped=skipped,
        )
        
        return jsonify(response.model_dump()), 200
        
    except MCPError as e:
        logger.error(f"Error getting test results: {e}")
        raise NovaSightException(f"Failed to get test results: {e}")


# ============================================================================
# Visual Model Builder Endpoints
# ============================================================================

@api_v1_bp.route('/dbt/mcp/visual-models', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def create_visual_model():
    """
    Create a dbt model from visual definition.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/VisualModelCreateRequest'
    responses:
      200:
        description: Model created
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/VisualModelCreateResponse'
      400:
        description: Validation failed
    """
    from app.domains.transformation.infrastructure.dbt_model_generator import (
        DbtModelGenerator,
        ModelGenerationError,
    )
    from app.services.template_engine import template_engine
    
    data = request.get_json() or {}
    
    try:
        req = VisualModelCreateRequest(**data)
    except Exception as e:
        raise ValidationError(f"Invalid request: {e}")
    
    definition = req.definition
    
    # Build SQL from visual definition
    try:
        sql_parts = []
        
        # Config block
        config_parts = [f"materialized='{definition.materialization}'"]
        if definition.tags:
            config_parts.append(f"tags={definition.tags}")
        sql_parts.append(f"{{{{ config({', '.join(config_parts)}) }}}}")
        sql_parts.append("")
        
        # CTEs for sources
        ctes = []
        for i, source in enumerate(definition.sources):
            alias = source.alias or source.table_name
            ctes.append(f"{alias} as (\n    select * from {{{{ source('{source.source_name}', '{source.table_name}') }}}}\n)")
        
        if ctes:
            sql_parts.append("with " + ",\n\n".join(ctes))
            sql_parts.append("")
        
        # Main SELECT
        select_columns = []
        for col in definition.columns:
            if col.expression:
                select_columns.append(f"    {col.expression} as {col.target_column or col.source_column}")
            elif col.data_type:
                select_columns.append(f"    cast({col.source_column} as {col.data_type}) as {col.target_column or col.source_column}")
            elif col.target_column and col.target_column != col.source_column:
                select_columns.append(f"    {col.source_column} as {col.target_column}")
            else:
                select_columns.append(f"    {col.source_column}")
        
        # Aggregations
        if definition.aggregations:
            for agg in definition.aggregations:
                select_columns.append(f"    {agg.function.value}({agg.column}) as {agg.alias}")
        
        sql_parts.append("select")
        sql_parts.append(",\n".join(select_columns))
        
        # FROM clause
        first_source = definition.sources[0]
        from_table = first_source.alias or first_source.table_name
        sql_parts.append(f"from {from_table}")
        
        # JOINs
        if definition.joins:
            for join in definition.joins:
                sql_parts.append(
                    f"{join.join_type} join {join.right_table} "
                    f"on {join.left_table}.{join.left_column} = {join.right_table}.{join.right_column}"
                )
                if join.additional_conditions:
                    sql_parts.append(f"    and {join.additional_conditions}")
        
        # WHERE
        if definition.where_clause:
            sql_parts.append(f"where {definition.where_clause}")
        
        # GROUP BY
        if definition.group_by:
            sql_parts.append(f"group by {', '.join(definition.group_by)}")
        
        # HAVING
        if definition.having_clause:
            sql_parts.append(f"having {definition.having_clause}")
        
        # ORDER BY
        if definition.order_by:
            sql_parts.append(f"order by {', '.join(definition.order_by)}")
        
        generated_sql = "\n".join(sql_parts)
        
        # Generate schema YAML if requested
        schema_yaml = None
        if req.generate_schema:
            schema_parts = [
                "version: 2",
                "",
                "models:",
                f"  - name: {definition.name}",
            ]
            if definition.description:
                schema_parts.append(f"    description: \"{definition.description}\"")
            
            schema_parts.append("    columns:")
            for col in definition.columns:
                col_name = col.target_column or col.source_column
                schema_parts.append(f"      - name: {col_name}")
                if col.description:
                    schema_parts.append(f"        description: \"{col.description}\"")
                if col.tests:
                    schema_parts.append("        tests:")
                    for test in col.tests:
                        schema_parts.append(f"          - {test}")
            
            schema_yaml = "\n".join(schema_parts)
        
        # Validate only - don't write files
        if req.validate_only:
            return jsonify(VisualModelCreateResponse(
                success=True,
                model_name=definition.name,
                generated_sql=generated_sql,
                schema_yaml=schema_yaml,
            ).model_dump()), 200
        
        # Write files to dbt project
        from flask import current_app
        from pathlib import Path
        
        dbt_path = Path(current_app.config.get('DBT_PROJECT_PATH', './dbt'))
        
        # Determine model directory based on layer
        layer_dir = dbt_path / 'models' / definition.layer
        layer_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = layer_dir / f"{definition.name}.sql"
        schema_path = layer_dir / f"{definition.name}.yml" if schema_yaml else None
        
        model_path.write_text(generated_sql, encoding='utf-8')
        if schema_path and schema_yaml:
            schema_path.write_text(schema_yaml, encoding='utf-8')
        
        return jsonify(VisualModelCreateResponse(
            success=True,
            model_name=definition.name,
            model_path=str(model_path),
            schema_path=str(schema_path) if schema_path else None,
            generated_sql=generated_sql,
            schema_yaml=schema_yaml,
        ).model_dump()), 200
        
    except Exception as e:
        logger.error(f"Error creating visual model: {e}")
        return jsonify(VisualModelCreateResponse(
            success=False,
            model_name=definition.name,
            generated_sql="",
            validation_errors=[str(e)],
        ).model_dump()), 400


# ============================================================================
# Server Management Endpoints
# ============================================================================

@api_v1_bp.route('/dbt/mcp/status', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def mcp_server_status():
    """
    Get MCP server status.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    responses:
      200:
        description: Server status
    """
    adapter = get_adapter()
    
    return jsonify({
        "status": adapter.state.value,
        "is_running": adapter.is_running,
        "project_path": str(adapter.project_path),
        "target": adapter.target,
    }), 200


@api_v1_bp.route('/dbt/mcp/start', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
@async_route
async def mcp_start_server():
    """
    Start the MCP server.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    responses:
      200:
        description: Server started
    """
    adapter = get_adapter()
    
    try:
        await adapter.start()
        return jsonify({
            "success": True,
            "status": adapter.state.value,
        }), 200
    except MCPConnectionError as e:
        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


@api_v1_bp.route('/dbt/mcp/stop', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin'])
@async_route
async def mcp_stop_server():
    """
    Stop the MCP server.
    
    ---
    tags:
      - dbt-mcp
    security:
      - BearerAuth: []
    responses:
      200:
        description: Server stopped
    """
    adapter = get_adapter()
    
    await adapter.stop()
    
    return jsonify({
        "success": True,
        "status": adapter.state.value,
    }), 200


# ============================================================================
# Tenant dbt Project Management Endpoints
# ============================================================================

@api_v1_bp.route('/dbt/project/structure', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['super_admin', 'tenant_admin', 'data_engineer'])
def get_project_structure():
    """
    Get the tenant's dbt project structure.
    
    Returns the complete file tree of the tenant's dbt project.
    Super admins and developers can view generated models and configurations.
    
    ---
    tags:
      - dbt-project
    security:
      - BearerAuth: []
    responses:
      200:
        description: Project structure
    """
    from app.domains.transformation.infrastructure.tenant_dbt_project import (
        get_tenant_project_manager,
        TenantDbtProjectError,
    )
    
    try:
        manager = get_tenant_project_manager()
        manager.ensure_project_exists()
        structure = manager.get_project_structure()
        
        return jsonify(structure), 200
        
    except TenantDbtProjectError as e:
        logger.error(f"Error getting project structure: {e}")
        raise NovaSightException(f"Failed to get project structure: {e}")


@api_v1_bp.route('/dbt/project/file', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['super_admin', 'tenant_admin', 'data_engineer'])
def get_project_file():
    """
    Get content of a file from tenant's dbt project.
    
    ---
    tags:
      - dbt-project
    security:
      - BearerAuth: []
    parameters:
      - name: path
        in: query
        required: true
        schema:
          type: string
        description: Relative path to file within project
    responses:
      200:
        description: File content
      404:
        description: File not found
    """
    from app.domains.transformation.infrastructure.tenant_dbt_project import (
        get_tenant_project_manager,
        TenantDbtProjectError,
    )
    
    file_path = request.args.get('path')
    if not file_path:
        raise ValidationError("File path required", details={"field": "path"})
    
    try:
        manager = get_tenant_project_manager()
        content = manager.get_file_content(file_path)
        
        if content is None:
            raise NovaSightException("File not found", status_code=404)
        
        return jsonify({
            "path": file_path,
            "content": content,
        }), 200
        
    except TenantDbtProjectError as e:
        logger.error(f"Error reading file: {e}")
        raise NovaSightException(f"Failed to read file: {e}")


@api_v1_bp.route('/dbt/project/file', methods=['PUT'])
@authenticated
@tenant_required
@require_roles(['super_admin', 'tenant_admin', 'data_engineer'])
def update_project_file():
    """
    Update (overwrite) a file in the tenant's dbt project.

    Allowed only for files under ``models/``, ``tests/``, ``snapshots/``,
    ``seeds/``, ``macros/`` and ``analyses/`` with safe text extensions.

    ---
    tags:
      - dbt-project
    security:
      - BearerAuth: []
    parameters:
      - name: path
        in: query
        required: true
        schema:
          type: string
        description: Path relative to the project root.
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [content]
            properties:
              content:
                type: string
                description: New file contents (UTF-8 text).
    responses:
      200:
        description: File written
      400:
        description: Invalid path, protected location, or oversized payload
    """
    from app.domains.transformation.infrastructure.tenant_dbt_project import (
        get_tenant_project_manager,
        TenantDbtProjectError,
    )

    file_path = request.args.get('path')
    if not file_path:
        raise ValidationError("File path required", details={"field": "path"})

    payload = request.get_json(silent=True) or {}
    if "content" not in payload:
        raise ValidationError(
            "File content required", details={"field": "content"}
        )
    content = payload.get("content")
    if not isinstance(content, str):
        raise ValidationError(
            "File content must be a string", details={"field": "content"}
        )

    try:
        manager = get_tenant_project_manager()
        result = manager.write_file(file_path, content)
        return jsonify({"success": True, **result}), 200

    except TenantDbtProjectError as e:
        msg = str(e)
        logger.warning("Refused dbt file write (%s): %s", file_path, msg)
        raise NovaSightException(msg, status_code=400)


@api_v1_bp.route('/dbt/project/file', methods=['DELETE'])
@authenticated
@tenant_required
@require_roles(['super_admin', 'tenant_admin', 'data_engineer'])
def delete_project_file():
    """
    Delete a file (dbt model, test, snapshot, seed, macro, or analysis)
    from the tenant's dbt project.

    For ``.sql`` model files, the paired schema YAML (``_<name>.yml``) in
    the same directory is also removed when present.

    ---
    tags:
      - dbt-project
    security:
      - BearerAuth: []
    parameters:
      - name: path
        in: query
        required: true
        schema:
          type: string
        description: |
          Path relative to the project root. Must live under one of:
          ``models/``, ``tests/``, ``snapshots/``, ``seeds/``,
          ``macros/``, ``analyses/``.
    responses:
      200:
        description: File(s) deleted
      400:
        description: Invalid path or protected location
      404:
        description: File not found
    """
    from app.domains.transformation.infrastructure.tenant_dbt_project import (
        get_tenant_project_manager,
        TenantDbtProjectError,
    )

    file_path = request.args.get('path')
    if not file_path:
        raise ValidationError("File path required", details={"field": "path"})

    try:
        manager = get_tenant_project_manager()
        result = manager.delete_file(file_path)
        return jsonify({"success": True, **result}), 200

    except TenantDbtProjectError as e:
        msg = str(e)
        logger.warning("Refused dbt file delete (%s): %s", file_path, msg)
        # Surface "not found" as 404, validation errors as 400.
        status = 404 if "not found" in msg.lower() else 400
        raise NovaSightException(msg, status_code=status)


@api_v1_bp.route('/dbt/project/models', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['super_admin', 'tenant_admin', 'data_engineer'])
def list_project_models():
    """
    List all models in tenant's dbt project.
    
    ---
    tags:
      - dbt-project
    security:
      - BearerAuth: []
    responses:
      200:
        description: List of models
    """
    from app.domains.transformation.infrastructure.tenant_dbt_project import (
        get_tenant_project_manager,
        TenantDbtProjectError,
    )
    
    try:
        manager = get_tenant_project_manager()
        manager.ensure_project_exists()
        models = manager.list_models()
        
        return jsonify({
            "models": models,
            "total_count": len(models),
        }), 200
        
    except TenantDbtProjectError as e:
        logger.error(f"Error listing models: {e}")
        raise NovaSightException(f"Failed to list models: {e}")


@api_v1_bp.route('/dbt/project/semantic-models', methods=['GET'])
@authenticated
@tenant_required
@require_roles(['super_admin', 'tenant_admin', 'data_engineer'])
def list_project_semantic_models():
    """
    List semantic model configurations in tenant's dbt project.
    
    ---
    tags:
      - dbt-project
    security:
      - BearerAuth: []
    responses:
      200:
        description: List of semantic models
    """
    from app.domains.transformation.infrastructure.tenant_dbt_project import (
        get_tenant_project_manager,
        TenantDbtProjectError,
    )
    
    try:
        manager = get_tenant_project_manager()
        manager.ensure_project_exists()
        semantic_models = manager.list_semantic_models()
        
        return jsonify({
            "semantic_models": semantic_models,
            "total_count": len(semantic_models),
        }), 200
        
    except TenantDbtProjectError as e:
        logger.error(f"Error listing semantic models: {e}")
        raise NovaSightException(f"Failed to list semantic models: {e}")


@api_v1_bp.route('/dbt/project/sources/discover', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def discover_sources():
    """
    Discover tables from tenant's ClickHouse database and update sources.yml.
    
    ---
    tags:
      - dbt-project
    security:
      - BearerAuth: []
    responses:
      200:
        description: Sources discovered and updated
    """
    from app.domains.transformation.infrastructure.tenant_dbt_project import (
        get_tenant_project_manager,
        TenantDbtProjectError,
    )
    
    try:
        manager = get_tenant_project_manager()
        manager.ensure_project_exists()
        
        # Ensure target database exists
        manager.ensure_target_database_sync()
        
        # Discover and update sources
        manager.update_sources_from_discovery()
        tables = manager.discover_source_tables()
        
        return jsonify({
            "success": True,
            "source_database": manager.source_database,
            "target_database": manager.target_database,
            "tables_discovered": len(tables),
            "tables": tables,
        }), 200
        
    except TenantDbtProjectError as e:
        logger.error(f"Error discovering sources: {e}")
        raise NovaSightException(f"Failed to discover sources: {e}")


@api_v1_bp.route('/dbt/project/init', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def init_tenant_project():
    """
    Initialize tenant's dbt project and target database.
    
    Creates:
    - dbt_{tenant_db} database in ClickHouse
    - Tenant's dbt project directory with scaffold
    
    ---
    tags:
      - dbt-project
    security:
      - BearerAuth: []
    responses:
      200:
        description: Project initialized
    """
    from app.domains.transformation.infrastructure.tenant_dbt_project import (
        get_tenant_project_manager,
        TenantDbtProjectError,
    )
    
    try:
        manager = get_tenant_project_manager()
        
        # Ensure target database in ClickHouse
        manager.ensure_target_database_sync()
        
        # Ensure project scaffold exists
        project_path = manager.ensure_project_exists()
        
        # Discover sources
        manager.update_sources_from_discovery()
        
        return jsonify({
            "success": True,
            "project_path": str(project_path),
            "source_database": manager.source_database,
            "target_database": manager.target_database,
            "tenant_slug": manager.tenant_slug,
        }), 200
        
    except TenantDbtProjectError as e:
        logger.error(f"Error initializing project: {e}")
        raise NovaSightException(f"Failed to initialize project: {e}")


# ============================================================================
# DAG Generation Endpoints
# ============================================================================

@api_v1_bp.route('/dbt/dag/generate', methods=['POST'])
@authenticated
@tenant_required
@require_roles(['tenant_admin', 'data_engineer'])
def generate_dbt_dag():
    """
    Generate a pipeline DAG for running dbt.
    
    Creates a DAG file from template that can be used in the Task Scheduler.
    
    ---
    tags:
      - dbt-project
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - dag_id
            properties:
              dag_id:
                type: string
                description: Unique identifier for the DAG
              schedule_interval:
                type: string
                description: Cron expression (default "0 6 * * *")
              dbt_command:
                type: string
                enum: [run, test, build, seed, snapshot]
                description: dbt command to execute (default "run")
              dbt_select:
                type: string
                description: Model selection criteria (e.g., "tag:daily")
              dbt_exclude:
                type: string
                description: Model exclusion criteria
              dbt_full_refresh:
                type: boolean
                description: Force full refresh of incremental models
              include_test:
                type: boolean
                description: Include dbt test after run
              generate_docs:
                type: boolean
                description: Generate dbt docs after run
              tags:
                type: array
                items:
                  type: string
                description: Additional DAG tags
              retries:
                type: integer
                description: Number of retries (default 2)
              email_on_failure:
                type: boolean
                description: Send email on failure
    responses:
      200:
        description: DAG generated successfully
    """
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    from app.domains.transformation.infrastructure.tenant_dbt_project import (
        get_tenant_project_manager,
        TenantDbtProjectError,
    )
    
    data = request.get_json() or {}
    
    # Validate required fields
    dag_id = data.get('dag_id')
    if not dag_id:
        raise ValidationError("DAG ID is required", details={"field": "dag_id"})
    
    # Sanitize dag_id
    import re
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', dag_id):
        raise ValidationError(
            "DAG ID must be a valid Python identifier",
            details={"field": "dag_id"}
        )
    
    try:
        manager = get_tenant_project_manager()
        
        # Ensure project exists
        manager.ensure_project_exists()
        
        # Load template
        template_dir = Path(__file__).parent.parent.parent.parent / 'templates' / 'dagster'
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template('dbt_run.py.j2')
        
        # Prepare template variables
        template_vars = {
            'dag_id': f"dbt_{manager.tenant_slug}_{dag_id}",
            'tenant_id': manager.tenant_id,
            'tenant_slug': manager.tenant_slug,
            'schedule_interval': data.get('schedule_interval', '0 6 * * *'),
            'dbt_command': data.get('dbt_command', 'run'),
            'dbt_select': data.get('dbt_select', ''),
            'dbt_exclude': data.get('dbt_exclude', ''),
            'dbt_full_refresh': data.get('dbt_full_refresh', False),
            'include_test': data.get('include_test', False),
            'generate_docs': data.get('generate_docs', False),
            'tags': data.get('tags', []),
            'owner': data.get('owner', 'novasight'),
            'retries': data.get('retries', 2),
            'retry_delay_minutes': data.get('retry_delay_minutes', 5),
            'email_on_failure': data.get('email_on_failure', False),
            'notification_emails': data.get('notification_emails', []),
            'execution_timeout_hours': data.get('execution_timeout_hours', 2),
        }
        
        # Render template
        dag_content = template.render(**template_vars)
        
        # Output path for DAG file
        dag_filename = f"dbt_{manager.tenant_slug}_{dag_id}.py"
        dag_output_dir = Path('/opt/dagster/dags') / f"tenant_{manager.tenant_slug}"
        dag_output_dir.mkdir(parents=True, exist_ok=True)
        dag_output_path = dag_output_dir / dag_filename
        
        # Write DAG file
        with open(dag_output_path, 'w') as f:
            f.write(dag_content)
        
        logger.info(f"Generated DAG: {dag_output_path}")
        
        return jsonify({
            "success": True,
            "dag_id": template_vars['dag_id'],
            "dag_path": str(dag_output_path),
            "dag_content": dag_content,
            "source_database": manager.source_database,
            "target_database": manager.target_database,
        }), 200
        
    except TenantDbtProjectError as e:
        logger.error(f"Error generating DAG: {e}")
        raise NovaSightException(f"Failed to generate DAG: {e}")
    except Exception as e:
        logger.error(f"Error generating DAG: {e}")
        raise NovaSightException(f"Failed to generate DAG: {e}")

