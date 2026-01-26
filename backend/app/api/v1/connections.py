"""
NovaSight Data Connection Endpoints
===================================

Database connection management for data sources.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.api.v1 import api_v1_bp
from app.services.connection_service import ConnectionService
from app.decorators import require_roles, require_tenant_context
from app.errors import ValidationError, NotFoundError, ConnectionTestError
import logging

logger = logging.getLogger(__name__)


@api_v1_bp.route("/connections", methods=["GET"])
@jwt_required()
@require_tenant_context
def list_connections():
    """
    List all data connections for current tenant.
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Items per page (default: 20)
        - db_type: Filter by database type
        - status: Filter by connection status
    
    Returns:
        Paginated list of connections (credentials masked)
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    db_type = request.args.get("db_type")
    status = request.args.get("status")
    
    connection_service = ConnectionService(tenant_id)
    result = connection_service.list_connections(
        page=page, per_page=per_page, db_type=db_type, status=status
    )
    
    return jsonify(result)


@api_v1_bp.route("/connections", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def create_connection():
    """
    Create a new data source connection.
    
    Request Body:
        - name: Connection display name (unique per tenant)
        - db_type: Database type (postgresql, oracle, sqlserver)
        - host: Database host/IP address
        - port: Database port
        - database: Database name
        - username: Connection username
        - password: Connection password
        - ssl_mode: Optional SSL mode
        - extra_params: Optional additional connection parameters
    
    Returns:
        Created connection details (password masked)
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    user_id = identity.get("user_id")
    data = request.get_json()
    
    if not data:
        raise ValidationError("Request body required")
    
    required_fields = ["name", "db_type", "host", "port", "database", "username", "password"]
    for field in required_fields:
        if not data.get(field):
            raise ValidationError(f"Field '{field}' is required")
    
    # Validate database type
    valid_db_types = ["postgresql", "oracle", "sqlserver", "mysql", "clickhouse"]
    if data["db_type"] not in valid_db_types:
        raise ValidationError(f"Invalid db_type. Must be one of: {', '.join(valid_db_types)}")
    
    connection_service = ConnectionService(tenant_id)
    connection = connection_service.create_connection(
        name=data["name"],
        db_type=data["db_type"],
        host=data["host"],
        port=data["port"],
        database=data["database"],
        username=data["username"],
        password=data["password"],
        ssl_mode=data.get("ssl_mode"),
        extra_params=data.get("extra_params", {}),
        created_by=user_id,
    )
    
    logger.info(f"Connection '{data['name']}' created in tenant {tenant_id}")
    
    return jsonify({"connection": connection.to_dict(mask_password=True)}), 201


@api_v1_bp.route("/connections/<connection_id>", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_connection(connection_id: str):
    """
    Get connection details.
    
    Args:
        connection_id: Connection UUID
    
    Returns:
        Connection details (password masked)
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    connection_service = ConnectionService(tenant_id)
    connection = connection_service.get_connection(connection_id)
    
    if not connection:
        raise NotFoundError("Connection not found")
    
    return jsonify({"connection": connection.to_dict(mask_password=True)})


@api_v1_bp.route("/connections/<connection_id>", methods=["PATCH"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def update_connection(connection_id: str):
    """
    Update connection details.
    
    Args:
        connection_id: Connection UUID
    
    Request Body:
        - name: Connection display name
        - host: Database host
        - port: Database port
        - database: Database name
        - username: Connection username
        - password: New password (optional)
        - ssl_mode: SSL mode
        - extra_params: Additional parameters
    
    Returns:
        Updated connection details
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    data = request.get_json()
    
    if not data:
        raise ValidationError("Request body required")
    
    connection_service = ConnectionService(tenant_id)
    connection = connection_service.update_connection(connection_id, **data)
    
    if not connection:
        raise NotFoundError("Connection not found")
    
    logger.info(f"Connection {connection_id} updated in tenant {tenant_id}")
    
    return jsonify({"connection": connection.to_dict(mask_password=True)})


@api_v1_bp.route("/connections/<connection_id>", methods=["DELETE"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def delete_connection(connection_id: str):
    """
    Delete a data connection.
    
    Args:
        connection_id: Connection UUID
    
    Returns:
        Success message
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    connection_service = ConnectionService(tenant_id)
    success = connection_service.delete_connection(connection_id)
    
    if not success:
        raise NotFoundError("Connection not found")
    
    logger.info(f"Connection {connection_id} deleted from tenant {tenant_id}")
    
    return jsonify({"message": "Connection deleted successfully"})


@api_v1_bp.route("/connections/<connection_id>/test", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin", "viewer"])
def test_connection(connection_id: str):
    """
    Test database connection.
    
    Args:
        connection_id: Connection UUID
    
    Returns:
        Connection test result
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    connection_service = ConnectionService(tenant_id)
    result = connection_service.test_connection(connection_id)
    
    if not result["success"]:
        return jsonify({
            "success": False,
            "message": result.get("error", "Connection test failed"),
            "details": result.get("details", {}),
        }), 400
    
    return jsonify({
        "success": True,
        "message": "Connection successful",
        "details": result.get("details", {}),
    })


@api_v1_bp.route("/connections/test", methods=["POST"])
@jwt_required()
@require_tenant_context
@require_roles(["data_engineer", "tenant_admin"])
def test_new_connection():
    """
    Test connection parameters without saving.
    
    Request Body:
        - db_type: Database type
        - host: Database host
        - port: Database port
        - database: Database name
        - username: Connection username
        - password: Connection password
        - ssl_mode: Optional SSL mode
    
    Returns:
        Connection test result
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    data = request.get_json()
    
    if not data:
        raise ValidationError("Request body required")
    
    required_fields = ["db_type", "host", "port", "database", "username", "password"]
    for field in required_fields:
        if not data.get(field):
            raise ValidationError(f"Field '{field}' is required")
    
    connection_service = ConnectionService(tenant_id)
    result = connection_service.test_connection_params(
        db_type=data["db_type"],
        host=data["host"],
        port=data["port"],
        database=data["database"],
        username=data["username"],
        password=data["password"],
        ssl_mode=data.get("ssl_mode"),
    )
    
    if not result["success"]:
        return jsonify({
            "success": False,
            "message": result.get("error", "Connection test failed"),
            "details": result.get("details", {}),
        }), 400
    
    return jsonify({
        "success": True,
        "message": "Connection successful",
        "details": result.get("details", {}),
    })


@api_v1_bp.route("/connections/<connection_id>/schema", methods=["GET"])
@jwt_required()
@require_tenant_context
def get_connection_schema(connection_id: str):
    """
    Get database schema information.
    
    Args:
        connection_id: Connection UUID
    
    Query Parameters:
        - schema_name: Filter by schema name
        - include_columns: Include column details (default: false)
    
    Returns:
        Database schema information (tables, columns, types)
    """
    identity = get_jwt_identity()
    tenant_id = identity.get("tenant_id")
    
    schema_name = request.args.get("schema_name")
    include_columns = request.args.get("include_columns", "false").lower() == "true"
    
    connection_service = ConnectionService(tenant_id)
    schema_info = connection_service.get_schema(
        connection_id=connection_id,
        schema_name=schema_name,
        include_columns=include_columns,
    )
    
    if schema_info is None:
        raise NotFoundError("Connection not found or inaccessible")
    
    return jsonify({"schema": schema_info})
