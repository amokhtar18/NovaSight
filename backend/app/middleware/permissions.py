"""
NovaSight Permission Decorators
===============================

RBAC permission decorators for endpoint authorization.
"""

from functools import wraps
from flask import g, abort
from typing import List, Union
import logging

logger = logging.getLogger(__name__)


def require_permission(permission: str):
    """
    Decorator to check user has a specific permission.
    
    Args:
        permission: Required permission string (e.g., "connections:create")
    
    Usage:
        @app.route('/api/v1/connections', methods=['POST'])
        @jwt_required()
        @require_permission('connections:create')
        def create_connection():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_permissions = getattr(g, 'user_permissions', [])
            
            # Check for wildcard admin permission
            if '*' in user_permissions or 'admin:*' in user_permissions:
                return f(*args, **kwargs)
            
            # Check for specific permission
            if permission not in user_permissions:
                logger.warning(
                    f"Permission denied: {permission} for user {g.get('current_user_id')}"
                )
                abort(403, description=f"Permission denied: {permission}")
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permissions: str):
    """
    Decorator to check user has any of the specified permissions.
    
    Args:
        *permissions: Variable permission strings
    
    Usage:
        @app.route('/api/v1/reports')
        @jwt_required()
        @require_any_permission('reports:read', 'reports:admin')
        def get_reports():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_permissions = getattr(g, 'user_permissions', [])
            
            # Check for wildcard admin permission
            if '*' in user_permissions or 'admin:*' in user_permissions:
                return f(*args, **kwargs)
            
            # Check for any matching permission
            if not any(p in user_permissions for p in permissions):
                logger.warning(
                    f"Permission denied: none of {permissions} for user {g.get('current_user_id')}"
                )
                abort(403, description="Permission denied")
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(*permissions: str):
    """
    Decorator to check user has all of the specified permissions.
    
    Args:
        *permissions: Variable permission strings (all required)
    
    Usage:
        @app.route('/api/v1/admin/dangerous')
        @jwt_required()
        @require_all_permissions('admin:access', 'admin:dangerous')
        def dangerous_action():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_permissions = getattr(g, 'user_permissions', [])
            
            # Check for wildcard admin permission
            if '*' in user_permissions or 'admin:*' in user_permissions:
                return f(*args, **kwargs)
            
            # Check all permissions are present
            missing = [p for p in permissions if p not in user_permissions]
            if missing:
                logger.warning(
                    f"Permission denied: missing {missing} for user {g.get('current_user_id')}"
                )
                abort(403, description=f"Missing permissions: {', '.join(missing)}")
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_role(role: str):
    """
    Decorator to check user has a specific role.
    
    Args:
        role: Required role name (e.g., "tenant_admin")
    
    Usage:
        @app.route('/api/v1/admin/users')
        @jwt_required()
        @require_role('tenant_admin')
        def manage_users():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_roles = getattr(g, 'user_roles', [])
            
            if role not in user_roles:
                logger.warning(
                    f"Role denied: {role} for user {g.get('current_user_id')}"
                )
                abort(403, description=f"Role required: {role}")
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def require_any_role(*roles: str):
    """
    Decorator to check user has any of the specified roles.
    
    Args:
        *roles: Variable role names
    
    Usage:
        @app.route('/api/v1/settings')
        @jwt_required()
        @require_any_role('tenant_admin', 'super_admin')
        def manage_settings():
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_roles = getattr(g, 'user_roles', [])
            
            if not any(r in user_roles for r in roles):
                logger.warning(
                    f"Role denied: none of {roles} for user {g.get('current_user_id')}"
                )
                abort(403, description=f"One of these roles required: {', '.join(roles)}")
            
            return f(*args, **kwargs)
        return wrapper
    return decorator


def check_permission(permission: str) -> bool:
    """
    Check if current user has a permission (non-decorator version).
    
    Args:
        permission: Permission to check
    
    Returns:
        True if user has permission
    """
    user_permissions = getattr(g, 'user_permissions', [])
    return (
        '*' in user_permissions or
        'admin:*' in user_permissions or
        permission in user_permissions
    )


def check_role(role: str) -> bool:
    """
    Check if current user has a role (non-decorator version).
    
    Args:
        role: Role to check
    
    Returns:
        True if user has role
    """
    user_roles = getattr(g, 'user_roles', [])
    return role in user_roles
