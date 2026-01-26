"""
NovaSight Auth API Tests
========================

Unit tests for authentication endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.services.password_service import password_service


class TestPasswordService:
    """Test password service functionality."""
    
    def test_hash_and_verify_password(self):
        """Test password hashing and verification."""
        password = "SecurePass123!@#"
        
        hashed = password_service.hash(password)
        
        assert hashed is not None
        assert hashed != password
        assert password_service.verify(password, hashed) is True
        assert password_service.verify("wrongpassword", hashed) is False
    
    def test_password_strength_valid(self):
        """Test valid password strength."""
        valid_passwords = [
            "SecurePass123!@#",
            "MyP@ssw0rd2024!",
            "Complex#1Password",
            "AbCdEfGh12!@#$",
        ]
        
        for password in valid_passwords:
            is_valid, error = password_service.validate_strength(password)
            assert is_valid is True, f"Password '{password}' should be valid: {error}"
            assert error is None
    
    def test_password_too_short(self):
        """Test password length validation."""
        is_valid, error = password_service.validate_strength("Short1!")
        
        assert is_valid is False
        assert "12 characters" in error
    
    def test_password_missing_uppercase(self):
        """Test uppercase requirement."""
        is_valid, error = password_service.validate_strength("lowercase123!@#")
        
        assert is_valid is False
        assert "uppercase" in error
    
    def test_password_missing_lowercase(self):
        """Test lowercase requirement."""
        is_valid, error = password_service.validate_strength("UPPERCASE123!@#")
        
        assert is_valid is False
        assert "lowercase" in error
    
    def test_password_missing_digit(self):
        """Test digit requirement."""
        is_valid, error = password_service.validate_strength("NoDigitsHere!@#")
        
        assert is_valid is False
        assert "digit" in error
    
    def test_password_missing_special(self):
        """Test special character requirement."""
        is_valid, error = password_service.validate_strength("NoSpecial1234AB")
        
        assert is_valid is False
        assert "special character" in error
    
    def test_password_common_patterns(self):
        """Test rejection of common patterns."""
        is_valid, error = password_service.validate_strength("Password123456!")
        
        assert is_valid is False
        assert "common" in error.lower()


class TestAuthRegister:
    """Test user registration endpoint."""
    
    def test_register_success(self, client, db_session, sample_tenant):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "SecurePass123!@#",
            "name": "New User",
            "tenant_slug": sample_tenant.slug
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data["message"] == "User registered successfully"
        assert data["user"]["email"] == "newuser@example.com"
    
    def test_register_weak_password(self, client, sample_tenant):
        """Test registration with weak password."""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "weak",
            "name": "New User",
            "tenant_slug": sample_tenant.slug
        })
        
        assert response.status_code == 400
    
    def test_register_invalid_tenant(self, client):
        """Test registration with invalid tenant."""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "SecurePass123!@#",
            "name": "New User",
            "tenant_slug": "nonexistent-tenant"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "not found" in data["message"].lower()
    
    def test_register_duplicate_email(self, client, sample_user, sample_tenant):
        """Test registration with existing email."""
        response = client.post("/api/v1/auth/register", json={
            "email": sample_user.email,
            "password": "SecurePass123!@#",
            "name": "Another User",
            "tenant_slug": sample_tenant.slug
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "already exists" in data["message"].lower()
    
    def test_register_missing_fields(self, client):
        """Test registration with missing fields."""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com"
        })
        
        assert response.status_code == 400


class TestAuthLogin:
    """Test user login endpoint."""
    
    def test_login_success(self, client, sample_user, sample_tenant):
        """Test successful login."""
        response = client.post("/api/v1/auth/login", json={
            "email": sample_user.email,
            "password": "TestPassword123!",  # Default test password
            "tenant_slug": sample_tenant.slug
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["user"]["email"] == sample_user.email
    
    def test_login_invalid_password(self, client, sample_user, sample_tenant):
        """Test login with invalid password."""
        response = client.post("/api/v1/auth/login", json={
            "email": sample_user.email,
            "password": "wrongpassword",
            "tenant_slug": sample_tenant.slug
        })
        
        assert response.status_code == 401
    
    def test_login_invalid_email(self, client, sample_tenant):
        """Test login with non-existent email."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "SomePassword123!",
            "tenant_slug": sample_tenant.slug
        })
        
        assert response.status_code == 401
    
    def test_login_missing_fields(self, client):
        """Test login with missing fields."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com"
        })
        
        assert response.status_code == 400


class TestAuthRefresh:
    """Test token refresh endpoint."""
    
    def test_refresh_success(self, client, auth_headers):
        """Test successful token refresh."""
        # First login to get refresh token
        # Using refresh token header
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {auth_headers['refresh_token']}"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
    
    def test_refresh_with_access_token(self, client, auth_headers):
        """Test refresh with access token (should fail)."""
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {auth_headers['access_token']}"}
        )
        
        # Should fail because access token is not a refresh token
        assert response.status_code == 422  # Unprocessable Entity


class TestAuthMe:
    """Test current user endpoint."""
    
    def test_me_success(self, client, auth_headers):
        """Test getting current user info."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_headers['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert "user" in data
        assert "email" in data["user"]
        assert "tenant_id" in data["user"]
    
    def test_me_no_token(self, client):
        """Test getting current user without token."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401


class TestAuthLogout:
    """Test logout endpoint."""
    
    def test_logout_success(self, client, auth_headers):
        """Test successful logout."""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {auth_headers['access_token']}"}
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data["message"] == "Successfully logged out"
    
    def test_logout_token_blacklisted(self, client, auth_headers):
        """Test that logged out token is blacklisted."""
        access_token = auth_headers['access_token']
        
        # Logout
        client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # Try to access protected endpoint with same token
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # Should be rejected (token revoked)
        assert response.status_code == 401
    
    def test_logout_no_token(self, client):
        """Test logout without token."""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401


class TestTokenBlacklist:
    """Test token blacklist functionality."""
    
    def test_blacklist_add_and_check(self):
        """Test adding token to blacklist and checking."""
        from app.services.token_service import token_blacklist
        
        jti = "test-jti-12345"
        
        # Add to blacklist
        with patch.object(token_blacklist, 'redis') as mock_redis:
            mock_redis.setex.return_value = True
            mock_redis.exists.return_value = 1
            
            result = token_blacklist.add(jti, 3600)
            assert result is True
            
            is_blacklisted = token_blacklist.is_blacklisted(jti)
            assert is_blacklisted is True


class TestLoginAttemptTracker:
    """Test login attempt tracking."""
    
    def test_lockout_after_max_attempts(self):
        """Test account lockout after max failed attempts."""
        from app.services.token_service import LoginAttemptTracker
        
        tracker = LoginAttemptTracker()
        identifier = "test@example.com"
        
        with patch.object(tracker, 'redis') as mock_redis:
            mock_redis.get.return_value = "5"  # At max attempts
            mock_redis.exists.return_value = 1
            
            # Should be locked out
            is_locked = tracker.is_locked_out(identifier)
            assert is_locked is True
