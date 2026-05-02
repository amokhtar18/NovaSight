"""
NovaSight API v1 Blueprint
==========================

Version 1 of the NovaSight REST API.
"""

from flask import Blueprint

api_v1_bp = Blueprint("api_v1", __name__)

# Identity domain routes (canonical)
from app.domains.identity.api import auth_routes   # noqa: F401
from app.domains.identity.api import user_routes   # noqa: F401
from app.domains.identity.api import role_routes   # noqa: F401

# Tenants domain routes (canonical)
from app.domains.tenants.api import tenant_routes  # noqa: F401

# Data Sources domain routes (canonical)
from app.domains.datasources.api import connection_routes  # noqa: F401

# Orchestration domain routes (canonical)
from app.domains.orchestration.api import dag_routes  # noqa: F401
from app.domains.orchestration.api import job_routes  # noqa: F401
from app.domains.orchestration.api.dagster_proxy import dagster_proxy_bp  # noqa: F401

# Analytics domain routes (canonical)
from app.domains.analytics.api import dashboard_routes  # noqa: F401
from app.domains.analytics.api import chart_routes  # noqa: F401

# Transformation domain routes (canonical)
from app.domains.transformation.api import semantic_routes  # noqa: F401
from app.domains.transformation.api import dbt_routes  # noqa: F401
from app.domains.transformation.api import mcp_routes  # noqa: F401
from app.domains.transformation.api import visual_model_routes  # noqa: F401

# Ingestion domain routes (canonical) - dlt pipelines
from app.domains.ingestion.api.dlt_routes import dlt_pipeline_bp  # noqa: F401
from app.domains.ingestion.api.dlt_uploads import dlt_uploads_bp  # noqa: F401

# AI domain routes (canonical)
from app.domains.ai.api import assistant_routes  # noqa: F401
from app.domains.ai.api import agent_config_routes  # noqa: F401
from app.domains.ai.api import mcp_routes  # noqa: F401
from app.domains.ai.api import ollama_config_routes  # noqa: F401

# Other route modules
from app.api.v1 import audit

# Register admin sub-blueprint
from app.api.v1.admin import admin_bp
api_v1_bp.register_blueprint(admin_bp)

# Register backup API (admin-only endpoints)
from app.domains.backup.api.routes import bp as backup_bp
api_v1_bp.register_blueprint(backup_bp)

# Register Dagster proxy (orchestration endpoints)
api_v1_bp.register_blueprint(dagster_proxy_bp)

# Register dlt pipeline routes (ingestion)
api_v1_bp.register_blueprint(dlt_pipeline_bp)
api_v1_bp.register_blueprint(dlt_uploads_bp)

# Optional Apache Superset proxy — only registered when SUPERSET_ENABLED=true.
# All Superset integration code is loaded lazily inside this guard so the
# default backend build never imports Superset internals.
from app.domains.analytics.superset import is_enabled as _superset_enabled  # noqa: E402
if _superset_enabled():
    from app.domains.analytics.superset.proxy_routes import (  # noqa: E402
        superset_proxy_bp,
    )
    from app.domains.analytics.superset.sqllab_routes import (  # noqa: E402
        sqllab_bp,
    )
    api_v1_bp.register_blueprint(superset_proxy_bp)
    api_v1_bp.register_blueprint(sqllab_bp)
