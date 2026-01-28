"""
NovaSight Query Classifier
===========================

Classifies natural language queries into query types and extracts entities.
Implements ADR-002: LLM generates intent and parameters only.
"""

import json
import logging
import re
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.services.ollama.client import OllamaClient, OllamaError

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Types of analytics queries."""
    AGGREGATION = "aggregation"       # "total sales by region"
    COMPARISON = "comparison"         # "compare Q1 vs Q2"
    TREND = "trend"                   # "sales trend over time"
    TOP_N = "top_n"                   # "top 10 products"
    FILTER = "filter"                 # "orders from California"
    DRILL_DOWN = "drill_down"         # "break down by category"
    DISTRIBUTION = "distribution"     # "distribution of order values"
    CORRELATION = "correlation"       # "relationship between X and Y"


class TimeRange(BaseModel):
    """Validated time range for queries."""
    
    start: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    end: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
    granularity: Optional[str] = Field(
        default=None, 
        description="Time granularity: day, week, month, quarter, year"
    )
    
    @field_validator('start', 'end')
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate date format if provided."""
        if v is None:
            return v
        # Accept various date formats
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            # Try to parse relative dates
            if v.lower() in ('today', 'yesterday', 'last_week', 'last_month', 'last_year'):
                return v
            raise ValueError(f"Invalid date format: {v}. Use YYYY-MM-DD or relative dates.")
        return v
    
    @field_validator('granularity')
    @classmethod
    def validate_granularity(cls, v: Optional[str]) -> Optional[str]:
        """Validate time granularity."""
        if v is None:
            return v
        valid = ('day', 'week', 'month', 'quarter', 'year', 'hour')
        if v.lower() not in valid:
            raise ValueError(f"Invalid granularity: {v}. Use: {valid}")
        return v.lower()


class QueryEntities(BaseModel):
    """Extracted entities from the query."""
    
    dimensions: List[str] = Field(default_factory=list)
    measures: List[str] = Field(default_factory=list)
    values: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dimension filter values extracted from query"
    )
    compare_dimension: Optional[str] = Field(
        default=None,
        description="Dimension to compare (for comparison queries)"
    )
    compare_values: List[str] = Field(
        default_factory=list,
        description="Values to compare (e.g., ['Q1', 'Q2'])"
    )
    top_n: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Number of top results (for top_n queries)"
    )
    
    @field_validator('dimensions', 'measures')
    @classmethod
    def validate_identifiers(cls, v: List[str]) -> List[str]:
        """Validate identifier format to prevent injection."""
        validated = []
        for item in v:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', item):
                logger.warning(f"Skipping invalid identifier: {item}")
                continue
            validated.append(item)
        return validated


class ClassifiedIntent(BaseModel):
    """
    Classified query intent with extracted entities.
    
    This model represents the structured output of query classification.
    """
    
    query_type: QueryType
    confidence: float = Field(ge=0.0, le=1.0)
    entities: QueryEntities
    time_range: Optional[TimeRange] = None
    original_query: str = ""
    explanation: str = ""
    
    @field_validator('confidence')
    @classmethod
    def round_confidence(cls, v: float) -> float:
        """Round confidence to 3 decimal places."""
        return round(v, 3)


