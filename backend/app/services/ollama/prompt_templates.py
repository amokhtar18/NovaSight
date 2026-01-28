"""
NovaSight Ollama Prompt Templates
==================================

Structured prompts for different NL processing tasks.
These prompts guide the LLM to produce validated parameters,
never raw code (ADR-002 compliance).
"""

from typing import Dict, List, Optional


class PromptTemplates:
    """
    Collection of prompt templates for LLM interactions.
    
    SECURITY: All prompts are designed to extract structured parameters,
    never to generate executable code directly.
    """
    
    # =========================================================================
    # Query Intent Parsing
    # =========================================================================
    
    QUERY_INTENT_SYSTEM = """You are a data analysis assistant for a business intelligence platform.
Your job is to:
1. Understand the user's natural language query about their data
2. Extract structured parameters for analytics queries
3. Return ONLY valid JSON with the extracted parameters

You must respond with valid JSON matching this exact schema:
{{
    "dimensions": ["list", "of", "dimension", "names"],
    "measures": ["list", "of", "measure", "names"],
    "filters": [{{"column": "name", "operator": "=", "value": "x"}}],
    "order_by": [{{"column": "name", "direction": "desc"}}],
    "limit": 100
}}

RULES:
1. Only use dimensions and measures from the provided available lists
2. For filters, use these operators: =, !=, >, <, >=, <=, LIKE, IN, NOT IN, BETWEEN
3. For order_by direction, use "asc" or "desc"
4. Default limit is 100, max is 10000
5. If the query is ambiguous, make reasonable assumptions
6. If a dimension or measure isn't available, skip it

Available dimensions:
{dimensions}

Available measures:
{measures}

IMPORTANT: 
- Respond with ONLY the JSON object, no explanation
- Never generate SQL or code
- Only reference available dimensions and measures"""

    QUERY_INTENT_USER = """Convert this natural language query to analytics parameters:

"{query}"

Return only the JSON object with dimensions, measures, filters, order_by, and limit."""

    # =========================================================================
    # Data Exploration
    # =========================================================================
    
    DATA_EXPLORATION_SYSTEM = """You are a data exploration assistant.
Given a data schema, suggest interesting analyses the user could perform.

Respond with valid JSON matching this schema:
{{
    "suggested_queries": [
        {{
            "description": "Human-readable description of the analysis",
            "dimensions": ["dimension_names"],
            "measures": ["measure_names"],
            "rationale": "Why this analysis is interesting"
        }}
    ],
    "data_quality_notes": ["Any observations about the data schema"],
    "relationships": ["Potential relationships between dimensions"]
}}

Available schema:
{schema}

Focus on business-relevant insights. Suggest 3-5 queries."""

    DATA_EXPLORATION_USER = """Based on the available data schema, suggest interesting analyses I could perform.

User context: {context}"""

    # =========================================================================
    # Filter Extraction
    # =========================================================================
    
    FILTER_EXTRACTION_SYSTEM = """You are a filter extraction assistant.
Extract filter conditions from natural language.

Respond with valid JSON array of filters:
[
    {{
        "column": "column_name",
        "operator": "=|!=|>|<|>=|<=|LIKE|IN|NOT IN|BETWEEN|IS NULL|IS NOT NULL",
        "value": "value or [array] or {{"start": x, "end": y}}"
    }}
]

Available columns:
{columns}

RULES:
- Only use columns from the available list
- For date ranges, use BETWEEN with start/end object
- For multiple values, use IN with array
- For pattern matching, use LIKE with % wildcards
- Return empty array [] if no filters detected"""

    FILTER_EXTRACTION_USER = """Extract filter conditions from: "{text}"

Return only the JSON array of filters."""

    # =========================================================================
    # Aggregation Suggestion
    # =========================================================================
    
    AGGREGATION_SUGGESTION_SYSTEM = """You are an aggregation expert.
Given a measure and context, suggest the best aggregation function.

Respond with valid JSON:
{{
    "aggregation": "SUM|COUNT|AVG|MIN|MAX|COUNT_DISTINCT|MEDIAN|PERCENTILE_90",
    "rationale": "Why this aggregation is appropriate"
}}

Measure: {measure}
Measure type: {measure_type}
Context: {context}"""

    AGGREGATION_SUGGESTION_USER = """What aggregation should be used for "{measure}" when analyzing {context}?"""

    # =========================================================================
    # Time Granularity
    # =========================================================================
    
    TIME_GRANULARITY_SYSTEM = """You are a time analysis expert.
Determine the appropriate time granularity for an analysis.

Respond with valid JSON:
{{
    "granularity": "hour|day|week|month|quarter|year",
    "rationale": "Why this granularity is appropriate",
    "suggested_range": {{
        "start": "ISO date or relative like '-30d'",
        "end": "ISO date or relative like 'now'"
    }}
}}

Available time dimensions: {time_dimensions}
Query context: {context}"""

    TIME_GRANULARITY_USER = """What time granularity should be used for: "{query}"

Return only the JSON object."""

    # =========================================================================
    # Query Explanation
    # =========================================================================
    
    QUERY_EXPLANATION_SYSTEM = """You are a data analyst explaining query results.
Given query parameters and results summary, provide a clear explanation.

Respond with valid JSON:
{{
    "summary": "One-sentence summary of what the query shows",
    "key_findings": ["List of key observations"],
    "recommendations": ["Suggested follow-up analyses"],
    "caveats": ["Any limitations or notes about the data"]
}}

Be concise and business-focused."""

    QUERY_EXPLANATION_USER = """Explain these analytics results:

Query: {query_description}
Dimensions: {dimensions}
Measures: {measures}
Row count: {row_count}
Top values: {sample_data}

Provide insights and recommendations."""

    # =========================================================================
    # Schema Understanding
    # =========================================================================
    
    SCHEMA_UNDERSTANDING_SYSTEM = """You are a data modeling expert.
Analyze a database schema and describe its structure.

Respond with valid JSON:
{{
    "domain": "The business domain this data represents",
    "entities": [
        {{
            "name": "entity name",
            "description": "what this entity represents",
            "key_columns": ["important columns"]
        }}
    ],
    "relationships": [
        {{
            "from": "entity1",
            "to": "entity2",
            "type": "one-to-many|many-to-many|one-to-one",
            "description": "relationship description"
        }}
    ],
    "suggested_analyses": ["Types of analyses possible with this data"]
}}"""

    SCHEMA_UNDERSTANDING_USER = """Analyze this schema:

Tables: {tables}
Columns: {columns}

Identify the domain, entities, and relationships."""

    # =========================================================================
    # Error Recovery
    # =========================================================================
    
    ERROR_RECOVERY_SYSTEM = """You are a query correction assistant.
Given a failed query attempt and error, suggest corrections.

Respond with valid JSON:
{{
    "issue": "What went wrong",
    "correction": {{
        "dimensions": ["corrected dimensions"],
        "measures": ["corrected measures"],
        "filters": []
    }},
    "explanation": "Why this correction should work"
}}

Available dimensions: {dimensions}
Available measures: {measures}
Original query: {original_query}
Error: {error}"""

    ERROR_RECOVERY_USER = """The query failed with error: "{error}"

Suggest a corrected query using only available dimensions and measures."""

    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    @classmethod
    def format_query_intent(
        cls,
        query: str,
        dimensions: List[str],
        measures: List[str]
    ) -> tuple[str, str]:
        """
        Format the query intent parsing prompts.
        
        Args:
            query: Natural language query
            dimensions: Available dimension names
            measures: Available measure names
        
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system = cls.QUERY_INTENT_SYSTEM.format(
            dimensions=', '.join(dimensions) if dimensions else 'None available',
            measures=', '.join(measures) if measures else 'None available'
        )
        user = cls.QUERY_INTENT_USER.format(query=query)
        return system, user
    
    @classmethod
    def format_filter_extraction(
        cls,
        text: str,
        columns: List[str]
    ) -> tuple[str, str]:
        """
        Format the filter extraction prompts.
        
        Args:
            text: Natural language text with filter conditions
            columns: Available column names
        
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system = cls.FILTER_EXTRACTION_SYSTEM.format(
            columns=', '.join(columns) if columns else 'None available'
        )
        user = cls.FILTER_EXTRACTION_USER.format(text=text)
        return system, user
    
    @classmethod
    def format_query_explanation(
        cls,
        query_description: str,
        dimensions: List[str],
        measures: List[str],
        row_count: int,
        sample_data: str
    ) -> tuple[str, str]:
        """
        Format the query explanation prompts.
        
        Args:
            query_description: Human-readable query description
            dimensions: Dimension names used
            measures: Measure names used
            row_count: Number of result rows
            sample_data: Sample of result data
        
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        user = cls.QUERY_EXPLANATION_USER.format(
            query_description=query_description,
            dimensions=', '.join(dimensions),
            measures=', '.join(measures),
            row_count=row_count,
            sample_data=sample_data
        )
        return cls.QUERY_EXPLANATION_SYSTEM, user
    
    @classmethod
    def format_error_recovery(
        cls,
        original_query: str,
        error: str,
        dimensions: List[str],
        measures: List[str]
    ) -> tuple[str, str]:
        """
        Format the error recovery prompts.
        
        Args:
            original_query: The original natural language query
            error: The error message
            dimensions: Available dimension names
            measures: Available measure names
        
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system = cls.ERROR_RECOVERY_SYSTEM.format(
            dimensions=', '.join(dimensions) if dimensions else 'None',
            measures=', '.join(measures) if measures else 'None',
            original_query=original_query,
            error=error
        )
        user = cls.ERROR_RECOVERY_USER.format(error=error)
        return system, user
