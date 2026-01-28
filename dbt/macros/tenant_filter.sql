{% macro tenant_filter() %}
    {#
        Returns tenant filter clause for use in WHERE clauses.
        Ensures data isolation in multi-tenant queries.
        
        Usage:
            SELECT * FROM some_table WHERE {{ tenant_filter() }}
    #}
    tenant_id = '{{ var("tenant_id") }}'
{% endmacro %}


{% macro current_tenant_id() %}
    {#
        Returns the current tenant ID as a quoted string.
        Useful for inserting into queries or comparisons.
        
        Usage:
            SELECT {{ current_tenant_id() }} as tenant_id
    #}
    '{{ var("tenant_id") }}'
{% endmacro %}


{% macro tenant_database() %}
    {#
        Returns the current tenant database name.
        Used for cross-database references if needed.
        
        Usage:
            SELECT * FROM {{ tenant_database() }}.some_table
    #}
    {{ var('tenant_database', target.schema) }}
{% endmacro %}
