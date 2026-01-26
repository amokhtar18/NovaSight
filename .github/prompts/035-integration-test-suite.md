# 035 - Integration Test Suite

## Metadata

```yaml
prompt_id: "035"
phase: 6
agent: "@testing"
model: "sonnet 4.5"
priority: P0
estimated_effort: "4 days"
dependencies: ["034"]
```

## Objective

Implement integration tests for API endpoints and cross-service interactions.

## Task Description

Create integration tests that verify end-to-end functionality across services.

## Requirements

### Integration Test Configuration

```python
# backend/tests/integration/conftest.py
import pytest
import docker
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from app import create_app
from app.extensions import db
import os

@pytest.fixture(scope='session')
def postgres_container():
    """Start PostgreSQL test container."""
    with PostgresContainer('postgres:15') as postgres:
        yield postgres

@pytest.fixture(scope='session')
def redis_container():
    """Start Redis test container."""
    with RedisContainer('redis:7') as redis:
        yield redis

@pytest.fixture(scope='session')
def app_with_containers(postgres_container, redis_container):
    """Create app with real database containers."""
    os.environ['DATABASE_URL'] = postgres_container.get_connection_url()
    os.environ['REDIS_URL'] = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}"
    
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        # Run migrations
        from flask_migrate import upgrade
        upgrade()
        
        yield app
        
        db.drop_all()

@pytest.fixture
def integration_client(app_with_containers):
    """Create test client with real database."""
    return app_with_containers.test_client()

@pytest.fixture
def seeded_tenant(app_with_containers):
    """Create a fully seeded tenant with users and roles."""
    from app.services.tenant_service import TenantService
    from app.services.rbac_service import RBACService
    
    with app_with_containers.app_context():
        # Create tenant
        tenant = TenantService().create(
            name='Integration Test Tenant',
            slug='integration-test',
            plan='professional'
        )
        
        # Initialize roles
        RBACService.initialize_tenant_roles(tenant.id)
        
        # Create admin user
        from app.models import User
        from app.services.password_service import PasswordService
        
        user = User(
            tenant_id=tenant.id,
            email='admin@integration.test',
            name='Admin User',
            password_hash=PasswordService().hash('TestPassword123!'),
            is_active=True
        )
        
        from app.models.rbac import Role
        admin_role = Role.query.filter_by(
            tenant_id=tenant.id,
            name='admin'
        ).first()
        user.roles = [admin_role]
        
        db.session.add(user)
        db.session.commit()
        
        return {'tenant': tenant, 'admin_user': user}
```

### Auth Flow Integration Tests

```python
# backend/tests/integration/test_auth_flow.py
import pytest

class TestAuthFlow:
    """Integration tests for authentication flow."""
    
    def test_full_registration_and_login_flow(self, integration_client, seeded_tenant):
        """Test complete registration and login flow."""
        tenant = seeded_tenant['tenant']
        
        # Register new user
        register_response = integration_client.post('/api/v1/auth/register', json={
            'email': 'newuser@integration.test',
            'password': 'SecurePassword123!',
            'name': 'New User',
            'tenant_slug': tenant.slug
        })
        
        assert register_response.status_code == 201
        assert 'id' in register_response.json['data']
        
        # Login with new user
        login_response = integration_client.post('/api/v1/auth/login', json={
            'email': 'newuser@integration.test',
            'password': 'SecurePassword123!'
        })
        
        assert login_response.status_code == 200
        tokens = login_response.json['data']
        assert 'access_token' in tokens
        assert 'refresh_token' in tokens
        
        # Access protected endpoint
        headers = {'Authorization': f"Bearer {tokens['access_token']}"}
        me_response = integration_client.get('/api/v1/auth/me', headers=headers)
        
        assert me_response.status_code == 200
        assert me_response.json['data']['email'] == 'newuser@integration.test'
        
        # Refresh token
        refresh_headers = {'Authorization': f"Bearer {tokens['refresh_token']}"}
        refresh_response = integration_client.post(
            '/api/v1/auth/refresh',
            headers=refresh_headers
        )
        
        assert refresh_response.status_code == 200
        assert 'access_token' in refresh_response.json['data']
        
        # Logout
        logout_response = integration_client.post(
            '/api/v1/auth/logout',
            headers=headers
        )
        
        assert logout_response.status_code == 200
        
        # Verify token is invalidated
        me_after_logout = integration_client.get(
            '/api/v1/auth/me',
            headers=headers
        )
        
        assert me_after_logout.status_code == 401
    
    def test_password_reset_flow(self, integration_client, seeded_tenant):
        """Test password reset flow."""
        user = seeded_tenant['admin_user']
        
        # Request password reset
        reset_request = integration_client.post('/api/v1/auth/forgot-password', json={
            'email': user.email
        })
        
        assert reset_request.status_code == 200
        
        # In real test, we'd get the token from email
        # For integration test, we can check the database directly
        # ...
```

### Data Source Integration Tests

