"""
NovaSight RBAC Service
======================

Canonical location: ``app.domains.identity.application.rbac_service``

Role-Based Access Control with permission inheritance,
resource-level permissions, and permission caching.

Uses ``domains.identity.domain.rules`` for pure permission logic.
"""

import uuid
from datetime import datetime
from typing import List, Set, Optional, Dict, Any
from sqlalchemy import and_

from app.extensions import db
from app.domains.identity.domain.models import (
    User,
    Role,
    Permission,
    ResourcePermission,
    RoleHierarchy,
    role_permissions,
    get_all_permissions,
)
from app.domains.identity.domain.rules import (
    matches_permission,
    action_to_resource_level,
)

import logging

logger = logging.getLogger(__name__)


class RBACService:
    """
    Service for role-based access control.

    Provides:
    - Permission checking (role-based and resource-based)
    - Permission inheritance through role hierarchy
    - Resource-level permission management
    - Default role/permission initialization for tenants
    - Permission caching for performance
    """

    # Default permissions by category
    DEFAULT_PERMISSIONS = {
        "datasources": [
            "datasources.view",
            "datasources.create",
            "datasources.edit",
            "datasources.delete",
            "datasources.sync",
            "datasources.test",
        ],
        "semantic": [
            "semantic.view",
            "semantic.create",
            "semantic.edit",
            "semantic.delete",
            "semantic.deploy",
        ],
        "analytics": [
            "analytics.query",
            "analytics.export",
            "analytics.schedule",
        ],
        "charts": [
            "charts.view",
            "charts.create",
            "charts.edit",
            "charts.delete",
            "charts.share",
        ],
        "dashboards": [
            "dashboards.view",
            "dashboards.create",
            "dashboards.edit",
            "dashboards.delete",
            "dashboards.share",
            "dashboards.publish",
        ],
        "pipelines": [
            "pipelines.view",
            "pipelines.create",
            "pipelines.edit",
            "pipelines.delete",
            "pipelines.deploy",
            "pipelines.trigger",
        ],
        "users": [
            "users.view",
            "users.create",
            "users.edit",
            "users.delete",
            "users.invite",
        ],
        "roles": [
            "roles.view",
            "roles.create",
            "roles.edit",
            "roles.delete",
            "roles.assign",
        ],
        "admin": [
            "admin.settings.view",
            "admin.settings.edit",
            "admin.audit.view",
            "admin.tenants.view",
            "admin.tenants.create",
            "admin.tenants.edit",
            "admin.tenants.delete",
            "admin.infrastructure.view",
            "admin.infrastructure.create",
            "admin.infrastructure.edit",
            "admin.infrastructure.delete",
            "admin.infrastructure.test",
        ],
    }

    # Default roles with their permissions
    DEFAULT_ROLES = {
        "super_admin": {
            "display_name": "Super Administrator",
            "description": "Full platform access across all tenants",
            "permissions": ["*"],
            "is_system": True,
            "level": 0,
        },
        "tenant_admin": {
            "display_name": "Tenant Administrator",
            "description": "Full access within the tenant",
            "permissions": [
                "datasources.*",
                "semantic.*",
                "analytics.*",
                "charts.*",
                "dashboards.*",
                "pipelines.*",
                "users.*",
                "roles.view",
                "roles.assign",
                "admin.settings.*",
                "admin.audit.view",
                "admin.infrastructure.*",
            ],
            "is_system": True,
            "level": 1,
        },
        "data_engineer": {
            "display_name": "Data Engineer",
            "description": "Can manage data sources and pipelines",
            "permissions": [
                "datasources.*",
                "semantic.*",
                "pipelines.*",
                "analytics.query",
                "analytics.export",
                "charts.view",
                "dashboards.view",
            ],
            "is_system": True,
            "level": 2,
        },
        "bi_developer": {
            "display_name": "BI Developer",
            "description": "Can create and manage dashboards and analytics",
            "permissions": [
                "datasources.view",
                "semantic.view",
                "analytics.*",
                "charts.*",
                "dashboards.*",
            ],
            "is_system": True,
            "level": 2,
        },
        "analyst": {
            "display_name": "Analyst",
            "description": "Can view data and create personal dashboards",
            "permissions": [
                "datasources.view",
                "semantic.view",
                "analytics.query",
                "analytics.export",
                "charts.view",
                "charts.create",
                "dashboards.view",
                "dashboards.create",
            ],
            "is_system": True,
            "level": 3,
        },
        "viewer": {
            "display_name": "Viewer",
            "description": "Read-only access to dashboards",
            "permissions": [
                "charts.view",
                "dashboards.view",
                "analytics.query",
            ],
            "is_system": True,
            "is_default": True,
            "level": 4,
        },
    }

    # In-memory permission cache (will move to Redis in a future iteration)
    _permission_cache: Dict[str, Set[str]] = {}

    @classmethod
    def clear_cache(cls, user_id: Optional[str] = None) -> None:
        """Clear the permission cache."""
        if user_id:
            cls._permission_cache.pop(str(user_id), None)
        else:
            cls._permission_cache.clear()

    @classmethod
    def get_user_permissions(cls, user: User, use_cache: bool = True) -> Set[str]:
        """
        Get all effective permissions for a user.

        Combines permissions from all assigned roles + inherited.
        """
        user_id_str = str(user.id)

        if use_cache and user_id_str in cls._permission_cache:
            return cls._permission_cache[user_id_str]

        permissions: Set[str] = set()
        for role in user.roles:
            role_perms = get_all_permissions(role)
            permissions.update(role_perms)

        cls._permission_cache[user_id_str] = permissions
        return permissions

    @classmethod
    def check_permission(
        cls,
        user: User,
        permission: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> bool:
        """
        Check if user has a specific permission.

        Delegates wildcard / hierarchy logic to ``domain.rules.matches_permission``.
        Falls back to resource-level check when resource is specified.
        """
        user_perms = cls.get_user_permissions(user)

        if matches_permission(user_perms, permission):
            return True

        # Resource-specific permission check
        if resource_type and resource_id:
            return cls.check_resource_permission(
                str(user.id), resource_type, resource_id, permission,
            )

        return False

    @classmethod
    def check_resource_permission(
        cls,
        user_id: str,
        resource_type: str,
        resource_id: str,
        required_permission: str,
    ) -> bool:
        """Check resource-level permission."""
        try:
            rp = ResourcePermission.query.filter(
                and_(
                    ResourcePermission.user_id == uuid.UUID(user_id),
                    ResourcePermission.resource_type == resource_type,
                    ResourcePermission.resource_id == uuid.UUID(resource_id),
                )
            ).first()

            if not rp or rp.is_expired():
                return False

            action = (
                required_permission.split(".")[-1]
                if "." in required_permission
                else required_permission
            )
            required_level = action_to_resource_level(action)
            return rp.has_level(required_level)

        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid UUID in resource permission check: {e}")
            return False

    # ── Resource permission management ────────────────

    @classmethod
    def grant_resource_permission(
        cls,
        user_id: str,
        resource_type: str,
        resource_id: str,
        permission: str,
        granted_by: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> ResourcePermission:
        """Grant resource-level permission to a user."""
        existing = ResourcePermission.query.filter(
            and_(
                ResourcePermission.user_id == uuid.UUID(user_id),
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == uuid.UUID(resource_id),
            )
        ).first()

        if existing:
            existing.permission = permission
            existing.granted_by = uuid.UUID(granted_by) if granted_by else None
            existing.granted_at = datetime.utcnow()
            existing.expires_at = expires_at
            db.session.commit()
            logger.info(
                f"Updated resource permission: {permission} on "
                f"{resource_type}:{resource_id} for user {user_id}"
            )
            return existing

        rp = ResourcePermission(
            user_id=uuid.UUID(user_id),
            resource_type=resource_type,
            resource_id=uuid.UUID(resource_id),
            permission=permission,
            granted_by=uuid.UUID(granted_by) if granted_by else None,
            expires_at=expires_at,
        )
        db.session.add(rp)
        db.session.commit()
        logger.info(
            f"Granted resource permission: {permission} on "
            f"{resource_type}:{resource_id} for user {user_id}"
        )
        return rp

    @classmethod
    def revoke_resource_permission(
        cls,
        user_id: str,
        resource_type: str,
        resource_id: str,
    ) -> bool:
        """Revoke resource-level permission from a user."""
        result = ResourcePermission.query.filter(
            and_(
                ResourcePermission.user_id == uuid.UUID(user_id),
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == uuid.UUID(resource_id),
            )
        ).delete()
        db.session.commit()

        if result:
            logger.info(
                f"Revoked resource permission on {resource_type}:{resource_id} "
                f"for user {user_id}"
            )
        return result > 0

    @classmethod
    def get_resource_permissions(
        cls,
        resource_type: str,
        resource_id: str,
    ) -> List[ResourcePermission]:
        """Get all permissions for a specific resource."""
        return ResourcePermission.query.filter(
            and_(
                ResourcePermission.resource_type == resource_type,
                ResourcePermission.resource_id == uuid.UUID(resource_id),
            )
        ).all()

    @classmethod
    def get_user_resource_permissions(
        cls,
        user_id: str,
        resource_type: Optional[str] = None,
    ) -> List[ResourcePermission]:
        """Get all resource permissions for a user."""
        query = ResourcePermission.query.filter(
            ResourcePermission.user_id == uuid.UUID(user_id),
        )
        if resource_type:
            query = query.filter(ResourcePermission.resource_type == resource_type)
        return query.all()

    # ── Initialization ────────────────────────────────

    @classmethod
    def initialize_permissions(cls) -> List[Permission]:
        """Initialize system permissions in the database."""
        created = []
        for category, perms in cls.DEFAULT_PERMISSIONS.items():
            for perm_name in perms:
                existing = Permission.query.filter_by(name=perm_name).first()
                if not existing:
                    permission = Permission(
                        name=perm_name,
                        description=f"Permission to {perm_name.split('.')[-1]} {category}",
                        category=category,
                        is_system=True,
                    )
                    db.session.add(permission)
                    created.append(permission)

        if created:
            db.session.commit()
            logger.info(f"Initialized {len(created)} system permissions")
        return created

    @classmethod
    def initialize_tenant_roles(cls, tenant_id: str) -> List[Role]:
        """Create default roles for a new tenant."""
        roles = []
        tenant_uuid = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id

        for role_name, config in cls.DEFAULT_ROLES.items():
            if role_name == "super_admin":
                continue

            existing = Role.query.filter(
                and_(Role.name == role_name, Role.tenant_id == tenant_uuid)
            ).first()
            if existing:
                continue

            permissions_dict = cls._expand_permission_patterns(config["permissions"])

            role = Role(
                name=role_name,
                display_name=config["display_name"],
                description=config["description"],
                permissions=permissions_dict,
                is_system=config.get("is_system", True),
                is_default=config.get("is_default", False),
                tenant_id=tenant_uuid,
            )
            db.session.add(role)
            roles.append(role)

        if roles:
            db.session.commit()
            logger.info(f"Initialized {len(roles)} roles for tenant {tenant_id}")
        return roles

    @classmethod
    def _expand_permission_patterns(cls, patterns: List[str]) -> Dict[str, Any]:
        """Expand permission patterns into a permissions dictionary."""
        permissions: Dict[str, Any] = {}

        for pattern in patterns:
            if pattern == "*":
                for category, perms in cls.DEFAULT_PERMISSIONS.items():
                    permissions[category] = perms
                break
            elif pattern.endswith(".*"):
                category = pattern[:-2]
                if category in cls.DEFAULT_PERMISSIONS:
                    permissions[category] = cls.DEFAULT_PERMISSIONS[category]
            else:
                parts = pattern.split(".")
                if len(parts) >= 2:
                    category = parts[0]
                    if category not in permissions:
                        permissions[category] = []
                    if pattern not in permissions[category]:
                        permissions[category].append(pattern)

        return permissions

    # ── Role assignment ───────────────────────────────

    @classmethod
    def assign_role_to_user(
        cls,
        user: User,
        role_name: str,
        assigned_by: Optional[str] = None,
    ) -> bool:
        """Assign a role to a user."""
        role = Role.query.filter(
            and_(Role.name == role_name, Role.tenant_id == user.tenant_id)
        ).first()

        if not role:
            role = Role.query.filter(
                and_(Role.name == role_name, Role.tenant_id.is_(None))
            ).first()

        if not role:
            logger.warning(f"Role not found: {role_name}")
            return False

        if role in user.roles:
            logger.info(f"User {user.id} already has role {role_name}")
            return False

        user.roles.append(role)
        db.session.commit()
        cls.clear_cache(str(user.id))

        logger.info(f"Assigned role {role_name} to user {user.id}")
        return True

    @classmethod
    def remove_role_from_user(cls, user: User, role_name: str) -> bool:
        """Remove a role from a user."""
        role = next((r for r in user.roles if r.name == role_name), None)
        if not role:
            return False

        user.roles.remove(role)
        db.session.commit()
        cls.clear_cache(str(user.id))

        logger.info(f"Removed role {role_name} from user {user.id}")
        return True

    @classmethod
    def create_role_hierarchy(
        cls,
        parent_role_id: str,
        child_role_id: str,
    ) -> RoleHierarchy:
        """Create a role hierarchy relationship."""
        hierarchy = RoleHierarchy(
            parent_role_id=uuid.UUID(parent_role_id),
            child_role_id=uuid.UUID(child_role_id),
        )
        db.session.add(hierarchy)
        db.session.commit()
        cls.clear_cache()
        return hierarchy


# Singleton
rbac_service = RBACService()
