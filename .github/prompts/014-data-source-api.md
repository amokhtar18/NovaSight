# 014 - Data Source API

## Metadata

```yaml
prompt_id: "014"
phase: 2
agent: "@data-sources"
model: "sonnet 4.5"
priority: P0
estimated_effort: "2 days"
dependencies: ["013"]
```

## Objective

Implement REST API endpoints for managing data source connections.

## Task Description

Create CRUD endpoints for data source management with secure credential handling.

## Requirements

### Data Source Model

```python
# backend/app/models/datasource.py
from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin
from sqlalchemy.dialects.postgresql import UUID, JSONB
from enum import Enum

class DataSourceType(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    SNOWFLAKE = "snowflake"
    BIGQUERY = "bigquery"
    S3 = "s3"
    GCS = "gcs"

class DataSourceStatus(str, Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    ERROR = "error"
    DISABLED = "disabled"

class DataSource(TenantMixin, TimestampMixin, db.Model):
    __tablename__ = 'datasources'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum(DataSourceType), nullable=False)
    status = db.Column(db.Enum(DataSourceStatus), default=DataSourceStatus.PENDING)
    
    # Connection details (encrypted)
    connection_config = db.Column(JSONB, nullable=False)
    
    # Metadata
    last_sync_at = db.Column(db.DateTime)
    sync_frequency = db.Column(db.String(50))  # cron expression
    error_message = db.Column(db.Text)
    
    # Relationships
    tables = db.relationship('DataSourceTable', backref='datasource', lazy='dynamic')
```

### API Endpoints

```python
# backend/app/api/v1/datasources.py
from flask import Blueprint, request, g
from app.schemas.datasource_schemas import (
    DataSourceCreateSchema, 
    DataSourceResponseSchema,
    DataSourceListSchema
)
from app.services.datasource_service import DataSourceService
from app.middleware.permissions import require_permission

datasources_bp = Blueprint('datasources', __name__)

@datasources_bp.route('/', methods=['GET'])
@require_permission('datasources.view')
def list_datasources():
    """List all data sources for tenant."""
    datasources = DataSourceService.list_for_tenant(g.tenant.id)
    return DataSourceListSchema(many=True).dump(datasources)

@datasources_bp.route('/', methods=['POST'])
@require_permission('datasources.create')
def create_datasource():
    """Create a new data source connection."""
    schema = DataSourceCreateSchema()
    data = schema.load(request.json)
    
    datasource = DataSourceService.create(
        tenant_id=g.tenant.id,
        **data
    )
    return DataSourceResponseSchema().dump(datasource), 201

@datasources_bp.route('/<uuid:datasource_id>', methods=['GET'])
@require_permission('datasources.view')
def get_datasource(datasource_id):
    """Get data source details."""
    datasource = DataSourceService.get(datasource_id, g.tenant.id)
    return DataSourceResponseSchema().dump(datasource)

@datasources_bp.route('/<uuid:datasource_id>/test', methods=['POST'])
@require_permission('datasources.create')
def test_connection(datasource_id):
    """Test data source connection."""
    result = DataSourceService.test_connection(datasource_id, g.tenant.id)
    return {'success': result['success'], 'message': result.get('message')}

@datasources_bp.route('/<uuid:datasource_id>/schema', methods=['GET'])
@require_permission('datasources.view')
def get_schema(datasource_id):
    """Get data source schema (tables/columns)."""
    schema_info = DataSourceService.get_schema(datasource_id, g.tenant.id)
    return schema_info

@datasources_bp.route('/<uuid:datasource_id>/sync', methods=['POST'])
@require_permission('datasources.sync')
def trigger_sync(datasource_id):
    """Trigger manual data sync."""
    job_id = DataSourceService.trigger_sync(datasource_id, g.tenant.id)
    return {'job_id': job_id, 'status': 'started'}
```

### Request/Response Schemas

```python
# backend/app/schemas/datasource_schemas.py
from marshmallow import Schema, fields, validate

class ConnectionConfigSchema(Schema):
    host = fields.Str(required=True)
    port = fields.Int(required=True)
    database = fields.Str(required=True)
    username = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)
    ssl = fields.Bool(default=True)

class DataSourceCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    type = fields.Str(required=True, validate=validate.OneOf([
        'postgresql', 'mysql', 'mongodb', 'snowflake', 'bigquery', 's3', 'gcs'
    ]))
    connection_config = fields.Nested(ConnectionConfigSchema, required=True)
    sync_frequency = fields.Str(validate=validate.Regexp(r'^(@(hourly|daily|weekly)|.*\s.*\s.*\s.*\s.*)$'))

class DataSourceResponseSchema(Schema):
    id = fields.UUID()
    name = fields.Str()
    type = fields.Str()
    status = fields.Str()
    last_sync_at = fields.DateTime()
    sync_frequency = fields.Str()
    created_at = fields.DateTime()
    tables_count = fields.Method('get_tables_count')
    
    def get_tables_count(self, obj):
        return obj.tables.count()
```

## Expected Output

```
backend/app/
├── api/v1/
│   └── datasources.py
├── models/
│   ├── datasource.py
│   └── datasource_table.py
├── schemas/
│   └── datasource_schemas.py
└── services/
    └── datasource_service.py
```

## Acceptance Criteria

- [ ] CRUD endpoints work correctly
- [ ] Connection testing works
- [ ] Schema introspection returns tables
- [ ] Credentials never exposed in responses
- [ ] Tenant isolation enforced
- [ ] Permission checks work
- [ ] Sync triggers Airflow DAG

## Reference Documents

- [Data Source Connectors](./013-data-source-connectors.md)
- [BRD - Epic 2](../../docs/requirements/BRD.md)
