# Prompt 070 — Spark Removal: Foundation (Storage, Catalog, SDKs)

**Phase**: 1 of 6 in [MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md)
**Owner**: `@infrastructure` + `@backend`
**Skill**: [dlt-iceberg](../skills/dlt-iceberg/SKILL.md)

## Context
We are replacing Spark with dlt + Iceberg-on-S3 + dbt(DuckDB→ClickHouse). This phase lays the foundation: per-tenant S3 buckets, a Postgres-backed Iceberg SQL catalog, MinIO for dev, the `iceberg_catalog` helper, and required Python deps. **No user-visible changes yet. Do not touch the wizard or remove Spark in this phase.**

## Read first
1. [.github/instructions/MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md) §4 Phase 1.
2. [.github/skills/dlt-iceberg/SKILL.md](../skills/dlt-iceberg/SKILL.md) §1, §2.
3. Existing pattern: `backend/app/api/v1/admin/infrastructure.py` (ClickHouse config CRUD).

## Deliverables
1. Add to `backend/requirements.txt`:
   - `dlt[clickhouse,filesystem,pyarrow,sql_database]==<latest stable>`
   - `pyiceberg[sql,s3fs]==<latest stable>`
   - `dbt-duckdb==<latest matching dbt-core 1.8.x>`
   Pin versions, regenerate the lock file if used.
2. Alembic migration `add_iceberg_catalog_schema.py`: `CREATE SCHEMA IF NOT EXISTS iceberg_catalog;` plus grants for the platform service role. Pyiceberg auto-creates its tables on first call.
3. New Pydantic schema `S3StorageSettings` in `backend/app/domains/tenants/schemas/infrastructure_schemas.py`, plus `service_type='object_storage'` enum value.
4. Admin endpoints in `backend/app/api/v1/admin/infrastructure.py`:
   - `GET /infrastructure/configs?service_type=object_storage&tenant_id=...`
   - `POST /infrastructure/configs/object_storage` (per-tenant required)
   - `PUT /infrastructure/configs/{id}`
   - `POST /infrastructure/configs/{id}/test` — runs `head_bucket` + write/delete probe at `prefix/.healthcheck`.
5. `ProvisioningService.provision_tenant_bucket()` in `backend/app/domains/tenants/infrastructure/provisioning.py`:
   - Dev (MinIO): create bucket if not exists.
   - Prod: validate existence + required permissions; raise actionable error otherwise.
6. New module `backend/app/platform/lake/iceberg_catalog.py` with `get_catalog_for_tenant()` and `ensure_namespace()` per the skill.
7. Add `minio` service to `docker-compose.yml` and an init script (`docker/minio/init-buckets.sh`) that creates buckets for tenants seeded in `backend/app/seed.py`.
8. Add env vars to `.env.example`: `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `ICEBERG_CATALOG_URL`, `S3_DEFAULT_REGION`. Do NOT remove `SPARK_*` yet (Phase 6).
9. Update `backend/app/config.py`: add `ICEBERG_CATALOG_URL`, `OBJECT_STORAGE_DEFAULT_REGION`. Leave Spark config in place.

## Tests
- Unit: `tests/platform/lake/test_iceberg_catalog.py` — given a fake `InfrastructureConfig`, returns a properly configured `SqlCatalog`; `ensure_namespace` is idempotent.
- Unit: `tests/domains/tenants/test_object_storage_config.py` — schema validation accepts MinIO-style configs and rejects bad bucket names.
- Integration: `tests/integration/test_provisioning_bucket.py` — against MinIO in compose, end-to-end provision + namespace + write-and-read a 3-row pyarrow table.

## Definition of done
- `docker-compose up minio` healthy; init script creates seed-tenant buckets.
- `pytest -q tests/platform/lake tests/integration/test_provisioning_bucket.py` green.
- No Spark code touched. No frontend changes. No PySparkApp model changes.
- Phase-1 PR description links this prompt and the migration doc.
