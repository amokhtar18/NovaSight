"""
Tests for Ollama Client
========================

Unit tests for the Ollama client service.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.services.ollama.client import (
    OllamaClient,
    OllamaError,
    OllamaConnectionError,
    OllamaGenerationError,
)


class TestOllamaClient:
    """Tests for OllamaClient class."""
    
    @pytest.fixture
    def client(self):
        """Create Ollama client for testing."""
        return OllamaClient(
            base_url='http://localhost:11434',
            model='llama3.2',
            timeout=30.0
        )
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Test client is properly initialized."""
        assert client.base_url == 'http://localhost:11434'
        assert client.model == 'llama3.2'
        assert client.timeout == 30.0
        assert client._client is None
    
    @pytest.mark.asyncio
    async def test_generate_success(self, client):
        """Test successful text generation."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': 'Generated text response',
            'model': 'llama3.2'
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client
            
            result = await client.generate(
                prompt='Test prompt',
                system='You are helpful',
                temperature=0.1
            )
            
            assert result == 'Generated text response'
            mock_http_client.post.assert_called_once()
            call_args = mock_http_client.post.call_args
            assert '/api/generate' in call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_generate_with_json_format(self, client):
        """Test generation with JSON format requested."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'response': '{"key": "value"}',
            'model': 'llama3.2'
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client
            
            result = await client.generate(
                prompt='Return JSON',
                format='json'
            )
            
            assert result == '{"key": "value"}'
            call_args = mock_http_client.post.call_args
            assert call_args[1]['json']['format'] == 'json'
    
    @pytest.mark.asyncio
    async def test_generate_connection_error(self, client):
        """Test handling of connection errors."""
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(
                side_effect=httpx.ConnectError('Connection refused')
            )
            mock_get_client.return_value = mock_http_client
            
            with pytest.raises(OllamaConnectionError) as exc_info:
                await client.generate(prompt='Test')
            
            assert 'Cannot connect to Ollama' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_http_error(self, client):
        """Test handling of HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            'Internal Server Error',
            request=MagicMock(),
            response=mock_response
        )
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client
            
            with pytest.raises(OllamaGenerationError) as exc_info:
                await client.generate(prompt='Test')
            
            assert 'API error' in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client):
        """Test health check when service is healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client
            
            result = await client.health_check()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, client):
        """Test health check when service is unavailable."""
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get = AsyncMock(side_effect=Exception('Connection failed'))
            mock_get_client.return_value = mock_http_client
            
            result = await client.health_check()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_list_models(self, client):
        """Test listing available models."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'models': [
                {'name': 'llama3.2', 'size': 7000000000},
                {'name': 'codellama:13b', 'size': 13000000000}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.get = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client
            
            result = await client.list_models()
            
            assert len(result) == 2
            assert result[0]['name'] == 'llama3.2'
    
    @pytest.mark.asyncio
    async def test_chat_completion(self, client):
        """Test chat completion with message history."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': {
                'role': 'assistant',
                'content': 'Hello! How can I help you?'
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.post = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_http_client
            
            result = await client.chat(
                messages=[
                    {'role': 'user', 'content': 'Hello'}
                ]
            )
            
            assert result == 'Hello! How can I help you?'
    
    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager functionality."""
        with patch.object(client, '_get_client') as mock_get_client:
            mock_http_client = AsyncMock()
            mock_http_client.is_closed = False
            mock_http_client.aclose = AsyncMock()
            mock_get_client.return_value = mock_http_client
            
            async with client as c:
                assert c is client
            
            # Client should attempt to get the client on enter
            mock_get_client.assert_called()
    
    @pytest.mark.asyncio
    async def test_close(self, client):
        """Test closing the client."""
        mock_http_client = AsyncMock()
        mock_http_client.is_closed = False
        mock_http_client.aclose = AsyncMock()
        client._client = mock_http_client
        
        await client.close()
        
        mock_http_client.aclose.assert_called_once()
        assert client._client is None
