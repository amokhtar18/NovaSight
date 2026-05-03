"""
NovaSight Ingestion Domain — dlt Pipeline Runner
=================================================

Pure-Python subprocess runner for generated dlt pipeline scripts.
No Dagster dependency — safe to call from a Flask app context or CLI.

``build_pipeline_env`` and ``parse_pipeline_metrics`` are the single source
of truth; ``dlt_builder.py`` imports them rather than defining its own copies.
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Any, Dict, Optional

_module_logger = logging.getLogger(__name__)

# Path where generated pipeline scripts are written.
# Must match the path used by DltPipelineService._write_generated_file.
DLT_PIPELINES_PATH = os.getenv("DLT_PIPELINES_PATH", "/opt/dlt/pipelines")


def build_pipeline_env(
    tenant_id: str,
    tenant_slug: str,
    pipeline_id: str,
    log_fn=None,
) -> Dict[str, str]:
    """
    Build environment variables for pipeline subprocess execution.

    Assumes an active Flask application context is present so SQLAlchemy
    models can be queried directly.  When called from a Dagster subprocess
    (no ambient Flask context), the caller must push an app context first
    — see ``dlt_builder._build_pipeline_env`` for the Dagster wrapper.

    Args:
        tenant_id:    Tenant UUID string.
        tenant_slug:  Tenant slug (used for namespace derivation).
        pipeline_id:  Pipeline UUID string.
        log_fn:       Optional callable(msg) used for warnings.
                      Defaults to the module-level logger.

    Returns:
        Dict of environment variables ready for ``subprocess.run(env=...)``.
    """
    _warn = log_fn or _module_logger.warning

    env = os.environ.copy()
    env["TENANT_ID"] = tenant_id
    env["TENANT_SLUG"] = tenant_slug
    env["PIPELINE_ID"] = pipeline_id

    # --- Tenant S3 / object-storage credentials ---
    #
    # Resolution order (mirrors ``dlt_uploads._get_tenant_s3``):
    #   1. ``infrastructure_configs`` row of type ``object_storage``
    #      scoped to the tenant (decrypted secrets).
    #   2. Platform-wide MinIO/S3 defaults from Flask config.
    # The default bucket name is ``tenant-<slug>`` — the same convention
    # used by the upload route, so the bucket the pipeline reads from
    # always matches the bucket files were uploaded to.
    s3_settings: Dict[str, Any] = {}
    try:
        from app.domains.tenants.infrastructure.config_service import (
            InfrastructureConfigService,
        )

        service = InfrastructureConfigService()
        configs = service.list_configs(
            service_type="object_storage",
            tenant_id=tenant_id,
            include_global=False,
            page=1,
            per_page=1,
        )
        if configs.get("items"):
            raw_settings = configs["items"][0].get("settings", {})
            s3_settings = service.decrypt_settings(raw_settings, "object_storage")
    except Exception as exc:
        _warn(f"Could not load S3 infrastructure config: {exc}")

    # Fallback to platform defaults from Flask config when fields are missing
    try:
        from flask import current_app

        cfg = current_app.config
        bucket = s3_settings.get("bucket") or f"tenant-{tenant_slug}"
        env["TENANT_S3_BUCKET"] = bucket
        env["AWS_ACCESS_KEY_ID"] = (
            s3_settings.get("access_key") or cfg.get("MINIO_ROOT_USER", "")
        )
        env["AWS_SECRET_ACCESS_KEY"] = (
            s3_settings.get("secret_key") or cfg.get("MINIO_ROOT_PASSWORD", "")
        )
        env["S3_ENDPOINT_URL"] = (
            s3_settings.get("endpoint_url") or cfg.get("MINIO_ENDPOINT_URL", "") or ""
        )
        env["AWS_REGION"] = (
            s3_settings.get("region")
            or cfg.get("OBJECT_STORAGE_DEFAULT_REGION")
            or "us-east-1"
        )
    except Exception as exc:
        _warn(f"Could not resolve S3 env fallback: {exc}")
        # Last-resort defaults so the subprocess still has something deterministic
        env.setdefault("TENANT_S3_BUCKET", f"tenant-{tenant_slug}")

    # Iceberg SQL catalog URL
    env["ICEBERG_CATALOG_URL"] = os.getenv(
        "ICEBERG_CATALOG_URL",
        "postgresql://novasight:novasight@postgres:5432/novasight_platform",
    )

    # --- Source connection string OR file-source env vars ---
    try:
        from app.domains.ingestion.domain.models import DltPipeline, DltSourceKind
        from app.domains.datasources.application.connection_service import ConnectionService

        pipeline = DltPipeline.query.get(pipeline_id)
        if pipeline is None:
            raise RuntimeError(f"Pipeline {pipeline_id} not found")

        kind = pipeline.source_kind or DltSourceKind.SQL.value
        if kind == DltSourceKind.FILE.value:
            # File-source pipelines read directly from the tenant S3 bucket;
            # S3 credentials injected above already cover access.
            env["FILE_OBJECT_KEY"] = pipeline.file_object_key or ""
            env["FILE_FORMAT"] = pipeline.file_format or ""
            env["FILE_OPTIONS_JSON"] = json.dumps(pipeline.file_options or {})
        elif pipeline.connection_id:
            conn_service = ConnectionService(tenant_id=tenant_id)
            connection = conn_service.get_connection(str(pipeline.connection_id))
            if connection:
                # Decrypt the stored password and ask the model to build a
                # fully-qualified SQLAlchemy URL (with ``drivername``) — dlt's
                # sql_database/sql_table credentials parser fails with
                # "Following fields are missing: ['drivername']" if we hand
                # it an empty or scheme-less string.
                from urllib.parse import quote_plus

                password = conn_service._encryption.decrypt(
                    connection.password_encrypted
                ) or ""
                env["SOURCE_CONNECTION_STRING"] = connection.get_connection_string(
                    password=quote_plus(password)
                )

                # --- Oracle thick-mode / Instant Client passthrough ---
                # The generated pipeline runs as a subprocess and creates
                # its own SQLAlchemy engine, bypassing OracleConnector. To
                # keep behavior consistent with the saved connection's
                # extra_params, propagate Oracle-specific flags as env vars
                # that the templates read at startup.
                from app.domains.datasources.domain.models import DatabaseType
                if connection.db_type == DatabaseType.ORACLE:
                    extra = connection.extra_params or {}
                    # Default to thick mode for Oracle: most enterprise
                    # servers reject thin mode (DPY-3010). Users can opt
                    # out by setting extra_params.thick_mode = false.
                    thick = extra.get("thick_mode")
                    if thick is None:
                        thick = True
                    env["ORACLE_THICK_MODE"] = "1" if thick else "0"
                    if instant_client_dir := extra.get("instant_client_dir"):
                        env["ORACLE_INSTANT_CLIENT_DIR"] = str(instant_client_dir)
                    if wallet_location := extra.get("wallet_location"):
                        env["ORACLE_WALLET_LOCATION"] = str(wallet_location)
                    if wallet_password := extra.get("wallet_password"):
                        env["ORACLE_WALLET_PASSWORD"] = str(wallet_password)
            else:
                _warn(
                    f"Pipeline {pipeline_id} references missing connection "
                    f"{pipeline.connection_id}; SOURCE_CONNECTION_STRING not set"
                )

    except Exception as exc:
        _warn(f"Could not load pipeline source env: {exc}")

    return env


def parse_pipeline_metrics(stdout: str) -> Dict[str, Any]:
    """
    Parse ``METRICS:key=value`` lines emitted to stdout by a pipeline script.

    Example lines::

        METRICS:rows=1000
        METRICS:duration_ms=5000
        METRICS:iceberg_snapshot_id=abc123

    Returns:
        Dict of metric values (converted to ``int`` where possible).
    """
    metrics: Dict[str, Any] = {}
    for line in stdout.split("\n"):
        if line.startswith("METRICS:"):
            try:
                metric_part = line[8:]  # strip "METRICS:"
                key, value = metric_part.split("=", 1)
                try:
                    value = int(value)  # type: ignore[assignment]
                except ValueError:
                    pass
                metrics[key] = value
            except Exception:
                pass
    return metrics


def execute_pipeline_script(
    pipeline_id: str,
    tenant_id: str,
    tenant_slug: str,
    pipeline_name: str,
    timeout_seconds: int = 3600,
    logger: Optional[logging.Logger] = None,
) -> Dict[str, Any]:
    """
    Execute a generated dlt pipeline script as a subprocess.

    The function never raises — all failure modes are captured and returned
    in the ``status`` field so callers can persist run stats unconditionally.

    Args:
        pipeline_id:      Pipeline UUID string.
        tenant_id:        Tenant UUID string.
        tenant_slug:      Tenant slug — used to locate the script file.
        pipeline_name:    Pipeline name (equals the script filename without ``.py``).
        timeout_seconds:  Hard wall-clock limit for the subprocess (default 1 h).
        logger:           Optional logger; falls back to the module logger.

    Returns::

        {
            "status":               "success" | "error" | "timeout",
            "rows":                 int | None,
            "duration_ms":          int,
            "iceberg_snapshot_id":  str | None,
            "stdout_tail":          str,   # last ~4 KB
            "stderr_tail":          str,   # last ~4 KB
            "exit_code":            int | None,
            "script_path":          str,
        }
    """
    _log = logger if logger is not None else _module_logger

    script_path = os.path.join(DLT_PIPELINES_PATH, tenant_slug, f"{pipeline_name}.py")

    if not os.path.exists(script_path):
        _log.error("Pipeline script not found: %s", script_path)
        return {
            "status": "error",
            "rows": None,
            "duration_ms": 0,
            "iceberg_snapshot_id": None,
            "stdout_tail": "",
            "stderr_tail": f"Pipeline script not found: {script_path}",
            "exit_code": None,
            "script_path": script_path,
        }

    env = build_pipeline_env(
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        pipeline_id=pipeline_id,
        log_fn=_log.warning,
    )

    start_time = datetime.utcnow()
    try:
        result = subprocess.run(
            ["python", script_path],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        _log.error("Pipeline %s timed out after %ds", pipeline_name, timeout_seconds)
        return {
            "status": "timeout",
            "rows": None,
            "duration_ms": duration_ms,
            "iceberg_snapshot_id": None,
            "stdout_tail": "",
            "stderr_tail": f"Pipeline timed out after {timeout_seconds}s",
            "exit_code": None,
            "script_path": script_path,
        }

    duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    stdout_tail = result.stdout[-4096:] if result.stdout else ""
    stderr_tail = result.stderr[-4096:] if result.stderr else ""

    if result.returncode != 0:
        _log.error(
            "Pipeline %s exited with code %d. stderr: %s",
            pipeline_name,
            result.returncode,
            stderr_tail[-500:],
        )
        return {
            "status": "error",
            "rows": None,
            "duration_ms": duration_ms,
            "iceberg_snapshot_id": None,
            "stdout_tail": stdout_tail,
            "stderr_tail": stderr_tail,
            "exit_code": result.returncode,
            "script_path": script_path,
        }

    metrics = parse_pipeline_metrics(result.stdout)
    _log.info(
        "Pipeline %s succeeded: rows=%s duration_ms=%d",
        pipeline_name,
        metrics.get("rows"),
        duration_ms,
    )
    return {
        "status": "success",
        "rows": metrics.get("rows"),
        "duration_ms": duration_ms,
        "iceberg_snapshot_id": metrics.get("iceberg_snapshot_id"),
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "exit_code": result.returncode,
        "script_path": script_path,
    }
