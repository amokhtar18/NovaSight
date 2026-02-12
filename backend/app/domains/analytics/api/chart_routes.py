"""
NovaSight Chart API
====================

REST API endpoints for chart management.
"""

from flask import request, jsonify
from flask_jwt_extended import jwt_required
from app.platform.auth.identity import get_current_identity
from pydantic import ValidationError
import logging

from app.api.v1 import api_v1_bp
from app.decorators import require_tenant_context
from app.middleware.permissions import require_permission
from app.domains.analytics.schemas.chart_schemas import (
    ChartCreateSchema,
    ChartUpdateSchema,
    ChartPreviewSchema,
    ChartFolderCreateSchema,
    ChartFolderUpdateSchema,
    SQLEditorSaveAsChartSchema,
)
from app.domains.analytics.application.chart_service import (
    ChartService,
    ChartServiceError,
    ChartNotFoundError,
    ChartFolderNotFoundError,
    ChartAccessDeniedError,
    ChartValidationError,
    ChartExecutionError,
)

logger = logging.getLogger(__name__)


def get_tenant_id():
    """Get tenant ID from current identity."""
    identity = get_current_identity()
    if identity is None:
        raise ChartAccessDeniedError("No authenticated identity")
    return identity.tenant_id


def get_user_id():
    """Get user ID from current identity."""
    identity = get_current_identity()
    if identity is None:
        raise ChartAccessDeniedError("No authenticated identity")
    return identity.user_id


# =============================================================================
# Chart CRUD Endpoints
# =============================================================================

