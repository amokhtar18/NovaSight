"""
NovaSight Tenant Utilities
==========================

Helper functions for tenant management and schema operations.
"""

from typing import Optional, List
from flask import g, has_request_context
from sqlalchemy import text
import logging
import re

from app.extensions import db

logger = logging.getLogger(__name__)


def get_tenant_schema_name(tenant_slug: str) -> str:
    """
    Generate PostgreSQL schema name from tenant slug.
    
    Args:
        tenant_slug: Tenant's URL-safe slug
    
    Returns:
        Schema name in format: tenant_{slug}
    """
    # Sanitize slug to ensure valid PostgreSQL identifier
    clean_slug = re.sub(r'[^a-z0-9_]', '_', tenant_slug.lower())
    return f"tenant_{clean_slug}"


def create_tenant_schema(tenant_slug: str) -> bool:
    """
    Create PostgreSQL schema for a tenant.
    
    Args:
        tenant_slug: Tenant's URL-safe slug
    
    Returns:
        True if schema was created successfully
    """
    schema_name = get_tenant_schema_name(tenant_slug)
    
    try:
        # Validate schema name format
        if not re.match(r'^tenant_[a-z0-9_]+$', schema_name):
            raise ValueError(f"Invalid schema name: {schema_name}")
        
        # Create schema if it doesn't exist
        db.session.execute(
            text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        )
        db.session.commit()
        
        logger.info(f"Created schema: {schema_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create schema {schema_name}: {e}")
        db.session.rollback()
        return False


def drop_tenant_schema(tenant_slug: str, cascade: bool = False) -> bool:
    """
    Drop PostgreSQL schema for a tenant.
    
    WARNING: This permanently deletes all tenant data!
    
    Args:
        tenant_slug: Tenant's URL-safe slug
        cascade: If True, drop all objects in schema
    
    Returns:
        True if schema was dropped successfully
    """
    schema_name = get_tenant_schema_name(tenant_slug)
    
    try:
        cascade_sql = "CASCADE" if cascade else "RESTRICT"
        db.session.execute(
            text(f"DROP SCHEMA IF EXISTS {schema_name} {cascade_sql}")
        )
        db.session.commit()
        
        logger.info(f"Dropped schema: {schema_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to drop schema {schema_name}: {e}")
        db.session.rollback()
        return False


def schema_exists(schema_name: str) -> bool:
    """
    Check if a PostgreSQL schema exists.
    
    Args:
        schema_name: Name of schema to check
    
    Returns:
        True if schema exists
    """
    try:
        result = db.session.execute(
            text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name = :schema_name
            """),
            {"schema_name": schema_name}
        )
        return result.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking schema existence: {e}")
        return False


def list_tenant_schemas() -> List[str]:
    """
    List all tenant schemas in the database.
    
    Returns:
        List of schema names starting with 'tenant_'
    """
    try:
        result = db.session.execute(
            text("""
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name LIKE 'tenant_%'
                ORDER BY schema_name
            """)
        )
        return [row[0] for row in result.fetchall()]
    except Exception as e:
        logger.error(f"Error listing tenant schemas: {e}")
        return []


def set_search_path(schema_name: str) -> None:
    """
    Set PostgreSQL search_path for current session.
    
    Args:
        schema_name: Schema to add to search path
    """
    if not re.match(r'^[a-z][a-z0-9_]*$', schema_name):
        raise ValueError(f"Invalid schema name: {schema_name}")
    
    db.session.execute(
        text(f"SET search_path TO {schema_name}, public")
    )


def reset_search_path() -> None:
    """Reset PostgreSQL search_path to public only."""
    db.session.execute(text("SET search_path TO public"))


def execute_in_tenant_context(tenant_slug: str, func, *args, **kwargs):
    """
    Execute a function within a tenant's schema context.
    
    Args:
        tenant_slug: Tenant slug
        func: Function to execute
        *args, **kwargs: Arguments to pass to function
    
    Returns:
        Result of function execution
    """
    schema_name = get_tenant_schema_name(tenant_slug)
    
    try:
        set_search_path(schema_name)
        result = func(*args, **kwargs)
        return result
    finally:
        reset_search_path()


def get_current_tenant_schema() -> Optional[str]:
    """
    Get current tenant's schema name from request context.
    
    Returns:
        Schema name or None if not in tenant context
    """
    if has_request_context() and hasattr(g, 'tenant_schema'):
        return g.tenant_schema
    return None


def validate_tenant_access(tenant_id: str) -> bool:
    """
    Validate that current user can access the specified tenant.
    
    Args:
        tenant_id: Tenant ID to validate access for
    
    Returns:
        True if access is allowed
    """
    if not has_request_context():
        return False
    
    current_tenant_id = getattr(g, 'tenant_id', None)
    if not current_tenant_id:
        return False
    
    # Users can only access their own tenant
    return str(current_tenant_id) == str(tenant_id)


class TenantSchemaContext:
    """
    Context manager for executing queries in a specific tenant schema.
    
    Usage:
        with TenantSchemaContext('acme-corp'):
            # All queries here use tenant_acme_corp schema
            data = SomeModel.query.all()
    """
    
    def __init__(self, tenant_slug: str):
        self.schema_name = get_tenant_schema_name(tenant_slug)
        self.original_schema = None
    
    def __enter__(self):
        # Save current search path
        try:
            result = db.session.execute(text("SHOW search_path"))
            self.original_schema = result.scalar()
        except Exception:
            self.original_schema = "public"
        
        # Set tenant schema
        set_search_path(self.schema_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original search path
        if self.original_schema:
            db.session.execute(
                text(f"SET search_path TO {self.original_schema}")
            )
        else:
            reset_search_path()
        
        return False  # Don't suppress exceptions
