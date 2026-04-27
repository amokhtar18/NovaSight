"""
Pydantic schemas for Visual Model Builder API.

Validates request/response payloads for the visual model builder
endpoints, test builder, execution history, and package manager.
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


# ── Enums ────────────────────────────────────────────────────


class ModelLayer(str, Enum):
    STAGING = "staging"
    INTERMEDIATE = "intermediate"
    MARTS = "marts"


class MaterializationType(str, Enum):
    VIEW = "view"
    TABLE = "table"
    INCREMENTAL = "incremental"
    EPHEMERAL = "ephemeral"


class JoinType(str, Enum):
    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    FULL = "full"


class TestType(str, Enum):
    UNIQUE = "unique"
    NOT_NULL = "not_null"
    ACCEPTED_VALUES = "accepted_values"
    RELATIONSHIPS = "relationships"
    # dbt_expectations tests
    EXPECT_COLUMN_VALUES_TO_NOT_BE_NULL = "dbt_expectations.expect_column_values_to_not_be_null"
    EXPECT_COLUMN_VALUES_TO_BE_UNIQUE = "dbt_expectations.expect_column_values_to_be_unique"
    EXPECT_COLUMN_VALUES_TO_BE_IN_SET = "dbt_expectations.expect_column_values_to_be_in_set"
    EXPECT_COLUMN_VALUES_TO_BE_BETWEEN = "dbt_expectations.expect_column_values_to_be_between"
    EXPECT_COLUMN_VALUES_TO_MATCH_REGEX = "dbt_expectations.expect_column_values_to_match_regex"
    EXPECT_COLUMN_VALUES_TO_BE_OF_TYPE = "dbt_expectations.expect_column_values_to_be_of_type"


class FreshnessPeriod(str, Enum):
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


class SourceKind(str, Enum):
    """Where a staging model reads its raw data from.

    - ``warehouse``: an existing ClickHouse table (``source()`` reference).
    - ``iceberg``: an Iceberg table on the tenant's S3 bucket, read via
      ClickHouse's native ``iceberg(...)`` table function. Always
      materializes into the tenant's ClickHouse database.
    """
    WAREHOUSE = "warehouse"
    ICEBERG = "iceberg"


# ── Column & Join Configs ────────────────────────────────────


class VisualTestConfig(BaseModel):
    """Test configuration from visual builder."""
    type: str
    values: Optional[List[str]] = None         # for accepted_values
    to: Optional[str] = None                   # for relationships
    field: Optional[str] = None                # for relationships
    min_value: Optional[float] = None          # for expect_between
    max_value: Optional[float] = None          # for expect_between
    regex: Optional[str] = None                # for expect_match_regex
    column_type: Optional[str] = None          # for expect_of_type
    value_set: Optional[List[str]] = None      # for expect_in_set
    row_condition: Optional[str] = None        # dbt_expectations row_condition
    severity: Optional[str] = "ERROR"          # ERROR | WARN


class VisualColumnConfig(BaseModel):
    """Column configuration from visual builder."""
    name: str = Field(..., min_length=1, max_length=100)
    source_expression: Optional[str] = None
    source_column: Optional[str] = None
    source_alias: Optional[str] = None
    alias: Optional[str] = None
    description: Optional[str] = None
    data_type: Optional[str] = None
    cast: Optional[str] = None
    expression: Optional[str] = None           # free-form SQL expression
    tests: List[VisualTestConfig] = []

    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-z_][a-z0-9_]*$', v):
            raise ValueError('Column name must match ^[a-z_][a-z0-9_]*$')
        return v


class VisualJoinConfig(BaseModel):
    """Join configuration from visual builder."""
    source_model: str
    join_type: JoinType = JoinType.LEFT
    model_alias: Optional[str] = None
    left_key: str
    right_key: str
    additional_conditions: Optional[str] = None


class VisualSourceModelConfig(BaseModel):
    """Source model for intermediate/marts CTEs."""
    name: str
    alias: Optional[str] = None
    where: Optional[str] = None


# ── Create / Update Requests ────────────────────────────────


class VisualModelCreateRequest(BaseModel):
    """Request to create a model from visual builder."""
    model_name: str = Field(..., min_length=1, max_length=64)
    model_layer: ModelLayer = ModelLayer.STAGING
    description: str = Field(default="", max_length=2000)
    materialization: MaterializationType = MaterializationType.VIEW

    # Source configuration (staging)
    source_kind: SourceKind = SourceKind.WAREHOUSE
    source_name: Optional[str] = None
    source_table: Optional[str] = None
    # Iceberg-only: full S3 URI of the Iceberg table (e.g.
    # ``s3://tenant-bucket/iceberg/tenant_acme/raw/orders/``). Required
    # when ``source_kind == 'iceberg'``.
    iceberg_s3_uri: Optional[str] = None
    refs: List[str] = []                          # upstream model refs

    # Source models (intermediate/marts)
    source_models: List[VisualSourceModelConfig] = []

    # Columns, joins, filters
    columns: List[VisualColumnConfig] = []
    joins: List[VisualJoinConfig] = []
    where_clause: Optional[str] = None
    group_by: List[str] = []

    # Incremental config
    unique_key: Optional[Union[str, List[str]]] = None
    incremental_strategy: Optional[str] = None

    # Staging-specific
    primary_key: Optional[str] = None
    tenant_column: Optional[str] = "tenant_id"

    # Marts-specific
    partition_by: Optional[str] = None
    cluster_by: Optional[List[str]] = None
    schema_name: Optional[str] = None

    # Metadata
    tags: List[str] = []
    canvas_position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})

    @validator('model_name')
    def validate_model_name(cls, v):
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('Model name must match ^[a-z][a-z0-9_]*$')
        return v

    @validator('iceberg_s3_uri', always=True)
    def validate_iceberg_uri(cls, v, values):
        kind = values.get('source_kind')
        if kind == SourceKind.ICEBERG:
            if not v:
                raise ValueError(
                    "iceberg_s3_uri is required when source_kind='iceberg'"
                )
            if not v.startswith('s3://'):
                raise ValueError(
                    "iceberg_s3_uri must start with 's3://'"
                )
        return v

    def to_code_gen_config(self) -> Dict[str, Any]:
        """Convert to template context for code generation."""
        # Build source_models list from refs if not provided directly
        source_models = [sm.dict() for sm in self.source_models]
        if not source_models and self.refs:
            source_models = [
                {
                    "name": ref,
                    "alias": ref.replace("stg_", "").replace("int_", ""),
                }
                for ref in self.refs
            ]

        return {
            "model_name": self.model_name,
            "description": self.description,
            "materialized": self.materialization.value,
            "schema": self.schema_name,
            "source_kind": self.source_kind.value,
            "source_name": self.source_name,
            "source_table": self.source_table,
            "iceberg_s3_uri": self.iceberg_s3_uri,
            "columns": [c.dict() for c in self.columns],
            "joins": [
                {
                    "type": j.join_type.value,
                    "model": j.source_model,
                    "model_alias": j.model_alias,
                    "left_key": j.left_key,
                    "right_key": j.right_key,
                    "additional_conditions": j.additional_conditions,
                }
                for j in self.joins
            ],
            "where_clause": self.where_clause,
            "group_by": self.group_by,
            "unique_key": self.unique_key,
            "incremental_strategy": self.incremental_strategy,
            "tags": self.tags,
            "primary_key": self.primary_key,
            "tenant_column": self.tenant_column,
            "source_models": source_models,
            "partition_by": self.partition_by,
            "cluster_by": self.cluster_by,
        }

    def to_schema_config(self) -> Dict[str, Any]:
        """Convert to template context for schema YAML generation."""
        columns_config = []
        for col in self.columns:
            col_dict = {
                "name": col.alias or col.name,
                "description": col.description or "",
            }
            if col.data_type:
                col_dict["data_type"] = col.data_type
            if col.tests:
                col_dict["tests"] = self._format_tests(col.tests)
            columns_config.append(col_dict)

        return {
            "model_name": self.model_name,
            "description": self.description,
            "columns": columns_config,
            "tags": self.tags,
        }

    @staticmethod
    def _format_tests(tests: List[VisualTestConfig]) -> List:
        """Format test configs for schema.yml.j2 template."""
        formatted: List[Any] = []
        for t in tests:
            test_type = t.type
            # Simple built-in tests
            if test_type in ("unique", "not_null"):
                formatted.append(test_type)
            elif test_type == "accepted_values":
                formatted.append({
                    "accepted_values": {"values": t.values or []}
                })
            elif test_type == "relationships":
                formatted.append({
                    "relationships": {"to": t.to, "field": t.field}
                })
            # dbt_expectations tests
            elif test_type.startswith("dbt_expectations."):
                test_config: Dict[str, Any] = {}
                if t.values:
                    test_config["values"] = t.values
                if t.value_set:
                    test_config["value_set"] = t.value_set
                if t.min_value is not None:
                    test_config["min_value"] = t.min_value
                if t.max_value is not None:
                    test_config["max_value"] = t.max_value
                if t.regex:
                    test_config["regex"] = t.regex
                if t.column_type:
                    test_config["type"] = t.column_type
                if t.row_condition:
                    test_config["row_condition"] = t.row_condition
                if t.severity and t.severity != "ERROR":
                    test_config["severity"] = t.severity
                formatted.append({test_type: test_config} if test_config else test_type)
            else:
                formatted.append({test_type: t.dict(exclude_none=True, exclude={"type"})})
        return formatted


class VisualModelUpdateRequest(VisualModelCreateRequest):
    """Request to update a visual model."""
    pass


class VisualModelCanvasState(BaseModel):
    """Canvas position update only (no regeneration)."""
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    zoom: float = 1.0
    viewport: Optional[Dict[str, float]] = None


class GeneratedCodeResponse(BaseModel):
    """Preview response for generated dbt code."""
    model_name: str
    sql: str
    yaml: str


class VisualModelResponse(BaseModel):
    """Response schema for a visual model."""
    id: str
    model_name: str
    model_path: str
    model_layer: str
    canvas_position: Dict[str, Any]
    visual_config: Dict[str, Any]
    generated_sql: Optional[str] = None
    generated_yaml: Optional[str] = None
    materialization: str
    tags: List[str]
    description: str = ""
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── Execution History ────────────────────────────────────────


class DbtExecutionRequest(BaseModel):
    """Request to create a tracked dbt execution."""
    command: str = Field(..., pattern=r'^(run|test|build|compile|seed|snapshot)$')
    selector: Optional[str] = None
    exclude: Optional[str] = None
    full_refresh: bool = False
    target: Optional[str] = None


class DbtExecutionResponse(BaseModel):
    """Response for a dbt execution record."""
    id: str
    command: str
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    selector: Optional[str] = None
    models_affected: List[str] = []
    models_succeeded: int = 0
    models_errored: int = 0
    models_skipped: int = 0
    log_output: str = ""
    error_output: str = ""
    run_results: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None


# ── Test Builder ─────────────────────────────────────────────


class SingularTestCreateRequest(BaseModel):
    """Create a singular (custom SQL) data test."""
    test_name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    sql: str = Field(..., min_length=1)
    tags: List[str] = []

    @validator('test_name')
    def validate_test_name(cls, v):
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('Test name must match ^[a-z][a-z0-9_]*$')
        return v


class FreshnessThreshold(BaseModel):
    """Freshness threshold (warn/error)."""
    count: int = Field(..., gt=0)
    period: FreshnessPeriod = FreshnessPeriod.HOUR


class SourceFreshnessConfig(BaseModel):
    """Source freshness configuration."""
    source_name: str
    table_name: str
    loaded_at_field: str
    warn_after: FreshnessThreshold
    error_after: FreshnessThreshold


# ── Package Manager ──────────────────────────────────────────


class DbtPackage(BaseModel):
    """A dbt package entry."""
    package: Optional[str] = None              # hub package (e.g. dbt-labs/dbt_utils)
    git: Optional[str] = None                  # git URL
    version: Optional[str] = None
    revision: Optional[str] = None


class PackagesUpdateRequest(BaseModel):
    """Update packages.yml."""
    packages: List[DbtPackage]


# ── DAG / Canvas ─────────────────────────────────────────────


class DagNodeData(BaseModel):
    """Data payload for a React Flow node."""
    label: str
    materialization: str
    layer: str
    description: str = ""
    tags: List[str] = []


class DagNode(BaseModel):
    """React Flow node."""
    id: str
    type: str
    position: Dict[str, float]
    data: DagNodeData


class DagEdge(BaseModel):
    """React Flow edge."""
    id: str
    source: str
    target: str
    type: str = "refEdge"


class DagResponse(BaseModel):
    """Full DAG for React Flow canvas."""
    nodes: List[DagNode]
    edges: List[DagEdge]
