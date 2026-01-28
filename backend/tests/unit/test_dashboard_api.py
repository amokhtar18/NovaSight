"""
Unit Tests for NovaSight Dashboard API
=======================================

Tests for dashboards, widgets, and dashboard service operations.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.dashboard import Dashboard, Widget, WidgetType
from app.schemas.dashboard_schemas import (
    DashboardCreateSchema,
    DashboardUpdateSchema,
    DashboardLayoutUpdateSchema,
    DashboardShareSchema,
    DashboardCloneSchema,
    WidgetCreateSchema,
    WidgetUpdateSchema,
    WidgetQueryConfigSchema,
    GridPositionSchema,
    WidgetVizConfigSchema,
    WidgetTypeEnum,
    FilterOperatorEnum,
    QueryFilterSchema,
    QueryOrderBySchema,
)


class TestDashboardSchemas:
    """Tests for dashboard Pydantic schemas."""
    
    def test_dashboard_create_schema_valid(self):
        """Test valid dashboard creation."""
        data = DashboardCreateSchema(
            name="Sales Dashboard",
            description="Main sales overview dashboard",
            is_public=False,
            auto_refresh=True,
            refresh_interval=60,
            tags=["sales", "kpi"],
        )
        
        assert data.name == "Sales Dashboard"
        assert data.is_public is False
        assert data.auto_refresh is True
        assert data.refresh_interval == 60
        assert "sales" in data.tags
    
    def test_dashboard_create_schema_minimal(self):
        """Test minimal dashboard creation."""
        data = DashboardCreateSchema(name="Test Dashboard")
        
        assert data.name == "Test Dashboard"
        assert data.is_public is False
        assert data.auto_refresh is False
        assert data.layout == []
    
    def test_dashboard_name_validation(self):
        """Test name validation rules."""
        # Valid names
        DashboardCreateSchema(name="Sales Dashboard")
        DashboardCreateSchema(name="Q1-2024_Report")
        DashboardCreateSchema(name="Dashboard.v2")
        
        # Invalid: special characters
        with pytest.raises(ValueError):
            DashboardCreateSchema(name="Sales @Dashboard!")
    
    def test_dashboard_refresh_interval_required_when_auto_refresh(self):
        """Test refresh_interval is required when auto_refresh is enabled."""
        with pytest.raises(ValueError):
            DashboardCreateSchema(
                name="Test",
                auto_refresh=True,
                # Missing refresh_interval
            )
    
    def test_dashboard_tags_validation(self):
        """Test tag format validation."""
        # Valid tags
        data = DashboardCreateSchema(
            name="Test",
            tags=["sales", "kpi-2024", "important_dashboard"],
        )
        assert len(data.tags) == 3
        
        # Invalid: special characters
        with pytest.raises(ValueError):
            DashboardCreateSchema(
                name="Test",
                tags=["sales@2024"],
            )
    
    def test_dashboard_layout_update_schema(self):
        """Test layout update schema validation."""
        data = DashboardLayoutUpdateSchema(
            layout=[
                {"id": str(uuid4()), "x": 0, "y": 0, "w": 6, "h": 4},
                {"id": str(uuid4()), "x": 6, "y": 0, "w": 6, "h": 4},
            ]
        )
        
        assert len(data.layout) == 2
        
        # Invalid: missing required field
        with pytest.raises(ValueError):
            DashboardLayoutUpdateSchema(
                layout=[
                    {"id": str(uuid4()), "x": 0, "y": 0}  # Missing w, h
                ]
            )
    
    def test_dashboard_share_schema(self):
        """Test share schema validation."""
        user_ids = [uuid4(), uuid4()]
        data = DashboardShareSchema(user_ids=user_ids)
        
        assert len(data.user_ids) == 2
        
        # Invalid: duplicate user IDs
        with pytest.raises(ValueError):
            uid = uuid4()
            DashboardShareSchema(user_ids=[uid, uid])
        
        # Invalid: empty list
        with pytest.raises(ValueError):
            DashboardShareSchema(user_ids=[])


class TestWidgetSchemas:
    """Tests for widget Pydantic schemas."""
    
    def test_widget_create_schema_valid(self):
        """Test valid widget creation."""
        data = WidgetCreateSchema(
            name="Sales by Region",
            type=WidgetTypeEnum.BAR_CHART,
            query_config=WidgetQueryConfigSchema(
                dimensions=["region"],
                measures=["total_sales"],
                limit=100,
            ),
            grid_position=GridPositionSchema(x=0, y=0, w=6, h=4),
        )
        
        assert data.name == "Sales by Region"
        assert data.type == WidgetTypeEnum.BAR_CHART
        assert "region" in data.query_config.dimensions
        assert "total_sales" in data.query_config.measures
    
    def test_widget_query_config_validation(self):
        """Test query config validation."""
        # Valid config
        config = WidgetQueryConfigSchema(
            dimensions=["date", "category"],
            measures=["sales_amount", "order_count"],
            filters=[
                QueryFilterSchema(
                    field="status",
                    operator=FilterOperatorEnum.EQUALS,
                    value="completed"
                )
            ],
            order_by=[
                QueryOrderBySchema(field="date", direction="desc")
            ],
            limit=500,
        )
        
        assert len(config.dimensions) == 2
        assert len(config.measures) == 2
        assert config.limit == 500
        
        # Invalid: no measures
        with pytest.raises(ValueError):
            WidgetQueryConfigSchema(
                dimensions=["region"],
                measures=[],  # At least one measure required
            )
        
        # Invalid: invalid field name format
        with pytest.raises(ValueError):
            WidgetQueryConfigSchema(
                dimensions=["123invalid"],
                measures=["total"],
            )
    
    def test_widget_grid_position_bounds(self):
        """Test grid position boundary validation."""
        # Valid positions
        GridPositionSchema(x=0, y=0, w=6, h=4)
        GridPositionSchema(x=18, y=100, w=6, h=10)
        
        # Invalid: out of bounds
        with pytest.raises(ValueError):
            GridPositionSchema(x=-1, y=0, w=6, h=4)
        
        with pytest.raises(ValueError):
            GridPositionSchema(x=0, y=0, w=25, h=4)  # w > 24
    
    def test_widget_viz_config(self):
        """Test visualization config options."""
        config = WidgetVizConfigSchema(
            colors=["#3B82F6", "#10B981"],
            showLegend=True,
            legendPosition="bottom",
            xAxisLabel="Date",
            yAxisLabel="Sales ($)",
            stacked=True,
        )
        
        assert len(config.colors) == 2
        assert config.showLegend is True
        assert config.stacked is True
    
    def test_widget_types(self):
        """Test all widget types are valid."""
        for widget_type in WidgetTypeEnum:
            data = WidgetCreateSchema(
                name=f"Test {widget_type.value}",
                type=widget_type,
                query_config=WidgetQueryConfigSchema(
                    measures=["count"],
                ),
                grid_position=GridPositionSchema(x=0, y=0, w=4, h=3),
            )
            assert data.type == widget_type


class TestDashboardModel:
    """Tests for Dashboard model methods."""
    
    def test_dashboard_to_dict(self):
        """Test dashboard serialization."""
        dashboard = Dashboard(
            id=uuid4(),
            tenant_id=uuid4(),
            created_by=uuid4(),
            name="Test Dashboard",
            description="Test description",
            layout=[{"id": "w1", "x": 0, "y": 0, "w": 6, "h": 4}],
            is_public=False,
            shared_with=[],
            global_filters={"date_range": "last_30_days"},
            auto_refresh=True,
            refresh_interval=60,
            theme={"dark_mode": False},
            tags=["test"],
        )
        dashboard.created_at = datetime.utcnow()
        dashboard.updated_at = datetime.utcnow()
        
        # Mock the widgets relationship
        mock_widgets = MagicMock()
        mock_widgets.count.return_value = 2
        mock_widgets.all.return_value = []
        
        with patch.object(Dashboard, 'widgets', mock_widgets):
            result = dashboard.to_dict(include_widgets=False)
        
        assert result["name"] == "Test Dashboard"
        assert result["is_public"] is False
        assert result["auto_refresh"] is True
        assert result["widget_count"] == 2
        assert "test" in result["tags"]
    
    def test_dashboard_can_view(self):
        """Test view permission checks."""
        owner_id = uuid4()
        viewer_id = uuid4()
        other_id = uuid4()
        
        dashboard = Dashboard(
            id=uuid4(),
            created_by=owner_id,
            is_public=False,
            shared_with=[viewer_id],
        )
        
        # Owner can view
        assert dashboard.can_view(str(owner_id)) is True
        
        # Shared user can view
        assert dashboard.can_view(str(viewer_id)) is True
        
        # Other users cannot view private dashboard
        assert dashboard.can_view(str(other_id)) is False
        
        # Anyone can view public dashboard
        dashboard.is_public = True
        assert dashboard.can_view(str(other_id)) is True
    
    def test_dashboard_can_edit(self):
        """Test edit permission checks."""
        owner_id = uuid4()
        viewer_id = uuid4()
        
        dashboard = Dashboard(
            id=uuid4(),
            created_by=owner_id,
            shared_with=[viewer_id],
        )
        
        # Only owner can edit
        assert dashboard.can_edit(str(owner_id)) is True
        assert dashboard.can_edit(str(viewer_id)) is False


class TestWidgetModel:
    """Tests for Widget model methods."""
    
    def test_widget_to_dict(self):
        """Test widget serialization."""
        widget = Widget(
            id=uuid4(),
            dashboard_id=uuid4(),
            tenant_id=uuid4(),
            name="Sales Chart",
            type=WidgetType.BAR_CHART,
            query_config={
                "dimensions": ["region"],
                "measures": ["total_sales"],
            },
            viz_config={"showLegend": True},
            grid_position={"x": 0, "y": 0, "w": 6, "h": 4},
        )
        widget.created_at = datetime.utcnow()
        widget.updated_at = datetime.utcnow()
        
        result = widget.to_dict()
        
        assert result["name"] == "Sales Chart"
        assert result["type"] == "bar_chart"
        assert "dimensions" in result["query_config"]
    
    def test_widget_cache_validity(self):
        """Test cache validity checking."""
        widget = Widget(
            id=uuid4(),
            dashboard_id=uuid4(),
            tenant_id=uuid4(),
            name="Test",
            type=WidgetType.TABLE,
            query_config={"measures": ["count"]},
            grid_position={"x": 0, "y": 0, "w": 4, "h": 3},
        )
        
        # No cache
        widget.cached_data = None
        widget.cache_expires_at = None
        assert widget.is_cache_valid() is False
        
        # Expired cache
        widget.cached_data = {"rows": []}
        widget.cache_expires_at = datetime.utcnow() - timedelta(minutes=1)
        assert widget.is_cache_valid() is False
        
        # Valid cache
        widget.cache_expires_at = datetime.utcnow() + timedelta(minutes=5)
        assert widget.is_cache_valid() is True


class TestDashboardService:
    """Tests for DashboardService methods."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        with patch('app.services.dashboard_service.db.session') as mock:
            yield mock
    
    @pytest.fixture
    def sample_dashboard(self):
        """Create a sample dashboard for testing."""
        dashboard = Dashboard(
            id=uuid4(),
            tenant_id=uuid4(),
            created_by=uuid4(),
            name="Test Dashboard",
            is_public=False,
            shared_with=[],
            layout=[],
            global_filters={},
            auto_refresh=False,
            theme={},
            tags=[],
            is_deleted=False,
        )
        dashboard.created_at = datetime.utcnow()
        dashboard.updated_at = datetime.utcnow()
        return dashboard
    
    @pytest.fixture
    def sample_widget(self, sample_dashboard):
        """Create a sample widget for testing."""
        widget = Widget(
            id=uuid4(),
            dashboard_id=sample_dashboard.id,
            tenant_id=sample_dashboard.tenant_id,
            name="Test Widget",
            type=WidgetType.BAR_CHART,
            query_config={
                "dimensions": ["date"],
                "measures": ["total_sales"],
            },
            viz_config={},
            grid_position={"x": 0, "y": 0, "w": 6, "h": 4},
        )
        widget.created_at = datetime.utcnow()
        widget.updated_at = datetime.utcnow()
        return widget
    
    def test_list_for_user_basic(self, mock_db_session):
        """Test listing dashboards for a user."""
        from app.services.dashboard_service import DashboardService
        
        tenant_id = str(uuid4())
        user_id = str(uuid4())
        
        with patch.object(Dashboard, 'query') as mock_query:
            mock_query.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
            
            result = DashboardService.list_for_user(
                tenant_id=tenant_id,
                user_id=user_id,
            )
            
            assert result == []
    
    def test_create_dashboard(self, mock_db_session):
        """Test dashboard creation."""
        from app.services.dashboard_service import DashboardService
        
        tenant_id = str(uuid4())
        user_id = str(uuid4())
        
        dashboard = DashboardService.create(
            tenant_id=tenant_id,
            created_by=user_id,
            name="New Dashboard",
            description="Test description",
            is_public=False,
        )
        
        assert dashboard.name == "New Dashboard"
        assert str(dashboard.tenant_id) == tenant_id
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
    
    def test_get_dashboard_not_found(self, mock_db_session):
        """Test getting non-existent dashboard."""
        from app.services.dashboard_service import (
            DashboardService, DashboardNotFoundError
        )
        
        with patch.object(Dashboard, 'query') as mock_query:
            mock_query.filter.return_value.first.return_value = None
            
            with pytest.raises(DashboardNotFoundError):
                DashboardService.get(
                    dashboard_id=str(uuid4()),
                    tenant_id=str(uuid4()),
                )
    
    def test_get_dashboard_access_denied(self, mock_db_session, sample_dashboard):
        """Test access control for private dashboards."""
        from app.services.dashboard_service import (
            DashboardService, DashboardAccessDeniedError
        )
        
        other_user_id = str(uuid4())
        
        with patch.object(Dashboard, 'query') as mock_query:
            mock_query.filter.return_value.first.return_value = sample_dashboard
            
            with pytest.raises(DashboardAccessDeniedError):
                DashboardService.get(
                    dashboard_id=str(sample_dashboard.id),
                    tenant_id=str(sample_dashboard.tenant_id),
                    user_id=other_user_id,
                    check_access=True,
                )
    
    def test_update_dashboard(self, mock_db_session, sample_dashboard):
        """Test dashboard update."""
        from app.services.dashboard_service import DashboardService
        
        owner_id = str(sample_dashboard.created_by)
        
        with patch.object(Dashboard, 'query') as mock_query:
            mock_query.filter.return_value.first.return_value = sample_dashboard
            
            updated = DashboardService.update(
                dashboard_id=str(sample_dashboard.id),
                tenant_id=str(sample_dashboard.tenant_id),
                user_id=owner_id,
                name="Updated Name",
                is_public=True,
            )
            
            assert updated.name == "Updated Name"
            assert updated.is_public is True
            mock_db_session.commit.assert_called()
    
    def test_delete_dashboard_soft(self, mock_db_session, sample_dashboard):
        """Test soft delete of dashboard."""
        from app.services.dashboard_service import DashboardService
        
        owner_id = str(sample_dashboard.created_by)
        
        with patch.object(Dashboard, 'query') as mock_query:
            mock_query.filter.return_value.first.return_value = sample_dashboard
            
            result = DashboardService.delete(
                dashboard_id=str(sample_dashboard.id),
                tenant_id=str(sample_dashboard.tenant_id),
                user_id=owner_id,
                soft_delete=True,
            )
            
            assert result is True
            assert sample_dashboard.is_deleted is True
            assert sample_dashboard.deleted_at is not None
    
    def test_share_dashboard(self, mock_db_session, sample_dashboard):
        """Test sharing dashboard with users."""
        from app.services.dashboard_service import DashboardService
        
        owner_id = str(sample_dashboard.created_by)
        target_users = [str(uuid4()), str(uuid4())]
        
        with patch.object(Dashboard, 'query') as mock_query:
            mock_query.filter.return_value.first.return_value = sample_dashboard
            
            updated = DashboardService.share(
                dashboard_id=str(sample_dashboard.id),
                tenant_id=str(sample_dashboard.tenant_id),
                user_id=owner_id,
                target_user_ids=target_users,
            )
            
            assert len(updated.shared_with) == 2
    
    def test_update_layout(self, mock_db_session, sample_dashboard, sample_widget):
        """Test updating dashboard layout."""
        from app.services.dashboard_service import DashboardService
        
        owner_id = str(sample_dashboard.created_by)
        
        # Mock widgets
        mock_widgets = MagicMock()
        mock_widgets.all.return_value = [sample_widget]
        sample_dashboard.widgets = mock_widgets
        
        new_layout = [
            {"id": str(sample_widget.id), "x": 2, "y": 1, "w": 8, "h": 6}
        ]
        
        with patch.object(Dashboard, 'query') as mock_query:
            mock_query.filter.return_value.first.return_value = sample_dashboard
            
            updated = DashboardService.update_layout(
                dashboard_id=str(sample_dashboard.id),
                tenant_id=str(sample_dashboard.tenant_id),
                user_id=owner_id,
                layout=new_layout,
            )
            
            assert updated.layout == new_layout
            assert sample_widget.grid_position["x"] == 2
            assert sample_widget.grid_position["w"] == 8


