"""
NovaSight Data Sources Domain â€” Connection Routes
===================================================

Database connection management API endpoints.

Canonical location: ``app.domains.datasources.api.connection_routes``

Changes from legacy ``app.api.v1.connections``:
- Imports service from ``domains.datasources.application``
- Uses ``platform.auth`` decorators and identity resolution
"""

from flask import request, jsonify, current_app

from app.api.v1 import api_v1_bp
from app.extensions import db
from app.domains.datasources.application.connection_service import ConnectionService
from app.domains.datasources.application.connection_validators import (
    validate_connection_data,
    get_supported_types,
)
from app.platform.auth.identity import get_current_identity
from app.platform.auth.decorators import authenticated, require_roles, tenant_required
from app.errors import ValidationError, NotFoundError
from app.platform.audit.service import AuditService
import logging

logger = logging.getLogger(__name__)


@api_v1_bp.route("/connections/types", methods=["GET"])
@authenticated
@tenant_required
def list_connection_types():
    """List available connection types with metadata."""
    from app.domains.datasources.infrastructure.connectors import ConnectorRegistry

    types_info = []
    for db_type in get_supported_types():
        entry = {
            "type": db_type,
            "category": "database",
            "requires_upload": False,
        }
        try:
            info = ConnectorRegistry.get_connector_info(db_type)
            entry.update(info)
        except ValueError:
            entry["default_port"] = 0
            entry["supports_ssl"] = False
        types_info.append(entry)

    return jsonify({"types": types_info})


@api_v1_bp.route("/connections", methods=["GET"])
@authenticated
@tenant_required
def list_connections():
    """List all data connections for current tenant."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id

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
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin"])
def create_connection():
    """Create a new data source connection."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    user_id = identity.user_id
    data = request.get_json()

    if not data:
        raise ValidationError("Request body required")

    # Name is always required
    if not data.get("name"):
        raise ValidationError("Field 'name' is required")
    if not data.get("db_type"):
        raise ValidationError("Field 'db_type' is required")

    db_type = data["db_type"]

    # Validate db_type and per-type required fields via registry
    valid, error_msg = validate_connection_data(db_type, data)
    if not valid:
        raise ValidationError(error_msg)

    connection_service = ConnectionService(tenant_id)

    ssl_mode = data.get("ssl_mode")
    if ssl_mode is None and data.get("ssl_enabled"):
        ssl_mode = "require"

    try:
        connection = connection_service.create_connection(
            name=data["name"],
            db_type=data["db_type"],
            host=data.get("host"),
            port=data.get("port"),
            database=data.get("database"),
            username=data.get("username"),
            password=data.get("password"),
            ssl_mode=ssl_mode,
            schema_name=data.get("schema_name"),
            extra_params=data.get("extra_params", {}),
            created_by=user_id,
        )
    except ValueError as e:
        raise ValidationError(str(e))

    logger.info(f"Connection '{data['name']}' created in tenant {tenant_id}")
    
    # Audit log: connection created
    AuditService.log(
        action='connection.created',
        resource_type='connection',
        resource_id=str(connection.id),
        resource_name=data['name'],
        tenant_id=tenant_id,
        extra_data={'db_type': data['db_type'], 'host': data.get('host')},
    )

    return jsonify({"connection": connection.to_dict(mask_password=True)}), 201


@api_v1_bp.route("/connections/<connection_id>", methods=["GET"])
@authenticated
@tenant_required
def get_connection(connection_id: str):
    """Get connection details."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id

    connection_service = ConnectionService(tenant_id)
    connection = connection_service.get_connection(connection_id)

    if not connection:
        raise NotFoundError("Connection not found")

    return jsonify({"connection": connection.to_dict(mask_password=True)})


@api_v1_bp.route("/connections/<connection_id>", methods=["PATCH"])
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin"])
def update_connection(connection_id: str):
    """Update connection details."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    data = request.get_json()

    if not data:
        raise ValidationError("Request body required")

    connection_service = ConnectionService(tenant_id)
    connection = connection_service.update_connection(connection_id, **data)

    if not connection:
        raise NotFoundError("Connection not found")

    logger.info(f"Connection {connection_id} updated in tenant {tenant_id}")
    
    # Audit log: connection updated
    AuditService.log(
        action='connection.updated',
        resource_type='connection',
        resource_id=connection_id,
        resource_name=connection.name,
        tenant_id=tenant_id,
        changes={'updated_fields': list(data.keys())},
    )

    return jsonify({"connection": connection.to_dict(mask_password=True)})


