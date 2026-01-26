"""
NovaSight Authentication Service
================================

User authentication, registration, and token management.
"""

from typing import Optional, Tuple
from datetime import datetime
from app.extensions import db
from app.models.user import User, UserStatus
from app.models.tenant import Tenant, TenantStatus
from app.services.password_service import password_service
from app.services.token_service import login_tracker
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user login, registration, and validation."""
    
    def register_user(
        self,
        email: str,
        password: str,
        name: str,
        tenant_slug: str
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new user.
        
        Args:
            email: User email address
            password: User password (plain text)
            name: User display name
            tenant_slug: Tenant slug
        
        Returns:
            Tuple of (User, None) on success, (None, error_message) on failure
        """
        try:
            # Validate password strength
            is_valid, error_msg = password_service.validate_strength(password)
            if not is_valid:
                return None, error_msg
            
            # Find tenant
            tenant = Tenant.query.filter(Tenant.slug == tenant_slug.lower()).first()
            if not tenant:
                return None, "Tenant not found"
            
            if tenant.status != TenantStatus.ACTIVE:
                return None, "Tenant is not active"
            
            # Check if user already exists in this tenant
            existing_user = User.query.filter(
                User.email == email.lower(),
                User.tenant_id == tenant.id
            ).first()
            
            if existing_user:
                return None, "User with this email already exists"
            
            # Hash password
            password_hash = password_service.hash(password)
            
            # Create user
            user = User(
                email=email.lower(),
                password_hash=password_hash,
                name=name.strip(),
                tenant_id=tenant.id,
                status=UserStatus.ACTIVE,
                email_verified=False,
            )
            
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"New user registered: {email} in tenant {tenant_slug}")
            return user, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            return None, "Registration failed. Please try again."
    
    def authenticate(
        self,
        email: str,
        password: str,
        tenant_slug: Optional[str] = None
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email address
            password: User password
            tenant_slug: Optional tenant slug for multi-tenant login
        
        Returns:
            Tuple of (User, None) on success, (None, error_message) on failure
        """
        identifier = email.lower()
        
        try:
            # Check for lockout
            if login_tracker.is_locked_out(identifier):
                remaining = login_tracker.get_lockout_remaining(identifier)
                minutes = remaining // 60 + 1
                return None, f"Account locked. Try again in {minutes} minutes."
            
            query = User.query.filter(User.email == identifier)
            
            if tenant_slug:
                tenant = Tenant.query.filter(Tenant.slug == tenant_slug.lower()).first()
                if not tenant:
                    login_tracker.record_attempt(identifier, success=False)
                    return None, "Invalid credentials"
                query = query.filter(User.tenant_id == tenant.id)
            
            user = query.first()
            
            if not user:
                logger.warning(f"Authentication failed: user {email} not found")
                login_tracker.record_attempt(identifier, success=False)
                return None, "Invalid credentials"
            
            if user.status != UserStatus.ACTIVE:
                logger.warning(f"Authentication failed: user {email} is not active")
                login_tracker.record_attempt(identifier, success=False)
                return None, "Account is not active"
            
            # Verify password using Argon2
            if not password_service.verify(password, user.password_hash):
                logger.warning(f"Authentication failed: invalid password for {email}")
                login_tracker.record_attempt(identifier, success=False)
                return None, "Invalid credentials"
            
            # Check tenant status
            if user.tenant and user.tenant.status != TenantStatus.ACTIVE:
                logger.warning(f"Authentication failed: tenant {user.tenant.slug} is not active")
                return None, "Tenant is not active"
            
            # Record successful login
            login_tracker.record_attempt(identifier, success=True)
            
            # Update last login timestamp
            user.last_login_at = datetime.utcnow()
            
            # Check if password needs rehash
            if password_service.needs_rehash(user.password_hash):
                user.password_hash = password_service.hash(password)
            
            db.session.commit()
            
            logger.info(f"User {email} authenticated successfully")
            return user, None
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            db.session.rollback()
            return None, "Authentication failed"
    
    def validate_token_identity(self, identity: dict) -> Optional[User]:
        """
        Validate JWT token identity and return associated user.
        
        Args:
            identity: JWT identity payload
        
        Returns:
            User object if valid, None otherwise
        """
        user_id = identity.get("user_id")
        tenant_id = identity.get("tenant_id")
        
        if not user_id:
            return None
        
        user = User.query.filter(
            User.id == user_id,
            User.tenant_id == tenant_id
        ).first()
        
        if not user or user.status != UserStatus.ACTIVE:
            return None
        
        return user
    
    def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Change user password.
        
        Args:
            user: User object
            current_password: Current password
            new_password: New password
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Verify current password
            if not password_service.verify(current_password, user.password_hash):
                return False, "Current password is incorrect"
            
            # Validate new password strength
            is_valid, error_msg = password_service.validate_strength(new_password)
            if not is_valid:
                return False, error_msg
            
            # Check new password is different
            if password_service.verify(new_password, user.password_hash):
                return False, "New password must be different from current password"
            
            # Update password
            user.password_hash = password_service.hash(new_password)
            db.session.commit()
            
            logger.info(f"Password changed for user {user.email}")
            return True, None
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Password change error: {e}")
            return False, "Password change failed"