class TestWidgetDataExecution:
    """Tests for widget query execution."""
    
    @pytest.fixture
    def mock_semantic_service(self):
        """Mock semantic service."""
        with patch('app.services.dashboard_service.SemanticService') as mock:
            mock.execute_query.return_value = {
                "columns": ["region", "total_sales"],
                "rows": [["East", 10000], ["West", 15000]],
                "row_count": 2,
                "execution_time_ms": 50,
            }
            yield mock
    
    @pytest.fixture
    def mock_current_app(self):
        """Mock Flask current_app."""
        with patch('app.services.dashboard_service.current_app') as mock:
            mock.config.get.return_value = 300  # Cache TTL
            yield mock
    
    def test_execute_widget_query_cached(self, mock_semantic_service):
        """Test that cached data is returned when valid."""
        from app.services.dashboard_service import DashboardService
        
        widget = Widget(
            id=uuid4(),
            dashboard_id=uuid4(),
            tenant_id=uuid4(),
            name="Test",
            type=WidgetType.BAR_CHART,
            query_config={"measures": ["total"]},
            grid_position={"x": 0, "y": 0, "w": 4, "h": 3},
            cached_data={"rows": [[100]]},
            cache_expires_at=datetime.utcnow() + timedelta(minutes=5),
            local_filters={},
        )
        
        result = DashboardService.execute_widget_query(
            widget=widget,
            tenant_id=str(widget.tenant_id),
            use_cache=True,
        )
        
        assert result["cached"] is True
        assert result["rows"] == [[100]]
        mock_semantic_service.execute_query.assert_not_called()
    
    def test_execute_widget_query_fresh(
        self, mock_semantic_service, mock_current_app
    ):
        """Test fresh query execution."""
        from app.services.dashboard_service import DashboardService
        
        widget = Widget(
            id=uuid4(),
            dashboard_id=uuid4(),
            tenant_id=uuid4(),
            name="Test",
            type=WidgetType.BAR_CHART,
            query_config={
                "dimensions": ["region"],
                "measures": ["total_sales"],
                "limit": 100,
            },
            grid_position={"x": 0, "y": 0, "w": 4, "h": 3},
            local_filters={},
        )
        
        with patch('app.services.dashboard_service.db.session'):
            result = DashboardService.execute_widget_query(
                widget=widget,
                tenant_id=str(widget.tenant_id),
                use_cache=False,
            )
        
        assert result["cached"] is False
        assert result["row_count"] == 2
        mock_semantic_service.execute_query.assert_called_once()
