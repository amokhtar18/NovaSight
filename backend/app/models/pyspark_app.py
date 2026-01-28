"""
NovaSight PySpark App Model
===========================

PySpark application configuration model for data extraction and transformation.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.extensions import db
import enum


class SourceType(enum.Enum):
    """Source type for PySpark extraction."""
    TABLE = "table"
    QUERY = "query"


class WriteMode(enum.Enum):
    """Write mode for target data."""
    APPEND = "append"
    OVERWRITE = "overwrite"
    MERGE = "merge"


class SCDType(enum.Enum):
    """Slowly Changing Dimension type."""
    NONE = "none"
    TYPE1 = "type1"  # Overwrite existing records
    TYPE2 = "type2"  # Historical tracking with validity dates


class CDCType(enum.Enum):
    """Change Data Capture detection type."""
    NONE = "none"
    TIMESTAMP = "timestamp"  # Use timestamp column
    VERSION = "version"      # Use version number column
    HASH = "hash"           # Compare hash of row data


class PySparkAppStatus(enum.Enum):
    """PySpark app configuration status."""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class PySparkApp(db.Model):
    """
    PySpark application configuration model.
    
    Stores configuration for generating PySpark jobs that extract data
    from source connections and load into target (ClickHouse).
    All generated code comes from pre-approved Jinja2 templates.
    """
    
    __tablename__ = "pyspark_apps"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tenant association
    tenant_id = db.Column(
        UUID(as_uuid=True), 
        ForeignKey("tenants.id"), 
        nullable=False, 
        index=True
    )
    
    # Source connection
    connection_id = db.Column(
        UUID(as_uuid=True), 
        ForeignKey("data_connections.id"), 
        nullable=False,
        index=True
    )
    
    # Identity
    name = db.Column(String(255), nullable=False)
    description = db.Column(Text, nullable=True)
    
    # Status
    status = db.Column(
        SQLEnum(PySparkAppStatus),
        default=PySparkAppStatus.DRAFT,
        nullable=False
    )
    
    # Source Configuration
    source_type = db.Column(
        SQLEnum(SourceType),
        default=SourceType.TABLE,
        nullable=False
    )
    source_schema = db.Column(String(255), nullable=True)  # Source schema name
    source_table = db.Column(String(255), nullable=True)   # Source table name
    source_query = db.Column(Text, nullable=True)          # Custom SQL query
    
    # Column Configuration
    # Format: [{"name": "col1", "data_type": "VARCHAR", "include": true}, ...]
    columns_config = db.Column(JSONB, default=list, nullable=False)
    
    # Primary Key Configuration
    # Format: ["col1", "col2"]
    primary_key_columns = db.Column(JSONB, default=list, nullable=False)
    
    # CDC Configuration
    cdc_type = db.Column(
        SQLEnum(CDCType),
        default=CDCType.NONE,
        nullable=False
    )
    cdc_column = db.Column(String(255), nullable=True)  # Column for CDC tracking
    cdc_high_watermark = db.Column(Text, nullable=True)  # Last processed value
    
    # Partition Configuration
    # Format: ["year", "month"] or ["region"]
    partition_columns = db.Column(JSONB, default=list, nullable=False)
    
    # SCD Configuration
    scd_type = db.Column(
        SQLEnum(SCDType),
        default=SCDType.NONE,
        nullable=False
    )
    
    # Write Mode
    write_mode = db.Column(
        SQLEnum(WriteMode),
        default=WriteMode.APPEND,
        nullable=False
    )
    
    # Target Configuration (ClickHouse)
    target_database = db.Column(String(255), nullable=True)
    target_table = db.Column(String(255), nullable=True)
    target_engine = db.Column(String(100), default="MergeTree", nullable=False)
    
    # Additional Options
    # Format: {"batch_size": 10000, "timeout": 300, ...}
    options = db.Column(JSONB, default=dict, nullable=False)
    
    # Generated Artifacts
    generated_code = db.Column(Text, nullable=True)
    generated_code_hash = db.Column(String(64), nullable=True)  # SHA-256 hash
    generated_at = db.Column(DateTime, nullable=True)
    template_version = db.Column(String(50), nullable=True)
    
    # Execution Stats
    last_run_at = db.Column(DateTime, nullable=True)
    last_run_status = db.Column(String(50), nullable=True)
    last_run_rows = db.Column(Integer, nullable=True)
    last_run_duration_ms = db.Column(Integer, nullable=True)
    
    # Audit
    created_by = db.Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Unique name within tenant
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "name", name="uq_tenant_pyspark_app_name"),
    )
    
    # Relationships
    tenant = relationship("Tenant", backref="pyspark_apps")
    connection = relationship("DataConnection", backref="pyspark_apps")
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<PySparkApp {self.name} ({self.id})>"
    
    def to_dict(self, include_code: bool = False) -> Dict[str, Any]:
        """
        Convert model to dictionary.
        
        Args:
            include_code: Include generated code in output
            
        Returns:
            Dictionary representation
        """
        result = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "connection_id": str(self.connection_id),
            "name": self.name,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "source_type": self.source_type.value if self.source_type else None,
            "source_schema": self.source_schema,
            "source_table": self.source_table,
            "source_query": self.source_query,
            "columns_config": self.columns_config or [],
            "primary_key_columns": self.primary_key_columns or [],
            "cdc_type": self.cdc_type.value if self.cdc_type else None,
            "cdc_column": self.cdc_column,
            "partition_columns": self.partition_columns or [],
            "scd_type": self.scd_type.value if self.scd_type else None,
            "write_mode": self.write_mode.value if self.write_mode else None,
            "target_database": self.target_database,
            "target_table": self.target_table,
            "target_engine": self.target_engine,
            "options": self.options or {},
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "template_version": self.template_version,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_status": self.last_run_status,
            "last_run_rows": self.last_run_rows,
            "last_run_duration_ms": self.last_run_duration_ms,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_code:
            result["generated_code"] = self.generated_code
            result["generated_code_hash"] = self.generated_code_hash
        
        return result
    
    def get_selected_columns(self) -> List[Dict[str, Any]]:
        """Get list of selected columns."""
        return [
            col for col in (self.columns_config or [])
            if col.get("include", True)
        ]
    
    def get_column_names(self) -> List[str]:
        """Get list of selected column names."""
        return [col["name"] for col in self.get_selected_columns()]
    
    def validate_config(self) -> List[str]:
        """
        Validate configuration for completeness.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Source validation
        if self.source_type == SourceType.TABLE:
            if not self.source_table:
                errors.append("Source table is required when source_type is 'table'")
        elif self.source_type == SourceType.QUERY:
            if not self.source_query:
                errors.append("Source query is required when source_type is 'query'")
        
        # Column validation
        if not self.columns_config or len(self.get_selected_columns()) == 0:
            errors.append("At least one column must be selected")
        
        # Primary key validation for SCD Type 2 and Merge
        if self.scd_type == SCDType.TYPE2 or self.write_mode == WriteMode.MERGE:
            if not self.primary_key_columns:
                errors.append("Primary key columns are required for SCD Type 2 or Merge write mode")
        
        # CDC validation
        if self.cdc_type != CDCType.NONE and not self.cdc_column:
            errors.append("CDC column is required when CDC type is specified")
        
        # SCD Type 2 requires CDC
        if self.scd_type == SCDType.TYPE2 and self.cdc_type == CDCType.NONE:
            errors.append("CDC configuration is recommended for SCD Type 2")
        
        # Target validation
        if not self.target_database or not self.target_table:
            errors.append("Target database and table are required")
        
        return errors
