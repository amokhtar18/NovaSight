"""
NovaSight Data Sources — Type Mapping Utilities
=================================================

Database type mapping to standard types.

Canonical location: ``app.domains.datasources.infrastructure.connectors.utils.type_mapping``
"""

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TypeMapper:
    """
    Map database-specific types to standard types.
    Provides normalised type names for cross-database compatibility.
    """

    NUMERIC_TYPES = {
        "integer", "bigint", "smallint", "decimal", "numeric",
        "float", "double", "real",
    }
    STRING_TYPES = {"varchar", "char", "text", "string"}
    DATE_TYPES = {"date", "time", "timestamp", "datetime"}
    BOOLEAN_TYPES = {"boolean", "bool"}
    BINARY_TYPES = {"binary", "varbinary", "blob", "bytea"}
    JSON_TYPES = {"json", "jsonb"}

    POSTGRESQL_TYPE_MAP = {
        "character varying": "varchar",
        "character": "char",
        "integer": "integer",
        "bigint": "bigint",
        "smallint": "smallint",
        "double precision": "double",
        "real": "float",
        "numeric": "decimal",
        "timestamp without time zone": "timestamp",
        "timestamp with time zone": "timestamptz",
        "time without time zone": "time",
        "time with time zone": "timetz",
        "boolean": "boolean",
        "bytea": "binary",
        "text": "text",
        "json": "json",
        "jsonb": "jsonb",
        "uuid": "uuid",
        "array": "array",
    }

    MYSQL_TYPE_MAP = {
        "int": "integer",
        "tinyint": "smallint",
        "bigint": "bigint",
        "varchar": "varchar",
        "char": "char",
        "text": "text",
        "longtext": "text",
        "mediumtext": "text",
        "tinytext": "text",
        "datetime": "datetime",
        "timestamp": "timestamp",
        "date": "date",
        "time": "time",
        "decimal": "decimal",
        "float": "float",
        "double": "double",
        "boolean": "boolean",
        "blob": "binary",
        "longblob": "binary",
        "mediumblob": "binary",
        "tinyblob": "binary",
        "json": "json",
    }

    # Fixed: Oracle keys are now lowercase (was uppercase — Phase 0.8 bug)
    ORACLE_TYPE_MAP = {
        "varchar2": "varchar",
        "nvarchar2": "varchar",
        "char": "char",
        "nchar": "char",
        "clob": "text",
        "nclob": "text",
        "number": "decimal",
        "binary_float": "float",
        "binary_double": "double",
        "date": "datetime",
        "timestamp": "timestamp",
        "blob": "binary",
        "raw": "binary",
    }

    SQLSERVER_TYPE_MAP = {
        "varchar": "varchar",
        "nvarchar": "varchar",
        "char": "char",
        "nchar": "char",
        "text": "text",
        "ntext": "text",
        "int": "integer",
        "bigint": "bigint",
        "smallint": "smallint",
        "tinyint": "smallint",
        "decimal": "decimal",
        "numeric": "decimal",
        "float": "double",
        "real": "float",
        "datetime": "datetime",
        "datetime2": "datetime",
        "date": "date",
        "time": "time",
        "bit": "boolean",
        "binary": "binary",
        "varbinary": "binary",
    }

    @classmethod
    def normalize_type(cls, db_type: str, database: str = "postgresql") -> str:
        db_type_lower = db_type.lower().strip()

        type_map = {
            "postgresql": cls.POSTGRESQL_TYPE_MAP,
            "mysql": cls.MYSQL_TYPE_MAP,
            "oracle": cls.ORACLE_TYPE_MAP,
            "sqlserver": cls.SQLSERVER_TYPE_MAP,
        }.get(database, {})

        return type_map.get(db_type_lower, db_type_lower)

    @classmethod
    def get_type_category(cls, normalized_type: str) -> str:
        normalized_type = normalized_type.lower()

        if normalized_type in cls.NUMERIC_TYPES:
            return "numeric"
        elif normalized_type in cls.STRING_TYPES:
            return "string"
        elif normalized_type in cls.DATE_TYPES:
            return "date"
        elif normalized_type in cls.BOOLEAN_TYPES:
            return "boolean"
        elif normalized_type in cls.BINARY_TYPES:
            return "binary"
        elif normalized_type in cls.JSON_TYPES:
            return "json"
        else:
            return "other"

    @classmethod
    def is_numeric(cls, normalized_type: str) -> bool:
        return normalized_type.lower() in cls.NUMERIC_TYPES

    @classmethod
    def is_string(cls, normalized_type: str) -> bool:
        return normalized_type.lower() in cls.STRING_TYPES

    @classmethod
    def is_date(cls, normalized_type: str) -> bool:
        return normalized_type.lower() in cls.DATE_TYPES


