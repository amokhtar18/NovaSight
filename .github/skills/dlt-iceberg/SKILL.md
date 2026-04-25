# dlt + Iceberg Skill

## Description
Patterns for generating tenant-isolated **dlt** pipelines that land data in **Apache Iceberg** tables on **per-tenant S3 buckets**, registered in a **Postgres-backed SQL catalog**. Replaces the deprecated PySpark ingestion patterns.

## When to apply
- Generating a new ingestion pipeline (dlt template).
- Adding a `write_disposition` (append / replace / merge / scd2).
- Provisioning a tenant's S3 bucket + Iceberg namespace.
- Wiring a Dagster asset that runs a generated dlt pipeline.
- Reviewing tenant isolation in ingestion code.

## Authoritative spec
Always read [MIGRATION_SPARK_TO_DLT.md](../../instructions/MIGRATION_SPARK_TO_DLT.md) first. This skill is the practical "how"; that doc is the architectural "what" and "why".

---

## 🔒 Hard rules

1. **Template Engine Rule applies**: dlt pipeline source files are rendered from `backend/templates/dlt/*.j2` with Pydantic-validated inputs. Never write a `.py` pipeline by hand.
2. **One bucket per tenant. Always.** Pipelines read `TENANT_S3_BUCKET_URL` from env; the URL is resolved per Dagster materialization from the tenant's `InfrastructureConfig` of type `object_storage`.
3. **Namespace is `tenant_{slug}.raw`**. The validator rejects any other namespace.
4. **No credentials in templates**. All secrets pass through env vars injected by the Dagster runner.
5. **No cross-tenant data flow**. The pipeline cannot read its own tenant context from the platform DB at runtime — it gets `TENANT_ID` and creds from env, nothing else.

---

## 1. Per-tenant S3 storage configuration

```python
# backend/app/domains/tenants/schemas/infrastructure_schemas.py
class S3StorageSettings(BaseModel):
    """Per-tenant object storage. Always required when service_type='object_storage'."""
    bucket: str = Field(..., min_length=3, max_length=63)
    region: str = "us-east-1"
    endpoint_url: Optional[str] = None         # MinIO / non-AWS S3
    path_style: bool = False                   # True for MinIO
    access_key: SecretStr
    secret_key: SecretStr
    prefix: str = ""                           # Optional sub-prefix inside the bucket
    kms_key_id: Optional[str] = None           # Server-side encryption

    @validator("bucket")
    def _bucket_naming(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9][a-z0-9.\-]{1,61}[a-z0-9]$", v):
            raise ValueError("Invalid S3 bucket name")
        return v
```

Admin endpoints follow the existing ClickHouse pattern in `backend/app/api/v1/admin/infrastructure.py`:
- `GET /api/v1/admin/infrastructure/configs?service_type=object_storage&tenant_id=...`
- `POST /api/v1/admin/infrastructure/configs/object_storage`
- `POST /api/v1/admin/infrastructure/configs/{id}/test` (calls `head_bucket` + a write/delete probe under `prefix/.healthcheck`)

---

## 2. Iceberg SQL catalog (Postgres-backed)

```python
# backend/app/platform/lake/iceberg_catalog.py
from pyiceberg.catalog.sql import SqlCatalog

def get_catalog_for_tenant(tenant_id: UUID) -> SqlCatalog:
    storage = InfrastructureConfigService.get_object_storage_for_tenant(tenant_id)
    return SqlCatalog(
        name=f"novasight_{tenant_id}",
        uri=settings.ICEBERG_CATALOG_URL,        # postgresql+psycopg://.../platform_db
        warehouse=f"s3://{storage.bucket}/{storage.prefix}",
        **{
            "s3.access-key-id": storage.access_key.get_secret_value(),
            "s3.secret-access-key": storage.secret_key.get_secret_value(),
            "s3.endpoint": storage.endpoint_url or "",
            "s3.region": storage.region,
            "s3.path-style-access": str(storage.path_style).lower(),
        },
    )

def ensure_namespace(tenant_slug: str) -> str:
    cat = get_catalog_for_tenant(...)
    namespace = (f"tenant_{tenant_slug}", "raw")
    if not cat.namespace_exists(namespace):
        cat.create_namespace(namespace)
    return ".".join(namespace)
```

The catalog tables (`iceberg_tables`, `iceberg_namespace_properties`) live under schema `iceberg_catalog` in the platform Postgres. An Alembic migration ensures the schema exists; pyiceberg auto-creates the tables on first use.

---

## 3. Pydantic validators (Template Engine Rule)

```python
# backend/app/services/template_engine/validator.py (excerpt)
class DltConnectionDefinition(BaseModel):
    db_type: Literal["postgresql", "mysql", "mssql"]
    connection_id: UUID                                   # validated for tenant ownership upstream

class DltSourceDefinition(BaseModel):
    type: Literal["table", "query"]
    schema: Optional[str]
    table: Optional[str]
    query: Optional[str]

class DltColumnDefinition(BaseModel):
    name: str
    data_type: str
    include: bool = True

class DltPipelineDefinition(BaseModel):
    """Validates inputs for backend/templates/dlt/*.j2."""
    tenant_id: UUID
    tenant_slug: str = Field(..., regex=r"^[a-z][a-z0-9_]{1,62}$")
    pipeline_name: str = Field(..., regex=r"^[a-z][a-z0-9_]{0,62}$")
    iceberg_namespace: str

    connection: DltConnectionDefinition
    source: DltSourceDefinition
    columns: List[DltColumnDefinition]
    primary_key_columns: List[str] = []
    write_disposition: Literal["append", "replace", "merge", "scd2"]
    incremental_cursor_column: Optional[str]
    incremental_cursor_type: Literal["none", "timestamp", "version"] = "none"

    @validator("iceberg_namespace")
    def _ns_must_match_tenant(cls, v, values):
        slug = values.get("tenant_slug")
        if v != f"tenant_{slug}.raw":
            raise ValueError(f"iceberg_namespace must be 'tenant_{slug}.raw'")
        return v

    @validator("primary_key_columns")
    def _scd2_or_merge_needs_pk(cls, v, values):
        wd = values.get("write_disposition")
        if wd in {"merge", "scd2"} and not v:
            raise ValueError(f"write_disposition '{wd}' requires primary_key_columns")
        return v

TEMPLATE_VALIDATORS = {
    "dlt/extract_pipeline.py.j2": DltPipelineDefinition,
    "dlt/merge_pipeline.py.j2": DltPipelineDefinition,
    "dlt/scd2_pipeline.py.j2": DltPipelineDefinition,
}
```

