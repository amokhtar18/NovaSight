# 032 - Audit Logging

## Metadata

```yaml
prompt_id: "032"
phase: 5
agent: "@security"
model: "opus 4.5"
priority: P0
estimated_effort: "2 days"
dependencies: ["003", "031"]
```

## Objective

Implement comprehensive audit logging for security and compliance.

## Task Description

Create an audit logging system that tracks all significant actions with tamper-evident storage.

## Requirements

### Audit Log Model

```python
# backend/app/models/audit.py
from app.extensions import db
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from datetime import datetime
import hashlib
import json

class AuditLog(db.Model):
    """Immutable audit log entry."""
    __tablename__ = 'audit_logs'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    
    # When
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Who
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.id'))
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    user_email = db.Column(db.String(255))  # Denormalized for queries
    
    # What
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(UUID(as_uuid=True))
    resource_name = db.Column(db.String(255))
    
    # Details
    changes = db.Column(JSONB)  # Before/after for updates
    metadata = db.Column(JSONB)  # Additional context
    
    # Where
    ip_address = db.Column(INET)
    user_agent = db.Column(db.String(500))
    
    # Integrity
    previous_hash = db.Column(db.String(64))  # Hash of previous entry
    entry_hash = db.Column(db.String(64), nullable=False)
    
    # Status
    severity = db.Column(db.String(20), default='info')  # info, warning, critical
    
    __table_args__ = (
        db.Index('idx_audit_tenant_timestamp', 'tenant_id', 'timestamp'),
        db.Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        db.Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )
    
    def calculate_hash(self) -> str:
        """Calculate hash for integrity verification."""
        data = {
            'timestamp': self.timestamp.isoformat(),
            'tenant_id': str(self.tenant_id) if self.tenant_id else None,
            'user_id': str(self.user_id) if self.user_id else None,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': str(self.resource_id) if self.resource_id else None,
            'changes': self.changes,
            'previous_hash': self.previous_hash,
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
```

### Audit Service

