# 031 - RBAC Implementation

## Metadata

```yaml
prompt_id: "031"
phase: 5
agent: "@security"
model: "opus 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["004", "029"]
```

## Objective

Implement comprehensive Role-Based Access Control (RBAC) system with permission inheritance.

## Task Description

Create a flexible RBAC system that supports hierarchical roles, granular permissions, and resource-level access control.

## Requirements

### Permission Models

```python
# backend/app/models/rbac.py
from app.extensions import db
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy import UniqueConstraint

# Association tables
user_roles = db.Table('user_roles',
    db.Column('user_id', UUID(as_uuid=True), db.ForeignKey('users.id')),
    db.Column('role_id', UUID(as_uuid=True), db.ForeignKey('roles.id')),
    UniqueConstraint('user_id', 'role_id')
)

role_permissions = db.Table('role_permissions',
    db.Column('role_id', UUID(as_uuid=True), db.ForeignKey('roles.id')),
    db.Column('permission_id', UUID(as_uuid=True), db.ForeignKey('permissions.id')),
    UniqueConstraint('role_id', 'permission_id')
)

class Role(db.Model):
    """Role definition with hierarchical support."""
    __tablename__ = 'roles'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.id'))
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    
    # Hierarchy support
    parent_id = db.Column(UUID(as_uuid=True), db.ForeignKey('roles.id'))
    level = db.Column(db.Integer, default=0)  # 0 = highest
    
    is_system = db.Column(db.Boolean, default=False)  # Can't be deleted
    is_default = db.Column(db.Boolean, default=False)  # Auto-assigned to new users
    
    # Relationships
    permissions = db.relationship(
        'Permission',
        secondary=role_permissions,
        backref='roles'
    )
    children = db.relationship(
        'Role',
        backref=db.backref('parent', remote_side=[id])
    )
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name'),
    )
    
    def get_all_permissions(self) -> set:
        """Get all permissions including inherited from parent."""
        perms = set(p.name for p in self.permissions)
        if self.parent:
            perms.update(self.parent.get_all_permissions())
        return perms

class Permission(db.Model):
    """Permission definition."""
    __tablename__ = 'permissions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # datasources, analytics, admin, etc.
    
    # Resource-specific permissions can use patterns
    # e.g., "datasources.{id}.view" or "dashboards.*.edit"

class ResourcePermission(db.Model):
    """Resource-level permissions (beyond role-based)."""
    __tablename__ = 'resource_permissions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    resource_type = db.Column(db.String(50))  # dashboard, datasource, etc.
    resource_id = db.Column(UUID(as_uuid=True))
    permission = db.Column(db.String(20))  # view, edit, admin, owner
    
    granted_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    granted_at = db.Column(db.DateTime, default=db.func.now())
```

### RBAC Service

