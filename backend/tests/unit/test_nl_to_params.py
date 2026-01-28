"""
Tests for NL-to-Parameters Service
===================================

Unit tests for the natural language to parameters conversion service.
Tests ADR-002 compliance: LLM only generates parameters, never code.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ollama.nl_to_params import (
    NLToParametersService,
    QueryIntent,
    FilterCondition,
    OrderBySpec,
    DataExplorationSuggestion,
    QueryExplanation,
)
from app.services.ollama.client import OllamaClient


class TestQueryIntent:
    """Tests for QueryIntent model validation."""
    
    def test_valid_query_intent(self):
        """Test valid query intent creation."""
        intent = QueryIntent(
            dimensions=['product_category', 'region'],
            measures=['total_sales', 'order_count'],
            filters=[],
            order_by=[],
            limit=100
        )
        
        assert intent.dimensions == ['product_category', 'region']
        assert intent.measures == ['total_sales', 'order_count']
        assert intent.limit == 100
    
    def test_query_intent_requires_content(self):
        """Test that query intent requires at least one dimension or measure."""
        with pytest.raises(ValueError) as exc_info:
            QueryIntent(
                dimensions=[],
                measures=[],
            )
        
        assert 'at least one dimension or measure' in str(exc_info.value).lower()
    
    def test_query_intent_validates_identifiers(self):
        """Test that identifiers are validated."""
        with pytest.raises(ValueError):
            QueryIntent(
                dimensions=['valid_dim', 'invalid-dim'],  # hyphen not allowed
                measures=['total_sales'],
            )
    
    def test_query_intent_limit_bounds(self):
        """Test limit value bounds validation."""
        # Valid limit
        intent = QueryIntent(dimensions=['dim1'], limit=5000)
        assert intent.limit == 5000
        
        # Too high
        with pytest.raises(ValueError):
            QueryIntent(dimensions=['dim1'], limit=20000)
        
        # Too low
        with pytest.raises(ValueError):
            QueryIntent(dimensions=['dim1'], limit=0)


class TestFilterCondition:
    """Tests for FilterCondition model validation."""
    
    def test_valid_filter(self):
        """Test valid filter creation."""
        filter_cond = FilterCondition(
            column='product_id',
            operator='=',
            value='SKU123'
        )
        
        assert filter_cond.column == 'product_id'
        assert filter_cond.operator == '='
        assert filter_cond.value == 'SKU123'
    
    def test_filter_operator_normalization(self):
        """Test that operators are normalized to uppercase."""
        filter_cond = FilterCondition(
            column='status',
            operator='like',
            value='%active%'
        )
        
        assert filter_cond.operator == 'LIKE'
    
    def test_invalid_operator_rejected(self):
        """Test that invalid operators are rejected."""
        with pytest.raises(ValueError) as exc_info:
            FilterCondition(
                column='status',
                operator='INVALID_OP',
                value='test'
            )
        
        assert 'Invalid operator' in str(exc_info.value)
    
    def test_column_name_validation(self):
        """Test column name validation prevents injection."""
        # Valid column names
        FilterCondition(column='product_id', operator='=', value='1')
        FilterCondition(column='_private_col', operator='=', value='1')
        FilterCondition(column='Col123', operator='=', value='1')
        
        # Invalid column names (would allow SQL injection)
        with pytest.raises(ValueError):
            FilterCondition(column='id; DROP TABLE', operator='=', value='1')
        
        with pytest.raises(ValueError):
            FilterCondition(column='col-name', operator='=', value='1')


class TestOrderBySpec:
    """Tests for OrderBySpec model validation."""
    
    def test_valid_order_by(self):
        """Test valid order by creation."""
        order = OrderBySpec(column='total_sales', direction='desc')
        
        assert order.column == 'total_sales'
        assert order.direction == 'desc'
    
    def test_direction_normalization(self):
        """Test direction is normalized to lowercase."""
        order = OrderBySpec(column='amount', direction='DESC')
        assert order.direction == 'desc'
    
    def test_invalid_direction_rejected(self):
        """Test invalid direction is rejected."""
        with pytest.raises(ValueError):
            OrderBySpec(column='amount', direction='ascending')


class TestNLToParametersService:
    """Tests for NLToParametersService class."""
    
    @pytest.fixture
    def mock_ollama_client(self):
        """Create mock Ollama client."""
        client = AsyncMock(spec=OllamaClient)
        return client
    
    @pytest.fixture
    def service(self, mock_ollama_client):
        """Create service with mock client."""
        return NLToParametersService(
            ollama_client=mock_ollama_client,
            default_limit=100,
            max_retries=1
        )
    
    @pytest.mark.asyncio
    async def test_parse_query_success(self, service, mock_ollama_client):
        """Test successful query parsing."""
        mock_ollama_client.generate.return_value = json.dumps({
            'dimensions': ['product_category', 'region'],
            'measures': ['total_sales'],
            'filters': [{'column': 'region', 'operator': '=', 'value': 'North'}],
            'order_by': [{'column': 'total_sales', 'direction': 'desc'}],
            'limit': 50
        })
        
        intent = await service.parse_query(
            natural_language="Show me total sales by product category and region in the North",
            available_dimensions=['product_category', 'region', 'date'],
            available_measures=['total_sales', 'order_count', 'avg_order_value']
        )
        
        assert 'product_category' in intent.dimensions
        assert 'region' in intent.dimensions
        assert 'total_sales' in intent.measures
        assert intent.limit == 50
        assert len(intent.filters) == 1
        assert len(intent.order_by) == 1
    
    @pytest.mark.asyncio
    async def test_parse_query_validates_references(self, service, mock_ollama_client):
        """Test that unknown references are rejected in strict mode."""
        mock_ollama_client.generate.return_value = json.dumps({
            'dimensions': ['unknown_dimension'],
            'measures': ['total_sales'],
            'filters': [],
            'order_by': [],
            'limit': 100
        })
        
        with pytest.raises(ValueError) as exc_info:
            await service.parse_query(
                natural_language="Show me data by unknown dimension",
                available_dimensions=['product_category', 'region'],
                available_measures=['total_sales'],
                strict=True
            )
        
        assert 'Unknown dimension' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_parse_query_filters_unknown_non_strict(self, service, mock_ollama_client):
        """Test that unknown references are filtered in non-strict mode."""
        mock_ollama_client.generate.return_value = json.dumps({
            'dimensions': ['product_category', 'unknown_dim'],
            'measures': ['total_sales', 'unknown_measure'],
            'filters': [],
            'order_by': [],
            'limit': 100
        })
        
        intent = await service.parse_query(
            natural_language="Show me data",
            available_dimensions=['product_category', 'region'],
            available_measures=['total_sales'],
            strict=False
        )
        
        assert intent.dimensions == ['product_category']
        assert intent.measures == ['total_sales']
    
    @pytest.mark.asyncio
    async def test_parse_query_handles_markdown_json(self, service, mock_ollama_client):
        """Test that JSON in markdown code blocks is extracted."""
        mock_ollama_client.generate.return_value = """
