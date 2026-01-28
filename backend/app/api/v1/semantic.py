"""
NovaSight Semantic Layer API
==============================

REST API endpoints for managing the semantic layer including
semantic models, dimensions, measures, relationships, and query execution.
"""

from flask import request, g, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from pydantic import ValidationError
import logging

from app.api.v1 import api_v1_bp
from app.decorators import require_tenant_context
from app.middleware.permissions import require_permission
from app.schemas.semantic_schemas import (
    SemanticModelCreateSchema,
    SemanticModelUpdateSchema,
    SemanticModelResponseSchema,
    DimensionCreateSchema,
    DimensionUpdateSchema,
    DimensionResponseSchema,
    MeasureCreateSchema,
    MeasureUpdateSchema,
    MeasureResponseSchema,
    RelationshipCreateSchema,
    RelationshipResponseSchema,
    SemanticQuerySchema,
    QueryResultSchema,
)
from app.services.semantic_service import (
    SemanticService,
    SemanticServiceError,
    ModelNotFoundError,
    DimensionNotFoundError,
    MeasureNotFoundError,
    QueryBuildError,
)

logger = logging.getLogger(__name__)


def get_tenant_id():
    """Get tenant ID from JWT identity."""
    identity = get_jwt_identity()
    return identity.get("tenant_id")


# =============================================================================
# Semantic Models
# =============================================================================

@api_v1_bp.route('/semantic/models', methods=['GET'])
@jwt_required()
@require_tenant_context
def list_semantic_models():
    """
    List all semantic models for the current tenant.
    
    Query Parameters:
        include_inactive: Include inactive models (default: false)
        model_type: Filter by type (fact, dimension, aggregate)
    
    Returns:
        List of semantic models
    """
    tenant_id = get_tenant_id()
    include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
    model_type = request.args.get('model_type')
    
    try:
        models = SemanticService.list_models(
            tenant_id=tenant_id,
            include_inactive=include_inactive,
            model_type=model_type,
        )
        
        result = []
        for model in models:
            model_dict = model.to_dict()
            model_dict['dimensions_count'] = model.dimensions.count()
            model_dict['measures_count'] = model.measures.count()
            result.append(model_dict)
        
        return jsonify(result)
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/models', methods=['POST'])
@jwt_required()
@require_tenant_context
def create_semantic_model():
    """
    Create a new semantic model.
    
    Request Body:
        name: Model name (required)
        dbt_model: Reference to dbt model (required)
        label: Human-readable label
        description: Model description
        model_type: fact, dimension, or aggregate
        cache_enabled: Enable query caching
        cache_ttl_seconds: Cache TTL
        tags: List of tags
        meta: Additional metadata
    
    Returns:
        Created semantic model
    """
    tenant_id = get_tenant_id()
    
    try:
        data = SemanticModelCreateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        model = SemanticService.create_model(
            tenant_id=tenant_id,
            **data.dict(exclude_none=True),
        )
        
        return jsonify(model.to_dict()), 201
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/models/<uuid:model_id>', methods=['GET'])
@jwt_required()
@require_tenant_context
def get_semantic_model(model_id):
    """
    Get a semantic model by ID.
    
    Returns:
        Semantic model with dimensions and measures
    """
    tenant_id = get_tenant_id()
    
    try:
        model = SemanticService.get_model(str(model_id), tenant_id)
        
        result = model.to_dict()
        result['dimensions'] = [d.to_dict() for d in model.dimensions]
        result['measures'] = [m.to_dict() for m in model.measures]
        
        return jsonify(result)
    except ModelNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/models/<uuid:model_id>', methods=['PUT'])
