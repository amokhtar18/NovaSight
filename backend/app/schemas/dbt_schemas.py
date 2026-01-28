"""
Pydantic schemas for dbt operations.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum


class Materialization(str, Enum):
    """dbt materialization types."""
    VIEW = "view"
    TABLE = "table"
    INCREMENTAL = "incremental"
    EPHEMERAL = "ephemeral"


class JoinType(str, Enum):
    """SQL join types."""
    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    FULL = "full"


class TestType(str, Enum):
    """dbt test types."""
    UNIQUE = "unique"
    NOT_NULL = "not_null"
    ACCEPTED_VALUES = "accepted_values"
    RELATIONSHIPS = "relationships"


# ============ Request Schemas ============

class DbtRunRequest(BaseModel):
    """Request to run dbt models."""
    select: Optional[str] = Field(
        None,
        description="Model selection criteria (e.g., 'staging.customers+')",
        examples=["staging.customers", "marts.*", "+orders"]
    )
    exclude: Optional[str] = Field(
        None,
        description="Models to exclude"
    )
    full_refresh: bool = Field(
        False,
        description="Force full refresh of incremental models"
    )
    vars: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional dbt variables"
    )
    target: Optional[str] = Field(
        None,
        description="Target environment (dev, prod)"
    )


class DbtTestRequest(BaseModel):
    """Request to run dbt tests."""
    select: Optional[str] = Field(
        None,
        description="Test selection criteria"
    )
    exclude: Optional[str] = Field(
        None,
        description="Tests to exclude"
    )
    store_failures: bool = Field(
        False,
        description="Store test failures in database"
    )


class DbtBuildRequest(BaseModel):
    """Request to run dbt build."""
    select: Optional[str] = Field(
        None,
        description="Selection criteria"
    )
    exclude: Optional[str] = Field(
        None,
        description="Items to exclude"
    )
    full_refresh: bool = Field(
        False,
        description="Force full refresh"
    )


class DbtCompileRequest(BaseModel):
    """Request to compile dbt models."""
    select: Optional[str] = Field(
        None,
        description="Model selection criteria"
    )


class DbtSeedRequest(BaseModel):
    """Request to load dbt seeds."""
    select: Optional[str] = Field(
        None,
        description="Seed selection criteria"
    )
    full_refresh: bool = Field(
        False,
        description="Drop and recreate seeds"
    )


class DbtSnapshotRequest(BaseModel):
    """Request to run dbt snapshots."""
    select: Optional[str] = Field(
        None,
        description="Snapshot selection criteria"
    )


class DbtListRequest(BaseModel):
    """Request to list dbt resources."""
    select: Optional[str] = Field(
        None,
        description="Selection criteria"
    )
    resource_type: str = Field(
        "model",
        description="Type of resource (model, test, source, etc.)"
    )


# ============ Response Schemas ============

class DbtResultResponse(BaseModel):
    """Response from dbt command execution."""
    success: bool
    command: str
    stdout: str
    stderr: str
    return_code: int
    run_results: Optional[Dict[str, Any]] = None
    manifest: Optional[Dict[str, Any]] = None


class DbtLineageNode(BaseModel):
    """Node in lineage graph."""
    name: str
    resource_type: str
    unique_id: str


class DbtLineageResponse(BaseModel):
    """Response with model lineage."""
    model: str
    unique_id: str
    upstream: List[DbtLineageNode]
    downstream: List[DbtLineageNode]
    columns: Dict[str, Any]
    description: str


class DbtDebugResponse(BaseModel):
    """Response from dbt debug."""
    success: bool
    connection_ok: bool
    deps_ok: bool
    config_ok: bool
    details: str


# ============ Model Definition Schemas ============

class ColumnDefinition(BaseModel):
    """Column definition for dbt model."""
    name: str = Field(..., description="Column name")
    description: Optional[str] = Field(None, description="Column description")
    data_type: Optional[str] = Field(None, description="Data type")
    tests: Optional[List[TestType]] = Field(None, description="Tests to apply")


class JoinDefinition(BaseModel):
    """Join definition between tables."""
    left_table: str = Field(..., description="Left table name")
    right_table: str = Field(..., description="Right table name")
    join_type: JoinType = Field(JoinType.LEFT, description="Type of join")
    left_key: str = Field(..., description="Left join key column")
    right_key: str = Field(..., description="Right join key column")


class ModelDefinition(BaseModel):
    """Definition for a dbt model."""
    name: str = Field(..., min_length=1, max_length=100, description="Model name")
    description: Optional[str] = Field(None, description="Model description")
    materialization: Materialization = Field(
        Materialization.VIEW,
        description="How to materialize the model"
    )
    schema_name: Optional[str] = Field(
        None,
        description="Custom schema name"
    )
    source_tables: List[str] = Field(
        ...,
        min_length=1,
        description="Source tables"
    )
    columns: List[ColumnDefinition] = Field(
        ...,
        min_length=1,
        description="Column definitions"
    )
    joins: Optional[List[JoinDefinition]] = Field(
        None,
        description="Join definitions"
    )
    where_clause: Optional[str] = Field(
        None,
        description="WHERE clause filter"
    )
    group_by: Optional[List[str]] = Field(
        None,
        description="GROUP BY columns"
    )
    tags: Optional[List[str]] = Field(
        None,
        description="Model tags"
    )


class ModelCreateRequest(BaseModel):
    """Request to create a dbt model."""
    definition: ModelDefinition
    layer: Literal["staging", "intermediate", "marts"] = Field(
        ...,
        description="Model layer"
    )


class ModelCreateResponse(BaseModel):
    """Response from model creation."""
    success: bool
    model_name: str
    file_path: str
    sql_content: str
    schema_content: Optional[str] = None
