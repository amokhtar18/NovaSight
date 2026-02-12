"""
NovaSight Database Models
=========================

SQLAlchemy models for the NovaSight metadata store.

Uses lazy imports (PEP 562 ``__getattr__``) for domain models to
break circular import chains.  Only mixins and the non-shim
``audit`` module are imported eagerly because they have no domain
dependencies.
"""

import importlib as _importlib

# ── Eagerly-loaded (no circular risk) ──────────────────────────
from app.models.mixins import TenantMixin, TimestampMixin, AuditMixin  # noqa: F401
from app.models.audit import AuditLog, AuditSeverity  # noqa: F401

# ── Lazy-load map: symbol → (module_path, name) ───────────────
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {}

def _register(module: str, *names: str) -> None:
    for n in names:
        _LAZY_IMPORTS[n] = (module, n)

_register(
    "app.domains.tenants.domain.models",
    "Tenant", "TenantStatus", "SubscriptionPlan",
    "InfrastructureConfig", "InfrastructureType", "DEFAULT_INFRASTRUCTURE_CONFIGS",
)
_register(
    "app.domains.identity.domain.models",
    "User", "Role", "UserRole", "UserStatus",
    "Permission", "ResourcePermission", "RoleHierarchy", "role_permissions",
)
_register(
    "app.domains.datasources.domain.models",
    "DataConnection", "DatabaseType", "ConnectionStatus",
)
_register(
    "app.domains.datasources.domain.value_objects",
    "DataSourceColumn", "DataSourceTable", "DataSourceSchema",
)
_register(
    "app.domains.orchestration.domain.models",
    "DagConfig", "DagVersion", "TaskConfig", "DagStatus",
    "ScheduleType", "TriggerRule", "TaskType",
)
_register(
    "app.domains.compute.domain.models",
    "PySparkApp", "PySparkAppStatus", "SourceType",
    "WriteMode", "SCDType", "CDCType",
)
_register(
    "app.domains.transformation.domain.models",
    "SemanticModel", "Dimension", "Measure", "Relationship",
    "DimensionType", "AggregationType", "ModelType",
    "RelationshipType", "JoinType",
)
_register(
    "app.domains.analytics.domain.models",
    "Dashboard", "Widget", "WidgetType",
)
_register(
    "app.domains.analytics.domain.chart_models",
    "Chart", "ChartFolder", "ChartType", "ChartSourceType", "DashboardChart",
)


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        mod = _importlib.import_module(module_path)
        value = getattr(mod, attr)
        # Cache on the module so __getattr__ is not called again
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Core models
    "Tenant",
    "TenantStatus",
    "SubscriptionPlan",
    "User",
    "UserStatus",
    "Role",
    "UserRole",
    "DataConnection",
    "DatabaseType",
    "ConnectionStatus",
    "DagConfig",
    "DagVersion",
    "TaskConfig",
    "DagStatus",
    "ScheduleType",
    "TriggerRule",
    "TaskType",
    "AuditLog",
    "AuditSeverity",
    # RBAC models
    "Permission",
    "ResourcePermission",
    "RoleHierarchy",
    "role_permissions",
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
    # Chart models
    "Chart",
    "ChartFolder",
    "ChartType",
    "ChartSourceType",
    "DashboardChart",
    # Infrastructure config models
    "InfrastructureConfig",
    "InfrastructureType",
    "DEFAULT_INFRASTRUCTURE_CONFIGS",
    # Mixins
    "TenantMixin",
    "TimestampMixin",
    "AuditMixin",
]