@jwt_required()
@require_tenant_context
def update_semantic_model(model_id):
    """
    Update a semantic model.
    
    Request Body:
        label, description, model_type, cache_enabled, cache_ttl_seconds,
        tags, meta, is_active
    
    Returns:
        Updated semantic model
    """
    tenant_id = get_tenant_id()
    
    try:
        data = SemanticModelUpdateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        model = SemanticService.update_model(
            model_id=str(model_id),
            tenant_id=tenant_id,
            **data.dict(exclude_none=True),
        )
        
        return jsonify(model.to_dict())
    except ModelNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/models/<uuid:model_id>', methods=['DELETE'])
@jwt_required()
@require_tenant_context
def delete_semantic_model(model_id):
    """
    Delete a semantic model and all its dimensions/measures.
    
    Returns:
        Success message
    """
    tenant_id = get_tenant_id()
    
    try:
        SemanticService.delete_model(str(model_id), tenant_id)
        return jsonify({"message": "Model deleted successfully"})
    except ModelNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Dimensions
# =============================================================================

@api_v1_bp.route('/semantic/models/<uuid:model_id>/dimensions', methods=['GET'])
@jwt_required()
@require_tenant_context
def list_dimensions(model_id):
    """
    List dimensions for a semantic model.
    
    Query Parameters:
        include_hidden: Include hidden dimensions
    
    Returns:
        List of dimensions
    """
    tenant_id = get_tenant_id()
    include_hidden = request.args.get('include_hidden', 'false').lower() == 'true'
    
    try:
        dimensions = SemanticService.list_dimensions(
            tenant_id=tenant_id,
            model_id=str(model_id),
            include_hidden=include_hidden,
        )
        
        return jsonify([d.to_dict() for d in dimensions])
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/models/<uuid:model_id>/dimensions', methods=['POST'])
@jwt_required()
@require_tenant_context
def add_dimension(model_id):
    """
    Add a dimension to a semantic model.
    
    Request Body:
        name: Dimension name (required)
        expression: SQL expression (required)
        label: Human-readable label
        description: Dimension description
        type: categorical, temporal, numeric, hierarchical
        data_type: Data type (String, Int32, etc.)
        is_primary_key: Primary key flag
        is_hidden: Hide from UI
        is_filterable: Allow filtering
        is_groupable: Allow grouping
    
    Returns:
        Created dimension
    """
    tenant_id = get_tenant_id()
    
    try:
        data = DimensionCreateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        dimension = SemanticService.add_dimension(
            model_id=str(model_id),
            tenant_id=tenant_id,
            **data.dict(exclude_none=True),
        )
        
        return jsonify(dimension.to_dict()), 201
    except ModelNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/dimensions/<uuid:dimension_id>', methods=['GET'])
@jwt_required()
@require_tenant_context
def get_dimension(dimension_id):
    """Get a dimension by ID."""
    tenant_id = get_tenant_id()
    
    try:
        dimension = SemanticService.get_dimension(str(dimension_id), tenant_id)
        return jsonify(dimension.to_dict())
    except DimensionNotFoundError as e:
        return jsonify({"error": str(e)}), 404


@api_v1_bp.route('/semantic/dimensions/<uuid:dimension_id>', methods=['PUT'])
@jwt_required()
@require_tenant_context
def update_dimension(dimension_id):
    """Update a dimension."""
    tenant_id = get_tenant_id()
    
    try:
        data = DimensionUpdateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        dimension = SemanticService.update_dimension(
            dimension_id=str(dimension_id),
            tenant_id=tenant_id,
            **data.dict(exclude_none=True),
        )
        
        return jsonify(dimension.to_dict())
    except DimensionNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/dimensions/<uuid:dimension_id>', methods=['DELETE'])
@jwt_required()
@require_tenant_context
def delete_dimension(dimension_id):
    """Delete a dimension."""
    tenant_id = get_tenant_id()
    
    try:
        SemanticService.delete_dimension(str(dimension_id), tenant_id)
        return jsonify({"message": "Dimension deleted successfully"})
    except DimensionNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Measures
# =============================================================================