@api_v1_bp.route('/charts', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('charts.view')
def list_charts():
    """
    List all accessible charts.
    
    Query Parameters:
        folder_id: Filter by folder (omit for root)
        include_public: Include public charts (default: true)
        tags: Filter by tags (comma-separated)
        chart_types: Filter by chart types (comma-separated)
        search: Search in name/description
        page: Page number (default: 1)
        per_page: Items per page (default: 20, max: 100)
    
    Returns:
        Paginated list of charts
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    folder_id = request.args.get('folder_id')
    include_public = request.args.get('include_public', 'true').lower() == 'true'
    tags = request.args.get('tags', '').split(',') if request.args.get('tags') else None
    chart_types = request.args.get('chart_types', '').split(',') if request.args.get('chart_types') else None
    search = request.args.get('search')
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    offset = (page - 1) * per_page
    
    try:
        charts, total = ChartService.list_for_user(
            tenant_id=tenant_id,
            user_id=user_id,
            folder_id=folder_id,
            include_public=include_public,
            tags=tags,
            chart_types=chart_types,
            search=search,
            limit=per_page,
            offset=offset,
        )
        
        result = {
            "items": [chart.to_dict() for chart in charts],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }
        return jsonify(result)
    
    except ChartServiceError as e:
        logger.error(f"Error listing charts: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/charts/all', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('charts.view')
def list_all_charts():
    """
    List all charts (flat list for selection UI).
    
    Query Parameters:
        include_folders: Include folder structure (default: true)
        search: Search filter
        limit: Maximum results (default: 100)
    
    Returns:
        Flat list of all accessible charts
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    include_folders = request.args.get('include_folders', 'true').lower() == 'true'
    search = request.args.get('search')
    limit = min(int(request.args.get('limit', 100)), 500)
    
    try:
        result = ChartService.list_all_for_tenant(
            tenant_id=tenant_id,
            user_id=user_id,
            include_folders=include_folders,
            search=search,
            limit=limit,
        )
        
        response = {
            "charts": [chart.to_dict() for chart in result.get("charts", [])],
        }
        
        if include_folders and "folders" in result:
            response["folders"] = [folder.to_dict() for folder in result["folders"]]
        
        return jsonify(response)
    
    except ChartServiceError as e:
        logger.error(f"Error listing all charts: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/charts', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('charts.create')
def create_chart():
    """
    Create a new chart.
    
    Request Body:
        name: Chart name (required)
        chart_type: Visualization type (required)
        source_type: Data source type (required)
        description: Chart description
        semantic_model_id: Semantic model UUID (required for semantic_model source)
        sql_query: SQL query (required for sql_query source)
        query_config: Query configuration
        viz_config: Visualization configuration
        folder_id: Parent folder UUID
        tags: List of tags
        is_public: Public visibility (default: false)
    
    Returns:
        Created chart
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = ChartCreateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        chart = ChartService.create(
            tenant_id=tenant_id,
            created_by=user_id,
            name=data.name,
            chart_type=data.chart_type.value,
            source_type=data.source_type.value,
            description=data.description,
            semantic_model_id=str(data.semantic_model_id) if data.semantic_model_id else None,
            sql_query=data.sql_query,
            query_config=data.query_config.dict() if data.query_config else None,
            viz_config=data.viz_config.dict() if data.viz_config else None,
            folder_id=str(data.folder_id) if data.folder_id else None,
            tags=data.tags,
            is_public=data.is_public,
        )
        
        return jsonify(chart.to_dict()), 201
    
    except ChartValidationError as e:
        return jsonify({"error": str(e)}), 400
    except ChartFolderNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ChartServiceError as e:
        logger.error(f"Error creating chart: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/charts/<uuid:chart_id>', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('charts.view')
def get_chart(chart_id):
    """
    Get a chart by ID.
    
    Path Parameters:
        chart_id: Chart UUID
    
    Returns:
        Chart details
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        chart = ChartService.get(
            chart_id=str(chart_id),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        return jsonify(chart.to_dict())
    
    except ChartNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ChartAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except ChartServiceError as e:
        logger.error(f"Error getting chart: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/charts/<uuid:chart_id>', methods=['PUT'])
@jwt_required()
@require_tenant_context
@require_permission('charts.edit')
def update_chart(chart_id):
    """
    Update a chart.
    
    Path Parameters:
        chart_id: Chart UUID
    
    Request Body:
        Any chart fields to update
    
    Returns:
        Updated chart
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = ChartUpdateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        update_data = data.dict(exclude_unset=True)
        
        # Convert Pydantic models to dicts
        if 'query_config' in update_data and update_data['query_config']:
            update_data['query_config'] = update_data['query_config'].dict()
        if 'viz_config' in update_data and update_data['viz_config']:
            update_data['viz_config'] = update_data['viz_config'].dict()
        if 'chart_type' in update_data and update_data['chart_type']:
            update_data['chart_type'] = update_data['chart_type'].value
        if 'source_type' in update_data and update_data['source_type']:
            update_data['source_type'] = update_data['source_type'].value
        
        chart = ChartService.update(
            chart_id=str(chart_id),
            tenant_id=tenant_id,
            user_id=user_id,
            **update_data,
        )
        
        return jsonify(chart.to_dict())
    
    except ChartNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ChartAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except ChartServiceError as e:
        logger.error(f"Error updating chart: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/charts/<uuid:chart_id>', methods=['DELETE'])
@jwt_required()
@require_tenant_context
@require_permission('charts.delete')
def delete_chart(chart_id):
    """
    Delete a chart.
    
    Path Parameters:
        chart_id: Chart UUID
    
    Query Parameters:
        hard: Permanently delete (default: false)
    
    Returns:
        Success message
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    hard_delete = request.args.get('hard', 'false').lower() == 'true'
    
    try:
        ChartService.delete(
            chart_id=str(chart_id),
            tenant_id=tenant_id,
            user_id=user_id,
            soft_delete=not hard_delete,
        )
        
        return jsonify({"message": "Chart deleted successfully"})
    
    except ChartNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ChartAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except ChartServiceError as e:
        logger.error(f"Error deleting chart: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/charts/<uuid:chart_id>/duplicate', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('charts.create')
def duplicate_chart(chart_id):
    """
    Duplicate a chart.
    
    Path Parameters:
        chart_id: Chart UUID to duplicate
    
    Request Body:
        name: Name for the new chart (optional)
    
    Returns:
        Newly created chart
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    new_name = request.json.get('name') if request.json else None
    
    try:
        chart = ChartService.duplicate(
            chart_id=str(chart_id),
            tenant_id=tenant_id,
            user_id=user_id,
            new_name=new_name,
        )
        
        return jsonify(chart.to_dict()), 201
    
    except ChartNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ChartAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except ChartServiceError as e:
        logger.error(f"Error duplicating chart: {e}")
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Chart Data Execution Endpoints
# =============================================================================

@api_v1_bp.route('/charts/<uuid:chart_id>/data', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('charts.view')
def get_chart_data(chart_id):
    """
    Execute chart query and return data.
    
    Path Parameters:
        chart_id: Chart UUID
    
    Query Parameters:
        refresh: Force bypass cache (default: false)
    
    Returns:
        Chart data with metadata
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    try:
        result = ChartService.execute_chart(
            chart_id=str(chart_id),
            tenant_id=tenant_id,
            user_id=user_id,
            force_refresh=force_refresh,
        )
        
        return jsonify(result)
    
    except ChartNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ChartAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except ChartExecutionError as e:
        return jsonify({"error": str(e)}), 400
    except ChartServiceError as e:
        logger.error(f"Error executing chart: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/charts/<uuid:chart_id>/data', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('charts.view')
def get_chart_data_with_filters(chart_id):
    """
    Execute chart query with runtime filters.
    
    Path Parameters:
        chart_id: Chart UUID
    
    Request Body:
        filters: Runtime filter conditions
        refresh: Force bypass cache (default: false)
    
    Returns:
        Chart data with metadata
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    body = request.json or {}
    force_refresh = body.get('refresh', False)
    runtime_filters = body.get('filters')
    
    try:
        result = ChartService.execute_chart(
            chart_id=str(chart_id),
            tenant_id=tenant_id,
            user_id=user_id,
            force_refresh=force_refresh,
            runtime_filters=runtime_filters,
        )
        
        return jsonify(result)
    
    except ChartNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ChartAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except ChartExecutionError as e:
        return jsonify({"error": str(e)}), 400
    except ChartServiceError as e:
        logger.error(f"Error executing chart: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/charts/preview', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('charts.view')
def preview_chart_data():
    """
    Preview query results without saving.
    
    Request Body:
        source_type: Data source type (required)
        semantic_model_id: Semantic model UUID (for semantic_model source)
        sql_query: SQL query (for sql_query source)
        query_config: Query configuration
        limit: Row limit (default: 100)
    
    Returns:
        Preview data with columns
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = ChartPreviewSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        result = ChartService.preview_query(
            tenant_id=tenant_id,
            user_id=user_id,
            source_type=data.source_type.value,
            semantic_model_id=str(data.semantic_model_id) if data.semantic_model_id else None,
            sql_query=data.sql_query,
            query_config=data.query_config.dict() if data.query_config else None,
            limit=data.limit,
        )
        
        return jsonify(result)
    
    except ChartValidationError as e:
        return jsonify({"error": str(e)}), 400
    except ChartExecutionError as e:
        return jsonify({"error": str(e)}), 400
    except ChartServiceError as e:
        logger.error(f"Error previewing chart: {e}")
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Chart Folder Endpoints
# =============================================================================

@api_v1_bp.route('/chart-folders', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('charts.view')
def list_chart_folders():
    """
    List chart folders.
    
    Query Parameters:
        parent_id: Parent folder UUID (omit for root)
    
    Returns:
        List of folders
    """
    tenant_id = get_tenant_id()
    parent_id = request.args.get('parent_id')
    
    try:
        folders = ChartService.list_folders(
            tenant_id=tenant_id,
            parent_id=parent_id,
        )
        
        return jsonify([folder.to_dict() for folder in folders])
    
    except ChartServiceError as e:
        logger.error(f"Error listing folders: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/chart-folders', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('charts.create')
def create_chart_folder():
    """
    Create a new chart folder.
    
    Request Body:
        name: Folder name (required)
        description: Folder description
        parent_id: Parent folder UUID
    
    Returns:
        Created folder
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = ChartFolderCreateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        folder = ChartService.create_folder(
            tenant_id=tenant_id,
            created_by=user_id,
            name=data.name,
            description=data.description,
            parent_id=str(data.parent_id) if data.parent_id else None,
        )
        
        return jsonify(folder.to_dict()), 201
    
    except ChartValidationError as e:
        return jsonify({"error": str(e)}), 400
    except ChartServiceError as e:
        logger.error(f"Error creating folder: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/chart-folders/<uuid:folder_id>', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('charts.view')
def get_chart_folder(folder_id):
    """
    Get a chart folder.
    
    Path Parameters:
        folder_id: Folder UUID
    
    Returns:
        Folder details
    """
    tenant_id = get_tenant_id()
    
    try:
        folder = ChartService.get_folder(
            folder_id=str(folder_id),
            tenant_id=tenant_id,
        )
        
        return jsonify(folder.to_dict())
    
    except ChartFolderNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ChartServiceError as e:
        logger.error(f"Error getting folder: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/chart-folders/<uuid:folder_id>', methods=['PUT'])
@jwt_required()
@require_tenant_context
@require_permission('charts.edit')
def update_chart_folder(folder_id):
    """
    Update a chart folder.
    
    Path Parameters:
        folder_id: Folder UUID
    
    Request Body:
        name: New folder name
        description: New description
        parent_id: New parent folder
    
    Returns:
        Updated folder
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = ChartFolderUpdateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        folder = ChartService.update_folder(
            folder_id=str(folder_id),
            tenant_id=tenant_id,
            user_id=user_id,
            **data.dict(exclude_unset=True),
        )
        
        return jsonify(folder.to_dict())
    
    except ChartFolderNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ChartAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except ChartServiceError as e:
        logger.error(f"Error updating folder: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/chart-folders/<uuid:folder_id>', methods=['DELETE'])
@jwt_required()
@require_tenant_context
@require_permission('charts.delete')
def delete_chart_folder(folder_id):
    """
    Delete a chart folder.
    
    Path Parameters:
        folder_id: Folder UUID
    
    Query Parameters:
        move_to: Folder UUID to move contents to (omit for root)
    
    Returns:
        Success message
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    move_to = request.args.get('move_to')
    
    try:
        ChartService.delete_folder(
            folder_id=str(folder_id),
            tenant_id=tenant_id,
            user_id=user_id,
            move_contents_to=move_to,
        )
        
        return jsonify({"message": "Folder deleted successfully"})
    
    except ChartFolderNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ChartAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except ChartServiceError as e:
        logger.error(f"Error deleting folder: {e}")
        return jsonify({"error": str(e)}), 400


# =============================================================================
# SQL Editor Chart Endpoints
# =============================================================================

@api_v1_bp.route('/sql-editor/save-as-chart', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('charts.create')
def sql_editor_save_as_chart():
    """
    Save SQL query result as a chart from SQL Editor.
    
    Request Body:
        name: Chart name (required)
        description: Chart description
        chart_type: Chart type (bar, line, pie only)
        sql_query: SQL query (required)
        x_column: X-axis column
        y_columns: Y-axis columns
        viz_config: Visualization configuration
        folder_id: Folder UUID
        tags: List of tags
    
    Returns:
        Created chart
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        data = SQLEditorSaveAsChartSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        # Build query config from SQL Editor selection
        query_config = {
            "dimensions": [data.x_column],
            "measures": data.y_columns,
            "limit": 1000,
        }
        
        viz_config = data.viz_config.dict() if data.viz_config else {}
        
        chart = ChartService.create(
            tenant_id=tenant_id,
            created_by=user_id,
            name=data.name,
            chart_type=data.chart_type.value,
            source_type="sql_query",
            description=data.description,
            sql_query=data.sql_query,
            query_config=query_config,
            viz_config=viz_config,
            folder_id=str(data.folder_id) if data.folder_id else None,
            tags=data.tags,
        )
        
        return jsonify(chart.to_dict()), 201
    
    except ChartValidationError as e:
        return jsonify({"error": str(e)}), 400
    except ChartServiceError as e:
        logger.error(f"Error saving SQL as chart: {e}")
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Dashboard Chart Integration Endpoints
# =============================================================================

@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/charts', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards.edit')
def add_chart_to_dashboard(dashboard_id):
    """
    Add a chart to a dashboard.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
    
    Request Body:
        chart_id: Chart UUID to add (required)
        grid_position: Grid position config
        local_filters: Dashboard-specific filters
        local_viz_config: Dashboard-specific viz overrides
    
    Returns:
        Dashboard chart configuration
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    body = request.json or {}
    chart_id = body.get('chart_id')
    
    if not chart_id:
        return jsonify({"error": "chart_id is required"}), 400
    
    try:
        dashboard_chart = ChartService.add_to_dashboard(
            chart_id=chart_id,
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
            grid_position=body.get('grid_position'),
            local_filters=body.get('local_filters'),
            local_viz_config=body.get('local_viz_config'),
        )
        
        return jsonify({
            "id": str(dashboard_chart.id),
            "dashboard_id": str(dashboard_chart.dashboard_id),
            "chart_id": str(dashboard_chart.chart_id),
            "grid_position": dashboard_chart.grid_position,
            "local_filters": dashboard_chart.local_filters,
            "local_viz_config": dashboard_chart.local_viz_config,
        }), 201
    
    except ChartNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ChartAccessDeniedError as e:
        return jsonify({"error": str(e)}), 403
    except ChartValidationError as e:
        return jsonify({"error": str(e)}), 400
    except ChartServiceError as e:
        logger.error(f"Error adding chart to dashboard: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/charts/<uuid:chart_id>', methods=['DELETE'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards.edit')
def remove_chart_from_dashboard(dashboard_id, chart_id):
    """
    Remove a chart from a dashboard.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
        chart_id: Chart UUID to remove
    
    Returns:
        Success message
    """
    tenant_id = get_tenant_id()
    user_id = get_user_id()
    
    try:
        removed = ChartService.remove_from_dashboard(
            chart_id=str(chart_id),
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
        if removed:
            return jsonify({"message": "Chart removed from dashboard"})
        else:
            return jsonify({"error": "Chart not found on dashboard"}), 404
    
    except ChartServiceError as e:
        logger.error(f"Error removing chart from dashboard: {e}")
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/dashboards/<uuid:dashboard_id>/charts', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('dashboards.view')
def get_dashboard_charts(dashboard_id):
    """
    Get all charts on a dashboard.
    
    Path Parameters:
        dashboard_id: Dashboard UUID
    
    Returns:
        List of charts with dashboard configurations
    """
    tenant_id = get_tenant_id()
    
    try:
        charts = ChartService.get_dashboard_charts(
            dashboard_id=str(dashboard_id),
            tenant_id=tenant_id,
        )
        
        result = []
        for item in charts:
            result.append({
                "dashboard_chart_id": item["dashboard_chart_id"],
                "chart": item["chart"].to_dict(),
                "grid_position": item["grid_position"],
                "local_filters": item["local_filters"],
                "local_viz_config": item["local_viz_config"],
            })
        
        return jsonify(result)
    
    except ChartServiceError as e:
        logger.error(f"Error getting dashboard charts: {e}")
        return jsonify({"error": str(e)}), 400
