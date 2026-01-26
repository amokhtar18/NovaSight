# Flask API Development Skill

## Description
This skill provides patterns and implementations for building Flask REST APIs with multi-tenant support, JWT authentication, and proper validation.

## Trigger
- User asks to create API endpoints
- User asks to implement REST services
- User mentions Flask routing or blueprints

## Instructions

### 1. Blueprint Structure
All API endpoints must be organized in versioned blueprints:

```python
# backend/app/api/v1/__init__.py
from flask import Blueprint

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

from app.api.v1 import auth, connections, ingestion, dbt, dags, analytics, dashboards, admin
```

### 2. Endpoint Pattern
```python
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.schemas.connection_schemas import ConnectionCreate, ConnectionUpdate
from app.services.connection_service import ConnectionService
from app.middleware import require_permission
from pydantic import ValidationError

bp = Blueprint('connections', __name__, url_prefix='/connections')

@bp.route('/', methods=['GET'])
@jwt_required()
@require_permission('datasources.view')
def list_connections():
    """List all connections for the tenant."""
    service = ConnectionService()
    connections = service.list_connections()
    return jsonify({
        'success': True,
        'data': [c.to_dict() for c in connections]
    })

@bp.route('/', methods=['POST'])
@jwt_required()
@require_permission('datasources.create')
def create_connection():
    """Create a new connection."""
    try:
        data = ConnectionCreate(**request.json)
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.errors()
        }), 400
    
    service = ConnectionService()
    try:
        connection = service.create_connection(data)
        return jsonify({
            'success': True,
            'data': connection.to_dict()
        }), 201
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@bp.route('/<uuid:connection_id>', methods=['GET'])
@jwt_required()
@require_permission('datasources.view')
def get_connection(connection_id):
    """Get a specific connection."""
    service = ConnectionService()
    connection = service.get_connection(connection_id)
    if not connection:
        return jsonify({
            'success': False,
            'error': 'Connection not found'
        }), 404
    return jsonify({
        'success': True,
        'data': connection.to_dict()
    })

@bp.route('/<uuid:connection_id>', methods=['PUT'])
@jwt_required()
@require_permission('datasources.edit')
def update_connection(connection_id):
    """Update a connection."""
    try:
        data = ConnectionUpdate(**request.json)
    except ValidationError as e:
        return jsonify({
            'success': False,
            'error': 'Validation error',
            'details': e.errors()
        }), 400
    
    service = ConnectionService()
    try:
        connection = service.update_connection(connection_id, data)
        return jsonify({
            'success': True,
            'data': connection.to_dict()
        })
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@bp.route('/<uuid:connection_id>', methods=['DELETE'])
@jwt_required()
@require_permission('datasources.delete')
def delete_connection(connection_id):
    """Delete a connection."""
    service = ConnectionService()
    try:
        service.delete_connection(connection_id)
        return jsonify({'success': True}), 204
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
```

### 3. Response Format
All API responses must follow this format:

```python
# Success response
{
    "success": True,
    "data": { ... } | [ ... ],
    "meta": {
        "page": 1,
        "per_page": 20,
        "total": 100
    }  # Optional, for paginated responses
}

# Error response
{
    "success": False,
    "error": "Human-readable error message",
    "details": [ ... ]  # Optional validation details
}
```

### 4. Authentication Middleware
```python
from functools import wraps
from flask import g, abort
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models import User, Tenant

def require_permission(permission):
    """Decorator to check user has permission."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not g.current_user.has_permission(permission):
                abort(403, description=f"Permission denied: {permission}")
            return f(*args, **kwargs)
        return wrapper
    return decorator

def init_tenant_context():
    """Middleware to set tenant context from JWT."""
    verify_jwt_in_request()
    identity = get_jwt_identity()
    
    user = User.query.get(identity['user_id'])
    if not user or not user.is_active:
        abort(401, description="Invalid user")
    
    tenant = Tenant.query.get(identity['tenant_id'])
    if not tenant or not tenant.is_active:
        abort(401, description="Invalid tenant")
    
    g.current_user = user
    g.tenant = tenant
    g.tenant_schema = f"tenant_{tenant.slug}"
```

### 5. Error Handling
```python
from flask import Flask, jsonify

def register_error_handlers(app: Flask):
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            'success': False,
            'error': str(e.description) if hasattr(e, 'description') else 'Bad request'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({
            'success': False,
            'error': str(e.description) if hasattr(e, 'description') else 'Forbidden'
        }), 403
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            'success': False,
            'error': 'Resource not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
```

## Reference Files
- [Backend Agent](../../agents/backend-agent.agent.md)
- [Security Agent](../../agents/security-agent.agent.md)
