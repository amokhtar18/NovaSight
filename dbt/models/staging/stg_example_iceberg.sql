{{
  config(
    materialized='view',
    schema='staging',
    tags=['staging', 'iceberg']
  )
}}

{#
  Example Staging Model for Iceberg Source
  =========================================
  
  This model reads from an Iceberg table loaded by dlt pipelines.
  It's designed to be run with the 'lake' target (dbt-duckdb).
  
  When running against the 'warehouse' target (dbt-clickhouse),
  this model should be skipped as marts will read from the
  compiled lake layer results.
  
  Usage:
    dbt run --target lake --select staging_example
#}

{% if target.name == 'lake' %}
  -- Lake target: Read from Iceberg via DuckDB
  SELECT
    *,
    now() as _loaded_at
  FROM {{ iceberg_source(var('iceberg_namespace', 'tenant_default.raw'), 'example_table') }}
  
{% else %}
  -- Non-lake targets: Create empty placeholder
  -- (marts should use ref() to the actual materialized source)
  SELECT
    NULL as id,
    NULL as name,
    now() as _loaded_at
  WHERE 1 = 0
  
{% endif %}
