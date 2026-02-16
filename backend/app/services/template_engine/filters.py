"""
NovaSight Template Engine - Custom Jinja2 Filters
==================================================

Custom filters for template rendering with security in mind.
"""

import re
from typing import Any


def to_snake_case(value: str) -> str:
    """
    Convert a string to snake_case.
    
    Examples:
        'MyTableName' -> 'my_table_name'
        'already_snake' -> 'already_snake'
        'CamelCASEWord' -> 'camel_case_word'
    """
    if not value:
        return ""
    
    # Insert underscore before uppercase letters
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', value)
    # Insert underscore before uppercase letters following lowercase letters
    s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1)
    # Convert to lowercase and clean up multiple underscores
    result = re.sub(r'_+', '_', s2.lower())
    # Remove leading/trailing underscores
    return result.strip('_')


def to_camel_case(value: str) -> str:
    """
    Convert a string to camelCase.
    
    Examples:
        'my_table_name' -> 'myTableName'
        'already-camel' -> 'alreadyCamel'
        'PascalCase' -> 'pascalCase'
    """
    if not value:
        return ""
    
    # Split on underscores, hyphens, and spaces
    words = re.split(r'[-_\s]+', value)
    if not words:
        return ""
    
    # First word lowercase, rest title case
    result = words[0].lower()
    for word in words[1:]:
        if word:
            result += word.capitalize()
    
    return result


def to_pascal_case(value: str) -> str:
    """
    Convert a string to PascalCase.
    
    Examples:
        'my_table_name' -> 'MyTableName'
        'already-pascal' -> 'AlreadyPascal'
    """
    if not value:
        return ""
    
    # Split on underscores, hyphens, and spaces
    words = re.split(r'[-_\s]+', value)
    
    # Capitalize each word
    return ''.join(word.capitalize() for word in words if word)


def sql_identifier_safe(value: str, max_length: int = 63) -> str:
    """
    Sanitize a string for use as a SQL identifier (table/column name).
    
    - Converts to lowercase
    - Replaces spaces and hyphens with underscores
    - Removes non-alphanumeric characters (except underscore)
    - Ensures starts with a letter
    - Truncates to max_length
    
    Args:
        value: The string to sanitize
        max_length: Maximum length for the identifier (PostgreSQL default: 63)
    
    Returns:
        A safe SQL identifier string
    
    Examples:
        'My Table-Name!' -> 'my_table_name'
        '123invalid' -> 't_123invalid'
    """
    if not value:
        return "unnamed"
    
    # Convert to lowercase
    result = value.lower()
    
    # Replace spaces and hyphens with underscores
    result = re.sub(r'[-\s]+', '_', result)
    
    # Remove non-alphanumeric characters except underscores
    result = re.sub(r'[^a-z0-9_]', '', result)
    
    # Collapse multiple underscores
    result = re.sub(r'_+', '_', result)
    
    # Remove leading/trailing underscores
    result = result.strip('_')
    
    # Ensure starts with a letter
    if result and not result[0].isalpha():
        result = 't_' + result
    
    # Handle empty result
    if not result:
        result = "unnamed"
    
    # Truncate to max length
    return result[:max_length]


def sql_string_escape(value: Any) -> str:
    """
    Escape and quote a value for safe use in SQL.
    
    This is for VALUES only - for identifiers use sql_identifier_safe.
    Handles different types appropriately:
    - None -> NULL
    - bool -> 1/0
    - int/float -> unquoted number
    - str -> escaped and quoted string
    
    Args:
        value: The value to escape
    
    Returns:
        Escaped value safe for SQL literal
    """
    if value is None:
        return "NULL"
    
    if isinstance(value, bool):
        return "1" if value else "0"
    
    if isinstance(value, (int, float)):
        return str(value)
    
    # String value - escape and quote
    escaped = str(value).replace("'", "''")
    escaped = escaped.replace("\\", "\\\\")
    
    return f"'{escaped}'"


def sql_value(value: Any) -> str:
    """
    Alias for sql_string_escape for backward compatibility.
    """
    return sql_string_escape(value)


