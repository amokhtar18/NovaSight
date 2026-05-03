"""
NovaSight Dataset Schemas
=========================

Pydantic schemas for the Superset-inspired :class:`Dataset` REST API.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DatasetKindEnum(str, Enum):
    PHYSICAL = "physical"
    VIRTUAL = "virtual"


class DatasetSourceEnum(str, Enum):
    DBT = "dbt"
    MANUAL = "manual"
    SQL_LAB = "sql_lab"


class DatasetColumnSchema(BaseModel):
    column_name: str = Field(..., min_length=1, max_length=250)
    verbose_name: Optional[str] = Field(None, max_length=1024)
    description: Optional[str] = None
    expression: Optional[str] = None
    type: Optional[str] = Field(None, max_length=64)
    is_dttm: bool = False
    is_active: bool = True
    groupby: bool = True
    filterable: bool = True
    is_hidden: bool = False
    python_date_format: Optional[str] = Field(None, max_length=255)
    column_order: int = 0
    extra: Dict[str, Any] = Field(default_factory=dict)


class DatasetMetricSchema(BaseModel):
    metric_name: str = Field(..., min_length=1, max_length=250)
    verbose_name: Optional[str] = Field(None, max_length=1024)
    description: Optional[str] = None
    expression: str = Field(..., min_length=1)
    metric_type: Optional[str] = Field(None, max_length=64)
    d3format: Optional[str] = Field(None, max_length=128)
    currency: Optional[str] = Field(None, max_length=8)
    warning_text: Optional[str] = None
    is_restricted: bool = False
    is_hidden: bool = False
    extra: Dict[str, Any] = Field(default_factory=dict)


class DatasetCreateSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=250)
    description: Optional[str] = None
    kind: DatasetKindEnum = DatasetKindEnum.PHYSICAL
    source: DatasetSourceEnum = DatasetSourceEnum.MANUAL
    database_name: Optional[str] = Field(None, max_length=250)
    schema_: Optional[str] = Field(None, max_length=250, alias="schema")
    table_name: Optional[str] = Field(None, max_length=250)
    sql: Optional[str] = None
    main_dttm_col: Optional[str] = Field(None, max_length=250)
    default_endpoint: Optional[str] = Field(None, max_length=500)
    cache_timeout_seconds: Optional[int] = Field(None, ge=0, le=86400)
    extra: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    is_featured: bool = False
    is_managed: bool = False
    columns: List[DatasetColumnSchema] = Field(default_factory=list)
    metrics: List[DatasetMetricSchema] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v

    def to_payload(self) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True)
        # Pydantic strips trailing underscore via alias; ensure ``schema`` key is set.
        return data


class DatasetUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=250)
    description: Optional[str] = None
    kind: Optional[DatasetKindEnum] = None
    source: Optional[DatasetSourceEnum] = None
    database_name: Optional[str] = Field(None, max_length=250)
    schema_: Optional[str] = Field(None, max_length=250, alias="schema")
    table_name: Optional[str] = Field(None, max_length=250)
    sql: Optional[str] = None
    main_dttm_col: Optional[str] = Field(None, max_length=250)
    default_endpoint: Optional[str] = Field(None, max_length=500)
    cache_timeout_seconds: Optional[int] = Field(None, ge=0, le=86400)
    extra: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    force: bool = Field(False, alias="_force")

    model_config = ConfigDict(populate_by_name=True)


class DatasetSyncDbtSchema(BaseModel):
    """Request body for ``POST /datasets/sync-dbt``."""

    manifest_path: Optional[str] = None
    deactivate_missing: bool = True
