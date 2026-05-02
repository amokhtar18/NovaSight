"""
NovaSight Integration Test Configuration
=========================================

Pytest fixtures for integration tests using test containers
for realistic database and service testing.
"""

import pytest
import os
from typing import Generator, Dict, Any
from flask import Flask
from flask.testing import FlaskClient

# Test container imports (optional - graceful fallback if not available)
try:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False
    PostgresContainer = None
    RedisContainer = None

# Set test environment before importing app
os.environ["FLASK_ENV"] = "testing"
os.environ["TESTING"] = "true"
# Enable the Superset proxy blueprint so its routes are registered on the
# session-scoped integration app. Individual tests still control the
# per-tenant ``FEATURE_SUPERSET_BACKEND`` flag via ``monkeypatch``.
os.environ.setdefault("SUPERSET_ENABLED", "true")

from app import create_app
from app.extensions import db
from app.models import Tenant, User, Role
from app.domains.tenants.domain.models import TenantStatus, SubscriptionPlan
from app.domains.identity.domain.models import UserStatus
from app.platform.security.passwords import password_service
from app.domains.identity.application.rbac_service import RBACService


# =============================================================================
# Container Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def postgres_container():
    """
    Start PostgreSQL test container.
    
    Falls back to configured test database if testcontainers not available.
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not installed")
        return None
    
    container = PostgresContainer("postgres:15")
    container.start()
    
    yield container
    
    container.stop()


@pytest.fixture(scope="session")
def redis_container():
    """
    Start Redis test container.
    
    Falls back to configured test Redis if testcontainers not available.
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not installed")
        return None
    
    container = RedisContainer("redis:7")
    container.start()
    
    yield container
    
    container.stop()


# =============================================================================
# App Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def integration_app() -> Generator[Flask, None, None]:
    """
    Create Flask application for integration testing.
    
    Uses containers if available, otherwise falls back to test config.
    """
    app = create_app("testing")
    
    with app.app_context():
        # Create all tables
        db.create_all()
        yield app
        # Cleanup: close all sessions first to release locks
        db.session.remove()
        
        # Drop tables with CASCADE to avoid FK constraint locks
        from sqlalchemy import text
        try:
            # Disable FK checks temporarily for clean drop
            db.session.execute(text("SET session_replication_role = 'replica';"))
            db.drop_all()
            db.session.execute(text("SET session_replication_role = 'origin';"))
            db.session.commit()
        except Exception:
            db.session.rollback()
            # Fallback
            db.drop_all()


@pytest.fixture(scope="session")
def app_with_containers(postgres_container, redis_container) -> Generator[Flask, None, None]:
    """
    Create Flask application with real database containers.
    
    Provides realistic integration testing environment.
    """
    # Configure app with container connections
    os.environ["DATABASE_URL"] = postgres_container.get_connection_url()
    os.environ["REDIS_URL"] = (
        f"redis://{redis_container.get_container_host_ip()}:"
        f"{redis_container.get_exposed_port(6379)}"
    )
    
    app = create_app("testing")
    
    with app.app_context():
        # Create schema
        db.create_all()
        
        # Run migrations if available
        try:
            from flask_migrate import upgrade
            upgrade()
        except Exception:
            pass  # Migrations may not be needed for tests
        
        yield app
        
        # Cleanup: close all sessions first to release locks
        db.session.remove()
        
        # Drop tables with CASCADE to avoid FK constraint locks
        from sqlalchemy import text
        try:
            db.session.execute(text("SET session_replication_role = 'replica';"))
            db.drop_all()
            db.session.execute(text("SET session_replication_role = 'origin';"))
            db.session.commit()
        except Exception:
            db.session.rollback()
            db.drop_all()


@pytest.fixture
def integration_client(integration_app: Flask) -> FlaskClient:
    """Create test client for integration tests."""
    return integration_app.test_client()


