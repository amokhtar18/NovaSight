{% macro clickhouse_incremental_strategy(
    unique_key,
    updated_at_column='updated_at',
    is_scd_type2=false
) %}
    {#
        ClickHouse-optimized incremental strategy for NovaSight.
        Handles both SCD Type 1 (upsert) and SCD Type 2 (versioning) patterns.
        
        Args:
            unique_key: Primary key column(s) for deduplication
            updated_at_column: Column to use for incremental loading
            is_scd_type2: Whether to use SCD Type 2 versioning
            
        Usage in model config:
            {{ config(
                materialized='incremental',
                unique_key='id',
                incremental_strategy='delete+insert'
            ) }}
    #}
    
    {% if is_incremental() %}
        WHERE {{ updated_at_column }} > (
            SELECT coalesce(max({{ updated_at_column }}), '1970-01-01')
            FROM {{ this }}
        )
    {% endif %}
{% endmacro %}


{% macro generate_surrogate_key(field_list) %}
    {#
        Generate a surrogate key from multiple fields using ClickHouse's cityHash64.
        More efficient than MD5 for ClickHouse.
        
        Args:
            field_list: List of column names to hash
            
        Usage:
            SELECT {{ generate_surrogate_key(['id', 'tenant_id']) }} as surrogate_key
    #}
    cityHash64(
        {%- for field in field_list %}
            coalesce(cast({{ field }} as String), '')
            {%- if not loop.last %} || '|' || {% endif -%}
        {%- endfor %}
    )
{% endmacro %}
