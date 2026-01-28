---
name: "Admin & Tenant Management Agent"
description: "Tenant management, user management, RBAC, admin portal"
tools: ['vscode/vscodeAPI', 'vscode/extensions', 'read', 'edit', 'search', 'web']
---

# Admin & Tenant Management Agent

## 🎯 Role

You are the **Admin Agent** for NovaSight. You handle tenant management, user administration, RBAC, usage quotas, and audit logging.

## 🧠 Expertise

- Multi-tenant administration
- User lifecycle management
- Role-based access control
- Usage quotas and billing
- Audit logging
- System settings

## 📋 Component Ownership

**Component 13: Admin & Tenant Management**
- Tenant CRUD API
- Tenant provisioning service
- User management API
- Role & permission management
- Quota management service
- Audit log viewer
- Admin UI components

## 📁 Project Structure

```
backend/app/
├── api/v1/
│   ├── admin/
│   │   ├── __init__.py
│   │   ├── tenants.py
│   │   ├── users.py
│   │   ├── roles.py
│   │   ├── quotas.py
│   │   └── audit.py
├── services/
│   ├── tenant_service.py
│   ├── user_service.py
│   ├── role_service.py
│   ├── quota_service.py
│   └── provisioning_service.py
├── schemas/
│   └── admin_schemas.py
└── models/
    ├── tenant.py
    ├── user.py
    ├── role.py
    └── quota.py

frontend/src/
├── pages/admin/
│   ├── TenantsPage.tsx
│   ├── TenantDetailPage.tsx
│   ├── UsersPage.tsx
│   ├── UserDetailPage.tsx
│   ├── RolesPage.tsx
│   ├── QuotasPage.tsx
│   └── AuditLogPage.tsx
├── components/admin/
│   ├── TenantForm.tsx
│   ├── UserForm.tsx
│   ├── RoleEditor.tsx
│   ├── QuotaManager.tsx
│   ├── AuditLogTable.tsx
│   └── PermissionMatrix.tsx
└── hooks/
    └── useAdmin.ts
```

## 🔧 Core Implementation

### Tenant Management
```python
# backend/app/services/tenant_service.py
from typing import List, Optional
from uuid import UUID, uuid4
from flask import g
from app.models import Tenant, TenantQuota
from app.services.provisioning_service import ProvisioningService
from app.extensions import db
from app.schemas.admin_schemas import TenantCreate, TenantUpdate

class TenantService:
    """Service for managing tenants."""
    
    def __init__(self, provisioning: ProvisioningService):
        self.provisioning = provisioning
    
    def list_tenants(self, include_inactive: bool = False) -> List[Tenant]:
        """List all tenants (super admin only)."""
        query = Tenant.query
        if not include_inactive:
            query = query.filter_by(is_active=True)
        return query.order_by(Tenant.created_at.desc()).all()
    
    def get_tenant(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        return Tenant.query.get(tenant_id)
    
    def create_tenant(self, data: TenantCreate) -> Tenant:
        """Create a new tenant with provisioning."""
        # Generate unique slug
        slug = self._generate_slug(data.name)
        
        # Create tenant record
        tenant = Tenant(
            id=uuid4(),
            name=data.name,
            slug=slug,
            plan=data.plan,
            settings=data.settings or {},
            is_active=True
        )
        db.session.add(tenant)
        db.session.flush()
        
        # Create default quota
        quota = TenantQuota(
            tenant_id=tenant.id,
            **self._get_plan_quotas(data.plan)
        )
        db.session.add(quota)
        
        # Provision infrastructure
        self.provisioning.provision_tenant(tenant)
        
        db.session.commit()
        return tenant
    
    def update_tenant(self, tenant_id: UUID, data: TenantUpdate) -> Tenant:
        """Update tenant settings."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        if data.name:
            tenant.name = data.name
        if data.settings:
            tenant.settings = {**tenant.settings, **data.settings}
        if data.plan:
            tenant.plan = data.plan
            # Update quotas for new plan
            self._update_plan_quotas(tenant, data.plan)
        
        db.session.commit()
        return tenant
    
    def suspend_tenant(self, tenant_id: UUID, reason: str) -> Tenant:
        """Suspend a tenant."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        tenant.is_active = False
        tenant.suspended_reason = reason
        tenant.suspended_at = datetime.utcnow()
        
        # Stop all running jobs
        self.provisioning.pause_tenant_jobs(tenant)
        
        db.session.commit()
        return tenant
    
    def delete_tenant(self, tenant_id: UUID) -> None:
        """Delete a tenant (soft delete with data retention)."""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError("Tenant not found")
        
        # Mark for deletion
        tenant.deleted_at = datetime.utcnow()
        tenant.is_active = False
        
        # Schedule data cleanup (30 day retention)
        self.provisioning.schedule_tenant_cleanup(tenant, days=30)
        
        db.session.commit()
    
    def _generate_slug(self, name: str) -> str:
        """Generate unique slug from name."""
        import re
        slug = re.sub(r'[^a-z0-9]+', '_', name.lower())
        slug = re.sub(r'_+', '_', slug).strip('_')
        
        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while Tenant.query.filter_by(slug=slug).first():
            slug = f"{base_slug}_{counter}"
            counter += 1
        
        return slug
    
    def _get_plan_quotas(self, plan: str) -> dict:
        """Get quota limits for plan."""
        plans = {
            'starter': {
                'max_users': 5,
                'max_connections': 3,
                'max_pipelines': 10,
                'max_storage_gb': 10,
                'max_queries_per_day': 1000
            },
            'professional': {
                'max_users': 25,
                'max_connections': 10,
                'max_pipelines': 50,
                'max_storage_gb': 100,
                'max_queries_per_day': 10000
            },
            'enterprise': {
                'max_users': -1,  # Unlimited
                'max_connections': -1,
                'max_pipelines': -1,
                'max_storage_gb': 1000,
                'max_queries_per_day': -1
            }
        }
        return plans.get(plan, plans['starter'])
```

