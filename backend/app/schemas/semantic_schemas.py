"""
NovaSight Semantic Layer Schemas
=================================

Pydantic schemas for semantic layer API request/response validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
from uuid import UUID


# =============================================================================
# Enums
# =============================================================================

class DimensionTypeEnum(str, Enum):
    """Dimension types."""
    CATEGORICAL = "categorical"
    TEMPORAL = "temporal"
    NUMERIC = "numeric"
    HIERARCHICAL = "hierarchical"


class AggregationTypeEnum(str, Enum):
    """Aggregation types for measures."""
    SUM = "sum"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    STDDEV = "stddev"
    VARIANCE = "variance"


class ModelTypeEnum(str, Enum):
    """Semantic model types."""
    FACT = "fact"
    DIMENSION = "dimension"
    AGGREGATE = "aggregate"


class RelationshipTypeEnum(str, Enum):
    """Relationship types."""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


class FilterOperatorEnum(str, Enum):
    """Filter operators for queries."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUALS = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUALS = "lte"
    IN = "in"
    NOT_IN = "not_in"
    LIKE = "like"
    NOT_LIKE = "not_like"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    BETWEEN = "between"


class SortOrderEnum(str, Enum):
    """Sort order."""
    ASC = "asc"
    DESC = "desc"


# =============================================================================
# Semantic Model Schemas
# =============================================================================

class SemanticModelCreateSchema(BaseModel):
    """Schema for creating a semantic model."""
    name: str = Field(..., min_length=1, max_length=100)
    label: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    dbt_model: str = Field(..., min_length=1, max_length=100)
    model_type: ModelTypeEnum = Field(default=ModelTypeEnum.FACT)
    target_schema: Optional[str] = Field(None, max_length=100)
    target_table: Optional[str] = Field(None, max_length=100)
    cache_enabled: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600, ge=0, le=86400)
    tags: Optional[List[str]] = Field(default=[])
    meta: Optional[Dict[str, Any]] = Field(default={})
    
    @validator('name')
    def validate_name(cls, v):
        """Validate model name format."""
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(
                'Name must start with lowercase letter and contain only '
                'lowercase letters, numbers, and underscores'
            )
        return v
    
    @validator('dbt_model')
    def validate_dbt_model(cls, v):
        """Validate dbt model reference."""
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('dbt_model must be a valid model name')
        return v
    
    class Config:
        use_enum_values = True


class SemanticModelUpdateSchema(BaseModel):
    """Schema for updating a semantic model."""
    label: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    model_type: Optional[ModelTypeEnum] = None
    target_schema: Optional[str] = Field(None, max_length=100)
    target_table: Optional[str] = Field(None, max_length=100)
    cache_enabled: Optional[bool] = None
    cache_ttl_seconds: Optional[int] = Field(None, ge=0, le=86400)
    tags: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    
    class Config:
        use_enum_values = True


class SemanticModelResponseSchema(BaseModel):
    """Schema for semantic model response."""
    id: str
    name: str
    label: Optional[str]
    description: Optional[str]
    dbt_model: str
    model_type: str
    target_schema: Optional[str]
    target_table: Optional[str]
    cache_enabled: bool
    cache_ttl_seconds: int
    tags: List[str]
    meta: Dict[str, Any]
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    dimensions_count: Optional[int] = 0
    measures_count: Optional[int] = 0
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# =============================================================================
# Dimension Schemas
# =============================================================================

class DimensionCreateSchema(BaseModel):
    """Schema for creating a dimension."""
    name: str = Field(..., min_length=1, max_length=100)
    label: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    type: DimensionTypeEnum = Field(default=DimensionTypeEnum.CATEGORICAL)
    expression: str = Field(..., min_length=1, max_length=500)
    data_type: str = Field(default="String", max_length=50)
    is_primary_key: bool = Field(default=False)
    is_hidden: bool = Field(default=False)
    is_filterable: bool = Field(default=True)
    is_groupable: bool = Field(default=True)
    hierarchy_name: Optional[str] = Field(None, max_length=100)
    hierarchy_level: Optional[int] = Field(None, ge=0, le=10)
    parent_dimension_id: Optional[str] = None
    default_value: Optional[str] = Field(None, max_length=100)
    format_string: Optional[str] = Field(None, max_length=100)
    meta: Optional[Dict[str, Any]] = Field(default={})
    
    @validator('name')
    def validate_name(cls, v):
        """Validate dimension name format."""
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(
                'Name must start with lowercase letter and contain only '
                'lowercase letters, numbers, and underscores'
            )
        return v
    
    @validator('expression')
    def validate_expression(cls, v):
        """Basic SQL injection prevention."""
        dangerous = ['drop', 'delete', 'truncate', 'alter', 'create', '--', ';']
        lower_v = v.lower()
        for pattern in dangerous:
            if pattern in lower_v:
                raise ValueError(f"Expression contains forbidden pattern: {pattern}")
        return v
    
    class Config:
        use_enum_values = True