```python
# backend/app/services/rbac_service.py
from typing import List, Set, Optional
from functools import lru_cache
from app.models.rbac import Role, Permission, ResourcePermission
from app.models import User

class RBACService:
    """Service for role-based access control."""
    
    # Default permissions by category
    DEFAULT_PERMISSIONS = {
        'datasources': [
            'datasources.view',
            'datasources.create',
            'datasources.edit',
            'datasources.delete',
            'datasources.sync',
        ],
        'semantic': [
            'semantic.view',
            'semantic.create',
            'semantic.edit',
            'semantic.delete',
        ],
        'analytics': [
            'analytics.query',
            'analytics.export',
        ],
        'dashboards': [
            'dashboards.view',
            'dashboards.create',
            'dashboards.edit',
            'dashboards.delete',
            'dashboards.share',
        ],
        'users': [
            'users.view',
            'users.create',
            'users.edit',
            'users.delete',
        ],
        'roles': [
            'roles.view',
            'roles.create',
            'roles.edit',
            'roles.delete',
        ],
        'admin': [
            'admin.tenants.view',
            'admin.tenants.create',
            'admin.tenants.edit',
            'admin.tenants.delete',
        ],
    }
    
    # Default roles
    DEFAULT_ROLES = {
        'admin': {
            'description': 'Full access to all features',
            'permissions': ['*'],  # All permissions
        },
        'analyst': {
            'description': 'Can view data and create dashboards',
            'permissions': [
                'datasources.view',
                'semantic.view',
                'analytics.query',
                'analytics.export',
                'dashboards.*',
            ],
        },
        'viewer': {
            'description': 'Read-only access to dashboards',
            'permissions': [
                'dashboards.view',
                'analytics.query',
            ],
        },
    }
    
    @classmethod
    def get_user_permissions(cls, user: User) -> Set[str]:
        """Get all effective permissions for a user."""
        permissions = set()
        
        # Get permissions from all roles
        for role in user.roles:
            permissions.update(role.get_all_permissions())
        
        return permissions
    
    @classmethod
    def check_permission(
        cls,
        user: User,
        permission: str,
        resource_type: str = None,
        resource_id: str = None
    ) -> bool:
        """Check if user has a specific permission."""
        user_perms = cls.get_user_permissions(user)
        
        # Check for wildcard permissions
        if '*' in user_perms:
            return True
        
        # Check direct permission
        if permission in user_perms:
            return True
        
        # Check category wildcard (e.g., "dashboards.*")
        category = permission.split('.')[0]
        if f'{category}.*' in user_perms:
            return True
        
        # Check resource-specific permission
        if resource_type and resource_id:
            return cls.check_resource_permission(
                user.id, resource_type, resource_id, permission
            )
        
        return False
    
    @classmethod
    def check_resource_permission(
        cls,
        user_id: str,
        resource_type: str,
        resource_id: str,
        required_permission: str
    ) -> bool:
        """Check resource-level permission."""
        rp = ResourcePermission.query.filter_by(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id
        ).first()
        
        if not rp:
            return False
        
        # Permission hierarchy: owner > admin > edit > view
        permission_hierarchy = ['owner', 'admin', 'edit', 'view']
        
        action = required_permission.split('.')[-1]
        if rp.permission in permission_hierarchy:
            user_level = permission_hierarchy.index(rp.permission)
            required_level = permission_hierarchy.index(action) if action in permission_hierarchy else 999
            return user_level <= required_level
        
        return False
    
    @classmethod
    def grant_resource_permission(
        cls,
        user_id: str,
        resource_type: str,
        resource_id: str,
        permission: str,
        granted_by: str
    ) -> ResourcePermission:
        """Grant resource-level permission to a user."""
        rp = ResourcePermission(
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            permission=permission,
            granted_by=granted_by
        )
        db.session.add(rp)
        db.session.commit()
        return rp
    
    @classmethod
    def initialize_tenant_roles(cls, tenant_id: str) -> List[Role]:
        """Create default roles for a new tenant."""
        roles = []
        
        for role_name, config in cls.DEFAULT_ROLES.items():
            role = Role(
                tenant_id=tenant_id,
                name=role_name,
                description=config['description'],
                is_system=True,
                is_default=(role_name == 'viewer'),
            )
            
            # Assign permissions
            for perm_pattern in config['permissions']:
                if perm_pattern == '*':
                    role.permissions = Permission.query.all()
                    break
                elif perm_pattern.endswith('.*'):
                    category = perm_pattern[:-2]
                    role.permissions.extend(
                        Permission.query.filter(
                            Permission.name.like(f'{category}.%')
                        ).all()
                    )
                else:
                    perm = Permission.query.filter_by(name=perm_pattern).first()
                    if perm:
                        role.permissions.append(perm)
            
            db.session.add(role)
            roles.append(role)
        
        db.session.commit()
        return roles
```

### Permission Decorators

```python
# backend/app/middleware/permissions.py
from functools import wraps
from flask import g, abort
from app.services.rbac_service import RBACService

def require_permission(permission: str):
    """Decorator to require a specific permission."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not hasattr(g, 'current_user') or not g.current_user:
                abort(401, description="Authentication required")
            
            if not RBACService.check_permission(g.current_user, permission):
                abort(403, description=f"Permission denied: {permission}")
            
            return f(*args, **kwargs)
        return wrapper
    return decorator

def require_resource_permission(resource_type: str, id_param: str = 'id'):
    """Decorator to require resource-level permission."""
    def decorator(permission: str):
        def inner_decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                resource_id = kwargs.get(id_param)
                
                if not RBACService.check_permission(
                    g.current_user,
                    permission,
                    resource_type=resource_type,
                    resource_id=str(resource_id)
                ):
                    abort(403, description=f"Permission denied for {resource_type}")
                
                return f(*args, **kwargs)
            return wrapper
        return inner_decorator
    return decorator

# Usage:
# @require_permission('dashboards.view')
# @require_resource_permission('dashboard', 'dashboard_id')('dashboards.edit')
```

## Expected Output

```
backend/app/
├── models/
│   └── rbac.py
├── services/
│   └── rbac_service.py
├── middleware/
│   └── permissions.py
└── migrations/
    └── versions/
        └── xxx_add_rbac_tables.py
```

## Acceptance Criteria

- [ ] Permission checks work correctly
- [ ] Role inheritance works
- [ ] Wildcard permissions work
- [ ] Resource-level permissions work
- [ ] Default roles created for new tenants
- [ ] Permission decorators work on endpoints
- [ ] Permission caching for performance
- [ ] API returns 403 for unauthorized access

## Reference Documents

- [Security Agent](../agents/security-agent.agent.md)
- [User Management API](./029-user-management-api.md)
