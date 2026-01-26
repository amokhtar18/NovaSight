# 034 - Unit Test Suite

## Metadata

```yaml
prompt_id: "034"
phase: 6
agent: "@testing"
model: "sonnet 4.5"
priority: P0
estimated_effort: "4 days"
dependencies: ["003", "008", "013"]
```

## Objective

Implement comprehensive unit test suite for backend services.

## Task Description

Create pytest-based unit tests with fixtures, mocking, and coverage requirements.

## Requirements

### Test Configuration

```python
# backend/tests/conftest.py
import pytest
from app import create_app
from app.extensions import db
from app.models import Tenant, User, Role
from app.services.password_service import PasswordService
import uuid

@pytest.fixture(scope='session')
def app():
    """Create application for testing."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def db_session(app):
    """Create database session for testing."""
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        
        options = dict(bind=connection, binds={})
        session = db.create_scoped_session(options=options)
        
        db.session = session
        
        yield session
        
        transaction.rollback()
        connection.close()
        session.remove()

@pytest.fixture
def test_tenant(db_session):
    """Create a test tenant."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name='Test Tenant',
        slug='test-tenant',
        plan='professional',
        is_active=True
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant

@pytest.fixture
def test_user(db_session, test_tenant):
    """Create a test user."""
    password_service = PasswordService()
    
    user = User(
        id=uuid.uuid4(),
        tenant_id=test_tenant.id,
        email='test@example.com',
        name='Test User',
        password_hash=password_service.hash('SecurePassword123!'),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def auth_headers(test_user, app):
    """Create authorization headers with JWT token."""
    from flask_jwt_extended import create_access_token
    
    with app.app_context():
        token = create_access_token(
            identity=str(test_user.id),
            additional_claims={
                'tenant_id': str(test_user.tenant_id),
                'roles': ['admin'],
                'permissions': ['*'],
            }
        )
        return {'Authorization': f'Bearer {token}'}

@pytest.fixture
def mock_clickhouse(mocker):
    """Mock ClickHouse client."""
    mock = mocker.patch('app.services.clickhouse.ClickHouseClient')
    mock.return_value.execute.return_value = []
    return mock

@pytest.fixture
def mock_ollama(mocker):
    """Mock Ollama client."""
    mock = mocker.patch('app.services.ollama.client.OllamaClient')
    mock.return_value.generate.return_value = '{"dimensions": [], "measures": []}'
    return mock
```

### Template Engine Tests

```python
# backend/tests/unit/test_template_engine.py
import pytest
from app.services.template_engine import TemplateEngine
from app.services.template_engine.validator import ColumnDefinition, SQLIdentifier

class TestTemplateEngine:
    """Tests for template engine."""
    
    @pytest.fixture
    def engine(self, tmp_path):
        """Create template engine with test templates."""
        templates_dir = tmp_path / 'templates'
        templates_dir.mkdir()
        
        # Create test template
        (templates_dir / 'test.sql.j2').write_text(
            "SELECT * FROM {{ table_name | sql_safe }}"
        )
        
        return TemplateEngine(str(templates_dir))
    
    def test_render_simple_template(self, engine):
        """Test basic template rendering."""
        result = engine.render('test.sql.j2', {'table_name': 'users'})
        assert result == 'SELECT * FROM users'
    
    def test_sql_safe_filter_blocks_injection(self, engine):
        """Test SQL injection prevention."""
        with pytest.raises(ValueError):
            engine.render('test.sql.j2', {'table_name': 'users; DROP TABLE users;'})
    
    def test_sql_safe_filter_allows_valid_names(self, engine):
        """Test valid SQL identifiers pass."""
        result = engine.render('test.sql.j2', {'table_name': 'user_accounts_2024'})
        assert 'user_accounts_2024' in result


class TestColumnDefinitionValidator:
    """Tests for column definition validation."""
    
    def test_valid_column_definition(self):
        """Test valid column definition passes."""
        col = ColumnDefinition(
            name='user_id',
            type='UUID',
            nullable=False
        )
        assert col.name == 'user_id'
    
    def test_invalid_column_name_rejected(self):
        """Test invalid column name is rejected."""
        with pytest.raises(ValueError):
            ColumnDefinition(
                name='User ID',  # Spaces not allowed
                type='VARCHAR(100)'
            )
    
    def test_invalid_type_rejected(self):
        """Test invalid type is rejected."""
        with pytest.raises(ValueError):
            ColumnDefinition(
                name='column',
                type='INVALID_TYPE'
            )
    
    def test_sql_identifier_validation(self):
        """Test SQL identifier validation."""
        # Valid
        SQLIdentifier(name='valid_name')
        SQLIdentifier(name='table123')
        
        # Invalid
        with pytest.raises(ValueError):
            SQLIdentifier(name='123invalid')  # Can't start with number
        
        with pytest.raises(ValueError):
            SQLIdentifier(name='SELECT')  # Reserved word (if checked)
```

### Auth Service Tests

