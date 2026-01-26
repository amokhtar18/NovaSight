"""
NovaSight Tenant Model
======================

Multi-tenant organization model.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.extensions import db
import enum


class TenantStatus(enum.Enum):
    """Tenant status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    ARCHIVED = "archived"


class SubscriptionPlan(enum.Enum):
    """Subscription plan enumeration."""
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class Tenant(db.Model):
    """
    Tenant (organization) model.
    
    Represents a tenant in the multi-tenant architecture.
    Each tenant has isolated data and configurations.
    """
    
    __tablename__ = "tenants"
    __table_args__ = {"schema": "public"}
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(String(255), nullable=False)
    slug = db.Column(String(100), unique=True, nullable=False, index=True)
    
    # Subscription
    plan = db.Column(
        SQLEnum(SubscriptionPlan),
        default=SubscriptionPlan.BASIC,
        nullable=False
    )
    
    # Status
    status = db.Column(
        SQLEnum(TenantStatus),
        default=TenantStatus.ACTIVE,
        nullable=False
    )
    
    # Settings (flexible JSON storage)
    settings = db.Column(JSONB, default=dict, nullable=False)
    
    # Metadata
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    users = db.relationship("User", back_populates="tenant", lazy="dynamic")
    connections = db.relationship("DataConnection", back_populates="tenant", lazy="dynamic")
    dag_configs = db.relationship("DagConfig", back_populates="tenant", lazy="dynamic")
    
    def __repr__(self):
        return f"<Tenant {self.slug}>"
    
    def to_dict(self, include_settings: bool = True) -> dict:
        """Convert tenant to dictionary."""
        result = {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "plan": self.plan.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_settings:
            result["settings"] = self.settings
        return result
    
    @property
    def schema_name(self) -> str:
        """Get the tenant-specific schema name."""
        return f"tenant_{self.slug}"
    
    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == TenantStatus.ACTIVE