```python
# backend/tests/integration/test_datasource_flow.py
import pytest
from testcontainers.postgres import PostgresContainer

class TestDataSourceFlow:
    """Integration tests for data source management."""
    
    @pytest.fixture
    def source_db(self):
        """Create a source database for testing."""
        with PostgresContainer('postgres:15') as postgres:
            # Create sample table with data
            import psycopg2
            conn = psycopg2.connect(postgres.get_connection_url())
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE orders (
                    id SERIAL PRIMARY KEY,
                    customer_name VARCHAR(100),
                    amount DECIMAL(10, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                INSERT INTO orders (customer_name, amount) VALUES
                ('Alice', 100.00),
                ('Bob', 250.50),
                ('Charlie', 75.25)
            ''')
            conn.commit()
            conn.close()
            
            yield postgres
    
    def test_full_datasource_flow(
        self,
        integration_client,
        seeded_tenant,
        source_db,
        auth_headers
    ):
        """Test complete data source creation and sync flow."""
        
        # Create data source
        create_response = integration_client.post(
            '/api/v1/datasources',
            json={
                'name': 'Test PostgreSQL',
                'type': 'postgresql',
                'connection_config': {
                    'host': source_db.get_container_host_ip(),
                    'port': int(source_db.get_exposed_port(5432)),
                    'database': 'test',
                    'username': 'test',
                    'password': 'test',
                    'ssl': False
                },
                'sync_frequency': '@hourly'
            },
            headers=auth_headers
        )
        
        assert create_response.status_code == 201
        datasource_id = create_response.json['data']['id']
        
        # Test connection
        test_response = integration_client.post(
            f'/api/v1/datasources/{datasource_id}/test',
            headers=auth_headers
        )
        
        assert test_response.status_code == 200
        assert test_response.json['success'] is True
        
        # Get schema
        schema_response = integration_client.get(
            f'/api/v1/datasources/{datasource_id}/schema',
            headers=auth_headers
        )
        
        assert schema_response.status_code == 200
        schemas = schema_response.json['schemas']
        assert 'public' in [s['name'] for s in schemas]
        
        tables = schemas[0]['tables']
        assert 'orders' in [t['name'] for t in tables]
        
        # Trigger sync
        sync_response = integration_client.post(
            f'/api/v1/datasources/{datasource_id}/sync',
            headers=auth_headers
        )
        
        assert sync_response.status_code == 200
        assert 'job_id' in sync_response.json
```

### Dashboard Integration Tests

```python
# backend/tests/integration/test_dashboard_flow.py
import pytest

class TestDashboardFlow:
    """Integration tests for dashboard creation and querying."""
    
    def test_full_dashboard_flow(
        self,
        integration_client,
        seeded_tenant,
        seeded_semantic_layer,
        auth_headers
    ):
        """Test complete dashboard creation and widget flow."""
        
        # Create dashboard
        create_response = integration_client.post(
            '/api/v1/dashboards',
            json={
                'name': 'Sales Dashboard',
                'description': 'Overview of sales metrics',
            },
            headers=auth_headers
        )
        
        assert create_response.status_code == 201
        dashboard_id = create_response.json['data']['id']
        
        # Add widget
        widget_response = integration_client.post(
            f'/api/v1/dashboards/{dashboard_id}/widgets',
            json={
                'name': 'Total Sales',
                'type': 'metric_card',
                'query_config': {
                    'measures': ['total_sales'],
                },
                'viz_config': {
                    'format': 'currency',
                    'showChange': True
                },
                'grid_position': {'x': 0, 'y': 0, 'w': 4, 'h': 2}
            },
            headers=auth_headers
        )
        
        assert widget_response.status_code == 201
        widget_id = widget_response.json['data']['id']
        
        # Get widget data
        data_response = integration_client.get(
            f'/api/v1/dashboards/{dashboard_id}/widgets/{widget_id}/data',
            headers=auth_headers
        )
        
        assert data_response.status_code == 200
        assert 'data' in data_response.json
        
        # Update layout
        layout_response = integration_client.put(
            f'/api/v1/dashboards/{dashboard_id}/layout',
            json={
                'layout': [
                    {'id': widget_id, 'x': 2, 'y': 0, 'w': 6, 'h': 4}
                ]
            },
            headers=auth_headers
        )
        
        assert layout_response.status_code == 200
        
        # Verify layout persisted
        get_response = integration_client.get(
            f'/api/v1/dashboards/{dashboard_id}',
            headers=auth_headers
        )
        
        widget = get_response.json['data']['widgets'][0]
        assert widget['grid_position']['x'] == 2
        assert widget['grid_position']['w'] == 6
```

## Expected Output

```
backend/tests/integration/
├── conftest.py
├── test_auth_flow.py
├── test_datasource_flow.py
├── test_semantic_flow.py
├── test_dashboard_flow.py
├── test_query_flow.py
└── test_admin_flow.py
```

## Acceptance Criteria

- [ ] Tests use real database containers
- [ ] Full user flows tested end-to-end
- [ ] Cross-service interactions verified
- [ ] Data isolation between tests
- [ ] Tests run in < 5 minutes
- [ ] Cleanup after test failures
- [ ] Works in CI/CD environment

## Reference Documents

- [Testing Agent](../agents/testing-agent.agent.md)
- [Unit Test Suite](./034-unit-test-suite.md)
