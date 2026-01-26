# 046 - API Documentation

## Metadata

```yaml
prompt_id: "046"
phase: 6
agent: "@backend"
model: "opus 4.5"
priority: P1
estimated_effort: "2 days"
dependencies: ["003", "014", "019", "024"]
```

## Objective

Generate comprehensive API documentation using OpenAPI/Swagger.

## Task Description

Create auto-generated API documentation with examples and interactive testing.

## Requirements

### Flask-RESTX Integration

```python
# backend/app/api/__init__.py
from flask import Blueprint
from flask_restx import Api

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': 'JWT Authorization header using the Bearer scheme. Example: "Bearer {token}"'
    }
}

api = Api(
    api_bp,
    version='1.0',
    title='NovaSight API',
    description='''
    Self-Service Business Intelligence Platform API
    
    ## Authentication
    
    All endpoints except `/auth/login` require a JWT token.
    Use the login endpoint to obtain a token, then include it in the Authorization header.
    
    ## Multi-Tenancy
    
    All data operations are scoped to the authenticated user's tenant.
    Cross-tenant access is not permitted.
    
    ## Rate Limiting
    
    API requests are rate-limited per user:
    - Standard endpoints: 100 requests/minute
    - Query endpoints: 20 requests/minute
    - Auth endpoints: 10 requests/minute
    
    ## Response Format
    
    All responses follow this structure:
    ```json
    {
      "success": true,
      "data": { ... },
      "message": "Optional message",
      "pagination": { ... }  // For list endpoints
    }
    ```
    ''',
    authorizations=authorizations,
    security='Bearer',
    doc='/docs'
)

# Import and register namespaces
from app.api.v1.auth import ns as auth_ns
from app.api.v1.datasources import ns as datasources_ns
from app.api.v1.semantic import ns as semantic_ns
from app.api.v1.dashboards import ns as dashboards_ns
from app.api.v1.query import ns as query_ns
from app.api.v1.admin import ns as admin_ns

api.add_namespace(auth_ns)
api.add_namespace(datasources_ns)
api.add_namespace(semantic_ns)
api.add_namespace(dashboards_ns)
api.add_namespace(query_ns)
api.add_namespace(admin_ns)
```

### API Models

```python
# backend/app/api/v1/models.py
from flask_restx import fields
from app.api import api

# Common models
pagination_model = api.model('Pagination', {
    'page': fields.Integer(description='Current page number'),
    'per_page': fields.Integer(description='Items per page'),
    'total': fields.Integer(description='Total items'),
    'pages': fields.Integer(description='Total pages'),
})

error_model = api.model('Error', {
    'success': fields.Boolean(default=False),
    'message': fields.String(description='Error message'),
    'code': fields.String(description='Error code'),
    'details': fields.Raw(description='Additional error details'),
})

# Auth models
login_request = api.model('LoginRequest', {
    'email': fields.String(required=True, description='User email', example='user@example.com'),
    'password': fields.String(required=True, description='User password', example='SecurePassword123!'),
})

login_response = api.model('LoginResponse', {
    'access_token': fields.String(description='JWT access token'),
    'refresh_token': fields.String(description='JWT refresh token'),
    'expires_in': fields.Integer(description='Token expiry in seconds'),
    'user': fields.Nested(api.model('UserBrief', {
        'id': fields.String(),
        'email': fields.String(),
        'name': fields.String(),
    })),
})

# Data source models
datasource_connection = api.model('DataSourceConnection', {
    'host': fields.String(required=True, example='db.example.com'),
    'port': fields.Integer(required=True, example=5432),
    'database': fields.String(required=True, example='analytics'),
    'username': fields.String(required=True, example='readonly_user'),
    'password': fields.String(required=True, description='Password (stored encrypted)'),
    'ssl': fields.Boolean(default=True),
})

datasource_create = api.model('DataSourceCreate', {
    'name': fields.String(required=True, description='Display name', example='Production Database'),
    'type': fields.String(required=True, enum=['postgresql', 'mysql', 'clickhouse', 's3_parquet', 'api'], example='postgresql'),
    'connection_config': fields.Nested(datasource_connection),
    'sync_frequency': fields.String(description='Cron expression for sync', example='@hourly'),
    'description': fields.String(example='Main production database'),
})

datasource_response = api.model('DataSource', {
    'id': fields.String(description='Unique identifier'),
    'name': fields.String(),
    'type': fields.String(),
    'status': fields.String(enum=['active', 'syncing', 'error', 'pending']),
    'last_sync_at': fields.DateTime(),
    'created_at': fields.DateTime(),
    'updated_at': fields.DateTime(),
})

# Dashboard models
widget_config = api.model('WidgetConfig', {
    'name': fields.String(required=True, example='Sales by Region'),
    'type': fields.String(required=True, enum=['metric_card', 'line_chart', 'bar_chart', 'pie_chart', 'table', 'heatmap']),
    'query_config': fields.Raw(description='Query configuration'),
    'viz_config': fields.Raw(description='Visualization settings'),
    'grid_position': fields.Nested(api.model('GridPosition', {
        'x': fields.Integer(required=True, min=0, max=11),
        'y': fields.Integer(required=True, min=0),
        'w': fields.Integer(required=True, min=1, max=12),
        'h': fields.Integer(required=True, min=1),
    })),
})

dashboard_create = api.model('DashboardCreate', {
    'name': fields.String(required=True, example='Sales Dashboard'),
    'description': fields.String(example='Overview of sales performance'),
    'widgets': fields.List(fields.Nested(widget_config)),
    'filters': fields.Raw(description='Global filter configuration'),
})

# Query models
query_request = api.model('QueryRequest', {
    'query': fields.String(required=True, description='Natural language query', example='What were total sales by region last month?'),
    'context': fields.Raw(description='Additional context for the query'),
})

query_response = api.model('QueryResponse', {
    'data': fields.Raw(description='Query result data'),
    'columns': fields.List(fields.Nested(api.model('Column', {
        'name': fields.String(),
        'type': fields.String(),
    }))),
    'row_count': fields.Integer(),
    'execution_time_ms': fields.Float(),
    'generated_sql': fields.String(description='SQL query that was executed'),
})
```

### Documented Endpoints

```python
# backend/app/api/v1/datasources.py
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required
from app.api.v1.models import (
    datasource_create, datasource_response, error_model
)
from app.services.datasource_service import DataSourceService

ns = Namespace('datasources', description='Data source management')

@ns.route('')
class DataSourceList(Resource):
    @ns.doc('list_datasources')
    @ns.marshal_list_with(datasource_response)
    @ns.response(401, 'Unauthorized', error_model)
    @jwt_required()
    def get(self):
        """
        List all data sources for the current tenant.
        
        Returns a list of configured data sources with their sync status.
        """
        return DataSourceService.list_for_tenant()
    
    @ns.doc('create_datasource')
    @ns.expect(datasource_create, validate=True)
    @ns.marshal_with(datasource_response, code=201)
    @ns.response(400, 'Validation Error', error_model)
    @ns.response(401, 'Unauthorized', error_model)
    @jwt_required()
    def post(self):
        """
        Create a new data source.
        
        Creates a data source with the provided connection configuration.
        The connection will be tested before saving.
        
        **Important**: Passwords are encrypted before storage.
        """
        return DataSourceService.create(**ns.payload), 201


@ns.route('/<string:id>')
@ns.param('id', 'Data source identifier')
class DataSourceDetail(Resource):
    @ns.doc('get_datasource')
    @ns.marshal_with(datasource_response)
    @ns.response(404, 'Not Found', error_model)
    @jwt_required()
    def get(self, id):
        """
        Get a specific data source.
        
        Returns the data source details including sync status.
        Connection credentials are never returned.
        """
        return DataSourceService.get(id)
    
    @ns.doc('delete_datasource')
    @ns.response(204, 'Deleted')
    @ns.response(404, 'Not Found', error_model)
    @jwt_required()
    def delete(self, id):
        """
        Delete a data source.
        
        **Warning**: This will also delete:
        - All ingested data
        - Associated semantic models
        - Dashboard widgets using this source
        """
        DataSourceService.delete(id)
        return '', 204


@ns.route('/<string:id>/test')
@ns.param('id', 'Data source identifier')
class DataSourceTest(Resource):
    @ns.doc('test_datasource')
    @ns.response(200, 'Connection test result')
    @jwt_required()
    def post(self, id):
        """
        Test data source connection.
        
        Attempts to connect to the data source and returns the result.
        Does not sync any data.
        """
        result = DataSourceService.test_connection(id)
        return {
            'success': result['success'],
            'message': result.get('message'),
            'latency_ms': result.get('latency_ms'),
        }


@ns.route('/<string:id>/schema')
@ns.param('id', 'Data source identifier')
class DataSourceSchema(Resource):
    @ns.doc('get_datasource_schema')
    @jwt_required()
    def get(self, id):
        """
        Get the schema of a data source.
        
        Returns the database schema including:
        - Schemas/databases
        - Tables and views
        - Columns with data types
        - Primary and foreign keys
        
        **Note**: Large schemas may take several seconds to retrieve.
        """
        return DataSourceService.get_schema(id)
```

### OpenAPI Export

```python
# backend/app/commands/docs.py
import click
import json
import yaml
from flask.cli import with_appcontext
from app.api import api

@click.command('export-openapi')
@click.option('--format', type=click.Choice(['json', 'yaml']), default='yaml')
@click.option('--output', '-o', default='openapi.yaml')
@with_appcontext
def export_openapi(format, output):
    """Export OpenAPI specification to file."""
    spec = api.__schema__
    
    if format == 'json':
        content = json.dumps(spec, indent=2)
    else:
        content = yaml.dump(spec, default_flow_style=False)
    
    with open(output, 'w') as f:
        f.write(content)
    
    click.echo(f'OpenAPI spec exported to {output}')
```

### Redoc Static Documentation

```html
<!-- docs/api/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>NovaSight API Documentation</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    <style>
        body { margin: 0; padding: 0; }
    </style>
</head>
<body>
    <redoc spec-url='/api/v1/openapi.json'></redoc>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
</body>
</html>
```

## Expected Output

```
backend/app/api/
├── __init__.py
└── v1/
    ├── __init__.py
    ├── models.py
    ├── auth.py
    ├── datasources.py
    ├── semantic.py
    ├── dashboards.py
    ├── query.py
    └── admin.py

docs/api/
├── index.html
├── openapi.yaml
└── examples/
    ├── authentication.md
    ├── datasources.md
    └── queries.md
```

## Acceptance Criteria

- [ ] Swagger UI accessible at /api/v1/docs
- [ ] All endpoints documented
- [ ] Request/response models defined
- [ ] Examples included
- [ ] Authentication documented
- [ ] Error responses documented
- [ ] OpenAPI export working
- [ ] Redoc static docs generated

## Reference Documents

- [Backend Agent](../agents/backend-agent.agent.md)
- [Flask API Skill](../skills/flask-api/SKILL.md)
