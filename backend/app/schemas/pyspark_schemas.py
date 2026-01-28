"""
NovaSight PySpark App Schemas
=============================

Pydantic validation schemas for PySpark app CRUD operations.
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, validator
from enum import Enum


class SourceTypeEnum(str, Enum):
    """Source type enumeration."""
    TABLE = "table"
    QUERY = "query"


class WriteModeEnum(str, Enum):
    """Write mode enumeration."""
    APPEND = "append"
    OVERWRITE = "overwrite"
    MERGE = "merge"


class SCDTypeEnum(str, Enum):
    """SCD type enumeration."""
    NONE = "none"
    TYPE1 = "type1"
    TYPE2 = "type2"


class CDCTypeEnum(str, Enum):
    """CDC type enumeration."""
    NONE = "none"
    TIMESTAMP = "timestamp"
    VERSION = "version"
    HASH = "hash"


class PySparkAppStatusEnum(str, Enum):
    """PySpark app status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class ColumnConfigSchema(BaseModel):
    """Schema for column configuration."""
    name: str = Field(..., min_length=1, max_length=255)
    data_type: str = Field(..., min_length=1, max_length=100)
    include: bool = Field(default=True)
    nullable: bool = Field(default=True)
    comment: Optional[str] = None
    
    class Config:
        extra = "allow"


class PySparkAppCreateSchema(BaseModel):
    """Schema for creating a PySpark app."""
    
    # Required fields
    name: str = Field(..., min_length=1, max_length=255)
    connection_id: str = Field(..., description="UUID of the source connection")
    
    # Optional identity
    description: Optional[str] = Field(None, max_length=2000)
    
    # Source configuration
    source_type: SourceTypeEnum = Field(default=SourceTypeEnum.TABLE)
    source_schema: Optional[str] = Field(None, max_length=255)
    source_table: Optional[str] = Field(None, max_length=255)
    source_query: Optional[str] = Field(None, max_length=50000)
    
    # Column configuration
    columns_config: List[ColumnConfigSchema] = Field(default_factory=list)
    
    # Key configuration
    primary_key_columns: List[str] = Field(default_factory=list)
    
    # CDC configuration
    cdc_type: CDCTypeEnum = Field(default=CDCTypeEnum.NONE)
    cdc_column: Optional[str] = Field(None, max_length=255)
    
    # Partition configuration
    partition_columns: List[str] = Field(default_factory=list)
    
    # SCD configuration
    scd_type: SCDTypeEnum = Field(default=SCDTypeEnum.NONE)
    
    # Write mode
    write_mode: WriteModeEnum = Field(default=WriteModeEnum.APPEND)
    
    # Target configuration
    target_database: Optional[str] = Field(None, max_length=255)
    target_table: Optional[str] = Field(None, max_length=255)
    target_engine: str = Field(default="MergeTree", max_length=100)
    
    # Additional options
    options: Dict[str, Any] = Field(default_factory=dict)
    
    @validator("source_table")
    def validate_source_table(cls, v, values):
        """Validate source table is provided for table source type."""
        if values.get("source_type") == SourceTypeEnum.TABLE and not v:
            # Will be validated at service layer
            pass
        return v
    
    @validator("source_query")
    def validate_source_query(cls, v, values):
        """Validate source query is provided for query source type."""
        if values.get("source_type") == SourceTypeEnum.QUERY and not v:
            # Will be validated at service layer
            pass
        return v
    
    @validator("primary_key_columns")
    def validate_primary_keys(cls, v, values):
        """Validate PK columns exist in columns_config."""
        columns_config = values.get("columns_config", [])
        column_names = {col.name for col in columns_config}
        
        for pk in v:
            if columns_config and pk not in column_names:
                raise ValueError(f"Primary key column '{pk}' not in selected columns")
        return v
    
    @validator("cdc_column")
    def validate_cdc_column(cls, v, values):
        """Validate CDC column is provided when CDC type is set."""
        if values.get("cdc_type") != CDCTypeEnum.NONE and not v:
            raise ValueError("CDC column is required when CDC type is specified")
        return v
    
    class Config:
        extra = "forbid"


