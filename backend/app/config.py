"""
NovaSight Configuration Module
==============================

Environment-specific configuration classes.
"""

import os
from datetime import timedelta
from typing import Type


class BaseConfig:
    """Base configuration with common settings."""
    
    # Flask Core
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    # SQLAlchemy (PostgreSQL Metadata Store)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://novasight:novasight@localhost:5432/novasight_platform"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"
    
    # Redis Configuration
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # ClickHouse Configuration
    CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
    CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
    CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
    CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "novasight")
    
    # Airflow Configuration
    AIRFLOW_BASE_URL = os.getenv("AIRFLOW_BASE_URL", "http://localhost:8080")
    AIRFLOW_USERNAME = os.getenv("AIRFLOW_USERNAME", "airflow")
    AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "airflow")
    
    # Ollama LLM Configuration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Security
    CREDENTIAL_ENCRYPTION_KEY = os.getenv("CREDENTIAL_ENCRYPTION_KEY", None)
    
    # Pagination Defaults
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""
    
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    
    # Allow more permissive CORS in development
    CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]


class TestingConfig(BaseConfig):
    """Testing environment configuration."""
    
    TESTING = True
    DEBUG = True
    
    # Use in-memory SQLite for faster tests
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    
    # Disable JWT in tests by default (can be overridden)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    
    # Faster password hashing for tests
    BCRYPT_LOG_ROUNDS = 4


class ProductionConfig(BaseConfig):
    """Production environment configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Enforce secure settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    
    # Stricter JWT settings
    JWT_COOKIE_SECURE = True


# Configuration mapping
config_map: dict[str, Type[BaseConfig]] = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(config_name: str = "default") -> BaseConfig:
    """
    Get configuration class by name.
    
    Args:
        config_name: Configuration environment name
    
    Returns:
        Configuration class instance
    """
    return config_map.get(config_name, DevelopmentConfig)
