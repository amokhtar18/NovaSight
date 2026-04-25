# Prompt 075 — Spark Removal: Cutover

**Phase**: 6 of 6 in [MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md)
**Owner**: `@infrastructure` + `@orchestrator` (sign-off)
**Depends on**: All prior phase prompts (070–074) merged and verified on staging.

## Context
Final cutover. Hard-delete Spark from the codebase: services, code, frontend, docs, env vars, configs, and the `pyspark_apps` table. **No row migration** — users recreate via the new wizard.

## Pre-flight gate (must all be true before opening this PR)
- [ ] `dlt`-based ingestion working on a staging tenant for at least 7 days.
- [ ] At least one tenant has its `lake/` and `warehouse/` dbt subprojects building cleanly.
- [ ] Playwright e2e green on the new wizard for 3 consecutive nightly runs.
- [ ] Communication sent to all affected tenants explaining the recreate-required flow.

## Deliverables — files to delete
- `infrastructure/spark/` (whole tree)
- `docker/spark/` (whole tree)
- `backend/templates/pyspark/` (3 templates)
- `backend/app/domains/compute/` (whole domain — the rename to `ingestion/` was done in Prompt 071)
- `frontend/src/features/pyspark/`, `frontend/src/pages/pyspark/`, `frontend/src/services/pysparkApi.ts`, `frontend/src/types/pyspark.ts`
- `backend/tests/domains/compute/test_pyspark_service.py`
- `.github/prompts/016-ingestion-dag-generator.md`

## Deliverables — files to edit
- `docker-compose.yml`, `docker-compose.override.yml` — drop `spark-master`, `spark-worker-1`, `spark-worker-2`, their volumes, and any `depends_on: [spark-master]` references.
- `helm/novasight/values*.yaml`, `helm/novasight/templates/NOTES.txt` — drop Spark stanzas.
- `k8s/base/backend/configmap.yaml` — remove all `SPARK_*` env vars.
- `.env.example` — drop `SPARK_*`; ensure `S3_*`, `MINIO_*`, `ICEBERG_CATALOG_URL`, `DAGSTER_DLT_CONCURRENCY_LIMIT` are present.
- `backend/app/config.py` — remove `SPARK_*` settings.
- `backend/app/api/v1/admin/infrastructure.py` — remove `SparkConfigCreateSchema`, all `/settings/spark` endpoints, drop `'spark'` from `CREATE_SCHEMAS` and validation lists.
- `backend/app/domains/tenants/schemas/infrastructure_schemas.py` — remove Spark schema.
- `frontend/src/types/infrastructure.ts` — drop `'spark'` everywhere.
- `backend/app/seed.py` — drop `pyspark_apps` flag, ensure `data_pipelines: True`.
- `backend/app/api/v1/__init__.py` — drop `pyspark_routes` import.
- `backend/app/api/v1/dags.py` — drop deprecated PySpark DAG shims (lines around 31–58).
- `backend/app/domains/orchestration/api/dag_routes.py` — delete `generate_pyspark_dag`, `generate_pyspark_pipeline_dag`, list/get/delete/update PySpark DAG endpoints.
- `backend/app/domains/orchestration/application/unified_job_service.py` — drop PySpark imports/branches.
- `backend/app/domains/orchestration/infrastructure/asset_factory.py` — drop `_build_spark_asset` (already done in Prompt 072 if present).
- `backend/app/platform/tenant/isolation.py` — replace `validate_pyspark_app_ownership` with `validate_pipeline_ownership`.
- `backend/app/models/__init__.py` — drop `PySparkApp`, `PySparkAppStatus`.
- `backend/orchestration/dagster.yaml` — drop `spark_jobs` storage location, add `dlt_pipelines`.
- `scripts/start-dev.sh`, `scripts/start-dev.bat` — drop `--no-spark` flag and `NO_SPARK` logic.
- `docker/postgres/tenant-schema.sql` — drop `spark_config` column and `SPARK_SUBMIT` enum value.
- `backend/scripts/lint_imports.py` — update Compute/PySpark domain comment to Ingestion/dlt.
- `frontend/src/App.tsx` (or routes file) — drop `pyspark` routes; promote `pipelines` routes.
- Sidebar nav — remove "PySpark Apps" entry.
- All `.github/agents/*.agent.md`, `.github/prompts/0[0-6]*.md`, `.github/skills/**/SKILL.md`, `.github/README.md`, `.github/HANDOFF_GUIDE.md`, `.github/handoff.yml` — search-and-replace residual Spark refs (preserve historical changelog references).
- `docs/requirements/*`, `docs/implementation/*`, `docs/developer/*` — update to dlt + Iceberg.

## Alembic migration (single squash)
- `DROP TABLE pyspark_apps;`
- ALTER `dag_configs.task_type` enum: ensure no `SPARK_SUBMIT` left.
- DROP COLUMN `spark_config` from any tenant config tables.
- `DELETE FROM infrastructure_configs WHERE service_type = 'spark';`

## New documentation
- `docs/guides/data-pipelines.md` — non-technical user guide for the new wizard. Match the language used in the wizard exactly.
- Add an entry in `CHANGELOG.md` describing the breaking change and the recreate-required flow.

## Verification gate (PR cannot merge unless all pass)
- [ ] `rg -i "spark|pyspark" --glob '!docs/CHANGELOG*' --glob '!.github/instructions/MIGRATION_SPARK_TO_DLT.md' --glob '!**/migrations/versions/*'` returns zero hits or only intentional historical references.
- [ ] `docker compose up` starts cleanly with no spark services.
- [ ] Backend boots with no `SPARK_*` env var set.
- [ ] Full unit + integration + e2e suites green.
- [ ] Helm chart renders without Spark.
- [ ] `kubectl apply -k k8s/overlays/dev` clean.

## Rollback plan
- This PR is reversible only via `git revert` of the merge commit + Alembic downgrade. The downgrade re-creates `pyspark_apps` empty (no row data is preserved).
- Keep the migration plan and prompts 070–074 in the repo for one minor release after cutover so reviewers can trace history.