class DimensionUpdateSchema(BaseModel):
    """Schema for updating a dimension."""
    label: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    type: Optional[DimensionTypeEnum] = None
    expression: Optional[str] = Field(None, max_length=500)
    data_type: Optional[str] = Field(None, max_length=50)
    is_hidden: Optional[bool] = None
    is_filterable: Optional[bool] = None
    is_groupable: Optional[bool] = None
    hierarchy_name: Optional[str] = Field(None, max_length=100)
    hierarchy_level: Optional[int] = Field(None, ge=0, le=10)
    parent_dimension_id: Optional[str] = None
    default_value: Optional[str] = Field(None, max_length=100)
    format_string: Optional[str] = Field(None, max_length=100)
    meta: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class DimensionResponseSchema(BaseModel):
    """Schema for dimension response."""
    id: str
    semantic_model_id: str
    name: str
    label: Optional[str]
    description: Optional[str]
    type: str
    expression: str
    data_type: str
    is_primary_key: bool
    is_hidden: bool
    is_filterable: bool
    is_groupable: bool
    hierarchy_name: Optional[str]
    hierarchy_level: Optional[int]
    parent_dimension_id: Optional[str]
    default_value: Optional[str]
    format_string: Optional[str]
    meta: Dict[str, Any]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# =============================================================================
# Measure Schemas
# =============================================================================

class MeasureCreateSchema(BaseModel):
    """Schema for creating a measure."""
    name: str = Field(..., min_length=1, max_length=100)
    label: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    aggregation: AggregationTypeEnum = Field(...)
    expression: str = Field(..., min_length=1, max_length=500)
    format: Optional[str] = Field(None, max_length=50)
    format_string: Optional[str] = Field(None, max_length=100)
    decimal_places: int = Field(default=2, ge=0, le=10)
    unit: Optional[str] = Field(None, max_length=50)
    unit_suffix: Optional[str] = Field(None, max_length=20)
    is_hidden: bool = Field(default=False)
    is_additive: bool = Field(default=True)
    percentile_value: Optional[int] = Field(None, ge=1, le=99)
    default_filters: Optional[List[Dict[str, Any]]] = Field(default=[])
    time_dimension: Optional[str] = Field(None, max_length=100)
    meta: Optional[Dict[str, Any]] = Field(default={})
    
    @validator('name')
    def validate_name(cls, v):
        """Validate measure name format."""
        import re
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(
                'Name must start with lowercase letter and contain only '
                'lowercase letters, numbers, and underscores'
            )
        return v
    
    @validator('expression')
    def validate_expression(cls, v):
        """Basic SQL injection prevention."""
        dangerous = ['drop', 'delete', 'truncate', 'alter', 'create', '--', ';']
        lower_v = v.lower()
        for pattern in dangerous:
            if pattern in lower_v:
                raise ValueError(f"Expression contains forbidden pattern: {pattern}")
        return v
    
    @validator('percentile_value')
    def validate_percentile(cls, v, values):
        """Validate percentile value when aggregation is PERCENTILE."""
        if values.get('aggregation') == AggregationTypeEnum.PERCENTILE and v is None:
            raise ValueError('percentile_value is required when aggregation is PERCENTILE')
        return v
    
    class Config:
        use_enum_values = True


class MeasureUpdateSchema(BaseModel):
    """Schema for updating a measure."""
    label: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    aggregation: Optional[AggregationTypeEnum] = None
    expression: Optional[str] = Field(None, max_length=500)
    format: Optional[str] = Field(None, max_length=50)
    format_string: Optional[str] = Field(None, max_length=100)
    decimal_places: Optional[int] = Field(None, ge=0, le=10)
    unit: Optional[str] = Field(None, max_length=50)
    unit_suffix: Optional[str] = Field(None, max_length=20)
    is_hidden: Optional[bool] = None
    is_additive: Optional[bool] = None
    percentile_value: Optional[int] = Field(None, ge=1, le=99)
    default_filters: Optional[List[Dict[str, Any]]] = None
    time_dimension: Optional[str] = Field(None, max_length=100)
    meta: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class MeasureResponseSchema(BaseModel):
    """Schema for measure response."""
    id: str
    semantic_model_id: str
    name: str
    label: Optional[str]
    description: Optional[str]
    aggregation: str
    expression: str
    format: Optional[str]
    format_string: Optional[str]
    decimal_places: int
    unit: Optional[str]
    unit_suffix: Optional[str]
    is_hidden: bool
    is_additive: bool
    percentile_value: Optional[int]
    default_filters: List[Dict[str, Any]]
    time_dimension: Optional[str]
    meta: Dict[str, Any]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        orm_mode = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# =============================================================================
