"""
Unit Tests for ClickHouse Type Mapper
======================================

Tests for the ClickHouseTypeMapper service that maps source database
types to ClickHouse types for use in PySpark jobs and data pipelines.
"""

import pytest
from app.domains.datasources.infrastructure.connectors.utils.type_mapping import (
    ClickHouseTypeMapper,
    TypeMapper,
)


class TestClickHouseTypeMapperPostgreSQL:
    """Tests for PostgreSQL to ClickHouse type mapping."""

    def test_varchar_mapping(self):
        assert ClickHouseTypeMapper.map_type("varchar(255)", "postgresql") == "String"
        assert ClickHouseTypeMapper.map_type("varchar", "postgresql") == "String"

    def test_character_varying_mapping(self):
        assert ClickHouseTypeMapper.map_type("character varying", "postgresql") == "String"

    def test_integer_mapping(self):
        assert ClickHouseTypeMapper.map_type("integer", "postgresql") == "Int32"
        assert ClickHouseTypeMapper.map_type("int", "postgresql") == "Int32"
        assert ClickHouseTypeMapper.map_type("int4", "postgresql") == "Int32"

    def test_bigint_mapping(self):
        assert ClickHouseTypeMapper.map_type("bigint", "postgresql") == "Int64"
        assert ClickHouseTypeMapper.map_type("int8", "postgresql") == "Int64"

    def test_smallint_mapping(self):
        assert ClickHouseTypeMapper.map_type("smallint", "postgresql") == "Int16"
        assert ClickHouseTypeMapper.map_type("int2", "postgresql") == "Int16"

    def test_numeric_with_precision(self):
        assert ClickHouseTypeMapper.map_type("numeric(18,4)", "postgresql") == "Decimal64(4)"
        assert ClickHouseTypeMapper.map_type("numeric(8,2)", "postgresql") == "Decimal32(2)"
        assert ClickHouseTypeMapper.map_type("numeric(28,6)", "postgresql") == "Decimal128(6)"
        assert ClickHouseTypeMapper.map_type("numeric(40,8)", "postgresql") == "Decimal256(8)"

    def test_numeric_without_precision(self):
        assert ClickHouseTypeMapper.map_type("numeric", "postgresql") == "Float64"

    def test_decimal_with_precision(self):
        assert ClickHouseTypeMapper.map_type("decimal(10,2)", "postgresql") == "Decimal64(2)"

    def test_float_mapping(self):
        assert ClickHouseTypeMapper.map_type("real", "postgresql") == "Float32"
        assert ClickHouseTypeMapper.map_type("double precision", "postgresql") == "Float64"
        assert ClickHouseTypeMapper.map_type("float8", "postgresql") == "Float64"

    def test_boolean_mapping(self):
        assert ClickHouseTypeMapper.map_type("boolean", "postgresql") == "UInt8"
        assert ClickHouseTypeMapper.map_type("bool", "postgresql") == "UInt8"

    def test_date_time_mapping(self):
        assert ClickHouseTypeMapper.map_type("date", "postgresql") == "Date"
        assert ClickHouseTypeMapper.map_type("timestamp", "postgresql") == "DateTime"
        assert ClickHouseTypeMapper.map_type("timestamp without time zone", "postgresql") == "DateTime"
        assert ClickHouseTypeMapper.map_type("timestamp with time zone", "postgresql") == "DateTime64(3)"
        assert ClickHouseTypeMapper.map_type("timestamptz", "postgresql") == "DateTime64(3)"

    def test_text_mapping(self):
        assert ClickHouseTypeMapper.map_type("text", "postgresql") == "String"

    def test_json_mapping(self):
        assert ClickHouseTypeMapper.map_type("json", "postgresql") == "String"
        assert ClickHouseTypeMapper.map_type("jsonb", "postgresql") == "String"

    def test_uuid_mapping(self):
        assert ClickHouseTypeMapper.map_type("uuid", "postgresql") == "UUID"

    def test_bytea_mapping(self):
        assert ClickHouseTypeMapper.map_type("bytea", "postgresql") == "String"

    def test_inet_mapping(self):
        assert ClickHouseTypeMapper.map_type("inet", "postgresql") == "IPv4"


