"""
NovaSight Audit Log Model
=========================

Comprehensive audit logging for security and compliance.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from app.extensions import db
import enum


class AuditAction(enum.Enum):
    """Audit action enumeration."""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    
    # Resource CRUD
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    
    # DAG Operations
    DAG_DEPLOYED = "dag_deployed"
    DAG_TRIGGERED = "dag_triggered"
    DAG_PAUSED = "dag_paused"
    DAG_UNPAUSED = "dag_unpaused"
    
    # Connection Operations
    CONNECTION_TESTED = "connection_tested"
    SCHEMA_BROWSED = "schema_browsed"
    
    # Data Operations
    QUERY_EXECUTED = "query_executed"
    EXPORT_EXECUTED = "export_executed"
    
    # Admin Operations
    USER_INVITED = "user_invited"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    RLS_POLICY_CHANGED = "rls_policy_changed"


class AuditLog(db.Model):
    """
    Audit log model.
    
    Stores comprehensive audit trail for all significant actions.
    """
    
    __tablename__ = "audit_logs"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tenant context (null for platform-level actions)
    tenant_id = db.Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    
    # Actor
    user_id = db.Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    user_email = db.Column(String(255), nullable=True)  # Denormalized for query efficiency
    
    # Action details
    action = db.Column(
        SQLEnum(AuditAction),
        nullable=False,
        index=True
    )
    
    # Resource affected
    resource_type = db.Column(String(50), nullable=True, index=True)  # e.g., "dag", "connection", "user"
    resource_id = db.Column(String(255), nullable=True)
    resource_name = db.Column(String(255), nullable=True)
    
    # Change details
    old_values = db.Column(JSONB, nullable=True)
    new_values = db.Column(JSONB, nullable=True)
    
    # Request context
    ip_address = db.Column(INET, nullable=True)
    user_agent = db.Column(Text, nullable=True)
    request_id = db.Column(String(100), nullable=True)
    
    # Status
    success = db.Column(db.Boolean, default=True, nullable=False)
    error_message = db.Column(Text, nullable=True)
    
    # Timestamp
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    tenant = relationship("Tenant", foreign_keys=[tenant_id])
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<AuditLog {self.action.value} by {self.user_email}>"
    
    def to_dict(self) -> dict:
        """Convert audit log to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "user_email": self.user_email,
            "action": self.action.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "resource_name": self.resource_name,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }
