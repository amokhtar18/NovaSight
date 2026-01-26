# 005 - Multi-Tenant Middleware

## Metadata

```yaml
prompt_id: "005"
phase: 1
agent: "@backend"
model: "opus 4.5"
priority: P0
estimated_effort: "2 days"
dependencies: ["003", "004"]
```

## Objective

Implement middleware that sets tenant context for every request, ensuring complete data isolation between tenants.

## Task Description

Create middleware that:

1. Extracts tenant from JWT claims
2. Sets tenant context in Flask `g` object
3. Configures database search_path for PostgreSQL
4. Validates tenant is active
5. Provides helper decorators for tenant-aware operations

## Requirements

### Tenant Context Middleware

```python
# backend/app/middleware/tenant_context.py
from flask import g, request, abort
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from app.models import Tenant
from app.extensions import db

def init_tenant_context():
    """Initialize tenant context from JWT."""
    # Skip for public endpoints
    if request.endpoint in ['api_v1.auth.login', 'api_v1.auth.register', 'api_v1.health']:
        return
    
    try:
        verify_jwt_in_request()
        claims = get_jwt()
        
        tenant_id = claims.get('tenant_id')
        if not tenant_id:
            abort(401, description="Missing tenant context")
        
        tenant = Tenant.query.get(tenant_id)
        if not tenant or not tenant.is_active:
            abort(401, description="Invalid tenant")
        
        # Set context
        g.tenant = tenant
        g.tenant_schema = f"tenant_{tenant.slug}"
        g.current_user_id = claims.get('sub')
        g.user_roles = claims.get('roles', [])
        g.user_permissions = claims.get('permissions', [])
        
        # Set PostgreSQL search_path
        db.session.execute(
            text(f"SET search_path TO {g.tenant_schema}, public")
        )
        
    except Exception as e:
        abort(401, description=str(e))
```

### Tenant-Aware Model Mixin

```python
# backend/app/models/mixins.py
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from flask import g

class TenantMixin:
    """Mixin for models that belong to a tenant."""
    
    @declared_attr
    def tenant_id(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey('public.tenants.id'),
            nullable=False,
            index=True
        )
    
    @classmethod
    def for_tenant(cls):
        """Query filtered by current tenant."""
        return cls.query.filter_by(tenant_id=g.tenant.id)
```

### Permission Decorator

```python
# backend/app/middleware/permissions.py
from functools import wraps
from flask import g, abort

def require_permission(permission: str):
    """Decorator to check user has permission."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if permission not in g.user_permissions:
                abort(403, description=f"Permission denied: {permission}")
            return f(*args, **kwargs)
        return wrapper
    return decorator

def require_any_permission(*permissions):
    """Decorator to check user has any of the permissions."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not any(p in g.user_permissions for p in permissions):
                abort(403, description="Permission denied")
            return f(*args, **kwargs)
        return wrapper
    return decorator
```

### Registration in App Factory

```python
# In create_app()
from app.middleware.tenant_context import init_tenant_context

app.before_request(init_tenant_context)
```

## Expected Output

```
backend/app/
├── middleware/
│   ├── __init__.py
│   ├── tenant_context.py
│   └── permissions.py
├── models/
│   └── mixins.py
└── utils/
    └── tenant_utils.py
```

## Acceptance Criteria

- [ ] Tenant context set from JWT
- [ ] Database search_path configured
- [ ] g.tenant available in request context
- [ ] Permission decorators work
- [ ] Cross-tenant access blocked
- [ ] Inactive tenants rejected
- [ ] Public endpoints accessible without JWT

## Reference Documents

- [Multi-Tenant DB Skill](../skills/multi-tenant-db/SKILL.md)
- [Architecture Decisions - ADR-003](../../docs/requirements/Architecture_Decisions.md)
