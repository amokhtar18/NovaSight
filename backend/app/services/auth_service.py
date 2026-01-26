"""
NovaSight Authentication Service
================================

User authentication and token management.
"""

from typing import Optional
from datetime import datetime
from app.extensions import db
from app.models.user import User
from app.models.tenant import Tenant, TenantStatus
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user login and validation."""
    
    def authenticate(
        self,
        email: str,
        password: str,
        tenant_id: Optional[str] = None
    ) -> Optional[User]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email address
            password: User password
            tenant_id: Optional tenant ID for multi-tenant login
        
        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            query = User.query.filter(User.email == email)
            
            if tenant_id:
                query = query.filter(User.tenant_id == tenant_id)
            
            user = query.first()
            
            if not user:
                logger.warning(f"Authentication failed: user {email} not found")
                return None
            
            if not user.is_active():
                logger.warning(f"Authentication failed: user {email} is not active")
                return None
            
            if not user.check_password(password):
                logger.warning(f"Authentication failed: invalid password for {email}")
                return None
            
            # Check tenant status
            if user.tenant and not user.tenant.is_active():
                logger.warning(f"Authentication failed: tenant {user.tenant.slug} is not active")
                return None
            
            # Update last login timestamp
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"User {email} authenticated successfully")
            return user
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            db.session.rollback()
            return None
    
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
        
        if not user or not user.is_active():
            return None
        
        return user