class PySparkAppUpdateSchema(BaseModel):
    """Schema for updating a PySpark app."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[PySparkAppStatusEnum] = None
    
    # Source configuration
    source_type: Optional[SourceTypeEnum] = None
    source_schema: Optional[str] = Field(None, max_length=255)
    source_table: Optional[str] = Field(None, max_length=255)
    source_query: Optional[str] = Field(None, max_length=50000)
    
    # Column configuration
    columns_config: Optional[List[ColumnConfigSchema]] = None
    
    # Key configuration
    primary_key_columns: Optional[List[str]] = None
    
    # CDC configuration
    cdc_type: Optional[CDCTypeEnum] = None
    cdc_column: Optional[str] = Field(None, max_length=255)
    
    # Partition configuration
    partition_columns: Optional[List[str]] = None
    
    # SCD configuration
    scd_type: Optional[SCDTypeEnum] = None
    
    # Write mode
    write_mode: Optional[WriteModeEnum] = None
    
    # Target configuration
    target_database: Optional[str] = Field(None, max_length=255)
    target_table: Optional[str] = Field(None, max_length=255)
    target_engine: Optional[str] = Field(None, max_length=100)
    
    # Additional options
    options: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = "forbid"


class PySparkAppResponseSchema(BaseModel):
    """Schema for PySpark app response."""
    
    id: str
    tenant_id: str
    connection_id: str
    name: str
    description: Optional[str]
    status: str
    
    source_type: str
    source_schema: Optional[str]
    source_table: Optional[str]
    source_query: Optional[str]
    
    columns_config: List[Dict[str, Any]]
    primary_key_columns: List[str]
    
    cdc_type: str
    cdc_column: Optional[str]
    
    partition_columns: List[str]
    scd_type: str
    write_mode: str
    
    target_database: Optional[str]
    target_table: Optional[str]
    target_engine: str
    
    options: Dict[str, Any]
    
    generated_at: Optional[str]
    template_version: Optional[str]
    
    last_run_at: Optional[str]
    last_run_status: Optional[str]
    last_run_rows: Optional[int]
    last_run_duration_ms: Optional[int]
    
    created_by: str
    created_at: str
    updated_at: str
    
    class Config:
        orm_mode = True


class PySparkAppWithCodeSchema(PySparkAppResponseSchema):
    """Schema for PySpark app response with generated code."""
    
    generated_code: Optional[str]
    generated_code_hash: Optional[str]


class PySparkAppListQuerySchema(BaseModel):
    """Schema for list query parameters."""
    
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)
    status: Optional[PySparkAppStatusEnum] = None
    connection_id: Optional[str] = None
    search: Optional[str] = None


class PySparkAppListResponseSchema(BaseModel):
    """Schema for paginated list response."""
    
    apps: List[PySparkAppResponseSchema]
    pagination: Dict[str, Any]


class PySparkCodePreviewSchema(BaseModel):
    """Schema for code preview request (without saving)."""
    
    connection_id: str
    source_type: SourceTypeEnum
    source_schema: Optional[str] = None
    source_table: Optional[str] = None
    source_query: Optional[str] = None
    
    columns_config: List[ColumnConfigSchema]
    primary_key_columns: List[str] = Field(default_factory=list)
    
    cdc_type: CDCTypeEnum = Field(default=CDCTypeEnum.NONE)
    cdc_column: Optional[str] = None
    
    partition_columns: List[str] = Field(default_factory=list)
    scd_type: SCDTypeEnum = Field(default=SCDTypeEnum.NONE)
    write_mode: WriteModeEnum = Field(default=WriteModeEnum.APPEND)
    
    target_database: str
    target_table: str
    target_engine: str = Field(default="MergeTree")
    
    options: Dict[str, Any] = Field(default_factory=dict)


class PySparkCodeResponseSchema(BaseModel):
    """Schema for generated code response."""
    
    code: str
    template_name: str
    template_version: str
    parameters_hash: str
    warnings: List[str] = Field(default_factory=list)


class QueryValidationRequestSchema(BaseModel):
    """Schema for SQL query validation request."""
    
    query: str = Field(..., min_length=1, max_length=50000)


class QueryValidationResponseSchema(BaseModel):
    """Schema for SQL query validation response."""
    
    valid: bool
    message: str
    columns: Optional[List[Dict[str, Any]]] = None
    estimated_rows: Optional[int] = None
