"""
NovaSight Chart Models
======================

Standalone chart models that can be saved independently and reused across dashboards.
Inspired by Superset and Metabase chart management patterns.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin


class ChartType(str, Enum):
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


class ChartSourceType(str, Enum):
    """Data source type for charts."""
    SEMANTIC_MODEL = "semantic_model"
    SQL_QUERY = "sql_query"


class ChartFolder(TenantMixin, TimestampMixin, db.Model):
    """
    Folder for organizing charts.
    
    Supports hierarchical organization with parent-child relationships.
    """
    __tablename__ = 'chart_folders'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(String(100), nullable=False, index=True)
    description = db.Column(Text, nullable=True)
    
    # Hierarchical structure
    parent_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey('chart_folders.id', ondelete='CASCADE'),
        nullable=True,
        index=True
    )
    
    # Ownership
    created_by = db.Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Relationships
    children = relationship(
        'ChartFolder',
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic'
    )
    charts = relationship('Chart', backref='folder', lazy='dynamic')
    
    def __repr__(self):
        return f"<ChartFolder {self.name} ({self.id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert folder to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "tenant_id": str(self.tenant_id),
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "chart_count": self.charts.count(),
            "children_count": self.children.count(),
        }


class Chart(TenantMixin, TimestampMixin, db.Model):
    """
    Standalone chart that can be saved and reused across dashboards.
    
    Charts can source data from:
    - Semantic models (recommended)
    - Raw SQL queries (for advanced users)
    
    Charts are tenant-scoped and can be organized into folders.
    """
    __tablename__ = 'charts'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(String(100), nullable=False, index=True)
    description = db.Column(Text, nullable=True)
    
    # Chart type
    chart_type = db.Column(SQLEnum(ChartType), nullable=False)
    
    # Data source configuration
    source_type = db.Column(SQLEnum(ChartSourceType), nullable=False)
    
    # For semantic model source
    semantic_model_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey('semantic_models.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    
    # For SQL query source (or generated SQL from semantic model)
    sql_query = db.Column(Text, nullable=True)
    
    # Query configuration (dimensions, measures, filters, etc.)
    query_config = db.Column(JSONB, nullable=False, default=dict)
    # Structure:
    # {
    #     "dimensions": ["date", "category"],
    #     "measures": ["total_sales", "order_count"],
    #     "filters": [{"field": "status", "operator": "eq", "value": "completed"}],
    #     "order_by": [{"field": "date", "direction": "desc"}],
    #     "limit": 100,
    #     "time_dimension": "order_date",
    #     "date_range": {"from": "2024-01-01", "to": "2024-12-31"}
    # }
    
    # Visualization configuration
    viz_config = db.Column(JSONB, nullable=False, default=dict)
    # Structure:
    # {
    #     "title": "Monthly Sales",
    #     "subtitle": "Last 12 months",
    #     "colors": ["#3B82F6", "#10B981", "#F59E0B"],
    #     "showLegend": true,
    #     "legendPosition": "bottom",
    #     "xAxisLabel": "Date",
    #     "yAxisLabel": "Sales ($)",
    #     "showDataLabels": false,
    #     "stacked": false,
    #     "curved": true,
    #     "showGrid": true
    # }
    
    # Organization
    folder_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey('chart_folders.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    tags = db.Column(ARRAY(String), default=list, nullable=False)
    
    # Ownership & sharing
    created_by = db.Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    is_public = db.Column(Boolean, default=False, nullable=False)  # Within tenant
    
    # Caching
    cached_data = db.Column(JSONB, nullable=True)
    cache_expires_at = db.Column(DateTime, nullable=True)
    cache_ttl_seconds = db.Column(Integer, default=300, nullable=False)  # 5 min default
    
    # Soft delete
    is_deleted = db.Column(Boolean, default=False, nullable=False)
    deleted_at = db.Column(DateTime, nullable=True)
    
    # Relationships
    creator = relationship('User', foreign_keys=[created_by], lazy='select')
    semantic_model = relationship('SemanticModel', lazy='select')
    # Note: DashboardChart has relationship back to this model via foreign key
    
    def __repr__(self):
        return f"<Chart {self.name} ({self.chart_type.value})>"
    
    def to_dict(self, include_data: bool = False) -> Dict[str, Any]:
        """Convert chart to dictionary."""
        result = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "chart_type": self.chart_type.value,
            "source_type": self.source_type.value,
            "semantic_model_id": str(self.semantic_model_id) if self.semantic_model_id else None,
            "query_config": self.query_config,
            "viz_config": self.viz_config,
            "folder_id": str(self.folder_id) if self.folder_id else None,
            "tags": self.tags or [],
            "is_public": self.is_public,
            "created_by": str(self.created_by),
            "tenant_id": str(self.tenant_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_data and self.cached_data:
            result["data"] = self.cached_data
        
        return result
    
    def is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        if not self.cached_data or not self.cache_expires_at:
            return False
        return datetime.utcnow() < self.cache_expires_at
    
    def can_view(self, user_id: str) -> bool:
        """Check if user can view this chart."""
        if self.is_public:
            return True
        return str(self.created_by) == str(user_id)
    
    def can_edit(self, user_id: str) -> bool:
        """Check if user can edit this chart."""
        return str(self.created_by) == str(user_id)


class DashboardChart(TenantMixin, TimestampMixin, db.Model):
    """
    Junction table connecting saved charts to dashboards.
    
    This allows the same chart to be used in multiple dashboards
    with different positions and local overrides.
    """
    __tablename__ = 'dashboard_charts'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # References
    dashboard_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey('dashboards.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    chart_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey('charts.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Grid position within dashboard
    grid_position = db.Column(JSONB, nullable=False, default=dict)
    # Structure: {"x": 0, "y": 0, "w": 6, "h": 4, "minW": 2, "minH": 2}
    
    # Local overrides (optional - override chart's default config)
    local_filters = db.Column(JSONB, default=dict, nullable=False)
    local_viz_config = db.Column(JSONB, default=dict, nullable=False)
    
    # Relationships - use unique backref names to avoid conflicts
    dashboard = relationship('Dashboard', backref=db.backref('chart_placements', lazy='dynamic'))
    chart = relationship('Chart', backref=db.backref('dashboard_usages', lazy='dynamic'))
    
    # Unique constraint: same chart can only appear once per dashboard
    __table_args__ = (
        db.UniqueConstraint('dashboard_id', 'chart_id', name='uq_dashboard_chart'),
        {'extend_existing': True}
    )
    
    def __repr__(self):
        return f"<DashboardChart {self.chart_id} in {self.dashboard_id}>"
    
    def to_dict(self, include_chart: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "id": str(self.id),
            "dashboard_id": str(self.dashboard_id),
            "chart_id": str(self.chart_id),
            "grid_position": self.grid_position,
            "local_filters": self.local_filters,
            "local_viz_config": self.local_viz_config,
        }
        
        if include_chart and self.chart:
            result["chart"] = self.chart.to_dict()
        
        return result