class TestClickHouseTypeMapperMySQL:
    """Tests for MySQL to ClickHouse type mapping."""

    def test_int_mapping(self):
        assert ClickHouseTypeMapper.map_type("int", "mysql") == "Int32"
        assert ClickHouseTypeMapper.map_type("mediumint", "mysql") == "Int32"

    def test_bigint_mapping(self):
        assert ClickHouseTypeMapper.map_type("bigint", "mysql") == "Int64"

    def test_tinyint_mapping(self):
        assert ClickHouseTypeMapper.map_type("tinyint", "mysql") == "Int8"
        assert ClickHouseTypeMapper.map_type("tinyint(1)", "mysql") == "UInt8"  # MySQL boolean

    def test_varchar_mapping(self):
        assert ClickHouseTypeMapper.map_type("varchar(100)", "mysql") == "String"
        assert ClickHouseTypeMapper.map_type("varchar", "mysql") == "String"

    def test_text_types_mapping(self):
        assert ClickHouseTypeMapper.map_type("text", "mysql") == "String"
        assert ClickHouseTypeMapper.map_type("longtext", "mysql") == "String"
        assert ClickHouseTypeMapper.map_type("mediumtext", "mysql") == "String"
        assert ClickHouseTypeMapper.map_type("tinytext", "mysql") == "String"

    def test_datetime_mapping(self):
        assert ClickHouseTypeMapper.map_type("datetime", "mysql") == "DateTime"
        assert ClickHouseTypeMapper.map_type("timestamp", "mysql") == "DateTime"

    def test_date_mapping(self):
        assert ClickHouseTypeMapper.map_type("date", "mysql") == "Date"

    def test_float_mapping(self):
        assert ClickHouseTypeMapper.map_type("float", "mysql") == "Float32"
        assert ClickHouseTypeMapper.map_type("double", "mysql") == "Float64"

    def test_decimal_mapping(self):
        assert ClickHouseTypeMapper.map_type("decimal(10,2)", "mysql") == "Decimal64(2)"

    def test_json_mapping(self):
        assert ClickHouseTypeMapper.map_type("json", "mysql") == "String"

    def test_enum_mapping(self):
        assert ClickHouseTypeMapper.map_type("enum", "mysql") == "String"

    def test_set_mapping(self):
        assert ClickHouseTypeMapper.map_type("set", "mysql") == "Array(String)"

    def test_year_mapping(self):
        assert ClickHouseTypeMapper.map_type("year", "mysql") == "UInt16"

    def test_blob_types_mapping(self):
        assert ClickHouseTypeMapper.map_type("blob", "mysql") == "String"
        assert ClickHouseTypeMapper.map_type("longblob", "mysql") == "String"


class TestClickHouseTypeMapperOracle:
    """Tests for Oracle to ClickHouse type mapping."""

    def test_varchar2_mapping(self):
        assert ClickHouseTypeMapper.map_type("varchar2(100)", "oracle") == "String"
        assert ClickHouseTypeMapper.map_type("varchar2", "oracle") == "String"
        assert ClickHouseTypeMapper.map_type("nvarchar2", "oracle") == "String"

    def test_number_mapping(self):
        assert ClickHouseTypeMapper.map_type("number", "oracle") == "Float64"
        assert ClickHouseTypeMapper.map_type("number(10,2)", "oracle") == "Decimal64(2)"

    def test_date_mapping(self):
        assert ClickHouseTypeMapper.map_type("date", "oracle") == "DateTime"

    def test_timestamp_mapping(self):
        assert ClickHouseTypeMapper.map_type("timestamp", "oracle") == "DateTime"
        assert ClickHouseTypeMapper.map_type("timestamp with time zone", "oracle") == "DateTime64(3)"
        assert ClickHouseTypeMapper.map_type("timestamp with local time zone", "oracle") == "DateTime64(3)"

    def test_clob_mapping(self):
        assert ClickHouseTypeMapper.map_type("clob", "oracle") == "String"
        assert ClickHouseTypeMapper.map_type("nclob", "oracle") == "String"

    def test_blob_mapping(self):
        assert ClickHouseTypeMapper.map_type("blob", "oracle") == "String"
        assert ClickHouseTypeMapper.map_type("raw", "oracle") == "String"

    def test_float_mapping(self):
        assert ClickHouseTypeMapper.map_type("binary_float", "oracle") == "Float32"
        assert ClickHouseTypeMapper.map_type("binary_double", "oracle") == "Float64"

    def test_interval_mapping(self):
        assert ClickHouseTypeMapper.map_type("interval year to month", "oracle") == "Int32"
        assert ClickHouseTypeMapper.map_type("interval day to second", "oracle") == "Int64"


