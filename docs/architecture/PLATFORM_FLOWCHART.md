# NovaSight Platform — End-to-End Flowchart

> Source-of-truth diagram for the NovaSight platform flow.
> Keep this file in sync with any architectural change. Edit the Mermaid block below.

## Flow

```mermaid
flowchart TD
    Start([User opens NovaSight]) --> Login{Authenticated?}
    Login -- No --> AuthFlow[Login + MFA<br/>JWT issued with tenant_id]
    AuthFlow --> Dashboard
    Login -- Yes --> Dashboard[Tenant Workspace]

    Dashboard --> Choice{What to do?}

    %% ==== CONNECTION PATH ====
    Choice -- Add data source --> ConnNew[Connection Wizard]
    ConnNew --> ConnTest[POST /connections/test<br/>verify reachability]
    ConnTest --> ConnOK{Reachable?}
    ConnOK -- No --> ConnErr[Show error] --> ConnNew
    ConnOK -- Yes --> ConnIntro[GET /connections/schema<br/>introspect tables]
    ConnIntro --> ConnSave[POST /connections<br/>encrypt creds + persist]
    ConnSave --> Dashboard

    %% ==== PIPELINE CREATION ====
    Choice -- Create pipeline --> Wiz[Pipeline Wizard 4 steps:<br/>source - tables - schedule - review]
    Wiz --> Validate[Backend: Pydantic validation]
    Validate --> Tpl[Template Engine<br/>render dlt + Dagster + dbt<br/>from approved Jinja2]
    Tpl --> Register[Register Dagster job + schedule<br/>Persist Pipeline row in Postgres]
    Register --> RunChoice{Run now?}
    RunChoice -- No --> Dashboard
    RunChoice -- Yes --> Trigger

    %% ==== PIPELINE RUN ====
    Trigger[POST /pipelines/id/run] --> Dagster[Dagster launches job]
    Dagster --> Extract[dlt: extract from source<br/>incremental cursor]
    Extract --> Land[Write Parquet to<br/>s3://novasight-tenant-id/raw/]
    Land --> IceCommit[Commit Iceberg snapshot<br/>in Postgres catalog]
    IceCommit --> DbtLake[dbt-duckdb: stage + clean<br/>reads Iceberg in place]
    DbtLake --> DbtMart[dbt-clickhouse: build marts]
    DbtMart --> CHWrite[Write to ClickHouse<br/>db tenant_id]
    CHWrite --> QC{Quality checks pass?}
    QC -- No --> Alert[Emit alert + audit<br/>mark run FAILED]
    Alert --> Dashboard
    QC -- Yes --> Done[Mark run SUCCESS<br/>emit metrics + lineage]
    Done --> Dashboard

    %% ==== ANALYTICS PATH ====
    Choice -- Build dashboard --> Chart[Chart builder / SQL editor]
    Chart --> QueryAPI[POST /query/sql or<br/>GET /charts/id/data]
    QueryAPI --> Guard[Inject tenant_id<br/>RBAC + read-only + row cap]
    Guard --> CHRead[(ClickHouse:<br/>SELECT FROM tenant_id.mart)]
    CHRead --> Render[Return rows + chart spec]
    Render --> Dashboard

    %% ==== AI PATH ====
    Choice -- Ask in natural language --> Ask[POST /ai/ask question]
    Ask --> Ctx[Load tenant schema +<br/>dbt semantic layer]
    Ctx --> LLM[Ollama: NL to SQL]
    LLM --> SQLVal{SQL valid<br/>and read-only?}
    SQLVal -- No --> Reject[Return explanation<br/>no execution] --> Dashboard
    SQLVal -- Yes --> Guard
    Guard --> CHRead

    %% ==== CROSS-CUTTING ====
    Trigger -. audit .-> Audit[(Audit log<br/>Postgres)]
    ConnSave -. audit .-> Audit
    QueryAPI -. audit .-> Audit
    Ask -. audit .-> Audit
    Dagster -. metrics/logs .-> Obs[(Prometheus + Loki<br/>Grafana)]
    Extract -. metrics .-> Obs
    CHRead -. metrics .-> Obs

    classDef store fill:#e8f0ff,stroke:#3b6,stroke-width:1px;
    classDef danger fill:#ffe8e8,stroke:#c33;
    classDef ok fill:#e8ffe8,stroke:#3a3;
    class CHRead,Audit,Obs store;
    class Alert,Reject,ConnErr danger;
    class Done ok;
```

## Notes

- **Tenant isolation**: `tenant_id` is taken from the JWT and enforced at every store boundary
  (Postgres RLS, S3 bucket-per-tenant, Iceberg namespace `tenant_{id}`, ClickHouse DB `tenant_{id}`).
- **Template Engine Rule**: pipeline artifacts (dlt, Dagster, dbt) are only generated from
  pre-approved Jinja2 templates with Pydantic-validated inputs. No arbitrary code paths.
- **Read-only guard**: SQL editor and AI NL2SQL outputs are parsed (sqlglot), forced to
  `SELECT`, capped in rows, and pinned to the tenant's ClickHouse database.

## Maintenance

When the architecture changes, update the Mermaid block above in the same PR.
Companion documents:

- [Blueprint overview](./PLATFORM_BLUEPRINT.md) *(create if/when needed)*
- [Architecture decisions](../requirements/Architecture_Decisions.md)
- [Spark → dlt migration](../../.github/instructions/MIGRATION_SPARK_TO_DLT.md)
