# 019 - Semantic Layer API

## Metadata

```yaml
prompt_id: "019"
phase: 3
agent: "@dbt"
model: "sonnet 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["018"]
```

## Objective

Implement API for managing the semantic layer (dimensions, measures, relationships).

## Task Description

Create REST endpoints for defining and querying the semantic layer powered by dbt metrics.

## Requirements

### Semantic Layer Models

```python
# backend/app/models/semantic.py
from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from enum import Enum

class DimensionType(str, Enum):
    CATEGORICAL = "categorical"
    TEMPORAL = "temporal"
    NUMERIC = "numeric"

class AggregationType(str, Enum):
    SUM = "sum"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"

class SemanticModel(TenantMixin, TimestampMixin, db.Model):
    """Represents a semantic model (fact/dimension table)."""
    __tablename__ = 'semantic_models'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    dbt_model = db.Column(db.String(100), nullable=False)  # Reference to dbt model
    model_type = db.Column(db.String(20))  # 'fact' or 'dimension'
    
    # Relationships
    dimensions = db.relationship('Dimension', backref='semantic_model', lazy='dynamic')
    measures = db.relationship('Measure', backref='semantic_model', lazy='dynamic')

class Dimension(TenantMixin, TimestampMixin, db.Model):
    """Represents a dimension in the semantic layer."""
    __tablename__ = 'dimensions'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    semantic_model_id = db.Column(UUID(as_uuid=True), db.ForeignKey('semantic_models.id'))
    name = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(100))  # Human-readable name
    description = db.Column(db.Text)
    type = db.Column(db.Enum(DimensionType), default=DimensionType.CATEGORICAL)
    expression = db.Column(db.String(500), nullable=False)  # SQL expression
    is_primary_key = db.Column(db.Boolean, default=False)
    
    # Hierarchy support
    hierarchy_level = db.Column(db.Integer)
    parent_dimension_id = db.Column(UUID(as_uuid=True), db.ForeignKey('dimensions.id'))

class Measure(TenantMixin, TimestampMixin, db.Model):
    """Represents a measure/metric in the semantic layer."""
    __tablename__ = 'measures'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    semantic_model_id = db.Column(UUID(as_uuid=True), db.ForeignKey('semantic_models.id'))
    name = db.Column(db.String(100), nullable=False)
    label = db.Column(db.String(100))
    description = db.Column(db.Text)
    aggregation = db.Column(db.Enum(AggregationType), nullable=False)
    expression = db.Column(db.String(500), nullable=False)  # Column or expression
    format = db.Column(db.String(50))  # number, currency, percent
    
    # Filters
    default_filters = db.Column(JSONB, default=[])

class Relationship(TenantMixin, db.Model):
    """Defines relationships between semantic models."""
    __tablename__ = 'relationships'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    from_model_id = db.Column(UUID(as_uuid=True), db.ForeignKey('semantic_models.id'))
    to_model_id = db.Column(UUID(as_uuid=True), db.ForeignKey('semantic_models.id'))
    from_column = db.Column(db.String(100), nullable=False)
    to_column = db.Column(db.String(100), nullable=False)
    relationship_type = db.Column(db.String(20))  # one-to-one, one-to-many, many-to-many
```

### Semantic Layer API

```python
# backend/app/api/v1/semantic.py
from flask import Blueprint, request, g
from app.schemas.semantic_schemas import (
    SemanticModelSchema,
    DimensionSchema,
    MeasureSchema,
    QuerySchema,
    QueryResultSchema
)
from app.services.semantic_service import SemanticService
from app.middleware.permissions import require_permission

semantic_bp = Blueprint('semantic', __name__)

@semantic_bp.route('/models', methods=['GET'])
@require_permission('semantic.view')
def list_models():
    """List all semantic models for tenant."""
    models = SemanticService.list_models(g.tenant.id)
    return SemanticModelSchema(many=True).dump(models)

@semantic_bp.route('/models', methods=['POST'])
@require_permission('semantic.create')
def create_model():
    """Create a new semantic model."""
    data = SemanticModelSchema().load(request.json)
    model = SemanticService.create_model(g.tenant.id, **data)
    return SemanticModelSchema().dump(model), 201

@semantic_bp.route('/models/<uuid:model_id>/dimensions', methods=['POST'])
@require_permission('semantic.create')
def add_dimension(model_id):
    """Add dimension to semantic model."""
    data = DimensionSchema().load(request.json)
    dimension = SemanticService.add_dimension(model_id, g.tenant.id, **data)
    return DimensionSchema().dump(dimension), 201

@semantic_bp.route('/models/<uuid:model_id>/measures', methods=['POST'])
@require_permission('semantic.create')
def add_measure(model_id):
    """Add measure to semantic model."""
    data = MeasureSchema().load(request.json)
    measure = SemanticService.add_measure(model_id, g.tenant.id, **data)
    return MeasureSchema().dump(measure), 201

@semantic_bp.route('/query', methods=['POST'])
@require_permission('analytics.query')
def execute_query():
    """Execute semantic layer query."""
    data = QuerySchema().load(request.json)
    result = SemanticService.execute_query(
        tenant_id=g.tenant.id,
        dimensions=data['dimensions'],
        measures=data['measures'],
        filters=data.get('filters', []),
        order_by=data.get('order_by'),
        limit=data.get('limit', 1000)
    )
    return QueryResultSchema().dump(result)
```

### Query Execution Service

```python
# backend/app/services/semantic_service.py
from typing import List, Dict, Any
from app.models.semantic import SemanticModel, Dimension, Measure
from app.services.clickhouse import ClickHouseClient

class SemanticService:
    """Service for semantic layer operations."""
    
    @classmethod
    def execute_query(
        cls,
        tenant_id: str,
        dimensions: List[str],
        measures: List[str],
        filters: List[Dict] = None,
        order_by: List[Dict] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """Execute a semantic query and return results."""
        
        # Resolve dimensions and measures
        dim_objects = cls._resolve_dimensions(tenant_id, dimensions)
        measure_objects = cls._resolve_measures(tenant_id, measures)
        
        # Build SQL query
        sql = cls._build_query(
            tenant_id,
            dim_objects,
            measure_objects,
            filters,
            order_by,
            limit
        )
        
        # Execute query
        client = ClickHouseClient(database=f'tenant_{tenant_id}')
        rows = client.execute(sql)
        
        return {
            'columns': [d.name for d in dim_objects] + [m.name for m in measure_objects],
            'rows': rows,
            'row_count': len(rows),
            'query': sql  # For debugging
        }
    
    @classmethod
    def _build_query(
        cls,
        tenant_id: str,
        dimensions: List[Dimension],
        measures: List[Measure],
        filters: List[Dict],
        order_by: List[Dict],
        limit: int
    ) -> str:
        """Build SQL query from semantic definitions."""
        # Complex query builder logic...
        pass
```

## Expected Output

```
backend/app/
├── models/
│   └── semantic.py
├── api/v1/
│   └── semantic.py
├── schemas/
│   └── semantic_schemas.py
└── services/
    └── semantic_service.py
```

## Acceptance Criteria

- [ ] Semantic models CRUD works
- [ ] Dimensions CRUD works
- [ ] Measures CRUD works
- [ ] Query execution returns results
- [ ] Relationships are respected in queries
- [ ] Filters work correctly
- [ ] Aggregations compute correctly
- [ ] Performance acceptable for 1M+ rows

## Reference Documents

- [dbt Model Generator](./018-dbt-model-generator.md)
- [BRD - Epic 3](../../docs/requirements/BRD_Part2.md)
