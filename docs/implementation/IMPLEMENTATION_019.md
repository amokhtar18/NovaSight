# Implementation 019 - Semantic Layer API

## Overview

This document describes the implementation of the Semantic Layer API for NovaSight, which provides REST endpoints for managing semantic models, dimensions, measures, relationships, and executing semantic queries against ClickHouse.

## Components Created

### 1. Database Models (`backend/app/models/semantic.py`)

SQLAlchemy models for the semantic layer:

| Model | Purpose |
|-------|---------|
| `SemanticModel` | Main semantic model entity referencing a dbt model |
| `Dimension` | Dimension definitions (categorical, temporal, numeric, hierarchical) |
| `Measure` | Measure definitions with aggregation types |
| `Relationship` | Model-to-model relationships for automatic joins |

**Enums:**
- `DimensionType`: categorical, temporal, numeric, hierarchical
- `AggregationType`: sum, count, avg, min, max, count_distinct, raw, median, percentile
- `ModelType`: fact, dimension, aggregate
- `RelationshipType`: one_to_one, one_to_many, many_to_one, many_to_many
- `JoinType`: LEFT, INNER, RIGHT, FULL

### 2. ClickHouse Client (`backend/app/services/clickhouse_client.py`)

Client for executing queries against tenant-isolated ClickHouse databases:

```python
class ClickHouseClient:
    def execute(query: str, params: Dict) -> QueryResult
    def execute_iter(query: str, params: Dict) -> Iterator
    def insert(table: str, data: List[Dict]) -> int
    def table_exists(table: str) -> bool
    def get_table_schema(table: str) -> Dict[str, str]
```

**Features:**
- Tenant isolation via separate databases
- Query result streaming for large datasets
- Connection pooling
- Mock client for testing

### 3. Pydantic Schemas (`backend/app/schemas/semantic_schemas.py`)

Request/response schemas for API validation:

| Schema | Purpose |
|--------|---------|
| `SemanticModelCreateSchema` | Create semantic model |
| `SemanticModelUpdateSchema` | Update semantic model |
| `DimensionCreateSchema` | Add dimension to model |
| `MeasureCreateSchema` | Add measure to model |
| `RelationshipCreateSchema` | Create model relationship |
| `SemanticQuerySchema` | Execute semantic query |
| `QueryResultSchema` | Query result response |
| `FilterSchema` | Query filter specification |
| `OrderBySchema` | Query ordering specification |

**Filter Operators:**
- `eq`, `ne`, `gt`, `gte`, `lt`, `lte` (comparison)
- `like`, `not_like`, `ilike` (pattern matching)
- `in`, `not_in` (set membership)
- `is_null`, `is_not_null` (null checks)
- `between` (range)

### 4. Semantic Service (`backend/app/services/semantic_service.py`)

Business logic for semantic layer operations:

```python
class SemanticService:
    # Model CRUD
    @staticmethod
    def create_model(tenant_id, name, dbt_model, ...) -> SemanticModel
    @staticmethod
    def get_model(model_id, tenant_id) -> SemanticModel
    @staticmethod
    def update_model(model_id, tenant_id, **kwargs) -> SemanticModel
    @staticmethod
    def delete_model(model_id, tenant_id) -> bool
    
    # Dimension/Measure CRUD
    @staticmethod
    def add_dimension(model_id, tenant_id, **kwargs) -> Dimension
    @staticmethod
    def add_measure(model_id, tenant_id, **kwargs) -> Measure
    
    # Query Execution
    @staticmethod
    def execute_query(tenant_id, dimensions, measures, filters, ...) -> Dict
```

**Query Features:**
- Automatic SQL generation from semantic definitions
- Multi-model join resolution via relationships
- Filter expression building
- Date range filtering on time dimensions
- Query caching with TTL
- Pagination support

### 5. REST API Routes (`backend/app/api/v1/semantic.py`)

API endpoints for semantic layer:

| Endpoint | Method | Permission | Description |
|----------|--------|------------|-------------|
| `/api/v1/semantic/models` | GET | `semantic:view` | List all models |
| `/api/v1/semantic/models` | POST | `semantic:create` | Create model |
| `/api/v1/semantic/models/{id}` | GET | `semantic:view` | Get model details |
| `/api/v1/semantic/models/{id}` | PUT | `semantic:edit` | Update model |
| `/api/v1/semantic/models/{id}` | DELETE | `semantic:delete` | Delete model |
| `/api/v1/semantic/models/{id}/dimensions` | GET | `semantic:view` | List dimensions |
| `/api/v1/semantic/models/{id}/dimensions` | POST | `semantic:create` | Add dimension |
| `/api/v1/semantic/models/{id}/measures` | GET | `semantic:view` | List measures |
| `/api/v1/semantic/models/{id}/measures` | POST | `semantic:create` | Add measure |
| `/api/v1/semantic/dimensions/{id}` | GET/PUT/DELETE | various | Dimension CRUD |
| `/api/v1/semantic/measures/{id}` | GET/PUT/DELETE | various | Measure CRUD |
| `/api/v1/semantic/relationships` | GET/POST | various | Relationship management |
| `/api/v1/semantic/query` | POST | `analytics:query` | Execute semantic query |
| `/api/v1/semantic/explore` | GET | `semantic:view` | Get all metadata |
| `/api/v1/semantic/cache/clear` | POST | `semantic:admin` | Clear query cache |

