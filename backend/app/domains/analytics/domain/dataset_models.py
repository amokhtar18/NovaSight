"""
NovaSight Dataset Models (Superset-inspired)
=============================================

Datasets are the canonical *queryable* abstraction that powers Charts and
Dashboards. They are heavily inspired by Apache Superset's
``SqlaTable``/``TableColumn``/``SqlMetric`` model, adapted for NovaSight's
multi-tenant, dbt-first architecture.

A :class:`Dataset` represents either:

* A **physical** dbt-materialized table/view in the tenant's ClickHouse
  database (``DatasetKind.PHYSICAL``). These are auto-synced from the dbt
  ``manifest.json`` for any node whose ``config.materialized`` is one of
  ``table``, ``view``, ``incremental``, ``materialized_view``.
* A **virtual** dataset backed by a saved SQL query
  (``DatasetKind.VIRTUAL``) — equivalent to Superset's "SQL dataset".

Each dataset owns a collection of :class:`DatasetColumn` rows (which are the
groupable/filterable dimensions, including ``is_dttm`` time columns) and
:class:`DatasetMetric` rows (named, expression-based aggregates, e.g.
``SUM(revenue)``). Charts and Widgets reference a dataset via ``dataset_id``
and pick column / metric names from it.

This module is intentionally self-contained and does **not** import the
existing :mod:`semantic` models so it can be adopted incrementally.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DatasetKind(str, Enum):
    """How the dataset's rows are produced."""

    PHYSICAL = "physical"  # backed by a real table/view (e.g. dbt materialized model)
    VIRTUAL = "virtual"    # backed by a saved SQL query


class DatasetSource(str, Enum):
    """Origin of the dataset definition."""

    DBT = "dbt"            # auto-synced from dbt manifest
    MANUAL = "manual"      # user-created
    SQL_LAB = "sql_lab"    # promoted from the SQL editor


class DbtMaterialization(str, Enum):
    """Subset of dbt materializations exposed as datasets."""

    TABLE = "table"
    VIEW = "view"
    INCREMENTAL = "incremental"
    MATERIALIZED_VIEW = "materialized_view"


# Materializations that produce a queryable physical relation. Anything
# outside this set (``ephemeral``, ``test``, ``seed`` configs we don't want,
# etc.) is skipped by the dbt sync.
MATERIALIZED_DBT_TYPES = {m.value for m in DbtMaterialization}


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


