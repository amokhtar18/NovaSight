"""
NovaSight Ingestion Domain — dlt Pipeline Schemas
===================================================

Pydantic schemas for dlt pipeline API validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
import re


# Allowed file formats for FILE-kind pipelines
FILE_FORMATS = ("csv", "tsv", "xlsx", "xls", "parquet", "json", "jsonl")

# Allowed object key prefix for tenant uploads
_RAW_UPLOADS_PREFIX = "raw_uploads/"
_OBJECT_KEY_RE = re.compile(r"^raw_uploads/[A-Za-z0-9._\-/]+$")


class ColumnConfig(BaseModel):
    """Column configuration for pipeline."""
    name: str = Field(..., min_length=1, max_length=255)
    data_type: str = Field(..., min_length=1, max_length=100)
    include: bool = Field(default=True)
    nullable: bool = Field(default=True)


class DltPipelineBase(BaseModel):
    """Base schema for dlt pipeline."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)

    # Source kind discriminator
    source_kind: Literal["sql", "file"] = Field(default="sql")

    # SQL-source fields
    connection_id: Optional[UUID] = None
    source_type: str = Field(default="table", pattern="^(table|query)$")
    source_schema: Optional[str] = Field(None, max_length=255)
    source_table: Optional[str] = Field(None, max_length=255)
    source_query: Optional[str] = Field(None, max_length=50000)

    # File-source fields
    file_format: Optional[str] = Field(None, max_length=16)
    file_object_key: Optional[str] = Field(None, max_length=1024)
    file_options: Dict[str, Any] = Field(default_factory=dict)

    # Column configuration
    columns_config: List[ColumnConfig] = Field(default_factory=list)

    # Key configuration
    primary_key_columns: List[str] = Field(default_factory=list)

    # Incremental configuration
    incremental_cursor_column: Optional[str] = Field(None, max_length=255)
    incremental_cursor_type: str = Field(default="none", pattern="^(none|timestamp|version)$")

    # Write configuration
    write_disposition: str = Field(default="append", pattern="^(append|replace|merge|scd2)$")

    # Partition configuration
    partition_columns: List[str] = Field(default_factory=list)

    # Target configuration
    iceberg_namespace: Optional[str] = Field(None, max_length=255)
    iceberg_table_name: Optional[str] = Field(None, max_length=255)

    # Additional options
    options: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate pipeline name is a valid identifier."""
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError(
                "Name must start with a letter and contain only letters, numbers, and underscores"
            )
        return v

    @field_validator("iceberg_table_name")
    @classmethod
    def validate_iceberg_table_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate Iceberg table name if provided."""
        if v is not None and not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(
                "Iceberg table name must be lowercase, start with a letter, "
                "and contain only letters, numbers, and underscores"
            )
        return v

    @model_validator(mode="after")
    def validate_source(self) -> "DltPipelineBase":
        """Cross-field validation for SQL- vs file-source pipelines."""
        if self.source_kind == "file":
            if self.connection_id is not None:
                raise ValueError("connection_id must be omitted for file-source pipelines")
            if not self.file_format:
                raise ValueError("file_format is required for file-source pipelines")
            if self.file_format not in FILE_FORMATS:
                raise ValueError(
                    f"file_format must be one of {FILE_FORMATS}"
                )
            if not self.file_object_key:
                raise ValueError("file_object_key is required for file-source pipelines")
            if not _OBJECT_KEY_RE.match(self.file_object_key):
                raise ValueError(
                    "file_object_key must start with 'raw_uploads/' and contain "
                    "only letters, digits, '.', '_', '-', or '/'"
                )
        else:  # sql
            if self.connection_id is None:
                raise ValueError("connection_id is required for SQL-source pipelines")
            if self.file_format or self.file_object_key:
                raise ValueError(
                    "file_format and file_object_key are only allowed for source_kind='file'"
                )
            if self.source_type == "table" and not self.source_table:
                raise ValueError("source_table is required when source_type is 'table'")
            if self.source_type == "query" and not self.source_query:
                raise ValueError("source_query is required when source_type is 'query'")
        return self

    @model_validator(mode="after")
    def validate_write_disposition(self) -> "DltPipelineBase":
        """Validate write disposition requirements."""
        if self.write_disposition in ("merge", "scd2"):
            if not self.primary_key_columns:
                raise ValueError(
                    f"primary_key_columns is required for write_disposition='{self.write_disposition}'"
                )
        return self


class DltPipelineCreate(DltPipelineBase):
    """Schema for creating a dlt pipeline."""
    pass


