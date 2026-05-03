"""
NovaSight Dashboard Service
============================

Business logic for dashboard and widget operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from flask import current_app
from sqlalchemy import and_, or_

from app.extensions import db
from app.domains.analytics.domain.models import Dashboard, Widget, WidgetType
from app.domains.analytics.application.dataset_service import (
    DatasetService,
    DatasetServiceError,
)

logger = logging.getLogger(__name__)


class DashboardServiceError(Exception):
    """Base exception for dashboard service errors."""
    pass


class DashboardNotFoundError(DashboardServiceError):
    """Raised when a dashboard is not found."""
    pass


class WidgetNotFoundError(DashboardServiceError):
    """Raised when a widget is not found."""
    pass


class DashboardAccessDeniedError(DashboardServiceError):
    """Raised when user doesn't have access to dashboard."""
    pass


class DashboardValidationError(DashboardServiceError):
    """Raised when dashboard data validation fails."""
    pass


class DashboardService:
    """
    Service for dashboard and widget operations.
    
    Provides methods for CRUD operations, sharing, layout management,
    and widget data execution through the configured Dataset.
    """
    
    # Default cache TTL for widget data (5 minutes)
    DEFAULT_CACHE_TTL_SECONDS = 300
    
    # ==========================================================================
    # Dashboard CRUD Operations
    # ==========================================================================
    
    @classmethod
    def list_for_user(
        cls,
        tenant_id: str,
        user_id: str,
        include_shared: bool = True,
        include_public: bool = True,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dashboard]:
        """
        List all accessible dashboards for a user.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            include_shared: Include dashboards shared with user
            include_public: Include public dashboards
            tags: Filter by tags
            search: Search in name/description
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            List of Dashboard instances
        """
        user_uuid = UUID(str(user_id))
        
        # Base query: owned dashboards
        conditions = [
            Dashboard.tenant_id == UUID(str(tenant_id)),
            Dashboard.is_deleted == False,
            Dashboard.created_by == user_uuid,
        ]
        
        # Build OR conditions for access
        access_conditions = [Dashboard.created_by == user_uuid]
        
        if include_shared:
            access_conditions.append(Dashboard.shared_with.contains([user_uuid]))
        
        if include_public:
            access_conditions.append(Dashboard.is_public == True)
        
        query = Dashboard.query.filter(
            Dashboard.tenant_id == UUID(str(tenant_id)),
            Dashboard.is_deleted == False,
            or_(*access_conditions)
        )
        
        # Apply tag filter
        if tags:
            for tag in tags:
                query = query.filter(Dashboard.tags.contains([tag]))
        
        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Dashboard.name.ilike(search_pattern),
                    Dashboard.description.ilike(search_pattern)
                )
            )
        
        # Order by most recently updated
        query = query.order_by(Dashboard.updated_at.desc())
        
        return query.offset(offset).limit(limit).all()
    
    @classmethod
    def get(
        cls,
        dashboard_id: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        check_access: bool = True,
    ) -> Dashboard:
        """
        Get a dashboard by ID.
        
        Args:
            dashboard_id: Dashboard identifier
            tenant_id: Tenant identifier
            user_id: User identifier (for access check)
            check_access: Whether to check user access
        
        Returns:
            Dashboard instance
        
        Raises:
            DashboardNotFoundError: If dashboard not found
            DashboardAccessDeniedError: If user doesn't have access
        """
        dashboard = Dashboard.query.filter(
            Dashboard.id == UUID(str(dashboard_id)),
            Dashboard.tenant_id == UUID(str(tenant_id)),
            Dashboard.is_deleted == False,
        ).first()
        
        if not dashboard:
            raise DashboardNotFoundError(f"Dashboard not found: {dashboard_id}")
        
        if check_access and user_id:
            if not dashboard.can_view(user_id):
                raise DashboardAccessDeniedError(
                    f"Access denied to dashboard: {dashboard_id}"
                )
        
        return dashboard
    
    @classmethod
    def create(
        cls,
        tenant_id: str,
        created_by: str,
        name: str,
        description: Optional[str] = None,
        layout: Optional[List[Dict]] = None,
        is_public: bool = False,
        global_filters: Optional[Dict] = None,
        auto_refresh: bool = False,
        refresh_interval: Optional[int] = None,
        theme: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ) -> Dashboard:
        """
        Create a new dashboard.
        
        Args:
            tenant_id: Tenant identifier
            created_by: Creator user ID
            name: Dashboard name
            description: Dashboard description
            layout: Initial layout configuration
            is_public: Public visibility flag
            global_filters: Global filter settings
            auto_refresh: Auto-refresh enabled
            refresh_interval: Refresh interval in seconds
            theme: Theme configuration
            tags: List of tags
        
        Returns:
            Created Dashboard instance
        """
        dashboard = Dashboard(
            id=uuid4(),
            tenant_id=UUID(str(tenant_id)),
            created_by=UUID(str(created_by)),
            name=name,
            description=description,
            layout=layout or [],
            is_public=is_public,
            shared_with=[],
            global_filters=global_filters or {},
            auto_refresh=auto_refresh,
            refresh_interval=refresh_interval,
            theme=theme or {},
            tags=tags or [],
        )
        
        db.session.add(dashboard)
        db.session.commit()
        
        logger.info(f"Created dashboard: {dashboard.id} for tenant {tenant_id}")
        return dashboard
    
    @classmethod
    def update(
        cls,
        dashboard_id: str,
        tenant_id: str,
        user_id: str,
        **updates,
    ) -> Dashboard:
        """
        Update a dashboard.
        
        Args:
            dashboard_id: Dashboard identifier
            tenant_id: Tenant identifier
            user_id: User identifier (for permission check)
            **updates: Fields to update
        
        Returns:
            Updated Dashboard instance
        """
        dashboard = cls.get(dashboard_id, tenant_id, user_id, check_access=False)
        
        if not dashboard.can_edit(user_id):
            raise DashboardAccessDeniedError(
                f"Cannot edit dashboard: {dashboard_id}"
            )
        
        allowed_fields = {
            'name', 'description', 'layout', 'is_public', 'global_filters',
            'auto_refresh', 'refresh_interval', 'theme', 'tags'
        }
        
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                setattr(dashboard, field, value)
        
        db.session.commit()
        
        logger.info(f"Updated dashboard: {dashboard_id}")
        return dashboard
    
    @classmethod
    def delete(
        cls,
        dashboard_id: str,
        tenant_id: str,
        user_id: str,
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete a dashboard.
        
        Args:
            dashboard_id: Dashboard identifier
            tenant_id: Tenant identifier
            user_id: User identifier (for permission check)
            soft_delete: Use soft delete (default: True)
        
        Returns:
            True if deleted successfully
        """
        dashboard = cls.get(dashboard_id, tenant_id, user_id, check_access=False)
        
        if not dashboard.can_edit(user_id):
            raise DashboardAccessDeniedError(
                f"Cannot delete dashboard: {dashboard_id}"
            )
        
        if soft_delete:
            dashboard.is_deleted = True
            dashboard.deleted_at = datetime.utcnow()
        else:
            db.session.delete(dashboard)
        
        db.session.commit()
        
        logger.info(f"Deleted dashboard: {dashboard_id}")
        return True
    
    @classmethod
    def clone(
        cls,
        dashboard_id: str,
        tenant_id: str,
        user_id: str,
        new_name: str,
        include_widgets: bool = True,
    ) -> Dashboard:
        """
        Clone a dashboard.
        
        Args:
            dashboard_id: Source dashboard ID
            tenant_id: Tenant identifier
            user_id: User identifier
            new_name: Name for the cloned dashboard
            include_widgets: Whether to clone widgets
        
        Returns:
            Cloned Dashboard instance
        """
        source = cls.get(dashboard_id, tenant_id, user_id)
        
        # Create new dashboard
        new_dashboard = Dashboard(
            id=uuid4(),
            tenant_id=source.tenant_id,
            created_by=UUID(str(user_id)),
            name=new_name,
            description=source.description,
            layout=[],
            is_public=False,  # Cloned dashboards are private
            shared_with=[],
            global_filters=source.global_filters.copy() if source.global_filters else {},
            auto_refresh=source.auto_refresh,
            refresh_interval=source.refresh_interval,
            theme=source.theme.copy() if source.theme else {},
            tags=source.tags.copy() if source.tags else [],
        )
        
        db.session.add(new_dashboard)
        
        if include_widgets:
            # Clone widgets and update layout
            new_layout = []
            for widget in source.widgets.all():
                new_widget = Widget(
                    id=uuid4(),
                    tenant_id=widget.tenant_id,
                    dashboard_id=new_dashboard.id,
                    name=widget.name,
                    description=widget.description,
                    type=widget.type,
                    query_config=widget.query_config.copy() if widget.query_config else {},
                    viz_config=widget.viz_config.copy() if widget.viz_config else {},
                    grid_position=widget.grid_position.copy() if widget.grid_position else {},
                    local_filters=widget.local_filters.copy() if widget.local_filters else {},
                    drilldown_config=widget.drilldown_config.copy() if widget.drilldown_config else None,
                )
                db.session.add(new_widget)
                
                # Add to layout with new widget ID
                new_layout.append({
                    'id': str(new_widget.id),
                    **new_widget.grid_position
                })
            
            new_dashboard.layout = new_layout
        
        db.session.commit()
        
        logger.info(f"Cloned dashboard {dashboard_id} to {new_dashboard.id}")
        return new_dashboard
    
    # ==========================================================================
    # Layout Operations
    # ==========================================================================
    
    @classmethod
    def update_layout(
        cls,
        dashboard_id: str,
        tenant_id: str,
        user_id: str,
        layout: List[Dict],
    ) -> Dashboard:
        """
        Update dashboard widget layout.
        
        Args:
            dashboard_id: Dashboard identifier
            tenant_id: Tenant identifier
            user_id: User identifier
            layout: New layout configuration
        
        Returns:
            Updated Dashboard instance
        """
        dashboard = cls.get(dashboard_id, tenant_id, user_id, check_access=False)
        
        if not dashboard.can_edit(user_id):
            raise DashboardAccessDeniedError(
                f"Cannot edit dashboard layout: {dashboard_id}"
            )
        
        # Update each widget's grid_position
        widget_ids = {str(w.id): w for w in dashboard.widgets.all()}
        
        for item in layout:
            widget_id = item.get('id')
            if widget_id and widget_id in widget_ids:
                widget = widget_ids[widget_id]
                widget.grid_position = {
                    'x': item['x'],
                    'y': item['y'],
                    'w': item['w'],
                    'h': item['h'],
                    'minW': item.get('minW', 1),
                    'minH': item.get('minH', 1),
                    'maxW': item.get('maxW'),
                    'maxH': item.get('maxH'),
                }
        
        dashboard.layout = layout
        db.session.commit()
        
        return dashboard
    
    # ==========================================================================
    # Sharing Operations
    # ==========================================================================
    
    @classmethod
    def share(
        cls,
        dashboard_id: str,
        tenant_id: str,
        user_id: str,
        target_user_ids: List[str],
    ) -> Dashboard:
        """
        Share dashboard with users.
        
        Args:
            dashboard_id: Dashboard identifier
            tenant_id: Tenant identifier
            user_id: Owner user ID
            target_user_ids: List of user IDs to share with
        
        Returns:
            Updated Dashboard instance
        """
        dashboard = cls.get(dashboard_id, tenant_id, user_id, check_access=False)
        
        if not dashboard.can_edit(user_id):
            raise DashboardAccessDeniedError(
                f"Cannot share dashboard: {dashboard_id}"
            )
        
        # Add new users to shared_with
        current_shared = set(dashboard.shared_with or [])
        for target_id in target_user_ids:
            current_shared.add(UUID(str(target_id)))
        
        dashboard.shared_with = list(current_shared)
        db.session.commit()
        
        logger.info(f"Shared dashboard {dashboard_id} with {len(target_user_ids)} users")
        return dashboard
    
    @classmethod
    def unshare(
        cls,
        dashboard_id: str,
        tenant_id: str,
        user_id: str,
        target_user_ids: List[str],
    ) -> Dashboard:
        """
        Remove sharing from users.
        
        Args:
            dashboard_id: Dashboard identifier
            tenant_id: Tenant identifier
            user_id: Owner user ID
            target_user_ids: List of user IDs to remove
        
        Returns:
            Updated Dashboard instance
        """
        dashboard = cls.get(dashboard_id, tenant_id, user_id, check_access=False)
        
        if not dashboard.can_edit(user_id):
            raise DashboardAccessDeniedError(
                f"Cannot modify dashboard sharing: {dashboard_id}"
            )
        
        # Remove users from shared_with
        remove_ids = {UUID(str(uid)) for uid in target_user_ids}
        current_shared = set(dashboard.shared_with or [])
        dashboard.shared_with = list(current_shared - remove_ids)
        
        db.session.commit()
        return dashboard
    
    # ==========================================================================
    # Widget CRUD Operations
    # ==========================================================================
    
    @classmethod
    def add_widget(
        cls,
        dashboard_id: str,
        tenant_id: str,
        user_id: str,
        name: str,
        type: str,
        query_config: Dict,
        grid_position: Dict,
        description: Optional[str] = None,
        viz_config: Optional[Dict] = None,
        local_filters: Optional[Dict] = None,
        drilldown_config: Optional[Dict] = None,
    ) -> Widget:
        """
        Add a widget to a dashboard.
        
        Args:
            dashboard_id: Dashboard identifier
            tenant_id: Tenant identifier
            user_id: User identifier
            name: Widget name
            type: Widget type
            query_config: Query configuration
            grid_position: Grid position
            description: Widget description
            viz_config: Visualization configuration
            local_filters: Widget-specific filters
            drilldown_config: Drilldown configuration
        
        Returns:
            Created Widget instance
        """
        dashboard = cls.get(dashboard_id, tenant_id, user_id, check_access=False)
        
        if not dashboard.can_edit(user_id):
            raise DashboardAccessDeniedError(
                f"Cannot add widget to dashboard: {dashboard_id}"
            )
        
        # Convert string type to enum
        widget_type = WidgetType(type) if isinstance(type, str) else type
        
        widget = Widget(
            id=uuid4(),
            tenant_id=dashboard.tenant_id,
            dashboard_id=dashboard.id,
            name=name,
            description=description,
            type=widget_type,
            query_config=query_config,
            viz_config=viz_config or {},
            grid_position=grid_position,
            local_filters=local_filters or {},
            drilldown_config=drilldown_config,
        )
        
        db.session.add(widget)
        
        # Update dashboard layout
        current_layout = dashboard.layout or []
        current_layout.append({
            'id': str(widget.id),
            **grid_position
        })
        dashboard.layout = current_layout
        
        db.session.commit()
        
        logger.info(f"Added widget {widget.id} to dashboard {dashboard_id}")
        return widget
    
    @classmethod
    def get_widget(
        cls,
        widget_id: str,
        tenant_id: str,
        user_id: Optional[str] = None,
    ) -> Widget:
        """
        Get a widget by ID.
        
        Args:
            widget_id: Widget identifier
            tenant_id: Tenant identifier
            user_id: User identifier (for access check)
        
        Returns:
            Widget instance
        """
        widget = Widget.query.filter(
            Widget.id == UUID(str(widget_id)),
            Widget.tenant_id == UUID(str(tenant_id)),
        ).first()
        
        if not widget:
            raise WidgetNotFoundError(f"Widget not found: {widget_id}")
        
        # Check dashboard access
        if user_id:
            dashboard = widget.dashboard
            if not dashboard.can_view(user_id):
                raise DashboardAccessDeniedError(
                    f"Access denied to widget: {widget_id}"
                )
        
        return widget
    
    @classmethod
    def update_widget(
        cls,
        widget_id: str,
        tenant_id: str,
        user_id: str,
        **updates,
    ) -> Widget:
        """
        Update a widget.
        
        Args:
            widget_id: Widget identifier
            tenant_id: Tenant identifier
            user_id: User identifier
            **updates: Fields to update
        
        Returns:
            Updated Widget instance
        """
        widget = cls.get_widget(widget_id, tenant_id, user_id)
        
        if not widget.dashboard.can_edit(user_id):
            raise DashboardAccessDeniedError(
                f"Cannot edit widget: {widget_id}"
            )
        
        allowed_fields = {
            'name', 'description', 'type', 'query_config', 'viz_config',
            'grid_position', 'local_filters', 'drilldown_config'
        }
        
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                if field == 'type' and isinstance(value, str):
                    value = WidgetType(value)
                setattr(widget, field, value)
        
        # Invalidate cache on update
        widget.cached_data = None
        widget.cache_expires_at = None
        
        db.session.commit()
        
        logger.info(f"Updated widget: {widget_id}")
        return widget
    
    @classmethod
    def delete_widget(
        cls,
        widget_id: str,
        dashboard_id: str,
        tenant_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a widget from a dashboard.
        
        Args:
            widget_id: Widget identifier
            dashboard_id: Dashboard identifier
            tenant_id: Tenant identifier
            user_id: User identifier
        
        Returns:
            True if deleted successfully
        """
        widget = cls.get_widget(widget_id, tenant_id, user_id)
        
        if str(widget.dashboard_id) != str(dashboard_id):
            raise DashboardValidationError(
                f"Widget {widget_id} does not belong to dashboard {dashboard_id}"
            )
        
        if not widget.dashboard.can_edit(user_id):
            raise DashboardAccessDeniedError(
                f"Cannot delete widget: {widget_id}"
            )
        
        # Remove from dashboard layout
        dashboard = widget.dashboard
        dashboard.layout = [
            item for item in (dashboard.layout or [])
            if item.get('id') != str(widget_id)
        ]
        
        db.session.delete(widget)
        db.session.commit()
        
        logger.info(f"Deleted widget: {widget_id}")
        return True
    
    # ==========================================================================
    # Widget Data Execution
    # ==========================================================================
    
    @classmethod
    def execute_widget_query(
        cls,
        widget: Widget,
        tenant_id: str,
        filter_overrides: Optional[List[Dict]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute widget query and optionally cache results.
        
        Args:
            widget: Widget instance
            tenant_id: Tenant identifier
            filter_overrides: Optional filter overrides
            use_cache: Whether to use cache
        
        Returns:
            Query results dictionary
        """
        # Check cache first
        if use_cache and widget.is_cache_valid():
            return {
                **widget.cached_data,
                'cached': True,
            }
        
        config = widget.query_config
        
        # Merge filters: global + local + overrides
        filters = []
        
        # Add widget's local filters
        if widget.local_filters:
            for key, value in widget.local_filters.items():
                if isinstance(value, list):
                    filters.append({'field': key, 'operator': 'in', 'values': value})
                else:
                    filters.append({'field': key, 'operator': 'eq', 'value': value})
        
        # Add query config filters
        if config.get('filters'):
            filters.extend(config['filters'])
        
        # Add filter overrides
        if filter_overrides:
            filters.extend(filter_overrides)
        
        # Execute through Dataset (canonical mart-backed source).
        if not widget.dataset_id:
            raise DashboardServiceError(
                "Widget has no dataset configured; assign a dataset to enable execution."
            )
        try:
            res = DatasetService.execute_preview(
                tenant_id=tenant_id,
                dataset_id=str(widget.dataset_id),
                limit=config.get('limit', 1000),
            )
        except DatasetServiceError as e:
            logger.error(f"Widget query failed: {e}")
            raise DashboardServiceError(f"Widget query execution failed: {e}")

        # Normalise to {data, columns, row_count} shape.
        col_meta = res.get("columns", [])
        col_names = [c["name"] for c in col_meta]
        rows = [dict(zip(col_names, r)) for r in res.get("rows", [])]
        result = {
            "data": rows,
            "columns": col_meta,
            "row_count": len(rows),
        }
        
        # Cache results
        cache_ttl = current_app.config.get(
            'WIDGET_CACHE_TTL_SECONDS',
            cls.DEFAULT_CACHE_TTL_SECONDS
        )
        
        widget.cached_data = result
        widget.cache_expires_at = datetime.utcnow() + timedelta(seconds=cache_ttl)
        db.session.commit()
        
        return {
            **result,
            'cached': False,
        }
    
    @classmethod
    def refresh_widget_cache(
        cls,
        widget_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Force refresh widget cache.
        
        Args:
            widget_id: Widget identifier
            tenant_id: Tenant identifier
            user_id: User identifier
        
        Returns:
            Fresh query results
        """
        widget = cls.get_widget(widget_id, tenant_id, user_id)
        
        # Clear existing cache
        widget.cached_data = None
        widget.cache_expires_at = None
        
        # Execute fresh query
        return cls.execute_widget_query(widget, tenant_id, use_cache=False)
    
    @classmethod
    def refresh_all_widgets(
        cls,
        dashboard_id: str,
        tenant_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Refresh all widget caches for a dashboard.
        
        Args:
            dashboard_id: Dashboard identifier
            tenant_id: Tenant identifier
            user_id: User identifier
        
        Returns:
            Summary of refresh results
        """
        dashboard = cls.get(dashboard_id, tenant_id, user_id)
        
        results = {
            'dashboard_id': str(dashboard_id),
            'widgets_refreshed': 0,
            'widgets_failed': 0,
            'errors': [],
        }
        
        for widget in dashboard.widgets.all():
            try:
                cls.refresh_widget_cache(str(widget.id), tenant_id, user_id)
                results['widgets_refreshed'] += 1
            except Exception as e:
                results['widgets_failed'] += 1
                results['errors'].append({
                    'widget_id': str(widget.id),
                    'error': str(e),
                })
                logger.error(f"Failed to refresh widget {widget.id}: {e}")
        
        return results
    
    # ==========================================================================
    # Statistics
    # ==========================================================================
    
    @classmethod
    def get_dashboard_stats(
        cls,
        tenant_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Get dashboard statistics for a user.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
        
        Returns:
            Statistics dictionary
        """
        user_uuid = UUID(str(user_id))
        tenant_uuid = UUID(str(tenant_id))
        
        # Count owned dashboards
        owned_count = Dashboard.query.filter(
            Dashboard.tenant_id == tenant_uuid,
            Dashboard.created_by == user_uuid,
            Dashboard.is_deleted == False,
        ).count()
        
        # Count shared with user
        shared_count = Dashboard.query.filter(
            Dashboard.tenant_id == tenant_uuid,
            Dashboard.shared_with.contains([user_uuid]),
            Dashboard.is_deleted == False,
        ).count()
        
        # Count public dashboards
        public_count = Dashboard.query.filter(
            Dashboard.tenant_id == tenant_uuid,
            Dashboard.is_public == True,
            Dashboard.is_deleted == False,
        ).count()
        
        # Total widgets owned
        widget_count = Widget.query.join(Dashboard).filter(
            Dashboard.tenant_id == tenant_uuid,
            Dashboard.created_by == user_uuid,
            Dashboard.is_deleted == False,
        ).count()
        
        return {
            'owned_dashboards': owned_count,
            'shared_dashboards': shared_count,
            'public_dashboards': public_count,
            'total_widgets': widget_count,
        }
