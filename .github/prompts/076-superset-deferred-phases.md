# Prompt 076 — Apache Superset Integration: Deferred Phases (4–6, 8, 9, 10)

**Phase**: 2 of 2 in the Apache Superset Integration Plan v2.
**Owner**: `@backend-agent` + `@frontend-agent` + `@security-agent` (sign-off) + `@testing-agent` (E2E).
**Depends on**: PR `copilot/develop-integration-plan-superset` merged. That PR shipped Phases 1, 2, 2b, 3 and 7 (scaffolding, AI Workbench, Superset proxy under feature flag, tenant lifecycle hook, mutators, security bridge, AI Workbench tabs).

## Context

Phase 1 of the integration shipped the additive scaffolding only. Apache Superset is now a pinned, optional pip dependency (`apache-superset==6.0.0`, see `backend/requirements-superset.txt`), runs as a sidecar service under the `superset` Docker Compose profile, and is reachable through `/api/v1/superset/*` when `SUPERSET_ENABLED=true`. The bridge code (`backend/app/domains/analytics/superset/`), AI Workbench UI (`frontend/src/features/query/`), and per-tenant ClickHouse provisioning are already in place but **no existing user-facing flow has been moved to Superset yet** — `chartService.ts`, `useDashboards.ts`, and the SQL Editor still use the legacy NovaSight tables.

This prompt closes the loop: rewire chart / dashboard / SQL-Lab persistence to Superset behind a per-tenant feature flag, finalise the tenant ClickHouse lockdown, prove the end-to-end journey with Playwright, then deprecate the legacy storage.

## Pre-flight gate (must all be true before opening any PR for this prompt)

- [ ] PR merged with `apache-superset==6.0.0` pinned and CodeQL passing.
- [ ] `docker compose --profile superset up -d` brings up `superset`, `superset-mcp`, and the existing `postgres` / `redis` / `clickhouse` cleanly on a developer machine.
- [ ] `SUPERSET_ENABLED=true` boots the Flask backend without errors and `/api/v1/superset/health` proxies through to Superset's `/health`.
- [ ] At least one tenant exists in dev with a non-empty ClickHouse database and at least one mart materialised by dbt.
- [ ] `redis-cli info keyspace` shows existing NovaSight keys only on `db0` / `db1`; Superset will populate `db2`–`db5`.

## Hard constraints (carry forward from Plan v2)

1. **Zero functional edits** to existing domains: `identity`, `datasources`, `ingestion`, `transformation`, `orchestration`, `tenants`, `platform`. Only the files listed under "Deliverables — files to edit" below may be touched.
2. **No vendored Superset source tree.** Customisation continues to go through public Superset extension points (`CUSTOM_SECURITY_MANAGER`, `DB_CONNECTION_MUTATOR`, `BLUEPRINTS`, `FLASK_APP_MUTATOR`).
3. **Every Superset query must target the caller's tenant ClickHouse DB only.** Three layers stay enforced: tenant provisioner, `db_connection_mutator`, FAB role map.
4. **React routes do not change.** `/app/charts`, `/app/dashboards`, `/app/sql-editor`, `/app/query` keep their paths and their public TypeScript service signatures.
5. **Per-tenant rollout.** Phases 4–6 must ship behind `FEATURE_SUPERSET_BACKEND` (boolean, per-tenant) so the legacy and Superset paths can coexist while we migrate.
6. **Error responses must not leak exception detail.** Per repo memory: log `str(exc)` server-side, return a static user message in the JSON body. Applies to every new endpoint added by this prompt.

---

## Phase 4 — Charts: rewire `chartService.ts` to Superset (`@frontend-agent`)

### Goal
`ChartBuilderPage`, `ChartListPage`, `DashboardPage` work unchanged but their underlying chart rows live in Superset's `slices` table. The TypeScript public API of `chartService.ts` must not change.

### Backend
- New thin endpoints under `backend/app/domains/analytics/superset/` (additive only):
  - `GET    /api/v1/superset/charts` → proxy to Superset `GET /api/v1/chart/`, scoped by `tenant_id`.
  - `POST   /api/v1/superset/charts` → proxy to `POST /api/v1/chart/`, server-side injects `database_id = tenant_database_id`.
  - `GET    /api/v1/superset/charts/<id>` / `PUT` / `DELETE` — standard CRUD, all tenant-scoped.
  - `POST   /api/v1/superset/charts/<id>/data` → proxy to Superset's `/api/v1/chart/<id>/data/` for live results.
