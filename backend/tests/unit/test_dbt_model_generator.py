"""
Unit Tests for dbt Model Generator
===================================

Tests for the DbtModelGenerator service.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from app.models.data_source import (
    DataSourceColumn,
    DataSourceTable,
    DataSourceSchema,
)
from app.services.dbt_model_generator import (
    DbtModelGenerator,
    get_dbt_model_generator,
    ModelGenerationError,
    DbtModelGeneratorError,
)


class TestDataSourceModels:
    """Tests for DataSourceColumn, DataSourceTable, and DataSourceSchema."""
    
    def test_data_source_column_creation(self):
        """Test basic column creation."""
        col = DataSourceColumn(
            name="user_id",
            source_name="UserID",
            type="integer",
            nullable=False,
            primary_key=True,
        )
        
        assert col.name == "user_id"
        assert col.source_name == "UserID"
        assert col.type == "integer"
        assert col.nullable is False
        assert col.primary_key is True
    
    def test_data_source_column_to_dict(self):
        """Test column serialization."""
        col = DataSourceColumn(
            name="email",
            source_name="Email",
            type="varchar",
            description="User email address",
        )
        
        data = col.to_dict()
        
        assert data["name"] == "email"
        assert data["source_name"] == "Email"
        assert data["type"] == "varchar"
        assert data["description"] == "User email address"
    
    def test_data_source_column_from_dict(self):
        """Test column deserialization."""
        data = {
            "name": "created_at",
            "source_name": "CreatedAt",
            "type": "timestamp",
            "nullable": False,
        }
        
        col = DataSourceColumn.from_dict(data)
        
        assert col.name == "created_at"
        assert col.type == "timestamp"
        assert col.nullable is False
    
    def test_data_source_table_creation(self):
        """Test basic table creation."""
        columns = [
            DataSourceColumn(name="id", source_name="ID", type="integer", primary_key=True),
            DataSourceColumn(name="name", source_name="Name", type="varchar"),
        ]
        
        table = DataSourceTable(
            name="users",
            source_name="Users",
            schema_name="public",
            columns=columns,
        )
        
        assert table.name == "users"
        assert table.source_name == "Users"
        assert len(table.columns) == 2
        assert table.primary_key_columns == ["id"]
    
    def test_data_source_table_get_column(self):
        """Test column lookup."""
        columns = [
            DataSourceColumn(name="id", source_name="ID", type="integer"),
            DataSourceColumn(name="email", source_name="Email", type="varchar"),
        ]
        
        table = DataSourceTable(
            name="users",
            source_name="Users",
            columns=columns,
        )
        
        # Find by name
        col = table.get_column("email")
        assert col is not None
        assert col.name == "email"
        
        # Find by source_name
        col = table.get_column("ID")
        assert col is not None
        assert col.source_name == "ID"
        
        # Not found
        col = table.get_column("nonexistent")
        assert col is None
    
    def test_data_source_schema_creation(self):
        """Test schema creation."""
        tables = [
            DataSourceTable(name="users", source_name="Users", columns=[]),
            DataSourceTable(name="orders", source_name="Orders", columns=[]),
        ]
        
        schema = DataSourceSchema(
            source_name="salesforce",
            database="sf_db",
            tables=tables,
        )
        
        assert schema.source_name == "salesforce"
        assert schema.database == "sf_db"
        assert len(schema.tables) == 2
    
    def test_data_source_schema_get_table(self):
        """Test table lookup in schema."""
        tables = [
            DataSourceTable(name="users", source_name="Users", columns=[]),
        ]
        
        schema = DataSourceSchema(
            source_name="test",
            database="test_db",
            tables=tables,
        )
        
        assert schema.has_table("users") is True
        assert schema.has_table("orders") is False


class TestDbtModelGenerator:
    """Tests for DbtModelGenerator service."""
    
    @pytest.fixture
    def temp_dbt_path(self):
        """Create a temporary directory for dbt files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_template_engine(self):
        """Create a mock template engine."""
        engine = Mock()
        engine.render = Mock(return_value="-- Generated SQL")
        return engine
    
    @pytest.fixture
    def generator(self, mock_template_engine, temp_dbt_path):
        """Create a generator instance with mocks."""
        return DbtModelGenerator(
            template_eng=mock_template_engine,
            dbt_path=temp_dbt_path,
        )
    
    @pytest.fixture
    def sample_table(self):
        """Create a sample table definition."""
        return DataSourceTable(
            name="users",
            source_name="Users",
            schema_name="public",
            columns=[
                DataSourceColumn(
                    name="id",
                    source_name="ID",
                    type="integer",
                    primary_key=True,
                    nullable=False,
                ),
                DataSourceColumn(
                    name="email",
                    source_name="Email",
                    type="varchar",
                    nullable=False,
                ),
                DataSourceColumn(
                    name="created_at",
                    source_name="CreatedAt",
                    type="timestamp",
                    nullable=False,
                ),
            ],
            description="User accounts table",
        )
    
    def test_generator_initialization(self, mock_template_engine, temp_dbt_path):
        """Test generator initialization."""
        generator = DbtModelGenerator(
            template_eng=mock_template_engine,
            dbt_path=temp_dbt_path,
        )
        
        assert generator.template_engine == mock_template_engine
        assert str(generator.dbt_path) == temp_dbt_path
    
    def test_type_mapping_common_types(self, generator):
        """Test type mapping for common database types."""
        assert generator._map_type("varchar") == "String"
        assert generator._map_type("text") == "String"
        assert generator._map_type("integer") == "Int32"
        assert generator._map_type("bigint") == "Int64"
        assert generator._map_type("boolean") == "UInt8"
        assert generator._map_type("timestamp") == "DateTime"
        assert generator._map_type("date") == "Date"
        assert generator._map_type("uuid") == "UUID"
        assert generator._map_type("json") == "String"
        assert generator._map_type("jsonb") == "String"
    
    def test_type_mapping_unknown_type(self, generator):
        """Test type mapping defaults to String for unknown types."""
        assert generator._map_type("custom_type") == "String"
        assert generator._map_type("") == "String"
    
    def test_type_mapping_with_size(self, generator):
        """Test type mapping handles types with size specifications."""
        assert generator._map_type("varchar(255)") == "String"
        assert generator._map_type("numeric(10,2)") == "Decimal64(2)"
        assert generator._map_type("decimal(18,4)") == "Decimal64(4)"
    
    def test_sanitize_identifier_basic(self, generator):
        """Test identifier sanitization."""
        assert generator._sanitize_identifier("UserName") == "user_name"
        assert generator._sanitize_identifier("already_snake") == "already_snake"
        assert generator._sanitize_identifier("CamelCaseWord") == "camel_case_word"
    
    def test_sanitize_identifier_special_chars(self, generator):
        """Test identifier sanitization removes special characters."""
        assert generator._sanitize_identifier("user-name") == "user_name"
        assert generator._sanitize_identifier("user.name") == "username"
        assert generator._sanitize_identifier("user@email") == "useremail"
    
    def test_sanitize_identifier_starts_with_number(self, generator):
        """Test identifier sanitization handles names starting with numbers."""
        assert generator._sanitize_identifier("123_column") == "col_123_column"
        assert generator._sanitize_identifier("1st_place") == "col_1st_place"
    
    def test_generate_column_tests_primary_key(self, generator):
        """Test test generation for primary key columns."""
        col = DataSourceColumn(
            name="id",
            source_name="ID",
            type="integer",
            primary_key=True,
        )
        
        tests = generator._generate_column_tests(col, "id")
        
        assert "unique" in tests
        assert "not_null" in tests
    
    def test_generate_column_tests_non_nullable(self, generator):
        """Test test generation for non-nullable columns."""
        col = DataSourceColumn(
            name="status",
            source_name="Status",
            type="varchar",
            nullable=False,
        )
        
        tests = generator._generate_column_tests(col, "status")
        
        assert "not_null" in tests
    
    def test_generate_staging_model(self, generator, sample_table, temp_dbt_path):
        """Test staging model generation."""
        result = generator.generate_staging_model(
            table=sample_table,
            source_name="salesforce",
        )
        
        assert "model_path" in result
        assert "schema_path" in result
        assert "model_name" in result
        assert result["model_name"] == "stg_salesforce__users"
        
        # Verify files were created
        model_path = Path(result["model_path"])
        schema_path = Path(result["schema_path"])
        
        assert model_path.exists()
        assert schema_path.exists()
    
    def test_generate_staging_model_with_options(self, generator, sample_table):
        """Test staging model generation with custom options."""
        result = generator.generate_staging_model(
            table=sample_table,
            source_name="postgres",
            options={
                "materialization": "table",
                "include_metadata": True,
                "generate_tests": False,
            },
        )
        
        assert result["model_name"] == "stg_postgres__users"
        
        # Verify template was called with correct parameters
        calls = generator.template_engine.render.call_args_list
        assert len(calls) >= 1
    
    def test_generate_source_yaml(self, generator, sample_table, temp_dbt_path):
        """Test sources.yml generation."""
        result = generator.generate_source_yaml(
            source_name="salesforce",
            database="sf_production",
            tables=[sample_table],
        )
        
        assert result is not None
        assert Path(result).exists()
        assert "sources.yml" in result
    
    def test_generate_source_yaml_with_options(self, generator, sample_table):
        """Test sources.yml generation with custom options."""
        result = generator.generate_source_yaml(
            source_name="postgres",
            database="analytics",
            tables=[sample_table],
            options={
                "schema": "public",
                "freshness_warn_hours": 12,
                "freshness_error_hours": 24,
                "loader": "Custom Loader",
            },
        )
        
        assert result is not None
    
    def test_generate_staging_layer(self, generator, temp_dbt_path):
        """Test complete staging layer generation."""
        schema = DataSourceSchema(
            source_name="salesforce",
            database="sf_db",
            tables=[
                DataSourceTable(
                    name="accounts",
                    source_name="Account",
                    columns=[
                        DataSourceColumn(name="id", source_name="Id", type="varchar", primary_key=True),
                        DataSourceColumn(name="name", source_name="Name", type="varchar"),
                    ],
                ),
                DataSourceTable(
                    name="contacts",
                    source_name="Contact",
                    columns=[
                        DataSourceColumn(name="id", source_name="Id", type="varchar", primary_key=True),
                        DataSourceColumn(name="email", source_name="Email", type="varchar"),
                    ],
                ),
            ],
        )
        
        result = generator.generate_staging_layer(schema)
        
        assert result["sources_file"] is not None
        assert len(result["models"]) == 2
        assert len(result["errors"]) == 0
    
    def test_generate_intermediate_model(self, generator, temp_dbt_path):
        """Test intermediate model generation."""
        result = generator.generate_intermediate_model(
            name="int_orders_enriched",
            description="Orders with customer details",
            source_models=[
                {"name": "stg_salesforce__orders", "alias": "orders"},
                {"name": "stg_salesforce__accounts", "alias": "accounts"},
            ],
            columns=[
                {"name": "order_id", "source_alias": "orders", "source_column": "id"},
                {"name": "order_date", "source_alias": "orders", "source_column": "created_at"},
                {"name": "customer_name", "source_alias": "accounts", "source_column": "name"},
            ],
            joins=[
                {
                    "model": "stg_salesforce__accounts",
                    "model_alias": "accounts",
                    "type": "LEFT",
                    "left_key": "account_id",
                    "right_key": "id",
                },
            ],
        )
        
        assert "model_path" in result
        assert result["model_name"] == "int_orders_enriched"
        assert Path(result["model_path"]).exists()
    
    def test_generate_mart_model(self, generator, temp_dbt_path):
        """Test mart model generation."""
        result = generator.generate_mart_model(
            name="fct_orders",
            description="Order fact table",
            source_models=[
                {"name": "int_orders_enriched"},
            ],
            columns=[
                {"name": "order_id", "source_column": "order_id"},
                {"name": "order_date", "source_column": "order_date"},
                {"name": "total_amount", "expression": "SUM(amount)"},
            ],
            options={
                "materialization": "incremental",
                "unique_key": "order_id",
                "incremental_strategy": "merge",
            },
        )
        
        assert "model_path" in result
        assert result["model_name"] == "fct_orders"
        assert Path(result["model_path"]).exists()
    
    def test_generate_mart_model_dimension(self, generator, temp_dbt_path):
        """Test dimension mart model generation."""
        result = generator.generate_mart_model(
            name="dim_customers",
            description="Customer dimension table",
            source_models=[
                {"name": "stg_salesforce__accounts"},
            ],
            columns=[
                {"name": "customer_id", "source_column": "id"},
                {"name": "customer_name", "source_column": "name"},
            ],
        )
        
        assert result["model_name"] == "dim_customers"
        # Should be in dimensions subdirectory
        assert "dimensions" in result["model_path"]
    
    def test_template_render_error(self, generator, sample_table):
        """Test handling of template rendering errors."""
        generator.template_engine.render.side_effect = Exception("Template error")
        
        with pytest.raises(ModelGenerationError) as exc_info:
            generator.generate_staging_model(sample_table, "test")
        
        assert "Failed to render templates" in str(exc_info.value)


