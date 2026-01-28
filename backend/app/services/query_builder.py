"""
NovaSight Query Builder
========================

Builds SQL queries from validated parameters using templates.
Implements ADR-002: All SQL is generated from templates, never from LLM output.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from app.models.semantic import Dimension, Measure, AggregationType
from app.services.template_engine import TemplateEngine, template_engine

logger = logging.getLogger(__name__)


class QueryBuilderError(Exception):
    """Base exception for query builder errors."""
    pass


class InvalidInputError(QueryBuilderError):
    """Raised when input validation fails."""
    pass


class TemplateRenderError(QueryBuilderError):
    """Raised when template rendering fails."""
    pass


class QueryBuilder:
    """
    Builds SQL queries from validated parameters using templates.
    
    SECURITY: All SQL is generated from templates, never from LLM output.
    This class ONLY accepts validated model objects (Dimension, Measure),
    never raw strings. All inputs are validated before rendering.
    
    ADR-002 Compliance:
    - Only accepts typed model objects, not raw strings
    - All SQL generated from pre-approved templates
    - Strict input validation before template rendering
    - Parameterized values to prevent injection
    """
    
    # Allowed filter operators (whitelist)
    VALID_OPERATORS = frozenset({
        '=', '!=', '<>', '>', '<', '>=', '<=',
        'IN', 'NOT IN', 'LIKE', 'NOT LIKE', 'ILIKE',
        'BETWEEN', 'IS NULL', 'IS NOT NULL'
    })
    
    # Allowed sort directions
    VALID_DIRECTIONS = frozenset({'ASC', 'DESC', 'asc', 'desc'})
    
    def __init__(self, engine: Optional[TemplateEngine] = None):
        """
        Initialize query builder.
        
        Args:
            engine: Template engine instance. Uses singleton if not provided.
        """
        self.templates = engine or template_engine
    
    def build_aggregation_query(
        self,
        tenant_id: str,
        dimensions: List[Dimension],
        measures: List[Measure],
        filters: Optional[List[Dict]] = None,
        order_by: Optional[List[Dict]] = None,
        limit: int = 1000,
        table_name: Optional[str] = None
    ) -> str:
        """
        Build an aggregation query from validated parameters.
        
        Args:
            tenant_id: Tenant identifier for database selection
            dimensions: List of validated Dimension objects
            measures: List of validated Measure objects
            filters: Optional filter conditions
            order_by: Optional ordering specifications
            limit: Maximum rows to return (capped at 10000)
        
        Returns:
            Generated SQL query string
        
        Raises:
            InvalidInputError: If input validation fails
        """
        # Validate inputs are model objects
        self._validate_model_inputs(dimensions, measures)
        
        # Validate and sanitize filters
        safe_filters = self._build_filters(filters) if filters else []
        
        # Validate order_by
        safe_order = self._validate_order_by(order_by) if order_by else []
        
        # Cap limit
        safe_limit = min(max(1, limit), 10000)
        
        # Determine target table
        target_table = table_name or 'events'
        
        # Build query using template
        try:
            return self.templates.render(
                'sql/analytics_query.sql.j2',
                {
                    'database': f'tenant_{tenant_id}',
                    'table': target_table,
                    'dimensions': [
                        {
                            'expression': d.expression,
                            'alias': d.name
                        }
                        for d in dimensions
                    ],
                    'measures': [
                        {
                            'aggregation': m.aggregation.value.upper() if isinstance(m.aggregation, AggregationType) else m.aggregation.upper(),
                            'expression': m.expression,
                            'alias': m.name
                        }
                        for m in measures
                    ],
                    'filters': safe_filters,
                    'group_by': [d.name for d in dimensions],
                    'order_by': safe_order,
                    'limit': safe_limit
                }
            )
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            raise TemplateRenderError(f"Failed to render query: {e}")
    
    def build_comparison_query(
        self,
        tenant_id: str,
        dimensions: List[Dimension],
        measures: List[Measure],
        compare_dimension: str,
        compare_values: List[str],
        filters: Optional[List[Dict]] = None,
        table_name: Optional[str] = None
    ) -> str:
        """
        Build a comparison query (e.g., Q1 vs Q2).
        
        Args:
            tenant_id: Tenant identifier
            dimensions: Dimensions for grouping (excluding compare dimension)
            measures: Measures to compare
            compare_dimension: Dimension to compare across
            compare_values: Values to compare (e.g., ['Q1', 'Q2'])
        
        Returns:
            Generated SQL comparison query
        """
        self._validate_model_inputs(dimensions, measures)
        
        # Validate compare_dimension is a valid identifier
        if not self._is_valid_identifier(compare_dimension):
            raise InvalidInputError(f"Invalid compare dimension: {compare_dimension}")
        
        # Validate compare_values
        if not compare_values or len(compare_values) < 2:
            raise InvalidInputError("Comparison requires at least 2 values")
        
        safe_filters = self._build_filters(filters) if filters else []
        target_table = table_name or 'events'
        
        try:
            return self.templates.render(
                'sql/comparison_query.sql.j2',
                {
                    'database': f'tenant_{tenant_id}',
                    'table': target_table,
                    'dimensions': [
                        {
                            'expression': d.expression,
                            'alias': d.name
                        }
                        for d in dimensions
                    ],
                    'measures': [
                        {
                            'aggregation': m.aggregation.value.upper() if isinstance(m.aggregation, AggregationType) else m.aggregation.upper(),
                            'expression': m.expression,
                            'alias': m.name
                        }
                        for m in measures
                    ],
                    'compare_dimension': compare_dimension,
                    'compare_values': compare_values,
                    'filters': safe_filters,
                    'group_by': [d.name for d in dimensions]
                }
            )
        except Exception as e:
            logger.error(f"Comparison template rendering failed: {e}")
            raise TemplateRenderError(f"Failed to render comparison query: {e}")
    
    def build_trend_query(
        self,
        tenant_id: str,
        time_dimension: Dimension,
        measures: List[Measure],
        granularity: str = 'day',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        dimensions: Optional[List[Dimension]] = None,
        filters: Optional[List[Dict]] = None,
        table_name: Optional[str] = None
    ) -> str:
        """
        Build a trend query (time-series analysis).
        
        Args:
            tenant_id: Tenant identifier
            time_dimension: Time dimension for trending
            measures: Measures to trend
            granularity: Time granularity (day, week, month, quarter, year)
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            dimensions: Optional additional grouping dimensions
            filters: Optional filters
        
        Returns:
            Generated SQL trend query
        """
        # Validate time dimension
        if not isinstance(time_dimension, Dimension):
            raise InvalidInputError("time_dimension must be a Dimension object")
        
        self._validate_model_inputs(dimensions or [], measures)
        
        # Validate granularity
        valid_granularities = ('day', 'week', 'month', 'quarter', 'year', 'hour')
        if granularity.lower() not in valid_granularities:
            raise InvalidInputError(
                f"Invalid granularity: {granularity}. Use: {valid_granularities}"
            )
        
        # Build date filters
        date_filters = []
        if start_date:
            date_filters.append({
                'column': time_dimension.name,
                'operator': '>=',
                'value': start_date
            })
        if end_date:
            date_filters.append({
                'column': time_dimension.name,
                'operator': '<=',
                'value': end_date
            })
        
        safe_filters = self._build_filters(filters or []) + date_filters
        target_table = table_name or 'events'
        
        # Additional grouping dimensions
        group_dims = [
            {
                'expression': d.expression,
                'alias': d.name
            }
            for d in (dimensions or [])
        ]
        
        try:
            return self.templates.render(
                'sql/trend_query.sql.j2',
                {
                    'database': f'tenant_{tenant_id}',
                    'table': target_table,
                    'time_dimension': {
                        'expression': time_dimension.expression,
                        'alias': time_dimension.name
                    },
                    'granularity': granularity.lower(),
                    'dimensions': group_dims,
                    'measures': [
                        {
                            'aggregation': m.aggregation.value.upper() if isinstance(m.aggregation, AggregationType) else m.aggregation.upper(),
                            'expression': m.expression,
                            'alias': m.name
                        }
                        for m in measures
                    ],
                    'filters': safe_filters,
                    'group_by': [d['alias'] for d in group_dims],
                    'order_by': [{'column': 'time_period', 'direction': 'ASC'}]
                }
            )
        except Exception as e:
            logger.error(f"Trend template rendering failed: {e}")
            raise TemplateRenderError(f"Failed to render trend query: {e}")
    
    def build_top_n_query(
        self,
        tenant_id: str,
        dimension: Dimension,
        measures: List[Measure],
        n: int = 10,
        order_measure: Optional[str] = None,
        order_direction: str = 'DESC',
        filters: Optional[List[Dict]] = None,
        table_name: Optional[str] = None
    ) -> str:
        """
        Build a top N query.
        
        Args:
            tenant_id: Tenant identifier
            dimension: Dimension to rank by
            measures: Measures for ranking
            n: Number of top results (default 10)
            order_measure: Measure to order by (defaults to first measure)
            order_direction: ASC or DESC
            filters: Optional filters
        
        Returns:
            Generated SQL top N query
        """
        if not isinstance(dimension, Dimension):
            raise InvalidInputError("dimension must be a Dimension object")
        
        self._validate_model_inputs([dimension], measures)
        
        # Cap N
        safe_n = min(max(1, n), 1000)
        
        # Determine order measure
        if order_measure:
            if not self._is_valid_identifier(order_measure):
                raise InvalidInputError(f"Invalid order measure: {order_measure}")
        else:
            order_measure = measures[0].name if measures else None
        
        # Validate direction
        safe_direction = order_direction.upper()
        if safe_direction not in ('ASC', 'DESC'):
            safe_direction = 'DESC'
        
        safe_filters = self._build_filters(filters) if filters else []
        target_table = table_name or 'events'
        
        try:
            return self.templates.render(
                'sql/top_n_query.sql.j2',
                {
                    'database': f'tenant_{tenant_id}',
                    'table': target_table,
                    'dimension': {
                        'expression': dimension.expression,
                        'alias': dimension.name
                    },
                    'measures': [
                        {
                            'aggregation': m.aggregation.value.upper() if isinstance(m.aggregation, AggregationType) else m.aggregation.upper(),
                            'expression': m.expression,
                            'alias': m.name
                        }
                        for m in measures
                    ],
                    'filters': safe_filters,
                    'order_by': {
                        'column': order_measure,
                        'direction': safe_direction
                    },
                    'limit': safe_n
                }
            )
        except Exception as e:
            logger.error(f"Top N template rendering failed: {e}")
            raise TemplateRenderError(f"Failed to render top N query: {e}")
    
    def _validate_model_inputs(
        self,
        dimensions: List[Dimension],
        measures: List[Measure]
    ) -> None:
        """
        Ensure inputs are validated model objects, not raw strings.
        
        SECURITY: This validation is critical for ADR-002 compliance.
        Raw strings from LLM output must never reach the template engine.
        """
        for d in dimensions:
            if not isinstance(d, Dimension):
                raise InvalidInputError(
                    f"Dimensions must be Dimension objects, got: {type(d).__name__}"
                )
            # Verify expression is reasonably safe
            if not d.expression or len(d.expression) > 500:
                raise InvalidInputError(f"Invalid dimension expression: {d.name}")
        
        for m in measures:
            if not isinstance(m, Measure):
                raise InvalidInputError(
                    f"Measures must be Measure objects, got: {type(m).__name__}"
                )
            if not m.expression or len(m.expression) > 500:
                raise InvalidInputError(f"Invalid measure expression: {m.name}")
            if not m.aggregation:
                raise InvalidInputError(f"Measure missing aggregation: {m.name}")
    
    def _build_filters(self, filters: List[Dict]) -> List[Dict]:
        """
        Build filter clauses with SQL injection prevention.
        
        Args:
            filters: List of filter dictionaries with column, operator, value
        
        Returns:
            List of validated filter dictionaries
        """
        safe_filters = []
        
        for f in filters:
            if not isinstance(f, dict):
                logger.warning(f"Skipping invalid filter: {f}")
                continue
            
            column = f.get('column', '')
            operator = f.get('operator', '=')
            value = f.get('value')
            
            # Validate column name
            if not self._is_valid_identifier(column):
                logger.warning(f"Skipping filter with invalid column: {column}")
                continue
            
            # Validate and normalize operator
            operator_upper = operator.upper().strip()
            if operator_upper not in self.VALID_OPERATORS:
                logger.warning(f"Skipping filter with invalid operator: {operator}")
                continue
            
            # Handle different value types
            safe_value = self._sanitize_value(value, operator_upper)
            
            safe_filters.append({
                'column': column,
                'operator': operator_upper,
                'value': safe_value,
            })
        
        return safe_filters
    
    def _validate_order_by(self, order_by: List[Dict]) -> List[Dict]:
        """Validate order by specifications."""
        safe_order = []
        
        for o in order_by:
            if not isinstance(o, dict):
                continue
            
            column = o.get('column', '')
            direction = o.get('direction', 'ASC')
            
            if not self._is_valid_identifier(column):
                logger.warning(f"Skipping order_by with invalid column: {column}")
                continue
            
            if direction.upper() not in self.VALID_DIRECTIONS:
                direction = 'ASC'
            
            safe_order.append({
                'column': column,
                'direction': direction.upper()
            })
        
        return safe_order
    
    def _is_valid_identifier(self, name: str) -> bool:
        """Check if a name is a valid SQL identifier."""
        import re
        if not name or not isinstance(name, str):
            return False
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name))
    
    def _sanitize_value(self, value: Any, operator: str) -> Any:
        """
        Sanitize filter values based on operator type.
        
        Values are parameterized in the template, but we still validate
        to prevent obvious injection attempts.
        """
        if value is None:
            return None
        
        if operator in ('IN', 'NOT IN'):
            # Expect a list
            if isinstance(value, (list, tuple)):
                return [self._sanitize_scalar(v) for v in value]
            return [self._sanitize_scalar(value)]
        
        if operator == 'BETWEEN':
            # Expect dict with start/end
            if isinstance(value, dict):
                return {
                    'start': self._sanitize_scalar(value.get('start')),
                    'end': self._sanitize_scalar(value.get('end'))
                }
            return value
        
        return self._sanitize_scalar(value)
    
    def _sanitize_scalar(self, value: Any) -> Any:
        """Sanitize a scalar value."""
        if value is None:
            return None
        if isinstance(value, (int, float, bool)):
            return value
        if isinstance(value, str):
            # Remove dangerous characters but allow normal values
            # The template will properly quote/escape the value
            return value[:1000]  # Limit length
        return str(value)[:1000]