- Mapping helpers in a new `backend/app/domains/analytics/superset/chart_mapper.py` translating between NovaSight chart payloads (existing `frontend/src/types/chart.ts`) and Superset `slice` payloads. Pure functions, fully unit-tested.
- Use the `FEATURE_SUPERSET_BACKEND` flag (read from tenant settings) to gate the new routes in `proxy_routes.py`.

### Frontend
- Edit `frontend/src/services/chartService.ts` only — its internals re-route to `supersetService.ts` when the tenant flag is on. Public function signatures (`listCharts`, `getChart`, `createChart`, `updateChart`, `deleteChart`, `runChartQuery`) MUST be byte-identical to today.
- Add adapter functions converting `NovaSightChartConfig` ↔ Superset slice JSON. Keep them in `frontend/src/services/supersetService.ts` (already created in Phase 1).
- No edits in `pages/charts/*`, `features/charts/*`, or any consumer of `chartService.ts`.

### Tests
- Unit: chart mapper round-trips for every chart type currently supported (`bar`, `line`, `area`, `pie`, `table`, `big_number`, `scatter`, `treemap`).
- Integration (`backend/tests/integration/test_superset_charts.py`): with a mocked Superset API, verify CRUD + data fetch.
- Frontend: existing `__tests__/chartService.test.ts` must still pass without modification.

### Acceptance
- Toggle `FEATURE_SUPERSET_BACKEND=true` for one tenant. Open `/app/charts`, build a new chart, save, edit, delete. UI behaviour identical to today; row appears in `superset.slices` (and **not** in the legacy NovaSight `charts` table).
- Toggle off: same flows still go through the legacy code path.

---

## Phase 5 — Dashboards: rewire `useDashboards.ts` (`@frontend-agent`)

### Goal
Dashboards persist in Superset's `dashboards` + `dashboard_slices` tables; existing `react-grid-layout`-based renderer is reused.

### Backend
- New proxy routes:
  - `GET / POST  /api/v1/superset/dashboards`
  - `GET / PUT / DELETE  /api/v1/superset/dashboards/<id>`
  - `GET  /api/v1/superset/dashboards/<id>/charts`
- Layout translation helper `dashboard_mapper.py`: NovaSight `react-grid-layout` JSON ↔ Superset `position_json`. Symmetrical, pure functions.

### Frontend
- Edit `frontend/src/features/dashboards/hooks/useDashboards.ts` only. Public hook return shape unchanged.
- Reuse the existing dashboard renderer; just feed it from the proxy.

### Tests
- Unit: layout round-trip for at least 3 representative real dashboards captured from staging (anonymise tenant IDs).
- Integration: dashboard CRUD against mocked Superset.
- Visual regression: existing Storybook / RTL snapshots for `DashboardPage` continue to match.

### Acceptance
- Create dashboard, drag/drop charts, resize, save, reload. Layout persists round-trip.
- Cross-tenant test: tenant B cannot read tenant A's dashboards even with a forged ID.

---

## Phase 6 — SQL Editor: route execute → Superset SQL Lab (`@frontend-agent` + `@backend-agent`)

### Goal
The SQL Editor (`/app/sql-editor`) keeps its UI but executes against Superset's `/api/v1/sqllab/execute/`, with results delivered through Superset's RESULTS_BACKEND (Redis db=2).

### Backend
- New routes:
  - `POST /api/v1/superset/sqllab/execute` — synchronous and async modes; returns `query_id` for async.
  - `GET  /api/v1/superset/sqllab/results/<key>` — fetch results from Redis-backed RESULTS_BACKEND.
  - `POST /api/v1/superset/sqllab/estimate` — query cost estimate (Superset-native).
- Reject any payload whose target `database_id` is not the caller's tenant DB. Defence in depth even though `db_connection_mutator` already covers it.

