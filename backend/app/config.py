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
    CLICKHOUSE_PORT = int(os.getenv("CLICKHOUSE_PORT", "9000"))
    CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
    CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")
    CLICKHOUSE_DATABASE = os.getenv("CLICKHOUSE_DATABASE", "novasight")
    
    # Spark Configuration
    SPARK_MASTER_HOST = os.getenv("SPARK_MASTER_HOST", "spark-master")
    SPARK_MASTER_PORT = int(os.getenv("SPARK_MASTER_PORT", "7077"))
    SPARK_MASTER_URL = os.getenv("SPARK_MASTER_URL", "spark://spark-master:7077")
    SPARK_DRIVER_MEMORY = os.getenv("SPARK_DRIVER_MEMORY", "2g")
    SPARK_EXECUTOR_MEMORY = os.getenv("SPARK_EXECUTOR_MEMORY", "2g")
    SPARK_EXECUTOR_CORES = int(os.getenv("SPARK_EXECUTOR_CORES", "2"))
    
    # Dagster Configuration (Primary Orchestrator)
    DAGSTER_HOST = os.getenv("DAGSTER_HOST", "localhost")
    DAGSTER_PORT = int(os.getenv("DAGSTER_PORT", "3000"))
    DAGSTER_GRAPHQL_URL = os.getenv("DAGSTER_GRAPHQL_URL", "http://localhost:3000/graphql")
    DAGSTER_MAX_CONCURRENT_RUNS = int(os.getenv("DAGSTER_MAX_CONCURRENT_RUNS", "10"))
    DAGSTER_SPARK_CONCURRENCY_LIMIT = int(os.getenv("DAGSTER_SPARK_CONCURRENCY_LIMIT", "3"))
    DAGSTER_DBT_CONCURRENCY_LIMIT = int(os.getenv("DAGSTER_DBT_CONCURRENCY_LIMIT", "2"))
    
    # Ollama LLM Configuration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # dbt Configuration
    DBT_PROJECT_PATH = os.getenv("DBT_PROJECT_PATH", "./dbt")
    DBT_TARGET = os.getenv("DBT_TARGET", "dev")
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    JSON_LOGS = os.getenv("JSON_LOGS", "true").lower() in ("true", "1", "yes")
    
    # Metrics
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() in ("true", "1", "yes")
    
    # Security & Encryption
    # ENCRYPTION_MASTER_KEY is the preferred key for AES-256 encryption
    # CREDENTIAL_ENCRYPTION_KEY is supported for backward compatibility
    ENCRYPTION_MASTER_KEY = os.getenv("ENCRYPTION_MASTER_KEY", None)
    CREDENTIAL_ENCRYPTION_KEY = os.getenv(
        "CREDENTIAL_ENCRYPTION_KEY",
        os.getenv("ENCRYPTION_MASTER_KEY", None)
    )
    
    # Backup & Recovery Configuration
    BACKUP_S3_BUCKET = os.getenv("BACKUP_S3_BUCKET", "novasight-backups")
    BACKUP_KMS_KEY_ID = os.getenv("BACKUP_KMS_KEY_ID", "")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    KUBERNETES_NAMESPACE = os.getenv("KUBERNETES_NAMESPACE", "novasight")
    
    # Pagination Defaults
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    # File-Based Data Sources
    FILE_UPLOAD_MAX_SIZE_MB = int(os.getenv("FILE_UPLOAD_MAX_SIZE_MB", "200"))
    FILE_UPLOAD_MAX_SIZE_BYTES = FILE_UPLOAD_MAX_SIZE_MB * 1024 * 1024
    FILE_STORAGE_ROOT = os.getenv(
        "FILE_STORAGE_ROOT",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "file_storage"),
    )
    FILE_UPLOAD_ALLOWED_EXTENSIONS = {
        ".csv", ".tsv", ".txt", ".json", ".parquet",
        ".xlsx", ".xls",
        ".sqlite", ".db", ".sqlite3",
    }
    FILE_UPLOAD_TOKEN_TTL_SECONDS = int(os.getenv("FILE_UPLOAD_TOKEN_TTL_SECONDS", "3600"))
    CLAMAV_ENABLED = os.getenv("CLAMAV_ENABLED", "true").lower() in ("true", "1", "yes")
    CLAMAV_HOST = os.getenv("CLAMAV_HOST", "localhost")
    CLAMAV_PORT = int(os.getenv("CLAMAV_PORT", "3310"))


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""
    
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    JSON_LOGS = False  # Human-readable logs in development
    
    # Allow more permissive CORS in development
    CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    
    # Auto-seed test users on startup
    SEED_USERS = True


class TestingConfig(BaseConfig):
    """Testing environment configuration."""
    
    TESTING = True
    DEBUG = True
    JSON_LOGS = False  # Human-readable logs in tests
    
    # Use PostgreSQL for tests to support JSONB, UUID, etc.
    # Falls back to SQLite only if DATABASE_URL not set
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql://novasight:novasight@localhost:5432/novasight_test"
        )
    )
    
    # Reduced pool for tests
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 5,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }
    
    # Disable rate limiting in tests
    RATELIMIT_ENABLED = False
    
    # Disable JWT in tests by default (can be overridden)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    
    # Faster password hashing for tests
    BCRYPT_LOG_ROUNDS = 4


class ProductionConfig(BaseConfig):
    """Production environment configuration."""
    
    DEBUG = False
    TESTING = False
    
    # Enforce required secrets — fail fast if missing
    SECRET_KEY = os.environ["SECRET_KEY"]  # type: ignore[assignment]
    JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]  # type: ignore[assignment]
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]  # type: ignore[assignment]
    
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
