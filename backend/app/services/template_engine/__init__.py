"""
NovaSight Template Engine
=========================

Secure template engine for code generation using Jinja2.
Implements ADR-002: All generated code comes from pre-approved templates only.

Usage:
    from app.services.template_engine import TemplateEngine, template_engine
    
    # Use the singleton instance
    result = template_engine.render('sql/create_table.sql.j2', {
        'table_name': 'users',
        'columns': [{'name': 'id', 'type': 'UUID'}]
    })
"""

from app.services.template_engine.engine import TemplateEngine, template_engine
from app.services.template_engine.validator import (
    SQLIdentifier,
    ColumnDefinition,
    TableDefinition,
    DbtModelDefinition,
    AirflowDagDefinition,
    TemplateParameterValidator,
)
from app.services.template_engine.filters import (
    to_snake_case,
    to_camel_case,
    to_pascal_case,
    sql_identifier_safe,
    sql_string_escape,
    sql_value,
)

__all__ = [
    # Engine
    "TemplateEngine",
    "template_engine",
    # Validators
    "SQLIdentifier",
    "ColumnDefinition",
    "TableDefinition",
    "DbtModelDefinition",
    "AirflowDagDefinition",
    "TemplateParameterValidator",
    # Filters
    "to_snake_case",
    "to_camel_case",
    "to_pascal_case",
    "sql_identifier_safe",
    "sql_string_escape",
    "sql_value",
]
    "sql_string_escape",
]