```python
# backend/app/services/audit_service.py
from typing import Dict, Any, Optional, List
from datetime import datetime
from flask import request, g
from app.models.audit import AuditLog
from app.extensions import db
import uuid

class AuditService:
    """Service for audit logging."""
    
    # Actions that should be logged
    AUDITED_ACTIONS = {
        # Authentication
        'auth.login': 'info',
        'auth.logout': 'info',
        'auth.login_failed': 'warning',
        'auth.password_changed': 'info',
        'auth.password_reset': 'info',
        
        # Users
        'user.created': 'info',
        'user.updated': 'info',
        'user.deleted': 'warning',
        'user.role_changed': 'info',
        
        # Data sources
        'datasource.created': 'info',
        'datasource.updated': 'info',
        'datasource.deleted': 'warning',
        'datasource.credentials_updated': 'critical',
        
        # Dashboards
        'dashboard.created': 'info',
        'dashboard.updated': 'info',
        'dashboard.deleted': 'info',
        'dashboard.shared': 'info',
        
        # Queries
        'query.executed': 'info',
        'query.exported': 'info',
        
        # Admin
        'tenant.created': 'critical',
        'tenant.updated': 'info',
        'tenant.deactivated': 'critical',
        'role.created': 'info',
        'role.permissions_changed': 'warning',
    }
    
    @classmethod
    def log(
        cls,
        action: str,
        resource_type: str,
        resource_id: str = None,
        resource_name: str = None,
        changes: Dict = None,
        metadata: Dict = None,
        user_id: str = None,
        tenant_id: str = None
    ) -> AuditLog:
        """Create an audit log entry."""
        
        # Get context from Flask g object if not provided
        if not user_id and hasattr(g, 'current_user_id'):
            user_id = g.current_user_id
        if not tenant_id and hasattr(g, 'tenant'):
            tenant_id = g.tenant.id
        
        # Get user email for denormalization
        user_email = None
        if user_id:
            from app.models import User
            user = User.query.get(user_id)
            if user:
                user_email = user.email
        
        # Get previous entry hash for chain
        previous = AuditLog.query.filter_by(
            tenant_id=tenant_id
        ).order_by(AuditLog.timestamp.desc()).first()
        previous_hash = previous.entry_hash if previous else None
        
        # Determine severity
        severity = cls.AUDITED_ACTIONS.get(action, 'info')
        
        # Create entry
        entry = AuditLog(
            id=uuid.uuid4(),
            timestamp=datetime.utcnow(),
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            changes=changes,
            metadata=metadata,
            ip_address=request.remote_addr if request else None,
            user_agent=request.user_agent.string if request else None,
            previous_hash=previous_hash,
            severity=severity
        )
        
        # Calculate and set entry hash
        entry.entry_hash = entry.calculate_hash()
        
        db.session.add(entry)
        db.session.commit()
        
        return entry
    
    @classmethod
    def query(
        cls,
        tenant_id: str,
        user_id: str = None,
        action: str = None,
        resource_type: str = None,
        resource_id: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        severity: str = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """Query audit logs with filters."""
        query = AuditLog.query.filter_by(tenant_id=tenant_id)
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        if action:
            query = query.filter(AuditLog.action.like(f'{action}%'))
        if resource_type:
            query = query.filter_by(resource_type=resource_type)
        if resource_id:
            query = query.filter_by(resource_id=resource_id)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        if severity:
            query = query.filter_by(severity=severity)
        
        query = query.order_by(AuditLog.timestamp.desc())
        pagination = query.paginate(page=page, per_page=per_page)
        
        return {
            'items': pagination.items,
            'total': pagination.total,
            'page': page,
            'per_page': per_page,
        }
    
    @classmethod
    def verify_integrity(cls, tenant_id: str) -> Dict[str, Any]:
        """Verify audit log chain integrity."""
        entries = AuditLog.query.filter_by(
            tenant_id=tenant_id
        ).order_by(AuditLog.timestamp.asc()).all()
        
        issues = []
        previous_hash = None
        
        for entry in entries:
            # Check hash chain
            if entry.previous_hash != previous_hash:
                issues.append({
                    'entry_id': str(entry.id),
                    'issue': 'Hash chain broken',
                    'timestamp': entry.timestamp.isoformat(),
                })
            
            # Verify entry hash
            calculated = entry.calculate_hash()
            if entry.entry_hash != calculated:
                issues.append({
                    'entry_id': str(entry.id),
                    'issue': 'Entry hash mismatch (possible tampering)',
                    'timestamp': entry.timestamp.isoformat(),
                })
            
            previous_hash = entry.entry_hash
        
        return {
            'verified': len(issues) == 0,
            'total_entries': len(entries),
            'issues': issues,
        }
```

### Audit Decorator

```python
# backend/app/middleware/audit.py
from functools import wraps
from app.services.audit_service import AuditService

def audited(action: str, resource_type: str):
    """Decorator to automatically audit an action."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            
            # Extract resource info from result or kwargs
            resource_id = kwargs.get('id') or (
                result.get('id') if isinstance(result, dict) else
                getattr(result, 'id', None)
            )
            
            AuditService.log(
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
            )
            
            return result
        return wrapper
    return decorator

# Usage:
# @audited('dashboard.created', 'dashboard')
# def create_dashboard(...):
```

## Expected Output

```
backend/app/
├── models/
│   └── audit.py
├── services/
│   └── audit_service.py
├── middleware/
│   └── audit.py
└── api/v1/
    └── audit.py
```

## Acceptance Criteria

- [ ] All audited actions are logged
- [ ] Hash chain maintains integrity
- [ ] Query API with filters works
- [ ] Integrity verification works
- [ ] IP address and user agent captured
- [ ] Changes (before/after) stored for updates
- [ ] Critical actions have higher severity
- [ ] Logs are immutable (no update/delete)

## Reference Documents

- [Security Agent](../agents/security-agent.agent.md)
- [BRD - Epic 7](../../docs/requirements/BRD_Part4.md)
