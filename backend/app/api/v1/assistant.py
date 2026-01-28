"""
NovaSight AI Assistant API
===========================

Endpoints for natural language query processing and AI-assisted analytics.
Implements ADR-002: LLM generates parameters only, never executable code.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import g, jsonify, request
from flask_jwt_extended import jwt_required
from pydantic import BaseModel, Field, ValidationError

from app.api.v1 import api_v1_bp
from app.decorators import async_route, require_tenant_context
from app.middleware.permissions import require_permission
from app.services.ollama.client import (
    OllamaClient, 
    OllamaError, 
    OllamaConnectionError,
    get_ollama_client
)
from app.services.ollama.nl_to_params import (
    NLToParametersService,
    QueryIntent,
    QueryExplanation
)
from app.services.semantic_service import SemanticService, SemanticServiceError

logger = logging.getLogger(__name__)


# =============================================================================
# Request/Response Models
# =============================================================================

class NLQueryRequest(BaseModel):
    """Request model for natural language query."""
    query: str = Field(..., min_length=1, max_length=2000)
    execute: bool = Field(default=True, description="Whether to execute the query")
    explain: bool = Field(default=False, description="Whether to explain results")
    strict: bool = Field(default=False, description="Reject unknown references if true")


class ExplainRequest(BaseModel):
    """Request model for query explanation."""
    query_description: str = Field(..., min_length=1, max_length=500)
    dimensions: List[str] = Field(default_factory=list)
    measures: List[str] = Field(default_factory=list)
    row_count: int = Field(ge=0)
    sample_data: List[Dict[str, Any]] = Field(default_factory=list)


class SuggestRequest(BaseModel):
    """Request model for analysis suggestions."""
    context: str = Field(default="", max_length=1000)


# =============================================================================
# Endpoints
# =============================================================================

@api_v1_bp.route('/assistant/query', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('analytics.query')
@async_route
async def natural_language_query():
    """
    Convert natural language to analytics query and optionally execute.
    
    This endpoint:
    1. Parses natural language into structured parameters (via Ollama)
    2. Validates parameters against available schema
    3. Optionally executes the query via SemanticService
    4. Optionally explains the results
    
    SECURITY: No raw SQL/code is generated. All execution goes through
    the template-based SemanticService (ADR-002 compliance).
    
    ---
    tags:
      - AI Assistant
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - query
            properties:
              query:
                type: string
                description: Natural language query
                example: "Show me total sales by product category for last month"
              execute:
                type: boolean
                default: true
                description: Whether to execute the parsed query
              explain:
                type: boolean
                default: false
                description: Whether to generate explanation of results
              strict:
                type: boolean
                default: false
                description: Reject query if it references unknown dimensions/measures
    responses:
      200:
        description: Query successfully parsed and optionally executed
      400:
        description: Invalid request or query parsing failed
      503:
        description: AI service unavailable
    """
    try:
        data = NLQueryRequest(**request.json)
    except ValidationError as e:
        return jsonify({'error': 'Invalid request', 'details': e.errors()}), 400
    
    tenant_id = g.tenant_id
    
    try:
        # Get available dimensions and measures for tenant
        semantic_models = SemanticService.list_models(tenant_id)
        
        available_dimensions = []
        available_measures = []
        
        for model in semantic_models:
            # Get dimensions for this model
            dimensions = SemanticService.list_dimensions(model.id)
            available_dimensions.extend([d.name for d in dimensions])
            
            # Get measures for this model
            measures = SemanticService.list_measures(model.id)
            available_measures.extend([m.name for m in measures])
        
        # Remove duplicates while preserving order
        available_dimensions = list(dict.fromkeys(available_dimensions))
        available_measures = list(dict.fromkeys(available_measures))
        
        if not available_dimensions and not available_measures:
            return jsonify({
                'error': 'No semantic models available',
                'message': 'Please create semantic models with dimensions and measures first.'
            }), 400
        
        # Initialize Ollama client and NL service
        ollama_client = get_ollama_client()
        nl_service = NLToParametersService(ollama_client)
        
        # Parse natural language to parameters
        intent = await nl_service.parse_query(
            natural_language=data.query,
            available_dimensions=available_dimensions,
            available_measures=available_measures,
            strict=data.strict
        )
        
        response = {
            'intent': {
                'dimensions': intent.dimensions,
                'measures': intent.measures,
                'filters': [f.model_dump() for f in intent.filters],
                'order_by': [o.model_dump() for o in intent.order_by],
                'limit': intent.limit,
                'time_dimension': intent.time_dimension,
                'date_from': intent.date_from,
                'date_to': intent.date_to,
            },
            'available_schema': {
                'dimensions': available_dimensions[:50],  # Limit for response size
                'measures': available_measures[:50],
            }
        }
        
        # Execute query if requested
        if data.execute and (intent.dimensions or intent.measures):
            try:
                # Convert filters to dict format for SemanticService
                filters = [
                    {
                        'column': f.column,
                        'operator': f.operator,
                        'value': f.value
                    }
                    for f in intent.filters
                ]
                
                # Convert order_by to dict format
                order_by = [
                    {'column': o.column, 'direction': o.direction}
                    for o in intent.order_by
                ]
                
                # Parse date strings if present
                date_from = None
                date_to = None
                if intent.date_from:
                    try:
                        date_from = datetime.fromisoformat(intent.date_from.replace('Z', '+00:00'))
                    except ValueError:
                        pass
                if intent.date_to:
                    try:
                        date_to = datetime.fromisoformat(intent.date_to.replace('Z', '+00:00'))
                    except ValueError:
                        pass
                
                result = SemanticService.execute_query(
                    tenant_id=tenant_id,
                    dimensions=intent.dimensions,
                    measures=intent.measures,
                    filters=filters if filters else None,
                    order_by=order_by if order_by else None,
                    limit=intent.limit,
                    time_dimension=intent.time_dimension,
                    date_from=date_from,
                    date_to=date_to,
                )
                
                response['result'] = result
                
                # Generate explanation if requested
                if data.explain and result.get('rows'):
                    try:
                        explanation = await nl_service.explain_results(
                            query_description=data.query,
                            dimensions=intent.dimensions,
                            measures=intent.measures,
                            row_count=result['row_count'],
                            sample_data=[
                                dict(zip(result['columns'], row))
                                for row in result['rows'][:5]
                            ]
                        )
                        response['explanation'] = explanation.model_dump()
                    except Exception as e:
                        logger.warning(f"Failed to generate explanation: {e}")
                        response['explanation_error'] = str(e)
                        
            except SemanticServiceError as e:
                response['execution_error'] = str(e)
                response['result'] = None
        
        await ollama_client.close()
        return jsonify(response), 200
        
    except OllamaConnectionError as e:
        logger.error(f"Ollama connection error: {e}")
        return jsonify({
            'error': 'AI service unavailable',
            'message': str(e)
        }), 503
    except OllamaError as e:
        logger.error(f"Ollama error: {e}")
        return jsonify({
            'error': 'AI processing failed',
            'message': str(e)
        }), 500
    except ValueError as e:
        return jsonify({
            'error': 'Query parsing failed',
            'message': str(e)
        }), 400
    except Exception as e:
        logger.exception(f"Unexpected error in NL query: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500


@api_v1_bp.route('/assistant/explain', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('analytics.query')
@async_route
async def explain_query_results():
    """
    Generate natural language explanation of query results.
    
    ---
    tags:
      - AI Assistant
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - query_description
              - row_count
            properties:
              query_description:
                type: string
              dimensions:
                type: array
                items:
                  type: string
              measures:
                type: array
                items:
                  type: string
              row_count:
                type: integer
              sample_data:
                type: array
                items:
                  type: object
    responses:
      200:
        description: Explanation generated successfully
      503:
        description: AI service unavailable
    """
    try:
        data = ExplainRequest(**request.json)
    except ValidationError as e:
        return jsonify({'error': 'Invalid request', 'details': e.errors()}), 400
    
    try:
        ollama_client = get_ollama_client()
        nl_service = NLToParametersService(ollama_client)
        
        explanation = await nl_service.explain_results(
            query_description=data.query_description,
            dimensions=data.dimensions,
            measures=data.measures,
            row_count=data.row_count,
            sample_data=data.sample_data
        )
        
        await ollama_client.close()
        
        return jsonify({
            'explanation': explanation.model_dump()
        }), 200
        
    except OllamaConnectionError as e:
        return jsonify({
            'error': 'AI service unavailable',
            'message': str(e)
        }), 503
    except Exception as e:
        logger.exception(f"Error generating explanation: {e}")
        return jsonify({
            'error': 'Failed to generate explanation',
            'message': str(e)
        }), 500


@api_v1_bp.route('/assistant/suggest', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('analytics.query')
@async_route
async def suggest_analyses():
    """
    Suggest interesting analyses based on available data.
    
    ---
    tags:
      - AI Assistant
    security:
      - bearerAuth: []
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              context:
                type: string
                description: Optional user context for suggestions
    responses:
      200:
        description: Suggestions generated successfully
      503:
        description: AI service unavailable
    """
    try:
        data = SuggestRequest(**(request.json or {}))
    except ValidationError as e:
        return jsonify({'error': 'Invalid request', 'details': e.errors()}), 400
    
    tenant_id = g.tenant_id
    
    try:
        # Build schema description
        semantic_models = SemanticService.list_models(tenant_id)
        
        schema_parts = []
        for model in semantic_models:
            dimensions = SemanticService.list_dimensions(model.id)
            measures = SemanticService.list_measures(model.id)
            
            schema_parts.append(f"""