@api_v1_bp.route('/semantic/models/<uuid:model_id>/measures', methods=['GET'])
@jwt_required()
@require_tenant_context
def list_measures(model_id):
    """
    List measures for a semantic model.
    
    Query Parameters:
        include_hidden: Include hidden measures
    
    Returns:
        List of measures
    """
    tenant_id = get_tenant_id()
    include_hidden = request.args.get('include_hidden', 'false').lower() == 'true'
    
    try:
        measures = SemanticService.list_measures(
            tenant_id=tenant_id,
            model_id=str(model_id),
            include_hidden=include_hidden,
        )
        
        return jsonify([m.to_dict() for m in measures])
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/models/<uuid:model_id>/measures', methods=['POST'])
@jwt_required()
@require_tenant_context
def add_measure(model_id):
    """
    Add a measure to a semantic model.
    
    Request Body:
        name: Measure name (required)
        aggregation: sum, count, avg, etc. (required)
        expression: SQL expression (required)
        label: Human-readable label
        description: Measure description
        format: number, currency, percent
        format_string: Format pattern
        decimal_places: Number of decimal places
        unit: Unit of measurement
        is_hidden: Hide from UI
        is_additive: Can be summed across dimensions
    
    Returns:
        Created measure
    """
    tenant_id = get_tenant_id()
    
    try:
        data = MeasureCreateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        measure = SemanticService.add_measure(
            model_id=str(model_id),
            tenant_id=tenant_id,
            **data.dict(exclude_none=True),
        )
        
        return jsonify(measure.to_dict()), 201
    except ModelNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/measures/<uuid:measure_id>', methods=['GET'])
@jwt_required()
@require_tenant_context
def get_measure(measure_id):
    """Get a measure by ID."""
    tenant_id = get_tenant_id()
    
    try:
        measure = SemanticService.get_measure(str(measure_id), tenant_id)
        return jsonify(measure.to_dict())
    except MeasureNotFoundError as e:
        return jsonify({"error": str(e)}), 404


@api_v1_bp.route('/semantic/measures/<uuid:measure_id>', methods=['PUT'])
@jwt_required()
@require_tenant_context
def update_measure(measure_id):
    """Update a measure."""
    tenant_id = get_tenant_id()
    
    try:
        data = MeasureUpdateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        measure = SemanticService.update_measure(
            measure_id=str(measure_id),
            tenant_id=tenant_id,
            **data.dict(exclude_none=True),
        )
        
        return jsonify(measure.to_dict())
    except MeasureNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/measures/<uuid:measure_id>', methods=['DELETE'])
@jwt_required()
@require_tenant_context
def delete_measure(measure_id):
    """Delete a measure."""
    tenant_id = get_tenant_id()
    
    try:
        SemanticService.delete_measure(str(measure_id), tenant_id)
        return jsonify({"message": "Measure deleted successfully"})
    except MeasureNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Relationships
# =============================================================================

@api_v1_bp.route('/semantic/relationships', methods=['GET'])
@jwt_required()
@require_tenant_context
def list_relationships():
    """List all relationships for the current tenant."""
    tenant_id = get_tenant_id()
    
    try:
        relationships = SemanticService.list_relationships(tenant_id)
        return jsonify([r.to_dict() for r in relationships])
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/relationships', methods=['POST'])
@jwt_required()
@require_tenant_context
def create_relationship():
    """
    Create a relationship between semantic models.
    
    Request Body:
        from_model_id: Source model UUID
        to_model_id: Target model UUID
        from_column: Source join column
        to_column: Target join column
        relationship_type: one_to_one, one_to_many, many_to_one, many_to_many
        join_type: LEFT, INNER, RIGHT, FULL
    
    Returns:
        Created relationship
    """
    tenant_id = get_tenant_id()
    
    try:
        data = RelationshipCreateSchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    try:
        relationship = SemanticService.create_relationship(
            tenant_id=tenant_id,
            **data.dict(exclude_none=True),
        )
        
        return jsonify(relationship.to_dict()), 201
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/relationships/<uuid:relationship_id>', methods=['DELETE'])
@jwt_required()
@require_tenant_context
def delete_relationship(relationship_id):
    """Delete a relationship."""
    tenant_id = get_tenant_id()
    
    try:
        SemanticService.delete_relationship(str(relationship_id), tenant_id)
        return jsonify({"message": "Relationship deleted successfully"})
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Query Execution
# =============================================================================