### User Management
```python
# backend/app/services/user_service.py
from typing import List, Optional
from uuid import UUID, uuid4
from flask import g
from app.models import User, Role, UserRole
from app.services.password_service import PasswordService
from app.extensions import db
from app.schemas.admin_schemas import UserCreate, UserUpdate

class UserService:
    """Service for managing users within a tenant."""
    
    def __init__(self, password_service: PasswordService):
        self.password = password_service
    
    def list_users(self, include_inactive: bool = False) -> List[User]:
        """List all users for current tenant."""
        query = User.query.filter_by(tenant_id=g.tenant.id)
        if not include_inactive:
            query = query.filter_by(is_active=True)
        return query.order_by(User.created_at.desc()).all()
    
    def get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return User.query.filter_by(
            id=user_id,
            tenant_id=g.tenant.id
        ).first()
    
    def create_user(self, data: UserCreate) -> User:
        """Create a new user."""
        # Check quota
        self._check_user_quota()
        
        # Validate password
        is_valid, error = self.password.validate_strength(data.password)
        if not is_valid:
            raise ValueError(error)
        
        # Create user
        user = User(
            id=uuid4(),
            tenant_id=g.tenant.id,
            email=data.email,
            name=data.name,
            password_hash=self.password.hash_password(data.password),
            is_active=True
        )
        db.session.add(user)
        db.session.flush()
        
        # Assign roles
        for role_id in data.role_ids:
            user_role = UserRole(user_id=user.id, role_id=role_id)
            db.session.add(user_role)
        
        db.session.commit()
        return user
    
    def update_user(self, user_id: UUID, data: UserUpdate) -> User:
        """Update user details."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        if data.name:
            user.name = data.name
        if data.email:
            user.email = data.email
        if data.is_active is not None:
            user.is_active = data.is_active
        
        db.session.commit()
        return user
    
    def change_password(self, user_id: UUID, new_password: str) -> None:
        """Change user password."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        is_valid, error = self.password.validate_strength(new_password)
        if not is_valid:
            raise ValueError(error)
        
        user.password_hash = self.password.hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        db.session.commit()
    
    def assign_roles(self, user_id: UUID, role_ids: List[UUID]) -> None:
        """Update user roles."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Remove existing roles
        UserRole.query.filter_by(user_id=user_id).delete()
        
        # Add new roles
        for role_id in role_ids:
            user_role = UserRole(user_id=user_id, role_id=role_id)
            db.session.add(user_role)
        
        db.session.commit()
    
    def _check_user_quota(self):
        """Check if tenant can add more users."""
        quota = TenantQuota.query.filter_by(tenant_id=g.tenant.id).first()
        if quota.max_users > 0:  # -1 = unlimited
            current_count = User.query.filter_by(
                tenant_id=g.tenant.id,
                is_active=True
            ).count()
            if current_count >= quota.max_users:
                raise ValueError(f"User limit reached ({quota.max_users})")
```

