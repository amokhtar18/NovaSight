# Prompt 073 — dbt Dual-Adapter (DuckDB Lake → ClickHouse Marts)

**Phase**: 4 of 6 in [MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md)
**Owner**: `@dbt`
**Depends on**: Prompt 070 (catalog + storage), Prompt 072 (so the asset chain is wired)

## Context
Per tenant we will generate **two dbt subprojects**: `lake/` (dbt-duckdb, reads Iceberg from S3, materializes Parquet) and `warehouse/` (dbt-clickhouse, ingests staged Parquet via CH `s3()`, materializes marts in `tenant_{slug}` ClickHouse DB).

## Read first
- [.github/instructions/MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md) §4 Phase 4 + §2 (locked decisions).
- [.github/agents/dbt-agent.agent.md](../agents/dbt-agent.agent.md).
- Current `TenantDbtProjectManager` at `backend/app/domains/transformation/infrastructure/tenant_dbt_project.py`.

## Deliverables
1. Rewrite `TenantDbtProjectManager` to generate, per tenant, the layout:
   ```
   dbt/tenants/{slug}/
   ├── lake/
   │   ├── dbt_project.yml
   │   ├── profiles.yml          # dbt-duckdb, extensions=[iceberg, httpfs]
   │   ├── packages.yml          # dbt-utils
   │   ├── models/
   │   │   ├── _sources.yml      # Iceberg sources under tenant_{slug}.raw
   │   │   └── staging/          # external Parquet outputs to s3://{bucket}/staged/
   │   └── target/
   └── warehouse/
       ├── dbt_project.yml
       ├── profiles.yml          # dbt-clickhouse against tenant_{slug} DB
       ├── packages.yml          # dbt_utils, dbt_expectations, dbt-clickhouse
       ├── models/
       │   ├── _sources.yml      # references the Parquet outputs from lake
       │   ├── staging/          # CH s3() ingest of staged Parquet
       │   └── marts/            # native CH tables/MVs
       └── target/
   ```
2. `lake/profiles.yml` injects S3 creds + `ICEBERG_CATALOG_URL` purely from env vars. Never write secrets to disk.
3. `warehouse/profiles.yml` reuses the existing CH env-var pattern.
4. Reuse macros: `tenant_filter`, `clickhouse_incremental_strategy`, `generate_surrogate_key`. Move them under `dbt/macros/` (shared) and reference from both subprojects.
5. Update `DbtService` (`backend/app/domains/transformation/application/dbt_service.py`):
   - Add `run_lake(tenant_id, **opts)` and `run_warehouse(tenant_id, **opts)`.
   - Add `run_full(tenant_id, **opts)` — runs lake then warehouse; aborts warehouse if lake fails.
6. Add `dbt-duckdb` to backend image:
   - `backend/Dockerfile`, `backend/Dockerfile.dev`, `backend/requirements.txt`.
7. `TaskType` (in `backend/app/domains/orchestration/domain/models.py` + schemas): add `DBT_RUN_LAKE`, `DBT_RUN_WAREHOUSE`. Keep `DBT_RUN` as a deprecated alias mapping to `DBT_RUN_FULL` (run lake then warehouse).
8. Auto-regeneration hook: when a `DltPipeline` is activated for the first time and produces an Iceberg table, regenerate the tenant's `lake/models/_sources.yml` to declare the new source.

## Tests
- Unit: `TenantDbtProjectManager.regenerate(slug)` produces both subprojects with valid YAML; profiles read from env vars only.
- Integration: end-to-end on a single tenant — `dlt → lake → warehouse` produces matching row counts in CH and Parquet.
- Multi-tenant isolation: tenants A and B in parallel; A's `lake/` cannot resolve B's namespace (runtime error from pyiceberg if forced).

## Definition of done
- `DbtService.run_full(tenant_id)` succeeds end-to-end on a seeded tenant.
- `dbt-duckdb` and `dbt-clickhouse` both present in the backend container.
- Existing `dbt/tenants/novasight_demo/` rebuild matches the new layout (regenerate via the manager — do not hand-edit).
- Old single-project layout is deleted from `dbt/tenants/`.
