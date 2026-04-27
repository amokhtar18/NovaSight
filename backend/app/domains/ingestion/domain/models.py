"""
NovaSight DltPipeline Model
============================

dlt pipeline configuration model for data extraction and loading.
Replaces the PySparkApp model with dlt-based ingestion to Iceberg.
"""

import uuid
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.extensions import db
import enum


class SourceType(enum.Enum):
    """Source type for dlt extraction (SQL connections)."""
    TABLE = "table"
    QUERY = "query"


class DltSourceKind(enum.Enum):
    """Source kind discriminator for dlt pipelines.

    - SQL:  pipeline reads from a registered DataConnection (sql_database).
    - FILE: pipeline reads an uploaded file from the tenant's S3 bucket
            under the ``raw_uploads/`` prefix.
    """
    SQL = "sql"
    FILE = "file"


class FileFormat(enum.Enum):
    """Supported file formats for FILE-kind dlt pipelines."""
    CSV = "csv"
    TSV = "tsv"
    XLSX = "xlsx"
    XLS = "xls"
    PARQUET = "parquet"
    JSON = "json"
    JSONL = "jsonl"


class WriteDisposition(enum.Enum):
    """Write disposition for dlt pipeline.
    
    Maps to dlt's write_disposition parameter:
    - APPEND: Insert new rows
    - REPLACE: Drop and recreate table
    - MERGE: Upsert based on primary key
    - SCD2: Slowly Changing Dimension Type 2 (history tracking)
    """
    APPEND = "append"
    REPLACE = "replace"
    MERGE = "merge"
    SCD2 = "scd2"


class IncrementalCursorType(enum.Enum):
    """Type of incremental cursor column."""
    NONE = "none"
    TIMESTAMP = "timestamp"
    VERSION = "version"