@pytest.fixture
def client_with_containers(app_with_containers: Flask) -> FlaskClient:
    """Create test client with real database containers."""
    return app_with_containers.test_client()


# =============================================================================
# Database Session Fixtures
# =============================================================================

@pytest.fixture
def integration_db(integration_app: Flask) -> Generator:
    """
    Create database session for integration tests.
    
    Uses savepoints for transaction isolation between tests.
    """
    with integration_app.app_context():
        # Start a transaction
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Begin a nested transaction (savepoint)
        nested = connection.begin_nested()
        
        # Configure session to use our connection
        db.session.begin_nested()
        
        yield db.session
        
        # Rollback to clean up
        db.session.rollback()
        transaction.rollback()
        connection.close()


# =============================================================================
# Seeded Data Fixtures
# =============================================================================

@pytest.fixture
def seeded_tenant(integration_app: Flask) -> Dict[str, Any]:
    """
    Create a fully seeded tenant with users and roles.
    
    Returns:
        Dictionary with primitive values for testing (avoids detached session issues)
    """
    import uuid as uuid_module
    from sqlalchemy.orm import make_transient
    
    with integration_app.app_context():
        # Generate unique suffix to avoid conflicts between tests
        unique_suffix = str(uuid_module.uuid4())[:8]
        
        # Create tenant - use string values for enum columns (DB stores as strings)
        tenant = Tenant(
            name="Integration Test Tenant",
            slug=f"integration-test-{unique_suffix}",
            plan="professional",  # String value, not enum
            status="active",  # String value, not enum
            settings={"timezone": "UTC"},
        )
        db.session.add(tenant)
        db.session.flush()
        
        # Create admin role with unique name (due to global unique constraint on role name)
        admin_role_name = f"tenant_admin_{unique_suffix}"
        admin_role = Role.query.filter_by(name=admin_role_name).first()
        
        if not admin_role:
            admin_role = Role(
                tenant_id=tenant.id,
                name=admin_role_name,
                display_name="Tenant Admin",
                description="Full administrative access",
                permissions={"*": ["*"]},
                is_system=True,
            )
            db.session.add(admin_role)
            db.session.flush()
        
        # Admin email and password for tests (use example.com which is a valid test domain)
        admin_email = f"admin-{unique_suffix}@example.com"
        admin_password = "Admin123!"
        
        # Create admin user - use string value for status
        admin_user = User(
            tenant_id=tenant.id,
            email=admin_email,
            name="Admin User",
            password_hash=password_service.hash(admin_password),
            status="active",
        )
        admin_user.roles = [admin_role]
        db.session.add(admin_user)
        db.session.flush()
        
        # Create regular user
        viewer_role_name = f"viewer_{unique_suffix}"
        viewer_role = Role.query.filter_by(name=viewer_role_name).first()
        
        if not viewer_role:
            viewer_role = Role(
                tenant_id=tenant.id,
                name=viewer_role_name,
                display_name="Viewer",
                description="Read-only access",
                permissions={"dashboards": ["view"], "semantic": ["view"]},
                is_system=True,
            )
            db.session.add(viewer_role)
            db.session.flush()
        
        regular_email = f"user-{unique_suffix}@example.com"
        regular_password = "TestPassword123!"
        
        regular_user = User(
            tenant_id=tenant.id,
            email=regular_email,
            name="Regular User",
            password_hash=password_service.hash(regular_password),
            status="active",
        )
        regular_user.roles = [viewer_role]
        db.session.add(regular_user)
        
        db.session.commit()
        
        # Store all attributes we need before leaving context
        tenant_id = str(tenant.id)
        tenant_slug = tenant.slug
        tenant_name = tenant.name
        admin_user_id = str(admin_user.id)
        regular_user_id = str(regular_user.id)
        admin_role_id = str(admin_role.id)
        viewer_role_id = str(viewer_role.id)
        
        # Create detached-safe proxy objects
        class TenantProxy:
            def __init__(self):
                self.id = tenant_id
                self.slug = tenant_slug
                self.name = tenant_name
        
        class UserProxy:
            def __init__(self, user_id, email, name):
                self.id = user_id
                self.email = email
                self.name = name
        
        class RoleProxy:
            def __init__(self, role_id, role_name, display_name):
                self.id = role_id
                self.name = role_name
                self.display_name = display_name
        
        # Return proxy objects that work outside app context
        return {
            "tenant": TenantProxy(),
            "admin_user": UserProxy(admin_user_id, admin_email, "Admin User"),
            "regular_user": UserProxy(regular_user_id, regular_email, "Regular User"),
            "admin_role": RoleProxy(admin_role_id, admin_role_name, "Tenant Admin"),
            "viewer_role": RoleProxy(viewer_role_id, viewer_role_name, "Viewer"),
            # Also provide primitive values for flexibility
            "tenant_id": tenant_id,
            "tenant_slug": tenant_slug,
            "admin_email": admin_email,
            "admin_password": admin_password,
            "regular_email": regular_email,
            "regular_password": regular_password,
        }


