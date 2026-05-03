"""
NovaSight Dashboard Models
==========================

Models for dashboard management including dashboards and widgets.
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


class WidgetType(str, Enum):
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


class Dashboard(TenantMixin, TimestampMixin, db.Model):
    """
    Dashboard container for widgets.
    
    A dashboard contains multiple widgets arranged in a grid layout.
    Supports sharing, global filters, and auto-refresh functionality.
    """
    __tablename__ = 'dashboards'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(String(100), nullable=False, index=True)
    description = db.Column(Text, nullable=True)
    
    # Layout configuration (grid layout positions for all widgets)
    layout = db.Column(JSONB, default=list, nullable=False)
    # Example: [{"id": "widget-uuid", "x": 0, "y": 0, "w": 6, "h": 4}, ...]
    
    # Sharing settings
    is_public = db.Column(Boolean, default=False, nullable=False)
    shared_with = db.Column(ARRAY(UUID(as_uuid=True)), default=list, nullable=False)
    
    # Global filters applied to all widgets
    global_filters = db.Column(JSONB, default=dict, nullable=False)
    # Example: {"date_range": {"from": "2024-01-01", "to": "2024-12-31"}, "category": ["A", "B"]}
    
    # Refresh settings
    auto_refresh = db.Column(Boolean, default=False, nullable=False)
    refresh_interval = db.Column(Integer, nullable=True)  # seconds
    
    # Theme/styling
    theme = db.Column(JSONB, default=dict, nullable=False)
    # Example: {"dark_mode": false, "primary_color": "#3B82F6"}
    
    # Tags for organization
    tags = db.Column(ARRAY(String), default=list, nullable=False)
    
    # Ownership
    created_by = db.Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Soft delete
    is_deleted = db.Column(Boolean, default=False, nullable=False)
    deleted_at = db.Column(DateTime, nullable=True)
    
    # Relationships
    widgets = relationship(
        'Widget',
        backref='dashboard',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Widget.created_at'
    )
    
    creator = relationship('User', foreign_keys=[created_by], lazy='select')
    
    def __repr__(self):
        return f"<Dashboard {self.name} ({self.id})>"
    
    def to_dict(self, include_widgets: bool = False) -> Dict[str, Any]:
        """Convert dashboard to dictionary."""
        result = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "layout": self.layout,
            "is_public": self.is_public,
            "shared_with": [str(uid) for uid in (self.shared_with or [])],
            "global_filters": self.global_filters,
            "auto_refresh": self.auto_refresh,
            "refresh_interval": self.refresh_interval,
            "theme": self.theme,
            "tags": self.tags or [],
            "created_by": str(self.created_by),
            "tenant_id": str(self.tenant_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "widget_count": self.widgets.count(),
        }
        
        if include_widgets:
            result["widgets"] = [w.to_dict() for w in self.widgets.all()]
        
        return result
    
    def can_view(self, user_id: str) -> bool:
        """Check if user can view this dashboard."""
        if self.is_public:
            return True
        if str(self.created_by) == str(user_id):
            return True
        if self.shared_with and uuid.UUID(str(user_id)) in self.shared_with:
            return True
        return False
    
    def can_edit(self, user_id: str) -> bool:
        """Check if user can edit this dashboard."""
        return str(self.created_by) == str(user_id)


class Widget(TenantMixin, TimestampMixin, db.Model):
    """
    Individual visualization widget within a dashboard.
    
    Widgets represent individual charts, tables, or metrics that
    query data through their assigned :class:`Dataset`.
    """
    __tablename__ = 'widgets'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dashboard_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey('dashboards.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    name = db.Column(String(100), nullable=False)
    description = db.Column(Text, nullable=True)
    type = db.Column(SQLEnum(WidgetType), nullable=False)
    
    # Optional Dataset reference (Superset-inspired). When set, the widget
    # queries this Dataset instead of relying solely on free-form query_config.
    dataset_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey('datasets.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    
    # Query configuration (filters/sort/limit) layered on the dataset
    query_config = db.Column(JSONB, nullable=False, default=dict)
    # Example:
    # {
    #   "dimensions": ["date", "category"],
    #   "measures": ["total_sales", "order_count"],
    #   "filters": [{"field": "status", "operator": "eq", "value": "completed"}],
    #   "order_by": [{"field": "date", "direction": "desc"}],
    #   "limit": 100,
    #   "time_dimension": "order_date",
    #   "date_from": "2024-01-01",
    #   "date_to": "2024-12-31"
    # }
    
    # Visualization configuration
    viz_config = db.Column(JSONB, default=dict, nullable=False)
    # Example:
    # {
    #   "colors": ["#3B82F6", "#10B981", "#F59E0B"],
    #   "showLegend": true,
    #   "legendPosition": "bottom",
    #   "xAxisLabel": "Date",
    #   "yAxisLabel": "Sales ($)",
    #   "showDataLabels": false,
    #   "stacked": false,
    #   "curved": true
    # }
    
    # Grid position within dashboard
    grid_position = db.Column(JSONB, nullable=False, default=dict)
    # Example: {"x": 0, "y": 0, "w": 6, "h": 4, "minW": 2, "minH": 2}
    
    # Cached query results
    cached_data = db.Column(JSONB, nullable=True)
    cache_expires_at = db.Column(DateTime, nullable=True)
    
    # Widget-specific filters (override global)
    local_filters = db.Column(JSONB, default=dict, nullable=False)
    
    # Drilldown configuration
    drilldown_config = db.Column(JSONB, nullable=True)
    # Example: {"enabled": true, "target_dashboard_id": "uuid", "param_mapping": {"category": "filter_category"}}
    
    def __repr__(self):
        return f"<Widget {self.name} ({self.type.value})>"
    
    def to_dict(self, include_data: bool = False) -> Dict[str, Any]:
        """Convert widget to dictionary."""
        result = {
            "id": str(self.id),
            "dashboard_id": str(self.dashboard_id),
            "name": self.name,
            "description": self.description,
            "type": self.type.value,
            "dataset_id": str(self.dataset_id) if self.dataset_id else None,
            "query_config": self.query_config,
            "viz_config": self.viz_config,
            "grid_position": self.grid_position,
            "local_filters": self.local_filters,
            "drilldown_config": self.drilldown_config,
            "tenant_id": str(self.tenant_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "cache_expires_at": self.cache_expires_at.isoformat() if self.cache_expires_at else None,
        }
        
        if include_data and self.cached_data:
            result["cached_data"] = self.cached_data
        
        return result
    
    def is_cache_valid(self) -> bool:
        """Check if cached data is still valid."""
        if not self.cached_data or not self.cache_expires_at:
            return False
        return datetime.utcnow() < self.cache_expires_at
