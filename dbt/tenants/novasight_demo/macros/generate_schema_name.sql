{% macro generate_schema_name(custom_schema_name, node) -%}
    {#-
        NovaSight multi-tenant schema routing (tenant copy).

        Mirrors dbt/macros/generate_schema_name.sql. Routes models with a
        ``+schema:`` config into ``tenant_<slug>_<layer>`` databases:

            staging      → tenant_<slug>_staging
            intermediate → tenant_<slug>_intermediate
            marts        → tenant_<slug>_marts

        Models without a ``+schema:`` override land in ``tenant_<slug>``.
    -#}
    {%- set base = var('tenant_database', target.schema) -%}
    {%- if custom_schema_name is none or (custom_schema_name | trim) == '' -%}
        {{ base | trim }}
    {%- else -%}
        {{ base | trim }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
