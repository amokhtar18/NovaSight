{#-
    Raw landing table for the revenuebyclient dlt extract.

    Reads JSONL files written by the dlt ``filesystem`` destination at
        s3://{TENANT_S3_BUCKET}/lake/{tenant_database}_raw/revenuebyclient/*.jsonl
    via ClickHouse's native ``s3()`` table function and materialises them
    as a MergeTree table inside the tenant's raw database
    (``tenant_{tenant_id}``).

    Schema is inferred from JSONL by ClickHouse. We materialise into the
    raw database (not ``dbt_tenant_*``) so dbt staging models can reference
    it via ``{{ source('tenant_raw', 'revenuebyclient') }}``.
-#}

{%- set tenant_id = var('tenant_id', '') -%}
{%- if not tenant_id -%}
    {{ exceptions.raise_compiler_error(
        "var 'tenant_id' is required for raw.revenuebyclient. "
        "Pass --vars '{tenant_id: <slug>}' or set TENANT_ID env var."
    ) }}
{%- endif -%}

{%- set tenant_database = 'tenant_' ~ tenant_id -%}
{%- set tenant_bucket = env_var('TENANT_S3_BUCKET', 'tenant-' ~ tenant_id | replace('_', '-')) -%}
{%- set s3_endpoint = env_var('MINIO_ENDPOINT_URL', 'http://minio:9000') -%}
{%- set s3_path = s3_endpoint ~ '/' ~ tenant_bucket ~ '/lake/' ~ tenant_database ~ '_raw/revenuebyclient/*.jsonl' -%}

{{
    config(
        materialized='table',
        schema=tenant_database,
        engine='MergeTree()',
        order_by='tuple()',
        tags=['raw', 'lake_landing', tenant_database]
    )
}}

SELECT *
FROM s3(
    '{{ s3_path }}',
    '{{ env_var("MINIO_ROOT_USER") }}',
    '{{ env_var("MINIO_ROOT_PASSWORD") }}',
    'JSONEachRow',
    'auto',
    'gzip'
)