def sql_type_mapping(python_type: str, database: str = "postgresql") -> str:
    """
    Map Python/generic types to database-specific SQL types.
    
    Args:
        python_type: The Python or generic type name
        database: Target database ('postgresql', 'clickhouse')
    
    Returns:
        Database-specific SQL type
    """
    postgresql_types = {
        "str": "VARCHAR(255)",
        "string": "VARCHAR(255)",
        "text": "TEXT",
        "int": "INTEGER",
        "integer": "INTEGER",
        "bigint": "BIGINT",
        "float": "NUMERIC",
        "decimal": "NUMERIC",
        "bool": "BOOLEAN",
        "boolean": "BOOLEAN",
        "date": "DATE",
        "datetime": "TIMESTAMP",
        "timestamp": "TIMESTAMP WITH TIME ZONE",
        "uuid": "UUID",
        "json": "JSONB",
        "jsonb": "JSONB",
        "binary": "BYTEA",
    }
    
    clickhouse_types = {
        "str": "String",
        "string": "String",
        "text": "String",
        "int": "Int32",
        "integer": "Int32",
        "bigint": "Int64",
        "float": "Float64",
        "decimal": "Decimal64(4)",
        "bool": "UInt8",
        "boolean": "UInt8",
        "date": "Date",
        "datetime": "DateTime",
        "timestamp": "DateTime64(3)",
        "uuid": "UUID",
        "json": "String",
        "jsonb": "String",
        "binary": "String",
    }
    
    type_maps = {
        "postgresql": postgresql_types,
        "clickhouse": clickhouse_types,
    }
    
    type_map = type_maps.get(database.lower(), postgresql_types)
    return type_map.get(python_type.lower(), python_type.upper())


def quote_identifier(value: str, database: str = "postgresql") -> str:
    """
    Quote a SQL identifier properly for the target database.
    
    Args:
        value: The identifier to quote
        database: Target database ('postgresql', 'clickhouse')
    
    Returns:
        Properly quoted identifier
    """
    if database.lower() == "clickhouse":
        # ClickHouse uses backticks or double quotes
        escaped = value.replace("`", "``")
        return f"`{escaped}`"
    else:
        # PostgreSQL uses double quotes
        escaped = value.replace('"', '""')
        return f'"{escaped}"'


def indent_lines(value: str, spaces: int = 4, first_line: bool = False) -> str:
    """
    Indent each line of a multi-line string.
    
    Args:
        value: Multi-line string to indent
        spaces: Number of spaces to indent
        first_line: Whether to indent the first line
    
    Returns:
        Indented string
    """
    if not value:
        return ""
    
    indent = " " * spaces
    lines = value.split('\n')
    
    if first_line:
        return '\n'.join(indent + line for line in lines)
    else:
        result = [lines[0]]
        result.extend(indent + line for line in lines[1:])
        return '\n'.join(result)


def to_clickhouse_type(source_type: str, database: str = "postgresql") -> str:
    """
    Map a source database type to a ClickHouse type.
    
    This filter uses the ClickHouseTypeMapper for comprehensive type conversion
    from various source databases (PostgreSQL, MySQL, Oracle, SQL Server) to
    ClickHouse types.
    
    Args:
        source_type: The source database column type (e.g., "varchar(255)", "numeric(18,4)")
        database: Source database type ('postgresql', 'mysql', 'oracle', 'sqlserver')
    
    Returns:
        Corresponding ClickHouse type string
        
    Examples:
        {{ "varchar(255)" | to_clickhouse_type("postgresql") }}  -> "String"
        {{ "numeric(18,4)" | to_clickhouse_type("postgresql") }}  -> "Decimal64(4)"
        {{ "int" | to_clickhouse_type("mysql") }}  -> "Int32"
        {{ "datetime2" | to_clickhouse_type("sqlserver") }}  -> "DateTime64(3)"
    """
    from app.domains.datasources.infrastructure.connectors.utils.type_mapping import (
        ClickHouseTypeMapper,
    )
    
    return ClickHouseTypeMapper.map_type(source_type, database)


def clickhouse_column_def(
    column_name: str,
    source_type: str,
    database: str = "postgresql",
    nullable: bool = True,
    default_value: str = None,
) -> str:
    """
    Generate a ClickHouse column definition for CREATE TABLE.
    
    Args:
        column_name: Column name
        source_type: Source database type
        database: Source database type ('postgresql', 'mysql', 'oracle', 'sqlserver')
        nullable: Whether column allows NULL
        default_value: Default value expression
    
    Returns:
        ClickHouse column definition string
        
    Examples:
        {{ "created_at" | clickhouse_column_def("timestamp", "postgresql", False) }}
        -> "created_at DateTime NOT NULL"
    """
    from app.domains.datasources.infrastructure.connectors.utils.type_mapping import (
        ClickHouseTypeMapper,
    )
    
    return ClickHouseTypeMapper.get_create_table_column_def(
        column_name=column_name,
        source_type=source_type,
        database=database,
        nullable=nullable,
        default_value=default_value,
    )