# Relationship Schemas
# =============================================================================

class RelationshipCreateSchema(BaseModel):
    """Schema for creating a relationship."""
    from_model_id: str = Field(...)
    to_model_id: str = Field(...)
    from_column: str = Field(..., min_length=1, max_length=100)
    to_column: str = Field(..., min_length=1, max_length=100)
    relationship_type: RelationshipTypeEnum = Field(default=RelationshipTypeEnum.MANY_TO_ONE)
    join_type: str = Field(default="LEFT", max_length=20)
    additional_conditions: Optional[str] = Field(None, max_length=500)
    
    @validator('join_type')
    def validate_join_type(cls, v):
        """Validate join type."""
        valid_types = ['LEFT', 'INNER', 'RIGHT', 'FULL']
        if v.upper() not in valid_types:
            raise ValueError(f'join_type must be one of: {valid_types}')
        return v.upper()
    
    class Config:
        use_enum_values = True


class RelationshipResponseSchema(BaseModel):
    """Schema for relationship response."""
    id: str
    from_model_id: str
    to_model_id: str
    from_column: str
    to_column: str
    relationship_type: str
    join_type: str
    additional_conditions: Optional[str]
    is_active: bool
    
    class Config:
        orm_mode = True


# =============================================================================
# Query Schemas
# =============================================================================

class QueryFilterSchema(BaseModel):
    """Schema for query filters."""
    dimension: str = Field(..., description="Dimension name to filter on")
    operator: FilterOperatorEnum = Field(...)
    value: Union[str, int, float, bool, List[Any], None] = Field(None)
    values: Optional[List[Any]] = Field(None, description="For IN/NOT_IN operators")
    
    @validator('values')
    def validate_values(cls, v, values):
        """Validate values for IN operators."""
        op = values.get('operator')
        if op in [FilterOperatorEnum.IN, FilterOperatorEnum.NOT_IN]:
            if v is None and values.get('value') is None:
                raise ValueError('values is required for IN/NOT_IN operators')
        return v
    
    class Config:
        use_enum_values = True


class QueryOrderBySchema(BaseModel):
    """Schema for query ordering."""
    field: str = Field(..., description="Dimension or measure name")
    order: SortOrderEnum = Field(default=SortOrderEnum.ASC)
    
    class Config:
        use_enum_values = True


class SemanticQuerySchema(BaseModel):
    """Schema for semantic layer queries."""
    dimensions: List[str] = Field(default=[], description="List of dimension names")
    measures: List[str] = Field(..., min_length=1, description="List of measure names")
    filters: Optional[List[QueryFilterSchema]] = Field(default=[])
    order_by: Optional[List[QueryOrderBySchema]] = Field(default=[])
    limit: int = Field(default=1000, ge=1, le=100000)
    offset: int = Field(default=0, ge=0)
    
    # Time range filter (convenience)
    time_dimension: Optional[str] = Field(None, description="Time dimension for date filtering")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    
    # Model selection (optional, auto-infer from dimensions/measures)
    models: Optional[List[str]] = Field(default=[], description="Explicit model selection")
    
    @validator('dimensions', 'measures')
    def validate_field_names(cls, v):
        """Validate field names."""
        import re
        for name in v:
            if not re.match(r'^[a-z][a-z0-9_]*$', name):
                raise ValueError(f'Invalid field name: {name}')
        return v


class QueryResultSchema(BaseModel):
    """Schema for query results."""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    total_count: Optional[int] = None
    query: Optional[str] = None  # For debugging
    execution_time_ms: float
    cached: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# =============================================================================
# Discovery Schemas
# =============================================================================

class AvailableFieldSchema(BaseModel):
    """Schema for available fields in explore."""
    name: str
    label: Optional[str]
    description: Optional[str]
    field_type: str  # 'dimension' or 'measure'
    data_type: Optional[str]
    model_name: str
    
    class Config:
        orm_mode = True


class ExploreSchema(BaseModel):
    """Schema for explore metadata."""
    models: List[SemanticModelResponseSchema]
    dimensions: List[DimensionResponseSchema]
    measures: List[MeasureResponseSchema]
    relationships: List[RelationshipResponseSchema]
