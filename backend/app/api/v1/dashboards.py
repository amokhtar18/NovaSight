"""
NovaSight Dashboard API
========================

REST API endpoints for dashboard and widget management.
"""

from flask import request, g, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
import logging

from app.api.v1 import api_v1_bp
from app.decorators import require_tenant_context
from app.middleware.permissions import require_permission
from app.schemas.dashboard_schemas import (
    DashboardCreateSchema,
    DashboardUpdateSchema,
    DashboardLayoutUpdateSchema,
    DashboardShareSchema,
    DashboardCloneSchema,
    WidgetCreateSchema,
    WidgetUpdateSchema,
    WidgetDataRequestSchema,
)
from app.services.dashboard_service import (
    DashboardService,
    DashboardServiceError,
    DashboardNotFoundError,
    WidgetNotFoundError,
    DashboardAccessDeniedError,
    DashboardValidationError,
)

logger = logging.getLogger(__name__)


def get_tenant_id():
    """Get tenant ID from JWT identity."""
    identity = get_jwt_identity()
    return identity.get("tenant_id")


def get_user_id():
    """Get user ID from JWT identity."""
    identity = get_jwt_identity()
    return identity.get("user_id")


# =============================================================================
# Dashboard CRUD Endpoints
# =============================================================================

@api_v1_bp.route('/dashboards', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:view')
def list_dashboards():
    """
    List all accessible dashboards.
    
    Query Parameters:
        include_shared: Include shared dashboards (default: true)
        include_public: Include public dashboards (default: true)
        tags: Filter by tags (comma-separated)
        search: Search in name/description
        limit: Maximum results (default: 50)
        offset: Pagination offset (default: 0)
    
    Returns:
        List of dashboard summaries
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    include_shared = request.args.get('include_shared', 'true').lower() == 'true'
    include_public = request.args.get('include_public', 'true').lower() == 'true'
    tags = request.args.get('tags', '').split(',') if request.args.get('tags') else None
    search = request.args.get('search')
    limit = min(int(request.args.get('limit', 50)), 100)
    offset = int(request.args.get('offset', 0))
    
    try:
        dashboards = DashboardService.list_for_user(
            tenant_id=tenant_id,
            user_id=user_id,
            include_shared=include_shared,
            include_public=include_public,
            tags=tags,
            search=search,
            limit=limit,
            offset=offset,
        )
        
        result = [d.to_dict(include_widgets=False) for d in dashboards]
        return jsonify(result)
    
    except DashboardServiceError as e:
        logger.error(f"Error listing dashboards: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:create')
def create_dashboard():
    """
    Create a new dashboard.
    
    Request Body:
        name: Dashboard name (required)
        description: Dashboard description
        layout: Initial layout configuration
        is_public: Public visibility (default: false)
        global_filters: Global filter settings
        auto_refresh: Enable auto-refresh (default: false)
        refresh_interval: Refresh interval in seconds
        theme: Theme configuration
        tags: List of tags
    
    Returns:
        Created dashboard
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = DashboardCreateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        dashboard = DashboardService.create(
            tenant_id=tenant_id,
            created_by=user_id,
            name=data.name,
            description=data.description,
            layout=data.layout,
            is_public=data.is_public,
            global_filters=data.global_filters,
            auto_refresh=data.auto_refresh,
            refresh_interval=data.refresh_interval,
            theme=data.theme.dict() if data.theme else None,
            tags=data.tags,
        )
        
        return jsonify(dashboard.to_dict(include_widgets=True)), 201
    
    except DashboardServiceError as e:
        logger.error(f"Error creating dashboard: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:view')
def get_dashboard(dashboard_id):
    """
    Get a dashboard with all widgets.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
    
    Returns:
        Dashboard with widgets
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        dashboard = DashboardService.get(
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        return jsonify(dashboard.to_dict(include_widgets=True))
    
    except DashboardNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error getting dashboard: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>', methods=['PUT'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:edit')
def update_dashboard(dashboard_id):
    """
    Update a dashboard.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
    
    Request Body:
        name: Dashboard name
        description: Dashboard description
        is_public: Public visibility
        global_filters: Global filter settings
        auto_refresh: Enable auto-refresh
        refresh_interval: Refresh interval in seconds
        theme: Theme configuration
        tags: List of tags
    
    Returns:
        Updated dashboard
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = DashboardUpdateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        # Filter out None values
        updates = {k: v for k, v in data.dict().items() if v is not None}
        if 'theme' in updates and updates['theme']:
            updates['theme'] = updates['theme']
        
        dashboard = DashboardService.update(
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
            **updates,
        )
        
        return jsonify(dashboard.to_dict(include_widgets=True))
    
    except DashboardNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error updating dashboard: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>', methods=['DELETE'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:delete')
def delete_dashboard(dashboard_id):
    """
    Delete a dashboard.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
    
    Query Parameters:
        hard: Perform hard delete (default: false)
    
    Returns:
        Success message
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    hard_delete = request.args.get('hard', 'false').lower() == 'true'
    
    try:
        DashboardService.delete(
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
            soft_delete=not hard_delete,
        )
        
        return jsonify({"success": True, "message": "Dashboard deleted"})
    
    except DashboardNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error deleting dashboard: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/clone', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:create')
def clone_dashboard(dashboard_id):
    """
    Clone a dashboard.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
    
    Request Body:
        name: Name for the cloned dashboard
        include_widgets: Include widgets in clone (default: true)
    
    Returns:
        Cloned dashboard
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = DashboardCloneSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        dashboard = DashboardService.clone(
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
            new_name=data.name,
            include_widgets=data.include_widgets,
        )
        
        return jsonify(dashboard.to_dict(include_widgets=True)), 201
    
    except DashboardNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error cloning dashboard: {e}")
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Layout Endpoints
# =============================================================================

@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/layout', methods=['PUT'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:edit')
def update_dashboard_layout(dashboard_id):
    """
    Update dashboard widget layout.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
    
    Request Body:
        layout: Array of widget positions
            [{ id, x, y, w, h, minW?, minH?, maxW?, maxH? }, ...]
    
    Returns:
        Success message
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = DashboardLayoutUpdateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        DashboardService.update_layout(
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
            layout=data.layout,
        )
        
        return jsonify({"success": True})
    
    except DashboardNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error updating layout: {e}")
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Sharing Endpoints
# =============================================================================

@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/share', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:share')
def share_dashboard(dashboard_id):
    """
    Share dashboard with users.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
    
    Request Body:
        user_ids: Array of user UUIDs to share with
    
    Returns:
        Updated dashboard
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = DashboardShareSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        dashboard = DashboardService.share(
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
            target_user_ids=[str(uid) for uid in data.user_ids],
        )
        
        return jsonify({"success": True, "shared_with": dashboard.to_dict()['shared_with']})
    
    except DashboardNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error sharing dashboard: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/unshare', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:share')
