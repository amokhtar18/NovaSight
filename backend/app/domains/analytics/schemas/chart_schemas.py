"""
NovaSight Chart Schemas
========================

Pydantic schemas for chart API request/response validation.
"""

from pydantic import BaseModel, Field, validator, conlist
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from uuid import UUID


# =============================================================================
# Enums
# =============================================================================

class ChartTypeEnum(str, Enum):
    """Available chart visualization types."""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    AREA = "area"
    SCATTER = "scatter"
    DONUT = "donut"
    METRIC = "metric"
    TABLE = "table"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    TREEMAP = "treemap"
    FUNNEL = "funnel"


class ChartSourceTypeEnum(str, Enum):
    """Data source type for charts."""
    SQL_QUERY = "sql_query"
    DATASET = "dataset"


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
    BETWEEN = "between"


class SortDirectionEnum(str, Enum):
    """Sort direction for queries."""
    ASC = "asc"
    DESC = "desc"


# =============================================================================
# Query Configuration Schemas
# =============================================================================

class ChartFilterSchema(BaseModel):
    """Schema for chart filter conditions."""
    field: str = Field(..., min_length=1, max_length=100)
    operator: FilterOperatorEnum
    value: Optional[Any] = None
    values: Optional[List[Any]] = None  # For IN, BETWEEN operators


class ChartOrderBySchema(BaseModel):
    """Schema for chart query ordering."""
    field: str = Field(..., min_length=1, max_length=100)
    direction: SortDirectionEnum = Field(default=SortDirectionEnum.ASC)


class ChartDateRangeSchema(BaseModel):
    """Schema for date range configuration."""
    from_date: Optional[str] = Field(None, alias="from")
    to_date: Optional[str] = Field(None, alias="to")
    preset: Optional[str] = None  # e.g., "last_7_days", "last_30_days", "this_month"
    
    class Config:
        populate_by_name = True


class ChartQueryConfigSchema(BaseModel):
    """Schema for chart query configuration."""
    dimensions: conlist(str, max_length=10) = Field(default=[])
    measures: conlist(str, max_length=20) = Field(default=[])
    filters: List[ChartFilterSchema] = Field(default=[])
    order_by: List[ChartOrderBySchema] = Field(default=[], alias="orderBy")
    limit: int = Field(default=1000, ge=1, le=10000)
    time_dimension: Optional[str] = Field(default=None, alias="timeDimension")
    date_range: Optional[ChartDateRangeSchema] = Field(default=None, alias="dateRange")
    
    class Config:
        populate_by_name = True
    
    @validator('dimensions', 'measures', each_item=True)
    def validate_field_names(cls, v):
        """Validate field name format."""
        import re
        # Allow dotted names for nested fields (e.g., "orders.total")
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_.]*$', v):
            raise ValueError(f"Invalid field name format: {v}")
        return v


# =============================================================================
# Visualization Configuration Schema
# =============================================================================

class ChartVizConfigSchema(BaseModel):
    """Schema for chart visualization configuration."""
    title: Optional[str] = None
    subtitle: Optional[str] = None
    colors: Optional[conlist(str, max_length=20)] = Field(default=None)
    showLegend: bool = Field(default=True)
    legendPosition: Optional[str] = Field(default="bottom")
    xAxisLabel: Optional[str] = None
    yAxisLabel: Optional[str] = None
    showDataLabels: bool = Field(default=False)
    stacked: bool = Field(default=False)
    curved: bool = Field(default=True)
    showGrid: bool = Field(default=True)
    animate: bool = Field(default=True)
    
    # Pie/Donut specific
    innerRadius: Optional[float] = Field(default=None, ge=0, le=1)
    
    # Metric card specific
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    format: Optional[str] = None  # "currency", "percentage", "number"
    
    # Table specific
    pageSize: Optional[int] = Field(default=10, ge=5, le=100)
    
    class Config:
        extra = 'allow'  # Allow additional viz config options


# =============================================================================
# Chart CRUD Schemas
# =============================================================================

