"""
NovaSight PySpark Apps API Endpoints
====================================

REST API for PySpark application configuration and code generation.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError as PydanticValidationError

from app.api.v1 import api_v1_bp
from app.services.pyspark_app_service import PySparkAppService
from app.decorators import require_roles, require_tenant_context
from app.errors import ValidationError, NotFoundError
from app.schemas.pyspark_schemas import (
    PySparkAppCreateSchema,
    PySparkAppUpdateSchema,
    PySparkCodePreviewSchema,
    QueryValidationRequestSchema,
)
import logging

logger = logging.getLogger(__name__)


@api_v1_bp.route("/pyspark-apps", methods=["GET"])
@jwt_required()
@require_tenant_context
def list_pyspark_apps():
    """
    List all PySpark apps for current tenant.
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - status: Filter by status (draft, active, inactive, error)
        - connection_id: Filter by source connection
        - search: Search by name/description
    
    Returns:
        Paginated list of PySpark apps
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")
    connection_id = request.args.get("connection_id")
    search = request.args.get("search")
    
    service = PySparkAppService(tenant_id)
    result = service.list_apps(
        page=page,
        per_page=per_page,
        status=status,
        connection_id=connection_id,
        search=search,
    )
    
    return jsonify(result)


@api_v1_bp.route("/pyspark-apps", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def create_pyspark_app():
    """
    Create a new PySpark app configuration.
    
    Request Body:
        - name: App display name (unique per tenant)
        - connection_id: Source connection UUID
        - source_type: 'table' or 'query'
        - source_table: Table name (if source_type is 'table')
        - source_query: SQL query (if source_type is 'query')
        - columns_config: Column configuration list
        - primary_key_columns: Primary key column names
        - cdc_type: CDC type (none, timestamp, version, hash)
        - cdc_column: CDC tracking column
        - partition_columns: Partition column names
        - scd_type: SCD type (none, type1, type2)
        - write_mode: Write mode (append, overwrite, merge)
        - target_database: Target database name
        - target_table: Target table name
        
    Returns:
        Created PySpark app details
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    user_id = identity.get("user_id")
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    # Validate with Pydantic
    try:
        schema = PySparkAppCreateSchema(**data)
    except PydanticValidationError as e:
        errors = [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        raise ValidationError("Validation failed", details={"errors": errors})
    
    service = PySparkAppService(tenant_id)
    app = service.create_app(
        name=schema.name,
        connection_id=schema.connection_id,
        created_by=user_id,
        description=schema.description,
        source_type=schema.source_type.value,
        source_schema=schema.source_schema,
        source_table=schema.source_table,
        source_query=schema.source_query,
        columns_config=[col.dict() for col in schema.columns_config],
        primary_key_columns=schema.primary_key_columns,
        cdc_type=schema.cdc_type.value,
        cdc_column=schema.cdc_column,
        partition_columns=schema.partition_columns,
        scd_type=schema.scd_type.value,
        write_mode=schema.write_mode.value,
        target_database=schema.target_database,
        target_table=schema.target_table,
        target_engine=schema.target_engine,
        options=schema.options,
    )
    
    return jsonify(app.to_dict()), 201


@api_v1_bp.route("/pyspark-apps/<app_id>", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_pyspark_app(app_id: str):
    """
    Get PySpark app details.
    
    Path Parameters:
        - app_id: PySpark app UUID
        
    Query Parameters:
        - include_code: Include generated code (default: false)
    
    Returns:
        PySpark app details
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    include_code = request.args.get("include_code", "false").lower() == "true"
    
    service = PySparkAppService(tenant_id)
    app = service.get_app(app_id, include_code=include_code)
    
    if not app:
        raise NotFoundError(f"PySpark app {app_id} not found")
    
    return jsonify(app.to_dict(include_code=include_code))


@api_v1_bp.route("/pyspark-apps/<app_id>", methods=["PUT"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def update_pyspark_app(app_id: str):
    """
    Update a PySpark app configuration.
    
    Path Parameters:
        - app_id: PySpark app UUID
        
    Request Body:
        Any fields from create endpoint (all optional)
    
    Returns:
        Updated PySpark app details
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    # Validate with Pydantic
    try:
        schema = PySparkAppUpdateSchema(**data)
    except PydanticValidationError as e:
        errors = [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        raise ValidationError("Validation failed", details={"errors": errors})
    
    # Convert schema to dict, excluding None values
    update_data = {k: v for k, v in schema.dict().items() if v is not None}
    
    # Convert enums to values
    if "source_type" in update_data:
        update_data["source_type"] = update_data["source_type"].value
    if "cdc_type" in update_data:
        update_data["cdc_type"] = update_data["cdc_type"].value
    if "scd_type" in update_data:
        update_data["scd_type"] = update_data["scd_type"].value
    if "write_mode" in update_data:
        update_data["write_mode"] = update_data["write_mode"].value
    if "status" in update_data:
        update_data["status"] = update_data["status"].value
    if "columns_config" in update_data:
        update_data["columns_config"] = [col.dict() for col in update_data["columns_config"]]
    
    service = PySparkAppService(tenant_id)
    app = service.update_app(app_id, **update_data)
    
    return jsonify(app.to_dict())


@api_v1_bp.route("/pyspark-apps/<app_id>", methods=["DELETE"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def delete_pyspark_app(app_id: str):
    """
    Delete a PySpark app.
    
    Path Parameters:
        - app_id: PySpark app UUID
    
    Returns:
        Success message
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    service = PySparkAppService(tenant_id)
    service.delete_app(app_id)
    
    return jsonify({"message": f"PySpark app {app_id} deleted successfully"})


@api_v1_bp.route("/pyspark-apps/<app_id>/generate", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def generate_pyspark_code(app_id: str):
    """
    Generate PySpark code from app configuration.
    
    Path Parameters:
        - app_id: PySpark app UUID
    
    Returns:
        Generated code and metadata
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    service = PySparkAppService(tenant_id)
    code, metadata = service.generate_code(app_id)
    
    return jsonify({
        "code": code,
        "template_name": metadata["template_name"],
        "template_version": metadata["template_version"],
        "parameters_hash": metadata["parameters_hash"],
        "generated_at": metadata["generated_at"],
    })


@api_v1_bp.route("/pyspark-apps/<app_id>/code", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_pyspark_code(app_id: str):
    """
    Get previously generated PySpark code.
    
    Path Parameters:
        - app_id: PySpark app UUID
    
    Returns:
        Generated code and metadata
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    service = PySparkAppService(tenant_id)
    app = service.get_app(app_id, include_code=True)
    
    if not app:
        raise NotFoundError(f"PySpark app {app_id} not found")
    
    if not app.generated_code:
        raise ValidationError("Code has not been generated yet. Use POST /generate first.")
    
    return jsonify({
        "code": app.generated_code,
        "code_hash": app.generated_code_hash,
        "template_version": app.template_version,
        "generated_at": app.generated_at.isoformat() if app.generated_at else None,
    })


@api_v1_bp.route("/pyspark-apps/preview", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def preview_pyspark_code():
    """
    Preview PySpark code without saving.
    
    Request Body:
        Same as create endpoint
    
    Returns:
        Generated code preview and metadata
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    # Validate with Pydantic
    try:
        schema = PySparkCodePreviewSchema(**data)
    except PydanticValidationError as e:
        errors = [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        raise ValidationError("Validation failed", details={"errors": errors})
    
    service = PySparkAppService(tenant_id)
    code, metadata = service.preview_code(
        connection_id=schema.connection_id,
        source_type=schema.source_type.value,
        source_schema=schema.source_schema,
        source_table=schema.source_table,
        source_query=schema.source_query,
        columns_config=[col.dict() for col in schema.columns_config],
        primary_key_columns=schema.primary_key_columns,
        cdc_type=schema.cdc_type.value,
        cdc_column=schema.cdc_column,
        partition_columns=schema.partition_columns,
        scd_type=schema.scd_type.value,
        write_mode=schema.write_mode.value,
        target_database=schema.target_database,
        target_table=schema.target_table,
        target_engine=schema.target_engine,
        options=schema.options,
    )
    
    return jsonify({
        "code": code,
        "template_name": metadata["template_name"],
        "template_version": metadata["template_version"],
        "parameters_hash": metadata["parameters_hash"],
        "is_preview": True,
    })


@api_v1_bp.route("/pyspark-apps/validate-query", methods=["POST"])
@jwt_required()
@require_tenant_context
def validate_pyspark_query():
    """
    Validate SQL query and get column metadata.
    
    Request Body:
        - connection_id: Connection UUID
        - query: SQL query to validate
    
    Returns:
        Validation result with columns
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    connection_id = data.get("connection_id")
    query = data.get("query")
    
    if not connection_id:
        raise ValidationError("connection_id is required")
    if not query:
        raise ValidationError("query is required")
    
    try:
        schema = QueryValidationRequestSchema(query=query)
    except PydanticValidationError as e:
        errors = [{"field": err["loc"][0], "message": err["msg"]} for err in e.errors()]
        raise ValidationError("Validation failed", details={"errors": errors})
    
    service = PySparkAppService(tenant_id)
    result = service.validate_query(connection_id, schema.query)
    
    return jsonify(result)
