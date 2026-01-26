# 022 - Ollama Integration

## Metadata

```yaml
prompt_id: "022"
phase: 3
agent: "@ai"
model: "opus 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["003"]
```

## Objective

Integrate Ollama for local LLM capabilities with the template-only code generation constraint.

## Task Description

Create a service that interfaces with Ollama for NL-to-SQL and parameter generation, ensuring all code comes from templates.

## Critical Security Mandate

**ADR-002 Compliance**: Ollama NEVER generates executable code directly. It ONLY generates:
1. Natural language explanations
2. **Validated parameters** for templates
3. Query intent classification

All executable artifacts MUST come from the template engine.

## Requirements

### Ollama Client

```python
# backend/app/services/ollama/client.py
import httpx
from typing import Dict, Any, Optional, AsyncGenerator
import json

class OllamaClient:
    """Client for Ollama API."""
    
    def __init__(
        self,
        base_url: str = 'http://localhost:11434',
        model: str = 'codellama:13b',
        timeout: float = 60.0
    ):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """Generate completion from Ollama."""
        
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': stream,
            'options': {
                'temperature': temperature,
                'num_predict': max_tokens,
            }
        }
        
        if system:
            payload['system'] = system
        
        if stream:
            return self._stream_response(payload)
        
        response = await self._client.post(
            f'{self.base_url}/api/generate',
            json=payload
        )
        response.raise_for_status()
        return response.json()['response']
    
    async def _stream_response(
        self, 
        payload: Dict
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens."""
        async with self._client.stream(
            'POST',
            f'{self.base_url}/api/generate',
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if line:
                    data = json.loads(line)
                    if 'response' in data:
                        yield data['response']
    
    async def health_check(self) -> bool:
        """Check if Ollama is available."""
        try:
            response = await self._client.get(f'{self.base_url}/api/version')
            return response.status_code == 200
        except Exception:
            return False
```

### NL-to-Parameters Service

```python
# backend/app/services/ollama/nl_to_params.py
from typing import Dict, Any, List
from pydantic import BaseModel, ValidationError
import json

from app.services.ollama.client import OllamaClient
from app.services.template_engine import TemplateEngine
from app.services.template_engine.validator import (
    ColumnDefinition,
    SQLIdentifier
)

class QueryIntent(BaseModel):
    """Parsed query intent from natural language."""
    dimensions: List[str]
    measures: List[str]
    filters: List[Dict[str, Any]] = []
    order_by: List[Dict[str, str]] = []
    limit: int = 100

class NLToParametersService:
    """
    Converts natural language to validated template parameters.
    
    SECURITY: This service NEVER generates code. It only generates
    parameters that are validated before being passed to templates.
    """
    
    SYSTEM_PROMPT = """You are a data analysis assistant. Your job is to:
1. Understand the user's natural language query
2. Extract structured parameters for analytics queries
3. Return ONLY valid JSON with the extracted parameters

You must respond with valid JSON matching this schema:
{
    "dimensions": ["list", "of", "dimension", "names"],
    "measures": ["list", "of", "measure", "names"],
    "filters": [{"column": "name", "operator": "=", "value": "x"}],
    "order_by": [{"column": "name", "direction": "desc"}],
    "limit": 100
}

Available dimensions: {dimensions}
Available measures: {measures}

IMPORTANT: Only use dimensions and measures from the available lists.
"""
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        template_engine: TemplateEngine
    ):
        self.ollama = ollama_client
        self.templates = template_engine
    
    async def parse_query(
        self,
        natural_language: str,
        available_dimensions: List[str],
        available_measures: List[str]
    ) -> QueryIntent:
        """
        Parse natural language into validated query parameters.
        
        Returns structured, validated parameters - never raw code.
        """
        
        # Build context-aware prompt
        system = self.SYSTEM_PROMPT.format(
            dimensions=', '.join(available_dimensions),
            measures=', '.join(available_measures)
        )
        
        # Get LLM response
        response = await self.ollama.generate(
            prompt=f"Convert this to a query: {natural_language}",
            system=system,
            temperature=0.1  # Low temperature for consistency
        )
        
        # Parse and validate response
        try:
            # Extract JSON from response
            params = self._extract_json(response)
            
            # Validate with Pydantic
            intent = QueryIntent(**params)
            
            # Additional validation: ensure all references are valid
            self._validate_references(
                intent, 
                available_dimensions, 
                available_measures
            )
            
            return intent
            
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Failed to parse LLM response: {e}")
    
    def _extract_json(self, response: str) -> Dict:
        """Extract JSON from LLM response."""
        # Try to find JSON in response
        start = response.find('{')
        end = response.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(response[start:end])
        raise json.JSONDecodeError("No JSON found", response, 0)
    
    def _validate_references(
        self,
        intent: QueryIntent,
        valid_dimensions: List[str],
        valid_measures: List[str]
    ) -> None:
        """Validate that all references are to known entities."""
        for dim in intent.dimensions:
            if dim not in valid_dimensions:
                raise ValueError(f"Unknown dimension: {dim}")
        
        for measure in intent.measures:
            if measure not in valid_measures:
                raise ValueError(f"Unknown measure: {measure}")
```

### AI Assistant API

```python
# backend/app/api/v1/assistant.py
from flask import Blueprint, request, g
from app.services.ollama.nl_to_params import NLToParametersService
from app.services.semantic_service import SemanticService
from app.middleware.permissions import require_permission

assistant_bp = Blueprint('assistant', __name__)

@assistant_bp.route('/query', methods=['POST'])
@require_permission('analytics.query')
async def natural_language_query():
    """Convert natural language to analytics query and execute."""
    data = request.json
    nl_query = data['query']
    
    # Get available dimensions and measures for tenant
    semantic_models = SemanticService.list_models(g.tenant.id)
    dimensions = [d.name for m in semantic_models for d in m.dimensions]
    measures = [m.name for model in semantic_models for m in model.measures]
    
    # Parse natural language to parameters
    nl_service = NLToParametersService(...)
    intent = await nl_service.parse_query(nl_query, dimensions, measures)
    
    # Execute query using semantic service (template-based)
    result = SemanticService.execute_query(
        tenant_id=g.tenant.id,
        dimensions=intent.dimensions,
        measures=intent.measures,
        filters=intent.filters,
        order_by=intent.order_by,
        limit=intent.limit
    )
    
    return {
        'intent': intent.dict(),
        'result': result,
    }
```

## Expected Output

```
backend/app/services/ollama/
├── __init__.py
├── client.py
├── nl_to_params.py
└── prompt_templates.py

backend/app/api/v1/
└── assistant.py
```

## Acceptance Criteria

- [ ] Ollama client connects successfully
- [ ] NL queries parse to structured parameters
- [ ] Parameter validation blocks invalid references
- [ ] No raw SQL/code in LLM responses
- [ ] Health check endpoint works
- [ ] Streaming responses work
- [ ] Error handling is robust
- [ ] ADR-002 compliance verified

## Reference Documents

- [AI Agent](../agents/ai-agent.agent.md)
- [Template Engine Core](./008-template-engine-core.md)
- [ADR-002](../../docs/requirements/Architecture_Decisions.md)
