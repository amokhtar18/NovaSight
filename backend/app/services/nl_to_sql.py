"""
NovaSight NL-to-SQL Service
============================

Converts natural language to SQL via the semantic layer.
Implements ADR-002: LLM generates INTENT only, SQL comes from templates.

Flow:
1. Classify query intent (LLM)
2. Extract parameters (LLM)
3. Resolve to semantic model objects (Database)
4. Build SQL from template (Template Engine)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from app.models.semantic import Dimension, Measure, SemanticModel
from app.services.ollama.client import OllamaClient
from app.services.ollama.query_classifier import (
    QueryClassifier,
    QueryType,
    ClassifiedIntent,
)
from app.services.ollama.nl_to_params import (
    NLToParametersService,
    QueryIntent,
)
from app.services.query_builder import (
    QueryBuilder,
    QueryBuilderError,
)
from app.services.semantic_service import (
    SemanticService,
    SemanticServiceError,
)

logger = logging.getLogger(__name__)


class NLToSQLError(Exception):
    """Base exception for NL-to-SQL errors."""
    pass


class QueryParsingError(NLToSQLError):
    """Raised when query parsing fails."""
    pass


class SemanticResolutionError(NLToSQLError):
    """Raised when semantic entity resolution fails."""
    pass


class SQLGenerationError(NLToSQLError):
    """Raised when SQL generation fails."""
    pass


class NLToSQLResult:
    """
    Result of NL-to-SQL conversion.
    
    Contains the generated SQL along with metadata about the conversion
    process for transparency and debugging.
    """
    
    def __init__(
        self,
        sql: str,
        intent: ClassifiedIntent,
        params: QueryIntent,
        resolved_dimensions: List[Dimension],
        resolved_measures: List[Measure],
        explanation: str,
        confidence: float,
        warnings: Optional[List[str]] = None
    ):
        self.sql = sql
        self.intent = intent
        self.params = params
        self.resolved_dimensions = resolved_dimensions
        self.resolved_measures = resolved_measures
        self.explanation = explanation
        self.confidence = confidence
        self.warnings = warnings or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'sql': self.sql,
            'intent': {
                'type': self.intent.query_type.value,
                'confidence': self.intent.confidence,
                'entities': self.intent.entities.model_dump() if hasattr(self.intent.entities, 'model_dump') else {},
                'time_range': self.intent.time_range.model_dump() if self.intent.time_range else None,
            },
            'params': self.params.model_dump() if hasattr(self.params, 'model_dump') else {},
            'resolved': {
                'dimensions': [d.name for d in self.resolved_dimensions],
                'measures': [m.name for m in self.resolved_measures],
            },
            'explanation': self.explanation,
            'confidence': self.confidence,
            'warnings': self.warnings,
        }


class NLToSQLService:
    """
    Converts natural language to SQL via the semantic layer.
    
    This service orchestrates the NL-to-SQL pipeline:
    1. Query Classification: Determine the type of query (aggregation, trend, etc.)
    2. Parameter Extraction: Extract dimensions, measures, filters from NL
    3. Semantic Resolution: Map extracted names to validated semantic objects
    4. SQL Generation: Build SQL from templates using resolved objects
    
    SECURITY (ADR-002):
    - LLM output is NEVER used as SQL directly
    - All SQL is generated from pre-approved templates
    - Entity names are resolved against the semantic layer
    - Only validated model objects reach the query builder
    """
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        query_builder: Optional[QueryBuilder] = None,
        semantic_service_class: Optional[type] = None
    ):
        """
        Initialize NL-to-SQL service.
        
        Args:
            ollama_client: Configured Ollama client
            query_builder: Query builder instance (creates default if not provided)
            semantic_service_class: SemanticService class (for dependency injection)
        """
        self.ollama = ollama_client
        self.classifier = QueryClassifier(ollama_client)
        self.param_extractor = NLToParametersService(ollama_client)
        self.builder = query_builder or QueryBuilder()
        self.semantic_class = semantic_service_class or SemanticService
    
    async def convert(
        self,
        tenant_id: str,
        natural_language: str,
        model_filter: Optional[str] = None,
        strict_mode: bool = True
    ) -> NLToSQLResult:
        """
        Convert natural language to executable SQL.
        
        Args:
            tenant_id: Tenant identifier
            natural_language: User's natural language query
            model_filter: Optional semantic model name to filter entities
            strict_mode: If True, fail on unresolved entities. If False, skip them.
        
        Returns:
            NLToSQLResult with SQL and metadata
        
        Raises:
            QueryParsingError: If query classification/extraction fails
            SemanticResolutionError: If entity resolution fails
            SQLGenerationError: If SQL generation fails
        """
        logger.info(f"Converting NL to SQL for tenant {tenant_id}: {natural_language[:100]}...")
        warnings: List[str] = []
        
        # Get available semantic entities
        try:
            dim_names, measure_names, all_dimensions, all_measures = \
                self._get_available_entities(tenant_id, model_filter)
        except Exception as e:
            logger.error(f"Failed to get semantic entities: {e}")
            raise SemanticResolutionError(f"Failed to load semantic layer: {e}")
        
        if not dim_names and not measure_names:
            raise SemanticResolutionError(
                "No semantic entities available. Please configure the semantic layer."
            )
        
        # Step 1: Classify query
        try:
            intent = await self.classifier.classify(
                natural_language, dim_names, measure_names
            )
        except Exception as e:
            logger.error(f"Query classification failed: {e}")
            raise QueryParsingError(f"Failed to understand query: {e}")
        
        # Step 2: Extract parameters
        try:
            params = await self.param_extractor.parse_query(
                natural_language, dim_names, measure_names,
                strict=strict_mode
            )
        except Exception as e:
            logger.error(f"Parameter extraction failed: {e}")
            raise QueryParsingError(f"Failed to extract query parameters: {e}")
        
        # Step 3: Resolve to model objects
        resolved_dims, resolved_measures, resolution_warnings = self._resolve_entities(
            params.dimensions,
            params.measures,
            all_dimensions,
            all_measures,
            strict_mode
        )
        warnings.extend(resolution_warnings)
        
        if not resolved_dims and not resolved_measures:
            raise SemanticResolutionError(
                "Could not resolve any dimensions or measures from the query."
            )
        
        # Step 4: Build SQL from template
        try:
            sql = self._generate_sql(
                tenant_id=tenant_id,
                intent=intent,
                params=params,
                dimensions=resolved_dims,
                measures=resolved_measures
            )
        except QueryBuilderError as e:
            logger.error(f"SQL generation failed: {e}")
            raise SQLGenerationError(f"Failed to generate SQL: {e}")
        
        # Generate explanation
        explanation = self._generate_explanation(intent, params, resolved_dims, resolved_measures)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(
            intent.confidence,
            len(resolved_dims),
            len(params.dimensions),
            len(resolved_measures),
            len(params.measures)
        )
        
        return NLToSQLResult(
            sql=sql,
            intent=intent,
            params=params,
            resolved_dimensions=resolved_dims,
            resolved_measures=resolved_measures,
            explanation=explanation,
            confidence=confidence,
            warnings=warnings
        )
    
    def _get_available_entities(
        self,
        tenant_id: str,
        model_filter: Optional[str] = None
    ) -> Tuple[List[str], List[str], List[Dimension], List[Measure]]:
        """
        Get available semantic entities for a tenant.
        
        Returns:
            Tuple of (dimension_names, measure_names, all_dimensions, all_measures)
        """
        models = self.semantic_class.list_models(tenant_id)
        
        if model_filter:
            models = [m for m in models if m.name == model_filter]
        
        all_dimensions: List[Dimension] = []
        all_measures: List[Measure] = []
        
        for model in models:
            # Get dimensions and measures for this model
            dims = list(model.dimensions.all()) if hasattr(model.dimensions, 'all') else []
            meas = list(model.measures.all()) if hasattr(model.measures, 'all') else []
            
            # Filter out hidden entities
            all_dimensions.extend([d for d in dims if not d.is_hidden])
            all_measures.extend([m for m in meas if not m.is_hidden])
        
        dim_names = [d.name for d in all_dimensions]
        measure_names = [m.name for m in all_measures]
        
        logger.debug(
            f"Available entities: {len(dim_names)} dimensions, {len(measure_names)} measures"
        )
        
        return dim_names, measure_names, all_dimensions, all_measures
    
    def _resolve_entities(
        self,
        dimension_names: List[str],
        measure_names: List[str],
        all_dimensions: List[Dimension],
        all_measures: List[Measure],
        strict: bool
    ) -> Tuple[List[Dimension], List[Measure], List[str]]:
        """
        Resolve dimension and measure names to model objects.
        
        This is a critical security step - we only accept entities
        that exist in the semantic layer, preventing arbitrary SQL injection.
        """
        warnings: List[str] = []
        
        # Build lookup maps (case-insensitive)
        dim_map = {d.name.lower(): d for d in all_dimensions}
        measure_map = {m.name.lower(): m for m in all_measures}
        
        # Resolve dimensions
        resolved_dims: List[Dimension] = []
        for name in dimension_names:
            if name.lower() in dim_map:
                resolved_dims.append(dim_map[name.lower()])
            else:
                msg = f"Dimension '{name}' not found in semantic layer"
                if strict:
                    logger.warning(msg)
                warnings.append(msg)
        
        # Resolve measures
        resolved_measures: List[Measure] = []
        for name in measure_names:
            if name.lower() in measure_map:
                resolved_measures.append(measure_map[name.lower()])
            else:
                msg = f"Measure '{name}' not found in semantic layer"
                if strict:
                    logger.warning(msg)
                warnings.append(msg)
        
        return resolved_dims, resolved_measures, warnings
    
    def _generate_sql(
        self,
        tenant_id: str,
        intent: ClassifiedIntent,
        params: QueryIntent,
        dimensions: List[Dimension],
        measures: List[Measure]
    ) -> str:
        """
        Generate SQL based on query type.
        
        Routes to the appropriate query builder method based on
        the classified query type.
        """
        query_type = intent.query_type
        
        # Convert filters to expected format
        filters = [
            {
                'column': f.column,
                'operator': f.operator,
                'value': f.value
            }
            for f in params.filters
        ] if params.filters else None
        
        # Convert order_by to expected format
        order_by = [
            {
                'column': o.column,
                'direction': o.direction
            }
            for o in params.order_by
        ] if params.order_by else None
        
        if query_type == QueryType.AGGREGATION:
            return self.builder.build_aggregation_query(
                tenant_id=tenant_id,
                dimensions=dimensions,
                measures=measures,
                filters=filters,
                order_by=order_by,
                limit=params.limit
            )
        
        elif query_type == QueryType.COMPARISON:
            return self.builder.build_comparison_query(
                tenant_id=tenant_id,
                dimensions=dimensions,
                measures=measures,
                compare_dimension=intent.entities.compare_dimension or '',
                compare_values=intent.entities.compare_values,
                filters=filters
            )
        
        elif query_type == QueryType.TREND:
            # Find time dimension
            time_dim = None
            if params.time_dimension:
                for d in dimensions:
                    if d.name.lower() == params.time_dimension.lower():
                        time_dim = d
                        break
            
            if not time_dim and dimensions:
                # Try to find a temporal dimension
                for d in dimensions:
                    if d.type and d.type.value == 'temporal':
                        time_dim = d
                        break
                if not time_dim:
                    # Fallback to first dimension
                    time_dim = dimensions[0]
            
            if not time_dim:
                raise SQLGenerationError("Trend query requires a time dimension")
            
            # Remove time dimension from grouping dimensions
            other_dims = [d for d in dimensions if d.id != time_dim.id]
            
            # Determine granularity with fallback
            granularity = 'day'
            if intent.time_range and intent.time_range.granularity:
                granularity = intent.time_range.granularity
            
            return self.builder.build_trend_query(
                tenant_id=tenant_id,
                time_dimension=time_dim,
                measures=measures,
                granularity=granularity,
                start_date=params.date_from or (intent.time_range.start if intent.time_range else None),
                end_date=params.date_to or (intent.time_range.end if intent.time_range else None),
                dimensions=other_dims,
                filters=filters
            )
        
        elif query_type == QueryType.TOP_N:
            if not dimensions:
                raise SQLGenerationError("Top N query requires at least one dimension")
            
            return self.builder.build_top_n_query(
                tenant_id=tenant_id,
                dimension=dimensions[0],
                measures=measures,
                n=intent.entities.top_n or 10,
                order_direction='DESC',
                filters=filters
            )
        
        elif query_type in (QueryType.FILTER, QueryType.DRILL_DOWN):
            # These use standard aggregation with specific filters/dimensions
            return self.builder.build_aggregation_query(
                tenant_id=tenant_id,
                dimensions=dimensions,
                measures=measures,
                filters=filters,
                order_by=order_by,
                limit=params.limit
            )
        
        else:
            # Default to aggregation
            logger.warning(f"Unknown query type {query_type}, using aggregation")
            return self.builder.build_aggregation_query(
                tenant_id=tenant_id,
                dimensions=dimensions,
                measures=measures,
                filters=filters,
                order_by=order_by,
                limit=params.limit
            )
    
    def _generate_explanation(
        self,
        intent: ClassifiedIntent,
        params: QueryIntent,
        dimensions: List[Dimension],
        measures: List[Measure]
    ) -> str:
        """Generate a human-readable explanation of the query."""
        dim_labels = [d.label or d.name for d in dimensions]
        measure_labels = [m.label or m.name for m in measures]
        
        query_type_descriptions = {
            QueryType.AGGREGATION: "calculate",
            QueryType.COMPARISON: "compare",
            QueryType.TREND: "show trend of",
            QueryType.TOP_N: f"find top {intent.entities.top_n or 10}",
            QueryType.FILTER: "filter and show",
            QueryType.DRILL_DOWN: "break down",
            QueryType.DISTRIBUTION: "show distribution of",
            QueryType.CORRELATION: "analyze correlation between",
        }
        
        action = query_type_descriptions.get(intent.query_type, "calculate")
        
        # Build explanation
        parts = [f"This query will {action}"]
        
        if measure_labels:
            parts.append(f" {', '.join(measure_labels)}")
        
        if dim_labels:
            if intent.query_type == QueryType.COMPARISON:
                parts.append(f" comparing {intent.entities.compare_dimension}")
            else:
                parts.append(f" grouped by {', '.join(dim_labels)}")
        
        if params.filters:
            filter_strs = [f"{f.column} {f.operator} {f.value}" for f in params.filters[:3]]
            parts.append(f" where {' and '.join(filter_strs)}")
            if len(params.filters) > 3:
                parts.append(f" (and {len(params.filters) - 3} more filters)")
        
        if intent.time_range:
            if intent.time_range.start and intent.time_range.end:
                parts.append(f" from {intent.time_range.start} to {intent.time_range.end}")
            elif intent.time_range.start:
                parts.append(f" since {intent.time_range.start}")
        
        return ''.join(parts) + '.'
    
    def _calculate_confidence(
        self,
        classification_confidence: float,
        resolved_dims: int,
        requested_dims: int,
        resolved_measures: int,
        requested_measures: int
    ) -> float:
        """Calculate overall confidence score."""
        # Resolution ratio
        total_requested = requested_dims + requested_measures
        total_resolved = resolved_dims + resolved_measures
        
        if total_requested > 0:
            resolution_ratio = total_resolved / total_requested
        else:
            resolution_ratio = 0.5
        
        # Combine classification and resolution confidence
        confidence = (classification_confidence * 0.6) + (resolution_ratio * 0.4)
        
        # Must have at least some resolved entities
        if total_resolved == 0:
            confidence *= 0.3
        
        return round(confidence, 3)
    
    async def suggest_queries(
        self,
        tenant_id: str,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest example queries based on available semantic entities.
        
        Args:
            tenant_id: Tenant identifier
            context: Optional context about what user is looking for
        
        Returns:
            List of suggested queries with descriptions
        """
        try:
            dim_names, measure_names, all_dimensions, all_measures = \
                self._get_available_entities(tenant_id)
        except Exception:
            return []
        
        suggestions = []
        
        # Generate suggestions based on available entities
        if measure_names and dim_names:
            # Basic aggregation
            suggestions.append({
                'query': f"Show total {measure_names[0]} by {dim_names[0]}",
                'description': 'Simple aggregation query',
                'type': 'aggregation'
            })
            
            # Trend if time dimension available
            time_dims = [d for d in all_dimensions if d.type and d.type.value == 'temporal']
            if time_dims:
                suggestions.append({
                    'query': f"Show {measure_names[0]} trend over the last 6 months",
                    'description': 'Time series analysis',
                    'type': 'trend'
                })
            
            # Top N
            suggestions.append({
                'query': f"Top 10 {dim_names[0]} by {measure_names[0]}",
                'description': 'Ranking query',
                'type': 'top_n'
            })
            
            # Comparison if multiple dimensions
            if len(dim_names) >= 2:
                suggestions.append({
                    'query': f"Compare {measure_names[0]} between different {dim_names[0]}",
                    'description': 'Comparison query',
                    'type': 'comparison'
                })
        
        return suggestions
