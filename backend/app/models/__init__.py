"""
NovaSight Database Models
=========================

SQLAlchemy models for the NovaSight metadata store.
"""

from app.models.tenant import Tenant, TenantStatus
from app.models.user import User, Role, UserRole, UserStatus
from app.models.connection import DataConnection
from app.models.dag import DagConfig, DagVersion, TaskConfig
from app.models.audit import AuditLog
from app.models.pyspark_app import (
    PySparkApp,
    PySparkAppStatus,
    SourceType,
    WriteMode,
    SCDType,
    CDCType,
)
from app.models.data_source import (
    DataSourceColumn,
    DataSourceTable,
    DataSourceSchema,
    ColumnDataType,
)
from app.models.semantic import (
    SemanticModel,
    Dimension,
    Measure,
    Relationship,
    DimensionType,
    AggregationType,
    ModelType,
    RelationshipType,
    JoinType,
)
from app.models.dashboard import (
    Dashboard,
    Widget,
    WidgetType,
)
from app.models.mixins import (
    TenantMixin,
    TimestampMixin,
    AuditMixin,
    SoftDeleteMixin,
)

__all__ = [
    # Core models
    "Tenant",
    "TenantStatus",
    "User",
    "UserStatus",
    "Role",
    "UserRole",
    "DataConnection",
    "DagConfig",
    "DagVersion",
    "TaskConfig",
    "AuditLog",
    # PySpark models
    "PySparkApp",
    "PySparkAppStatus",
    "SourceType",
    "WriteMode",
    "SCDType",
    "CDCType",
    # Data source models
    "DataSourceColumn",
    "DataSourceTable",
    "DataSourceSchema",
    "ColumnDataType",
    # Semantic layer models
    "SemanticModel",
    "Dimension",
    "Measure",
    "Relationship",
    "DimensionType",
    "AggregationType",
    "ModelType",
    "RelationshipType",
    "JoinType",
    # Dashboard models
    "Dashboard",
    "Widget",
    "WidgetType",
    # Mixins
    "TenantMixin",
    "TimestampMixin",
    "AuditMixin",
    "SoftDeleteMixin",
]
