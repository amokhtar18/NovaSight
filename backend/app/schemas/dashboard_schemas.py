"""
NovaSight Dashboard Schemas
============================

Pydantic schemas for dashboard API request/response validation.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
from uuid import UUID


# =============================================================================
# Enums
# =============================================================================

class WidgetTypeEnum(str, Enum):
    """Widget visualization types."""
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    TABLE = "table"
    METRIC_CARD = "metric_card"
    AREA_CHART = "area_chart"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"
    DONUT_CHART = "donut_chart"
    GAUGE = "gauge"
    TREEMAP = "treemap"
    FUNNEL = "funnel"
    TEXT = "text"


class FilterOperatorEnum(str, Enum):
    """Filter operators for widget queries."""
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
    """Sort order for query results."""
    ASC = "asc"
    DESC = "desc"


# =============================================================================
# Filter and Order Schemas
# =============================================================================

class QueryFilterSchema(BaseModel):
    """Schema for query filter conditions."""
    field: str = Field(..., min_length=1, max_length=100)
    operator: FilterOperatorEnum
    value: Optional[Any] = None
    values: Optional[List[Any]] = None  # For IN, NOT_IN, BETWEEN operators
    
    @validator('value', 'values', pre=True, always=True)
    def validate_value_presence(cls, v, values):
        operator = values.get('operator')
        if operator in [FilterOperatorEnum.IS_NULL, FilterOperatorEnum.IS_NOT_NULL]:
            return None
        return v


class QueryOrderBySchema(BaseModel):
    """Schema for query ordering."""
    field: str = Field(..., min_length=1, max_length=100)
    direction: SortOrderEnum = Field(default=SortOrderEnum.ASC)


# =============================================================================
# Widget Query Configuration
# =============================================================================

class WidgetQueryConfigSchema(BaseModel):
    """Schema for widget query configuration."""
    dimensions: List[str] = Field(default=[], max_items=10)
    measures: List[str] = Field(..., min_items=1, max_items=20)
    filters: List[QueryFilterSchema] = Field(default=[])
    order_by: List[QueryOrderBySchema] = Field(default=[])
    limit: int = Field(default=1000, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)
    time_dimension: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    
    @validator('dimensions', 'measures', each_item=True)
    def validate_field_names(cls, v):
        """Validate field name format."""
        import re
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError(f"Invalid field name format: {v}")
        return v


# =============================================================================
# Widget Visualization Configuration
# =============================================================================

class WidgetVizConfigSchema(BaseModel):
    """Schema for widget visualization configuration."""
    colors: Optional[List[str]] = Field(default=None, max_items=20)
    showLegend: bool = Field(default=True)
    legendPosition: Optional[str] = Field(default="bottom")
    xAxisLabel: Optional[str] = None
    yAxisLabel: Optional[str] = None
    showDataLabels: bool = Field(default=False)
    stacked: bool = Field(default=False)
    curved: bool = Field(default=True)
    showGrid: bool = Field(default=True)
    animate: bool = Field(default=True)
    aspectRatio: Optional[float] = Field(default=None, ge=0.1, le=10)
    
    # For specific chart types
    innerRadius: Optional[float] = Field(default=None, ge=0, le=1)  # Donut
    startAngle: Optional[int] = Field(default=None)  # Pie/Donut
    endAngle: Optional[int] = Field(default=None)  # Pie/Donut
    
    # Table specific
    pageSize: Optional[int] = Field(default=10, ge=5, le=100)
    sortable: bool = Field(default=True)
    filterable: bool = Field(default=False)
    
    # Metric card specific
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    format: Optional[str] = None  # e.g., "currency", "percentage", "number"
    trend: Optional[Dict[str, Any]] = None
    
    class Config:
        extra = 'allow'  # Allow additional viz config options


# =============================================================================
# Grid Position Configuration
# =============================================================================

class GridPositionSchema(BaseModel):
    """Schema for widget grid position."""
    x: int = Field(..., ge=0, le=24)
    y: int = Field(..., ge=0)
    w: int = Field(..., ge=1, le=24)
    h: int = Field(..., ge=1, le=20)
    minW: int = Field(default=1, ge=1)
    minH: int = Field(default=1, ge=1)
    maxW: Optional[int] = Field(default=None, ge=1)
    maxH: Optional[int] = Field(default=None, ge=1)


# =============================================================================
# Drilldown Configuration
# =============================================================================

class DrilldownConfigSchema(BaseModel):
    """Schema for widget drilldown configuration."""
    enabled: bool = Field(default=False)
    target_dashboard_id: Optional[UUID] = None
    target_url: Optional[str] = None
    param_mapping: Dict[str, str] = Field(default={})


# =============================================================================
# Widget Schemas
# =============================================================================

class WidgetCreateSchema(BaseModel):
    """Schema for creating a widget."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    type: WidgetTypeEnum
    query_config: WidgetQueryConfigSchema
    viz_config: Optional[WidgetVizConfigSchema] = Field(default_factory=WidgetVizConfigSchema)
    grid_position: GridPositionSchema
    local_filters: Optional[Dict[str, Any]] = Field(default={})
    drilldown_config: Optional[DrilldownConfigSchema] = None


