# Implementation 022: Ollama Integration

## Summary

This implementation adds Ollama integration for natural language processing capabilities in NovaSight. The integration strictly follows ADR-002 (Template Engine Rule) - the LLM only generates validated parameters, never executable code.

## Components Created

### 1. Ollama Client (`backend/app/services/ollama/client.py`)

Async client for Ollama API with:
- Text generation (sync and streaming)
- Chat completion with message history
- Health checking
- Model listing
- Automatic retry and error handling

```python
from app.services.ollama.client import OllamaClient, get_ollama_client

# Using context manager
async with OllamaClient() as client:
    response = await client.generate(
        prompt="Analyze this data",
        system="You are a data analyst",
        temperature=0.1
    )
```

### 2. NL-to-Parameters Service (`backend/app/services/ollama/nl_to_params.py`)

Converts natural language to validated query parameters:

- `QueryIntent` - Validated query structure (dimensions, measures, filters, etc.)
- `FilterCondition` - Validated filter with operator whitelist
- `OrderBySpec` - Validated ordering specification
- `NLToParametersService` - Main service class

**Key Security Features:**
- Pydantic validation on all outputs
- SQL identifier pattern enforcement
- Operator whitelist (no arbitrary SQL)
- Reference validation against schema
- Retry with validation on parse failures

```python
from app.services.ollama.nl_to_params import NLToParametersService

service = NLToParametersService(ollama_client)
intent = await service.parse_query(
    natural_language="Show me total sales by product category",
    available_dimensions=['product_category', 'region'],
    available_measures=['total_sales', 'order_count'],
    strict=True  # Reject unknown references
)
# intent.dimensions = ['product_category']
# intent.measures = ['total_sales']
```

### 3. Prompt Templates (`backend/app/services/ollama/prompt_templates.py`)

Structured prompts for different NL tasks:
- Query intent parsing
- Filter extraction
- Data exploration suggestions
- Query result explanation
- Error recovery

### 4. AI Assistant API (`backend/app/api/v1/assistant.py`)

REST endpoints for AI-assisted analytics:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/assistant/query` | POST | Parse NL query and optionally execute |
| `/api/v1/assistant/explain` | POST | Generate explanation of results |
| `/api/v1/assistant/suggest` | POST | Suggest analyses based on schema |
| `/api/v1/assistant/health` | GET | Check Ollama health |
| `/api/v1/assistant/models` | GET | List available models |

## Configuration

Add to your environment or config:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## ADR-002 Compliance

This implementation strictly adheres to ADR-002:

1. **LLM generates parameters only** - Never raw SQL or code
2. **All output is validated** - Pydantic models with strict patterns
3. **Reference validation** - Only allows known dimensions/measures
4. **Operator whitelist** - Only safe SQL operators allowed
5. **Execution through SemanticService** - All queries go through template-based system

## API Usage Examples

### Natural Language Query

```bash
curl -X POST http://localhost:5000/api/v1/assistant/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me total sales by product category for the last month",
    "execute": true,
    "explain": true
  }'
```

Response:
```json
{
  "intent": {
    "dimensions": ["product_category"],
    "measures": ["total_sales"],
    "filters": [{"column": "date", "operator": ">=", "value": "2026-01-01"}],
    "order_by": [],
    "limit": 100
  },
  "result": {
    "columns": ["product_category", "total_sales"],
    "rows": [["Electronics", 150000], ["Clothing", 80000]],
    "row_count": 2
  },
  "explanation": {
    "summary": "Electronics leads sales with $150K",
    "key_findings": ["Electronics accounts for 65% of total sales"],
    "recommendations": ["Analyze electronics subcategories"]
  }
}
```

### Suggest Analyses

```bash
curl -X POST http://localhost:5000/api/v1/assistant/suggest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "context": "Looking for revenue growth opportunities"
  }'
```

## Testing

Run tests with:

```bash
cd backend
pytest tests/unit/test_ollama_client.py -v
pytest tests/unit/test_nl_to_params.py -v
pytest tests/unit/test_assistant_api.py -v
```

## Files Created/Modified

### Created
- `backend/app/services/ollama/__init__.py`
- `backend/app/services/ollama/client.py`
- `backend/app/services/ollama/nl_to_params.py`
- `backend/app/services/ollama/prompt_templates.py`
- `backend/app/api/v1/assistant.py`
- `backend/tests/unit/test_ollama_client.py`
- `backend/tests/unit/test_nl_to_params.py`
- `backend/tests/unit/test_assistant_api.py`

### Modified
- `backend/app/decorators.py` - Added `async_route` decorator
- `backend/app/api/v1/__init__.py` - Registered assistant module

## Acceptance Criteria Status

- [x] Ollama client connects successfully
- [x] NL queries parse to structured parameters
- [x] Parameter validation blocks invalid references
- [x] No raw SQL/code in LLM responses
- [x] Health check endpoint works
- [x] Streaming responses work
- [x] Error handling is robust
- [x] ADR-002 compliance verified

## Next Steps

1. Deploy Ollama with appropriate model (llama3.2 or codellama:13b recommended)
2. Configure OLLAMA_BASE_URL in environment
3. Add Redis caching for NL parsing results
4. Add usage tracking and rate limiting
5. Fine-tune prompt templates based on user feedback
