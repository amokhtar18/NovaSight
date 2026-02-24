"""
NovaSight Auth Constants
========================

Canonical role names, permission delimiters, and public endpoint
definitions. This is the single source of truth for all auth-related
constants across the application.

IMPORTANT: Do not define role names or permission delimiters anywhere
else in the codebase. Always import from this module.
"""

from typing import Dict, FrozenSet

# =============================================================================
# Canonical Role Names
# =============================================================================

ROLE_SUPER_ADMIN = "super_admin"
ROLE_TENANT_ADMIN = "tenant_admin"
ROLE_DATA_ENGINEER = "data_engineer"
ROLE_BI_DEVELOPER = "bi_developer"
ROLE_ANALYST = "analyst"
ROLE_VIEWER = "viewer"
ROLE_AUDITOR = "auditor"

ROLE_NAMES: Dict[str, str] = {
    ROLE_SUPER_ADMIN: "Super Administrator",
    ROLE_TENANT_ADMIN: "Tenant Administrator",
    ROLE_DATA_ENGINEER: "Data Engineer",
    ROLE_BI_DEVELOPER: "BI Developer",
    ROLE_ANALYST: "Analyst",
    ROLE_VIEWER: "Viewer",
    ROLE_AUDITOR: "Auditor",
}

# Roles that have elevated privileges
ADMIN_ROLES: FrozenSet[str] = frozenset({ROLE_SUPER_ADMIN, ROLE_TENANT_ADMIN})

# Roles that bypass tenant-level restrictions
SUPER_ROLES: FrozenSet[str] = frozenset({ROLE_SUPER_ADMIN})

# Ordered role hierarchy (higher index = more privileges)
ROLE_HIERARCHY = [
    ROLE_VIEWER,
    ROLE_ANALYST,
    ROLE_AUDITOR,
    ROLE_BI_DEVELOPER,
    ROLE_DATA_ENGINEER,
    ROLE_TENANT_ADMIN,
    ROLE_SUPER_ADMIN,
]

# =============================================================================
# Permission Delimiter
# =============================================================================

# Standardized permission delimiter — ALWAYS use dot notation
# e.g., "dashboards.create", "semantic.view"
# NEVER use colon notation (e.g., "dashboards:create")
PERMISSION_DELIMITER = "."

# =============================================================================
# Deprecated Role Name Mappings
# =============================================================================
# Maps old/inconsistent role names to canonical names
# Used during migration period only

DEPRECATED_ROLE_MAPPINGS: Dict[str, str] = {
    "admin": ROLE_TENANT_ADMIN,
    "platform_admin": ROLE_SUPER_ADMIN,
}


# =============================================================================
# Public Endpoints (No Auth Required)
# =============================================================================

PUBLIC_ENDPOINTS: FrozenSet[str] = frozenset([
    "health.health_check",
    "health.readiness",
    "health.liveness",
    "api_v1.login",
    "api_v1.register",
    "api_v1.refresh",
    "api_v1.forgot_password",
    "api_v1.reset_password",
])

# Path prefixes for public endpoints
PUBLIC_PATH_PREFIXES = (
    "/health",
    "/ready",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/dagster/health",
)


def normalize_permission(permission: str) -> str:
    """
    Normalize a permission string to use dot notation.

    Args:
        permission: Permission string (may use ':' or '.' delimiter)

    Returns:
        Normalized permission with '.' delimiter
    """
    return permission.replace(":", PERMISSION_DELIMITER)


def normalize_role_name(role: str) -> str:
    """
    Normalize a role name to canonical form.

    Args:
        role: Role name (may be deprecated/inconsistent)

    Returns:
        Canonical role name
    """
    return DEPRECATED_ROLE_MAPPINGS.get(role, role)