class TestClickHouseTypeMapperSQLServer:
    """Tests for SQL Server to ClickHouse type mapping."""

    def test_varchar_mapping(self):
        assert ClickHouseTypeMapper.map_type("varchar(255)", "sqlserver") == "String"
        assert ClickHouseTypeMapper.map_type("nvarchar(100)", "sqlserver") == "String"

    def test_integer_mapping(self):
        assert ClickHouseTypeMapper.map_type("int", "sqlserver") == "Int32"
        assert ClickHouseTypeMapper.map_type("bigint", "sqlserver") == "Int64"
        assert ClickHouseTypeMapper.map_type("smallint", "sqlserver") == "Int16"
        assert ClickHouseTypeMapper.map_type("tinyint", "sqlserver") == "UInt8"

    def test_datetime_mapping(self):
        assert ClickHouseTypeMapper.map_type("datetime", "sqlserver") == "DateTime"
        assert ClickHouseTypeMapper.map_type("datetime2", "sqlserver") == "DateTime64(3)"
        assert ClickHouseTypeMapper.map_type("smalldatetime", "sqlserver") == "DateTime"
        assert ClickHouseTypeMapper.map_type("datetimeoffset", "sqlserver") == "DateTime64(3)"

    def test_date_mapping(self):
        assert ClickHouseTypeMapper.map_type("date", "sqlserver") == "Date"

    def test_decimal_mapping(self):
        assert ClickHouseTypeMapper.map_type("decimal(18,4)", "sqlserver") == "Decimal64(4)"
        assert ClickHouseTypeMapper.map_type("numeric(10,2)", "sqlserver") == "Decimal64(2)"

    def test_float_mapping(self):
        assert ClickHouseTypeMapper.map_type("float", "sqlserver") == "Float64"
        assert ClickHouseTypeMapper.map_type("real", "sqlserver") == "Float32"

    def test_bit_mapping(self):
        assert ClickHouseTypeMapper.map_type("bit", "sqlserver") == "UInt8"

    def test_uniqueidentifier_mapping(self):
        assert ClickHouseTypeMapper.map_type("uniqueidentifier", "sqlserver") == "UUID"

    def test_money_mapping(self):
        assert ClickHouseTypeMapper.map_type("money", "sqlserver") == "Decimal64(4)"
        assert ClickHouseTypeMapper.map_type("smallmoney", "sqlserver") == "Decimal64(4)"

    def test_xml_mapping(self):
        assert ClickHouseTypeMapper.map_type("xml", "sqlserver") == "String"

    def test_geography_mapping(self):
        assert ClickHouseTypeMapper.map_type("geography", "sqlserver") == "String"
        assert ClickHouseTypeMapper.map_type("geometry", "sqlserver") == "String"


class TestClickHouseTypeMapperEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_type(self):
        assert ClickHouseTypeMapper.map_type("", "postgresql") == "String"

    def test_none_type(self):
        assert ClickHouseTypeMapper.map_type(None, "postgresql") == "String"

    def test_unknown_type(self):
        assert ClickHouseTypeMapper.map_type("custom_type", "postgresql") == "String"

    def test_case_insensitive(self):
        assert ClickHouseTypeMapper.map_type("VARCHAR(255)", "postgresql") == "String"
        assert ClickHouseTypeMapper.map_type("INTEGER", "postgresql") == "Int32"
        assert ClickHouseTypeMapper.map_type("BIGINT", "mysql") == "Int64"

    def test_whitespace_handling(self):
        assert ClickHouseTypeMapper.map_type("  varchar(255)  ", "postgresql") == "String"
        assert ClickHouseTypeMapper.map_type(" integer ", "postgresql") == "Int32"

    def test_unknown_database(self):
        # Should fall back to normalized type mapping
        assert ClickHouseTypeMapper.map_type("varchar", "unknown_db") == "String"
        assert ClickHouseTypeMapper.map_type("integer", "unknown_db") == "Int32"

    def test_postgres_alias(self):
        assert ClickHouseTypeMapper.map_type("varchar", "postgres") == "String"

    def test_mariadb_alias(self):
        assert ClickHouseTypeMapper.map_type("int", "mariadb") == "Int32"

    def test_mssql_alias(self):
        assert ClickHouseTypeMapper.map_type("int", "mssql") == "Int32"


