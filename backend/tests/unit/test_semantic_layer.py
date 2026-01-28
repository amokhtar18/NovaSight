"""
Unit Tests for NovaSight Semantic Layer
========================================

Tests for semantic models, dimensions, measures, relationships,
and query execution.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime

from app.models.semantic import (
    SemanticModel,
    Dimension,
    Measure,
    Relationship,
    DimensionType,
    AggregationType,
    ModelType,
    RelationshipType,
    JoinType,
)
from app.schemas.semantic_schemas import (
    SemanticModelCreateSchema,
    SemanticModelUpdateSchema,
    DimensionCreateSchema,
    MeasureCreateSchema,
    RelationshipCreateSchema,
    SemanticQuerySchema,
    FilterSchema,
    OrderBySchema,
    DimensionTypeEnum,
    AggregationTypeEnum,
    ModelTypeEnum,
    FilterOperatorEnum,
    SortOrderEnum,
)
from app.services.clickhouse_client import (
    QueryResult,
    MockClickHouseClient,
)


class TestSemanticModelSchemas:
    """Tests for semantic model Pydantic schemas."""
    
    def test_semantic_model_create_schema_valid(self):
        """Test valid semantic model creation."""
        data = SemanticModelCreateSchema(
            name="sales_orders",
            dbt_model="mart_sales_orders",
            label="Sales Orders",
            description="Sales order fact table",
            model_type=ModelTypeEnum.FACT,
            cache_enabled=True,
            cache_ttl_seconds=3600,
            tags=["sales", "orders"],
        )
        
        assert data.name == "sales_orders"
        assert data.dbt_model == "mart_sales_orders"
        assert data.model_type == ModelTypeEnum.FACT
        assert data.cache_ttl_seconds == 3600
    
    def test_semantic_model_create_schema_minimal(self):
        """Test minimal semantic model creation."""
        data = SemanticModelCreateSchema(
            name="customers",
            dbt_model="dim_customers",
        )
        
        assert data.name == "customers"
        assert data.model_type is None  # Will use default
        assert data.cache_enabled is None
    
    def test_semantic_model_name_validation(self):
        """Test name must be valid identifier."""
        with pytest.raises(ValueError):
            SemanticModelCreateSchema(
                name="sales orders",  # Invalid: contains space
                dbt_model="mart_sales",
            )
        
        with pytest.raises(ValueError):
            SemanticModelCreateSchema(
                name="123_sales",  # Invalid: starts with number
                dbt_model="mart_sales",
            )
    
    def test_semantic_model_update_schema(self):
        """Test model update schema."""
        data = SemanticModelUpdateSchema(
            label="Updated Label",
            is_active=False,
        )
        
        assert data.label == "Updated Label"
        assert data.is_active is False
        assert data.description is None


class TestDimensionSchemas:
    """Tests for dimension Pydantic schemas."""
    
    def test_dimension_create_schema_valid(self):
        """Test valid dimension creation."""
        data = DimensionCreateSchema(
            name="order_date",
            expression="order_created_at",
            label="Order Date",
            type=DimensionTypeEnum.TEMPORAL,
            data_type="Date",
            is_filterable=True,
            is_groupable=True,
        )
        
        assert data.name == "order_date"
        assert data.type == DimensionTypeEnum.TEMPORAL
        assert data.is_filterable is True
    
    def test_dimension_create_primary_key(self):
        """Test primary key dimension."""
        data = DimensionCreateSchema(
            name="customer_id",
            expression="customer_id",
            is_primary_key=True,
            is_hidden=True,  # PKs often hidden
        )
        
        assert data.is_primary_key is True
        assert data.is_hidden is True
    
    def test_dimension_name_validation(self):
        """Test dimension name validation."""
        with pytest.raises(ValueError):
            DimensionCreateSchema(
                name="order date",  # Invalid: contains space
                expression="order_date",
            )


class TestMeasureSchemas:
    """Tests for measure Pydantic schemas."""
    
    def test_measure_create_schema_valid(self):
        """Test valid measure creation."""
        data = MeasureCreateSchema(
            name="total_revenue",
            aggregation=AggregationTypeEnum.SUM,
            expression="order_total",
            label="Total Revenue",
            format="currency",
            format_string="$#,##0.00",
            decimal_places=2,
        )
        
        assert data.name == "total_revenue"
        assert data.aggregation == AggregationTypeEnum.SUM
        assert data.format == "currency"
    
    def test_measure_count_distinct(self):
        """Test count distinct measure."""
        data = MeasureCreateSchema(
            name="unique_customers",
            aggregation=AggregationTypeEnum.COUNT_DISTINCT,
            expression="customer_id",
            label="Unique Customers",
        )
        
        assert data.aggregation == AggregationTypeEnum.COUNT_DISTINCT
    
    def test_measure_derived_expression(self):
        """Test derived measure with complex expression."""
        data = MeasureCreateSchema(
            name="avg_order_value",
            aggregation=AggregationTypeEnum.RAW,
            expression="sum(order_total) / count(order_id)",
            label="Average Order Value",
            is_additive=False,  # Can't sum averages
        )
        
        assert data.is_additive is False


class TestRelationshipSchemas:
    """Tests for relationship Pydantic schemas."""
    
    def test_relationship_create_schema_valid(self):
        """Test valid relationship creation."""
        from_id = str(uuid4())
        to_id = str(uuid4())
        
        data = RelationshipCreateSchema(
            from_model_id=from_id,
            to_model_id=to_id,
            from_column="customer_id",
            to_column="id",
            relationship_type="many_to_one",
            join_type="LEFT",
        )
        
        assert data.from_column == "customer_id"
        assert data.to_column == "id"
        assert data.relationship_type == "many_to_one"


class TestSemanticQuerySchemas:
    """Tests for semantic query schemas."""
    
    def test_query_schema_valid(self):
        """Test valid query schema."""
        data = SemanticQuerySchema(
            dimensions=["order_date", "customer_name"],
            measures=["total_revenue", "order_count"],
            limit=1000,
        )
        
        assert len(data.dimensions) == 2
        assert len(data.measures) == 2
        assert data.limit == 1000
    
    def test_query_schema_with_filters(self):
        """Test query with filters."""
        data = SemanticQuerySchema(
            measures=["total_revenue"],
            filters=[
                FilterSchema(
                    field="order_status",
                    operator=FilterOperatorEnum.EQ,
                    value="completed",
                ),
                FilterSchema(
                    field="order_total",
                    operator=FilterOperatorEnum.GT,
                    value=100,
                ),
            ],
        )
        
        assert len(data.filters) == 2
        assert data.filters[0].operator == FilterOperatorEnum.EQ
    
    def test_query_schema_with_ordering(self):
        """Test query with ordering."""
        data = SemanticQuerySchema(
            measures=["total_revenue"],
            order_by=[
                OrderBySchema(
                    field="total_revenue",
                    order=SortOrderEnum.DESC,
                ),
            ],
        )
        
        assert data.order_by[0].order == SortOrderEnum.DESC
    
    def test_query_schema_with_date_range(self):
        """Test query with date range."""
        data = SemanticQuerySchema(
            dimensions=["order_date"],
            measures=["total_revenue"],
            time_dimension="order_date",
            date_from="2024-01-01",
            date_to="2024-12-31",
        )
        
        assert data.time_dimension == "order_date"
        assert data.date_from == "2024-01-01"
    
    def test_query_schema_limit_validation(self):
        """Test query limit validation."""
        # Valid limit
        data = SemanticQuerySchema(
            measures=["total_revenue"],
            limit=50000,
        )
        assert data.limit == 50000
        
        # Default limit
        data = SemanticQuerySchema(
            measures=["total_revenue"],
        )
        assert data.limit == 1000


class TestMockClickHouseClient:
    """Tests for mock ClickHouse client."""
    
    def test_mock_client_execute(self):
        """Test mock client execute."""
        client = MockClickHouseClient()
        
        result = client.execute("SELECT 1")
        
        assert isinstance(result, QueryResult)
        assert result.columns == []
        assert result.rows == []
    
    def test_mock_client_table_exists(self):
        """Test mock client table exists."""
        client = MockClickHouseClient()
        
        assert client.table_exists("any_table") is True
    
    def test_mock_client_get_schema(self):
        """Test mock client get schema."""
        client = MockClickHouseClient()
        
        schema = client.get_table_schema("any_table")
        
        assert schema == {}


class TestQueryResult:
    """Tests for QueryResult dataclass."""
    
    def test_query_result_to_dict(self):
        """Test QueryResult to dict."""
        result = QueryResult(
            columns=["name", "count"],
            rows=[["Alice", 10], ["Bob", 20]],
            row_count=2,
            execution_time_ms=50.5,
        )
        
        data = result.to_dict()
        
        assert data["columns"] == ["name", "count"]
        assert data["row_count"] == 2
        assert data["execution_time_ms"] == 50.5
    
    def test_query_result_to_records(self):
        """Test QueryResult to records."""
        result = QueryResult(
            columns=["name", "count"],
            rows=[["Alice", 10], ["Bob", 20]],
            row_count=2,
        )
        
        records = result.to_records()
        
        assert len(records) == 2
        assert records[0] == {"name": "Alice", "count": 10}
        assert records[1] == {"name": "Bob", "count": 20}


class TestSemanticModels:
    """Tests for SQLAlchemy semantic models."""
    
    def test_semantic_model_to_dict(self, db_session):
        """Test SemanticModel to_dict."""
        tenant_id = str(uuid4())
        
        model = SemanticModel(
            tenant_id=tenant_id,
            name="orders",
            dbt_model="mart_orders",
            label="Orders",
            model_type=ModelType.FACT,
            cache_enabled=True,
        )
        
        data = model.to_dict()
        
        assert data["name"] == "orders"
        assert data["model_type"] == "fact"
        assert data["cache_enabled"] is True
    
    def test_dimension_to_dict(self, db_session):
        """Test Dimension to_dict."""
        model_id = uuid4()
        
        dim = Dimension(
            model_id=model_id,
            name="customer_name",
            expression="customer_name",
            label="Customer Name",
            type=DimensionType.CATEGORICAL,
            is_filterable=True,
        )
        
        data = dim.to_dict()
        
        assert data["name"] == "customer_name"
        assert data["type"] == "categorical"
        assert data["is_filterable"] is True
    
    def test_measure_to_dict(self, db_session):
        """Test Measure to_dict."""
        model_id = uuid4()
        
        measure = Measure(
            model_id=model_id,
            name="total_sales",
            aggregation=AggregationType.SUM,
            expression="order_total",
            label="Total Sales",
            format="currency",
        )
        
        data = measure.to_dict()
        
        assert data["name"] == "total_sales"
        assert data["aggregation"] == "sum"
        assert data["format"] == "currency"
    
    def test_relationship_to_dict(self, db_session):
        """Test Relationship to_dict."""
        tenant_id = str(uuid4())
        from_id = uuid4()
        to_id = uuid4()
        
        rel = Relationship(
            tenant_id=tenant_id,
            from_model_id=from_id,
            to_model_id=to_id,
            from_column="customer_id",
            to_column="id",
            relationship_type=RelationshipType.MANY_TO_ONE,
            join_type=JoinType.LEFT,
        )
        
        data = rel.to_dict()
        
        assert data["from_column"] == "customer_id"
        assert data["to_column"] == "id"
        assert data["relationship_type"] == "many_to_one"
        assert data["join_type"] == "LEFT"


class TestFilterExpressions:
    """Tests for filter expression building."""
    
    def test_equals_filter(self):
        """Test equals filter."""
        filter_spec = FilterSchema(
            field="status",
            operator=FilterOperatorEnum.EQ,
            value="active",
        )
        
        # This would be tested via SemanticService._build_filter_expression
        assert filter_spec.operator == FilterOperatorEnum.EQ
        assert filter_spec.value == "active"
    
    def test_in_filter(self):
        """Test IN filter."""
        filter_spec = FilterSchema(
            field="region",
            operator=FilterOperatorEnum.IN,
            value=["US", "CA", "MX"],
        )
        
        assert filter_spec.operator == FilterOperatorEnum.IN
        assert isinstance(filter_spec.value, list)
    
    def test_between_filter(self):
        """Test BETWEEN filter."""
        filter_spec = FilterSchema(
            field="order_total",
            operator=FilterOperatorEnum.BETWEEN,
            value=[100, 1000],
        )
        
        assert filter_spec.operator == FilterOperatorEnum.BETWEEN
        assert len(filter_spec.value) == 2


class TestSemanticModelEnums:
    """Tests for semantic layer enums."""
    
    def test_dimension_types(self):
        """Test dimension type enum values."""
        assert DimensionType.CATEGORICAL.value == "categorical"
        assert DimensionType.TEMPORAL.value == "temporal"
        assert DimensionType.NUMERIC.value == "numeric"
        assert DimensionType.HIERARCHICAL.value == "hierarchical"
    
    def test_aggregation_types(self):
        """Test aggregation type enum values."""
        assert AggregationType.SUM.value == "sum"
        assert AggregationType.COUNT.value == "count"
        assert AggregationType.AVG.value == "avg"
        assert AggregationType.MIN.value == "min"
        assert AggregationType.MAX.value == "max"
        assert AggregationType.COUNT_DISTINCT.value == "count_distinct"
    
    def test_model_types(self):
        """Test model type enum values."""
        assert ModelType.FACT.value == "fact"
        assert ModelType.DIMENSION.value == "dimension"
        assert ModelType.AGGREGATE.value == "aggregate"
    
    def test_relationship_types(self):
        """Test relationship type enum values."""
        assert RelationshipType.ONE_TO_ONE.value == "one_to_one"
        assert RelationshipType.ONE_TO_MANY.value == "one_to_many"
        assert RelationshipType.MANY_TO_ONE.value == "many_to_one"
        assert RelationshipType.MANY_TO_MANY.value == "many_to_many"


@pytest.fixture
def db_session():
    """Mock database session for tests."""
    session = MagicMock()
    return session


@pytest.fixture
def sample_semantic_model():
    """Create sample semantic model for tests."""
    tenant_id = str(uuid4())
    model = SemanticModel(
        id=uuid4(),
        tenant_id=tenant_id,
        name="orders",
        dbt_model="mart_orders",
        label="Orders",
        model_type=ModelType.FACT,
        cache_enabled=True,
        cache_ttl_seconds=3600,
        created_at=datetime.utcnow(),
    )
    return model


@pytest.fixture
def sample_dimensions(sample_semantic_model):
    """Create sample dimensions for tests."""
    return [
        Dimension(
            id=uuid4(),
            model_id=sample_semantic_model.id,
            name="order_date",
            expression="order_created_at",
            label="Order Date",
            type=DimensionType.TEMPORAL,
            data_type="Date",
            is_filterable=True,
            is_groupable=True,
        ),
        Dimension(
            id=uuid4(),
            model_id=sample_semantic_model.id,
            name="customer_name",
            expression="customer_name",
            label="Customer Name",
            type=DimensionType.CATEGORICAL,
            is_filterable=True,
            is_groupable=True,
        ),
    ]


@pytest.fixture
def sample_measures(sample_semantic_model):
    """Create sample measures for tests."""
    return [
        Measure(
            id=uuid4(),
            model_id=sample_semantic_model.id,
            name="total_revenue",
            aggregation=AggregationType.SUM,
            expression="order_total",
            label="Total Revenue",
            format="currency",
            format_string="$#,##0.00",
        ),
        Measure(
            id=uuid4(),
            model_id=sample_semantic_model.id,
            name="order_count",
            aggregation=AggregationType.COUNT,
            expression="order_id",
            label="Order Count",
            format="number",
        ),
    ]