@api_v1_bp.route('/semantic/query', methods=['POST'])
@jwt_required()
@require_tenant_context
def execute_semantic_query():
    """
    Execute a semantic layer query.
    
    Request Body:
        dimensions: List of dimension names (optional)
        measures: List of measure names (required)
        filters: List of filter conditions
        order_by: List of ordering specifications
        limit: Maximum rows (default 1000, max 100000)
        offset: Offset for pagination
        time_dimension: Time dimension for date filtering
        date_from: Start date (ISO format)
        date_to: End date (ISO format)
    
    Returns:
        Query results with columns, rows, and metadata
    """
    tenant_id = get_tenant_id()
    
    try:
        data = SemanticQuerySchema(**request.json)
    except ValidationError as e:
        return jsonify({"error": "Validation Error", "details": e.errors()}), 400
    
    # Convert filters and order_by to dicts
    filters = [f.dict() for f in data.filters] if data.filters else []
    order_by = [o.dict() for o in data.order_by] if data.order_by else []
    
    try:
        result = SemanticService.execute_query(
            tenant_id=tenant_id,
            dimensions=data.dimensions,
            measures=data.measures,
            filters=filters,
            order_by=order_by,
            limit=data.limit,
            offset=data.offset,
            time_dimension=data.time_dimension,
            date_from=data.date_from,
            date_to=data.date_to,
        )
        
        return jsonify(result)
        
    except QueryBuildError as e:
        return jsonify({"error": str(e)}), 400
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Discovery / Explore
# =============================================================================

@api_v1_bp.route('/semantic/explore', methods=['GET'])
@jwt_required()
@require_tenant_context
def explore_semantic_layer():
    """
    Get all available semantic layer metadata for exploration.
    
    Returns:
        All models, dimensions, measures, and relationships
    """
    tenant_id = get_tenant_id()
    
    try:
        models = SemanticService.list_models(tenant_id)
        dimensions = SemanticService.list_dimensions(tenant_id)
        measures = SemanticService.list_measures(tenant_id)
        relationships = SemanticService.list_relationships(tenant_id)
        
        return jsonify({
            "models": [m.to_dict() for m in models],
            "dimensions": [d.to_dict() for d in dimensions],
            "measures": [m.to_dict() for m in measures],
            "relationships": [r.to_dict() for r in relationships],
        })
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/dimensions', methods=['GET'])
@jwt_required()
@require_tenant_context
def list_all_dimensions():
    """List all dimensions across all models for the tenant."""
    tenant_id = get_tenant_id()
    
    try:
        dimensions = SemanticService.list_dimensions(tenant_id)
        return jsonify([d.to_dict() for d in dimensions])
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


@api_v1_bp.route('/semantic/measures', methods=['GET'])
@jwt_required()
@require_tenant_context
def list_all_measures():
    """List all measures across all models for the tenant."""
    tenant_id = get_tenant_id()
    
    try:
        measures = SemanticService.list_measures(tenant_id)
        return jsonify([m.to_dict() for m in measures])
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400


# =============================================================================
# Cache Management
# =============================================================================

@api_v1_bp.route('/semantic/cache/clear', methods=['POST'])
@jwt_required()
@require_tenant_context
def clear_semantic_cache():
    """
    Clear the semantic layer query cache.
    
    Returns:
        Number of cache entries cleared
    """
    tenant_id = get_tenant_id()
    
    try:
        count = SemanticService.clear_cache(tenant_id)
        return jsonify({
            "message": "Cache cleared",
            "entries_cleared": count,
        })
    except SemanticServiceError as e:
        return jsonify({"error": str(e)}), 400
