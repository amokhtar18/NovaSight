"""
NovaSight Platform — Iceberg Writer
====================================

Post-load Iceberg materialization for dlt pipelines.

The dlt 1.10 ``filesystem`` destination writes JSONL/Parquet files to S3
but does not produce Iceberg metadata. This module reads the JSONL files
from a freshly completed dlt load package and creates / appends to an
Iceberg table via ``pyiceberg``'s SQL catalog.

This step is *opt-in* via the ``ENABLE_ICEBERG=true`` environment variable
because (a) it requires the platform Postgres catalog to be reachable
from the pipeline subprocess and (b) it adds runtime cost. When disabled
(default), pipelines fall back to the JSONL-on-S3 layout that ClickHouse
reads via the native ``s3()`` table function.

Usage from a generated dlt pipeline::

    from app.platform.lake.iceberg_writer import materialize_jsonl_to_iceberg

    info = pipeline.run(...)
    if os.environ.get("ENABLE_ICEBERG", "").lower() in ("1", "true", "yes"):
        materialize_jsonl_to_iceberg(
            tenant_id=TENANT_ID,
            namespace=ICEBERG_NAMESPACE,    # e.g. "tenant_acme.raw"
            table_name=ICEBERG_TABLE,       # e.g. "revenuebyclient"
            jsonl_glob=f"s3://{TENANT_S3_BUCKET}/lake/{DATASET_NAME}/{ICEBERG_TABLE}/*.jsonl",
            write_disposition=WRITE_DISPOSITION,  # "replace" | "append"
            s3_endpoint_url=S3_ENDPOINT_URL,
            s3_access_key=S3_ACCESS_KEY,
            s3_secret_key=S3_SECRET_KEY,
            s3_region=S3_REGION,
        )
"""
from __future__ import annotations

import logging
import os
from typing import Optional
from uuid import UUID

logger = logging.getLogger(__name__)


def _build_filesystem(
    s3_endpoint_url: str,
    s3_access_key: str,
    s3_secret_key: str,
    s3_region: str,
):
    """Build a pyarrow S3 FileSystem for reading the JSONL files."""
    import pyarrow.fs as pafs

    kwargs = {
        "access_key": s3_access_key,
        "secret_key": s3_secret_key,
        "region": s3_region or "us-east-1",
    }
    if s3_endpoint_url:
        # MinIO / non-AWS S3
        kwargs["endpoint_override"] = s3_endpoint_url
        kwargs["scheme"] = "http" if s3_endpoint_url.startswith("http://") else "https"
    return pafs.S3FileSystem(**kwargs)


def _read_jsonl_to_arrow(
    s3_glob: str,
    fs,
):
    """
    Read every JSONL file matching ``s3_glob`` into a single pyarrow Table.

    The glob is restricted to a directory + ``*.jsonl`` suffix because
    pyarrow.fs doesn't accept wildcards directly — we list and filter.
    """
    import pyarrow as pa
    import pyarrow.json as pajson

    # Strip s3:// scheme; pyarrow.fs uses bucket/key syntax.
    if not s3_glob.startswith("s3://"):
        raise ValueError(f"Expected s3:// URI, got {s3_glob!r}")
    path = s3_glob[len("s3://") :]
    if "/*" not in path:
        raise ValueError(f"Glob must end with /*.<ext>, got {s3_glob!r}")
    dir_path, pattern = path.rsplit("/", 1)
    suffix = pattern.lstrip("*")  # ".jsonl" or ".jsonl.gz"

    selector = fs.get_file_info(__import__("pyarrow.fs", fromlist=["FileSelector"]).FileSelector(dir_path, recursive=False))
    files = [info.path for info in selector if info.is_file and info.path.endswith(suffix)]
    if not files:
        raise FileNotFoundError(f"No JSONL files at s3://{dir_path}/ matching *{suffix}")

    logger.info("Reading %d JSONL files from s3://%s/", len(files), dir_path)

    # Read each file (pyarrow auto-detects gzip via the file extension when
    # we open through the filesystem). For dlt 1.10 the layout writes
    # gzip-compressed JSONL with a plain ``.jsonl`` extension, so we have
    # to read manually with gzip.
    import gzip
    import io
    import json

    chunks = []
    for f in files:
        with fs.open_input_stream(f) as stream:
            raw = stream.readall()
        # Try gzip decode first (dlt default), fall back to plain JSON
        try:
            buf = gzip.decompress(raw)
        except OSError:
            buf = raw
        rows = [json.loads(line) for line in buf.splitlines() if line.strip()]
        if rows:
            chunks.append(pa.Table.from_pylist(rows))

    if not chunks:
        raise ValueError(f"All {len(files)} JSONL files were empty")

    # Unify schemas (some load packages may differ in column order)
    return pa.concat_tables(chunks, promote_options="default")


