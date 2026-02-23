"""
NovaSight Alembic Migrations Environment
========================================

Configuration for running database migrations.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_config
from app.extensions import db

# Import all models so that db.metadata is populated
import app.models  # noqa: F401

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
# Handle both running from /app and /app/migrations
if config.config_file_name is not None:
    config_path = config.config_file_name
    if not os.path.isabs(config_path):
        # Try relative to backend root first
        backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        abs_path = os.path.join(backend_root, config_path)
        if os.path.exists(abs_path):
            config_path = abs_path
    if os.path.exists(config_path):
        fileConfig(config_path)

# Get database URL from app config
app_config = get_config(os.getenv("FLASK_ENV", "development"))
config.set_main_option("sqlalchemy.url", app_config.SQLALCHEMY_DATABASE_URI)

# Add model's MetaData object for 'autogenerate' support
target_metadata = db.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This generates SQL script without needing a database connection.
    Useful for generating migration scripts for review or manual execution.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    Creates an Engine and associates a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