def unshare_dashboard(dashboard_id):
    """
    Remove dashboard sharing from users.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
    
    Request Body:
        user_ids: Array of user UUIDs to remove
    
    Returns:
        Success message
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = DashboardShareSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        dashboard = DashboardService.unshare(
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
            target_user_ids=[str(uid) for uid in data.user_ids],
        )
        
        return jsonify({"success": True, "shared_with": dashboard.to_dict()['shared_with']})
    
    except DashboardNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error unsharing dashboard: {e}")
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Widget CRUD Endpoints
# =============================================================================

@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/widgets', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:edit')
def add_widget(dashboard_id):
    """
    Add a widget to a dashboard.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
    
    Request Body:
        name: Widget name (required)
        type: Widget type (required)
        query_config: Query configuration (required)
        grid_position: Grid position (required)
        description: Widget description
        viz_config: Visualization configuration
        local_filters: Widget-specific filters
        drilldown_config: Drilldown configuration
    
    Returns:
        Created widget
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = WidgetCreateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        widget = DashboardService.add_widget(
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
            name=data.name,
            description=data.description,
            type=data.type.value,
            query_config=data.query_config.dict(),
            viz_config=data.viz_config.dict() if data.viz_config else {},
            grid_position=data.grid_position.dict(),
            local_filters=data.local_filters,
            drilldown_config=data.drilldown_config.dict() if data.drilldown_config else None,
        )
        
        return jsonify(widget.to_dict()), 201
    
    except DashboardNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error adding widget: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/widgets/<uuid:widget_id>', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:view')
def get_widget(dashboard_id, widget_id):
    """
    Get a widget by ID.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
        widget_id: Widget UUID
    
    Returns:
        Widget details
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        widget = DashboardService.get_widget(
            widget_id=str(widget_id),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        if str(widget.dashboard_id) != str(dashboard_id):
            return jsonify({"error": "Widget not found in this dashboard"}), 404
        
        return jsonify(widget.to_dict())
    
    except WidgetNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/widgets/<uuid:widget_id>', methods=['PUT'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:edit')
def update_widget(dashboard_id, widget_id):
    """
    Update a widget.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
        widget_id: Widget UUID
    
    Request Body:
        name: Widget name
        description: Widget description
        type: Widget type
        query_config: Query configuration
        viz_config: Visualization configuration
        grid_position: Grid position
        local_filters: Widget-specific filters
        drilldown_config: Drilldown configuration
    
    Returns:
        Updated widget
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = WidgetUpdateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        # Build updates dict
        updates = {}
        if data.name is not None:
            updates['name'] = data.name
        if data.description is not None:
            updates['description'] = data.description
        if data.type is not None:
            updates['type'] = data.type.value
        if data.query_config is not None:
            updates['query_config'] = data.query_config.dict()
        if data.viz_config is not None:
            updates['viz_config'] = data.viz_config.dict()
        if data.grid_position is not None:
            updates['grid_position'] = data.grid_position.dict()
        if data.local_filters is not None:
            updates['local_filters'] = data.local_filters
        if data.drilldown_config is not None:
            updates['drilldown_config'] = data.drilldown_config.dict()
        
        widget = DashboardService.update_widget(
            widget_id=str(widget_id),
            tenant_id=tenant_id,
            user_id=user_id,
            **updates,
        )
        
        return jsonify(widget.to_dict())
    
    except WidgetNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error updating widget: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/widgets/<uuid:widget_id>', methods=['DELETE'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:edit')