Here's the structured query:

```json
{
    "dimensions": ["product_category"],
    "measures": ["total_sales"],
    "filters": [],
    "order_by": [],
    "limit": 100
}
```
"""
        
        intent = await service.parse_query(
            natural_language="Show me sales by category",
            available_dimensions=['product_category'],
            available_measures=['total_sales']
        )
        
        assert intent.dimensions == ['product_category']
        assert intent.measures == ['total_sales']
    
    @pytest.mark.asyncio
    async def test_parse_query_case_insensitive_matching(self, service, mock_ollama_client):
        """Test that dimension/measure matching is case-insensitive."""
        mock_ollama_client.generate.return_value = json.dumps({
            'dimensions': ['PRODUCT_CATEGORY'],  # Uppercase
            'measures': ['Total_Sales'],  # Mixed case
            'filters': [],
            'order_by': [],
            'limit': 100
        })
        
        intent = await service.parse_query(
            natural_language="Show me sales by category",
            available_dimensions=['product_category'],  # Lowercase
            available_measures=['total_sales']
        )
        
        # Should match and return the canonical case
        assert intent.dimensions == ['product_category']
        assert intent.measures == ['total_sales']
    
    @pytest.mark.asyncio
    async def test_extract_filters(self, service, mock_ollama_client):
        """Test filter extraction from natural language."""
        mock_ollama_client.generate.return_value = json.dumps([
            {'column': 'status', 'operator': '=', 'value': 'active'},
            {'column': 'amount', 'operator': '>', 'value': 1000}
        ])
        
        filters = await service.extract_filters(
            text="Show active items with amount greater than 1000",
            available_columns=['status', 'amount', 'date']
        )
        
        assert len(filters) == 2
        assert filters[0].column == 'status'
        assert filters[1].operator == '>'
    
    @pytest.mark.asyncio
    async def test_explain_results(self, service, mock_ollama_client):
        """Test query result explanation."""
        mock_ollama_client.generate.return_value = json.dumps({
            'summary': 'Sales are highest in the electronics category.',
            'key_findings': [
                'Electronics leads with 40% of total sales',
                'Clothing shows 20% growth'
            ],
            'recommendations': [
                'Focus marketing on electronics',
                'Investigate clothing growth drivers'
            ],
            'caveats': ['Data limited to last 30 days']
        })
        
        explanation = await service.explain_results(
            query_description="Sales by product category",
            dimensions=['product_category'],
            measures=['total_sales'],
            row_count=5,
            sample_data=[
                {'product_category': 'Electronics', 'total_sales': 50000},
                {'product_category': 'Clothing', 'total_sales': 30000}
            ]
        )
        
        assert 'electronics' in explanation.summary.lower()
        assert len(explanation.key_findings) == 2
        assert len(explanation.recommendations) == 2
    
    @pytest.mark.asyncio
    async def test_suggest_analyses(self, service, mock_ollama_client):
        """Test analysis suggestion generation."""
        mock_ollama_client.generate.return_value = json.dumps({
            'suggested_queries': [
                {
                    'description': 'Sales trend over time',
                    'dimensions': ['date'],
                    'measures': ['total_sales'],
                    'rationale': 'Identify seasonal patterns'
                },
                {
                    'description': 'Top performing products',
                    'dimensions': ['product_name'],
                    'measures': ['total_sales', 'order_count'],
                    'rationale': 'Find bestsellers'
                }
            ],
            'data_quality_notes': [],
            'relationships': []
        })
        
        suggestions = await service.suggest_analyses(
            schema_description="Sales data with date, product, and revenue",
            user_context="Looking for growth opportunities"
        )
        
        assert len(suggestions) == 2
        assert 'trend' in suggestions[0].description.lower()
    
    @pytest.mark.asyncio
    async def test_retry_on_parse_failure(self, service, mock_ollama_client):
        """Test retry behavior on parse failure."""
        # First call returns invalid JSON, second returns valid
        mock_ollama_client.generate.side_effect = [
            "Invalid response without JSON",
            json.dumps({
                'dimensions': ['category'],
                'measures': ['sales'],
                'filters': [],
                'order_by': [],
                'limit': 100
            })
        ]
        
        intent = await service.parse_query(
            natural_language="Show me sales by category",
            available_dimensions=['category'],
            available_measures=['sales']
        )
        
        assert intent.dimensions == ['category']
        assert mock_ollama_client.generate.call_count == 2
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, service, mock_ollama_client):
        """Test that error is raised after max retries."""
        mock_ollama_client.generate.return_value = "Always invalid"
        
        with pytest.raises(ValueError) as exc_info:
            await service.parse_query(
                natural_language="Show me data",
                available_dimensions=['dim1'],
                available_measures=['measure1']
            )
        
        assert 'Failed to parse query' in str(exc_info.value)


class TestADR002Compliance:
    """Tests to verify ADR-002 compliance: No code generation."""
    
    @pytest.fixture
    def service(self):
        """Create service with mock client."""
        client = AsyncMock(spec=OllamaClient)
        return NLToParametersService(ollama_client=client)
    
    def test_query_intent_contains_no_code(self):
        """Verify QueryIntent cannot contain executable code."""
        # Attempt to inject SQL
        with pytest.raises(ValueError):
            QueryIntent(
                dimensions=['id; DROP TABLE users'],
                measures=['total']
            )
    
    def test_filter_blocks_sql_in_column(self):
        """Verify filters block SQL injection in column names."""
        with pytest.raises(ValueError):
            FilterCondition(
                column='id); DELETE FROM users; --',
                operator='=',
                value='1'
            )
    
    def test_filter_blocks_dangerous_operators(self):
        """Verify only safe operators are allowed."""
        # These should work
        safe_ops = ['=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN', 'NOT IN', 'BETWEEN']
        for op in safe_ops:
            FilterCondition(column='col', operator=op, value='val')
        
        # This should fail
        with pytest.raises(ValueError):
            FilterCondition(column='col', operator='EXECUTE', value='val')
    
    def test_output_is_always_structured_data(self):
        """Verify service outputs are always structured data, never strings of code."""
        intent = QueryIntent(
            dimensions=['category'],
            measures=['total'],
            limit=100
        )
        
        # Convert to dict
        data = intent.model_dump()
        
        # Verify it's pure data, no SQL strings
        assert isinstance(data['dimensions'], list)
        assert isinstance(data['measures'], list)
        assert isinstance(data['limit'], int)
        
        # Check no SQL keywords leaked through
        data_str = str(data)
        assert 'SELECT' not in data_str.upper()
        assert 'FROM' not in data_str.upper()
        assert 'WHERE' not in data_str.upper()
