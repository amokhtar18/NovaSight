"""
Tests for NovaSight NL-to-SQL Service
======================================

Tests for query classification, query building, and NL-to-SQL conversion.
Verifies ADR-002 compliance: all SQL is template-generated.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.semantic import Dimension, Measure, AggregationType, DimensionType
from app.services.ollama.query_classifier import (
    QueryClassifier,
    QueryType,
    ClassifiedIntent,
    QueryEntities,
    TimeRange,
)
from app.services.query_builder import (
    QueryBuilder,
    InvalidInputError,
    TemplateRenderError,
)
from app.services.nl_to_sql import (
    NLToSQLService,
    NLToSQLResult,
    NLToSQLError,
    QueryParsingError,
    SemanticResolutionError,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_ollama_client():
    """Create a mock Ollama client."""
    client = MagicMock()
    client.generate = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def sample_dimensions():
    """Create sample dimension objects."""
    dims = []
    
    # Create mock dimension objects
    region_dim = MagicMock(spec=Dimension)
    region_dim.id = uuid4()
    region_dim.name = 'region'
    region_dim.label = 'Region'
    region_dim.expression = 'region'
    region_dim.type = DimensionType.CATEGORICAL
    region_dim.is_hidden = False
    dims.append(region_dim)
    
    product_dim = MagicMock(spec=Dimension)
    product_dim.id = uuid4()
    product_dim.name = 'product_category'
    product_dim.label = 'Product Category'
    product_dim.expression = 'product_category'
    product_dim.type = DimensionType.CATEGORICAL
    product_dim.is_hidden = False
    dims.append(product_dim)
    
    date_dim = MagicMock(spec=Dimension)
    date_dim.id = uuid4()
    date_dim.name = 'order_date'
    date_dim.label = 'Order Date'
    date_dim.expression = 'order_date'
    date_dim.type = DimensionType.TEMPORAL
    date_dim.is_hidden = False
    dims.append(date_dim)
    
    return dims


@pytest.fixture
def sample_measures():
    """Create sample measure objects."""
    measures = []
    
    revenue = MagicMock(spec=Measure)
    revenue.id = uuid4()
    revenue.name = 'total_revenue'
    revenue.label = 'Total Revenue'
    revenue.expression = 'revenue'
    revenue.aggregation = AggregationType.SUM
    revenue.is_hidden = False
    measures.append(revenue)
    
    order_count = MagicMock(spec=Measure)
    order_count.id = uuid4()
    order_count.name = 'order_count'
    order_count.label = 'Order Count'
    order_count.expression = '1'
    order_count.aggregation = AggregationType.COUNT
    order_count.is_hidden = False
    measures.append(order_count)
    
    avg_value = MagicMock(spec=Measure)
    avg_value.id = uuid4()
    avg_value.name = 'avg_order_value'
    avg_value.label = 'Average Order Value'
    avg_value.expression = 'order_value'
    avg_value.aggregation = AggregationType.AVG
    avg_value.is_hidden = False
    measures.append(avg_value)
    
    return measures


# =============================================================================
# Query Classifier Tests
# =============================================================================

class TestQueryClassifier:
    """Tests for query classification."""
    
    @pytest.mark.asyncio
    async def test_classify_aggregation_query(self, mock_ollama_client):
        """Test classification of aggregation query."""
        mock_ollama_client.generate.return_value = '''
        {
            "query_type": "aggregation",
            "confidence": 0.95,
            "entities": {
                "dimensions": ["region"],
                "measures": ["total_revenue"]
            },
            "explanation": "Sum of revenue grouped by region"
        }
        '''
        
        classifier = QueryClassifier(mock_ollama_client)
        intent = await classifier.classify(
            "Show me total revenue by region",
            dimensions=['region', 'product_category'],
            measures=['total_revenue', 'order_count']
        )
        
        assert intent.query_type == QueryType.AGGREGATION
        assert intent.confidence >= 0.9
        assert 'region' in intent.entities.dimensions
        assert 'total_revenue' in intent.entities.measures
    
    @pytest.mark.asyncio
    async def test_classify_trend_query(self, mock_ollama_client):
        """Test classification of trend query."""
        mock_ollama_client.generate.return_value = '''
        {
            "query_type": "trend",
            "confidence": 0.88,
            "entities": {
                "dimensions": ["order_date"],
                "measures": ["total_revenue"]
            },
            "time_range": {
                "start": "2025-01-01",
                "end": "2025-12-31",
                "granularity": "month"
            },
            "explanation": "Monthly revenue trend"
        }
        '''
        
        classifier = QueryClassifier(mock_ollama_client)
        intent = await classifier.classify(
            "Show me the monthly revenue trend for 2025",
            dimensions=['order_date', 'region'],
            measures=['total_revenue']
        )
        
        assert intent.query_type == QueryType.TREND
        assert intent.time_range is not None
        assert intent.time_range.granularity == 'month'
    
    @pytest.mark.asyncio
    async def test_classify_comparison_query(self, mock_ollama_client):
        """Test classification of comparison query."""
        mock_ollama_client.generate.return_value = '''
        {
            "query_type": "comparison",
            "confidence": 0.92,
            "entities": {
                "dimensions": ["product_category"],
                "measures": ["total_revenue"],
                "compare_dimension": "region",
                "compare_values": ["North", "South"]
            },
            "explanation": "Compare revenue between North and South regions"
        }
        '''
        
        classifier = QueryClassifier(mock_ollama_client)
        intent = await classifier.classify(
            "Compare revenue between North and South regions by product",
            dimensions=['region', 'product_category'],
            measures=['total_revenue']
        )
        
        assert intent.query_type == QueryType.COMPARISON
        assert intent.entities.compare_dimension == 'region'
        assert len(intent.entities.compare_values) == 2
    
    @pytest.mark.asyncio
    async def test_classify_top_n_query(self, mock_ollama_client):
        """Test classification of top N query."""
        mock_ollama_client.generate.return_value = '''
        {
            "query_type": "top_n",
            "confidence": 0.97,
            "entities": {
                "dimensions": ["product_category"],
                "measures": ["total_revenue"],
                "top_n": 10
            },
            "explanation": "Top 10 products by revenue"
        }
        '''
        
        classifier = QueryClassifier(mock_ollama_client)
        intent = await classifier.classify(
            "Show me the top 10 products by revenue",
            dimensions=['product_category'],
            measures=['total_revenue']
        )
        
        assert intent.query_type == QueryType.TOP_N
        assert intent.entities.top_n == 10
    
    @pytest.mark.asyncio
    async def test_filter_to_available_entities(self, mock_ollama_client):
        """Test that classifier filters to available entities only."""
        mock_ollama_client.generate.return_value = '''
        {
            "query_type": "aggregation",
            "confidence": 0.85,
            "entities": {
                "dimensions": ["region", "unknown_dim"],
                "measures": ["total_revenue", "unknown_measure"]
            }
        }
        '''
        
        classifier = QueryClassifier(mock_ollama_client)
        intent = await classifier.classify(
            "Show revenue by region and other things",
            dimensions=['region'],
            measures=['total_revenue']
        )
        
        # Unknown entities should be filtered out
        assert 'unknown_dim' not in intent.entities.dimensions
        assert 'unknown_measure' not in intent.entities.measures
        assert 'region' in intent.entities.dimensions
        assert 'total_revenue' in intent.entities.measures


# =============================================================================
# Query Builder Tests
# =============================================================================

class TestQueryBuilder:
    """Tests for SQL query building."""
    
    def test_validate_dimension_objects(self, sample_dimensions):
        """Test that builder validates dimension objects."""
        builder = QueryBuilder()
        
        # Should not raise for valid dimensions
        builder._validate_model_inputs(sample_dimensions, [])
    
    def test_validate_measure_objects(self, sample_measures):
        """Test that builder validates measure objects."""
        builder = QueryBuilder()
        
        # Should not raise for valid measures
        builder._validate_model_inputs([], sample_measures)
    
    def test_reject_string_dimensions(self):
        """Test that builder rejects raw strings (ADR-002)."""
        builder = QueryBuilder()
        
        with pytest.raises(InvalidInputError):
            # Intentionally passing wrong type to test validation
            builder._validate_model_inputs(['region'], [])  # type: ignore[arg-type]
    
    def test_reject_string_measures(self):
        """Test that builder rejects raw strings (ADR-002)."""
        builder = QueryBuilder()
        
        with pytest.raises(InvalidInputError):
            # Intentionally passing wrong type to test validation
            builder._validate_model_inputs([], ['revenue'])  # type: ignore[arg-type]
    
    def test_valid_operators(self):
        """Test filter operator validation."""
        builder = QueryBuilder()
        
        # Valid operators should work
        valid_filters = [
            {'column': 'region', 'operator': '=', 'value': 'North'},
            {'column': 'revenue', 'operator': '>=', 'value': 1000},
            {'column': 'category', 'operator': 'IN', 'value': ['A', 'B']},
        ]
        
        safe = builder._build_filters(valid_filters)
        assert len(safe) == 3
    
    def test_reject_invalid_operators(self):
        """Test that invalid operators are rejected."""
        builder = QueryBuilder()
        
        # Invalid operator should be filtered out
        filters = [
            {'column': 'region', 'operator': 'DROP', 'value': 'test'},
        ]
        
        safe = builder._build_filters(filters)
        assert len(safe) == 0  # Invalid operator filtered
    
    def test_reject_invalid_column_names(self):
        """Test that invalid column names are rejected."""
        builder = QueryBuilder()
        
        # SQL injection attempt
        filters = [
            {'column': 'region; DROP TABLE users; --', 'operator': '=', 'value': 'x'},
        ]
        
        safe = builder._build_filters(filters)
        assert len(safe) == 0  # Invalid column filtered
    
    def test_cap_limit(self, sample_dimensions, sample_measures):
        """Test that limit is capped at maximum."""
        builder = QueryBuilder()
        
        # Mock template engine
        with patch.object(builder, 'templates') as mock_templates:
            mock_templates.render.return_value = "SELECT * FROM test LIMIT 10000"
            
            # Try to exceed limit
            builder.build_aggregation_query(
                tenant_id='test_tenant',
                dimensions=sample_dimensions[:1],
                measures=sample_measures[:1],
                limit=999999  # Should be capped
            )
            
            # Verify limit was capped in template call
            call_args = mock_templates.render.call_args
            assert call_args[0][1]['limit'] == 10000
    
    def test_sanitize_scalar_values(self):
        """Test value sanitization."""
        builder = QueryBuilder()
        
        # Normal values
        assert builder._sanitize_scalar('hello') == 'hello'
        assert builder._sanitize_scalar(123) == 123
        assert builder._sanitize_scalar(12.5) == 12.5
        assert builder._sanitize_scalar(True) == True
        
        # Long strings are truncated
        long_string = 'a' * 2000
        assert len(builder._sanitize_scalar(long_string)) == 1000


# =============================================================================
# NL-to-SQL Service Tests
# =============================================================================

class TestNLToSQLService:
    """Tests for the NL-to-SQL service."""
    
    @pytest.mark.asyncio
    async def test_convert_aggregation(
        self,
        mock_ollama_client,
        sample_dimensions,
        sample_measures
    ):
        """Test converting aggregation query."""
        # Mock classifier response
        mock_ollama_client.generate.side_effect = [
            # Classifier response
            '''
            {
                "query_type": "aggregation",
                "confidence": 0.95,
                "entities": {
                    "dimensions": ["region"],
                    "measures": ["total_revenue"]
                }
            }
            ''',
            # Param extractor response
            '''
            {
                "dimensions": ["region"],
                "measures": ["total_revenue"],
                "filters": [],
                "order_by": [],
                "limit": 100
            }
            '''
        ]
        
        # Mock semantic service
        mock_semantic = MagicMock()
        mock_model = MagicMock()
        mock_model.dimensions.all.return_value = sample_dimensions
        mock_model.measures.all.return_value = sample_measures
        mock_semantic.list_models.return_value = [mock_model]
        
        with patch('app.services.nl_to_sql.SemanticService', mock_semantic):
            service = NLToSQLService(mock_ollama_client)
            
            # Mock query builder to return SQL
            with patch.object(service.builder, 'build_aggregation_query') as mock_build:
                mock_build.return_value = "SELECT region, SUM(revenue) FROM tenant_test.events GROUP BY region"
                
                result = await service.convert(
                    tenant_id='test',
                    natural_language="Show total revenue by region"
                )
        
        assert result.sql is not None
        assert result.intent.query_type == QueryType.AGGREGATION
        assert len(result.resolved_dimensions) > 0
        assert len(result.resolved_measures) > 0
    
    @pytest.mark.asyncio
    async def test_resolution_filters_to_available(
        self,
        mock_ollama_client,
        sample_dimensions,
        sample_measures
    ):
        """Test that resolution filters to available entities."""
        service = NLToSQLService(mock_ollama_client)
        
        resolved_dims, resolved_measures, warnings = service._resolve_entities(
            dimension_names=['region', 'unknown_dimension'],
            measure_names=['total_revenue', 'unknown_measure'],
            all_dimensions=sample_dimensions,
            all_measures=sample_measures,
            strict=False
        )
        
        assert len(resolved_dims) == 1
        assert resolved_dims[0].name == 'region'
        assert len(resolved_measures) == 1
        assert resolved_measures[0].name == 'total_revenue'
        assert len(warnings) == 2  # Two unknown entities
    
    def test_generate_explanation(self, sample_dimensions, sample_measures):
        """Test explanation generation."""
        service = NLToSQLService(MagicMock())
        
        intent = ClassifiedIntent(
            query_type=QueryType.AGGREGATION,
            confidence=0.9,
            entities=QueryEntities(
                dimensions=['region'],
                measures=['total_revenue']
            ),
            original_query="Show revenue by region"
        )
        
        from app.services.ollama.nl_to_params import QueryIntent
        params = QueryIntent(
            dimensions=['region'],
            measures=['total_revenue']
        )
        
        explanation = service._generate_explanation(
            intent, params,
            sample_dimensions[:1],
            sample_measures[:1]
        )
        
        assert 'Region' in explanation or 'region' in explanation
        assert 'Total Revenue' in explanation or 'total_revenue' in explanation
    
    def test_calculate_confidence(self):
        """Test confidence calculation."""
        service = NLToSQLService(MagicMock())
        
        # All entities resolved
        confidence = service._calculate_confidence(
            classification_confidence=0.9,
            resolved_dims=2,
            requested_dims=2,
            resolved_measures=3,
            requested_measures=3
        )
        assert confidence > 0.8
        
        # Half entities resolved
        confidence = service._calculate_confidence(
            classification_confidence=0.9,
            resolved_dims=1,
            requested_dims=2,
            resolved_measures=1,
            requested_measures=2
        )
        assert 0.5 < confidence < 0.9
        
        # No entities resolved
        confidence = service._calculate_confidence(
            classification_confidence=0.9,
            resolved_dims=0,
            requested_dims=2,
            resolved_measures=0,
            requested_measures=2
        )
        assert confidence < 0.4


# =============================================================================
# ADR-002 Compliance Tests
# =============================================================================

class TestADR002Compliance:
    """Tests verifying ADR-002 compliance: no arbitrary code generation."""
    
    def test_query_builder_only_accepts_model_objects(
        self,
        sample_dimensions,
        sample_measures
    ):
        """Verify QueryBuilder only accepts validated model objects."""
        builder = QueryBuilder()
        
        # Raw strings should be rejected - intentionally passing wrong types
        with pytest.raises(InvalidInputError):
            builder.build_aggregation_query(
                tenant_id='test',
                dimensions=['region'],  # type: ignore[arg-type]
                measures=sample_measures
            )
        
        with pytest.raises(InvalidInputError):
            builder.build_aggregation_query(
                tenant_id='test',
                dimensions=sample_dimensions,
                measures=['revenue']  # type: ignore[arg-type]
            )
    
    def test_sql_never_from_llm_output(self, mock_ollama_client):
        """Verify SQL is never directly from LLM output."""
        # Even if LLM returns SQL, it should not be used
        mock_ollama_client.generate.return_value = '''
        {
            "query_type": "aggregation",
            "confidence": 0.95,
            "entities": {
                "dimensions": ["region"],
                "measures": ["revenue"]
            },
            "sql": "SELECT * FROM users; DROP TABLE users; --"
        }
        '''
        
        # The classifier should extract intent, not SQL
        import asyncio
        classifier = QueryClassifier(mock_ollama_client)
        
        intent = asyncio.get_event_loop().run_until_complete(
            classifier.classify(
                "Malicious query",
                dimensions=['region'],
                measures=['revenue']
            )
        )
        
        # Intent should be extracted, but no SQL attribute
        assert not hasattr(intent, 'sql')
        assert intent.query_type == QueryType.AGGREGATION