```python
# backend/tests/unit/test_auth_service.py
import pytest
from app.services.auth_service import AuthService
from app.services.password_service import PasswordService

class TestPasswordService:
    """Tests for password service."""
    
    @pytest.fixture
    def service(self):
        return PasswordService()
    
    def test_hash_password(self, service):
        """Test password hashing."""
        password = 'SecurePassword123!'
        hashed = service.hash(password)
        
        assert hashed != password
        assert hashed.startswith('$argon2')
    
    def test_verify_correct_password(self, service):
        """Test correct password verification."""
        password = 'SecurePassword123!'
        hashed = service.hash(password)
        
        assert service.verify(password, hashed) is True
    
    def test_verify_incorrect_password(self, service):
        """Test incorrect password verification."""
        hashed = service.hash('SecurePassword123!')
        
        assert service.verify('WrongPassword', hashed) is False
    
    def test_password_strength_validation(self, service):
        """Test password strength requirements."""
        # Too short
        valid, msg = service.validate_strength('short')
        assert valid is False
        assert 'length' in msg.lower()
        
        # No uppercase
        valid, msg = service.validate_strength('alllowercase123!')
        assert valid is False
        
        # Valid password
        valid, msg = service.validate_strength('SecurePassword123!')
        assert valid is True


class TestAuthService:
    """Tests for auth service."""
    
    def test_login_success(self, db_session, test_user, client):
        """Test successful login."""
        response = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'SecurePassword123!'
        })
        
        assert response.status_code == 200
        assert 'access_token' in response.json['data']
        assert 'refresh_token' in response.json['data']
    
    def test_login_invalid_password(self, db_session, test_user, client):
        """Test login with invalid password."""
        response = client.post('/api/v1/auth/login', json={
            'email': 'test@example.com',
            'password': 'WrongPassword'
        })
        
        assert response.status_code == 401
    
    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent user."""
        response = client.post('/api/v1/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123!'
        })
        
        assert response.status_code == 401
```

### Data Source Tests

```python
# backend/tests/unit/test_datasource_service.py
import pytest
from unittest.mock import Mock, patch
from app.services.datasource_service import DataSourceService
from app.connectors.postgresql import PostgreSQLConnector

class TestDataSourceService:
    """Tests for data source service."""
    
    def test_create_datasource(self, db_session, test_tenant):
        """Test creating a new data source."""
        datasource = DataSourceService.create(
            tenant_id=test_tenant.id,
            name='Test DB',
            type='postgresql',
            connection_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'testdb',
                'username': 'user',
                'password': 'pass',
            }
        )
        
        assert datasource.name == 'Test DB'
        assert datasource.type.value == 'postgresql'
        assert datasource.tenant_id == test_tenant.id
    
    def test_credentials_encrypted(self, db_session, test_tenant):
        """Test that credentials are encrypted at rest."""
        datasource = DataSourceService.create(
            tenant_id=test_tenant.id,
            name='Test DB',
            type='postgresql',
            connection_config={
                'host': 'localhost',
                'port': 5432,
                'database': 'testdb',
                'username': 'user',
                'password': 'mysecretpassword',
            }
        )
        
        # Password should be encrypted in DB
        raw_config = datasource.connection_config
        assert 'mysecretpassword' not in str(raw_config)
    
    @patch.object(PostgreSQLConnector, 'test_connection')
    def test_test_connection_success(self, mock_test, db_session, test_tenant):
        """Test successful connection test."""
        mock_test.return_value = True
        
        datasource = DataSourceService.create(...)
        result = DataSourceService.test_connection(datasource.id, test_tenant.id)
        
        assert result['success'] is True
    
    @patch.object(PostgreSQLConnector, 'test_connection')
    def test_test_connection_failure(self, mock_test, db_session, test_tenant):
        """Test failed connection test."""
        mock_test.side_effect = Exception('Connection refused')
        
        datasource = DataSourceService.create(...)
        result = DataSourceService.test_connection(datasource.id, test_tenant.id)
        
        assert result['success'] is False
        assert 'Connection refused' in result['message']
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_template_engine.py

# Run tests matching pattern
pytest -k "test_auth"

# Run with verbose output
pytest -v

# Run parallel (requires pytest-xdist)
pytest -n auto
```

## Expected Output

```
backend/tests/
├── conftest.py
├── unit/
│   ├── __init__.py
│   ├── test_template_engine.py
│   ├── test_auth_service.py
│   ├── test_password_service.py
│   ├── test_datasource_service.py
│   ├── test_semantic_service.py
│   ├── test_dashboard_service.py
│   ├── test_rbac_service.py
│   └── test_encryption_service.py
└── fixtures/
    ├── __init__.py
    └── sample_data.py
```

## Acceptance Criteria

- [ ] Test coverage > 80%
- [ ] All services have unit tests
- [ ] Database transactions rolled back after tests
- [ ] Mocks used for external services
- [ ] Tests run in < 60 seconds
- [ ] No flaky tests
- [ ] Tests pass in CI/CD

## Reference Documents

- [Testing Agent](../agents/testing-agent.agent.md)
- [Flask API Skill](../skills/flask-api/SKILL.md)
