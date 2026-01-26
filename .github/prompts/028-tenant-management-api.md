# 028 - Tenant Management API

## Metadata

```yaml
prompt_id: "028"
phase: 5
agent: "@admin"
model: "haiku 4.5"
priority: P1
estimated_effort: "2 days"
dependencies: ["003", "005"]
```

## Objective

Implement tenant management API for platform administrators.

## Task Description

Create REST endpoints for managing tenants including provisioning, configuration, and monitoring.

## Requirements

### Tenant Management Service

```python
# backend/app/services/tenant_service.py
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models import Tenant
from app.extensions import db
from app.services.template_engine import TemplateEngine
from app.utils.clickhouse_client import ClickHouseClient

class TenantService:
    """Service for tenant lifecycle management."""
    
    def __init__(
        self, 
        template_engine: TemplateEngine,
        clickhouse_client: ClickHouseClient
    ):
        self.templates = template_engine
        self.clickhouse = clickhouse_client
    
    @classmethod
    def list(
        cls,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """List all tenants with pagination."""
        query = Tenant.query
        
        if search:
            query = query.filter(
                Tenant.name.ilike(f'%{search}%') |
                Tenant.slug.ilike(f'%{search}%')
            )
        
        if status:
            query = query.filter(Tenant.is_active == (status == 'active'))
        
        pagination = query.paginate(page=page, per_page=per_page)
        
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
            'pages': pagination.pages,
        }
    
    def create(
        self,
        name: str,
        slug: str,
        plan: str = 'starter',
        settings: Dict = None
    ) -> Tenant:
        """Create a new tenant with all required resources."""
        
        # Create tenant record
        tenant = Tenant(
            name=name,
            slug=slug,
            plan=plan,
            settings=settings or {},
            is_active=True
        )
        db.session.add(tenant)
        db.session.flush()  # Get tenant ID
        
        # Create PostgreSQL schema
        self._create_pg_schema(tenant)
        
        # Create ClickHouse database
        self._create_ch_database(tenant)
        
        # Initialize dbt project for tenant (if needed)
        # self._init_dbt_project(tenant)
        
        db.session.commit()
        return tenant
    
    def _create_pg_schema(self, tenant: Tenant) -> None:
        """Create PostgreSQL schema for tenant."""
        sql = self.templates.render(
            'sql/tenant_schema.sql.j2',
            {'tenant_slug': tenant.slug}
        )
        db.session.execute(sql)
    
    def _create_ch_database(self, tenant: Tenant) -> None:
        """Create ClickHouse database for tenant."""
        sql = self.templates.render(
            'clickhouse/tenant_database.sql.j2',
            {
                'tenant_id': str(tenant.id),
                'tenant_slug': tenant.slug
            }
        )
        self.clickhouse.execute(sql)
    
    def update(
        self,
        tenant_id: str,
        **kwargs
    ) -> Tenant:
        """Update tenant configuration."""
        tenant = Tenant.query.get_or_404(tenant_id)
        
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        tenant.updated_at = datetime.utcnow()
        db.session.commit()
        return tenant
    
    def deactivate(self, tenant_id: str) -> Tenant:
        """Deactivate a tenant (soft delete)."""
        tenant = Tenant.query.get_or_404(tenant_id)
        tenant.is_active = False
        tenant.updated_at = datetime.utcnow()
        db.session.commit()
        return tenant
    
    def get_usage(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant usage statistics."""
        tenant = Tenant.query.get_or_404(tenant_id)
        
        return {
            'storage_gb': self._get_storage_usage(tenant),
            'users_count': tenant.users.count(),
            'datasources_count': tenant.datasources.count(),
            'dashboards_count': tenant.dashboards.count(),
            'queries_last_30d': self._get_query_count(tenant),
        }
    
    def _get_storage_usage(self, tenant: Tenant) -> float:
        """Get ClickHouse storage usage in GB."""
        result = self.clickhouse.execute(f"""
            SELECT sum(bytes) / 1024 / 1024 / 1024 as gb
            FROM system.parts
            WHERE database = 'tenant_{tenant.slug}'
        """)
        return round(result[0]['gb'] or 0, 2)
    
    def _get_query_count(self, tenant: Tenant) -> int:
        """Get query count for last 30 days."""
        # Implementation depends on query logging
        return 0
```

