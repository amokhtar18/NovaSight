"""
NovaSight Ollama Client
========================

Async client for interacting with Ollama API.
Provides text generation with streaming support.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama errors."""
    pass


class OllamaConnectionError(OllamaError):
    """Raised when connection to Ollama fails."""
    pass


class OllamaGenerationError(OllamaError):
    """Raised when generation fails."""
    pass


class OllamaClient:
    """
    Async client for Ollama API.
    
    Provides methods for text generation with optional streaming.
    Supports health checks and model listing.
    
    SECURITY: This client generates text only. All code generation
    MUST go through the template engine (ADR-002 compliance).
    """
    
    def __init__(
        self,
        base_url: str = 'http://localhost:11434',
        model: str = 'Qwen3-vl',
        timeout: float = 120.0,
        max_retries: int = 3
    ):
        """
        Initialize Ollama client.
        
        Args:
            base_url: Ollama API base URL
            model: Default model to use for generation
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=10)
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        stream: bool = False,
        model: Optional[str] = None,
        context: Optional[List[int]] = None,
        format: Optional[str] = None,
    ) -> str:
        """
        Generate completion from Ollama.
        
        Args:
            prompt: The user prompt to generate from
            system: Optional system prompt for context
            temperature: Sampling temperature (0.0-1.0, lower = more deterministic)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            model: Override the default model
            context: Previous conversation context (for multi-turn)
            format: Response format ("json" for JSON output)
        
        Returns:
            Generated text response
        
        Raises:
            OllamaConnectionError: If connection to Ollama fails
            OllamaGenerationError: If generation fails
        """
        client = await self._get_client()
        
        payload: Dict[str, Any] = {
            'model': model or self.model,
            'prompt': prompt,
            'stream': False,  # Always false for this method
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
            }
        }
        
        if system:
            payload['system'] = system
        
        if context:
            payload['context'] = context
        
        if format:
            payload['format'] = format
        
        try:
            response = await client.post(
                f'{self.base_url}/api/generate',
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            logger.debug(
                f"Ollama generation complete: {len(result.get('response', ''))} chars, "
                f"model={result.get('model')}"
            )
            
            return result['response']
            
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Ollama at {self.base_url}: {e}")
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running."
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.status_code}")
            raise OllamaGenerationError(
                f"Ollama API error: {e.response.status_code}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error during generation: {e}")
            raise OllamaGenerationError(f"Generation failed: {e}") from e
    
    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream completion tokens from Ollama.
        
        Args:
            prompt: The user prompt to generate from
            system: Optional system prompt for context
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Override the default model
        
        Yields:
            Individual response tokens
        
        Raises:
            OllamaConnectionError: If connection to Ollama fails
            OllamaGenerationError: If generation fails
        """
        client = await self._get_client()
        
        payload = {
            'model': model or self.model,
            'prompt': prompt,
            'stream': True,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
            }
        }
        
        if system:
            payload['system'] = system
        
        try:
            async with client.stream(
                'POST',
                f'{self.base_url}/api/generate',
                json=payload,
                timeout=self.timeout
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if 'response' in data:
                                yield data['response']
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse streaming line: {line}")
                            continue
                            
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Ollama: {e}")
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}"
            ) from e
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise OllamaGenerationError(f"Streaming failed: {e}") from e
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        model: Optional[str] = None,
        format: Optional[str] = None,
    ) -> str:
        """
        Chat completion using message history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            model: Override the default model
            format: Response format ("json" for JSON output)
        
        Returns:
            Assistant's response message content
        """
        client = await self._get_client()
        
        payload: Dict[str, Any] = {
            'model': model or self.model,
            'messages': messages,
            'stream': False,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
            }
        }
        
        if format:
            payload['format'] = format
        
        try:
            response = await client.post(
                f'{self.base_url}/api/chat',
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            return result['message']['content']
            
        except httpx.ConnectError as e:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}"
            ) from e
        except Exception as e:
            raise OllamaGenerationError(f"Chat completion failed: {e}") from e
    
    async def health_check(self) -> bool:
        """
        Check if Ollama is available and responding.
        
        Returns:
            True if Ollama is healthy, False otherwise
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f'{self.base_url}/api/version',
                timeout=5.0
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models in Ollama.
        
        Returns:
            List of model information dictionaries
        """
        try:
            client = await self._get_client()
            response = await client.get(f'{self.base_url}/api/tags')
            response.raise_for_status()
            
            result = response.json()
            return result.get('models', [])
            
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise OllamaConnectionError(f"Failed to list models: {e}") from e
    
    async def model_info(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a specific model.
        
        Args:
            model: Model name (uses default if not specified)
        
        Returns:
            Model information dictionary
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f'{self.base_url}/api/show',
                json={'name': model or self.model}
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            raise OllamaError(f"Failed to get model info: {e}") from e
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._get_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


def _resolve_ollama_settings(
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resolve Ollama settings with the following precedence:

    1. Active ``InfrastructureConfig`` row for ``ollama`` (tenant → global
       fallback handled by the service).
    2. Flask app config / environment variables.
    3. Hard-coded defaults.

    The DB-backed infrastructure configuration therefore *overrides* any
    ``OLLAMA_BASE_URL`` / ``OLLAMA_MODEL`` env vars whenever an admin has
    saved a config through ``/api/v1/admin/infrastructure``.
    """
    from flask import current_app

    base_url: Optional[str] = None
    model: Optional[str] = None
    timeout: Optional[float] = None

    try:
        from app.domains.tenants.infrastructure.config_service import (
            InfrastructureConfigService,
        )

        service = InfrastructureConfigService()
        cfg = service.get_active_config("ollama", tenant_id)
        if cfg is not None:
            settings = dict(cfg.settings or {})
            # Prefer explicit base_url, otherwise compose from host/port.
            base_url = settings.get("base_url") or (
                f"http://{cfg.host}:{cfg.port}"
                if cfg.host and cfg.port
                else None
            )
            model = settings.get("default_model")
            req_timeout = settings.get("request_timeout")
            if req_timeout is not None:
                try:
                    timeout = float(req_timeout)
                except (TypeError, ValueError):
                    timeout = None
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug(
            "Falling back to env-based Ollama config (%s)", exc
        )

    if not base_url:
        base_url = current_app.config.get(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
    if not model:
        model = current_app.config.get("OLLAMA_MODEL", "llama3.2")
    if timeout is None:
        timeout = float(
            current_app.config.get("OLLAMA_REQUEST_TIMEOUT", 120.0)
        )

    return {"base_url": base_url, "model": model, "timeout": timeout}


def get_ollama_client(
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> OllamaClient:
    """
    Factory function to create OllamaClient.

    Resolution order:
        explicit args > InfrastructureConfig (DB) > Flask config / env > defaults

    Args:
        base_url: Hard override for the Ollama base URL.
        model: Hard override for the default model.
        tenant_id: Optional tenant scope when looking up the DB config.

    Returns:
        Configured OllamaClient instance.
    """
    settings = _resolve_ollama_settings(tenant_id=tenant_id)
    return OllamaClient(
        base_url=base_url or settings["base_url"],
        model=model or settings["model"],
        timeout=settings["timeout"],
    )
