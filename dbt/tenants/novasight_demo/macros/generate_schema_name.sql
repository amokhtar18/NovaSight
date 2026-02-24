{% macro generate_schema_name(custom_schema_name, node) -%}
    {# 
        Custom schema name generation for NovaSight multi-tenant architecture.
        Uses tenant database as schema to ensure proper tenant isolation.
        
        Args:
            custom_schema_name: The custom schema defined in the model config
            node: The dbt node being compiled
            
        Returns:
            The tenant-specific database/schema name
    #}
    {{ var('tenant_database', target.schema) }}
{%- endmacro %}