class ChartCreateSchema(BaseModel):
    """Schema for creating a new chart."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    chart_type: ChartTypeEnum
    source_type: ChartSourceTypeEnum
    dataset_id: Optional[UUID] = None
    sql_query: Optional[str] = None
    query_config: ChartQueryConfigSchema = Field(default_factory=ChartQueryConfigSchema)
    viz_config: ChartVizConfigSchema = Field(default_factory=ChartVizConfigSchema)
    folder_id: Optional[UUID] = None
    tags: List[str] = Field(default=[])
    is_public: bool = Field(default=False)
    
    @validator('sql_query')
    def validate_sql_query(cls, v, values):
        """Validate SQL query is provided for SQL source type."""
        source_type = values.get('source_type')
        if source_type == ChartSourceTypeEnum.SQL_QUERY and not v:
            raise ValueError("SQL query is required for SQL source type")
        return v
    
    @validator('dataset_id')
    def validate_dataset(cls, v, values):
        """Validate dataset is provided for dataset source type."""
        source_type = values.get('source_type')
        if source_type == ChartSourceTypeEnum.DATASET and not v:
            raise ValueError("Dataset ID is required for dataset source type")
        return v


class ChartUpdateSchema(BaseModel):
    """Schema for updating an existing chart."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    chart_type: Optional[ChartTypeEnum] = None
    source_type: Optional[ChartSourceTypeEnum] = None
    dataset_id: Optional[UUID] = None
    sql_query: Optional[str] = None
    query_config: Optional[ChartQueryConfigSchema] = None
    viz_config: Optional[ChartVizConfigSchema] = None
    folder_id: Optional[UUID] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class ChartResponseSchema(BaseModel):
    """Schema for chart response."""
    id: UUID
    name: str
    description: Optional[str]
    chart_type: ChartTypeEnum
    source_type: ChartSourceTypeEnum
    dataset_id: Optional[UUID] = None
    query_config: Dict[str, Any]
    viz_config: Dict[str, Any]
    folder_id: Optional[UUID]
    tags: List[str]
    is_public: bool
    created_by: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ChartListResponseSchema(BaseModel):
    """Schema for paginated chart list response."""
    items: List[ChartResponseSchema]
    total: int
    page: int
    per_page: int
    pages: int


class ChartDataResponseSchema(BaseModel):
    """Schema for chart data execution response."""
    chart_id: UUID
    data: List[Dict[str, Any]]
    columns: List[Dict[str, str]]  # [{"name": "date", "type": "datetime"}, ...]
    row_count: int
    execution_time_ms: int
    cached: bool
    cache_expires_at: Optional[datetime]


# =============================================================================
# Chart Preview Schema (without saving)
# =============================================================================

class ChartPreviewSchema(BaseModel):
    """Schema for previewing chart data without saving."""
    source_type: ChartSourceTypeEnum
    dataset_id: Optional[UUID] = None
    sql_query: Optional[str] = None
    query_config: ChartQueryConfigSchema = Field(default_factory=ChartQueryConfigSchema)
    limit: int = Field(default=100, ge=1, le=1000)


# =============================================================================
# Chart Folder Schemas
# =============================================================================

class ChartFolderCreateSchema(BaseModel):
    """Schema for creating a chart folder."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[UUID] = None


class ChartFolderUpdateSchema(BaseModel):
    """Schema for updating a chart folder."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    parent_id: Optional[UUID] = None


class ChartFolderResponseSchema(BaseModel):
    """Schema for chart folder response."""
    id: UUID
    name: str
    description: Optional[str]
    parent_id: Optional[UUID]
    tenant_id: UUID
    created_by: UUID
    created_at: datetime
    chart_count: int = 0
    children_count: int = 0
    
    class Config:
        from_attributes = True


# =============================================================================
# SQL Editor Chart Schemas (Limited chart types)
# =============================================================================

class SQLEditorChartTypeEnum(str, Enum):
    """Limited chart types for SQL Editor quick visualization."""
    BAR = "bar"
    LINE = "line"
    PIE = "pie"


class SQLEditorChartConfigSchema(BaseModel):
    """Schema for SQL Editor quick chart configuration."""
    chart_type: SQLEditorChartTypeEnum
    x_column: str = Field(..., description="Column to use for X-axis or categories")
    y_columns: conlist(str, min_length=1, max_length=5) = Field(..., description="Columns to use for Y-axis values")
    viz_config: Optional[ChartVizConfigSchema] = None


class SQLEditorSaveAsChartSchema(BaseModel):
    """Schema for saving SQL query result as a chart."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    chart_type: SQLEditorChartTypeEnum
    sql_query: str = Field(..., min_length=1)
    x_column: str
    y_columns: conlist(str, min_length=1) = Field(...)
    viz_config: Optional[ChartVizConfigSchema] = None
    folder_id: Optional[UUID] = None
    tags: List[str] = Field(default=[])
