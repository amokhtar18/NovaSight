# Multi-Tenant Database Skill

## Description
This skill provides patterns for implementing multi-tenant database isolation using PostgreSQL schema-per-tenant and ClickHouse database-per-tenant approaches.

## Trigger
- User asks about tenant isolation
- User asks about database schemas
- User mentions multi-tenancy patterns
- User asks about RLS (Row-Level Security)

## Instructions

### 1. PostgreSQL Schema-Per-Tenant

```python
# backend/app/services/tenant_db_service.py
from sqlalchemy import text, event
from flask import g
from app.extensions import db

class TenantDatabaseService:
    """Manages tenant-specific database operations."""
    
    def create_tenant_schema(self, tenant_slug: str):
        """Create a new schema for a tenant."""
        schema_name = f"tenant_{tenant_slug}"
        
        # Create schema
        db.session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))
        
        # Apply base tables to schema
        self._apply_schema_migrations(schema_name)
        
        db.session.commit()
    
    def set_search_path(self, tenant_slug: str):
        """Set PostgreSQL search_path for current connection."""
        schema_name = f"tenant_{tenant_slug}"
        db.session.execute(text(f'SET search_path TO "{schema_name}", public'))
    
    def _apply_schema_migrations(self, schema_name: str):
        """Apply table structures to tenant schema."""
        # Tables are created with schema prefix
        tables_sql = f'''
        CREATE TABLE IF NOT EXISTS "{schema_name}".connections (
            id UUID PRIMARY KEY,
            name VARCHAR(64) NOT NULL,
            database_type VARCHAR(20) NOT NULL,
            host VARCHAR(255) NOT NULL,
            port INTEGER NOT NULL,
            database VARCHAR(128) NOT NULL,
            username VARCHAR(128) NOT NULL,
            password_encrypted TEXT NOT NULL,
            ssl_mode VARCHAR(20) DEFAULT 'disable',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS "{schema_name}".ingestion_jobs (
            id UUID PRIMARY KEY,
            name VARCHAR(64) NOT NULL,
            connection_id UUID REFERENCES "{schema_name}".connections(id),
            source_table VARCHAR(255) NOT NULL,
            target_table VARCHAR(64) NOT NULL,
            load_type VARCHAR(20) NOT NULL,
            schedule VARCHAR(100),
            config JSONB,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        '''
        db.session.execute(text(tables_sql))

# Middleware to set tenant context
def setup_tenant_middleware(app):
    @app.before_request
    def set_tenant_context():
        if hasattr(g, 'tenant') and g.tenant:
            service = TenantDatabaseService()
            service.set_search_path(g.tenant.slug)
```

### 2. ClickHouse Database-Per-Tenant

```python
# backend/app/services/clickhouse_service.py
from clickhouse_driver import Client
from typing import List, Dict

class ClickHouseService:
    """Manages ClickHouse operations with tenant isolation."""
    
    def __init__(self, host: str, port: int = 9000):
        self.host = host
        self.port = port
    
    def get_client(self, tenant_slug: str) -> Client:
        """Get client connected to tenant database."""
        database = f"tenant_{tenant_slug}"
        return Client(
            host=self.host,
            port=self.port,
            database=database
        )
    
    def create_tenant_database(self, tenant_slug: str):
        """Create ClickHouse database for tenant."""
        database = f"tenant_{tenant_slug}"
        
        client = Client(host=self.host, port=self.port)
        client.execute(f'CREATE DATABASE IF NOT EXISTS {database}')
    
    def create_table(
        self,
        tenant_slug: str,
        table_name: str,
        columns: List[Dict],
        engine: str = "MergeTree",
        order_by: str = None
    ):
        """Create table in tenant database."""
        database = f"tenant_{tenant_slug}"
        
        column_defs = ", ".join([
            f"`{col['name']}` {col['type']}"
            for col in columns
        ])
        
        order_by = order_by or columns[0]['name']
        
        sql = f'''
        CREATE TABLE IF NOT EXISTS {database}.{table_name} (
            {column_defs}
        )
        ENGINE = {engine}()
        ORDER BY ({order_by})
        '''
        
        client = Client(host=self.host, port=self.port)
        client.execute(sql)
    
    def query(
        self,
        tenant_slug: str,
        sql: str,
        params: Dict = None
    ) -> List[Dict]:
        """Execute query in tenant database."""
        client = self.get_client(tenant_slug)
        
        result = client.execute(sql, params or {}, with_column_types=True)
        
        if not result:
            return []
        
        data, columns = result
        column_names = [col[0] for col in columns]
        
        return [dict(zip(column_names, row)) for row in data]
```

### 3. Row-Level Security (RLS)