class ClickHouseTypeMapper:
    """
    Map source database types directly to ClickHouse types.
    
    This class provides comprehensive type mapping from various database
    systems (PostgreSQL, MySQL, Oracle, SQL Server) to ClickHouse types,
    suitable for use in PySpark jobs and data pipeline templates.
    
    Usage:
        mapper = ClickHouseTypeMapper()
        ch_type = mapper.map_type("varchar(255)", "postgresql")
        # Returns: "String"
        
        ch_type = mapper.map_type("numeric(18,4)", "postgresql")
        # Returns: "Decimal128(4)"
    """
    
    # ─── Normalized Type to ClickHouse Mapping ────────────────────────
    # This maps the normalized type names (output of TypeMapper.normalize_type)
    # to ClickHouse native types
    
    NORMALIZED_TO_CLICKHOUSE: Dict[str, str] = {
        # String types
        "varchar": "String",
        "char": "String",
        "text": "String",
        "string": "String",
        "clob": "String",
        "nvarchar": "String",
        "nchar": "String",
        "ntext": "String",
        "longtext": "String",
        "mediumtext": "String",
        "tinytext": "String",
        
        # Integer types
        "integer": "Int32",
        "int": "Int32",
        "int4": "Int32",
        "bigint": "Int64",
        "int8": "Int64",
        "smallint": "Int16",
        "int2": "Int16",
        "tinyint": "Int8",
        "serial": "Int32",
        "bigserial": "Int64",
        "smallserial": "Int16",
        
        # Floating point types
        "real": "Float32",
        "float": "Float64",
        "float4": "Float32",
        "float8": "Float64",
        "double": "Float64",
        "double precision": "Float64",
        "numeric": "Float64",
        "decimal": "Decimal64(4)",  # Default precision
        "money": "Decimal64(4)",
        "number": "Float64",
        
        # Boolean
        "boolean": "UInt8",
        "bool": "UInt8",
        "bit": "UInt8",
        
        # Date/Time types
        "date": "Date",
        "time": "String",  # ClickHouse has no native TIME type
        "timetz": "String",
        "timestamp": "DateTime",
        "timestamptz": "DateTime64(3)",
        "datetime": "DateTime",
        "interval": "Int64",  # Store as seconds
        
        # Binary types
        "binary": "String",
        "varbinary": "String",
        "bytea": "String",
        "blob": "String",
        "raw": "String",
        "longblob": "String",
        "mediumblob": "String",
        "tinyblob": "String",
        
        # JSON types
        "json": "String",
        "jsonb": "String",
        
        # UUID
        "uuid": "UUID",
        
        # Array
        "array": "Array(String)",
        
        # Geographic (store as JSON strings)
        "geometry": "String",
        "geography": "String",
        "point": "String",
        
        # XML
        "xml": "String",
    }
    
    # ─── Direct Source DB Type to ClickHouse Mapping ──────────────────
    # These handle database-specific types that need special translation
    
    POSTGRESQL_TO_CLICKHOUSE: Dict[str, str] = {
        "character varying": "String",
        "character": "String",
        "integer": "Int32",
        "bigint": "Int64",
        "smallint": "Int16",
        "double precision": "Float64",
        "real": "Float32",
        "numeric": "Float64",
        "timestamp without time zone": "DateTime",
        "timestamp with time zone": "DateTime64(3)",
        "time without time zone": "String",
        "time with time zone": "String",
        "boolean": "UInt8",
        "bytea": "String",
        "text": "String",
        "json": "String",
        "jsonb": "String",
        "uuid": "UUID",
        "array": "Array(String)",
        "inet": "IPv4",
        "cidr": "String",
        "macaddr": "String",
        "money": "Decimal64(4)",
        "oid": "UInt32",
        "interval": "Int64",
    }
    
    MYSQL_TO_CLICKHOUSE: Dict[str, str] = {
        "int": "Int32",
        "tinyint": "Int8",
        "smallint": "Int16",
        "mediumint": "Int32",
        "bigint": "Int64",
        "varchar": "String",
        "char": "String",
        "text": "String",
        "longtext": "String",
        "mediumtext": "String",
        "tinytext": "String",
        "datetime": "DateTime",
        "timestamp": "DateTime",
        "date": "Date",
        "time": "String",
        "year": "UInt16",
        "decimal": "Decimal64(4)",
        "float": "Float32",
        "double": "Float64",
        "boolean": "UInt8",
        "tinyint(1)": "UInt8",  # MySQL boolean
        "blob": "String",
        "longblob": "String",
        "mediumblob": "String",
        "tinyblob": "String",
        "binary": "String",
        "varbinary": "String",
        "json": "String",
        "enum": "String",
        "set": "Array(String)",
    }
    
    ORACLE_TO_CLICKHOUSE: Dict[str, str] = {
        "varchar2": "String",
        "nvarchar2": "String",
        "char": "String",
        "nchar": "String",
        "clob": "String",
        "nclob": "String",
        "number": "Float64",
        "binary_float": "Float32",
        "binary_double": "Float64",
        "date": "DateTime",
        "timestamp": "DateTime",
        "timestamp with time zone": "DateTime64(3)",
        "timestamp with local time zone": "DateTime64(3)",
        "blob": "String",
        "raw": "String",
        "long": "String",
        "long raw": "String",
        "rowid": "String",
        "urowid": "String",
        "xmltype": "String",
        "bfile": "String",
        "interval year to month": "Int32",
        "interval day to second": "Int64",
    }
    
    SQLSERVER_TO_CLICKHOUSE: Dict[str, str] = {
        "varchar": "String",
        "nvarchar": "String",
        "char": "String",
        "nchar": "String",
        "text": "String",
        "ntext": "String",
        "int": "Int32",
        "bigint": "Int64",
        "smallint": "Int16",
        "tinyint": "UInt8",
        "decimal": "Decimal64(4)",
        "numeric": "Float64",
        "float": "Float64",
        "real": "Float32",
        "datetime": "DateTime",
        "datetime2": "DateTime64(3)",
        "smalldatetime": "DateTime",
        "date": "Date",
        "time": "String",
        "datetimeoffset": "DateTime64(3)",
        "bit": "UInt8",
        "binary": "String",
        "varbinary": "String",
        "image": "String",
        "money": "Decimal64(4)",
        "smallmoney": "Decimal64(4)",
        "uniqueidentifier": "UUID",
        "xml": "String",
        "sql_variant": "String",
        "hierarchyid": "String",
        "geography": "String",
        "geometry": "String",
    }
    
    @classmethod
    def _get_db_mapping(cls, database: str) -> Dict[str, str]:
        """Get the type mapping for a specific database."""
        mappings = {
            "postgresql": cls.POSTGRESQL_TO_CLICKHOUSE,
            "postgres": cls.POSTGRESQL_TO_CLICKHOUSE,
            "mysql": cls.MYSQL_TO_CLICKHOUSE,
            "mariadb": cls.MYSQL_TO_CLICKHOUSE,
            "oracle": cls.ORACLE_TO_CLICKHOUSE,
            "sqlserver": cls.SQLSERVER_TO_CLICKHOUSE,
            "mssql": cls.SQLSERVER_TO_CLICKHOUSE,
        }
        return mappings.get(database.lower(), cls.NORMALIZED_TO_CLICKHOUSE)
    
    @classmethod
    def _parse_type_precision(cls, type_str: str) -> tuple:
        """
        Parse type string to extract base type, precision, and scale.
        
        Args:
            type_str: Type string like "varchar(255)" or "numeric(18,4)"
            
        Returns:
            Tuple of (base_type, precision, scale)
        """
        import re
        
        type_lower = type_str.lower().strip()
        
        # Match patterns like varchar(255), numeric(18,4), decimal(10)
        match = re.match(r'^(\w+(?:\s+\w+)*)\s*(?:\((\d+)(?:,\s*(\d+))?\))?$', type_lower)
        
        if match:
            base_type = match.group(1).strip()
            precision = int(match.group(2)) if match.group(2) else None
            scale = int(match.group(3)) if match.group(3) else None
            return base_type, precision, scale
        
        return type_lower, None, None
    
    @classmethod
    def _get_decimal_type(cls, precision: Optional[int], scale: Optional[int]) -> str:
        """
        Determine the appropriate ClickHouse Decimal type based on precision.
        
        Args:
            precision: Total number of digits
            scale: Number of decimal places
            
        Returns:
            ClickHouse Decimal type string
        """
        scale = scale if scale is not None else 0
        
        if precision is None:
            return f"Decimal64({scale})"
        elif precision <= 9:
            return f"Decimal32({scale})"
        elif precision <= 18:
            return f"Decimal64({scale})"
        elif precision <= 38:
            return f"Decimal128({scale})"
        else:
            return f"Decimal256({scale})"
    
    @classmethod
    def map_type(
        cls,
        source_type: Optional[str],
        database: str = "postgresql",
        nullable: bool = True,
    ) -> str:
        """
        Map a source database type to a ClickHouse type.
        
        Args:
            source_type: The source database column type (e.g., "varchar(255)")
            database: Source database type ('postgresql', 'mysql', 'oracle', 'sqlserver')
            nullable: Whether the column allows NULL values
            
        Returns:
            Corresponding ClickHouse type string
            
        Examples:
            >>> ClickHouseTypeMapper.map_type("varchar(255)", "postgresql")
            'String'
            >>> ClickHouseTypeMapper.map_type("numeric(18,4)", "postgresql")
            'Decimal64(4)'
            >>> ClickHouseTypeMapper.map_type("int", "mysql", nullable=False)
            'Int32'
        """
        if not source_type:
            return "String"
        
        base_type, precision, scale = cls._parse_type_precision(source_type)
        db_mapping = cls._get_db_mapping(database)
        
        # First, try direct lookup with full type string
        type_lower = source_type.lower().strip()
        if type_lower in db_mapping:
            clickhouse_type = db_mapping[type_lower]
        # Then try with base type
        elif base_type in db_mapping:
            clickhouse_type = db_mapping[base_type]
        # Fallback to normalized type mapping
        elif base_type in cls.NORMALIZED_TO_CLICKHOUSE:
            clickhouse_type = cls.NORMALIZED_TO_CLICKHOUSE[base_type]
        else:
            # Default to String for unknown types
            logger.warning(f"Unknown type '{source_type}' from {database}, defaulting to String")
            clickhouse_type = "String"
        
        # Handle Decimal precision
        if clickhouse_type.startswith("Decimal") or base_type in ("numeric", "decimal", "number"):
            if precision is not None or scale is not None:
                clickhouse_type = cls._get_decimal_type(precision, scale)
        
        # Handle Nullable wrapper if needed (ClickHouse convention)
        # Note: Most users prefer to handle Nullable at the DDL level
        # so we don't wrap by default
        
        return clickhouse_type
    
    @classmethod
    def map_columns(
        cls,
        columns: list,
        database: str = "postgresql",
    ) -> list:
        """
        Map a list of column definitions to ClickHouse types.
        
        Args:
            columns: List of column dicts with 'name', 'data_type', 'nullable' keys
            database: Source database type
            
        Returns:
            List of column dicts with 'clickhouse_type' added
            
        Example:
            >>> columns = [
            ...     {"name": "id", "data_type": "integer", "nullable": False},
            ...     {"name": "email", "data_type": "varchar(255)", "nullable": True},
            ... ]
            >>> ClickHouseTypeMapper.map_columns(columns, "postgresql")
            [
                {"name": "id", "data_type": "integer", "nullable": False, "clickhouse_type": "Int32"},
                {"name": "email", "data_type": "varchar(255)", "nullable": True, "clickhouse_type": "String"},
            ]
        """
        result = []
        for col in columns:
            col_copy = dict(col)
            col_copy["clickhouse_type"] = cls.map_type(
                source_type=col.get("data_type", "varchar"),
                database=database,
                nullable=col.get("nullable", True),
            )
            result.append(col_copy)
        return result
    
    @classmethod
    def get_create_table_column_def(
        cls,
        column_name: str,
        source_type: str,
        database: str = "postgresql",
        nullable: bool = True,
        default_value: Optional[str] = None,
    ) -> str:
        """
        Generate a ClickHouse column definition for CREATE TABLE.
        
        Args:
            column_name: Column name
            source_type: Source database type
            database: Source database type
            nullable: Whether column allows NULL
            default_value: Default value expression
            
        Returns:
            ClickHouse column definition string
            
        Example:
            >>> ClickHouseTypeMapper.get_create_table_column_def(
            ...     "created_at", "timestamp", "postgresql", False
            ... )
            'created_at DateTime NOT NULL'
        """
        clickhouse_type = cls.map_type(source_type, database, nullable)
        
        parts = [f"`{column_name}`"]
        
        if nullable:
            parts.append(f"Nullable({clickhouse_type})")
        else:
            parts.append(clickhouse_type)
        
        if default_value:
            parts.append(f"DEFAULT {default_value}")
        
        return " ".join(parts)
    
    @classmethod
    def generate_create_table_ddl(
        cls,
        table_name: str,
        columns: list,
        database: str = "postgresql",
        engine: str = "MergeTree",
        order_by: Optional[list] = None,
        partition_by: Optional[str] = None,
        target_database: Optional[str] = None,
    ) -> str:
        """
        Generate a complete CREATE TABLE DDL for ClickHouse.
        
        Args:
            table_name: Target table name
            columns: List of column dicts with 'name', 'data_type', 'nullable' keys
            database: Source database type
            engine: ClickHouse table engine
            order_by: ORDER BY columns (required for MergeTree family)
            partition_by: PARTITION BY expression
            target_database: Target ClickHouse database name
            
        Returns:
            Complete CREATE TABLE DDL string
        """
        # Map columns to ClickHouse types
        mapped_columns = cls.map_columns(columns, database)
        
        # Build column definitions
        column_defs = []
        for col in mapped_columns:
            col_def = cls.get_create_table_column_def(
                column_name=col["name"],
                source_type=col["data_type"],
                database=database,
                nullable=col.get("nullable", True),
                default_value=col.get("default_value"),
            )
            column_defs.append(f"    {col_def}")
        
        # Build table name
        full_table_name = f"`{target_database}`.`{table_name}`" if target_database else f"`{table_name}`"
        
        # Build DDL
        ddl_parts = [
            f"CREATE TABLE IF NOT EXISTS {full_table_name}",
            "(",
            ",\n".join(column_defs),
            ")",
            f"ENGINE = {engine}",
        ]
        
        # Add ORDER BY (required for MergeTree)
        if order_by:
            order_by_str = ", ".join(f"`{c}`" for c in order_by)
            ddl_parts.append(f"ORDER BY ({order_by_str})")
        elif engine.startswith("MergeTree"):
            # Default to tuple() if no order specified
            ddl_parts.append("ORDER BY tuple()")
        
        # Add PARTITION BY if specified
        if partition_by:
            ddl_parts.append(f"PARTITION BY {partition_by}")
        
        return "\n".join(ddl_parts)