### Tenant Management API

```python
# backend/app/api/v1/admin/tenants.py
from flask import Blueprint, request
from app.schemas.tenant_schemas import (
    TenantSchema,
    TenantCreateSchema,
    TenantUpdateSchema,
    TenantListSchema
)
from app.services.tenant_service import TenantService
from app.middleware.permissions import require_permission

admin_tenants_bp = Blueprint('admin_tenants', __name__)

@admin_tenants_bp.route('/', methods=['GET'])
@require_permission('admin.tenants.view')
def list_tenants():
    """List all tenants with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search')
    status = request.args.get('status')
    
    result = TenantService.list(
        page=page,
        per_page=per_page,
        search=search,
        status=status
    )
    
    return TenantListSchema().dump(result)

@admin_tenants_bp.route('/', methods=['POST'])
@require_permission('admin.tenants.create')
def create_tenant():
    """Create a new tenant."""
    data = TenantCreateSchema().load(request.json)
    
    service = TenantService(...)
    tenant = service.create(**data)
    
    return TenantSchema().dump(tenant), 201

@admin_tenants_bp.route('/<uuid:tenant_id>', methods=['GET'])
@require_permission('admin.tenants.view')
def get_tenant(tenant_id):
    """Get tenant details."""
    tenant = Tenant.query.get_or_404(tenant_id)
    return TenantSchema().dump(tenant)

@admin_tenants_bp.route('/<uuid:tenant_id>', methods=['PUT'])
@require_permission('admin.tenants.edit')
def update_tenant(tenant_id):
    """Update tenant configuration."""
    data = TenantUpdateSchema().load(request.json)
    
    service = TenantService(...)
    tenant = service.update(tenant_id, **data)
    
    return TenantSchema().dump(tenant)

@admin_tenants_bp.route('/<uuid:tenant_id>', methods=['DELETE'])
@require_permission('admin.tenants.delete')
def deactivate_tenant(tenant_id):
    """Deactivate a tenant."""
    service = TenantService(...)
    tenant = service.deactivate(tenant_id)
    
    return TenantSchema().dump(tenant)

@admin_tenants_bp.route('/<uuid:tenant_id>/usage', methods=['GET'])
@require_permission('admin.tenants.view')
def get_tenant_usage(tenant_id):
    """Get tenant usage statistics."""
    service = TenantService(...)
    usage = service.get_usage(tenant_id)
    
    return usage
```

### Schemas

```python
# backend/app/schemas/tenant_schemas.py
from marshmallow import Schema, fields, validate

class TenantSchema(Schema):
    id = fields.UUID()
    name = fields.Str()
    slug = fields.Str()
    plan = fields.Str()
    settings = fields.Dict()
    is_active = fields.Bool()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

class TenantCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    slug = fields.Str(
        required=True, 
        validate=validate.Regexp(r'^[a-z][a-z0-9-]*$')
    )
    plan = fields.Str(
        validate=validate.OneOf(['starter', 'professional', 'enterprise'])
    )
    settings = fields.Dict()

class TenantUpdateSchema(Schema):
    name = fields.Str(validate=validate.Length(min=1, max=100))
    plan = fields.Str(
        validate=validate.OneOf(['starter', 'professional', 'enterprise'])
    )
    settings = fields.Dict()
    is_active = fields.Bool()

class TenantListSchema(Schema):
    items = fields.List(fields.Nested(TenantSchema))
    total = fields.Int()
    page = fields.Int()
    per_page = fields.Int()
    pages = fields.Int()
```

## Expected Output

```
backend/app/
├── api/v1/admin/
│   ├── __init__.py
│   └── tenants.py
├── schemas/
│   └── tenant_schemas.py
└── services/
    └── tenant_service.py
```

## Acceptance Criteria

- [ ] List tenants with pagination
- [ ] Create tenant provisions all resources
- [ ] Update tenant configuration works
- [ ] Deactivate tenant works (soft delete)
- [ ] Usage statistics are accurate
- [ ] Only platform admins can access
- [ ] Tenant slug is unique
- [ ] PostgreSQL schema created
- [ ] ClickHouse database created

## Reference Documents

- [Admin Agent](../agents/admin-agent.agent.md)
- [Multi-Tenant DB Skill](../skills/multi-tenant-db/SKILL.md)
