# 024 - Dashboard API

## Metadata

```yaml
prompt_id: "024"
phase: 4
agent: "@dashboard"
model: "sonnet 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["019", "023"]
```

## Objective

Implement the dashboard management API with widget configurations and layout persistence.

## Task Description

Create REST endpoints for creating, managing, and sharing dashboards with visualizations.

## Requirements

### Dashboard Models

```python
# backend/app/models/dashboard.py
from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from enum import Enum

class WidgetType(str, Enum):
    BAR_CHART = "bar_chart"
    LINE_CHART = "line_chart"
    PIE_CHART = "pie_chart"
    TABLE = "table"
    METRIC_CARD = "metric_card"
    AREA_CHART = "area_chart"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"

class Dashboard(TenantMixin, TimestampMixin, db.Model):
    """Dashboard container for widgets."""
    __tablename__ = 'dashboards'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Layout configuration
    layout = db.Column(JSONB, default=[])  # Grid layout config
    
    # Sharing
    is_public = db.Column(db.Boolean, default=False)
    shared_with = db.Column(ARRAY(UUID(as_uuid=True)), default=[])
    
    # Global filters
    global_filters = db.Column(JSONB, default={})
    
    # Refresh settings
    auto_refresh = db.Column(db.Boolean, default=False)
    refresh_interval = db.Column(db.Integer)  # seconds
    
    # Relationships
    widgets = db.relationship('Widget', backref='dashboard', lazy='dynamic',
                              cascade='all, delete-orphan')
    
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))

class Widget(TenantMixin, TimestampMixin, db.Model):
    """Individual visualization widget."""
    __tablename__ = 'widgets'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    dashboard_id = db.Column(UUID(as_uuid=True), db.ForeignKey('dashboards.id'))
    
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum(WidgetType), nullable=False)
    
    # Query configuration
    query_config = db.Column(JSONB, nullable=False)
    # {
    #   "dimensions": ["date", "category"],
    #   "measures": ["total_sales", "order_count"],
    #   "filters": [...],
    #   "order_by": [...],
    #   "limit": 100
    # }
    
    # Visualization configuration
    viz_config = db.Column(JSONB, default={})
    # {
    #   "colors": ["#3B82F6", "#10B981"],
    #   "showLegend": true,
    #   "xAxisLabel": "Date",
    #   "yAxisLabel": "Sales"
    # }
    
    # Grid position
    grid_position = db.Column(JSONB, nullable=False)
    # { "x": 0, "y": 0, "w": 6, "h": 4 }
    
    # Cached data
    cached_data = db.Column(JSONB)
    cache_expires_at = db.Column(db.DateTime)
```

### Dashboard API Endpoints