class TestGetDbtModelGenerator:
    """Tests for the get_dbt_model_generator singleton factory."""
    
    def test_get_generator_creates_instance(self):
        """Test that get_dbt_model_generator creates an instance."""
        with patch('app.services.dbt_model_generator.template_engine'):
            generator = get_dbt_model_generator(dbt_path="/tmp/test_dbt")
            assert isinstance(generator, DbtModelGenerator)
    
    def test_get_generator_returns_same_instance(self):
        """Test singleton behavior - returns same instance."""
        with patch('app.services.dbt_model_generator.template_engine'):
            # Reset singleton
            import app.services.dbt_model_generator as dbt_gen_module
            dbt_gen_module._dbt_model_generator = None
            
            generator1 = get_dbt_model_generator()
            generator2 = get_dbt_model_generator()
            
            assert generator1 is generator2


class TestTypeMapping:
    """Comprehensive tests for database type mapping."""
    
    @pytest.fixture
    def generator(self):
        """Create a generator instance with mock template engine."""
        mock_engine = Mock()
        return DbtModelGenerator(template_eng=mock_engine, dbt_path="/tmp/test")
    
    @pytest.mark.parametrize("source_type,expected", [
        # String types
        ("varchar", "String"),
        ("VARCHAR(255)", "String"),
        ("character varying", "String"),
        ("text", "String"),
        ("char(10)", "String"),
        ("nvarchar(max)", "String"),
        
        # Integer types
        ("integer", "Int32"),
        ("int", "Int32"),
        ("bigint", "Int64"),
        ("smallint", "Int16"),
        ("tinyint", "Int8"),
        
        # Float types
        ("real", "Float32"),
        ("float", "Float64"),
        ("double precision", "Float64"),
        
        # Boolean
        ("boolean", "UInt8"),
        ("bool", "UInt8"),
        
        # Date/Time
        ("date", "Date"),
        ("timestamp", "DateTime"),
        ("timestamp with time zone", "DateTime64(3)"),
        ("timestamptz", "DateTime64(3)"),
        
        # JSON
        ("json", "String"),
        ("jsonb", "String"),
        
        # UUID
        ("uuid", "UUID"),
        
        # Unknown
        ("custom_type", "String"),
    ])
    def test_type_mapping(self, generator, source_type, expected):
        """Test various type mappings."""
        result = generator._map_type(source_type)
        assert result == expected


class TestColumnTestGeneration:
    """Tests for automatic test generation."""
    
    @pytest.fixture
    def generator(self):
        """Create a generator instance."""
        mock_engine = Mock()
        return DbtModelGenerator(template_eng=mock_engine, dbt_path="/tmp/test")
    
    def test_id_column_tests(self, generator):
        """Test that 'id' columns get unique and not_null tests."""
        col = DataSourceColumn(name="id", source_name="id", type="integer")
        tests = generator._generate_column_tests(col, "id")
        
        assert "unique" in tests
        assert "not_null" in tests
    
    def test_foreign_key_column_tests(self, generator):
        """Test that foreign key columns get not_null tests."""
        col = DataSourceColumn(name="user_id", source_name="user_id", type="integer", nullable=False)
        tests = generator._generate_column_tests(col, "user_id")
        
        assert "not_null" in tests
    
    def test_timestamp_column_tests(self, generator):
        """Test that timestamp columns get appropriate tests."""
        col = DataSourceColumn(name="created_at", source_name="created_at", type="timestamp")
        tests = generator._generate_column_tests(col, "created_at")
        
        assert "not_null" in tests
