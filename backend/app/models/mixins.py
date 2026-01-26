"""
NovaSight Model Mixins
======================

Reusable mixins for SQLAlchemy models.
"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, DateTime, ForeignKey, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Query
from flask import g, has_request_context

from app.extensions import db

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class TenantMixin:
    """
    Mixin for models that belong to a tenant.
    
    Provides:
    - tenant_id foreign key column
    - for_tenant() class method for filtered queries
    - Automatic tenant_id assignment on creation
    
    Usage:
        class Connection(db.Model, TenantMixin):
            __tablename__ = 'connections'
            id = Column(UUID(as_uuid=True), primary_key=True)
            name = Column(String(255), nullable=False)
    """
    
    @declared_attr
    def tenant_id(cls):
        """Foreign key to tenants table in public schema."""
        return Column(
            UUID(as_uuid=True),
            ForeignKey('tenants.id', ondelete='CASCADE'),
            nullable=False,
            index=True
        )
    
    @declared_attr
    def tenant(cls):
        """Relationship to Tenant model."""
        from sqlalchemy.orm import relationship
        return relationship(
            "Tenant",
            foreign_keys=[cls.tenant_id],
            lazy="select"
        )
    
    @classmethod
    def for_tenant(cls, tenant_id: Optional[str] = None) -> Query:
        """
        Query filtered by current tenant.
        
        Args:
            tenant_id: Optional explicit tenant ID. If not provided,
                       uses current request's tenant context.
        
        Returns:
            Query filtered by tenant_id
        
        Usage:
            # Using request context
            connections = Connection.for_tenant().all()
            
            # Explicit tenant
            connections = Connection.for_tenant(some_tenant_id).all()
        """
        if tenant_id is None:
            if has_request_context() and hasattr(g, 'tenant') and g.tenant:
                tenant_id = str(g.tenant.id)
            elif has_request_context() and hasattr(g, 'tenant_id'):
                tenant_id = g.tenant_id
        
        if not tenant_id:
            raise ValueError("Tenant context required for this query")
        
        return cls.query.filter(cls.tenant_id == tenant_id)
    
    @classmethod
    def get_for_tenant(cls, id: str, tenant_id: Optional[str] = None):
        """
        Get a single record by ID within tenant scope.
        
        Args:
            id: Record primary key
            tenant_id: Optional explicit tenant ID
        
        Returns:
            Model instance or None
        """
        return cls.for_tenant(tenant_id).filter(cls.id == id).first()
    
    def _set_tenant_on_create(self):
        """Set tenant_id from context if not already set."""
        if not self.tenant_id and has_request_context():
            if hasattr(g, 'tenant') and g.tenant:
                self.tenant_id = g.tenant.id
            elif hasattr(g, 'tenant_id') and g.tenant_id:
                self.tenant_id = g.tenant_id


class TimestampMixin:
    """
    Mixin for automatic timestamp tracking.
    
    Provides:
    - created_at: Set on insert
    - updated_at: Updated on every change
    """
    
    @declared_attr
    def created_at(cls):
        return Column(
            DateTime,
            default=datetime.utcnow,
            nullable=False
        )
    
    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime,
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False
        )


class AuditMixin(TimestampMixin):
    """
    Mixin for audit tracking.
    
    Extends TimestampMixin with:
    - created_by: User who created the record
    - updated_by: User who last modified the record
    """
    
    @declared_attr
    def created_by(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True
        )
    
    @declared_attr
    def updated_by(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True
        )
    
    def _set_audit_fields(self, is_create: bool = True):
        """Set audit fields from request context."""
        if has_request_context() and hasattr(g, 'current_user_id'):
            user_id = g.current_user_id
            if is_create and not self.created_by:
                self.created_by = user_id
            self.updated_by = user_id


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.
    
    Records are not actually deleted but marked with deleted_at timestamp.
    """
    
    @declared_attr
    def deleted_at(cls):
        return Column(DateTime, nullable=True)
    
    @declared_attr
    def deleted_by(cls):
        return Column(
            UUID(as_uuid=True),
            ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True
        )
    
    @property
    def is_deleted(self) -> bool:
        """Check if record is soft-deleted."""
        return self.deleted_at is not None
    
    def soft_delete(self):
        """Soft delete this record."""
        self.deleted_at = datetime.utcnow()
        if has_request_context() and hasattr(g, 'current_user_id'):
            self.deleted_by = g.current_user_id
    
    def restore(self):
        """Restore a soft-deleted record."""
        self.deleted_at = None
        self.deleted_by = None
    
    @classmethod
    def active(cls) -> Query:
        """Query for non-deleted records only."""
        return cls.query.filter(cls.deleted_at.is_(None))
    
    @classmethod
    def with_deleted(cls) -> Query:
        """Query including deleted records."""
        return cls.query
    
    @classmethod
    def only_deleted(cls) -> Query:
        """Query for deleted records only."""
        return cls.query.filter(cls.deleted_at.isnot(None))
