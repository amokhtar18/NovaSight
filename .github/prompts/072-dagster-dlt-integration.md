# Prompt 072 — Dagster Integration for dlt Pipelines

**Phase**: 3 of 6 in [MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md)
**Owner**: `@orchestration` + `@ingestion`
**Depends on**: Prompts 070, 071

## Context
Wire dlt pipelines into Dagster as assets. Add `TaskType.DLT_RUN`. Spark resources/assets/schedules are deleted in this phase (because nothing schedules SPARK_SUBMIT once it's removed); the rest of Spark removal happens in Prompt 075.

## Read first
- [.github/instructions/MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md) §4 Phase 3.
- [.github/skills/dlt-iceberg/SKILL.md](../skills/dlt-iceberg/SKILL.md) §5.
- Existing `backend/orchestration/assets/pyspark_builder.py` (to delete) and `backend/orchestration/resources/spark_resource.py` (to delete).

## Deliverables
1. New `backend/orchestration/assets/dlt_builder.py`:
   - `DltAssetBuilder` reads `DltPipeline` rows for a tenant and emits assets named `dlt_{slug}__{pipeline_name}` grouped by `tenant_{slug}`.
   - The asset op runs `python /opt/dlt/pipelines/{slug}/{name}.py` as a subprocess with env vars per the skill.
   - Captures stdout/stderr to Dagster logs; on non-zero exit, raises `Failure` with the last 2000 chars of stderr.
   - Records `MaterializeResult` metadata: `pipeline_id`, `rows`, `duration_ms`, `iceberg_snapshot_id`.
   - Updates `DltPipeline.last_run_*` columns post-run.
2. New `backend/orchestration/schedules/dlt_schedules.py` (mirrors the deleted PySpark schedules).
3. Update `backend/app/domains/orchestration/domain/models.py` and `schemas/dag_schemas.py`:
   - Replace `TaskType.SPARK_SUBMIT` with `TaskType.DLT_RUN`.
   - Alembic migration to update the `task_type` enum (drop SPARK_SUBMIT, add DLT_RUN); migrate any existing `DagConfig` rows referencing SPARK_SUBMIT (set to DLT_RUN if a corresponding `DltPipeline` exists; otherwise mark `archived`).
4. Delete:
   - `backend/orchestration/resources/spark_resource.py`
   - `backend/orchestration/resources/remote_spark_resource.py`
   - `backend/orchestration/assets/pyspark_builder.py`
   - `backend/orchestration/schedules/pyspark_schedules.py`
   - `_build_spark_asset` branch in `backend/app/domains/orchestration/infrastructure/asset_factory.py`
5. Update `backend/orchestration/definitions.py` to load dlt assets/schedules; remove Spark imports/comments.
6. Rename env var `DAGSTER_SPARK_CONCURRENCY_LIMIT` → `DAGSTER_DLT_CONCURRENCY_LIMIT` (in `.env.example`, `backend/app/config.py`, K8s configmaps, Helm values).

## Tests
- Unit: `DltAssetBuilder.build()` produces an `AssetsDefinition` with the expected name and group.
- Integration: end-to-end `materialize_assets()` for a sample pipeline against MinIO; assert `last_run_status='success'` and rows updated.
- Migration: alembic upgrade head + downgrade -1 round-trip clean.

## Definition of done
- Dagster UI shows a `tenant_{slug}` group containing the new dlt asset(s).
- Triggering a run materializes the Iceberg table.
- No `spark_resource`, `pyspark_builder`, `pyspark_schedules` imports anywhere; tests pass.
- `TaskType.SPARK_SUBMIT` no longer referenced (except in the migration history).
