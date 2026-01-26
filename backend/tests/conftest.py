"""
NovaSight Test Configuration
============================

Pytest fixtures and configuration for backend tests.
"""

import os
import pytest
from typing import Generator
from flask import Flask
from flask.testing import FlaskClient

# Set test environment before importing app
os.environ["FLASK_ENV"] = "testing"

from app import create_app
from app.extensions import db
from app.models import Tenant, User, Role
from app.models.tenant import TenantStatus
from app.models.user import UserStatus


@pytest.fixture(scope="session")
def app() -> Generator[Flask, None, None]:
    """Create application for testing."""
    app = create_app("testing")
    
    # Create app context
    with app.app_context():
        yield app


@pytest.fixture(scope="function")
def client(app: Flask) -> FlaskClient:
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app: Flask) -> Generator:
    """Create database session for testing."""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        yield db.session
        
        # Rollback and cleanup
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def sample_tenant(db_session) -> Tenant:
    """Create a sample tenant for testing."""
    tenant = Tenant(
        name="Test Tenant",
        slug="test-tenant",
        plan="professional",
        status=TenantStatus.ACTIVE,
        settings={"timezone": "UTC"}
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def sample_user(db_session, sample_tenant) -> User:
    """Create a sample user for testing."""
    from app.services.password_service import password_service
    
    user = User(
        tenant_id=sample_tenant.id,
        email="test@example.com",
        name="Test User",
        status=UserStatus.ACTIVE,
        password_hash=password_service.hash("TestPassword123!")
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_headers(client: FlaskClient, sample_user: User, sample_tenant: Tenant) -> dict:
    """Get authentication headers for API requests."""
    response = client.post("/api/v1/auth/login", json={
        "email": sample_user.email,
        "password": "TestPassword123!",
        "tenant_slug": sample_tenant.slug
    })
    
    if response.status_code == 200:
        data = response.json
        return {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
        }
    
    # Return empty headers if login fails
    return {"access_token": None, "refresh_token": None}


@pytest.fixture
def admin_role(db_session) -> Role:
    """Create admin role for testing."""
    role = Role(
        name="tenant_admin",
        display_name="Tenant Admin",
        description="Administrator role",
        is_system=True,
        permissions={"tenant": "all"}
    )
    db_session.add(role)
    db_session.commit()
    return role


class TestConfig:
    """Test configuration helpers."""
    
    @staticmethod
    def mock_clickhouse_response(data: list) -> dict:
        """Create mock ClickHouse query response."""
        return {
            "data": data,
            "rows": len(data),
            "statistics": {
                "elapsed": 0.001,
                "rows_read": len(data),
                "bytes_read": 1024
            }
        }
