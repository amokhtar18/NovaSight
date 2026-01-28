# Implementation 023: NL-to-SQL Service

## Overview

This document describes the implementation of the NL-to-SQL Service, which converts natural language queries into ClickHouse SQL using the semantic layer and validated templates.

**Prompt ID**: 023  
**Phase**: 3  
**Agent**: @ai  
**Priority**: P0  
**Status**: ✅ Complete

## Implemented Components

### 1. Query Classifier (`backend/app/services/ollama/query_classifier.py`)

Classifies natural language queries into structured intents:

- **Query Types Supported**:
  - `aggregation` - "total sales by region"
  - `comparison` - "compare Q1 vs Q2"
  - `trend` - "sales trend over time"
  - `top_n` - "top 10 products"
  - `filter` - "orders from California"
  - `drill_down` - "break down by category"
  - `distribution` - "distribution of order values"
  - `correlation` - "relationship between X and Y"

- **Key Classes**:
  - `QueryType` - Enum of query types
  - `TimeRange` - Validated time range with granularity
  - `QueryEntities` - Extracted dimensions, measures, and values
  - `ClassifiedIntent` - Complete classification result
  - `QueryClassifier` - Main classification service

### 2. Query Builder (`backend/app/services/query_builder.py`)

Builds SQL queries from validated parameters using templates:

- **Security Features (ADR-002)**:
  - Only accepts `Dimension` and `Measure` model objects
  - Rejects raw strings to prevent injection
  - Validates all operators against whitelist
  - Validates column names with regex
  - Caps limits and sanitizes values

- **Query Types**:
  - `build_aggregation_query()` - Standard aggregation with GROUP BY
  - `build_comparison_query()` - Side-by-side comparison (Q1 vs Q2)
  - `build_trend_query()` - Time-series with granularity
  - `build_top_n_query()` - Ranking queries

### 3. NL-to-SQL Service (`backend/app/services/nl_to_sql.py`)

Orchestrates the complete NL-to-SQL pipeline:

```
Natural Language → Classify Intent → Extract Parameters → Resolve Entities → Generate SQL
       ↓               (LLM)              (LLM)            (Database)        (Templates)
```

- **Pipeline Steps**:
  1. Get available semantic entities for tenant
  2. Classify query intent (LLM)
  3. Extract parameters from NL (LLM)
  4. Resolve names to model objects (Database)
  5. Build SQL from templates

- **Key Methods**:
  - `convert()` - Main conversion method
  - `suggest_queries()` - Generate query suggestions

### 4. SQL Templates

Located in `backend/templates/sql/`:

| Template | Description |
|----------|-------------|
| `analytics_query.sql.j2` | Aggregation with GROUP BY, filters, ORDER BY |
| `comparison_query.sql.j2` | Side-by-side comparison using CASE |
| `trend_query.sql.j2` | Time-series with granularity functions |
| `top_n_query.sql.j2` | Ranking queries with LIMIT |

### 5. API Endpoints

Added to `backend/app/api/v1/assistant.py`:

#### POST `/api/v1/assistant/nl-to-sql`

Convert natural language to ClickHouse SQL.

**Request**:
```json
{
  "query": "Show me total revenue by region for last month",
  "model_filter": "sales_model",
  "strict_mode": true,
  "include_sql": true
}
```

**Response**:
```json
{
  "sql": "SELECT region, SUM(revenue) AS total_revenue FROM tenant_xxx.events ...",
  "intent": {
    "type": "aggregation",
    "confidence": 0.95,
    "entities": {
      "dimensions": ["region"],
      "measures": ["total_revenue"]
    }
  },
  "resolved": {
    "dimensions": ["region"],
    "measures": ["total_revenue"]
  },
  "explanation": "This query will calculate Total Revenue grouped by Region.",
  "confidence": 0.92,
  "warnings": []
}
```

#### GET `/api/v1/assistant/nl-to-sql/suggestions`

Get suggested queries based on available semantic entities.

## ADR-002 Compliance

The implementation strictly follows ADR-002 (No Arbitrary Code Generation):

1. **LLM generates INTENT only** - The LLM classifies queries and extracts parameters (dimensions, measures, filters) but never generates SQL.

2. **Template-based SQL** - All SQL is generated from pre-approved Jinja2 templates in `backend/templates/sql/`.

3. **Validated Objects Only** - The QueryBuilder only accepts `Dimension` and `Measure` model objects, never raw strings.

4. **Input Validation**:
   - Column names validated with regex: `^[a-zA-Z_][a-zA-Z0-9_]*$`
   - Operators whitelisted: `=`, `!=`, `>`, `<`, `>=`, `<=`, `IN`, `NOT IN`, `LIKE`, `BETWEEN`, etc.
   - Values sanitized and length-limited
   - Limits capped at 10,000 rows

## Files Created/Modified

### Created
- `backend/app/services/ollama/query_classifier.py`
- `backend/app/services/query_builder.py`
- `backend/app/services/nl_to_sql.py`
- `backend/templates/sql/analytics_query.sql.j2`
- `backend/templates/sql/comparison_query.sql.j2`
- `backend/templates/sql/trend_query.sql.j2`
- `backend/templates/sql/top_n_query.sql.j2`
- `backend/tests/unit/test_nl_to_sql.py`

### Modified
- `backend/app/services/ollama/__init__.py` - Added new exports
- `backend/app/api/v1/assistant.py` - Added NL-to-SQL endpoints
- `backend/templates/manifest.json` - Added template definitions

## Testing

Run tests with:
```bash
cd backend
pytest tests/unit/test_nl_to_sql.py -v
```

Test categories:
- Query classification tests
- Query builder validation tests
- NL-to-SQL pipeline tests
- ADR-002 compliance tests

## Usage Example

```python
from app.services.ollama.client import OllamaClient
from app.services.nl_to_sql import NLToSQLService

# Initialize
ollama = OllamaClient()
service = NLToSQLService(ollama)

# Convert NL to SQL
result = await service.convert(
    tenant_id="tenant_123",
    natural_language="Show me total revenue by product category for last quarter"
)

print(result.sql)
# SELECT product_category, SUM(revenue) AS total_revenue 
# FROM tenant_tenant_123.events
# WHERE order_date >= '2025-10-01' AND order_date <= '2025-12-31'
# GROUP BY product_category
# ORDER BY total_revenue DESC
# LIMIT 1000

print(result.explanation)
# "This query will calculate Total Revenue grouped by Product Category 
#  from 2025-10-01 to 2025-12-31."
```

## Dependencies

- Prompt 022: Ollama Integration (OllamaClient)
- Prompt 019: Semantic Layer API (SemanticService, Dimension, Measure)
- Template Engine (ADR-002 compliant code generation)

## Next Steps

- [ ] Add more query templates for advanced analytics
- [ ] Implement query caching
- [ ] Add streaming response for long queries
- [ ] Create frontend integration

---

*Implementation completed: January 28, 2026*