Model: {model.name}
  Dimensions: {', '.join(d.name for d in dimensions)}
  Measures: {', '.join(m.name for m in measures)}
""")
        
        schema_description = '\n'.join(schema_parts)
        
        if not schema_description.strip():
            return jsonify({
                'suggestions': [],
                'message': 'No semantic models available for suggestions'
            }), 200
        
        ollama_client = get_ollama_client()
        nl_service = NLToParametersService(ollama_client)
        
        suggestions = await nl_service.suggest_analyses(
            schema_description=schema_description,
            user_context=data.context
        )
        
        await ollama_client.close()
        
        return jsonify({
            'suggestions': [s.model_dump() for s in suggestions]
        }), 200
        
    except OllamaConnectionError as e:
        return jsonify({
            'error': 'AI service unavailable',
            'message': str(e)
        }), 503
    except Exception as e:
        logger.exception(f"Error generating suggestions: {e}")
        return jsonify({
            'error': 'Failed to generate suggestions',
            'message': str(e)
        }), 500


@api_v1_bp.route('/assistant/health', methods=['GET'])
@async_route
async def ollama_health():
    """
    Check Ollama service health.
    
    ---
    tags:
      - AI Assistant
    responses:
      200:
        description: Ollama is healthy
      503:
        description: Ollama is unavailable
    """
    try:
        ollama_client = get_ollama_client()
        is_healthy = await ollama_client.health_check()
        
        if is_healthy:
            # Also get model info
            try:
                models = await ollama_client.list_models()
                model_names = [m.get('name', 'unknown') for m in models]
            except Exception:
                model_names = []
            
            await ollama_client.close()
            
            return jsonify({
                'status': 'healthy',
                'service': 'ollama',
                'available_models': model_names
            }), 200
        else:
            await ollama_client.close()
            return jsonify({
                'status': 'unhealthy',
                'service': 'ollama',
                'message': 'Health check failed'
            }), 503
            
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'service': 'ollama',
            'message': str(e)
        }), 503


# =============================================================================
# NL-to-SQL Endpoint
# =============================================================================

class NLToSQLRequest(BaseModel):
    """Request model for NL-to-SQL conversion."""
    query: str = Field(..., min_length=1, max_length=2000, description="Natural language query")
    model_filter: Optional[str] = Field(None, description="Optional semantic model name to filter")
    strict_mode: bool = Field(True, description="Fail on unresolved entities if true")
    include_sql: bool = Field(True, description="Include generated SQL in response")


@api_v1_bp.route('/assistant/nl-to-sql', methods=['POST'])
@jwt_required()
@require_tenant_context
@require_permission('analytics.query')
@async_route
async def nl_to_sql():
    """
    Convert natural language to ClickHouse SQL.
    
    This endpoint:
    1. Classifies the query intent (aggregation, trend, comparison, etc.)
    2. Extracts parameters from natural language
    3. Resolves entities against the semantic layer
    4. Generates SQL from validated templates (ADR-002 compliant)
    
    SECURITY: All SQL is generated from pre-approved templates.
    LLM output is NEVER used as SQL directly.
    
    ---
    tags:
      - AI Assistant
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required:
              - query
            properties:
              query:
                type: string
                description: Natural language query
                example: "Show me total revenue by region for the last 6 months"
              model_filter:
                type: string
                description: Optional semantic model name to filter entities
              strict_mode:
                type: boolean
                default: true
                description: Fail on unresolved entities if true
              include_sql:
                type: boolean
                default: true
                description: Include generated SQL in response
    responses:
      200:
        description: Query successfully converted to SQL
        content:
          application/json:
            schema:
              type: object
              properties:
                sql:
                  type: string
                  description: Generated ClickHouse SQL query
                intent:
                  type: object
                  properties:
                    type:
                      type: string
                      enum: [aggregation, comparison, trend, top_n, filter, drill_down]
                    confidence:
                      type: number
                explanation:
                  type: string
                  description: Human-readable explanation of the query
                warnings:
                  type: array
                  items:
                    type: string
      400:
        description: Invalid request or query parsing failed
      503:
        description: AI service unavailable
    """
    from app.services.nl_to_sql import (
        NLToSQLService, 
        NLToSQLError,
        QueryParsingError,
        SemanticResolutionError,
        SQLGenerationError,
    )
    
    try:
        data = NLToSQLRequest(**request.json)
    except ValidationError as e:
        return jsonify({'error': 'Invalid request', 'details': e.errors()}), 400
    
    tenant_id = g.tenant_id
    
    try:
        # Initialize services
        ollama_client = get_ollama_client()
        nl_to_sql_service = NLToSQLService(ollama_client)
        
        # Convert natural language to SQL
        result = await nl_to_sql_service.convert(
            tenant_id=tenant_id,
            natural_language=data.query,
            model_filter=data.model_filter,
            strict_mode=data.strict_mode
        )
        
        await ollama_client.close()
        
        # Build response
        response = {
            'intent': {
                'type': result.intent.query_type.value,
                'confidence': result.intent.confidence,
                'entities': {
                    'dimensions': result.intent.entities.dimensions,
                    'measures': result.intent.entities.measures,
                },
            },
            'resolved': {
                'dimensions': [d.name for d in result.resolved_dimensions],
                'measures': [m.name for m in result.resolved_measures],
            },
            'explanation': result.explanation,
            'confidence': result.confidence,
            'warnings': result.warnings,
        }
        
        # Include SQL if requested
        if data.include_sql:
            response['sql'] = result.sql
        
        return jsonify(response), 200
        
    except QueryParsingError as e:
        return jsonify({
            'error': 'Failed to parse query',
            'message': str(e),
            'error_type': 'parsing'
        }), 400
        
    except SemanticResolutionError as e:
        return jsonify({
            'error': 'Failed to resolve semantic entities',
            'message': str(e),
            'error_type': 'resolution'
        }), 400
        
    except SQLGenerationError as e:
        return jsonify({
            'error': 'Failed to generate SQL',
            'message': str(e),
            'error_type': 'generation'
        }), 400
        
    except OllamaConnectionError as e:
        return jsonify({
            'error': 'AI service unavailable',
            'message': str(e)
        }), 503
        
    except Exception as e:
        logger.error(f"NL-to-SQL conversion failed: {e}", exc_info=True)
        return jsonify({
            'error': 'Internal error',
            'message': str(e)
        }), 500


@api_v1_bp.route('/assistant/nl-to-sql/suggestions', methods=['GET'])
@jwt_required()
@require_tenant_context
@require_permission('analytics.query')
@async_route
async def nl_to_sql_suggestions():
    """
    Get suggested natural language queries based on available semantic entities.
    
    ---
    tags:
      - AI Assistant
    security:
      - bearerAuth: []
    parameters:
      - name: context
        in: query
        type: string
        description: Optional context for suggestions
    responses:
      200:
        description: List of suggested queries
    """
    from app.services.nl_to_sql import NLToSQLService
    
    tenant_id = g.tenant_id
    context = request.args.get('context', '')
    
    try:
        ollama_client = get_ollama_client()
        nl_to_sql_service = NLToSQLService(ollama_client)
        
        suggestions = await nl_to_sql_service.suggest_queries(
            tenant_id=tenant_id,
            context=context or None
        )
        
        await ollama_client.close()
        
        return jsonify({
            'suggestions': suggestions
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to generate suggestions: {e}", exc_info=True)
        return jsonify({
            'suggestions': [],
            'error': str(e)
        }), 200  # Return empty suggestions, not an error


@api_v1_bp.route('/assistant/models', methods=['GET'])
@jwt_required()
@async_route
async def list_ollama_models():
    """
    List available Ollama models.
    
    ---
    tags:
      - AI Assistant
    security:
      - bearerAuth: []
    responses:
      200:
        description: List of available models
      503:
        description: Ollama is unavailable
    """
    try:
        ollama_client = get_ollama_client()
        models = await ollama_client.list_models()
        await ollama_client.close()
        
        return jsonify({
            'models': [
                {
                    'name': m.get('name'),
                    'size': m.get('size'),
                    'modified_at': m.get('modified_at'),
                }
                for m in models
            ]
        }), 200
        
    except OllamaConnectionError as e:
        return jsonify({
            'error': 'AI service unavailable',
            'message': str(e)
        }), 503
