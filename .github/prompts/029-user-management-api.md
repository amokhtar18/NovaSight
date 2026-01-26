# 029 - User Management API

## Metadata

```yaml
prompt_id: "029"
phase: 5
agent: "@admin"
model: "haiku 4.5"
priority: P1
estimated_effort: "2 days"
dependencies: ["004", "028"]
```

## Objective

Implement user management API for tenant administrators.

## Task Description

Create REST endpoints for managing users within a tenant including roles and permissions.

## Requirements

### User Management Service

```python
# backend/app/services/user_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models import User, Role, Permission
from app.services.password_service import PasswordService
from app.extensions import db

class UserService:
    """Service for user management within a tenant."""
    
    def __init__(self):
        self.password_service = PasswordService()
    
    @classmethod
    def list_for_tenant(
        cls,
        tenant_id: str,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """List all users for a tenant."""
        query = User.query.filter_by(tenant_id=tenant_id)
        
        if search:
            query = query.filter(
                User.email.ilike(f'%{search}%') |
                User.name.ilike(f'%{search}%')
            )
        
        if role:
            query = query.join(User.roles).filter(Role.name == role)
        
        pagination = query.paginate(page=page, per_page=per_page)
        
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
        }
    
    def create(
        self,
        tenant_id: str,
        email: str,
        name: str,
        password: str,
        roles: List[str] = None
    ) -> User:
        """Create a new user."""
        # Validate password strength
        is_valid, message = self.password_service.validate_strength(password)
        if not is_valid:
            raise ValueError(message)
        
        # Check email uniqueness within tenant
        existing = User.query.filter_by(
            tenant_id=tenant_id, 
            email=email
        ).first()
        if existing:
            raise ValueError("Email already exists")
        
        user = User(
            tenant_id=tenant_id,
            email=email,
            name=name,
            password_hash=self.password_service.hash(password),
            is_active=True
        )
        
        # Assign roles
        if roles:
            role_objects = Role.query.filter(
                Role.tenant_id == tenant_id,
                Role.name.in_(roles)
            ).all()
            user.roles = role_objects
        else:
            # Assign default role
            default_role = Role.query.filter_by(
                tenant_id=tenant_id,
                is_default=True
            ).first()
            if default_role:
                user.roles = [default_role]
        
        db.session.add(user)
        db.session.commit()
        
        return user
    
    def update(
        self,
        user_id: str,
        tenant_id: str,
        **kwargs
    ) -> User:
        """Update user details."""
        user = User.query.filter_by(
            id=user_id,
            tenant_id=tenant_id
        ).first_or_404()
        
        if 'password' in kwargs:
            is_valid, message = self.password_service.validate_strength(
                kwargs['password']
            )
            if not is_valid:
                raise ValueError(message)
            user.password_hash = self.password_service.hash(kwargs.pop('password'))
        
        if 'roles' in kwargs:
            role_names = kwargs.pop('roles')
            role_objects = Role.query.filter(
                Role.tenant_id == tenant_id,
                Role.name.in_(role_names)
            ).all()
            user.roles = role_objects
        
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return user
    
    def deactivate(self, user_id: str, tenant_id: str) -> User:
        """Deactivate a user."""
        user = User.query.filter_by(
            id=user_id,
            tenant_id=tenant_id
        ).first_or_404()
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return user
    
    def get_permissions(self, user_id: str, tenant_id: str) -> List[str]:
        """Get all permissions for a user (from all roles)."""
        user = User.query.filter_by(
            id=user_id,
            tenant_id=tenant_id
        ).first_or_404()
        
        permissions = set()
        for role in user.roles:
            for permission in role.permissions:
                permissions.add(permission.name)
        
        return list(permissions)
```

### User Management API

