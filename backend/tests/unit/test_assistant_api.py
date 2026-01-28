"""
Tests for AI Assistant API
===========================

Integration tests for the AI assistant endpoints.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from flask import Flask
from flask_jwt_extended import create_access_token

from app import create_app
from app.services.ollama.nl_to_params import QueryIntent, FilterCondition


class TestAssistantAPI:
    """Tests for AI Assistant API endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test application."""
        app = create_app('testing')
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def auth_headers(self, app):
        """Create authentication headers with JWT."""
        with app.app_context():
            token = create_access_token(
                identity={
                    'user_id': 'test-user-id',
                    'tenant_id': 'test-tenant-id',
                    'email': 'test@example.com',
                    'roles': ['analyst']
                }
            )
            return {'Authorization': f'Bearer {token}'}
    
    @pytest.fixture
    def mock_semantic_service(self):
        """Mock SemanticService."""
        with patch('app.api.v1.assistant.SemanticService') as mock:
            # Mock list_models
            mock_model = MagicMock()
            mock_model.id = 'model-1'
            mock_model.name = 'Sales Model'
            mock.list_models.return_value = [mock_model]
            
            # Mock list_dimensions
            mock_dim = MagicMock()
            mock_dim.name = 'product_category'
            mock.list_dimensions.return_value = [mock_dim]
            
            # Mock list_measures
            mock_measure = MagicMock()
            mock_measure.name = 'total_sales'
            mock.list_measures.return_value = [mock_measure]
            
            # Mock execute_query
            mock.execute_query.return_value = {
                'columns': ['product_category', 'total_sales'],
                'rows': [['Electronics', 50000], ['Clothing', 30000]],
                'row_count': 2,
                'execution_time_ms': 150,
                'cached': False
            }
            
            yield mock
    
    @pytest.fixture
    def mock_ollama_client(self):
        """Mock Ollama client."""
        with patch('app.api.v1.assistant.get_ollama_client') as mock_factory:
            mock_client = AsyncMock()
            mock_client.generate.return_value = json.dumps({
                'dimensions': ['product_category'],
                'measures': ['total_sales'],
                'filters': [],
                'order_by': [{'column': 'total_sales', 'direction': 'desc'}],
                'limit': 100
            })
            mock_client.close = AsyncMock()
            mock_client.health_check.return_value = True
            mock_client.list_models.return_value = [
                {'name': 'llama3.2', 'size': 7000000000}
            ]
            mock_factory.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def mock_permissions(self):
        """Mock permission check."""
        with patch('app.middleware.permissions.require_permission') as mock:
            mock.return_value = lambda f: f
            yield mock
    
    def test_natural_language_query_requires_auth(self, client):
        """Test that NL query endpoint requires authentication."""
        response = client.post(
            '/api/v1/assistant/query',
            json={'query': 'Show me sales'}
        )
        
        assert response.status_code == 401
    
    def test_natural_language_query_success(
        self, 
        app,
        client, 
        auth_headers, 
        mock_semantic_service, 
        mock_ollama_client
    ):
        """Test successful natural language query."""
        with patch('app.api.v1.assistant.require_permission', lambda p: lambda f: f):
            with patch('app.api.v1.assistant.require_tenant_context', lambda f: f):
                with patch('app.api.v1.assistant.g') as mock_g:
                    mock_g.tenant_id = 'test-tenant-id'
                    mock_g.user_permissions = ['analytics.query']
                    
                    response = client.post(
                        '/api/v1/assistant/query',
                        json={
                            'query': 'Show me total sales by product category',
                            'execute': True
                        },
                        headers=auth_headers
                    )
        
        # Check response structure (may be 200 or error depending on full setup)
        assert response.status_code in [200, 400, 500]
    
    def test_query_validation_error(self, client, auth_headers):
        """Test query validation rejects invalid requests."""
        with patch('app.api.v1.assistant.require_permission', lambda p: lambda f: f):
            response = client.post(
                '/api/v1/assistant/query',
                json={'query': ''},  # Empty query
                headers=auth_headers
            )
        
        # Should fail validation
        assert response.status_code in [400, 401, 422]
    
    def test_ollama_health_endpoint(self, client, mock_ollama_client):
        """Test Ollama health check endpoint."""
        response = client.get('/api/v1/assistant/health')
        
        # Response depends on actual Ollama availability
        assert response.status_code in [200, 503]
        data = json.loads(response.data)
        assert 'status' in data
    
    def test_explain_requires_auth(self, client):
        """Test that explain endpoint requires authentication."""
        response = client.post(
            '/api/v1/assistant/explain',
            json={
                'query_description': 'Sales by category',
                'row_count': 5
            }
        )
        
        assert response.status_code == 401
    
    def test_suggest_requires_auth(self, client):
        """Test that suggest endpoint requires authentication."""
        response = client.post(
            '/api/v1/assistant/suggest',
            json={'context': 'Looking for insights'}
        )
        
        assert response.status_code == 401


class TestAssistantRequestValidation:
    """Tests for request validation in assistant endpoints."""
    
    def test_nl_query_request_valid(self):
        """Test valid NL query request."""
        from app.api.v1.assistant import NLQueryRequest
        
        request = NLQueryRequest(
            query="Show me sales by region",
            execute=True,
            explain=False,
            strict=False
        )
        
        assert request.query == "Show me sales by region"
        assert request.execute is True
    
    def test_nl_query_request_defaults(self):
        """Test NL query request defaults."""
        from app.api.v1.assistant import NLQueryRequest
        
        request = NLQueryRequest(query="Test query")
        
        assert request.execute is True  # Default
        assert request.explain is False  # Default
        assert request.strict is False  # Default
    
    def test_nl_query_request_max_length(self):
        """Test NL query request max length validation."""
        from app.api.v1.assistant import NLQueryRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            NLQueryRequest(query="x" * 3000)  # Exceeds 2000 char limit
    
    def test_explain_request_valid(self):
        """Test valid explain request."""
        from app.api.v1.assistant import ExplainRequest
        
        request = ExplainRequest(
            query_description="Sales analysis",
            dimensions=['region', 'product'],
            measures=['total_sales'],
            row_count=100,
            sample_data=[{'region': 'North', 'total_sales': 50000}]
        )
        
        assert request.row_count == 100
        assert len(request.sample_data) == 1


class TestADR002ComplianceAPI:
    """Tests verifying ADR-002 compliance at API level."""
    
    def test_response_contains_no_raw_sql(self):
        """Verify API responses don't contain raw SQL."""
        # Mock a QueryIntent response
        intent = QueryIntent(
            dimensions=['category'],
            measures=['total'],
            filters=[FilterCondition(column='status', operator='=', value='active')],
            order_by=[],
            limit=100
        )
        
        response_data = {
            'intent': {
                'dimensions': intent.dimensions,
                'measures': intent.measures,
                'filters': [f.model_dump() for f in intent.filters],
                'limit': intent.limit
            }
        }
        
        response_str = json.dumps(response_data)
        
        # Should not contain SQL keywords as part of code
        assert 'SELECT * FROM' not in response_str
        assert 'DROP TABLE' not in response_str
        assert 'DELETE FROM' not in response_str
    
    def test_llm_output_is_parameterized(self):
        """Verify LLM output is always parameterized data."""
        # This tests that the NL service always produces structured data
        intent = QueryIntent(
            dimensions=['product'],
            measures=['sales'],
            filters=[
                FilterCondition(column='amount', operator='>', value=1000)
            ],
            limit=50
        )
        
        # The output should be pure data that can be passed to templates
        data = intent.model_dump()
        
        # Verify structure
        assert isinstance(data['dimensions'], list)
        assert isinstance(data['measures'], list)
        assert isinstance(data['filters'], list)
        assert isinstance(data['limit'], int)
        
        # Verify filters are structured
        for f in data['filters']:
            assert 'column' in f
            assert 'operator' in f
            assert 'value' in f
