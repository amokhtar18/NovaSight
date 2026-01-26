"""
NovaSight Flask Extensions
==========================

Centralized extension instances for Flask application.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from redis import Redis
from typing import Optional


class RedisClient:
    """Redis client wrapper for Flask application."""
    
    def __init__(self, app=None):
        self._client: Optional[Redis] = None
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize Redis client with Flask app configuration."""
        redis_url = app.config.get("REDIS_URL")
        if redis_url:
            self._client = Redis.from_url(redis_url, decode_responses=True)
    
    @property
    def client(self) -> Optional[Redis]:
        """Get Redis client instance."""
        return self._client
    
    def __getattr__(self, name):
        """Proxy attribute access to Redis client."""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call init_app() first.")
        return getattr(self._client, name)


# SQLAlchemy database instance
db = SQLAlchemy()

# Flask-Migrate instance
migrate = Migrate()

# JWT Manager instance
jwt = JWTManager()

# Redis client instance
redis_client = RedisClient()
