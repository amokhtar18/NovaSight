"""
NovaSight Decorators
====================

Custom decorators for authorization and request handling.
"""

from functools import wraps
from flask import request, g
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.errors import AuthorizationError, AuthenticationError
import logging

logger = logging.getLogger(__name__)


def require_roles(allowed_roles: list):
    """
    Decorator to require specific roles for endpoint access.
    
    Args:
        allowed_roles: List of role names that can access the endpoint
    
    Usage:
        @require_roles(["admin", "data_engineer"])
        def my_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identity = get_jwt_identity()
            
            if not identity:
                raise AuthenticationError("Authentication required")
            
            user_roles = identity.get("roles", [])
            
            # Super admin can access everything
            if "super_admin" in user_roles:
                return f(*args, **kwargs)
            
            # Check if user has any of the allowed roles
            if not any(role in user_roles for role in allowed_roles):
                logger.warning(
                    f"Access denied for user {identity.get('email')}: "
                    f"required roles {allowed_roles}, has {user_roles}"
                )
                raise AuthorizationError(
                    f"Access denied. Required roles: {', '.join(allowed_roles)}"
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def require_tenant_context(f):
    """
    Decorator to ensure tenant context is available.
    
    Sets g.tenant_id from JWT identity for use in request handlers.
    
    Usage:
        @require_tenant_context
        def my_endpoint():
            tenant_id = g.tenant_id
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        identity = get_jwt_identity()
        
        if not identity:
            raise AuthenticationError("Authentication required")
        
        tenant_id = identity.get("tenant_id")
        
        if not tenant_id:
            raise AuthorizationError("Tenant context required")
        
        # Store in Flask g object for request-scoped access
        g.tenant_id = tenant_id
        g.user_id = identity.get("user_id")
        g.user_email = identity.get("email")
        g.user_roles = identity.get("roles", [])
        
        return f(*args, **kwargs)
    
    return decorated_function


def audit_action(action: str, resource_type: str = None):
    """
    Decorator to automatically log audit trail for endpoint actions.
    
    Args:
        action: The action being performed (e.g., "create", "update", "delete")
        resource_type: The type of resource being acted upon
    
    Usage:
        @audit_action("create", "dag")
        def create_dag():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from app.services.audit_service import AuditService
            
            identity = get_jwt_identity() or {}
            tenant_id = identity.get("tenant_id")
            user_id = identity.get("user_id")
            
            # Get request context
            ip_address = request.remote_addr
            user_agent = request.user_agent.string if request.user_agent else None
            
            # Execute the actual function
            try:
                result = f(*args, **kwargs)
                
                # Log successful action
                AuditService.log(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    resource_id=kwargs.get("dag_id") or kwargs.get("connection_id") or kwargs.get("user_id"),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=True,
                )
                
                return result
                
            except Exception as e:
                # Log failed action
                AuditService.log(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    action=action,
                    resource_type=resource_type,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    error_message=str(e),
                )
                raise
        
        return decorated_function
    return decorator
