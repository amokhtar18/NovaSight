"""
NovaSight Backend Application
=============================

Self-Service End-to-End BI Solution Backend API.
Flask-based REST API with multi-tenant architecture.
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
import logging
import os

from app.config import get_config
from app.extensions import db, migrate, jwt, redis_client

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
    
    # Configure logging
    _configure_logging(app)
    
    logger.info(f"NovaSight API initialized in {config_name} mode")
    
    return app


def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions."""
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})
    
    # Initialize Redis if configured
    if app.config.get("REDIS_URL"):
        redis_client.init_app(app)


def _register_blueprints(app: Flask) -> None:
    """Register API blueprints."""
    from app.api.v1 import api_v1_bp
    from app.api.health import health_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""
    from app.errors import register_error_handlers
    register_error_handlers(app)


def _configure_logging(app: Flask) -> None:
    """Configure application logging."""
    log_level = app.config.get("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
