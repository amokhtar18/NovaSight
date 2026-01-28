"""
NovaSight NL-to-Parameters Service
===================================

Converts natural language queries to validated template parameters.
Implements ADR-002: LLM generates parameters only, never executable code.
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.ollama.client import OllamaClient, OllamaError
from app.services.ollama.prompt_templates import PromptTemplates

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models for Validated Parameters
# =============================================================================

class FilterCondition(BaseModel):
    """Validated filter condition extracted from NL."""
    
    column: str = Field(..., min_length=1, max_length=128)
    operator: str = Field(...)
    value: Any = Field(...)
    
    VALID_OPERATORS = {
        '=', '!=', '>', '<', '>=', '<=',
        'LIKE', 'NOT LIKE', 'IN', 'NOT IN',
        'BETWEEN', 'IS NULL', 'IS NOT NULL'
    }
    
    @field_validator('operator')
    @classmethod
    def validate_operator(cls, v: str) -> str:
        """Validate operator is in allowed set."""
        normalized = v.upper().strip()
        if normalized not in cls.VALID_OPERATORS:
            raise ValueError(
                f"Invalid operator '{v}'. Allowed: {cls.VALID_OPERATORS}"
            )
        return normalized
    
    @field_validator('column')
    @classmethod
    def validate_column_name(cls, v: str) -> str:
        """Validate column name format (prevent injection)."""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError(
                f"Invalid column name '{v}'. Must be alphanumeric with underscores."
            )
        return v


class OrderBySpec(BaseModel):
    """Validated order by specification."""
    
    column: str = Field(..., min_length=1, max_length=128)
    direction: str = Field(default='asc')
    
    @field_validator('column')
    @classmethod
    def validate_column_name(cls, v: str) -> str:
        """Validate column name format."""
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', v):
            raise ValueError(f"Invalid column name '{v}'")
        return v
    
    @field_validator('direction')
    @classmethod
    def validate_direction(cls, v: str) -> str:
        """Validate sort direction."""
        normalized = v.lower().strip()
        if normalized not in ('asc', 'desc'):
            raise ValueError(f"Invalid direction '{v}'. Use 'asc' or 'desc'.")
        return normalized


class QueryIntent(BaseModel):
    """
    Parsed and validated query intent from natural language.
    
    This model represents the structured output of NL parsing.
    All fields are validated to prevent injection attacks.
    """
    
    dimensions: List[str] = Field(default_factory=list)
    measures: List[str] = Field(default_factory=list)
    filters: List[FilterCondition] = Field(default_factory=list)
    order_by: List[OrderBySpec] = Field(default_factory=list)
    limit: int = Field(default=100, ge=1, le=10000)
    
    # Optional metadata
    time_dimension: Optional[str] = Field(default=None)
    date_from: Optional[str] = Field(default=None)
    date_to: Optional[str] = Field(default=None)
    
    @field_validator('dimensions', 'measures')
    @classmethod
    def validate_identifiers(cls, v: List[str]) -> List[str]:
        """Validate all identifiers in list."""
        validated = []
        for item in v:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', item):
                raise ValueError(f"Invalid identifier '{item}'")
            validated.append(item)
        return validated
    
    @model_validator(mode='after')
    def validate_has_content(self):
        """Ensure query has at least dimensions or measures."""
        if not self.dimensions and not self.measures:
            raise ValueError("Query must have at least one dimension or measure")
        return self


class DataExplorationSuggestion(BaseModel):
    """Suggested analysis from data exploration."""
    
    description: str
    dimensions: List[str] = Field(default_factory=list)
    measures: List[str] = Field(default_factory=list)
    rationale: str = ""


class QueryExplanation(BaseModel):
    """Explanation of query results."""
    
    summary: str
    key_findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)


# =============================================================================
# NL to Parameters Service
# =============================================================================

class NLToParametersService:
    """
    Converts natural language to validated template parameters.
    
    SECURITY: This service NEVER generates code. It only generates
    parameters that are validated before being passed to templates.
    All executable artifacts MUST come from the template engine.
    
    ADR-002 Compliance:
    - LLM output is always parsed as JSON
    - All values are validated with Pydantic models
    - Invalid references are rejected before use
    - No raw SQL or code is ever returned
    """
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        default_limit: int = 100,
        max_retries: int = 2
    ):
        """
        Initialize NL-to-Parameters service.
        
        Args:
            ollama_client: Configured Ollama client
            default_limit: Default query result limit
            max_retries: Maximum retry attempts for parsing
        """
        self.ollama = ollama_client
        self.default_limit = default_limit
        self.max_retries = max_retries
    
    async def parse_query(
        self,
        natural_language: str,
        available_dimensions: List[str],
        available_measures: List[str],
        strict: bool = True
    ) -> QueryIntent:
        """
        Parse natural language into validated query parameters.
        
        Args:
            natural_language: User's natural language query
            available_dimensions: List of valid dimension names
            available_measures: List of valid measure names
            strict: If True, reject unknown references. If False, filter them out.
        
        Returns:
            Validated QueryIntent with structured parameters
        
        Raises:
            ValueError: If parsing fails or validation fails
            OllamaError: If LLM communication fails
        """
        logger.info(f"Parsing NL query: {natural_language[:100]}...")
        
        # Build context-aware prompt
        system, user = PromptTemplates.format_query_intent(
            query=natural_language,
            dimensions=available_dimensions,
            measures=available_measures
        )
        
        # Get LLM response with retries
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.ollama.generate(
                    prompt=user,
                    system=system,
                    temperature=0.1,  # Low temperature for consistency
                    format='json'  # Request JSON format
                )
                
                # Parse and validate response
                params = self._extract_json(response)
                
                # Convert filters and order_by to proper format
                filters = [
                    FilterCondition(**f) if isinstance(f, dict) else f
                    for f in params.get('filters', [])
                ]
                order_by = [
                    OrderBySpec(**o) if isinstance(o, dict) else o
                    for o in params.get('order_by', [])
                ]
                
                intent = QueryIntent(
                    dimensions=params.get('dimensions', []),
                    measures=params.get('measures', []),
                    filters=filters,
                    order_by=order_by,
                    limit=params.get('limit', self.default_limit),
                    time_dimension=params.get('time_dimension'),
                    date_from=params.get('date_from'),
                    date_to=params.get('date_to'),
                )
                
                # Validate references against available schema
                intent = self._validate_references(
                    intent,
                    available_dimensions,
                    available_measures,
                    strict=strict
                )
                
                logger.info(
                    f"Successfully parsed query: "
                    f"{len(intent.dimensions)} dims, {len(intent.measures)} measures"
                )
                return intent
                
            except json.JSONDecodeError as e:
                last_error = f"Invalid JSON response: {e}"
                logger.warning(f"Attempt {attempt + 1}: {last_error}")
            except ValueError as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}: Validation error: {e}")
        
        raise ValueError(f"Failed to parse query after {self.max_retries + 1} attempts: {last_error}")
    
    async def extract_filters(
        self,
        text: str,
        available_columns: List[str]
    ) -> List[FilterCondition]:
        """
        Extract filter conditions from natural language text.
        
        Args:
            text: Natural language text containing filter conditions
            available_columns: List of valid column names
        
        Returns:
            List of validated FilterCondition objects
        """
        system, user = PromptTemplates.format_filter_extraction(
            text=text,
            columns=available_columns
        )
        
        response = await self.ollama.generate(
            prompt=user,
            system=system,
            temperature=0.1,
            format='json'
        )
        
        filters_data = self._extract_json(response)
        
        # Handle both array and object with filters key
        if isinstance(filters_data, dict):
            filters_data = filters_data.get('filters', [])
        
        validated_filters = []
        for f in filters_data:
            try:
                condition = FilterCondition(**f)
                if condition.column in available_columns:
                    validated_filters.append(condition)
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid filter: {f}, error: {e}")
        
        return validated_filters
    
    async def suggest_analyses(
        self,
        schema_description: str,
        user_context: str = ""
    ) -> List[DataExplorationSuggestion]:
        """
        Suggest interesting analyses based on available data.
        
        Args:
            schema_description: Description of available schema
            user_context: Optional user-provided context
        
        Returns:
            List of suggested analyses
        """
        system = PromptTemplates.DATA_EXPLORATION_SYSTEM.format(
            schema=schema_description
        )
        user = PromptTemplates.DATA_EXPLORATION_USER.format(
            context=user_context or "General exploration"
        )
        
        response = await self.ollama.generate(
            prompt=user,
            system=system,
            temperature=0.3,  # Slightly higher for creativity
            format='json'
        )
        
        data = self._extract_json(response)
        suggestions = []
        
        for item in data.get('suggested_queries', []):
            try:
                suggestions.append(DataExplorationSuggestion(**item))
            except (ValueError, TypeError) as e:
                logger.warning(f"Skipping invalid suggestion: {e}")
        
        return suggestions
    
    async def explain_results(
        self,
        query_description: str,
        dimensions: List[str],
        measures: List[str],
        row_count: int,
        sample_data: List[Dict]
    ) -> QueryExplanation:
        """
        Generate natural language explanation of query results.
        
        Args:
            query_description: Human-readable query description
            dimensions: Dimension names used
            measures: Measure names used
            row_count: Number of result rows
            sample_data: Sample of result data (first few rows)
        
        Returns:
            QueryExplanation with insights
        """
        sample_str = json.dumps(sample_data[:5], indent=2, default=str)
        
        system, user = PromptTemplates.format_query_explanation(
            query_description=query_description,
            dimensions=dimensions,
            measures=measures,
            row_count=row_count,
            sample_data=sample_str
        )
        
        response = await self.ollama.generate(
            prompt=user,
            system=system,
            temperature=0.2,
            format='json'
        )
        
        data = self._extract_json(response)
        return QueryExplanation(**data)
    
    async def recover_from_error(
        self,
        original_query: str,
        error: str,
        available_dimensions: List[str],
        available_measures: List[str]
    ) -> QueryIntent:
        """
        Attempt to recover from a query error with corrections.
        
        Args:
            original_query: The original natural language query
            error: The error message
            available_dimensions: Valid dimension names
            available_measures: Valid measure names
        
        Returns:
            Corrected QueryIntent
        """
        system, user = PromptTemplates.format_error_recovery(
            original_query=original_query,
            error=error,
            dimensions=available_dimensions,
            measures=available_measures
        )
        
        response = await self.ollama.generate(
            prompt=user,
            system=system,
            temperature=0.1,
            format='json'
        )
        
        data = self._extract_json(response)
        correction = data.get('correction', {})
        
        # Parse corrected query intent
        intent = QueryIntent(
            dimensions=correction.get('dimensions', []),
            measures=correction.get('measures', []),
            filters=[FilterCondition(**f) for f in correction.get('filters', [])],
            order_by=[OrderBySpec(**o) for o in correction.get('order_by', [])],
            limit=correction.get('limit', self.default_limit)
        )
        
        # Validate the correction
        return self._validate_references(
            intent,
            available_dimensions,
            available_measures,
            strict=False
        )
    
    def _extract_json(self, response: str) -> Dict:
        """
        Extract JSON from LLM response.
        
        Handles responses that may include markdown code blocks
        or extra text around the JSON.
        """
        # Try to parse as-is first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to extract from markdown code block
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in response
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON array
        start = response.find('[')
        end = response.rfind(']') + 1
        if start >= 0 and end > start:
            try:
                return json.loads(response[start:end])
            except json.JSONDecodeError:
                pass
        
        raise json.JSONDecodeError("No valid JSON found in response", response, 0)
    
    def _validate_references(
        self,
        intent: QueryIntent,
        valid_dimensions: List[str],
        valid_measures: List[str],
        strict: bool = True
    ) -> QueryIntent:
        """
        Validate that all references are to known entities.
        
        Args:
            intent: Parsed query intent
            valid_dimensions: List of valid dimension names
            valid_measures: List of valid measure names
            strict: If True, raise error on invalid reference.
                   If False, filter out invalid references.
        
        Returns:
            Validated QueryIntent (possibly filtered)
        
        Raises:
            ValueError: If strict=True and invalid reference found
        """
        # Normalize to lowercase for comparison
        valid_dims_lower = {d.lower() for d in valid_dimensions}
        valid_measures_lower = {m.lower() for m in valid_measures}
        
        # Create mappings for case restoration
        dim_mapping = {d.lower(): d for d in valid_dimensions}
        measure_mapping = {m.lower(): m for m in valid_measures}
        
        validated_dimensions = []
        for dim in intent.dimensions:
            dim_lower = dim.lower()
            if dim_lower in valid_dims_lower:
                validated_dimensions.append(dim_mapping[dim_lower])
            elif strict:
                raise ValueError(
                    f"Unknown dimension: '{dim}'. "
                    f"Available: {', '.join(valid_dimensions[:10])}..."
                )
            else:
                logger.warning(f"Filtering out unknown dimension: {dim}")
        
        validated_measures = []
        for measure in intent.measures:
            measure_lower = measure.lower()
            if measure_lower in valid_measures_lower:
                validated_measures.append(measure_mapping[measure_lower])
            elif strict:
                raise ValueError(
                    f"Unknown measure: '{measure}'. "
                    f"Available: {', '.join(valid_measures[:10])}..."
                )
            else:
                logger.warning(f"Filtering out unknown measure: {measure}")
        
        # Validate filter columns
        all_valid = valid_dims_lower | valid_measures_lower
        validated_filters = []
        for f in intent.filters:
            if f.column.lower() in all_valid:
                validated_filters.append(f)
            elif strict:
                raise ValueError(f"Unknown filter column: '{f.column}'")
            else:
                logger.warning(f"Filtering out filter on unknown column: {f.column}")
        
        # Validate order_by columns
        validated_order_by = []
        for o in intent.order_by:
            if o.column.lower() in all_valid:
                validated_order_by.append(o)
            elif strict:
                raise ValueError(f"Unknown order_by column: '{o.column}'")
            else:
                logger.warning(f"Filtering out order_by on unknown column: {o.column}")
        
        return QueryIntent(
            dimensions=validated_dimensions,
            measures=validated_measures,
            filters=validated_filters,
            order_by=validated_order_by,
            limit=intent.limit,
            time_dimension=intent.time_dimension,
            date_from=intent.date_from,
            date_to=intent.date_to
        )