@api_v1_bp.route("/connections/<connection_id>", methods=["DELETE"])
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin"])
def delete_connection(connection_id: str):
    """Delete a data connection."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id

    connection_service = ConnectionService(tenant_id)
    success = connection_service.delete_connection(connection_id)

    if not success:
        raise NotFoundError("Connection not found")

    logger.info(f"Connection {connection_id} deleted from tenant {tenant_id}")
    
    # Audit log: connection deleted
    AuditService.log(
        action='connection.deleted',
        resource_type='connection',
        resource_id=connection_id,
        tenant_id=tenant_id,
    )

    return jsonify({"message": "Connection deleted successfully"})


@api_v1_bp.route("/connections/<connection_id>/test", methods=["POST"])
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin", "viewer"])
def test_connection(connection_id: str):
    """Test database connection."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id

    connection_service = ConnectionService(tenant_id)
    result = connection_service.test_connection(connection_id)

    # Audit log: connection tested
    AuditService.log(
        action='connection.tested',
        resource_type='connection',
        resource_id=connection_id,
        tenant_id=tenant_id,
        success=result["success"],
        error_message=result.get("error") if not result["success"] else None,
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


@api_v1_bp.route("/connections/test", methods=["POST"])
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin"])
def test_new_connection():
    """Test connection parameters without saving."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    data = request.get_json()

    if not data:
        raise ValidationError("Request body required")

    if not data.get("db_type"):
        raise ValidationError("Field 'db_type' is required")

    required_fields = ["db_type", "host", "port", "database", "username", "password"]
    for field in required_fields:
        if not data.get(field):
            raise ValidationError(f"Field '{field}' is required")

    connection_service = ConnectionService(tenant_id)

    ssl_mode = data.get("ssl_mode")
    if ssl_mode is None and data.get("ssl_enabled"):
        ssl_mode = "require"

    result = connection_service.test_connection_params(
        db_type=data["db_type"],
        host=data["host"],
        port=data["port"],
        database=data["database"],
        username=data["username"],
        password=data["password"],
        ssl_mode=ssl_mode,
        extra_params=data.get("extra_params"),
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
@authenticated
@tenant_required
def get_connection_schema(connection_id: str):
    """Get database schema information."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id

    schema_name = request.args.get("schema_name")
    include_columns = request.args.get("include_columns", "false").lower() == "true"
    schemas_only = request.args.get("schemas_only", "false").lower() == "true"

    connection_service = ConnectionService(tenant_id)
    schema_info = connection_service.get_schema(
        connection_id=connection_id,
        schema_name=schema_name,
        include_columns=include_columns,
        schemas_only=schemas_only,
    )

    if schema_info is None:
        raise NotFoundError("Connection not found or inaccessible")

    return jsonify({"schema": schema_info})


@api_v1_bp.route("/connections/<connection_id>/sync", methods=["POST"])
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin"])
def trigger_connection_sync(connection_id: str):
    """Trigger data sync for a connection."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id

    data = request.get_json() or {}
    sync_config = {
        "tables": data.get("tables"),
        "incremental": data.get("incremental", False),
        **data.get("sync_config", {}),
    }

    connection_service = ConnectionService(tenant_id)
    job_id = connection_service.trigger_sync(
        connection_id=connection_id,
        sync_config=sync_config,
    )

    if not job_id:
        raise NotFoundError("Connection not found or sync failed to start")

    logger.info(f"Sync triggered for connection {connection_id}: job_id={job_id}")

    return jsonify({
        "job_id": job_id,
        "status": "started",
        "message": "Data sync job started successfully",
    })


@api_v1_bp.route("/query/execute", methods=["POST"])
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin", "analyst", "viewer"])
def execute_query():
    """Execute a SQL query against a connection."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    data = request.get_json()

    if not data:
        raise ValidationError("Request body required")

    connection_id = data.get("connection_id")
    sql = data.get("sql")
    limit = data.get("limit", 1000)

    if not connection_id:
        raise ValidationError("connection_id is required")
    if not sql:
        raise ValidationError("sql is required")

    connection_service = ConnectionService(tenant_id)

    try:
        result = connection_service.execute_query(
            connection_id=connection_id,
            sql=sql,
            limit=limit,
        )
        return jsonify(result)

    except ValueError as e:
        raise ValidationError(str(e))


# â”€â”€â”€ Tenant ClickHouse Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@api_v1_bp.route("/clickhouse/info", methods=["GET"])
@authenticated
@tenant_required
def get_tenant_clickhouse_info():
    """Get tenant's ClickHouse database information."""
    from app.platform.tenant.isolation import TenantIsolationService
    
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    isolation = TenantIsolationService(tenant_id)
    
    return jsonify({
        "database": isolation.tenant_database,
        "tenant_id": tenant_id,
        "type": "clickhouse",
        "name": f"Tenant ClickHouse ({isolation.tenant_database})",
    })


@api_v1_bp.route("/clickhouse/schema", methods=["GET"])
@authenticated
@tenant_required
def get_tenant_clickhouse_schema():
    """Get tenant's ClickHouse database schema (tables and columns)."""
    from app.domains.analytics.infrastructure.clickhouse_client import get_clickhouse_client
    from app.platform.tenant.isolation import TenantIsolationService
    
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    
    include_columns = request.args.get("include_columns", "false").lower() == "true"
    
    try:
        isolation = TenantIsolationService(tenant_id)
        db_name = isolation.tenant_database
        
        # Connect to ClickHouse (use default database to query system tables)
        client = get_clickhouse_client(database=db_name)
        
        # Get tables from the tenant's database
        tables_query = f"""
            SELECT 
                name,
                engine,
                total_rows,
                total_bytes,
                comment
            FROM system.tables 
            WHERE database = '{db_name}'
            ORDER BY name
        """
        tables_result = client.execute(tables_query)
        
        tables = []
        for row in tables_result.rows:
            table_name = row[0]
            table_info = {
                "name": table_name,
                "schema": db_name,
                "engine": row[1],
                "row_count": row[2] if row[2] else 0,
                "size_bytes": row[3] if row[3] else 0,
                "comment": row[4] if len(row) > 4 else None,
                "table_type": "TABLE",
            }
            
            # Get columns if requested
            if include_columns:
                columns_query = f"""
                    SELECT 
                        name,
                        type,
                        default_kind,
                        comment,
                        is_in_primary_key
                    FROM system.columns 
                    WHERE database = '{db_name}' AND table = '{table_name}'
                    ORDER BY position
                """
                columns_result = client.execute(columns_query)
                
                columns = []
                for col_row in columns_result.rows:
                    columns.append({
                        "name": col_row[0],
                        "data_type": col_row[1],
                        "nullable": "Nullable" in col_row[1],
                        "default_kind": col_row[2] if col_row[2] else None,
                        "comment": col_row[3] if len(col_row) > 3 else None,
                        "primary_key": bool(col_row[4]) if len(col_row) > 4 else False,
                    })
                table_info["columns"] = columns
            
            tables.append(table_info)
        
        # Return in the same format as connection schema endpoint
        return jsonify({
            "schema": {
                "schemas": [{
                    "name": db_name,
                    "tables": tables,
                }],
                "total_tables": len(tables),
                "total_columns": sum(len(t.get("columns", [])) for t in tables),
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get ClickHouse schema: {e}")
        return jsonify({
            "schema": {
                "schemas": [],
                "total_tables": 0,
                "total_columns": 0,
                "error": str(e),
            }
        })


@api_v1_bp.route("/clickhouse/query", methods=["POST"])
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin", "analyst", "viewer"])
def execute_clickhouse_query():
    """Execute a SQL query against tenant's ClickHouse database."""
    import time
    from app.domains.analytics.infrastructure.clickhouse_client import get_clickhouse_client
    from app.platform.tenant.isolation import TenantIsolationService
    
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    data = request.get_json()

    if not data:
        raise ValidationError("Request body required")

    sql = data.get("sql")
    limit = data.get("limit", 1000)

    if not sql:
        raise ValidationError("sql is required")

    # Validate query
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT"):
        raise ValidationError("Only SELECT queries are allowed")

    dangerous_keywords = ["DROP", "TRUNCATE", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    for keyword in dangerous_keywords:
        if keyword in sql_stripped:
            raise ValidationError(f"Query contains disallowed keyword: {keyword}")

    try:
        # Get tenant-specific ClickHouse client
        isolation = TenantIsolationService(tenant_id)
        client = get_clickhouse_client(database=isolation.tenant_database)
        
        # Add LIMIT if not present
        if "LIMIT" not in sql_stripped:
            sql = f"{sql.rstrip().rstrip(';')} LIMIT {limit}"
        
        start_time = time.time()
        result = client.execute(sql)
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        columns = result.columns if hasattr(result, 'columns') else []
        rows = result.to_records() if hasattr(result, 'to_records') else []
        
        return jsonify({
            "columns": [{"name": col, "type": "unknown"} for col in columns],
            "rows": rows[:limit],
            "row_count": len(rows),
            "execution_time_ms": execution_time_ms,
            "truncated": len(rows) > limit,
        })

    except Exception as e:
        logger.error(f"ClickHouse query failed: {e}")
        raise ValidationError(f"Query execution failed: {str(e)}")


@api_v1_bp.route("/connections/<connection_id>/preview", methods=["POST"])
@authenticated
@tenant_required
@require_roles(["data_engineer", "tenant_admin", "analyst"])
def preview_connection_data(connection_id: str):
    """Preview sample data from an existing connection."""
    identity = get_current_identity()
    tenant_id = identity.tenant_id

    connection_service = ConnectionService(tenant_id)
    connection = connection_service.get_connection(connection_id)
    if not connection:
        raise NotFoundError("Connection not found")

    data = request.get_json() or {}
    limit = min(int(data.get("limit", 100)), 500)

    try:
        preview = connection_service.preview_data(
            connection_id=connection_id,
            table=data.get("table"),
            schema=data.get("schema"),
            limit=limit,
        )
    except ValueError as e:
        raise ValidationError(str(e))

    return jsonify({
        "rows": preview.get("rows", []),
        "columns": preview.get("columns", []),
    })


# â”€â”€â”€ Saved Queries Endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@api_v1_bp.route("/saved-queries", methods=["GET"])
@authenticated
@tenant_required
def list_saved_queries():
    """List saved queries for the current tenant."""
    from app.domains.datasources.domain.models import SavedQuery
    
    identity = get_current_identity()
    user_id = identity.user_id
    
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    query_type = request.args.get("query_type")
    
    query = SavedQuery.query
    
    # Filter by type if specified
    if query_type:
        from app.domains.datasources.domain.models import QueryType
        try:
            qt = QueryType(query_type)
            query = query.filter(SavedQuery.query_type == qt)
        except ValueError:
            pass
    
    # Show user's own queries and public queries
    query = query.filter(
        db.or_(
            SavedQuery.created_by == user_id,
            SavedQuery.is_public == True
        )
    )
    
    query = query.order_by(SavedQuery.updated_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        "items": [q.to_dict() for q in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages,
    })


@api_v1_bp.route("/saved-queries", methods=["POST"])
@authenticated
@tenant_required
def create_saved_query():
    """Create a new saved query."""
    from app.domains.datasources.domain.models import SavedQuery, QueryType
    
    identity = get_current_identity()
    tenant_id = identity.tenant_id
    user_id = identity.user_id
    data = request.get_json()

    if not data:
        raise ValidationError("Request body required")

    name = data.get("name")
    sql = data.get("sql")

    if not name:
        raise ValidationError("name is required")
    if not sql:
        raise ValidationError("sql is required")

    # Check for duplicate name
    existing = SavedQuery.query.filter_by(tenant_id=tenant_id, name=name).first()
    if existing:
        raise ValidationError(f"A query with name '{name}' already exists")

    query_type = QueryType.ADHOC
    if data.get("query_type"):
        try:
            query_type = QueryType(data.get("query_type"))
        except ValueError:
            pass

    saved_query = SavedQuery(
        tenant_id=tenant_id,
        name=name,
        description=data.get("description"),
        sql=sql,
        query_type=query_type,
        tags=data.get("tags", []),
        connection_id=data.get("connection_id"),
        is_clickhouse=data.get("is_clickhouse", False),
        is_public=data.get("is_public", False),
        created_by=user_id,
    )
    
    db.session.add(saved_query)
    db.session.commit()
    
    logger.info(f"Saved query '{name}' created by user {user_id}")
    
    return jsonify({"saved_query": saved_query.to_dict()}), 201


@api_v1_bp.route("/saved-queries/<query_id>", methods=["GET"])
@authenticated
@tenant_required
def get_saved_query(query_id: str):
    """Get a saved query by ID."""
    from app.domains.datasources.domain.models import SavedQuery
    
    identity = get_current_identity()
    user_id = identity.user_id
    
    saved_query = SavedQuery.query.filter_by(id=query_id).first()
    
    if not saved_query:
        raise NotFoundError("Saved query not found")
    
    # Check access
    if not saved_query.is_public and str(saved_query.created_by) != str(user_id):
        raise NotFoundError("Saved query not found")
    
    return jsonify({"saved_query": saved_query.to_dict()})


@api_v1_bp.route("/saved-queries/<query_id>", methods=["PATCH"])
@authenticated
@tenant_required
def update_saved_query(query_id: str):
    """Update a saved query."""
    from app.domains.datasources.domain.models import SavedQuery, QueryType
    
    identity = get_current_identity()
    user_id = identity.user_id
    data = request.get_json()

    if not data:
        raise ValidationError("Request body required")

    saved_query = SavedQuery.query.filter_by(id=query_id).first()
    
    if not saved_query:
        raise NotFoundError("Saved query not found")
    
    # Only owner can update
    if str(saved_query.created_by) != str(user_id):
        raise ValidationError("You can only update your own queries")

    # Update fields
    if "name" in data:
        saved_query.name = data["name"]
    if "description" in data:
        saved_query.description = data["description"]
    if "sql" in data:
        saved_query.sql = data["sql"]
    if "query_type" in data:
        try:
            saved_query.query_type = QueryType(data["query_type"])
        except ValueError:
            pass
    if "tags" in data:
        saved_query.tags = data["tags"]
    if "is_public" in data:
        saved_query.is_public = data["is_public"]
    
    db.session.commit()
    
    return jsonify({"saved_query": saved_query.to_dict()})


@api_v1_bp.route("/saved-queries/<query_id>", methods=["DELETE"])
@authenticated
@tenant_required
def delete_saved_query(query_id: str):
    """Delete a saved query."""
    from app.domains.datasources.domain.models import SavedQuery
    
    identity = get_current_identity()
    user_id = identity.user_id

    saved_query = SavedQuery.query.filter_by(id=query_id).first()
    
    if not saved_query:
        raise NotFoundError("Saved query not found")
    
    # Only owner can delete
    if str(saved_query.created_by) != str(user_id):
        raise ValidationError("You can only delete your own queries")

    db.session.delete(saved_query)
    db.session.commit()
    
    return jsonify({"message": "Saved query deleted successfully"})