class Dataset(TenantMixin, TimestampMixin, db.Model):
    """
    Tenant-scoped, queryable dataset usable by charts and dashboards.

    Ports the core fields from Superset's ``SqlaTable``:

    * ``database`` / ``schema`` / ``table_name`` for physical datasets,
    * ``sql`` for virtual datasets,
    * ``main_dttm_col`` for the default time column,
    * ``default_endpoint`` / ``description`` / ``cache_timeout`` etc.

    NovaSight extensions:

    * ``kind`` — physical vs virtual (Superset infers this; we make it explicit).
    * ``source`` + ``dbt_unique_id`` — link back to the originating dbt node so
      we can re-sync deterministically.
    * ``tenant_id`` — every dataset is tenant-scoped via :class:`TenantMixin`.
    """

    __tablename__ = "datasets"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identity ---------------------------------------------------------------
    name = db.Column(String(250), nullable=False, index=True)
    """Human-readable dataset name (Superset's ``table_name`` user-facing label)."""

    description = db.Column(Text, nullable=True)

    kind = db.Column(
        SQLEnum(DatasetKind, name="dataset_kind"),
        nullable=False,
        default=DatasetKind.PHYSICAL,
        index=True,
    )

    source = db.Column(
        SQLEnum(DatasetSource, name="dataset_source"),
        nullable=False,
        default=DatasetSource.MANUAL,
        index=True,
    )

    # Physical-dataset fields (mirror Superset SqlaTable) --------------------
    database_name = db.Column(String(250), nullable=True, index=True)
    """ClickHouse database (e.g. ``tenant_acme``)."""

    schema = db.Column(String(250), nullable=True, index=True)
    """Optional schema. For ClickHouse this is usually equal to ``database_name``."""

    table_name = db.Column(String(250), nullable=True, index=True)
    """Physical table or view name."""

    # Virtual-dataset fields -------------------------------------------------
    sql = db.Column(Text, nullable=True)
    """SQL expression for virtual datasets (used as a sub-query)."""

    # dbt linkage ------------------------------------------------------------
    dbt_unique_id = db.Column(String(500), nullable=True, index=True)
    """Stable dbt manifest unique_id, e.g. ``model.novasight.fct_revenue``."""

    dbt_materialization = db.Column(
        SQLEnum(DbtMaterialization, name="dbt_materialization"),
        nullable=True,
    )

    dbt_meta = db.Column(JSONB, nullable=True)
    """Snapshot of selected dbt config / meta at sync time (tags, package, fqn)."""

    # Visualization defaults -------------------------------------------------
    main_dttm_col = db.Column(String(250), nullable=True)
    """Default time column for charts (Superset parity)."""

    default_endpoint = db.Column(String(500), nullable=True)
    """Optional default chart/explore URL (Superset parity)."""

    cache_timeout_seconds = db.Column(Integer, nullable=True)
    """Per-dataset query cache TTL override. ``None`` = use chart default."""

    extra = db.Column(JSONB, nullable=False, default=dict)
    """Free-form JSON for advanced settings (filters, certifications, etc.)."""

    # Governance / display ---------------------------------------------------
    is_managed = db.Column(Boolean, nullable=False, default=False, index=True)
    """``True`` for datasets managed by an automated process (e.g. dbt sync).
    Managed datasets are read-only in the UI."""

    is_featured = db.Column(Boolean, nullable=False, default=False)
    tags = db.Column(ARRAY(String), nullable=False, default=list)

    owner_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    last_synced_at = db.Column(DateTime, nullable=True)

    is_deleted = db.Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = db.Column(DateTime, nullable=True)

    # Relationships ----------------------------------------------------------
    columns = relationship(
        "DatasetColumn",
        back_populates="dataset",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="DatasetColumn.column_order",
    )
    metrics = relationship(
        "DatasetMetric",
        back_populates="dataset",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    owner = relationship("User", foreign_keys=[owner_id], lazy="select")

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_dataset_tenant_name"),
        UniqueConstraint(
            "tenant_id", "dbt_unique_id", name="uq_dataset_tenant_dbt_unique_id"
        ),
    )

    # ---- helpers ----------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover - debug only
        return f"<Dataset {self.name} ({self.kind.value})>"

    @property
    def qualified_table(self) -> Optional[str]:
        """Return ``"schema"."table"`` for physical datasets, or ``None``."""
        if self.kind != DatasetKind.PHYSICAL or not self.table_name:
            return None
        schema = self.schema or self.database_name
        if schema:
            return f'"{schema}"."{self.table_name}"'
        return f'"{self.table_name}"'

    def to_dict(self, include_columns: bool = False) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "kind": self.kind.value,
            "source": self.source.value,
            "database_name": self.database_name,
            "schema": self.schema,
            "table_name": self.table_name,
            "sql": self.sql,
            "dbt_unique_id": self.dbt_unique_id,
            "dbt_materialization": (
                self.dbt_materialization.value if self.dbt_materialization else None
            ),
            "dbt_meta": self.dbt_meta or {},
            "main_dttm_col": self.main_dttm_col,
            "default_endpoint": self.default_endpoint,
            "cache_timeout_seconds": self.cache_timeout_seconds,
            "extra": self.extra or {},
            "is_managed": self.is_managed,
            "is_featured": self.is_featured,
            "tags": list(self.tags or []),
            "owner_id": str(self.owner_id) if self.owner_id else None,
            "tenant_id": str(self.tenant_id),
            "last_synced_at": (
                self.last_synced_at.isoformat() if self.last_synced_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_columns:
            result["columns"] = [c.to_dict() for c in self.columns]
            result["metrics"] = [m.to_dict() for m in self.metrics]
        return result


# ---------------------------------------------------------------------------
# Dataset columns (≈ Superset TableColumn)
# ---------------------------------------------------------------------------


class DatasetColumn(TimestampMixin, db.Model):
    """A queryable column on a :class:`Dataset` — Superset ``TableColumn`` parity."""

    __tablename__ = "dataset_columns"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    column_name = db.Column(String(250), nullable=False)
    verbose_name = db.Column(String(1024), nullable=True)
    description = db.Column(Text, nullable=True)

    # Either a physical column name or a SQL expression (Superset parity).
    expression = db.Column(Text, nullable=True)

    type = db.Column(String(64), nullable=True)
    """Source-provided type, e.g. ``String``, ``Int64``, ``DateTime``."""

    # Superset-style flags ---------------------------------------------------
    is_dttm = db.Column(Boolean, nullable=False, default=False)
    is_active = db.Column(Boolean, nullable=False, default=True)
    groupby = db.Column(Boolean, nullable=False, default=True)
    filterable = db.Column(Boolean, nullable=False, default=True)
    is_hidden = db.Column(Boolean, nullable=False, default=False)

    python_date_format = db.Column(String(255), nullable=True)
    column_order = db.Column(Integer, nullable=False, default=0)

    extra = db.Column(JSONB, nullable=False, default=dict)

    dataset = relationship("Dataset", back_populates="columns")

    __table_args__ = (
        UniqueConstraint("dataset_id", "column_name", name="uq_dataset_column_name"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug only
        return f"<DatasetColumn {self.column_name} ({self.type})>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "dataset_id": str(self.dataset_id),
            "column_name": self.column_name,
            "verbose_name": self.verbose_name,
            "description": self.description,
            "expression": self.expression,
            "type": self.type,
            "is_dttm": self.is_dttm,
            "is_active": self.is_active,
            "groupby": self.groupby,
            "filterable": self.filterable,
            "is_hidden": self.is_hidden,
            "python_date_format": self.python_date_format,
            "column_order": self.column_order,
            "extra": self.extra or {},
        }


# ---------------------------------------------------------------------------
# Dataset metrics (≈ Superset SqlMetric)
# ---------------------------------------------------------------------------


class DatasetMetric(TimestampMixin, db.Model):
    """A named SQL aggregate on a :class:`Dataset` — Superset ``SqlMetric`` parity."""

    __tablename__ = "dataset_metrics"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    dataset_id = db.Column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    metric_name = db.Column(String(250), nullable=False)
    verbose_name = db.Column(String(1024), nullable=True)
    description = db.Column(Text, nullable=True)

    # SQL aggregate, e.g. ``SUM(revenue)`` or ``COUNT(DISTINCT order_id)``.
    expression = db.Column(Text, nullable=False)

    metric_type = db.Column(String(64), nullable=True)  # sum, count, avg, …
    d3format = db.Column(String(128), nullable=True)
    currency = db.Column(String(8), nullable=True)
    warning_text = db.Column(Text, nullable=True)

    is_restricted = db.Column(Boolean, nullable=False, default=False)
    is_hidden = db.Column(Boolean, nullable=False, default=False)

    extra = db.Column(JSONB, nullable=False, default=dict)

    dataset = relationship("Dataset", back_populates="metrics")

    __table_args__ = (
        UniqueConstraint("dataset_id", "metric_name", name="uq_dataset_metric_name"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug only
        return f"<DatasetMetric {self.metric_name}>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": str(self.id),
            "dataset_id": str(self.dataset_id),
            "metric_name": self.metric_name,
            "verbose_name": self.verbose_name,
            "description": self.description,
            "expression": self.expression,
            "metric_type": self.metric_type,
            "d3format": self.d3format,
            "currency": self.currency,
            "warning_text": self.warning_text,
            "is_restricted": self.is_restricted,
            "is_hidden": self.is_hidden,
            "extra": self.extra or {},
        }
