# Prompt 074 — Data Pipeline Wizard (4-step, Non-Technical Users)

**Phase**: 5 of 6 in [MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md)
**Owner**: `@frontend`
**Depends on**: Prompt 071 (API contract)

## Context
Replace the 6-step PySpark App Wizard with a **4-step plain-language Data Pipeline Wizard**. The target persona is a non-technical analyst — no "SCD", "CDC", "MergeTree", or "write mode" jargon in primary UI. All those concepts still exist in code, schemas, and admin views. The PySpark UI remains in place until Phase 6 (Prompt 075).

## Read first
- [.github/instructions/MIGRATION_SPARK_TO_DLT.md](../instructions/MIGRATION_SPARK_TO_DLT.md) §4 Phase 5.
- [.github/skills/dlt-iceberg/SKILL.md](../skills/dlt-iceberg/SKILL.md) §6 (wizard mapping table).
- Existing wizard for reference: `frontend/src/features/pyspark/components/*.tsx`.

## Deliverables
1. New folder structure:
   - `frontend/src/features/pipelines/`
   - `frontend/src/pages/pipelines/PipelinesListPage.tsx`, `PipelineBuilderPage.tsx`, `PipelineDetailPage.tsx`
   - `frontend/src/services/pipelinesApi.ts`
   - `frontend/src/types/pipeline.ts`
   - Update `frontend/src/types/index.ts`, router, sidebar.
2. Wizard 4 steps:
   - **Step 1 — "What data do you want to copy?"**
     - One-click connection picker (re-use `useDataSources()`).
     - Searchable schema-table tree; default-expand most-recently-used schema.
     - "Advanced: write a query" toggle hides the Monaco SQL textarea + Validate button.
   - **Step 2 — "Which columns, and how should we keep it fresh?"**
     - Default: all columns selected. Collapsible "Customize columns" reuses the existing column-picker UI.
     - Three plain-language radios. Map to API:
       - "Replace everything each time" → `write_disposition='replace'`.
       - "Add only new rows" → `write_disposition='append'` + auto-detect `incremental_cursor_*` (first timestamp/serial column wins; user can override via "Advanced").
       - "Keep history of changes" → `write_disposition='scd2'` + auto-suggested `primary_key_columns` from connection schema metadata; user confirms.
     - Never display the literal terms "append", "replace", "scd2", "merge", "CDC", "SCD".
   - **Step 3 — "Where should it go?"**
     - Auto-fills `pipeline_name` and `iceberg_table_name` from the source table name (snake_case).
     - Shows: *"Will be saved to your data lake (Iceberg) and made available for analytics in ClickHouse."*
     - "Advanced" disclosure exposes pipeline name + Iceberg table name + namespace override (greyed unless user has admin permission).
   - **Step 4 — "Review & save"**
     - Plain-English summary template:
       *"This pipeline will copy* {table} *from your* {connection.name} *database every time it runs, {strategy_phrase}. New data will be available in ClickHouse as `{ch_database}.{ch_table}`."*
     - "Advanced: view generated code" disclosure mounts a Monaco read-only editor populated by `POST /api/v1/pipelines/preview`.
     - Primary action: **Save & schedule** — calls Create, then Activate, then opens the existing schedule picker.
3. Auto-derived rules (no UI surface):
   - CH engine: `replace` → `MergeTree`; `append` → `MergeTree`; `scd2` → `VersionedCollapsingMergeTree`. Send to API; do not show user.
   - Target DB: tenant-derived from `useCurrentTenant()`.
   - Iceberg namespace: `tenant_{slug}.raw`.
4. List page: title **"Data Pipelines"**. Action labels: **Run now / Pause / Edit / Delete**. Drop the "Generate Code" primary action. Status badges: Draft / Active / Paused / Error.
5. Detail page: lead row is a freshness card (last-run-at, rows, status, "Run now" button). Code/template metadata in a collapsible "Advanced" section.
6. In-app help: each step header has a one-sentence explainer + an info icon linking to `docs/guides/data-pipelines.md` (created in Prompt 075).
7. i18n: add a `pipelines` namespace; do not yet remove the `pyspark` namespace.
8. Feature flag: add `data_pipelines` (default true). Hide the new menu item if false. Do not yet remove the `pyspark_apps` flag — Prompt 075 handles that.

## Accessibility & UX guardrails
- WCAG 2.1 AA for all step cards and radio groups.
- Keyboard-only completion of the wizard from start to finish.
- All radios have a one-line explanation under the label, not in a tooltip.
- The freshness-strategy radio choices are visually equally weighted (no "recommended" badge unless we have data to justify it).

## Tests
- Vitest unit tests for the freshness mapping helper (`mapStrategyToWriteDisposition`).
- Playwright e2e: a non-technical persona test creates → saves → runs → sees data in CH within 10 minutes; no docs opened.
- Snapshot test of the Step 4 summary sentence for each strategy.

## Definition of done
- New menu entry "Data Pipelines" is visible and functional behind the `data_pipelines` flag.
- Old "PySpark Apps" menu still present and functional.
- Playwright e2e green.
- No frontend code references `'spark'`, `'pyspark'`, `'CDC'`, `'SCD'` in user-visible strings.
