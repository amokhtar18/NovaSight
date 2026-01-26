"""
NovaSight Tenant Context Middleware
===================================

Middleware for extracting and validating tenant context from requests.
Ensures complete data isolation between tenants.
"""

from flask import Flask, g, request, abort
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
from sqlalchemy import text
from functools import wraps
from typing import Optional, List
import logging

from app.extensions import db

logger = logging.getLogger(__name__)

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = frozenset([
    "health.health_check",
    "health.readiness",
    "health.liveness",
    "api_v1.login",
    "api_v1.register",
    "api_v1.refresh",
])

# Path prefixes for public endpoints
PUBLIC_PATH_PREFIXES = (
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
)


class TenantContextMiddleware:
    """
    Middleware to extract tenant context from JWT claims.
    
    Responsibilities:
    - Extract tenant_id from JWT claims
    - Validate tenant exists and is active
    - Set PostgreSQL search_path for schema isolation
    - Store tenant context in Flask g object
    """
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize middleware with Flask app."""
        app.before_request(self._init_tenant_context)
        app.teardown_request(self._cleanup_tenant_context)
    
    def _init_tenant_context(self) -> None:
        """Initialize tenant context from JWT before each request."""
        # Initialize default context
        g.tenant = None
        g.tenant_id = None
        g.tenant_schema = "public"
        g.current_user_id = None
        g.user_roles = []
        g.user_permissions = []
        
        # Skip for public endpoints
        if self._is_public_endpoint():
            return
        
        try:
            # Verify JWT and extract claims
            verify_jwt_in_request()
            claims = get_jwt()
            identity = get_jwt_identity()
            
            tenant_id = None
            if isinstance(identity, dict):
                tenant_id = identity.get("tenant_id")
            elif claims:
                tenant_id = claims.get("tenant_id")
            
            if not tenant_id:
                logger.warning("Missing tenant_id in JWT claims")
                abort(401, description="Missing tenant context")
            
            # Load and validate tenant
            from app.models.tenant import Tenant, TenantStatus
            tenant = db.session.get(Tenant, tenant_id)
            
            if not tenant:
                logger.warning(f"Tenant not found: {tenant_id}")
                abort(401, description="Invalid tenant")
            
            if tenant.status != TenantStatus.ACTIVE:
                logger.warning(f"Inactive tenant access attempt: {tenant.slug}")
                abort(401, description="Tenant is not active")
            
            # Set tenant context
            g.tenant = tenant
            g.tenant_id = str(tenant.id)
            g.tenant_schema = f"tenant_{tenant.slug}"
            
            # Set user context from JWT
            if isinstance(identity, dict):
                g.current_user_id = identity.get("user_id")
                g.user_roles = identity.get("roles", [])
            
            g.user_permissions = claims.get("permissions", [])
            
            # Set PostgreSQL search_path for schema isolation
            self._set_search_path(g.tenant_schema)
            
            logger.debug(f"Tenant context set: {tenant.slug} (schema: {g.tenant_schema})")
            
        except Exception as e:
            if hasattr(e, 'code') and e.code in (401, 403):
                raise
            logger.error(f"Error initializing tenant context: {e}")
            abort(401, description="Authentication required")
    
    def _set_search_path(self, tenant_schema: str) -> None:
        """
        Set PostgreSQL search_path to tenant schema.
        
        This ensures all queries are scoped to the tenant's schema.
        """
        try:
            # Sanitize schema name to prevent SQL injection
            if not tenant_schema.replace("_", "").isalnum():
                raise ValueError(f"Invalid schema name: {tenant_schema}")
            
            db.session.execute(
                text(f"SET search_path TO {tenant_schema}, public")
            )
            logger.debug(f"Search path set to: {tenant_schema}, public")
        except Exception as e:
            logger.error(f"Failed to set search_path: {e}")
            # Don't abort - schema might not exist yet for new tenants
    
    def _is_public_endpoint(self) -> bool:
        """Check if current endpoint is public (no auth required)."""
        # Check by endpoint name
        if request.endpoint in PUBLIC_ENDPOINTS:
            return True
        
        # Check by path prefix
        return request.path.startswith(PUBLIC_PATH_PREFIXES)
    
    def _cleanup_tenant_context(self, exception=None) -> None:
        """Cleanup tenant context after request."""
        # Reset search_path to public
        try:
            if g.get("tenant_schema") and g.tenant_schema != "public":
                db.session.execute(text("SET search_path TO public"))
        except Exception:
            pass
        
        # Clear context variables
        for attr in ("tenant", "tenant_id", "tenant_schema", 
                     "current_user_id", "user_roles", "user_permissions"):
            g.pop(attr, None)


def require_tenant(f):
    """
    Decorator to require valid tenant context for an endpoint.
    
    Usage:
        @app.route('/api/v1/data')
        @jwt_required()
        @require_tenant
        def get_data():
            tenant = g.tenant
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not getattr(g, 'tenant', None):
            abort(401, description="Tenant context required")
        return f(*args, **kwargs)
    return decorated_function


def get_current_tenant():
    """Get the current tenant from request context."""
    return getattr(g, 'tenant', None)


def get_current_tenant_id() -> Optional[str]:
    """Get the current tenant ID from request context."""
    return getattr(g, 'tenant_id', None)


def get_current_user_id() -> Optional[str]:
    """Get the current user ID from request context."""
    return getattr(g, 'current_user_id', None)


def get_user_roles() -> List[str]:
    """Get the current user's roles from request context."""
    return getattr(g, 'user_roles', [])


def get_user_permissions() -> List[str]:
    """Get the current user's permissions from request context."""
    return getattr(g, 'user_permissions', [])


def get_current_tenant_id() -> Optional[str]:
    """Get the current tenant ID from request context."""
    return getattr(g, 'tenant_id', None)


def get_current_tenant_slug() -> Optional[str]:
    """Get the current tenant slug from request context."""
    return getattr(g, 'tenant_slug', None)
