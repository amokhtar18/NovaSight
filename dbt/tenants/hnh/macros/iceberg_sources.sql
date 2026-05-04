-- NovaSight: Example Iceberg source macro
-- Used to read from Iceberg tables in the data lake

{% macro iceberg_source(namespace, table_name) %}
    {#
    Reads from an Iceberg table on S3 using DuckDB's iceberg extension.
    
    Usage in staging models:
        SELECT * FROM {{ iceberg_source('tenant_acme.raw', 'customers') }}
    
    Args:
        namespace: Iceberg namespace (e.g., 'tenant_acme.raw')
        table_name: Iceberg table name (e.g., 'customers')
    
    Returns:
        SQL expression to read from the Iceberg table
    #}
    
    {% set s3_bucket = env_var('S3_BUCKET', '') %}
    {% set s3_endpoint = env_var('S3_ENDPOINT_URL', '') %}
    
    {% if s3_endpoint %}
        {# MinIO/custom S3 endpoint #}
        iceberg_scan('s3://{{ s3_bucket }}/iceberg/{{ namespace }}/{{ table_name }}')
    {% else %}
        {# AWS S3 #}
        iceberg_scan('s3://{{ s3_bucket }}/iceberg/{{ namespace }}/{{ table_name }}')
    {% endif %}
{% endmacro %}


{% macro iceberg_incremental(namespace, table_name, cursor_column, last_value=None) %}
    {#
    Reads incrementally from an Iceberg table using time-travel.
    
    Usage:
        SELECT * FROM {{ iceberg_incremental('tenant_acme.raw', 'orders', 'updated_at', var('last_processed')) }}
    
    Args:
        namespace: Iceberg namespace
        table_name: Iceberg table name
        cursor_column: Column for incremental filtering
        last_value: Last processed value (optional)
    #}
    
    {% set s3_bucket = env_var('S3_BUCKET', '') %}
    
    SELECT * 
    FROM iceberg_scan('s3://{{ s3_bucket }}/iceberg/{{ namespace }}/{{ table_name }}')
    {% if last_value %}
    WHERE {{ cursor_column }} > '{{ last_value }}'
    {% endif %}
{% endmacro %}
