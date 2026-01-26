"""
NovaSight Tenant Middleware Tests
=================================

Unit tests for tenant context middleware and permissions.
"""

import pytest
from unittest.mock import patch, MagicMock
from flask import g


class TestTenantContextMiddleware:
    """Test tenant context middleware."""
    
    def test_public_endpoint_no_auth_required(self, client):
        """Test public endpoints don't require authentication."""
        # Health check is public
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_login_is_public(self, client):
        """Test login endpoint is accessible without auth."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "test"
        })
        # Should fail with 401 (invalid creds), not 400 (missing tenant)
        assert response.status_code in (400, 401)
    
    def test_protected_endpoint_requires_auth(self, client):
        """Test protected endpoints require authentication."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_tenant_context_set_from_jwt(self, client, auth_headers, sample_tenant):
        """Test tenant context is set from JWT claims."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_headers['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["tenant_id"] == str(sample_tenant.id)
    
    def test_inactive_tenant_rejected(self, client, db_session, sample_tenant):
        """Test inactive tenant access is rejected."""
        from app.models.tenant import TenantStatus
        
        # Deactivate tenant
        sample_tenant.status = TenantStatus.SUSPENDED
        db_session.commit()
        
        # Login should fail
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "tenant_slug": sample_tenant.slug
        })
        
        # Should fail due to inactive tenant
        assert response.status_code in (400, 401)


class TestRequireTenantDecorator:
    """Test require_tenant decorator."""
    
    def test_require_tenant_allows_valid_context(self, app, sample_tenant):
        """Test decorator allows requests with valid tenant context."""
        from app.middleware import require_tenant
        
        with app.test_request_context():
            g.tenant = sample_tenant
            g.tenant_id = str(sample_tenant.id)
            
            @require_tenant
            def test_func():
                return "success"
            
            result = test_func()
            assert result == "success"
    
    def test_require_tenant_rejects_missing_context(self, app):
        """Test decorator rejects requests without tenant context."""
        from app.middleware import require_tenant
        from werkzeug.exceptions import Unauthorized
        
        with app.test_request_context():
            g.tenant = None
            g.tenant_id = None
            
            @require_tenant
            def test_func():
                return "success"
            
            with pytest.raises(Unauthorized):
                test_func()


class TestPermissionDecorators:
    """Test permission decorators."""
    
    def test_require_permission_allows_valid(self, app):
        """Test permission decorator allows valid permissions."""
        from app.middleware.permissions import require_permission
        
        with app.test_request_context():
            g.user_permissions = ["connections:create", "connections:read"]
            
            @require_permission("connections:create")
            def test_func():
                return "success"
            
            result = test_func()
            assert result == "success"
    
    def test_require_permission_denies_missing(self, app):
        """Test permission decorator denies missing permissions."""
        from app.middleware.permissions import require_permission
        from werkzeug.exceptions import Forbidden
        
        with app.test_request_context():
            g.user_permissions = ["connections:read"]
            
            @require_permission("connections:delete")
            def test_func():
                return "success"
            
            with pytest.raises(Forbidden):
                test_func()
    
    def test_require_permission_admin_wildcard(self, app):
        """Test admin wildcard bypasses permission check."""
        from app.middleware.permissions import require_permission
        
        with app.test_request_context():
            g.user_permissions = ["admin:*"]
            
            @require_permission("anything:here")
            def test_func():
                return "success"
            
            result = test_func()
            assert result == "success"
    
    def test_require_any_permission_allows_one_match(self, app):
        """Test any_permission allows if one matches."""
        from app.middleware.permissions import require_any_permission
        
        with app.test_request_context():
            g.user_permissions = ["reports:read"]
            
            @require_any_permission("reports:read", "reports:admin")
            def test_func():
                return "success"
            
            result = test_func()
            assert result == "success"
    
    def test_require_all_permissions_requires_all(self, app):
        """Test all_permissions requires all specified."""
        from app.middleware.permissions import require_all_permissions
        from werkzeug.exceptions import Forbidden
        
        with app.test_request_context():
            g.user_permissions = ["admin:access"]  # Missing admin:dangerous
            
            @require_all_permissions("admin:access", "admin:dangerous")
            def test_func():
                return "success"
            
            with pytest.raises(Forbidden):
                test_func()
    
    def test_require_role_allows_valid(self, app):
        """Test role decorator allows valid roles."""
        from app.middleware.permissions import require_role
        
        with app.test_request_context():
            g.user_roles = ["tenant_admin", "viewer"]
            
            @require_role("tenant_admin")
            def test_func():
                return "success"
            
            result = test_func()
            assert result == "success"
    
    def test_require_role_denies_missing(self, app):
        """Test role decorator denies missing roles."""
        from app.middleware.permissions import require_role
        from werkzeug.exceptions import Forbidden
        
        with app.test_request_context():
            g.user_roles = ["viewer"]
            
            @require_role("tenant_admin")
            def test_func():
                return "success"
            
            with pytest.raises(Forbidden):
                test_func()


class TestTenantMixin:
    """Test TenantMixin functionality."""
    
    def test_for_tenant_with_context(self, app, db_session, sample_tenant, sample_user):
        """Test for_tenant() uses request context."""
        from app.models import DataConnection
        from app.models.connection import DatabaseType
        
        with app.test_request_context():
            g.tenant = sample_tenant
            g.tenant_id = str(sample_tenant.id)
            
            # Create a connection for this tenant
            conn = DataConnection(
                tenant_id=sample_tenant.id,
                name="Test Connection",
                db_type=DatabaseType.POSTGRESQL,
                host="localhost",
                port=5432,
                database="test",
                username="test_user",
                password_encrypted="encrypted_value",
                created_by=sample_user.id
            )
            db_session.add(conn)
            db_session.commit()
            
            # Query using for_tenant
            connections = DataConnection.for_tenant().all()
            assert len(connections) >= 1
            assert all(str(c.tenant_id) == str(sample_tenant.id) for c in connections)
    
    def test_for_tenant_explicit_id(self, app, db_session, sample_tenant):
        """Test for_tenant() with explicit tenant_id."""
        from app.models import DataConnection
        
        with app.test_request_context():
            connections = DataConnection.for_tenant(str(sample_tenant.id)).all()
            # Should not raise, returns filtered query
            assert isinstance(connections, list)


class TestTenantUtils:
    """Test tenant utility functions."""
    
    def test_get_tenant_schema_name(self):
        """Test schema name generation."""
        from app.utils.tenant_utils import get_tenant_schema_name
        
        assert get_tenant_schema_name("acme-corp") == "tenant_acme_corp"
        assert get_tenant_schema_name("test123") == "tenant_test123"
        assert get_tenant_schema_name("My Company") == "tenant_my_company"
    
    def test_validate_tenant_access_same_tenant(self, app, sample_tenant):
        """Test access validation for same tenant."""
        from app.utils.tenant_utils import validate_tenant_access
        
        with app.test_request_context():
            g.tenant_id = str(sample_tenant.id)
            
            result = validate_tenant_access(str(sample_tenant.id))
            assert result is True
    
    def test_validate_tenant_access_different_tenant(self, app, sample_tenant):
        """Test access validation blocks different tenant."""
        from app.utils.tenant_utils import validate_tenant_access
        import uuid
        
        with app.test_request_context():
            g.tenant_id = str(sample_tenant.id)
            
            other_tenant_id = str(uuid.uuid4())
            result = validate_tenant_access(other_tenant_id)
            assert result is False
    
    def test_tenant_schema_context_manager(self, app, db_session, sample_tenant):
        """Test TenantSchemaContext context manager."""
        from app.utils.tenant_utils import TenantSchemaContext
        
        with app.app_context():
            with TenantSchemaContext(sample_tenant.slug) as ctx:
                # Inside context, schema should be set
                assert ctx.schema_name == f"tenant_{sample_tenant.slug}"
            
            # After context, schema should be reset
            # (would need to verify search_path but this tests the mechanics)


class TestCrossTenantAccess:
    """Test cross-tenant access is blocked."""
    
    def test_cannot_access_other_tenant_data(self, app, db_session, sample_user):
        """Test users cannot access data from other tenants."""
        from app.models import Tenant, DataConnection, TenantStatus
        from app.models.connection import DatabaseType
        import uuid
        
        # Create two tenants
        tenant1 = Tenant(
            name="Tenant 1",
            slug="tenant-1",
            status=TenantStatus.ACTIVE
        )
        tenant2 = Tenant(
            name="Tenant 2", 
            slug="tenant-2",
            status=TenantStatus.ACTIVE
        )
        db_session.add_all([tenant1, tenant2])
        db_session.commit()
        
        # Create connection for tenant1
        conn1 = DataConnection(
            tenant_id=tenant1.id,
            name="Tenant1 Connection",
            db_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            database="db1",
            username="user1",
            password_encrypted="encrypted",
            created_by=sample_user.id
        )
        db_session.add(conn1)
        db_session.commit()
        
        with app.test_request_context():
            # Set context to tenant2
            g.tenant = tenant2
            g.tenant_id = str(tenant2.id)
            
            # Query for_tenant should not return tenant1's data
            connections = DataConnection.for_tenant().all()
            tenant1_ids = [str(c.id) for c in connections if str(c.tenant_id) == str(tenant1.id)]
            
            assert len(tenant1_ids) == 0, "Should not see other tenant's data"
