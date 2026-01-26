"""
NovaSight User Models
=====================

User, Role, and Permission models for RBAC.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, Enum as SQLEnum, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
import enum


class UserStatus(enum.Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    LOCKED = "locked"


# User-Role association table
user_roles = Table(
    "user_roles",
    db.Model.metadata,
    db.Column("user_id", UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True),
    db.Column("role_id", UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True),
    db.Column("assigned_at", DateTime, default=datetime.utcnow),
    db.Column("assigned_by", UUID(as_uuid=True), nullable=True),
)


class Role(db.Model):
    """
    Role model for RBAC.
    
    Predefined roles: super_admin, tenant_admin, data_engineer, 
    bi_developer, analyst, viewer
    """
    
    __tablename__ = "roles"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(String(100), nullable=False)
    description = db.Column(Text, nullable=True)
    
    # Permission flags (can be extended to JSONB for granular permissions)
    permissions = db.Column(JSONB, default=dict, nullable=False)
    
    # Is this a system role (cannot be deleted/modified)
    is_system = db.Column(Boolean, default=False, nullable=False)
    
    # Tenant scope (null = global role like super_admin)
    tenant_id = db.Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    
    def __repr__(self):
        return f"<Role {self.name}>"
    
    def to_dict(self) -> dict:
        """Convert role to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "permissions": self.permissions,
            "is_system": self.is_system,
        }


class UserRole(db.Model):
    """
    Explicit User-Role association model for additional metadata.
    """
    
    __tablename__ = "user_role_assignments"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role_id = db.Column(UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    assigned_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    assigned_by = db.Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    expires_at = db.Column(DateTime, nullable=True)
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )


class User(db.Model):
    """
    User model.
    
    Represents a user within a tenant context.
    """
    
    __tablename__ = "users"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tenant association
    tenant_id = db.Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    # Authentication
    email = db.Column(String(255), nullable=False, index=True)
    password_hash = db.Column(String(255), nullable=False)
    
    # Profile
    name = db.Column(String(255), nullable=False)
    avatar_url = db.Column(String(500), nullable=True)
    
    # Status
    status = db.Column(
        SQLEnum(UserStatus),
        default=UserStatus.ACTIVE,
        nullable=False
    )
    
    # SSO integration
    sso_provider = db.Column(String(50), nullable=True)
    sso_subject = db.Column(String(255), nullable=True)
    
    # Email verification
    email_verified = db.Column(Boolean, default=False, nullable=False)
    
    # Preferences and settings
    preferences = db.Column(JSONB, default=dict, nullable=False)
    
    # Timestamps
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = db.Column(DateTime, nullable=True)
    
    # Unique email within tenant
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "email", name="uq_tenant_user_email"),
    )
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    
    def __repr__(self):
        return f"<User {self.email}>"
    
    def set_password(self, password: str) -> None:
        """Hash and set user password using Argon2."""
        from app.services.password_service import password_service
        self.password_hash = password_service.hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password against stored hash using Argon2."""
        from app.services.password_service import password_service
        return password_service.verify(password, self.password_hash)
    
    def has_role(self, role_name: str) -> bool:
        """Check if user has a specific role."""
        return any(role.name == role_name for role in self.roles)
    
    def has_any_role(self, role_names: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role.name in role_names for role in self.roles)
    
    def to_dict(self, include_roles: bool = True) -> dict:
        """Convert user to dictionary."""
        result = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
        if include_roles:
            result["roles"] = [role.to_dict() for role in self.roles]
        return result
    
    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE
