# NovaSight S3 / Object Storage Infrastructure

This directory contains the configuration for the **S3-compatible object
storage** used by NovaSight as the **Iceberg data lake**.

## Role in the platform

```
   ┌────────┐   dlt    ┌──────────────────┐   dbt-duckdb   ┌────────────┐
   │ source │────────▶ │  Iceberg on S3   │ ─────────────▶ │ ClickHouse │
   │  DBs   │          │  (this layer)    │   materialize  │   marts    │
   └────────┘          └──────────────────┘                └────────────┘
```

* **dlt** pipelines extract from operational sources and **write Iceberg
  tables** into per-tenant buckets on this storage.
* **dbt** (with the `dbt-duckdb` adapter and the DuckDB `iceberg` + `httpfs`
  extensions) **reads Iceberg tables from S3** as sources and
  **materializes** the transformed marts into **ClickHouse** via the
  `dbt-clickhouse` adapter.

This replaces the previous Spark-based ingestion/transformation path.
There is **no Spark** in the runtime data path anymore.

## Files

| File                          | Purpose                                                  |
|-------------------------------|----------------------------------------------------------|
| `s3.env.example`              | Environment variables consumed by dlt, dbt and Iceberg.  |
| `iceberg-catalog.yaml`        | Iceberg SQL catalog configuration (Postgres-backed).     |
| `bucket-policy.template.json` | Per-tenant bucket policy template (least-privilege).     |
| `lifecycle-policy.json`       | Default lifecycle rules (snapshot expiry, abort MPU).    |
| `init-buckets.sh`             | Bucket bootstrap script (mirrors `docker/minio/`).       |

## Local development (MinIO)

In dev, the S3 endpoint is provided by the `minio` service in
`docker-compose.yml`:

* S3 API:  `http://minio:9000` (host: `localhost:9002`)
* Console: `http://localhost:9001`
* Default credentials: `minioadmin / minioadmin`

## Production

Use any S3-compatible service (AWS S3, Cloudflare R2, GCS via S3 gateway,
MinIO cluster, etc.). Set the variables in `s3.env.example` to match your
deployment and enable TLS + IAM.

## Tenant isolation

Each tenant gets a dedicated bucket: `novasight-{tenant_slug}`.
The Iceberg catalog tracks tables per tenant namespace
(`tenant_{slug}.<schema>.<table>`).