class TestClickHouseTypeMapperMapColumns:
    """Tests for the map_columns method."""

    def test_map_columns_basic(self):
        columns = [
            {"name": "id", "data_type": "integer", "nullable": False},
            {"name": "name", "data_type": "varchar(255)", "nullable": True},
            {"name": "created_at", "data_type": "timestamp", "nullable": False},
        ]
        
        result = ClickHouseTypeMapper.map_columns(columns, "postgresql")
        
        assert len(result) == 3
        assert result[0]["clickhouse_type"] == "Int32"
        assert result[1]["clickhouse_type"] == "String"
        assert result[2]["clickhouse_type"] == "DateTime"

    def test_map_columns_preserves_original_data(self):
        columns = [
            {"name": "id", "data_type": "integer", "nullable": False, "extra": "value"},
        ]
        
        result = ClickHouseTypeMapper.map_columns(columns, "postgresql")
        
        assert result[0]["name"] == "id"
        assert result[0]["data_type"] == "integer"
        assert result[0]["nullable"] is False
        assert result[0]["extra"] == "value"
        assert result[0]["clickhouse_type"] == "Int32"

    def test_map_columns_empty_list(self):
        result = ClickHouseTypeMapper.map_columns([], "postgresql")
        assert result == []


class TestClickHouseTypeMapperColumnDef:
    """Tests for the get_create_table_column_def method."""

    def test_column_def_nullable(self):
        result = ClickHouseTypeMapper.get_create_table_column_def(
            column_name="email",
            source_type="varchar(255)",
            database="postgresql",
            nullable=True,
        )
        assert result == "`email` Nullable(String)"

    def test_column_def_not_nullable(self):
        result = ClickHouseTypeMapper.get_create_table_column_def(
            column_name="id",
            source_type="integer",
            database="postgresql",
            nullable=False,
        )
        assert result == "`id` Int32"

    def test_column_def_with_default(self):
        result = ClickHouseTypeMapper.get_create_table_column_def(
            column_name="created_at",
            source_type="timestamp",
            database="postgresql",
            nullable=False,
            default_value="now()",
        )
        assert result == "`created_at` DateTime DEFAULT now()"


class TestClickHouseTypeMapperGenerateDDL:
    """Tests for the generate_create_table_ddl method."""

    def test_generate_ddl_basic(self):
        columns = [
            {"name": "id", "data_type": "integer", "nullable": False},
            {"name": "name", "data_type": "varchar(255)", "nullable": True},
        ]
        
        ddl = ClickHouseTypeMapper.generate_create_table_ddl(
            table_name="users",
            columns=columns,
            database="postgresql",
            engine="MergeTree",
            order_by=["id"],
        )
        
        assert "CREATE TABLE IF NOT EXISTS `users`" in ddl
        assert "`id` Int32" in ddl
        assert "`name` Nullable(String)" in ddl
        assert "ENGINE = MergeTree" in ddl
        assert "ORDER BY (`id`)" in ddl

    def test_generate_ddl_with_target_database(self):
        columns = [
            {"name": "id", "data_type": "integer", "nullable": False},
        ]
        
        ddl = ClickHouseTypeMapper.generate_create_table_ddl(
            table_name="users",
            columns=columns,
            database="postgresql",
            engine="MergeTree",
            target_database="tenant_acme",
        )
        
        assert "CREATE TABLE IF NOT EXISTS `tenant_acme`.`users`" in ddl

    def test_generate_ddl_with_partition(self):
        columns = [
            {"name": "id", "data_type": "integer", "nullable": False},
            {"name": "created_at", "data_type": "date", "nullable": False},
        ]
        
        ddl = ClickHouseTypeMapper.generate_create_table_ddl(
            table_name="events",
            columns=columns,
            database="postgresql",
            engine="MergeTree",
            order_by=["id"],
            partition_by="toYYYYMM(created_at)",
        )
        
        assert "PARTITION BY toYYYYMM(created_at)" in ddl

    def test_generate_ddl_default_order_by(self):
        columns = [
            {"name": "data", "data_type": "text", "nullable": True},
        ]
        
        ddl = ClickHouseTypeMapper.generate_create_table_ddl(
            table_name="logs",
            columns=columns,
            database="postgresql",
            engine="MergeTree",
        )
        
        assert "ORDER BY tuple()" in ddl


class TestTypeMapperIntegration:
    """Tests for integration between TypeMapper and ClickHouseTypeMapper."""

    def test_normalize_then_map(self):
        # Normalize PostgreSQL type
        normalized = TypeMapper.normalize_type("character varying", "postgresql")
        assert normalized == "varchar"
        
        # Map normalized type to ClickHouse
        clickhouse_type = ClickHouseTypeMapper.map_type(normalized, "postgresql")
        assert clickhouse_type == "String"

    def test_direct_mapping_vs_normalized(self):
        # Direct mapping
        direct = ClickHouseTypeMapper.map_type("character varying", "postgresql")
        
        # Normalized + mapped
        normalized = TypeMapper.normalize_type("character varying", "postgresql")
        indirect = ClickHouseTypeMapper.map_type(normalized, "postgresql")
        
        # Both should produce the same result
        assert direct == "String"
        assert indirect == "String"
