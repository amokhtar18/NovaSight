# Prompt 071 — dlt Pipeline Service & Code Generation

**Phase**: 2 of 6 in [MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md)
**Owner**: `@ingestion` + `@template-engine`
**Depends on**: Prompt 070

## Context
Build the dlt-based ingestion domain that will replace `PySparkApp`. The `pyspark_apps` table and PySpark code remain untouched in this phase; both are removed in Phase 6 (Prompt 075).

## Read first
- [.github/instructions/MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md) §4 Phase 2.
- [.github/agents/ingestion-agent.agent.md](../agents/ingestion-agent.agent.md).
- [.github/skills/dlt-iceberg/SKILL.md](../skills/dlt-iceberg/SKILL.md) §3, §4, §7.

## Deliverables
1. Create domain `backend/app/domains/ingestion/`:
   - `domain/models.py` — `DltPipeline` SQLAlchemy model + Alembic migration creating `dlt_pipelines` table (per the canonical data model in the agent file).
   - `schemas/dlt_schemas.py` — Pydantic Create/Update/Response/Preview schemas.
   - `application/dlt_pipeline_service.py` — CRUD + `generate_code()` + `preview_code()` + `run_now()` (delegates to Dagster trigger from Phase 3 prompt; for now returns 202 with a TODO).
   - `api/dlt_routes.py` — endpoints under `/api/v1/pipelines/...` mirroring the previous PySpark surface (list/get/create/update/delete/preview/generate/activate/deactivate/run).
2. Templates under `backend/templates/dlt/`:
   - `extract_pipeline.py.j2` (`write_disposition` ∈ {append, replace}).
   - `merge_pipeline.py.j2` (`write_disposition=merge`, requires PK).
   - `scd2_pipeline.py.j2` (`write_disposition=scd2`, requires PK).
   - All MUST follow the canonical shape from the agent file. Tenant ID, namespace, bucket are env-var driven.
3. Update `backend/app/services/template_engine/validator.py`:
   - Add `Dlt*Definition` Pydantic schemas per the skill.
   - Register the three templates in `TEMPLATE_VALIDATORS`.
   - Forbidden-patterns regex applied to rendered output.
4. Update `backend/app/services/template_engine/engine.py` — register the three templates.
5. Generated code path: write rendered pipelines to `/opt/dlt/pipelines/{tenant_slug}/{pipeline_name}.py` and store the source on `DltPipeline.generated_code` (TEXT) with a `code_hash`.
6. Register the new blueprint in `backend/app/api/v1/__init__.py`. Do not yet remove the PySpark blueprint.

## Tests
- Unit: render each template against a fixture; assert presence of `iceberg(...)`, the correct namespace string, no hard-coded creds, no banned imports.
- Validator tests: reject namespace mismatch, missing PK on `merge`/`scd2`, AWS-key-shaped strings, `os.system` calls.
- Integration: against MinIO + local Postgres catalog, run a rendered pipeline against a SQLite source; assert Iceberg table exists and row counts match.
- Tenant isolation: rendering with `tenant_slug='a'` must not produce code referring to slug `'b'`.

## Definition of done
- `pytest -q tests/services/template_engine tests/domains/ingestion` green.
- `POST /api/v1/pipelines/preview` returns generated code for a sample config.
- `pyspark_apps` table and PySparkApp endpoints still functional (no regression).
- No Spark code modified.
