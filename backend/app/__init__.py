"""
NovaSight Backend Application
=============================

Self-Service End-to-End BI Solution Backend API.
Flask-based REST API with multi-tenant architecture.
"""

from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import logging
import os

from app.config import get_config
from app.extensions import db, migrate, jwt, redis_client, limiter

logger = logging.getLogger(__name__)


def create_app(config_name: str = None) -> Flask:
    """
    Application factory for creating Flask app instances.
    
    Args:
        config_name: Configuration environment name (development, testing, production)
    
    Returns:
        Configured Flask application instance
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    
    app = Flask(__name__)
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize extensions
    _init_extensions(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    # Register error handlers
    _register_error_handlers(app)
    
    # Register middleware
    _register_middleware(app)
    
    # Configure logging
    _configure_logging(app)
    
    # Register CLI commands
    _register_commands(app)
    
    # Auto-seed default users on first startup (dev/demo)
    _auto_seed(app)

    # Optional Superset integration — register tenant lifecycle hooks
    # so that creating a tenant automatically provisions its Superset
    # database row pointing at the tenant's ClickHouse DB.
    _register_superset_lifecycle(app)

    logger.info(f"NovaSight API initialized in {config_name} mode")
    
    return app


def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    # Configure CORS with explicit settings for preflight requests
    CORS(app, 
         resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}},
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
         expose_headers=["Content-Type", "Authorization"])
    
    # Initialize Redis if configured
    if app.config.get("REDIS_URL"):
        redis_client.init_app(app)
        # Use Redis for rate limiting in production
        limiter._storage_uri = app.config.get("REDIS_URL")
    
    # Initialize rate limiter with OPTIONS exemption
    @limiter.request_filter
    def _rate_limit_exempt():
        """Exempt OPTIONS requests from rate limiting (CORS preflight)."""
        return request.method == "OPTIONS"
    
    limiter.init_app(app)
    
    # Register JWT handlers (callbacks for token blacklist, etc.)
    from app.platform.auth.jwt_handler import register_jwt_handlers
    register_jwt_handlers(jwt)


def _register_blueprints(app: Flask) -> None:
    """Register API blueprints."""
    from app.api.v1 import api_v1_bp
    from app.api.health import health_bp, health_api_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(health_api_bp, url_prefix="/api/v1")
    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")
    
    # Register Flask-RESTX API documentation (Swagger UI at /api/v1/docs)
    from app.api.swagger import init_api_docs
    init_api_docs(app)


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""
    from app.errors import register_error_handlers
    register_error_handlers(app)


def _configure_logging(app: Flask) -> None:
    """Configure application logging with structured JSON output."""
    from app.utils.logger import setup_logging
    setup_logging(app)


def _register_middleware(app: Flask) -> None:
    """Register request/response middleware."""
    from app.middleware import TenantContextMiddleware, setup_metrics
    from app.middleware.request_logging import setup_request_logging
    
    # Initialize request logging middleware
    setup_request_logging(app)
    
    # Initialize tenant context middleware
    TenantContextMiddleware(app)
    
    # Initialize metrics middleware (exposes /metrics endpoint)
    if app.config.get("ENABLE_METRICS", True):
        setup_metrics(app)


def _register_commands(app: Flask) -> None:
    """Register Flask CLI commands."""
    from app.commands import register_commands
    register_commands(app)


def _auto_seed(app: Flask) -> None:
    """
    Automatically seed default test users on first startup.

    Controlled by the ``SEED_USERS`` environment variable:
        - ``true`` / ``1`` / ``yes`` (default in dev) → seed on startup
        - ``false`` / ``0`` / ``no``                  → skip

    Safe to call repeatedly — existing records are silently skipped.
    """
    seed_flag = os.getenv("SEED_USERS", "true").strip().lower()
    if seed_flag not in ("true", "1", "yes"):
        return

    with app.app_context():
        try:
            from app.seed import seed_default_data
            summary = seed_default_data()
            created = summary.get("users_created", [])
            if created:
                logger.info(
                    "Auto-seeded %d test user(s): %s",
                    len(created),
                    ", ".join(created),
                )
            else:
                logger.debug("Seed users already present — nothing to do")
        except Exception as exc:
            # Never crash the app because seeding failed
            logger.warning("Auto-seed skipped due to error: %s", exc)


def _register_superset_lifecycle(app: Flask) -> None:
    """
    Register Superset provisioning hooks on the Tenant model when the
    integration is enabled. Idempotent and safe to call repeatedly.
    """
    try:
        from app.domains.analytics.superset import is_enabled
        if not is_enabled():
            return
        from app.domains.analytics.superset.lifecycle import register
        register()
    except Exception as exc:  # noqa: BLE001 — never crash app boot
        logger.warning(
            "Superset lifecycle hook registration skipped: %s", exc
        )