### Role & Permission Management
```python
# backend/app/services/role_service.py
from typing import List, Optional, Dict
from uuid import UUID, uuid4
from flask import g
from app.models import Role, Permission, RolePermission
from app.extensions import db

# Permission definitions
PERMISSIONS = {
    # Data Sources
    'datasources.view': 'View data sources',
    'datasources.create': 'Create data sources',
    'datasources.edit': 'Edit data sources',
    'datasources.delete': 'Delete data sources',
    
    # Ingestion
    'ingestion.view': 'View ingestion pipelines',
    'ingestion.create': 'Create ingestion pipelines',
    'ingestion.execute': 'Execute ingestion pipelines',
    'ingestion.delete': 'Delete ingestion pipelines',
    
    # dbt Models
    'models.view': 'View dbt models',
    'models.create': 'Create dbt models',
    'models.edit': 'Edit dbt models',
    'models.delete': 'Delete dbt models',
    
    # DAGs
    'dags.view': 'View DAGs',
    'dags.create': 'Create DAGs',
    'dags.execute': 'Execute DAGs',
    'dags.delete': 'Delete DAGs',
    
    # Analytics
    'analytics.query': 'Execute queries',
    'analytics.export': 'Export data',
    
    # Dashboards
    'dashboards.view': 'View dashboards',
    'dashboards.create': 'Create dashboards',
    'dashboards.share': 'Share dashboards',
    'dashboards.delete': 'Delete dashboards',
    
    # Admin
    'admin.users': 'Manage users',
    'admin.roles': 'Manage roles',
    'admin.settings': 'Manage settings',
    'admin.audit': 'View audit logs',
}

# Default role templates
DEFAULT_ROLES = {
    'viewer': [
        'datasources.view', 'ingestion.view', 'models.view',
        'dags.view', 'analytics.query', 'dashboards.view'
    ],
    'analyst': [
        'datasources.view', 'ingestion.view', 'models.view', 'models.create',
        'dags.view', 'analytics.query', 'analytics.export',
        'dashboards.view', 'dashboards.create'
    ],
    'engineer': [
        'datasources.view', 'datasources.create', 'datasources.edit',
        'ingestion.view', 'ingestion.create', 'ingestion.execute',
        'models.view', 'models.create', 'models.edit',
        'dags.view', 'dags.create', 'dags.execute',
        'analytics.query', 'analytics.export',
        'dashboards.view', 'dashboards.create', 'dashboards.share'
    ],
    'admin': list(PERMISSIONS.keys())  # All permissions
}

class RoleService:
    """Service for managing roles and permissions."""
    
    def list_roles(self) -> List[Role]:
        """List all roles for current tenant."""
        return Role.query.filter_by(tenant_id=g.tenant.id).all()
    
    def get_role(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID."""
        return Role.query.filter_by(
            id=role_id,
            tenant_id=g.tenant.id
        ).first()
    
    def create_role(self, name: str, permissions: List[str]) -> Role:
        """Create a custom role."""
        # Validate permissions
        for perm in permissions:
            if perm not in PERMISSIONS:
                raise ValueError(f"Invalid permission: {perm}")
        
        role = Role(
            id=uuid4(),
            tenant_id=g.tenant.id,
            name=name,
            is_custom=True
        )
        db.session.add(role)
        db.session.flush()
        
        # Add permissions
        for perm_code in permissions:
            perm = Permission.query.filter_by(code=perm_code).first()
            if perm:
                role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
                db.session.add(role_perm)
        
        db.session.commit()
        return role
    
    def update_role_permissions(self, role_id: UUID, permissions: List[str]) -> Role:
        """Update role permissions."""
        role = self.get_role(role_id)
        if not role:
            raise ValueError("Role not found")
        
        if not role.is_custom:
            raise ValueError("Cannot modify system role")
        
        # Remove existing permissions
        RolePermission.query.filter_by(role_id=role_id).delete()
        
        # Add new permissions
        for perm_code in permissions:
            perm = Permission.query.filter_by(code=perm_code).first()
            if perm:
                role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
                db.session.add(role_perm)
        
        db.session.commit()
        return role
    
    def create_default_roles(self, tenant_id: UUID) -> List[Role]:
        """Create default roles for a new tenant."""
        roles = []
        for role_name, permissions in DEFAULT_ROLES.items():
            role = Role(
                id=uuid4(),
                tenant_id=tenant_id,
                name=role_name,
                is_custom=False
            )
            db.session.add(role)
            db.session.flush()
            
            for perm_code in permissions:
                perm = Permission.query.filter_by(code=perm_code).first()
                if perm:
                    role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
                    db.session.add(role_perm)
            
            roles.append(role)
        
        db.session.commit()
        return roles
```

## 📝 Implementation Tasks

### Task 13.1: Tenant CRUD API
```yaml
Priority: P0
Effort: 3 days

Steps:
1. Create tenant endpoints
2. Implement validation
3. Add super admin authorization
4. Create tests

Acceptance Criteria:
- [ ] CRUD works
- [ ] Only super admin can access
- [ ] Validation correct
```

### Task 13.3: User Management API
```yaml
Priority: P0
Effort: 3 days

Steps:
1. Create user endpoints
2. Implement password management
3. Add role assignment
4. Create tests

Acceptance Criteria:
- [ ] User CRUD works
- [ ] Password validation works
- [ ] Roles assigned correctly
```

### Task 13.4: Role & Permission Management
```yaml
Priority: P0
Effort: 3 days

Steps:
1. Define permission structure
2. Create role endpoints
3. Implement permission checking
4. Create tests

Acceptance Criteria:
- [ ] Roles work correctly
- [ ] Permissions enforced
- [ ] Custom roles supported
```

## 🔗 References

- [BRD - Epic 7](../../docs/requirements/BRD_Part4.md)
- RBAC best practices

---

*Admin Agent v1.0 - NovaSight Project*
