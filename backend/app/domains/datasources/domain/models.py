"""
NovaSight Data Sources Domain — Models
=======================================

SQLAlchemy models and enums for data source connections.
Canonical location: ``app.domains.datasources.domain.models``

Changes from legacy ``app.models.connection``:
- Adopts ``TenantMixin`` for consistent tenant_id handling
- Adopts ``TimestampMixin`` for automatic created_at / updated_at
- Keeps ``created_by`` as an explicit column (not from AuditMixin)
  because connections don't track ``updated_by`` today.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin

import enum


# ─── Enums ──────────────────────────────────────────────────────────

class SourceCategory(enum.Enum):
    """High-level source category."""
    DATABASE = "database"
    FILE = "file"


class DatabaseType(enum.Enum):
    """Supported database types (SQL connections only).

    File ingestion is handled by the dlt pipeline builder via
    ``source_kind = 'file'`` and is not represented as a connection type.
    """
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    MYSQL = "mysql"
    CLICKHOUSE = "clickhouse"

    @property
    def category(self) -> SourceCategory:
        return SourceCategory.DATABASE

    @property
    def is_file_based(self) -> bool:
        return False


class ConnectionStatus(enum.Enum):
    """Connection status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"


class QueryType(enum.Enum):
    """Saved query type for categorization."""
    ADHOC = "adhoc"
    PYSPARK = "pyspark"
    DBT = "dbt"
    REPORT = "report"


# ─── SavedQuery Model ──────────────────────────────────────────────

class SavedQuery(TenantMixin, TimestampMixin, db.Model):
    """
    Saved SQL query model.
    
    Stores reusable SQL queries that can be used in:
    - SQL Editor
    - PySpark builder
    - dbt modeling
    """
    
    __tablename__ = "saved_queries"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Query metadata
    name = db.Column(String(255), nullable=False)
    description = db.Column(Text, nullable=True)
    
    # Query content
    sql = db.Column(Text, nullable=False)
    
    # Classification
    query_type = db.Column(
        SQLEnum(QueryType),
        default=QueryType.ADHOC,
        nullable=False,
    )
    tags = db.Column(JSONB, default=list, nullable=False)
    
    # Connection reference (optional - for connection-specific queries)
    connection_id = db.Column(UUID(as_uuid=True), ForeignKey("data_connections.id"), nullable=True)
    
    # For ClickHouse tenant DB queries
    is_clickhouse = db.Column(Boolean, default=False, nullable=False)
    
    # Visibility
    is_public = db.Column(Boolean, default=False, nullable=False)  # Shared within tenant
    
    # Audit
    created_by = db.Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Unique name within tenant
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "name", name="uq_tenant_savedquery_name"),
    )
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    connection = relationship("DataConnection", foreign_keys=[connection_id])
    
    def __repr__(self):
        return f"<SavedQuery {self.name}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "description": self.description,
            "sql": self.sql,
            "query_type": self.query_type.value,
            "tags": self.tags or [],
            "connection_id": str(self.connection_id) if self.connection_id else None,
            "is_clickhouse": self.is_clickhouse,
            "is_public": self.is_public,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ─── DataConnection Model ──────────────────────────────────────────

class DataConnection(TenantMixin, TimestampMixin, db.Model):
    """
    Data source connection model.

    Stores encrypted database connection configurations.
    Credentials are encrypted at rest using tenant-specific keys
    via the unified ``platform.security.encryption.EncryptionService``.

    Uses:
    - ``TenantMixin`` → ``tenant_id`` FK + ``for_tenant()`` helper
    - ``TimestampMixin`` → ``created_at``, ``updated_at``
    """

    __tablename__ = "data_connections"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Connection identity
    name = db.Column(String(255), nullable=False)
    description = db.Column(Text, nullable=True)

    # Connection type
    db_type = db.Column(
        SQLEnum(DatabaseType),
        nullable=False,
    )

    # Connection parameters (nullable for file-based sources)
    host = db.Column(String(255), nullable=True)
    port = db.Column(Integer, nullable=True)
    database = db.Column(String(255), nullable=True)
    schema_name = db.Column(String(255), nullable=True)  # Default schema

    # Credentials (encrypted, nullable for file-based sources)
    username = db.Column(String(255), nullable=True)
    password_encrypted = db.Column(Text, nullable=True)  # AES-256 encrypted

    # SSL / Security
    ssl_mode = db.Column(String(50), nullable=True)
    ssl_cert = db.Column(Text, nullable=True)  # Encrypted if present

    # Additional connection parameters
    extra_params = db.Column(JSONB, default=dict, nullable=False)

    # Status
    status = db.Column(
        SQLEnum(ConnectionStatus),
        default=ConnectionStatus.ACTIVE,
        nullable=False,
    )
    last_tested_at = db.Column(DateTime, nullable=True)
    last_test_result = db.Column(JSONB, nullable=True)

    # Audit — who created the connection
    created_by = db.Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Unique name within tenant
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "name", name="uq_tenant_connection_name"),
    )

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<DataConnection {self.name}>"

    def to_dict(self, mask_password: bool = True) -> dict:
        """Convert connection to dictionary."""
        result = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "name": self.name,
            "description": self.description,
            "db_type": self.db_type.value,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "schema_name": self.schema_name,
            "username": self.username,
            "ssl_mode": self.ssl_mode,
            "extra_params": self.extra_params,
            "status": self.status.value,
            "last_tested_at": self.last_tested_at.isoformat() if self.last_tested_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "created_by": str(self.created_by),
        }
        if mask_password:
            result["password"] = "********"
        return result

    def get_connection_string(self, password: str = "") -> str:
        """Generate SQLAlchemy connection string."""
        dialect_map = {
            DatabaseType.POSTGRESQL: "postgresql+psycopg2",
            DatabaseType.ORACLE: "oracle+oracledb",
            DatabaseType.SQLSERVER: "mssql+pyodbc",
            DatabaseType.MYSQL: "mysql+pymysql",
            DatabaseType.CLICKHOUSE: "clickhouse+native",
        }

        dialect = dialect_map.get(self.db_type, "postgresql+psycopg2")

        # Oracle requires special handling: SQLAlchemy's oracle+oracledb URL
        # treats the path component as service_name (Easy Connect format).
        # If the user stored an SID in `database` and provided `service_name`
        # in extra_params, we must route those correctly.
        if self.db_type == DatabaseType.ORACLE:
            extra = self.extra_params or {}
            service_name = extra.get("service_name")
            query_parts: list[str] = []
            if service_name:
                # Use service_name from extra_params; treat `database` as SID
                # only if it was meant to be one (we honor the explicit
                # service_name and ignore `database` here to avoid ambiguity).
                path = service_name
            else:
                # No explicit service_name → treat `database` as service_name
                # (Easy Connect default for oracle+oracledb).
                path = self.database
            base_url = (
                f"{dialect}://{self.username}:{password}"
                f"@{self.host}:{self.port}/{path}"
            )
            if self.ssl_mode:
                query_parts.append(f"sslmode={self.ssl_mode}")
            if query_parts:
                base_url += "?" + "&".join(query_parts)
            return base_url

        base_url = f"{dialect}://{self.username}:{password}@{self.host}:{self.port}/{self.database}"

        # Add SSL mode if specified
        if self.ssl_mode:
            base_url += f"?sslmode={self.ssl_mode}"

        return base_url