### Frontend
- Edit `frontend/src/features/sql-editor/hooks/useSqlExecution.ts` (or equivalent) only. Keep saved-query / history hooks as-is for now (they still talk to NovaSight); they will be migrated in Phase 10.

### Tests
- Integration: `SELECT 1`, `SELECT * FROM <mart>` against the seeded tenant CH DB, simulated long-running query (async), forged cross-tenant `database_id` → 403.

### Acceptance
- Run a query in the SQL Editor → spinner → results table renders identically.
- Cancel a long-running query stops execution at Superset.
- `redis-cli -n 2 keys "superset_results_*"` shows the cached rows.

---

## Phase 8 — Tenant ClickHouse lockdown: finalisation (`@security-agent`)

### Goal
End users provably cannot register, edit, or impersonate any database other than their tenant's ClickHouse DB.

### Deliverables
- `backend/app/domains/analytics/superset/permissions.py` — boot-time hook (registered via `FLASK_APP_MUTATOR` in `superset_config.py`) that, for every non-`Admin` FAB role, **revokes** the following permissions:
  - `can_add` / `can_edit` / `can_delete` on `Database`.
  - `can_csv_upload`, `can_excel_upload`.
  - `database_access` for any database whose `extra.tenant_id` is not the user's tenant.
- Idempotent — runs on every Flask boot.
- Negative-test pytest: any non-Admin user calling `POST /api/v1/database/` against the embedded Superset gets `403`.
- Mutator unit tests must additionally cover: URI without `/`, URI with query-string, URI with embedded credentials whose host is not the configured ClickHouse host (must reject), URI mutation that strips a trailing `/?param=` cleanly.

### Acceptance
- Superset audit log for one tenant over a 24-hour soak shows zero queries against any database other than `tenant_<slug>_clickhouse`.
- Every entry in the audit log has a non-null `tenant_id` in its `extra` JSON.

---

## Phase 9 — End-to-end Playwright (`@testing-agent`)

### Goal
A single Playwright spec proves the full journey through the unchanged React routes.

### File
`frontend/tests/e2e/superset-integration.spec.ts`.

### Scenario (single tenant, fixture-seeded)
1. Login at `/login`.
2. Navigate `/app/datasources` — create a Postgres datasource (use the existing test fixture container).
3. Navigate `/app/pipelines` — create a dlt pipeline against that datasource.
4. Navigate `/app/jobs` — schedule it; wait for one successful run.
5. Navigate `/app/dbt-studio` — run a mart that materialises into the tenant CH DB.
6. Navigate `/app/sql-editor` — `SELECT * FROM <mart> LIMIT 5` and assert at least one row.
7. Navigate `/app/charts` — build a `bar` chart against that mart, save.
8. Navigate `/app/dashboards` — create a dashboard, add the chart, save, reload, assert layout persists.
9. Navigate `/app/query` — run an "Ask" tab NL query that should resolve to the mart; assert non-empty result.
10. (Negative) attempt to call `POST /api/v1/superset/charts` with `database_id` of another tenant → assert `403`.

### CI
- Add a `superset-e2e` job in `.github/workflows/ci.yml` that:
  - Uses Docker Compose with `--profile superset`.
  - Runs Alembic migrations including the AI Workbench migration `f5d8a1c20b3e`.
  - Seeds two tenants and the fixture mart.
  - Runs only this Playwright spec on every PR that touches `backend/app/domains/analytics/superset/`, `frontend/src/services/supersetService.ts`, or `frontend/src/features/query/`.

### Acceptance
- Spec is green on three consecutive nightly runs.
- Average run time < 12 min wall-clock.

---

## Phase 10 — Cleanup: deprecate legacy chart/dashboard/saved-query storage (`@backend-agent`)

**Ship in a separate follow-up PR after Phase 9 is green for ≥ 2 weeks.** This phase is the only one in the prompt that **deletes existing code**.

### Steps (PR 1 — soft deprecate)
- Mark legacy SQLAlchemy models (`Chart`, `Dashboard`, `DashboardChart`, `SavedQuery`) with a `DeprecationWarning` on instantiation.
- Backend log line on every legacy endpoint hit: `"legacy chart/dashboard endpoint hit, will be removed"`.