---

## 4. Generated pipeline template (canonical)

See [.github/agents/ingestion-agent.agent.md](../../agents/ingestion-agent.agent.md#-generated-dlt-pipeline-shape) for the canonical shape. Each `*.j2` file under `backend/templates/dlt/` MUST follow it. Differences between templates are limited to the `apply_hints(...)` block.

---

## 5. Dagster runner pattern

```python
# backend/orchestration/assets/dlt_builder.py (excerpt)
def build_dlt_asset(pipeline: DltPipeline) -> AssetsDefinition:
    @asset(
        name=f"dlt_{pipeline.tenant.slug}__{pipeline.name}",
        group_name=f"tenant_{pipeline.tenant.slug}",
        compute_kind="dlt",
    )
    def _run(context, object_storage, source_secret):
        env = os.environ.copy() | {
            "TENANT_ID": str(pipeline.tenant_id),
            "TENANT_S3_BUCKET_URL": object_storage.bucket_url(),
            "TENANT_S3_ACCESS_KEY": object_storage.access_key,
            "TENANT_S3_SECRET_KEY": object_storage.secret_key,
            "TENANT_S3_REGION": object_storage.region,
            "TENANT_S3_ENDPOINT_URL": object_storage.endpoint_url or "",
            "ICEBERG_CATALOG_URL": settings.ICEBERG_CATALOG_URL,
            "SOURCE_DB_DSN": source_secret,
        }
        proc = subprocess.run(
            ["python", f"/opt/dlt/pipelines/{pipeline.tenant.slug}/{pipeline.name}.py"],
            env=env, capture_output=True, text=True, check=False, timeout=settings.DLT_RUN_TIMEOUT,
        )
        context.log.info(proc.stdout)
        if proc.returncode != 0:
            context.log.error(proc.stderr)
            raise Failure(description=f"dlt pipeline {pipeline.name} failed", metadata={"stderr": proc.stderr[-2000:]})
        return MaterializeResult(metadata={"pipeline_id": str(pipeline.id)})
    return _run
```

Concurrency is bounded by `DAGSTER_DLT_CONCURRENCY_LIMIT`.

---

## 6. Wizard freshness mapping (used by `@frontend`)

The wizard never shows the words "append / replace / merge / scd2". It maps user choice → `write_disposition`:

| Wizard choice (Step 2) | `write_disposition` | Auto-derived needs |
|---|---|---|
| "Replace everything each time" | `replace` | none |
| "Add only new rows" | `append` | `incremental_cursor_*` auto-detected from a timestamp/serial column |
| "Keep history of changes" | `scd2` | `primary_key_columns` auto-suggested from CH metadata; user confirms |

The validator enforces the constraints (PK required for `scd2`/`merge`, cursor required for `append` with incremental).

---

## 7. Forbidden patterns (security)

The validator rejects any of:
- `os.system`, `subprocess`, `__import__`, `eval`, `exec`, `open(` outside of a known allowlist of read-only paths.
- Hard-coded AWS keys (regex `AKIA[0-9A-Z]{16}`).
- A `dataset_name` or `bucket_url` value not derived from env vars.
- A `tenant_slug` not matching the authenticated tenant.

```python
FORBIDDEN_PATTERNS = [
    r"\bos\.system\b", r"\bsubprocess\b", r"\b__import__\b",
    r"\beval\s*\(", r"\bexec\s*\(",
    r"AKIA[0-9A-Z]{16}",
]
```

---

## 8. Verification checklist

Before merging any change in this area:
- [ ] Pydantic validator covers the new path; security tests added.
- [ ] All three templates still render against the standard fixture.
- [ ] End-to-end run on MinIO + local Postgres catalog produces the expected Iceberg snapshot.
- [ ] Tenant isolation test: tenant A cannot read tenant B's bucket or namespace.
- [ ] No `pyspark` / `SparkSession` strings introduced in this PR.
- [ ] Generated code passes `ruff` + `pyflakes` cleanly.
- [ ] Dagster materialization succeeds in `dev` compose.

---

## 9. Anti-patterns (do not do)

- ❌ Importing the Flask app or SQLAlchemy session inside a generated pipeline.
- ❌ Reading `current_app.config` inside a pipeline — use env vars only.
- ❌ Hard-coding the bucket URL in a template.
- ❌ Sharing a single S3 bucket across tenants (decision is locked to bucket-per-tenant).
- ❌ Using ClickHouse `Iceberg` engine as a dbt source — dbt-duckdb is the lake-read path. (See `dbt-agent.agent.md`.)
- ❌ Persisting dlt's pipeline state in the platform DB. dlt manages its own state alongside the Iceberg tables.
