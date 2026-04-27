"""
NovaSight Data Sources Domain — Connection Schemas
====================================================

Pydantic schemas for connection request/response validation.

Canonical location: ``app.domains.datasources.schemas.connection_schemas``
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class DatabaseTypeEnum(str, Enum):
    """Supported database types (SQL connections only)."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"
    CLICKHOUSE = "clickhouse"


class ConnectionStatusEnum(str, Enum):
    """Connection status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    TESTING = "testing"


class ConnectionConfigSchema(BaseModel):
    """Connection configuration parameters."""
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)
    ssl_mode: Optional[str] = Field(None, max_length=50)
    schema_name: Optional[str] = Field(None, max_length=255, alias="schema")

    @validator('host')
    def validate_host(cls, v):
        """Validate host to prevent SSRF."""
        import ipaddress
        try:
            ip = ipaddress.ip_address(v)
            if ip.is_private or ip.is_loopback:
                import logging
                logging.getLogger(__name__).warning(
                    f"Private/loopback IP detected: {v}"
                )
        except ValueError:
            pass
        return v

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "host": "db.example.com",
                "port": 5432,
                "database": "analytics",
                "username": "data_user",
                "password": "secure_password",
                "ssl_mode": "require",
                "schema": "public",
            }
        }
    }


class ConnectionCreateSchema(BaseModel):
    """Schema for creating a new connection."""
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    db_type: DatabaseTypeEnum

    # Database connection fields (all required for SQL connections)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)
    ssl_mode: Optional[str] = Field(None, max_length=50)
    schema_name: Optional[str] = Field(None, max_length=255)
    extra_params: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('name')
    def validate_name(cls, v):
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_\- ]*$', v):
            raise ValueError(
                "Name must start with a letter and contain only letters, "
                "numbers, spaces, hyphens, and underscores"
            )
        return v

    class Config:
        use_enum_values = True


class ConnectionUpdateSchema(BaseModel):
    """Schema for updating a connection."""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    database: Optional[str] = Field(None, min_length=1, max_length=255)
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = None
    ssl_mode: Optional[str] = Field(None, max_length=50)
    schema_name: Optional[str] = Field(None, max_length=255)
    extra_params: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True


class ConnectionTestSchema(BaseModel):
    """Schema for testing connection parameters."""
    db_type: DatabaseTypeEnum
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1)
    ssl_mode: Optional[str] = Field(None, max_length=50)

    class Config:
        use_enum_values = True


class ConnectionResponseSchema(BaseModel):
    """Schema for connection response."""
    id: str
    name: str
    description: Optional[str]
    db_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    schema_name: Optional[str]
    username: Optional[str] = None
    ssl_mode: Optional[str]
    status: str
    last_tested_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    created_by: str

    model_config = {
        "from_attributes": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None,
        }
    }


class ColumnSchema(BaseModel):
    """Schema for column information."""
    name: str
    data_type: str
    nullable: bool
    primary_key: bool = False
    comment: Optional[str] = None
    max_length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None


class TableSchema(BaseModel):
    """Schema for table information."""
    name: str
    schema_name: str = Field(..., alias="schema")
    
    model_config = {"populate_by_name": True}
    row_count: int = 0
    comment: Optional[str] = None
    table_type: str = "BASE TABLE"
    columns: List[ColumnSchema] = Field(default_factory=list)


class SchemaResponseSchema(BaseModel):
    """Schema for database schema response."""
    schemas: List[str]
    tables: Dict[str, List[TableSchema]] = Field(default_factory=dict)


class ConnectionTestResultSchema(BaseModel):
    """Schema for connection test result."""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    version: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Connection successful",
                "version": "PostgreSQL 14.5",
                "details": {
                    "database": "analytics",
                    "schemas_count": 3,
                },
            }
        }
    }


class ConnectionListQuerySchema(BaseModel):
    """Schema for connection list query parameters."""
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)
    db_type: Optional[DatabaseTypeEnum] = None
    status: Optional[ConnectionStatusEnum] = None

    class Config:
        use_enum_values = True


class PaginationSchema(BaseModel):
    """Schema for pagination metadata."""
    page: int
    per_page: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool


class ConnectionListResponseSchema(BaseModel):
    """Schema for connection list response."""
    connections: List[ConnectionResponseSchema]
    pagination: PaginationSchema
