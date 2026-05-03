"""
NovaSight Dataset Service
=========================

Business logic for the Superset-inspired :class:`Dataset` model — CRUD,
column / metric management, dbt manifest sync, and lightweight preview.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from flask import current_app
from sqlalchemy import and_, or_

from app.extensions import db
from app.domains.analytics.domain.dataset_models import (
    Dataset,
    DatasetColumn,
    DatasetKind,
    DatasetMetric,
    DatasetSource,
    DbtMaterialization,
    MATERIALIZED_DBT_TYPES,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DatasetServiceError(Exception):
    """Base exception for dataset service errors."""


class DatasetNotFoundError(DatasetServiceError):
    """Raised when a dataset cannot be located for the current tenant."""


class DatasetValidationError(DatasetServiceError):
    """Raised when a dataset payload fails validation."""


class DbtManifestNotFoundError(DatasetServiceError):
    """Raised when the dbt manifest cannot be located on disk."""


# ---------------------------------------------------------------------------
# Tenant mart DB helpers
# ---------------------------------------------------------------------------


def get_tenant_mart_database(tenant_id: str) -> str:
    """Return the canonical ClickHouse mart database name for a tenant.

    Datasets are restricted to this database — it is the curated dbt
    *marts* layer (``tenant_<safe_slug>_marts``) where business-ready,
    governed tables live. Raw / staging / intermediate layers are
    intentionally hidden from the dataset wizard so analysts never
    publish charts on top of un-modelled data.
    """
    from app.platform.tenant.isolation import TenantIsolationService
    from app.domains.tenants.domain.models import Tenant

    tenant = Tenant.query.get(tenant_id)
    slug = tenant.slug if tenant and tenant.slug else str(tenant_id)
    iso = TenantIsolationService(tenant_id=str(tenant_id), tenant_slug=slug)
    return f"{iso.tenant_database}_marts"


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass
class DbtSyncResult:
    """Result of a dbt → datasets sync run for a given tenant."""

    created: int = 0
    updated: int = 0
    deactivated: int = 0
    skipped: int = 0
    inspected: int = 0
    errors: List[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "created": self.created,
            "updated": self.updated,
            "deactivated": self.deactivated,
            "skipped": self.skipped,
            "inspected": self.inspected,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class DatasetService:
    """CRUD + dbt-sync operations for :class:`Dataset`."""

    # -- query -----------------------------------------------------------------

    @classmethod
    def list_for_tenant(
        cls,
        tenant_id: str,
        *,
        kind: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dataset], int]:
        q = Dataset.query.filter(Dataset.tenant_id == UUID(str(tenant_id)))
        if not include_deleted:
            q = q.filter(Dataset.is_deleted.is_(False))
        if kind:
            q = q.filter(Dataset.kind == kind)
        if source:
            q = q.filter(Dataset.source == source)
        if search:
            like = f"%{search}%"
            q = q.filter(
                or_(
                    Dataset.name.ilike(like),
                    Dataset.description.ilike(like),
                    Dataset.table_name.ilike(like),
                )
            )
        total = q.count()
        items = (
            q.order_by(Dataset.is_featured.desc(), Dataset.name.asc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        return items, total

    @classmethod
    def get(cls, tenant_id: str, dataset_id: str) -> Dataset:
        ds = Dataset.query.filter(
            and_(
                Dataset.id == UUID(str(dataset_id)),
                Dataset.tenant_id == UUID(str(tenant_id)),
                Dataset.is_deleted.is_(False),
            )
        ).first()
        if ds is None:
            raise DatasetNotFoundError(f"Dataset {dataset_id} not found")
        return ds

    # -- mutation --------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        tenant_id: str,
        owner_id: Optional[str],
        payload: Dict[str, Any],
    ) -> Dataset:
        cls._validate_payload(payload)
        # Enforce: physical datasets may only target the tenant mart DB.
        # If no database_name was supplied we default to it; if a
        # different one was supplied we reject the request.
        kind_value = payload.get("kind", DatasetKind.PHYSICAL.value)
        source_value = payload.get("source", DatasetSource.MANUAL.value)
        if (
            kind_value == DatasetKind.PHYSICAL.value
            and source_value != DatasetSource.DBT.value
        ):
            mart_db = get_tenant_mart_database(tenant_id)
            requested_db = (payload.get("database_name") or "").strip() or None
            requested_schema = (payload.get("schema") or "").strip() or None
            if requested_db and requested_db != mart_db:
                raise DatasetValidationError(
                    f"Datasets can only be created from the tenant mart "
                    f"database '{mart_db}', got '{requested_db}'"
                )
            if requested_schema and requested_schema != mart_db:
                raise DatasetValidationError(
                    f"Datasets can only be created from the tenant mart "
                    f"database '{mart_db}', got schema '{requested_schema}'"
                )
            payload["database_name"] = mart_db
            payload["schema"] = mart_db
        ds = Dataset(
            tenant_id=UUID(str(tenant_id)),
            owner_id=UUID(str(owner_id)) if owner_id else None,
            name=payload["name"].strip(),
            description=payload.get("description"),
            kind=DatasetKind(payload.get("kind", DatasetKind.PHYSICAL.value)),
            source=DatasetSource(payload.get("source", DatasetSource.MANUAL.value)),
            database_name=payload.get("database_name"),
            schema=payload.get("schema"),
            table_name=payload.get("table_name"),
            sql=payload.get("sql"),
            main_dttm_col=payload.get("main_dttm_col"),
            default_endpoint=payload.get("default_endpoint"),
            cache_timeout_seconds=payload.get("cache_timeout_seconds"),
            extra=payload.get("extra") or {},
            tags=list(payload.get("tags") or []),
            is_featured=bool(payload.get("is_featured", False)),
            is_managed=bool(payload.get("is_managed", False)),
        )
        db.session.add(ds)
        db.session.flush()

        for col in payload.get("columns") or []:
            db.session.add(_build_column(ds.id, col))
        for met in payload.get("metrics") or []:
            db.session.add(_build_metric(ds.id, met))

        db.session.commit()
        return ds

    @classmethod
    def update(
        cls,
        *,
        tenant_id: str,
        dataset_id: str,
        payload: Dict[str, Any],
    ) -> Dataset:
        ds = cls.get(tenant_id, dataset_id)
        if ds.is_managed and not payload.get("_force"):
            raise DatasetValidationError(
                "Dataset is managed by automated sync; use 'sync' or pass _force=true to override"
            )
        editable = {
            "name",
            "description",
            "schema",
            "database_name",
            "table_name",
            "sql",
            "main_dttm_col",
            "default_endpoint",
            "cache_timeout_seconds",
            "extra",
            "tags",
            "is_featured",
        }
        for key in editable & payload.keys():
            setattr(ds, key, payload[key])
        if "kind" in payload:
            ds.kind = DatasetKind(payload["kind"])
        if "source" in payload:
            ds.source = DatasetSource(payload["source"])
        db.session.commit()
        return ds

    @classmethod
    def delete(cls, tenant_id: str, dataset_id: str, *, hard: bool = False) -> None:
        ds = cls.get(tenant_id, dataset_id)
        if hard:
            db.session.delete(ds)
        else:
            ds.is_deleted = True
            ds.deleted_at = datetime.utcnow()
        db.session.commit()

    # -- mart browsing ---------------------------------------------------------

    @classmethod
    def list_mart_tables(cls, tenant_id: str) -> Dict[str, Any]:
        """List ClickHouse tables in the tenant's curated mart database.

        This is the single source the dataset wizard is allowed to pick
        from — see :func:`get_tenant_mart_database`. Returns a structure
        ready for the frontend wizard:

        ``{ "database": "<mart_db>", "exists": bool, "tables": [...] }``

        Each table includes its name, engine, total row count (best
        effort), and a lightweight column list so the wizard can show
        a preview without an extra round-trip.
        """
        from app.domains.analytics.infrastructure.clickhouse_client import (
            get_clickhouse_client,
        )

        mart_db = get_tenant_mart_database(tenant_id)
        client = get_clickhouse_client(tenant_id=tenant_id)

        # Verify the mart DB exists; if not, return an empty list with a
        # hint so the UI can render a "No mart tables yet — run dbt"
        # empty state instead of an error.
        try:
            existence = client.execute(
                "SELECT name FROM system.databases WHERE name = %(db)s",
                {"db": mart_db},
            )
            exists = bool(existence.rows)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning(
                "Mart DB existence check failed for tenant %s: %s",
                tenant_id,
                exc,
            )
            exists = False

        if not exists:
            return {"database": mart_db, "exists": False, "tables": []}

        try:
            tables_res = client.execute(
                "SELECT name, engine, total_rows "
                "FROM system.tables "
                "WHERE database = %(db)s AND is_temporary = 0 "
                "ORDER BY name",
                {"db": mart_db},
            )
        except Exception as exc:
            logger.warning(
                "Failed to list mart tables for tenant %s: %s",
                tenant_id,
                exc,
            )
            return {"database": mart_db, "exists": True, "tables": []}

        try:
            cols_res = client.execute(
                "SELECT table, name, type "
                "FROM system.columns "
                "WHERE database = %(db)s "
                "ORDER BY table, position",
                {"db": mart_db},
            )
        except Exception as exc:
            logger.warning(
                "Failed to list mart columns for tenant %s: %s",
                tenant_id,
                exc,
            )
            cols_res_rows: List[Any] = []
        else:
            cols_res_rows = cols_res.rows

        cols_by_table: Dict[str, List[Dict[str, Any]]] = {}
        for row in cols_res_rows:
            cols_by_table.setdefault(row[0], []).append(
                {"name": row[1], "type": row[2]}
            )

        tables: List[Dict[str, Any]] = []
        for row in tables_res.rows:
            name, engine, total_rows = row[0], row[1], row[2]
            tables.append(
                {
                    "name": name,
                    "engine": engine,
                    "total_rows": int(total_rows) if total_rows is not None else None,
                    "columns": cols_by_table.get(name, []),
                }
            )

        return {"database": mart_db, "exists": True, "tables": tables}

    # -- columns / metrics -----------------------------------------------------

    @classmethod
    def replace_columns(
        cls, tenant_id: str, dataset_id: str, columns: List[Dict[str, Any]]
    ) -> Dataset:
        ds = cls.get(tenant_id, dataset_id)
        DatasetColumn.query.filter(DatasetColumn.dataset_id == ds.id).delete()
        for col in columns:
            db.session.add(_build_column(ds.id, col))
        db.session.commit()
        return ds

    @classmethod
    def replace_metrics(
        cls, tenant_id: str, dataset_id: str, metrics: List[Dict[str, Any]]
    ) -> Dataset:
        ds = cls.get(tenant_id, dataset_id)
        DatasetMetric.query.filter(DatasetMetric.dataset_id == ds.id).delete()
        for met in metrics:
            db.session.add(_build_metric(ds.id, met))
        db.session.commit()
        return ds

    # -- preview ---------------------------------------------------------------

    @classmethod
    def preview_sql(cls, ds: Dataset, *, limit: int = 100) -> str:
        """Build a safe ``SELECT … LIMIT n`` against the dataset (no execution)."""
        limit = max(1, min(int(limit), 1000))
        if ds.kind == DatasetKind.PHYSICAL:
            target = ds.qualified_table
            if not target:
                raise DatasetValidationError(
                    "Physical dataset is missing table_name/schema"
                )
            return f"SELECT * FROM {target} LIMIT {limit}"
        if not (ds.sql or "").strip():
            raise DatasetValidationError("Virtual dataset has no SQL defined")
        return f"SELECT * FROM ({ds.sql}) AS dataset LIMIT {limit}"

    @classmethod
    def execute_preview(
        cls, tenant_id: str, dataset_id: str, *, limit: int = 100
    ) -> Dict[str, Any]:
        """Run the preview SQL on the tenant's ClickHouse database."""
        # Local import to avoid hard dependency at module load time.
        from app.domains.analytics.infrastructure.clickhouse_client import (
            get_clickhouse_client,
        )

        ds = cls.get(tenant_id, dataset_id)
        sql = cls.preview_sql(ds, limit=limit)
        client = get_clickhouse_client(
            database=ds.database_name, tenant_id=tenant_id
        )
        rows, types = client.execute(sql, with_column_types=True)
        cols = [{"name": n, "type": t} for n, t in (types or [])]
        return {
            "sql": sql,
            "columns": cols,
            "rows": [list(r) for r in rows],
            "row_count": len(rows),
        }

    # -- dbt sync --------------------------------------------------------------

    @classmethod
    def sync_from_dbt(
        cls,
        *,
        tenant_id: str,
        manifest_path: Optional[str] = None,
        owner_id: Optional[str] = None,
        deactivate_missing: bool = True,
    ) -> DbtSyncResult:
        """
        Auto-create / update datasets from materialized dbt models for *this tenant*.

        Strategy:

        * Load ``manifest.json`` from the configured dbt project directory.
        * Pick model nodes whose ``config.materialized`` is in
          :data:`MATERIALIZED_DBT_TYPES` **and** whose schema/database matches
          the tenant's ClickHouse database (``tenant_<slug>``).
        * Upsert one :class:`Dataset` per such node, keyed by
          ``(tenant_id, dbt_unique_id)``.
        * Replace its :class:`DatasetColumn` rows with the columns described in
          the manifest's ``columns`` block (if any).
        * Mark dbt-managed datasets that no longer exist in the manifest as
          deactivated (``is_deleted=True``) when ``deactivate_missing`` is set.
        """
        manifest = _load_manifest(manifest_path)
        tenant_database = _resolve_tenant_database(tenant_id)
        result = DbtSyncResult()

        seen_unique_ids: List[str] = []
        nodes = manifest.get("nodes", {}) or {}
        for unique_id, node in nodes.items():
            if node.get("resource_type") != "model":
                continue
            result.inspected += 1

            config = node.get("config") or {}
            materialization = (config.get("materialized") or "").strip()
            if materialization not in MATERIALIZED_DBT_TYPES:
                result.skipped += 1
                continue

            node_schema = (config.get("schema") or node.get("schema") or "").strip()
            node_database = (
                config.get("database") or node.get("database") or ""
            ).strip()
            # Match either schema or database against the tenant's CH database.
            if tenant_database and not _matches_tenant_db(
                tenant_database, node_schema, node_database
            ):
                result.skipped += 1
                continue

            try:
                created = cls._upsert_dbt_dataset(
                    tenant_id=tenant_id,
                    owner_id=owner_id,
                    unique_id=unique_id,
                    node=node,
                    materialization=materialization,
                    tenant_database=tenant_database or node_database or node_schema,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Failed to sync dbt node %s", unique_id)
                result.errors.append(f"{unique_id}: {exc}")
                continue

            seen_unique_ids.append(unique_id)
            if created:
                result.created += 1
            else:
                result.updated += 1

        if deactivate_missing:
            stale = (
                Dataset.query.filter(
                    Dataset.tenant_id == UUID(str(tenant_id)),
                    Dataset.source == DatasetSource.DBT,
                    Dataset.is_deleted.is_(False),
                    ~Dataset.dbt_unique_id.in_(seen_unique_ids)
                    if seen_unique_ids
                    else Dataset.dbt_unique_id.isnot(None),
                )
                .all()
            )
            for ds in stale:
                ds.is_deleted = True
                ds.deleted_at = datetime.utcnow()
                result.deactivated += 1

        db.session.commit()
        return result

    # -- helpers ---------------------------------------------------------------

    @classmethod
    def _upsert_dbt_dataset(
        cls,
        *,
        tenant_id: str,
        owner_id: Optional[str],
        unique_id: str,
        node: Dict[str, Any],
        materialization: str,
        tenant_database: Optional[str],
    ) -> bool:
        """Upsert a dataset for a single dbt node. Returns True if created."""
        config = node.get("config") or {}
        node_name = node.get("alias") or node.get("name") or unique_id
        schema = config.get("schema") or node.get("schema") or tenant_database
        database = (
            config.get("database") or node.get("database") or tenant_database
        )

        ds: Optional[Dataset] = (
            Dataset.query.filter(
                Dataset.tenant_id == UUID(str(tenant_id)),
                Dataset.dbt_unique_id == unique_id,
            )
            .first()
        )
        created = False
        if ds is None:
            ds = Dataset(
                tenant_id=UUID(str(tenant_id)),
                owner_id=UUID(str(owner_id)) if owner_id else None,
                name=node_name,
                kind=DatasetKind.PHYSICAL,
                source=DatasetSource.DBT,
                is_managed=True,
                dbt_unique_id=unique_id,
            )
            db.session.add(ds)
            created = True

        # Always-refresh fields on each sync.
        ds.is_deleted = False
        ds.deleted_at = None
        ds.description = node.get("description") or ds.description
        ds.database_name = database
        ds.schema = schema
        ds.table_name = node_name
        ds.dbt_materialization = DbtMaterialization(materialization)
        ds.dbt_meta = {
            "fqn": node.get("fqn"),
            "package_name": node.get("package_name"),
            "tags": list(node.get("tags") or []),
            "relation_name": node.get("relation_name"),
            "alias": node.get("alias"),
            "unrendered_config": node.get("unrendered_config"),
        }
        ds.tags = list({*(ds.tags or []), *(node.get("tags") or []), "dbt"})
        ds.last_synced_at = datetime.utcnow()

        # Replace columns from the manifest's column block (if present).
        manifest_columns = node.get("columns") or {}
        if manifest_columns:
            DatasetColumn.query.filter(DatasetColumn.dataset_id == ds.id).delete(
                synchronize_session=False
            )
            for idx, (col_name, col_meta) in enumerate(manifest_columns.items()):
                col_type = (col_meta or {}).get("data_type") or (col_meta or {}).get(
                    "type"
                )
                is_dttm = _looks_like_datetime(col_type, col_name)
                db.session.add(
                    DatasetColumn(
                        dataset_id=ds.id,
                        column_name=col_name,
                        verbose_name=(col_meta or {}).get("name") or col_name,
                        description=(col_meta or {}).get("description"),
                        type=col_type,
                        is_dttm=is_dttm,
                        groupby=not is_dttm or True,
                        filterable=True,
                        column_order=idx,
                        extra={"meta": (col_meta or {}).get("meta") or {}},
                    )
                )
            # Promote first datetime-looking column as default time dim
            if not ds.main_dttm_col:
                first_dttm = next(
                    (
                        c
                        for c in manifest_columns
                        if _looks_like_datetime(
                            (manifest_columns[c] or {}).get("data_type"), c
                        )
                    ),
                    None,
                )
                if first_dttm:
                    ds.main_dttm_col = first_dttm

        return created

    @classmethod
    def _validate_payload(cls, payload: Dict[str, Any]) -> None:
        if not (payload.get("name") or "").strip():
            raise DatasetValidationError("Dataset name is required")
        kind = payload.get("kind", DatasetKind.PHYSICAL.value)
        if kind == DatasetKind.PHYSICAL.value and not payload.get("table_name"):
            raise DatasetValidationError(
                "Physical dataset requires table_name"
            )
        if kind == DatasetKind.VIRTUAL.value and not (payload.get("sql") or "").strip():
            raise DatasetValidationError("Virtual dataset requires sql")


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def _build_column(dataset_id: UUID, col: Dict[str, Any]) -> DatasetColumn:
    return DatasetColumn(
        dataset_id=dataset_id,
        column_name=col["column_name"],
        verbose_name=col.get("verbose_name"),
        description=col.get("description"),
        expression=col.get("expression"),
        type=col.get("type"),
        is_dttm=bool(col.get("is_dttm", False)),
        is_active=bool(col.get("is_active", True)),
        groupby=bool(col.get("groupby", True)),
        filterable=bool(col.get("filterable", True)),
        is_hidden=bool(col.get("is_hidden", False)),
        python_date_format=col.get("python_date_format"),
        column_order=int(col.get("column_order", 0)),
        extra=col.get("extra") or {},
    )


def _build_metric(dataset_id: UUID, met: Dict[str, Any]) -> DatasetMetric:
    if not met.get("metric_name") or not met.get("expression"):
        raise DatasetValidationError(
            "metric requires both 'metric_name' and 'expression'"
        )
    return DatasetMetric(
        dataset_id=dataset_id,
        metric_name=met["metric_name"],
        verbose_name=met.get("verbose_name"),
        description=met.get("description"),
        expression=met["expression"],
        metric_type=met.get("metric_type"),
        d3format=met.get("d3format"),
        currency=met.get("currency"),
        warning_text=met.get("warning_text"),
        is_restricted=bool(met.get("is_restricted", False)),
        is_hidden=bool(met.get("is_hidden", False)),
        extra=met.get("extra") or {},
    )


def _load_manifest(manifest_path: Optional[str] = None) -> Dict[str, Any]:
    if manifest_path:
        path = Path(manifest_path)
    else:
        try:
            project_path = Path(
                current_app.config.get("DBT_PROJECT_PATH", "./dbt")
            )
        except RuntimeError:
            project_path = Path("./dbt")
        path = project_path / "target" / "manifest.json"
    if not path.exists():
        raise DbtManifestNotFoundError(
            f"dbt manifest not found at {path}. Run `dbt parse` first."
        )
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise DatasetServiceError(f"Invalid dbt manifest: {exc}") from exc


def _resolve_tenant_database(tenant_id: str) -> Optional[str]:
    """Return the tenant's ClickHouse database name (``tenant_<slug>``)."""
    try:
        from app.domains.tenants.domain.models import Tenant  # local import

        tenant = Tenant.query.filter(Tenant.id == UUID(str(tenant_id))).first()
        if tenant and tenant.slug:
            return f"tenant_{tenant.slug.replace('-', '_')}"
    except Exception:  # pragma: no cover - defensive
        logger.debug("Could not resolve tenant database for %s", tenant_id)
    return None


def _matches_tenant_db(
    tenant_database: str, node_schema: str, node_database: str
) -> bool:
    candidates = {s for s in (node_schema, node_database) if s}
    return tenant_database in candidates


_DATETIME_TYPE_HINTS = (
    "date",
    "time",
    "timestamp",
    "datetime",
)


def _looks_like_datetime(col_type: Optional[str], col_name: str) -> bool:
    typ = (col_type or "").lower()
    if any(h in typ for h in _DATETIME_TYPE_HINTS):
        return True
    name = (col_name or "").lower()
    return name in {"date", "datetime", "timestamp", "event_time", "occurred_at"} or (
        name.endswith("_at") or name.endswith("_date") or name.endswith("_time")
    )