## API Examples

### Create Semantic Model

```bash
POST /api/v1/semantic/models
{
    "name": "orders",
    "dbt_model": "mart_orders",
    "label": "Sales Orders",
    "description": "Order fact table",
    "model_type": "fact",
    "cache_enabled": true,
    "cache_ttl_seconds": 3600
}
```

### Add Dimension

```bash
POST /api/v1/semantic/models/{model_id}/dimensions
{
    "name": "order_date",
    "expression": "order_created_at",
    "label": "Order Date",
    "type": "temporal",
    "data_type": "Date",
    "is_filterable": true,
    "is_groupable": true
}
```

### Add Measure

```bash
POST /api/v1/semantic/models/{model_id}/measures
{
    "name": "total_revenue",
    "aggregation": "sum",
    "expression": "order_total",
    "label": "Total Revenue",
    "format": "currency",
    "format_string": "$#,##0.00"
}
```

### Execute Semantic Query

```bash
POST /api/v1/semantic/query
{
    "dimensions": ["order_date", "customer_region"],
    "measures": ["total_revenue", "order_count"],
    "filters": [
        {
            "field": "order_status",
            "operator": "eq",
            "value": "completed"
        }
    ],
    "order_by": [
        {"field": "total_revenue", "order": "desc"}
    ],
    "time_dimension": "order_date",
    "date_from": "2024-01-01",
    "date_to": "2024-12-31",
    "limit": 1000
}
```

**Response:**
```json
{
    "columns": ["order_date", "customer_region", "total_revenue", "order_count"],
    "rows": [
        ["2024-01-15", "North America", 125000.00, 342],
        ["2024-01-15", "Europe", 98000.00, 287]
    ],
    "row_count": 2,
    "execution_time_ms": 45.2,
    "from_cache": false,
    "query": "SELECT ... (generated SQL)"
}
```

## Architecture Decisions

### 1. Query Generation

The semantic service generates ClickHouse SQL from semantic definitions:

```python
# Dimension -> SQL expression
dimension.expression  # e.g., "order_created_at"
# Becomes: toDate(order_created_at) AS order_date

# Measure -> Aggregation
measure.aggregation, measure.expression  # sum, order_total
# Becomes: sum(order_total) AS total_revenue
```

### 2. Multi-Model Joins

When a query spans multiple models, the service:

1. Identifies required models from dimensions/measures
2. Finds relationships between models
3. Builds JOIN clauses using relationship definitions
4. Ensures proper join order (fact tables first)

### 3. Query Caching

- Caches are tenant-isolated
- TTL configurable per model
- Cache key: hash(query + filters + params)
- Clear cache via API or programmatically

### 4. Tenant Isolation

All queries include tenant filtering:
- Models filtered by `tenant_id`
- ClickHouse database per tenant (`tenant_{id}`)
- No cross-tenant data access possible

## Dependencies

- **SQLAlchemy**: ORM for semantic metadata
- **clickhouse-connect**: ClickHouse Python client
- **Pydantic**: Request/response validation
- **Flask**: REST API framework

## Testing

Unit tests in `backend/tests/unit/test_semantic_layer.py`:

- Schema validation tests
- Enum value tests
- Model serialization tests
- Filter expression tests
- Mock client tests

## Files Created

| File | Purpose |
|------|---------|
| `backend/app/models/semantic.py` | SQLAlchemy models |
| `backend/app/services/clickhouse_client.py` | ClickHouse client |
| `backend/app/schemas/semantic_schemas.py` | Pydantic schemas |
| `backend/app/services/semantic_service.py` | Business logic |
| `backend/app/api/v1/semantic.py` | REST API routes |
| `backend/tests/unit/test_semantic_layer.py` | Unit tests |

## Files Modified

| File | Changes |
|------|---------|
| `backend/app/api/v1/__init__.py` | Register semantic blueprint |
| `backend/app/models/__init__.py` | Export semantic models |
| `backend/app/services/__init__.py` | Export semantic service |
| `backend/app/schemas/__init__.py` | Export semantic schemas |

## Next Steps

1. **Database Migration**: Create Alembic migration for semantic tables
2. **Integration Tests**: Test full API flow with database
3. **ClickHouse Setup**: Configure tenant-isolated ClickHouse databases
4. **dbt Integration**: Link semantic models to generated dbt models
5. **Dashboard Integration**: Connect query API to dashboard visualizations

## Compliance

✅ **Template Engine Rule**: No arbitrary code generation  
✅ **Tenant Isolation**: All operations scoped to tenant  
✅ **Security**: Permission decorators on all endpoints  
✅ **API Standards**: RESTful design, Pydantic validation  
