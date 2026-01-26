"""
NovaSight Middleware Package
============================

Request/response middleware and error handlers.
"""

from app.middleware.error_handlers import register_error_handlers
from app.middleware.tenant_context import (
    TenantContextMiddleware,
    require_tenant,
    get_current_tenant,
    get_current_tenant_id,
    get_current_user_id,
    get_user_roles,
    get_user_permissions,
)
from app.middleware.jwt_handlers import register_jwt_handlers
from app.middleware.permissions import (
    require_permission,
    require_any_permission,
    require_all_permissions,
    require_role,
    require_any_role,
    check_permission,
    check_role,
)

__all__ = [
    # Error handlers
    "register_error_handlers",
    # Tenant context
    "TenantContextMiddleware",
    "require_tenant",
    "get_current_tenant",
    "get_current_tenant_id",
    "get_current_user_id",
    "get_user_roles",
    "get_user_permissions",
    # JWT handlers
    "register_jwt_handlers",
    # Permission decorators
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "require_role",
    "require_any_role",
    "check_permission",
    "check_role",
]
