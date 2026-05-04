{% macro generate_schema_name(custom_schema_name, node) -%}
    {#-
        NovaSight multi-tenant schema routing.

        Each tenant has its own ClickHouse database, named ``tenant_<slug>``,
        injected via the ``tenant_database`` dbt variable (set by the tenant
        dbt project's vars block, falling back to ``target.schema``).

        When a model declares a ``+schema:`` config (typically per layer in
        dbt_project.yml), we honor it by appending ``_<layer>`` to the base
        tenant database. This routes:

            staging models       → tenant_<slug>_staging
            intermediate models  → tenant_<slug>_intermediate
            marts models         → tenant_<slug>_marts

        Models without a ``+schema:`` override land in the base tenant
        database (``tenant_<slug>``). dbt-clickhouse will create the
        database lazily on first materialization.

        Args:
            custom_schema_name: The custom schema declared in model config
            node: The dbt node being compiled
        Returns:
            Tenant + layer-qualified database name
    -#}
    {%- set base = var('tenant_database', target.schema) -%}
    {%- if custom_schema_name is none or (custom_schema_name | trim) == '' -%}
        {{ base | trim }}
    {%- else -%}
        {{ base | trim }}_{{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