```python
# backend/app/api/v1/users.py
from flask import Blueprint, request, g
from app.schemas.user_schemas import (
    UserSchema,
    UserCreateSchema,
    UserUpdateSchema,
    UserListSchema
)
from app.services.user_service import UserService
from app.middleware.permissions import require_permission

users_bp = Blueprint('users', __name__)

@users_bp.route('/', methods=['GET'])
@require_permission('users.view')
def list_users():
    """List all users in tenant."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search')
    role = request.args.get('role')
    
    result = UserService.list_for_tenant(
        tenant_id=g.tenant.id,
        page=page,
        per_page=per_page,
        search=search,
        role=role
    )
    
    return UserListSchema().dump(result)

@users_bp.route('/', methods=['POST'])
@require_permission('users.create')
def create_user():
    """Create a new user."""
    data = UserCreateSchema().load(request.json)
    
    service = UserService()
    user = service.create(tenant_id=g.tenant.id, **data)
    
    return UserSchema().dump(user), 201

@users_bp.route('/<uuid:user_id>', methods=['GET'])
@require_permission('users.view')
def get_user(user_id):
    """Get user details."""
    user = User.query.filter_by(
        id=user_id,
        tenant_id=g.tenant.id
    ).first_or_404()
    
    return UserSchema().dump(user)

@users_bp.route('/<uuid:user_id>', methods=['PUT'])
@require_permission('users.edit')
def update_user(user_id):
    """Update user details."""
    data = UserUpdateSchema().load(request.json)
    
    service = UserService()
    user = service.update(user_id, g.tenant.id, **data)
    
    return UserSchema().dump(user)

@users_bp.route('/<uuid:user_id>', methods=['DELETE'])
@require_permission('users.delete')
def deactivate_user(user_id):
    """Deactivate a user."""
    service = UserService()
    user = service.deactivate(user_id, g.tenant.id)
    
    return UserSchema().dump(user)

@users_bp.route('/<uuid:user_id>/permissions', methods=['GET'])
@require_permission('users.view')
def get_user_permissions(user_id):
    """Get user's effective permissions."""
    service = UserService()
    permissions = service.get_permissions(user_id, g.tenant.id)
    
    return {'permissions': permissions}
```

### Role Management API

```python
# backend/app/api/v1/roles.py
from flask import Blueprint, request, g
from app.models import Role, Permission
from app.middleware.permissions import require_permission

roles_bp = Blueprint('roles', __name__)

@roles_bp.route('/', methods=['GET'])
@require_permission('roles.view')
def list_roles():
    """List all roles in tenant."""
    roles = Role.query.filter_by(tenant_id=g.tenant.id).all()
    return RoleSchema(many=True).dump(roles)

@roles_bp.route('/', methods=['POST'])
@require_permission('roles.create')
def create_role():
    """Create a new role."""
    data = RoleCreateSchema().load(request.json)
    
    role = Role(
        tenant_id=g.tenant.id,
        name=data['name'],
        description=data.get('description'),
    )
    
    # Assign permissions
    if data.get('permissions'):
        permissions = Permission.query.filter(
            Permission.name.in_(data['permissions'])
        ).all()
        role.permissions = permissions
    
    db.session.add(role)
    db.session.commit()
    
    return RoleSchema().dump(role), 201

@roles_bp.route('/permissions', methods=['GET'])
@require_permission('roles.view')
def list_permissions():
    """List all available permissions."""
    permissions = Permission.query.all()
    return PermissionSchema(many=True).dump(permissions)
```

## Expected Output

```
backend/app/
├── api/v1/
│   ├── users.py
│   └── roles.py
├── schemas/
│   ├── user_schemas.py
│   └── role_schemas.py
└── services/
    └── user_service.py
```

## Acceptance Criteria

- [ ] List users with pagination and filtering
- [ ] Create user with role assignment
- [ ] Update user details
- [ ] Deactivate user works
- [ ] Role assignment works
- [ ] Permission inheritance works
- [ ] Email uniqueness per tenant enforced
- [ ] Password strength validated

## Reference Documents

- [Admin Agent](../agents/admin-agent.agent.md)
- [Auth System](./004-auth-system.md)
