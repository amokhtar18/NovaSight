"""
Superset runtime configuration (loaded by Superset itself)
===========================================================

Superset reads its configuration from the Python module pointed to by
``SUPERSET_CONFIG_PATH``. Our Docker image / sidecar sets that to::

    SUPERSET_CONFIG_PATH=/app/app/domains/analytics/superset/superset_config.py

The configuration here:

* reuses NovaSight's existing **Postgres** instance (a separate logical
  database called ``superset`` for Superset metadata),
* reuses NovaSight's existing **Redis** for results / cache / Celery
  on dedicated logical DB indices (db=2..5),
* installs NovaSight's custom security manager and connection mutators
  so that every query is locked to the caller's tenant ClickHouse DB.

This file is intentionally importable WITHOUT Superset installed —
``apache-superset`` is only required at runtime by the Superset process.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Shared infrastructure (re-uses NovaSight services)
# ---------------------------------------------------------------------------

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "novasight")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "novasight")
SUPERSET_DB_NAME = os.getenv("SUPERSET_DB_NAME", "superset")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# ---------------------------------------------------------------------------
# Superset metadata DB (isolated logical DB inside the same Postgres server)
# ---------------------------------------------------------------------------

SQLALCHEMY_DATABASE_URI = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{SUPERSET_DB_NAME}"
)

# ---------------------------------------------------------------------------
# Redis layout (shared with NovaSight; documented in docker-compose.yml)
#
#   db=0 → NovaSight app cache         (existing)
#   db=1 → NovaSight flask-limiter     (existing)
#   db=2 → Superset RESULTS_BACKEND    (SQL Lab async results)
#   db=3 → Superset CACHE_CONFIG       (chart / data / form cache)
#   db=4 → Superset Celery broker
#   db=5 → Superset Celery result backend
# ---------------------------------------------------------------------------

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_URL": f"redis://{REDIS_HOST}:{REDIS_PORT}/3",
}
DATA_CACHE_CONFIG = {**CACHE_CONFIG, "CACHE_KEY_PREFIX": "superset_data_"}
FILTER_STATE_CACHE_CONFIG = {
    **CACHE_CONFIG,
    "CACHE_KEY_PREFIX": "superset_filter_",
}
EXPLORE_FORM_DATA_CACHE_CONFIG = {
    **CACHE_CONFIG,
    "CACHE_KEY_PREFIX": "superset_form_",
}


class CeleryConfig:  # pylint: disable=too-few-public-methods
    """Celery broker / backend on shared NovaSight Redis."""

    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/4"
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/5"
    worker_prefetch_multiplier = 1
    task_acks_late = False
    # Imported lazily — only available when Superset is installed.
    imports = ("superset.sql_lab", "superset.tasks.scheduler")


CELERY_CONFIG = CeleryConfig

# RESULTS_BACKEND is a cachelib instance, not a dict. Constructing it here
# keeps the configuration declarative; the import is guarded so this module
# remains importable in environments where cachelib is not installed
# (e.g. the main NovaSight Flask app's unit tests).
try:
    from cachelib.redis import RedisCache  # type: ignore

    RESULTS_BACKEND = RedisCache(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=2,
        key_prefix="superset_results_",
    )
except ImportError:  # pragma: no cover — only hit when cachelib absent
    RESULTS_BACKEND = None

# ---------------------------------------------------------------------------
# Security manager — bridges NovaSight JWT into FAB users
# ---------------------------------------------------------------------------

# Superset will import this dotted path at startup.
CUSTOM_SECURITY_MANAGER = (
    "app.domains.analytics.superset.security_bridge.NovaSightSecurityManager"
)

# ---------------------------------------------------------------------------
# Datasource lockdown — every query must hit the caller's tenant ClickHouse DB
# ---------------------------------------------------------------------------

# Superset evaluates these names at import time. We assign them lazily
# from `mutators.py` to avoid importing Superset internals here.
from app.domains.analytics.superset import mutators as _mutators  # noqa: E402

DB_CONNECTION_MUTATOR = _mutators.db_connection_mutator
SQLALCHEMY_URI_MUTATOR = _mutators.sqlalchemy_uri_mutator

# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

FEATURE_FLAGS = {
    "ALERT_REPORTS": False,
    "DASHBOARD_RBAC": True,
    "EMBEDDED_SUPERSET": True,
    "ENABLE_TEMPLATE_PROCESSING": True,
    "ROW_LEVEL_SECURITY": True,
    "ESTIMATE_QUERY_COST": True,
}

GUEST_ROLE_NAME = "Public"
GUEST_TOKEN_JWT_SECRET = os.getenv(
    "JWT_SECRET_KEY", "jwt-dev-secret-key-change-in-production"
)
GUEST_TOKEN_JWT_ALGO = "HS256"
GUEST_TOKEN_JWT_EXP_SECONDS = 300

# ---------------------------------------------------------------------------
# Web / Flask settings
# ---------------------------------------------------------------------------

SECRET_KEY = os.getenv(
    "SUPERSET_SECRET_KEY",
    os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
)

# Superset is reached only through NovaSight's proxy blueprint, so we
# can lock CORS down to the NovaSight backend host.
ENABLE_PROXY_FIX = True
WTF_CSRF_ENABLED = False  # disabled because all calls are JWT-authenticated
TALISMAN_ENABLED = False

APP_NAME = "NovaSight Analytics"
APP_ICON = "/static/assets/images/superset-logo-horiz.png"