def delete_widget(dashboard_id, widget_id):
    """
    Delete a widget from a dashboard.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
        widget_id: Widget UUID
    
    Returns:
        Success message
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        DashboardService.delete_widget(
            widget_id=str(widget_id),
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        return jsonify({"success": True, "message": "Widget deleted"})
    
    except WidgetNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardValidationError as e:
        return jsonify({"error": str(e)}), 400
    except DashboardServiceError as e:
        logger.error(f"Error deleting widget: {e}")
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Widget Data Endpoints
# =============================================================================

@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/widgets/<uuid:widget_id>/data', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('analytics:query')
def get_widget_data(dashboard_id, widget_id):
    """
    Get widget data (execute query).
    
    Path Parameters:
        dashboard_id: Dashboard UUID
        widget_id: Widget UUID
    
    Query Parameters:
        use_cache: Use cached data if available (default: true)
    
    Returns:
        Query results with metadata
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    use_cache = request.args.get('use_cache', 'true').lower() == 'true'
    
    try:
        widget = DashboardService.get_widget(
            widget_id=str(widget_id),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        if str(widget.dashboard_id) != str(dashboard_id):
            return jsonify({"error": "Widget not found in this dashboard"}), 404
        
        result = DashboardService.execute_widget_query(
            widget=widget,
            tenant_id=tenant_id,
            use_cache=use_cache,
        )
        
        return jsonify({
            'widget_id': str(widget_id),
            'data': result,
        })
    
    except WidgetNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error executing widget query: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/widgets/<uuid:widget_id>/data', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('analytics:query')
def get_widget_data_with_filters(dashboard_id, widget_id):
    """
    Get widget data with filter overrides.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
        widget_id: Widget UUID
    
    Request Body:
        filter_overrides: Additional filters to apply
        use_cache: Use cached data (default: true)
    
    Returns:
        Query results with metadata
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = WidgetDataRequestSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        widget = DashboardService.get_widget(
            widget_id=str(widget_id),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        if str(widget.dashboard_id) != str(dashboard_id):
            return jsonify({"error": "Widget not found in this dashboard"}), 404
        
        # Convert filter overrides to dicts
        filter_overrides = [f.dict() for f in data.filter_overrides] if data.filter_overrides else None
        
        result = DashboardService.execute_widget_query(
            widget=widget,
            tenant_id=tenant_id,
            filter_overrides=filter_overrides,
            use_cache=data.use_cache,
        )
        
        return jsonify({
            'widget_id': str(widget_id),
            'data': result,
        })
    
    except WidgetNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error executing widget query: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/widgets/<uuid:widget_id>/refresh', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('analytics:query')
def refresh_widget_data(dashboard_id, widget_id):
    """
    Force refresh widget cache.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
        widget_id: Widget UUID
    
    Returns:
        Fresh query results
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        result = DashboardService.refresh_widget_cache(
            widget_id=str(widget_id),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        return jsonify({
            'widget_id': str(widget_id),
            'data': result,
            'message': 'Cache refreshed',
        })
    
    except WidgetNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error refreshing widget cache: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/refresh', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('analytics:query')
def refresh_all_widgets(dashboard_id):
    """
    Refresh all widget caches for a dashboard.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
    
    Returns:
        Refresh summary
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        result = DashboardService.refresh_all_widgets(
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        return jsonify(result)
    
    except DashboardNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except DashboardAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except DashboardServiceError as e:
        logger.error(f"Error refreshing widgets: {e}")
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Statistics Endpoints
# =============================================================================

@api_v1_bp.route('/dashboards/stats', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards:view')
def get_dashboard_stats():
    """
    Get dashboard statistics for the current user.
    
    Returns:
        Dashboard statistics
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        stats = DashboardService.get_dashboard_stats(
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        return jsonify(stats)
    
    except DashboardServiceError as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({"error": str(e)}), 400