@pytest.fixture
def seeded_connection(integration_app: Flask, seeded_tenant: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a seeded data connection for testing.
    
    Returns:
        Dictionary with connection and related objects
    """
    import uuid
    from app.domains.datasources.domain.models import DataConnection, DatabaseType, ConnectionStatus
    
    unique_suffix = uuid.uuid4().hex[:8]
    with integration_app.app_context():
        tenant = seeded_tenant["tenant"]
        admin_user = seeded_tenant["admin_user"]
        
        connection = DataConnection(
            tenant_id=tenant.id,
            name=f"Test PostgreSQL Connection-{unique_suffix}",
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="integration_test_db",
            username="testuser",
            password_encrypted="encrypted:testpassword",
            status=ConnectionStatus.ACTIVE,
            created_by=admin_user.id,
        )
        db.session.add(connection)
        db.session.commit()
        
        # Extract values before leaving session context
        connection_id = str(connection.id)
        connection_name = connection.name
        
        # Create proxy object
        class ConnectionProxy:
            def __init__(self, conn_id, name):
                self.id = conn_id
                self.name = name
        
        return {
            **seeded_tenant,
            "connection": ConnectionProxy(connection_id, connection_name),
            "connection_id": connection_id,
        }


@pytest.fixture
def seeded_semantic_layer(
    integration_app: Flask,
    seeded_connection: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a seeded semantic layer with models, dimensions, and measures.
    
    Returns:
        Dictionary with semantic models and related objects
    """
    from app.domains.transformation.domain.models import (
        SemanticModel,
        Dimension,
        Measure,
        ModelType,
        DimensionType,
        AggregationType,
    )
    
    with integration_app.app_context():
        tenant = seeded_connection["tenant"]
        admin_user = seeded_connection["admin_user"]
        
        # Create fact model
        sales_model = SemanticModel(
            tenant_id=tenant.id,
            name="sales_orders",
            dbt_model="mart_sales_orders",
            label="Sales Orders",
            description="Sales order fact table",
            model_type=ModelType.FACT,
            is_active=True,
            cache_enabled=True,
            cache_ttl_seconds=3600,
        )
        db.session.add(sales_model)
        db.session.flush()
        
        # Create dimensions
        date_dim = Dimension(
            tenant_id=tenant.id,
            semantic_model_id=sales_model.id,
            name="order_date",
            expression="order_date",
            label="Order Date",
            type=DimensionType.TEMPORAL,
        )
        
        customer_dim = Dimension(
            tenant_id=tenant.id,
            semantic_model_id=sales_model.id,
            name="customer_name",
            expression="customer_name",
            label="Customer Name",
            type=DimensionType.CATEGORICAL,
        )
        
        db.session.add_all([date_dim, customer_dim])
        
        # Create measures
        total_sales = Measure(
            tenant_id=tenant.id,
            semantic_model_id=sales_model.id,
            name="total_sales",
            expression="amount",
            label="Total Sales",
            aggregation=AggregationType.SUM,
            format_string="$,.2f",
        )
        
        order_count = Measure(
            tenant_id=tenant.id,
            semantic_model_id=sales_model.id,
            name="order_count",
            expression="id",
            label="Order Count",
            aggregation=AggregationType.COUNT,
        )
        
        db.session.add_all([total_sales, order_count])
        db.session.commit()
        
        # Extract all values before leaving session context
        sales_model_id = str(sales_model.id)
        sales_model_name = sales_model.name
        sales_model_dbt_model = sales_model.dbt_model
        sales_model_label = sales_model.label
        
        date_dim_id = str(date_dim.id)
        date_dim_name = date_dim.name
        customer_dim_id = str(customer_dim.id)
        customer_dim_name = customer_dim.name
        
        total_sales_id = str(total_sales.id)
        total_sales_name = total_sales.name
        order_count_id = str(order_count.id)
        order_count_name = order_count.name
        
        # Create proxy objects
        class SemanticModelProxy:
            def __init__(self, model_id, name, dbt_model, label):
                self.id = model_id
                self.name = name
                self.dbt_model = dbt_model
                self.label = label
        
        class DimensionProxy:
            def __init__(self, dim_id, name):
                self.id = dim_id
                self.name = name
        
        class MeasureProxy:
            def __init__(self, measure_id, name):
                self.id = measure_id
                self.name = name
        
        sales_model_proxy = SemanticModelProxy(
            sales_model_id, sales_model_name, sales_model_dbt_model, sales_model_label
        )
        
        return {
            **seeded_connection,
            "sales_model": sales_model_proxy,
            "sales_model_id": sales_model_id,
            "dimensions": [
                DimensionProxy(date_dim_id, date_dim_name),
                DimensionProxy(customer_dim_id, customer_dim_name),
            ],
            "dimension_ids": [date_dim_id, customer_dim_id],
            "measures": [
                MeasureProxy(total_sales_id, total_sales_name),
                MeasureProxy(order_count_id, order_count_name),
            ],
            "measure_ids": [total_sales_id, order_count_id],
        }


@pytest.fixture
def seeded_dashboard(
    integration_app: Flask,
    seeded_semantic_layer: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a seeded dashboard with widgets.
    
    Returns:
        Dictionary with dashboard and related objects
    """
    from app.domains.analytics.domain.models import Dashboard, Widget, WidgetType
    
    with integration_app.app_context():
        tenant = seeded_semantic_layer["tenant"]
        admin_user = seeded_semantic_layer["admin_user"]
        
        dashboard = Dashboard(
            tenant_id=tenant.id,
            name="Integration Test Dashboard",
            description="Dashboard for integration testing",
            is_public=False,
            created_by=admin_user.id,
            layout=[],
            theme={"mode": "light"},
        )
        db.session.add(dashboard)
        db.session.flush()
        
        # Create widget
        widget = Widget(
            dashboard_id=dashboard.id,
            tenant_id=tenant.id,
            name="Total Sales Card",
            type=WidgetType.METRIC_CARD,
            query_config={
                "measures": ["total_sales"],
            },
            viz_config={
                "format": "currency",
                "showChange": True,
            },
            grid_position={"x": 0, "y": 0, "w": 4, "h": 2},
        )
        db.session.add(widget)
        db.session.commit()
        
        # Extract values before leaving session context
        dashboard_id = str(dashboard.id)
        dashboard_name = dashboard.name
        widget_id = str(widget.id)
        widget_name = widget.name
        
        # Create proxy objects
        class DashboardProxy:
            def __init__(self, dash_id, name):
                self.id = dash_id
                self.name = name
        
        class WidgetProxy:
            def __init__(self, w_id, name):
                self.id = w_id
                self.name = name
        
        return {
            **seeded_semantic_layer,
            "dashboard": DashboardProxy(dashboard_id, dashboard_name),
            "dashboard_id": dashboard_id,
            "widget": WidgetProxy(widget_id, widget_name),
            "widget_id": widget_id,
        }


# =============================================================================
# Authentication Fixtures
# =============================================================================

@pytest.fixture
def auth_headers(integration_client: FlaskClient, seeded_tenant: Dict[str, Any]) -> Dict[str, str]:
    """
    Get authentication headers for admin user.
    
    Returns:
        Dictionary with Authorization header
    """
    # Use primitive values from seeded_tenant
    admin_email = seeded_tenant["admin_email"]
    admin_password = seeded_tenant["admin_password"]
    tenant_slug = seeded_tenant["tenant_slug"]
    
    response = integration_client.post("/api/v1/auth/login", json={
        "email": admin_email,
        "password": admin_password,
        "tenant_slug": tenant_slug,
    })
    
    if response.status_code == 200:
        data = response.get_json()
        return {
            "Authorization": f"Bearer {data.get('access_token')}",
            "Content-Type": "application/json",
        }
    
    # Fallback: generate token directly
    from flask_jwt_extended import create_access_token
    
    admin_user = seeded_tenant["admin_user"]
    tenant = seeded_tenant["tenant"]
    
    with integration_client.application.app_context():
        token = create_access_token(
            identity={
                "user_id": admin_user.id,
                "email": admin_email,
                "tenant_id": tenant.id,
                "roles": ["tenant_admin"],
            }
        )
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }


@pytest.fixture
def viewer_auth_headers(
    integration_client: FlaskClient,
    seeded_tenant: Dict[str, Any]
) -> Dict[str, str]:
    """
    Get authentication headers for regular (viewer) user.
    
    Returns:
        Dictionary with Authorization header
    """
    # Use primitive values from seeded_tenant
    regular_email = seeded_tenant["regular_email"]
    regular_password = seeded_tenant["regular_password"]
    tenant_slug = seeded_tenant["tenant_slug"]
    
    response = integration_client.post("/api/v1/auth/login", json={
        "email": regular_email,
        "password": regular_password,
        "tenant_slug": tenant_slug,
    })
    
    if response.status_code == 200:
        data = response.get_json()
        return {
            "Authorization": f"Bearer {data.get('access_token')}",
            "Content-Type": "application/json",
        }
    
    # Fallback: generate token directly
    from flask_jwt_extended import create_access_token
    
    regular_user = seeded_tenant["regular_user"]
    tenant = seeded_tenant["tenant"]
    
    with integration_client.application.app_context():
        token = create_access_token(
            identity={
                "user_id": regular_user.id,
                "email": regular_email,
                "tenant_id": tenant.id,
                "roles": ["viewer"],
            }
        )
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }


# =============================================================================
# Test Helpers
# =============================================================================

class IntegrationTestHelper:
    """Helper utilities for integration tests."""
    
    @staticmethod
    def assert_success_response(response, expected_status: int = 200) -> Dict[str, Any]:
        """Assert API response is successful and return data."""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}: "
            f"{response.get_json()}"
        )
        return response.get_json()
    
    @staticmethod
    def assert_error_response(
        response,
        expected_status: int = 400,
        error_contains: str = None
    ) -> Dict[str, Any]:
        """Assert API response is an error."""
        assert response.status_code == expected_status, (
            f"Expected {expected_status}, got {response.status_code}"
        )
        data = response.get_json()
        if error_contains:
            assert error_contains.lower() in str(data).lower()
        return data
    
    @staticmethod
    def assert_unauthorized(response):
        """Assert response is unauthorized (401)."""
        assert response.status_code == 401
    
    @staticmethod
    def assert_forbidden(response):
        """Assert response is forbidden (403)."""
        assert response.status_code == 403
    
    @staticmethod
    def assert_not_found(response):
        """Assert response is not found (404)."""
        assert response.status_code == 404


# Export helper for use in tests
helper = IntegrationTestHelper()