### Steps (PR 2 — hard delete, only after 100 % of tenants are on `FEATURE_SUPERSET_BACKEND=true` for ≥ 30 days)
- Files to delete:
  - `backend/app/domains/analytics/charts/*` legacy CRUD (keep the domain module; only legacy storage classes go).
  - `backend/app/domains/analytics/dashboards/legacy/*` if present.
  - `backend/app/api/v1/charts_legacy.py`, `dashboards_legacy.py`, `saved_queries_legacy.py` (only if they exist after the first PR's renames).
  - `frontend/src/services/__legacy__/chartService.legacy.ts` (if introduced during Phase 4).
- Alembic migration:
  - `DROP TABLE charts, dashboards, dashboard_charts, saved_queries;` (verify each table is empty first via a guard migration).
- Delete `FEATURE_SUPERSET_BACKEND` flag plumbing: tenant settings, backend reads, frontend reads. Superset becomes the only path.

### Acceptance
- `pg_stat_user_tables` shows the legacy tables are gone.
- `grep -ri "FEATURE_SUPERSET_BACKEND" backend frontend` returns zero matches.
- All existing pytest / Playwright suites still green.

---

## Files this prompt is allowed to edit (whole-prompt allow-list)

### New files
```
backend/app/domains/analytics/superset/chart_mapper.py
backend/app/domains/analytics/superset/dashboard_mapper.py
backend/app/domains/analytics/superset/permissions.py
backend/app/domains/analytics/superset/sqllab_routes.py     # if split out from proxy_routes
backend/tests/integration/test_superset_charts.py
backend/tests/integration/test_superset_dashboards.py
backend/tests/integration/test_superset_sqllab.py
backend/tests/integration/test_superset_permissions.py
backend/tests/unit/test_chart_mapper.py
backend/tests/unit/test_dashboard_mapper.py
frontend/tests/e2e/superset-integration.spec.ts
```

### Edited files (small, surgical diffs only)
```
backend/app/domains/analytics/superset/proxy_routes.py        # add chart/dashboard/sqllab routes
backend/app/domains/analytics/superset/superset_config.py     # FLASK_APP_MUTATOR for permissions hook
backend/app/domains/analytics/superset/mutators.py            # extra negative-case coverage
frontend/src/services/chartService.ts                         # internal re-route
frontend/src/services/supersetService.ts                      # mapper wiring
frontend/src/features/dashboards/hooks/useDashboards.ts       # internal re-route
frontend/src/features/sql-editor/hooks/useSqlExecution.ts     # internal re-route
.github/workflows/ci.yml                                      # superset-e2e job
```

Anything outside this list is out of scope and must be handled in a separate PR.

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Superset upgrade (e.g. 6.x → 6.y) breaks chart/dashboard payload shapes | Mappers are version-pinned and round-trip-tested; bump in a dedicated PR |
| Per-tenant flag drift creates dual-storage divergence | Phase 10 PR 2 is gated on `FEATURE_SUPERSET_BACKEND=true` for 100 % of tenants for 30 days |
| FAB permission hook regresses on Superset minor upgrades | Idempotent + explicit allow-list; covered by `test_superset_permissions.py` |
| Async SQL Lab results not available because Redis db=2 evicted | `RESULTS_BACKEND` already uses dedicated key prefix; raise the keyspace `maxmemory-policy` to `volatile-lru` only on db=2 if eviction observed |
| Cross-tenant data leak via forged `database_id` | Three layers: provisioner allow-list + `db_connection_mutator` + per-route assertion in proxy |

## Definition of done

- [ ] Phases 4, 5, 6, 8, 9, 10-PR-1 are merged.
- [ ] Phase 10-PR-2 is merged after the 30-day soak.
- [ ] All Plan v2 success criteria (§ 11) are demonstrably met:
  - Existing NovaSight backend domains still have zero functional edits.
  - The full flow login → datasource → pipeline → schedule → dbt model → SQL Lab → chart → dashboard works through current React routes.
  - Superset, MCP, and Ollama remain configurable from `/app/query`.
  - Audit log shows tenant-only queries.
  - Redis keyspace cleanly partitioned.
  - `requirements.txt` family contains only the pinned `apache-superset` library; no Superset source tree in the repo.