```python
# backend/app/api/v1/dashboards.py
from flask import Blueprint, request, g
from app.schemas.dashboard_schemas import (
    DashboardSchema,
    DashboardCreateSchema,
    WidgetSchema,
    WidgetCreateSchema
)
from app.services.dashboard_service import DashboardService
from app.middleware.permissions import require_permission

dashboards_bp = Blueprint('dashboards', __name__)

@dashboards_bp.route('/', methods=['GET'])
@require_permission('dashboards.view')
def list_dashboards():
    """List all accessible dashboards."""
    dashboards = DashboardService.list_for_user(
        tenant_id=g.tenant.id,
        user_id=g.current_user_id
    )
    return DashboardSchema(many=True).dump(dashboards)

@dashboards_bp.route('/', methods=['POST'])
@require_permission('dashboards.create')
def create_dashboard():
    """Create a new dashboard."""
    data = DashboardCreateSchema().load(request.json)
    dashboard = DashboardService.create(
        tenant_id=g.tenant.id,
        created_by=g.current_user_id,
        **data
    )
    return DashboardSchema().dump(dashboard), 201

@dashboards_bp.route('/<uuid:dashboard_id>', methods=['GET'])
@require_permission('dashboards.view')
def get_dashboard(dashboard_id):
    """Get dashboard with all widgets."""
    dashboard = DashboardService.get(
        dashboard_id, g.tenant.id, g.current_user_id
    )
    return DashboardSchema().dump(dashboard)

@dashboards_bp.route('/<uuid:dashboard_id>', methods=['PUT'])
@require_permission('dashboards.edit')
def update_dashboard(dashboard_id):
    """Update dashboard metadata."""
    data = DashboardCreateSchema().load(request.json)
    dashboard = DashboardService.update(
        dashboard_id, g.tenant.id, **data
    )
    return DashboardSchema().dump(dashboard)

@dashboards_bp.route('/<uuid:dashboard_id>/layout', methods=['PUT'])
@require_permission('dashboards.edit')
def update_layout(dashboard_id):
    """Update dashboard layout."""
    layout = request.json['layout']
    dashboard = DashboardService.update_layout(
        dashboard_id, g.tenant.id, layout
    )
    return {'success': True}

@dashboards_bp.route('/<uuid:dashboard_id>/widgets', methods=['POST'])
@require_permission('dashboards.edit')
def add_widget(dashboard_id):
    """Add widget to dashboard."""
    data = WidgetCreateSchema().load(request.json)
    widget = DashboardService.add_widget(
        dashboard_id, g.tenant.id, **data
    )
    return WidgetSchema().dump(widget), 201

@dashboards_bp.route('/<uuid:dashboard_id>/widgets/<uuid:widget_id>/data', methods=['GET'])
@require_permission('analytics.query')
def get_widget_data(dashboard_id, widget_id):
    """Get widget data (execute query)."""
    widget = DashboardService.get_widget(widget_id, g.tenant.id)
    
    # Check cache
    if widget.cached_data and widget.cache_expires_at > datetime.utcnow():
        return {'data': widget.cached_data, 'cached': True}
    
    # Execute query
    data = DashboardService.execute_widget_query(widget, g.tenant.id)
    return {'data': data, 'cached': False}

@dashboards_bp.route('/<uuid:dashboard_id>/share', methods=['POST'])
@require_permission('dashboards.share')
def share_dashboard(dashboard_id):
    """Share dashboard with users."""
    user_ids = request.json['user_ids']
    DashboardService.share(dashboard_id, g.tenant.id, user_ids)
    return {'success': True}
```

### Dashboard Service

```python
# backend/app/services/dashboard_service.py
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.models.dashboard import Dashboard, Widget
from app.services.semantic_service import SemanticService
from app.extensions import db

class DashboardService:
    """Service for dashboard operations."""
    
    @classmethod
    def execute_widget_query(
        cls,
        widget: Widget,
        tenant_id: str
    ) -> Dict[str, Any]:
        """Execute widget query and cache results."""
        
        config = widget.query_config
        
        # Execute through semantic layer
        result = SemanticService.execute_query(
            tenant_id=tenant_id,
            dimensions=config.get('dimensions', []),
            measures=config.get('measures', []),
            filters=config.get('filters', []),
            order_by=config.get('order_by'),
            limit=config.get('limit', 1000)
        )
        
        # Cache results
        widget.cached_data = result
        widget.cache_expires_at = datetime.utcnow() + timedelta(minutes=5)
        db.session.commit()
        
        return result
    
    @classmethod
    def update_layout(
        cls,
        dashboard_id: str,
        tenant_id: str,
        layout: List[Dict]
    ) -> Dashboard:
        """Update widget positions."""
        dashboard = cls.get(dashboard_id, tenant_id)
        
        # Update each widget's grid_position
        for item in layout:
            widget = Widget.query.get(item['id'])
            if widget and widget.dashboard_id == dashboard.id:
                widget.grid_position = {
                    'x': item['x'],
                    'y': item['y'],
                    'w': item['w'],
                    'h': item['h'],
                }
        
        db.session.commit()
        return dashboard
```

## Expected Output

```
backend/app/
├── models/
│   └── dashboard.py
├── api/v1/
│   └── dashboards.py
├── schemas/
│   └── dashboard_schemas.py
└── services/
    └── dashboard_service.py
```

## Acceptance Criteria

- [ ] Dashboard CRUD works
- [ ] Widget CRUD works
- [ ] Layout updates persist
- [ ] Widget queries execute correctly
- [ ] Caching works
- [ ] Sharing works
- [ ] Global filters apply to all widgets
- [ ] Auto-refresh triggers correctly

## Reference Documents

- [Dashboard Agent](../agents/dashboard-agent.agent.md)
- [Semantic Layer API](./019-semantic-layer-api.md)