class QueryClassifier:
    """
    Classifies natural language queries into structured intents.
    
    SECURITY: This classifier only extracts INTENT and ENTITIES.
    No executable code is generated. All output is validated.
    """
    
    CLASSIFICATION_PROMPT_SYSTEM = """You are a query classifier for a business intelligence platform.
Your job is to:
1. Determine the type of analytics query the user is asking
2. Extract relevant entities (dimensions, measures, values)
3. Identify time ranges if mentioned
4. Return structured JSON

Query Types:
- aggregation: Summarizing data with grouping (e.g., "total sales by region")
- comparison: Comparing values between groups (e.g., "compare Q1 vs Q2")
- trend: Analyzing changes over time (e.g., "sales trend over 12 months")
- top_n: Finding highest/lowest values (e.g., "top 10 products")
- filter: Simple filtered query (e.g., "orders from California")
- drill_down: Breaking down into detail (e.g., "break down revenue by category")
- distribution: Analyzing value distributions (e.g., "order value distribution")
- correlation: Finding relationships (e.g., "correlation between price and quantity")

Available dimensions: {dimensions}
Available measures: {measures}

RESPOND ONLY with valid JSON matching this schema:
{{
    "query_type": "aggregation|comparison|trend|top_n|filter|drill_down|distribution|correlation",
    "confidence": 0.0 to 1.0,
    "entities": {{
        "dimensions": ["matched dimension names"],
        "measures": ["matched measure names"],
        "values": {{"dimension": "filter_value"}},
        "compare_dimension": "dimension for comparison" or null,
        "compare_values": ["value1", "value2"] or [],
        "top_n": integer or null
    }},
    "time_range": {{
        "start": "YYYY-MM-DD or relative",
        "end": "YYYY-MM-DD or relative",
        "granularity": "day|week|month|quarter|year"
    }} or null,
    "explanation": "Brief explanation of the classification"
}}

IMPORTANT:
- Only reference dimensions and measures from the available lists
- If uncertain, choose the most likely query type and lower confidence
- Never generate SQL or code"""

    CLASSIFICATION_PROMPT_USER = """Classify this analytics query:

"{query}"

Return only the JSON classification."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        max_retries: int = 2
    ):
        """
        Initialize query classifier.
        
        Args:
            ollama_client: Configured Ollama client
            max_retries: Maximum retry attempts for classification
        """
        self.ollama = ollama_client
        self.max_retries = max_retries
    
    async def classify(
        self,
        query: str,
        dimensions: List[str],
        measures: List[str]
    ) -> ClassifiedIntent:
        """
        Classify a natural language query.
        
        Args:
            query: Natural language analytics query
            dimensions: Available dimension names
            measures: Available measure names
        
        Returns:
            ClassifiedIntent with query type and extracted entities
        
        Raises:
            ValueError: If classification fails after retries
            OllamaError: If LLM communication fails
        """
        logger.info(f"Classifying query: {query[:100]}...")
        
        system = self.CLASSIFICATION_PROMPT_SYSTEM.format(
            dimensions=', '.join(dimensions),
            measures=', '.join(measures)
        )
        user = self.CLASSIFICATION_PROMPT_USER.format(query=query)
        
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.ollama.generate(
                    prompt=user,
                    system=system,
                    temperature=0.1,  # Low temperature for consistency
                    format='json'
                )
                
                # Parse and validate response
                data = self._extract_json(response)
                
                # Build validated entities
                entities_data = data.get('entities', {})
                entities = QueryEntities(
                    dimensions=entities_data.get('dimensions', []),
                    measures=entities_data.get('measures', []),
                    values=entities_data.get('values', {}),
                    compare_dimension=entities_data.get('compare_dimension'),
                    compare_values=entities_data.get('compare_values', []),
                    top_n=entities_data.get('top_n'),
                )
                
                # Filter entities to only available ones
                entities = self._filter_to_available(
                    entities, dimensions, measures
                )
                
                # Build time range if present
                time_range = None
                if data.get('time_range'):
                    try:
                        time_range = TimeRange(**data['time_range'])
                    except Exception as e:
                        logger.warning(f"Invalid time range, skipping: {e}")
                
                intent = ClassifiedIntent(
                    query_type=QueryType(data['query_type']),
                    confidence=data.get('confidence', 0.8),
                    entities=entities,
                    time_range=time_range,
                    original_query=query,
                    explanation=data.get('explanation', '')
                )
                
                logger.info(
                    f"Query classified as {intent.query_type.value} "
                    f"with confidence {intent.confidence}"
                )
                return intent
                
            except json.JSONDecodeError as e:
                last_error = f"Invalid JSON response: {e}"
                logger.warning(f"Attempt {attempt + 1}: {last_error}")
            except (ValueError, KeyError) as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}: Validation error: {e}")
        
        raise ValueError(
            f"Failed to classify query after {self.max_retries + 1} attempts: {last_error}"
        )
    
    def _extract_json(self, response: str) -> Dict[str, Any]:
        """Extract JSON from LLM response."""
        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        raise json.JSONDecodeError("No valid JSON found in response", response, 0)
    
    def _filter_to_available(
        self,
        entities: QueryEntities,
        dimensions: List[str],
        measures: List[str]
    ) -> QueryEntities:
        """Filter entities to only include available schema elements."""
        dim_set = set(d.lower() for d in dimensions)
        measure_set = set(m.lower() for m in measures)
        
        # Map back to original case
        dim_map = {d.lower(): d for d in dimensions}
        measure_map = {m.lower(): m for m in measures}
        
        # Filter dimensions
        filtered_dims = [
            dim_map[d.lower()]
            for d in entities.dimensions
            if d.lower() in dim_set
        ]
        
        # Filter measures
        filtered_measures = [
            measure_map[m.lower()]
            for m in entities.measures
            if m.lower() in measure_set
        ]
        
        # Filter compare_dimension
        compare_dim = None
        if entities.compare_dimension and entities.compare_dimension.lower() in dim_set:
            compare_dim = dim_map[entities.compare_dimension.lower()]
        
        return QueryEntities(
            dimensions=filtered_dims,
            measures=filtered_measures,
            values=entities.values,
            compare_dimension=compare_dim,
            compare_values=entities.compare_values,
            top_n=entities.top_n,
        )
    
    async def suggest_query_type(
        self,
        query: str,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest possible query types for an incomplete query.
        
        Args:
            query: Partial or incomplete query
            context: Additional context about the data
        
        Returns:
            List of suggested query types with examples
        """
        suggestions = []
        
        # Simple heuristic-based suggestions
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['total', 'sum', 'count', 'average', 'by']):
            suggestions.append({
                'type': QueryType.AGGREGATION,
                'description': 'Aggregate data with grouping',
                'example': 'Show total revenue by region'
            })
        
        if any(word in query_lower for word in ['compare', 'vs', 'versus', 'difference']):
            suggestions.append({
                'type': QueryType.COMPARISON,
                'description': 'Compare values between groups',
                'example': 'Compare Q1 vs Q2 sales'
            })
        
        if any(word in query_lower for word in ['trend', 'over time', 'monthly', 'weekly', 'growth']):
            suggestions.append({
                'type': QueryType.TREND,
                'description': 'Analyze trends over time',
                'example': 'Show sales trend over the last 12 months'
            })
        
        if any(word in query_lower for word in ['top', 'best', 'highest', 'lowest', 'worst']):
            suggestions.append({
                'type': QueryType.TOP_N,
                'description': 'Find top or bottom values',
                'example': 'Show top 10 products by revenue'
            })
        
        if any(word in query_lower for word in ['breakdown', 'break down', 'detail', 'drill']):
            suggestions.append({
                'type': QueryType.DRILL_DOWN,
                'description': 'Break down into detailed categories',
                'example': 'Break down revenue by product category'
            })
        
        # Default suggestion if none matched
        if not suggestions:
            suggestions.append({
                'type': QueryType.AGGREGATION,
                'description': 'General data aggregation',
                'example': 'Show metrics grouped by dimensions'
            })
        
        return suggestions