class WidgetUpdateSchema(BaseModel):
    """Schema for updating a widget."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    type: Optional[WidgetTypeEnum] = None
    query_config: Optional[WidgetQueryConfigSchema] = None
    viz_config: Optional[WidgetVizConfigSchema] = None
    grid_position: Optional[GridPositionSchema] = None
    local_filters: Optional[Dict[str, Any]] = None
    drilldown_config: Optional[DrilldownConfigSchema] = None


class WidgetResponseSchema(BaseModel):
    """Schema for widget response."""
    id: UUID
    dashboard_id: UUID
    name: str
    description: Optional[str]
    type: WidgetTypeEnum
    query_config: Dict[str, Any]
    viz_config: Dict[str, Any]
    grid_position: Dict[str, Any]
    local_filters: Dict[str, Any]
    drilldown_config: Optional[Dict[str, Any]]
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    cache_expires_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# =============================================================================
# Dashboard Schemas
# =============================================================================

class DashboardThemeSchema(BaseModel):
    """Schema for dashboard theme configuration."""
    dark_mode: bool = Field(default=False)
    primary_color: Optional[str] = Field(default="#3B82F6")
    background_color: Optional[str] = None
    font_family: Optional[str] = None


class DashboardCreateSchema(BaseModel):
    """Schema for creating a dashboard."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    layout: List[Dict[str, Any]] = Field(default=[])
    is_public: bool = Field(default=False)
    global_filters: Optional[Dict[str, Any]] = Field(default={})
    auto_refresh: bool = Field(default=False)
    refresh_interval: Optional[int] = Field(None, ge=10, le=3600)  # 10s to 1h
    theme: Optional[DashboardThemeSchema] = None
    tags: List[str] = Field(default=[])
    
    @validator('name')
    def validate_name(cls, v):
        """Validate dashboard name."""
        import re
        if not re.match(r'^[\w\s\-\.]+$', v):
            raise ValueError("Name can only contain letters, numbers, spaces, hyphens, underscores, and dots")
        return v.strip()
    
    @validator('refresh_interval', always=True)
    def validate_refresh_interval(cls, v, values):
        """Validate refresh interval is set when auto_refresh is enabled."""
        if values.get('auto_refresh') and not v:
            raise ValueError("refresh_interval is required when auto_refresh is enabled")
        return v
    
    @validator('tags', each_item=True)
    def validate_tags(cls, v):
        """Validate tag format."""
        import re
        v = v.strip().lower()
        if not re.match(r'^[\w\-]+$', v):
            raise ValueError("Tags can only contain letters, numbers, hyphens, and underscores")
        if len(v) > 50:
            raise ValueError("Tag must be 50 characters or less")
        return v


class DashboardUpdateSchema(BaseModel):
    """Schema for updating a dashboard."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    layout: Optional[List[Dict[str, Any]]] = None
    is_public: Optional[bool] = None
    global_filters: Optional[Dict[str, Any]] = None
    auto_refresh: Optional[bool] = None
    refresh_interval: Optional[int] = Field(None, ge=10, le=3600)
    theme: Optional[DashboardThemeSchema] = None
    tags: Optional[List[str]] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is None:
            return v
        import re
        if not re.match(r'^[\w\s\-\.]+$', v):
            raise ValueError("Name can only contain letters, numbers, spaces, hyphens, underscores, and dots")
        return v.strip()


class DashboardLayoutUpdateSchema(BaseModel):
    """Schema for updating dashboard layout."""
    layout: List[Dict[str, Any]]
    
    @validator('layout', each_item=True)
    def validate_layout_item(cls, v):
        """Validate each layout item has required fields."""
        required_fields = ['id', 'x', 'y', 'w', 'h']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"Layout item missing required field: {field}")
        return v


class DashboardShareSchema(BaseModel):
    """Schema for sharing a dashboard."""
    user_ids: List[UUID] = Field(..., min_items=1)
    
    @validator('user_ids')
    def validate_unique_users(cls, v):
        """Ensure user IDs are unique."""
        if len(v) != len(set(v)):
            raise ValueError("Duplicate user IDs not allowed")
        return v


class DashboardResponseSchema(BaseModel):
    """Schema for dashboard response."""
    id: UUID
    name: str
    description: Optional[str]
    layout: List[Dict[str, Any]]
    is_public: bool
    shared_with: List[UUID]
    global_filters: Dict[str, Any]
    auto_refresh: bool
    refresh_interval: Optional[int]
    theme: Dict[str, Any]
    tags: List[str]
    created_by: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
    widget_count: int
    widgets: Optional[List[WidgetResponseSchema]] = None
    
    class Config:
        from_attributes = True


class DashboardListResponseSchema(BaseModel):
    """Schema for dashboard list response."""
    id: UUID
    name: str
    description: Optional[str]
    is_public: bool
    tags: List[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    widget_count: int
    
    class Config:
        from_attributes = True


# =============================================================================
# Widget Data Schemas
# =============================================================================

class WidgetDataRequestSchema(BaseModel):
    """Schema for requesting widget data with optional filter overrides."""
    filter_overrides: Optional[List[QueryFilterSchema]] = Field(default=[])
    use_cache: bool = Field(default=True)


class WidgetDataResponseSchema(BaseModel):
    """Schema for widget data response."""
    data: Dict[str, Any]
    cached: bool
    execution_time_ms: Optional[float]
    row_count: int
    columns: List[str]


# =============================================================================
# Dashboard Clone Schema
# =============================================================================

class DashboardCloneSchema(BaseModel):
    """Schema for cloning a dashboard."""
    name: str = Field(..., min_length=1, max_length=100)
    include_widgets: bool = Field(default=True)