class DltPipelineUpdate(BaseModel):
    """Schema for updating a dlt pipeline."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    
    # Source configuration
    source_type: Optional[str] = Field(None, pattern="^(table|query)$")
    source_schema: Optional[str] = Field(None, max_length=255)
    source_table: Optional[str] = Field(None, max_length=255)
    source_query: Optional[str] = Field(None, max_length=50000)
    
    # Column configuration
    columns_config: Optional[List[ColumnConfig]] = None
    
    # Key configuration
    primary_key_columns: Optional[List[str]] = None
    
    # Incremental configuration
    incremental_cursor_column: Optional[str] = Field(None, max_length=255)
    incremental_cursor_type: Optional[str] = Field(None, pattern="^(none|timestamp|version)$")
    
    # Write configuration
    write_disposition: Optional[str] = Field(None, pattern="^(append|replace|merge|scd2)$")
    
    # Partition configuration
    partition_columns: Optional[List[str]] = None
    
    # Target configuration
    iceberg_namespace: Optional[str] = Field(None, max_length=255)
    iceberg_table_name: Optional[str] = Field(None, max_length=255)
    
    # Additional options
    options: Optional[Dict[str, Any]] = None


class DltPipelineResponse(BaseModel):
    """Response schema for dlt pipeline."""
    id: UUID
    tenant_id: UUID
    connection_id: Optional[UUID] = None
    name: str
    description: Optional[str]
    status: str

    # Source kind
    source_kind: str = "sql"

    # Source configuration
    source_type: str
    source_schema: Optional[str]
    source_table: Optional[str]
    source_query: Optional[str]

    # File-source
    file_format: Optional[str] = None
    file_object_key: Optional[str] = None
    file_options: Dict[str, Any] = Field(default_factory=dict)
    
    # Column configuration
    columns_config: List[Dict[str, Any]]
    
    # Key configuration
    primary_key_columns: List[str]
    
    # Incremental configuration
    incremental_cursor_column: Optional[str]
    incremental_cursor_type: str
    
    # Write configuration
    write_disposition: str
    
    # Partition configuration
    partition_columns: List[str]
    
    # Target configuration
    iceberg_namespace: Optional[str]
    iceberg_table_name: Optional[str]
    
    # Additional options
    options: Dict[str, Any]
    
    # Generated artifacts
    generated_at: Optional[datetime]
    template_name: Optional[str]
    template_version: Optional[str]
    
    # Execution stats
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    last_run_rows: Optional[int]
    last_run_duration_ms: Optional[int]
    last_run_iceberg_snapshot_id: Optional[str]
    
    # Audit
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DltPipelineListResponse(BaseModel):
    """Paginated list response for dlt pipelines."""
    items: List[DltPipelineResponse]
    total: int
    page: int
    per_page: int
    pages: int


class DltPipelinePreviewRequest(BaseModel):
    """Request schema for previewing generated code."""
    source_kind: Literal["sql", "file"] = Field(default="sql")

    # SQL-source fields
    connection_id: Optional[UUID] = None
    source_type: str = Field(default="table", pattern="^(table|query)$")
    source_schema: Optional[str] = Field(None, max_length=255)
    source_table: Optional[str] = Field(None, max_length=255)
    source_query: Optional[str] = Field(None, max_length=50000)

    # File-source fields
    file_format: Optional[str] = Field(None, max_length=16)
    file_object_key: Optional[str] = Field(None, max_length=1024)
    file_options: Dict[str, Any] = Field(default_factory=dict)

    # Column configuration
    columns_config: List[ColumnConfig] = Field(default_factory=list)

    # Key configuration
    primary_key_columns: List[str] = Field(default_factory=list)

    # Incremental configuration
    incremental_cursor_column: Optional[str] = Field(None, max_length=255)
    incremental_cursor_type: str = Field(default="none", pattern="^(none|timestamp|version)$")

    # Write configuration
    write_disposition: str = Field(default="append", pattern="^(append|replace|merge|scd2)$")

    # Partition configuration
    partition_columns: List[str] = Field(default_factory=list)

    # Target configuration
    iceberg_table_name: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def validate_source(self) -> "DltPipelinePreviewRequest":
        if self.source_kind == "file":
            if not self.file_format or self.file_format not in FILE_FORMATS:
                raise ValueError(f"file_format must be one of {FILE_FORMATS}")
            if not self.file_object_key or not _OBJECT_KEY_RE.match(self.file_object_key):
                raise ValueError("file_object_key must start with 'raw_uploads/'")
        else:
            if self.connection_id is None:
                raise ValueError("connection_id is required for SQL-source pipelines")
            if self.source_type == "table" and not self.source_table:
                raise ValueError("source_table is required when source_type is 'table'")
            if self.source_type == "query" and not self.source_query:
                raise ValueError("source_query is required when source_type is 'query'")
        return self


class DltPipelinePreviewResponse(BaseModel):
    """Response schema for code preview."""
    code: str
    template_name: str
    template_version: str
    validation_errors: List[str] = Field(default_factory=list)


class DltPipelineRunResponse(BaseModel):
    """Response schema for pipeline run trigger."""
    pipeline_id: UUID
    run_id: Optional[str]
    status: str
    message: str