class DltPipelineStatus(enum.Enum):
    """dlt pipeline configuration status."""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class DltPipeline(db.Model):
    """
    dlt pipeline configuration model.
    
    Stores configuration for generating dlt pipelines that extract data
    from source connections and load into Iceberg tables in the tenant's
    S3 bucket. All generated code comes from pre-approved Jinja2 templates.
    """
    
    __tablename__ = "dlt_pipelines"
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Tenant association
    tenant_id = db.Column(
        UUID(as_uuid=True), 
        ForeignKey("tenants.id"), 
        nullable=False, 
        index=True
    )
    
    # Source connection (NULL when source_kind == 'file')
    connection_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey("data_connections.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )

    # Source kind discriminator: 'sql' (default) or 'file'
    source_kind = db.Column(
        String(16),
        default=DltSourceKind.SQL.value,
        nullable=False,
        index=True,
    )

    # File-source fields (only used when source_kind == 'file')
    file_format = db.Column(String(16), nullable=True)
    file_object_key = db.Column(String(1024), nullable=True)
    file_options = db.Column(JSONB, default=dict, nullable=False)
    
    # Identity
    name = db.Column(String(255), nullable=False)
    description = db.Column(Text, nullable=True)
    
    # Status
    status = db.Column(
        SQLEnum(DltPipelineStatus, values_callable=lambda e: [m.value for m in e]),
        default=DltPipelineStatus.DRAFT,
        nullable=False
    )
    
    # Source Configuration
    source_type = db.Column(
        SQLEnum(SourceType, values_callable=lambda e: [m.value for m in e]),
        default=SourceType.TABLE,
        nullable=False
    )
    source_schema = db.Column(String(255), nullable=True)
    source_table = db.Column(String(255), nullable=True)
    source_query = db.Column(Text, nullable=True)
    
    # Column Configuration
    # Format: [{"name": "col1", "data_type": "VARCHAR", "include": true}, ...]
    columns_config = db.Column(JSONB, default=list, nullable=False)
    
    # Primary Key Configuration (required for MERGE and SCD2)
    # Format: ["col1", "col2"]
    primary_key_columns = db.Column(JSONB, default=list, nullable=False)
    
    # Incremental Loading Configuration
    incremental_cursor_column = db.Column(String(255), nullable=True)
    incremental_cursor_type = db.Column(
        SQLEnum(IncrementalCursorType, values_callable=lambda e: [m.value for m in e]),
        default=IncrementalCursorType.NONE,
        nullable=False
    )
    
    # Write Disposition
    write_disposition = db.Column(
        SQLEnum(WriteDisposition, values_callable=lambda e: [m.value for m in e]),
        default=WriteDisposition.APPEND,
        nullable=False
    )
    
    # Partition Configuration
    # Format: ["year", "month"] or ["region"]
    partition_columns = db.Column(JSONB, default=list, nullable=False)
    
    # Iceberg Target Configuration
    iceberg_namespace = db.Column(String(255), nullable=True)
    iceberg_table_name = db.Column(String(255), nullable=True)
    
    # Additional Options
    # Format: {"batch_size": 10000, "parallelism": 4, ...}
    options = db.Column(JSONB, default=dict, nullable=False)
    
    # Generated Artifacts
    generated_code = db.Column(Text, nullable=True)
    generated_code_hash = db.Column(String(64), nullable=True)  # SHA-256 hash
    generated_at = db.Column(DateTime, nullable=True)
    template_name = db.Column(String(100), nullable=True)
    template_version = db.Column(String(50), nullable=True)
    
    # Execution Stats
    last_run_at = db.Column(DateTime, nullable=True)
    last_run_status = db.Column(String(50), nullable=True)
    last_run_rows = db.Column(Integer, nullable=True)
    last_run_duration_ms = db.Column(Integer, nullable=True)
    last_run_iceberg_snapshot_id = db.Column(String(64), nullable=True)
    
    # Audit
    created_by = db.Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = db.Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Unique name within tenant
    __table_args__ = (
        db.UniqueConstraint("tenant_id", "name", name="uq_tenant_dlt_pipeline_name"),
    )
    
    # Relationships
    tenant = relationship("Tenant", backref="dlt_pipelines")
    connection = relationship(
        "DataConnection",
        backref=db.backref(
            "dlt_pipelines",
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
    )
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<DltPipeline {self.name} ({self.id})>"
    
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
            "connection_id": str(self.connection_id) if self.connection_id else None,
            "name": self.name,
            "description": self.description,
            "status": self.status.value if self.status else None,
            "source_kind": self.source_kind or DltSourceKind.SQL.value,
            "source_type": self.source_type.value if self.source_type else None,
            "source_schema": self.source_schema,
            "source_table": self.source_table,
            "source_query": self.source_query,
            "file_format": self.file_format,
            "file_object_key": self.file_object_key,
            "file_options": self.file_options or {},
            "columns_config": self.columns_config or [],
            "primary_key_columns": self.primary_key_columns or [],
            "incremental_cursor_column": self.incremental_cursor_column,
            "incremental_cursor_type": self.incremental_cursor_type.value if self.incremental_cursor_type else None,
            "write_disposition": self.write_disposition.value if self.write_disposition else None,
            "partition_columns": self.partition_columns or [],
            "iceberg_namespace": self.iceberg_namespace,
            "iceberg_table_name": self.iceberg_table_name,
            "options": self.options or {},
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "template_name": self.template_name,
            "template_version": self.template_version,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_status": self.last_run_status,
            "last_run_rows": self.last_run_rows,
            "last_run_duration_ms": self.last_run_duration_ms,
            "last_run_iceberg_snapshot_id": self.last_run_iceberg_snapshot_id,
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
    
    def compute_code_hash(self) -> str:
        """Compute SHA-256 hash of the generated code."""
        if not self.generated_code:
            return ""
        return hashlib.sha256(self.generated_code.encode()).hexdigest()
    
    def get_template_name(self) -> str:
        """Determine the template name based on source kind and write disposition.

        File-source pipelines (csv/xlsx/parquet/json) always use the file template;
        the write disposition is honoured inside the template itself.
        """
        if (self.source_kind or DltSourceKind.SQL.value) == DltSourceKind.FILE.value:
            return "dlt/file_pipeline.py.j2"

        disposition = self.write_disposition
        if disposition == WriteDisposition.SCD2:
            return "dlt/scd2_pipeline.py.j2"
        elif disposition == WriteDisposition.MERGE:
            return "dlt/merge_pipeline.py.j2"
        else:
            return "dlt/extract_pipeline.py.j2"
    
    def validate_config(self) -> List[str]:
        """
        Validate configuration for completeness.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        kind = self.source_kind or DltSourceKind.SQL.value

        if kind == DltSourceKind.FILE.value:
            # File-source validation
            if self.connection_id is not None:
                errors.append("connection_id must be empty for file-source pipelines")
            if not self.file_format:
                errors.append("file_format is required for file-source pipelines")
            elif self.file_format not in {f.value for f in FileFormat}:
                errors.append(
                    f"file_format must be one of {sorted({f.value for f in FileFormat})}"
                )
            if not self.file_object_key:
                errors.append("file_object_key is required for file-source pipelines")
            elif not str(self.file_object_key).startswith("raw_uploads/"):
                errors.append("file_object_key must live under 'raw_uploads/'")
        else:
            # SQL-source validation
            if self.connection_id is None:
                errors.append("connection_id is required for SQL-source pipelines")
            if self.source_type == SourceType.TABLE:
                if not self.source_table:
                    errors.append("Source table is required when source_type is 'table'")
            elif self.source_type == SourceType.QUERY:
                if not self.source_query:
                    errors.append("Source query is required when source_type is 'query'")

        # Column validation (applies to both kinds; for file-source, columns are
        # the projected output columns).
        if not self.columns_config or len(self.get_selected_columns()) == 0:
            errors.append("At least one column must be selected")
        
        # Primary key validation for MERGE and SCD2
        if self.write_disposition in (WriteDisposition.MERGE, WriteDisposition.SCD2):
            if not self.primary_key_columns:
                errors.append(
                    "Primary key columns are required for merge or scd2 write disposition"
                )
        
        # Incremental cursor validation
        if self.incremental_cursor_type != IncrementalCursorType.NONE:
            if not self.incremental_cursor_column:
                errors.append(
                    "Incremental cursor column is required when incremental type is specified"
                )
        
        return errors