def materialize_jsonl_to_iceberg(
    *,
    tenant_id: UUID | str,
    namespace: str,
    table_name: str,
    jsonl_glob: str,
    write_disposition: str = "replace",
    s3_endpoint_url: Optional[str] = None,
    s3_access_key: Optional[str] = None,
    s3_secret_key: Optional[str] = None,
    s3_region: Optional[str] = None,
) -> dict:
    """
    Read JSONL files from S3 and append/overwrite an Iceberg table.

    Parameters
    ----------
    tenant_id
        Tenant UUID (used to look up the per-tenant catalog config).
    namespace
        Iceberg namespace, e.g. ``"tenant_acme.raw"``.
    table_name
        Iceberg table name, e.g. ``"revenuebyclient"``.
    jsonl_glob
        ``s3://bucket/path/*.jsonl`` glob of files to load.
    write_disposition
        ``"replace"`` → ``Table.overwrite``; ``"append"``/``"merge"`` →
        ``Table.append``. (Merge semantics not yet implemented; falls
        back to append.)
    s3_endpoint_url, s3_access_key, s3_secret_key, s3_region
        S3/MinIO credentials. When omitted, environment defaults are
        used (``S3_ENDPOINT_URL``, ``AWS_ACCESS_KEY_ID``, …).

    Returns
    -------
    dict with keys ``namespace``, ``table``, ``rows``, ``snapshot_id``.

    Raises
    ------
    Any pyiceberg / pyarrow / S3 error is propagated. Callers should
    catch broadly to avoid failing the dlt run when Iceberg is best-effort.
    """
    if isinstance(tenant_id, str):
        tenant_id = UUID(tenant_id)

    # Lazy imports so the helper is importable even when pyiceberg
    # is missing in the environment (e.g. dlt-only worker images).
    from app.platform.lake.iceberg_catalog import (
        ensure_namespace,
        get_catalog_for_tenant,
    )

    s3_endpoint_url = s3_endpoint_url or os.environ.get("S3_ENDPOINT_URL")
    s3_access_key = s3_access_key or os.environ.get("AWS_ACCESS_KEY_ID", "")
    s3_secret_key = s3_secret_key or os.environ.get("AWS_SECRET_ACCESS_KEY", "")
    s3_region = s3_region or os.environ.get("AWS_REGION", "us-east-1")

    fs = _build_filesystem(s3_endpoint_url or "", s3_access_key, s3_secret_key, s3_region)
    arrow_table = _read_jsonl_to_arrow(jsonl_glob, fs)
    logger.info(
        "Read %d rows / %d columns into Arrow table for %s.%s",
        arrow_table.num_rows,
        arrow_table.num_columns,
        namespace,
        table_name,
    )

    catalog = get_catalog_for_tenant(tenant_id)

    # ensure_namespace expects "tenant_slug + suffix"; the caller already
    # passes the full namespace, so just create it idempotently.
    from pyiceberg.exceptions import NamespaceAlreadyExistsError

    try:
        catalog.create_namespace(namespace)
    except NamespaceAlreadyExistsError:
        pass
    except Exception as e:  # noqa: BLE001
        logger.warning("create_namespace(%s) failed: %s", namespace, e)

    identifier = f"{namespace}.{table_name}"
    try:
        table = catalog.load_table(identifier)
        existed = True
    except Exception:
        table = catalog.create_table(identifier, schema=arrow_table.schema)
        existed = False

    disp = (write_disposition or "replace").lower()
    if disp == "replace":
        table.overwrite(arrow_table)
    else:
        # append / merge (merge support is a follow-up using equality deletes)
        table.append(arrow_table)

    snapshot = table.current_snapshot()
    result = {
        "namespace": namespace,
        "table": table_name,
        "identifier": identifier,
        "existed_before": existed,
        "rows": arrow_table.num_rows,
        "snapshot_id": snapshot.snapshot_id if snapshot else None,
        "write_disposition": disp,
    }
    logger.info("Iceberg materialization complete: %s", result)
    return result
