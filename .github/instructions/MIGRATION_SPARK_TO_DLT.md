# Migration: Spark → dlt + Iceberg/S3 + dbt(DuckDB→ClickHouse)

**Status**: Approved plan. Authoritative source for the Spark removal effort.
**Owner**: NovaSight Orchestrator Agent (coordinates), Ingestion Agent (executes Phases 1–3, 6), dbt Agent (Phase 4), Frontend Agent (Phase 5).
**Replaces**: PySpark ingestion templates, `pyspark_apps` table, the 6-step PySpark App Wizard, all Spark services (master/workers).

---

## 1. Goal

Replace the Spark-based ingestion engine with **[dlt](https://dlthub.com/)** pipelines that land **tenant-isolated Iceberg tables** in **per-tenant S3 buckets**, with a **Postgres SQL catalog**. Transform via a **dual-adapter dbt** project per tenant: `dbt-duckdb` reads Iceberg from S3 (staging), `dbt-clickhouse` writes marts into the tenant ClickHouse database. Replace the 6-step PySpark wizard with a **4-step plain-language Data Pipeline wizard** for non-technical users. Remove Spark from the codebase entirely.

---

## 2. Locked Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Iceberg catalog | **SQL catalog backed by existing platform Postgres** | No new service to deploy. pyiceberg + dbt-duckdb both support it natively. |
| Per-tenant S3 isolation | **Bucket-per-tenant, always** | Strongest isolation; matches enterprise-tenant expectation of own bucket + IAM. |
| Existing `PySparkApp` rows | **Hard cutover** | Drop `pyspark_apps` table; users recreate via new wizard. No row migration code. |
| dbt read path for Iceberg | **`dbt-duckdb` for lake (Iceberg reads) + `dbt-clickhouse` for marts**; handoff via CH `s3()` Parquet ingest | DuckDB has first-class Postgres SQL-catalog support; ClickHouse Iceberg integration is read-only and immature for SQL catalogs. |
| Dev object storage | **MinIO** in `docker-compose.yml` | Drop-in S3 API, no AWS dependency for local dev. |

---

## 3. Template Engine Rule (updated)

> NO arbitrary code generation. All executable artifacts (**dlt pipelines**, Dagster ops, dbt models) must be generated from pre-approved, security-audited Jinja2 templates with Pydantic-validated inputs.

PySpark templates (`backend/templates/pyspark/*.j2`) are removed. They are replaced by:

- `backend/templates/dlt/extract_pipeline.py.j2` — append / replace
- `backend/templates/dlt/merge_pipeline.py.j2` — `write_disposition=merge`
- `backend/templates/dlt/scd2_pipeline.py.j2` — dlt native SCD2

All rendered pipelines hard-code `tenant_id`, read tenant S3 creds from env vars injected by Dagster, and write to the namespace `tenant_{slug}.raw` in the Iceberg catalog. The validator (`backend/app/services/template_engine/validator.py`) rejects any namespace or bucket override.

---

## 4. Phases

Phases 1–3 may proceed in parallel branches; Phase 4 depends on Phase 1. Phase 5 depends on Phase 2's API surface. Phase 6 (deletion) runs last, only after 1–5 are green in CI and on a staging tenant.

### Phase 1 — Foundation: storage, catalog, SDKs

**Owner**: `@infrastructure` + `@backend`.

**Deliverables**
1. Add Python deps to [backend/requirements.txt](backend/requirements.txt): `dlt[clickhouse,filesystem,pyarrow,sql_database]`, `pyiceberg[sql,s3fs]`, `dbt-duckdb`. Pin versions. `boto3` already present.
2. Alembic migration: ensure schema `iceberg_catalog` exists in the platform DB. Pyiceberg auto-creates its tables on first use; the migration only guarantees the schema and grants.
3. Per-tenant S3 storage config:
   - Extend `BaseInfrastructureConfigSchema` with `service_type='object_storage'` and a new `S3StorageSettings` Pydantic schema (fields: `bucket`, `region`, `endpoint_url`, `access_key`, `secret_key`, `prefix`, `kms_key_id`, `path_style`).
   - Add admin endpoints in [backend/app/api/v1/admin/infrastructure.py](backend/app/api/v1/admin/infrastructure.py) mirroring the ClickHouse pattern (list/get/create/update/test) for `object_storage`. Per-tenant scope only.
   - In `ProvisioningService` add `provision_tenant_bucket()`. In dev (MinIO), auto-create. In prod, validate existence + `s3:ListBucket` / `s3:PutObject` / `s3:GetObject` permissions.
   - Tenant onboarding flow calls `provision_tenant_bucket()` and seeds an `InfrastructureConfig` row.
4. Compose: add `minio` service to [docker-compose.yml](docker-compose.yml). Init script auto-creates buckets for seeded tenants.
5. New module `backend/app/platform/lake/iceberg_catalog.py`:
   - `get_catalog_for_tenant(tenant_id) -> SqlCatalog`
   - Namespace convention: `tenant_{slug}.raw`, optional `tenant_{slug}.staging`.
   - Fetches S3 creds from the tenant's `InfrastructureConfig`.

**Verification**: unit tests for the catalog factory; manual: create tenant, see bucket + namespace created, write a 3-row pyarrow table, list it.

### Phase 2 — dlt pipeline service & code generation

**Owner**: `@ingestion` (new) + `@template-engine`.

**Deliverables**
1. Rename domain `backend/app/domains/compute/` → `backend/app/domains/ingestion/`. Inside:
   - `domain/models.py`: new `DltPipeline` SQLAlchemy model (replaces `PySparkApp`). Fields: id, tenant_id, connection_id, name, description, status (draft/active/inactive/error), source_type (table/query), source_schema, source_table, source_query, columns_config (JSONB), primary_key_columns, incremental_cursor_column, incremental_cursor_type (timestamp/version/none), write_disposition (append/replace/merge/scd2), partition_columns, iceberg_namespace, iceberg_table_name, last_run_at/status/rows/duration, created_by/at, updated_at, generated_at, options.
   - `application/dlt_pipeline_service.py`: replaces `PySparkAppService`. CRUD + code generation + run trigger.
   - `api/dlt_routes.py`: replaces `pyspark_routes.py`. Endpoints under `/api/v1/pipelines/...`.
   - `schemas/dlt_schemas.py`: Pydantic Create/Update/Response/Preview schemas.
2. New Jinja templates at `backend/templates/dlt/`: `extract_pipeline.py.j2`, `merge_pipeline.py.j2`, `scd2_pipeline.py.j2`. Each produces a thin Python entrypoint that imports `dlt`, configures the Iceberg destination over the tenant's S3 bucket + Postgres SQL catalog, defines a `dlt.source` over the JDBC source via `dlt-sql_database`, and runs the pipeline.
3. Template engine integration:
   - Register the three templates in `backend/app/services/template_engine/engine.py`.
   - In `backend/app/services/template_engine/validator.py`, add `Dlt*Definition` Pydantic schemas (mirroring the previous `PySpark*Definition` family) and the template→schema map. Remove the PySpark validators in Phase 6.
4. Generated code storage: same shape as today — code on the `DltPipeline` row + a file under `/opt/dlt/pipelines/{tenant_slug}/{pipeline}.py` (replaces `/opt/spark/jobs`).
5. Tenant isolation enforcement: validator rejects pipelines whose `iceberg_namespace` does not match `tenant_{slug}.raw` or whose template attempts to override the bucket env var.

**Verification**: render each template against a fixture; run end-to-end against SQLite source → MinIO bucket → Postgres catalog locally; assert Iceberg table appears via pyiceberg and row counts match.

### Phase 3 — Orchestration: Dagster

**Owner**: `@orchestration` + `@ingestion`.

**Deliverables**
1. Delete: [backend/orchestration/resources/spark_resource.py](backend/orchestration/resources/spark_resource.py), [remote_spark_resource.py](backend/orchestration/resources/remote_spark_resource.py), [assets/pyspark_builder.py](backend/orchestration/assets/pyspark_builder.py), [schedules/pyspark_schedules.py](backend/orchestration/schedules/pyspark_schedules.py), and the `_build_spark_asset` branch in `asset_factory.py`.
2. New `backend/orchestration/assets/dlt_builder.py`:
   - `DltAssetBuilder` reads `DltPipeline` rows per tenant and emits one Dagster asset per pipeline.
   - Asset op runs the generated pipeline as a subprocess: `python /opt/dlt/pipelines/{tenant}/{pipeline}.py`, injecting env vars for `TENANT_ID`, `TENANT_S3_BUCKET`, S3 creds, `ICEBERG_CATALOG_URL`.
   - Logs/metrics piped to Dagster.
3. `TaskType` enum: in [backend/app/domains/orchestration/domain/models.py](backend/app/domains/orchestration/domain/models.py) and `dag_schemas.py`, replace `SPARK_SUBMIT` with `DLT_RUN`. Migrate any existing `DagConfig` rows referencing `SPARK_SUBMIT`.
4. New `backend/orchestration/schedules/dlt_schedules.py` mirrors the old PySpark one.
5. Concurrency: rename `DAGSTER_SPARK_CONCURRENCY_LIMIT` → `DAGSTER_DLT_CONCURRENCY_LIMIT` in `backend/app/config.py` and `.env.example`.

**Verification**: Dagster UI shows assets per pipeline; trigger a run end-to-end; row counts in Iceberg match source.

### Phase 4 — dbt: dual-adapter project per tenant

**Owner**: `@dbt`.

**Deliverables**
1. Add `dbt-duckdb` to backend image (Dockerfile.dev + Dockerfile + requirements).
2. Rewrite `TenantDbtProjectManager` ([backend/app/domains/transformation/infrastructure/tenant_dbt_project.py](backend/app/domains/transformation/infrastructure/tenant_dbt_project.py)) to generate **two subprojects per tenant** under `dbt/tenants/{slug}/`:
   - `lake/` — `dbt-duckdb` profile, `extensions: [iceberg, httpfs]`, configured for tenant's S3 bucket + Postgres SQL catalog. `sources.yml` declares each Iceberg table written by dlt under namespace `tenant_{slug}.raw`. Models materialize as `external` Parquet to the tenant bucket's `staged/` prefix.
   - `warehouse/` — `dbt-clickhouse` profile against `tenant_{slug}` DB. `sources.yml` references the staged Parquet outputs. Staging models use a CH `s3()` table function or a `pre_hook` `INSERT INTO ... SELECT * FROM s3(...)`. Marts materialize as native CH tables/MVs. Reuses existing `tenant_filter`, `clickhouse_incremental_strategy`, surrogate-key macros.
3. `DbtService` gains `run_lake()` / `run_warehouse()` and a `run_full()` that runs lake then warehouse.
4. `TaskType`: add `DBT_RUN_LAKE` / `DBT_RUN_WAREHOUSE` (preferred) **or** keep a single `DBT_RUN` with a `target` field. Pick one and stay consistent across schemas, services, Dagster ops.
5. Update `dbt/profiles.yml` template generation to inject S3 creds + catalog URL via env vars only (never hard-code).

**Verification**: end-to-end smoke — dlt loads sample table → lake dbt builds Parquet outputs → warehouse dbt loads CH → `select count(*)` matches across all three layers.

### Phase 5 — Frontend: simplified Data Pipeline wizard

**Owner**: `@frontend`.

**Goal**: a wizard a non-technical user (an analyst, a marketing ops person, a finance partner) can complete without reading docs. No "SCD", no "CDC", no "MergeTree", no "write mode" jargon in primary UI.

**Deliverables**
1. Rename / relocate:
   - `frontend/src/features/pyspark/` → `features/pipelines/`
   - `frontend/src/pages/pyspark/` → `pages/pipelines/`
   - `frontend/src/services/pysparkApi.ts` → `services/pipelinesApi.ts`
   - `frontend/src/types/pyspark.ts` → `types/pipeline.ts`
   - Update `types/index.ts`, routes, and sidebar entries.
2. Wizard 6 steps → **4 steps**:
   - **Step 1 — "What data do you want to copy?"** Single screen. One-click connection picker. Searchable tree of tables grouped by schema (default-expand the most recently used schema). "Advanced: write a query" toggle hides the SQL textarea. The connection's last-used schema is preselected.
   - **Step 2 — "Which columns, and how should we keep it fresh?"** Default: all columns selected; collapsible "Customize columns". Freshness strategy presented as **3 plain options** (radios with one-line explanation):
     - "Replace everything each time" → `write_disposition=replace`.
     - "Add only new rows" → `write_disposition=append` + auto-detect cursor (first timestamp/serial column wins; user can override).
     - "Keep history of changes" → `write_disposition=scd2` + auto-pick PK from CH metadata; user confirms.
     The terms *CDC, SCD, append, merge, replace, scd2* are NOT shown; they live only in code, schemas, and admin views.
   - **Step 3 — "Where should it go?"** Auto-fills target table name from the source name. Shows a single line: *"Will be saved to your data lake (Iceberg) and made available for analytics in ClickHouse."* No engine picker, no database picker. An "Advanced" disclosure exposes target table name + Iceberg namespace override.
   - **Step 4 — "Review & save"**. Plain-English summary, e.g. *"This pipeline will copy* customers *from your* Postgres - Production *database every time it runs, keeping a full history of changes. Data will be available in ClickHouse as `marts.customers`."* Code preview moves behind an "Advanced: view generated code" disclosure (Monaco kept for power users). Primary action is **Save & schedule** (bundles save + activate + opens schedule picker).
3. Auto-derived rules (no UI):
   - CH engine: `replace` → `MergeTree`; `append` (with cursor) → `MergeTree`; `scd2` → `VersionedCollapsingMergeTree`.
   - Target database: tenant-derived.
   - Iceberg namespace: `tenant_{slug}.raw`.
   - Pipeline name auto-generated from table name; user can rename in Step 4.
4. List page: rename "PySpark Apps" → **"Data Pipelines"**. Action labels: *Run now / Pause / Edit / Delete*. Drop "Generate Code" from the primary actions (kept in detail page advanced).
5. Detail page: lead with last-run summary + freshness indicator + **Run now** CTA. Code/template metadata behind collapsible "Advanced".
6. In-app help: each step has a one-sentence explainer + an info tooltip linking to a docs page (`docs/guides/data-pipelines.md`).
7. Drop the `pyspark` i18n namespace; add `pipelines`.
8. Replace feature flag `pyspark_apps` with `data_pipelines` (default on for new tenants).

**Verification**: Playwright e2e — non-technical persona creates pipeline → saves → runs → sees data in CH within 10 minutes without reading docs.

### Phase 6 — Spark removal (final, single PR)

**Owner**: `@infrastructure` + `@orchestrator` for sign-off.

Run only after Phases 1–5 are green in CI and verified on a staging tenant.

**Files to delete entirely**
- [infrastructure/spark/](infrastructure/spark/) (whole tree)
- [docker/spark/](docker/spark/) (whole tree)
- [backend/orchestration/resources/spark_resource.py](backend/orchestration/resources/spark_resource.py), [remote_spark_resource.py](backend/orchestration/resources/remote_spark_resource.py)
- [backend/orchestration/assets/pyspark_builder.py](backend/orchestration/assets/pyspark_builder.py), [schedules/pyspark_schedules.py](backend/orchestration/schedules/pyspark_schedules.py)
- [backend/templates/pyspark/](backend/templates/pyspark/) (3 templates)
- [backend/app/domains/compute/](backend/app/domains/compute/) (after rename to `ingestion/` is merged)
- [frontend/src/features/pyspark/](frontend/src/features/pyspark/), [frontend/src/pages/pyspark/](frontend/src/pages/pyspark/), [frontend/src/services/pysparkApi.ts](frontend/src/services/pysparkApi.ts), [frontend/src/types/pyspark.ts](frontend/src/types/pyspark.ts)
- [backend/tests/domains/compute/test_pyspark_service.py](backend/tests/domains/compute/test_pyspark_service.py)
- PySpark fixtures in [backend/tests/integration/test_tenant_isolation_integration.py](backend/tests/integration/test_tenant_isolation_integration.py) (rewrite for dlt)
- [.github/prompts/016-ingestion-dag-generator.md](.github/prompts/016-ingestion-dag-generator.md) (superseded by new prompts 070–074)

**Files to edit (remove Spark refs)**
- [docker-compose.yml](docker-compose.yml), [docker-compose.override.yml](docker-compose.override.yml) — drop spark-master/worker services + volumes/depends_on entries
- `helm/novasight/values*.yaml`, [helm/novasight/templates/NOTES.txt](helm/novasight/templates/NOTES.txt) — drop Spark stanzas
- [k8s/base/backend/configmap.yaml](k8s/base/backend/configmap.yaml) — remove `SPARK_*` env vars
- `.env.example` — drop `SPARK_*`; add `S3_*`, `MINIO_*`, `ICEBERG_CATALOG_URL`, `DAGSTER_DLT_CONCURRENCY_LIMIT`
- [backend/app/config.py](backend/app/config.py) — remove `SPARK_*`; add S3/Iceberg config
- [backend/app/api/v1/admin/infrastructure.py](backend/app/api/v1/admin/infrastructure.py) — remove `SparkConfigCreateSchema`, all `/settings/spark` endpoints, drop `'spark'` from `CREATE_SCHEMAS` and validation lists; add `'object_storage'`
- [backend/app/domains/tenants/schemas/infrastructure_schemas.py](backend/app/domains/tenants/schemas/infrastructure_schemas.py) — remove Spark; add S3
- [frontend/src/types/infrastructure.ts](frontend/src/types/infrastructure.ts) — drop `'spark'` everywhere; add `'object_storage'`
- [backend/app/seed.py](backend/app/seed.py) — drop `pyspark_apps` flag
- [backend/app/api/v1/__init__.py](backend/app/api/v1/__init__.py) — drop `pyspark_routes` import
- [backend/app/api/v1/dags.py](backend/app/api/v1/dags.py) — drop deprecated PySpark DAG shims
- [backend/app/domains/orchestration/api/dag_routes.py](backend/app/domains/orchestration/api/dag_routes.py) — delete `generate_pyspark_dag` and friends
- [backend/app/domains/orchestration/application/unified_job_service.py](backend/app/domains/orchestration/application/unified_job_service.py) — drop PySpark imports/branches
- [backend/app/domains/orchestration/infrastructure/asset_factory.py](backend/app/domains/orchestration/infrastructure/asset_factory.py) — drop `_build_spark_asset`
- [backend/app/domains/orchestration/domain/models.py](backend/app/domains/orchestration/domain/models.py), [schemas/dag_schemas.py](backend/app/domains/orchestration/schemas/dag_schemas.py) — remove `TaskType.SPARK_SUBMIT`
- [backend/app/platform/tenant/isolation.py](backend/app/platform/tenant/isolation.py) — replace `validate_pyspark_app_ownership` with `validate_pipeline_ownership`
- [backend/app/models/__init__.py](backend/app/models/__init__.py) — drop `PySparkApp`, `PySparkAppStatus`
- [backend/orchestration/dagster.yaml](backend/orchestration/dagster.yaml) — drop `spark_jobs` storage location, add `dlt_pipelines`
- [backend/orchestration/definitions.py](backend/orchestration/definitions.py) — drop Spark imports + comments
- [scripts/start-dev.sh](scripts/start-dev.sh), [scripts/start-dev.bat](scripts/start-dev.bat) — drop `--no-spark` flag and NO_SPARK logic
- [docker/postgres/tenant-schema.sql](docker/postgres/tenant-schema.sql) — drop `spark_config` column and `SPARK_SUBMIT` enum value (via migration)
- All `.github/agents/*.agent.md`, `.github/prompts/*.md`, and skill files — search-and-replace pass for residual Spark refs
- `docs/requirements/*`, `docs/implementation/*`, `docs/developer/*` — update to dlt + Iceberg
- [backend/scripts/lint_imports.py](backend/scripts/lint_imports.py) — update domain comment Compute/PySpark → Ingestion/dlt

**Alembic migration (single squash for cutover)**
- `DROP TABLE pyspark_apps`.
- ALTER `dag_configs.task_type` enum: remove `SPARK_SUBMIT`, ensure `DLT_RUN` (added in Phase 3).
- DROP COLUMN `spark_config` from tenant configuration tables.
- DELETE FROM `infrastructure_configs` WHERE `service_type='spark'`.

**Verification gate** (all must pass)
- `rg -i "spark|pyspark" --glob '!docs/CHANGELOG*'` returns only intentional historical references.
- `docker-compose up` starts cleanly with no spark services.
- Backend boots with no `SPARK_*` env vars set.
- Full unit + integration + e2e suites green.
- `docs/guides/data-pipelines.md` (new, non-technical) is reviewed.

---

## 5. Cross-cutting concerns

- **Tenant isolation**: every layer (S3 bucket, Iceberg namespace, dbt project pair, CH database, dlt `dataset_name`) carries the tenant slug. Pipelines never receive credentials for another tenant; Dagster ops resolve creds per asset materialization via the tenant's `InfrastructureConfig`.
- **Secrets**: S3 credentials and Postgres catalog DSN are stored encrypted in `InfrastructureConfig.settings` (existing pattern). Never logged. Templates pass them through env vars only.
- **Observability**: dlt run metrics (rows loaded, schema changes) and pyiceberg snapshot ids are recorded in `DltPipeline.last_run_*` columns and emitted as Dagster metadata.
- **Idempotency**: dlt's built-in state (`_dlt_load_id`, `_dlt_pipeline_state`) is stored alongside the Iceberg tables. Re-running a pipeline is safe.
- **Backfill / replay**: an Iceberg table's snapshot history allows time-travel reads; document this in operations docs (Phase 4 follow-up).

---

## 6. Out of scope (this migration)

- REST/Glue Iceberg catalog (Lakekeeper, Polaris, AWS Glue).
- Multi-region buckets.
- dbt-duckdb end-to-end (CH as serving cache only) — see [Open Considerations](#7-open-considerations).
- Side-by-side Spark + dlt operation behind a feature flag.
- Auto-migration of `PySparkApp` rows to `DltPipeline` rows (hard cutover decision).
- Time-travel UI in the wizard.

---

## 7. Open considerations (track separately, do not block this migration)

1. **Future catalog upgrade**: when ClickHouse ships robust Iceberg writes against SQL or REST catalogs, collapse Phase 4 to a single dbt-clickhouse project and retire `dbt-duckdb`. Re-evaluate every 6 months.
2. **History export for tenants with Spark-loaded CH data**: optional one-shot `scripts/export_ch_to_iceberg.py` to backfill the lake from CH before cutover. Mention in the cutover runbook; not required.
3. **S3 lifecycle policies**: Glacier transitions for raw partitions older than N days. Follow-up after Phase 6.
4. **Cost / quota model**: bucket-per-tenant changes the AWS billing surface. Add bucket-level cost tags and a per-tenant storage usage admin view.

---

## 8. Authoritative references

- New agent: [.github/agents/ingestion-agent.agent.md](.github/agents/ingestion-agent.agent.md)
- New skill: [.github/skills/dlt-iceberg/SKILL.md](.github/skills/dlt-iceberg/SKILL.md)
- Phase prompts:
  - [.github/prompts/070-spark-removal-foundation.md](.github/prompts/070-spark-removal-foundation.md)
  - [.github/prompts/071-dlt-pipeline-service.md](.github/prompts/071-dlt-pipeline-service.md)
  - [.github/prompts/072-dagster-dlt-integration.md](.github/prompts/072-dagster-dlt-integration.md)
  - [.github/prompts/073-dbt-dual-adapter.md](.github/prompts/073-dbt-dual-adapter.md)
  - [.github/prompts/074-pipeline-wizard-frontend.md](.github/prompts/074-pipeline-wizard-frontend.md)
  - [.github/prompts/075-spark-removal-cutover.md](.github/prompts/075-spark-removal-cutover.md)

When any doc references "PySpark Apps" or "Spark ingestion", treat this file as the source of truth and update the doc.