```python
# backend/app/services/rls_service.py
import sqlparse
from sqlparse.sql import Where, Comparison
from typing import Optional
from flask import g

class RLSService:
    """Injects row-level security filters into SQL queries."""
    
    def __init__(self):
        self.rls_rules = {}
    
    def register_rule(
        self,
        model_name: str,
        column: str,
        user_attribute: str
    ):
        """Register an RLS rule for a model."""
        self.rls_rules[model_name] = {
            'column': column,
            'user_attribute': user_attribute
        }
    
    def inject_filters(
        self,
        sql: str,
        model_name: str,
        user: 'User'
    ) -> str:
        """Inject RLS filters into SQL query."""
        
        rule = self.rls_rules.get(model_name)
        if not rule:
            return sql
        
        # Get user attribute value
        user_value = getattr(user, rule['user_attribute'], None)
        if user_value is None:
            return sql
        
        # Build filter condition
        filter_condition = f"{rule['column']} = '{user_value}'"
        
        # Parse and modify SQL
        parsed = sqlparse.parse(sql)[0]
        
        # Check if WHERE exists
        has_where = any(
            isinstance(token, Where)
            for token in parsed.tokens
        )
        
        if has_where:
            # Add to existing WHERE
            sql = sql.replace(' WHERE ', f' WHERE {filter_condition} AND ')
        else:
            # Add WHERE clause before ORDER BY, GROUP BY, or LIMIT
            for keyword in ['ORDER BY', 'GROUP BY', 'LIMIT']:
                if keyword in sql.upper():
                    pos = sql.upper().find(keyword)
                    sql = sql[:pos] + f' WHERE {filter_condition} ' + sql[pos:]
                    break
            else:
                # Add at end
                sql = f"{sql.rstrip().rstrip(';')} WHERE {filter_condition}"
        
        return sql

# Example usage in query service
class QueryService:
    def __init__(self, rls: RLSService):
        self.rls = rls
        
        # Register RLS rules
        self.rls.register_rule('sales', 'region', 'user_region')
        self.rls.register_rule('orders', 'department_id', 'department_id')
    
    def execute(self, sql: str, model_name: str) -> list:
        # Inject RLS
        sql_with_rls = self.rls.inject_filters(sql, model_name, g.current_user)
        
        # Execute query...
        pass
```

### 4. Tenant-Aware Model Mixin

```python
# backend/app/models/mixins.py
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr
from flask import g

class TenantMixin:
    """Mixin for tenant-aware models."""
    
    @declared_attr
    def tenant_id(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey('public.tenants.id', ondelete='CASCADE'),
            nullable=False,
            index=True
        )
    
    @classmethod
    def query_for_tenant(cls):
        """Get query filtered by current tenant."""
        return cls.query.filter_by(tenant_id=g.tenant.id)

# Usage
class Connection(db.Model, TenantMixin):
    __tablename__ = 'connections'
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(64), nullable=False)
    # ... other columns

# In service
connections = Connection.query_for_tenant().all()
```

### 5. Tenant Provisioning

```python
# backend/app/services/provisioning_service.py
class TenantProvisioningService:
    """Handles complete tenant provisioning."""
    
    def __init__(
        self,
        pg_service: TenantDatabaseService,
        ch_service: ClickHouseService,
        dbt_service: 'DbtProjectService'
    ):
        self.pg = pg_service
        self.ch = ch_service
        self.dbt = dbt_service
    
    def provision_tenant(self, tenant: 'Tenant'):
        """Provision all infrastructure for a new tenant."""
        
        # 1. Create PostgreSQL schema
        self.pg.create_tenant_schema(tenant.slug)
        
        # 2. Create ClickHouse database
        self.ch.create_tenant_database(tenant.slug)
        
        # 3. Create dbt project
        self.dbt.create_project(tenant.slug)
        
        # 4. Create default roles
        from app.services.role_service import RoleService
        role_service = RoleService()
        role_service.create_default_roles(tenant.id)
        
        # 5. Log provisioning
        from app.services.audit_service import AuditService
        audit = AuditService()
        audit.log('TENANT_PROVISIONED', {'tenant_id': str(tenant.id)})
    
    def deprovision_tenant(self, tenant: 'Tenant', retain_days: int = 30):
        """Schedule tenant deprovisioning."""
        # Mark for deletion
        tenant.scheduled_deletion = datetime.utcnow() + timedelta(days=retain_days)
        db.session.commit()
        
        # Schedule cleanup job
        # This would be done via Airflow DAG
```

## Security Considerations
- Always use parameterized queries
- Validate tenant context before every database operation
- Never expose tenant IDs in URLs (use slugs)
- Audit all cross-tenant access attempts
- Use connection pooling per tenant for isolation

## Reference Files
- [Backend Agent](../../agents/backend-agent.agent.md)
- [Architecture Decisions - ADR-003](../../docs/requirements/Architecture_Decisions.md)
