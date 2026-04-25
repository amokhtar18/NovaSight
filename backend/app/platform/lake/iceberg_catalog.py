"""
NovaSight Platform — Iceberg Catalog Module
=============================================

Provides a factory for obtaining a pyiceberg SqlCatalog instance
configured for a specific tenant's S3 bucket and the platform's
Postgres-backed Iceberg catalog.

Usage:
    from app.platform.lake.iceberg_catalog import get_catalog_for_tenant, ensure_namespace
    
    catalog = get_catalog_for_tenant(tenant_id)
    ensure_namespace(catalog, tenant_slug)
    
    # Write data
    table = catalog.create_table(
        identifier=f"tenant_{tenant_slug}.raw.my_table",
        schema=my_pyarrow_schema,
    )
"""

import logging
import os
import re
from typing import TYPE_CHECKING, Optional
from uuid import UUID

if TYPE_CHECKING:
    from pyiceberg.catalog.sql import SqlCatalog

logger = logging.getLogger(__name__)


def _get_tenant_s3_config(tenant_id: UUID) -> dict:
    """
    Fetch S3 configuration for a tenant from InfrastructureConfig.
    
    Args:
        tenant_id: The tenant's UUID
        
    Returns:
        Dictionary with S3 configuration:
        - bucket: str
        - region: str
        - endpoint_url: Optional[str]
        - access_key: str
        - secret_key: str
        - prefix: str
        - path_style: bool
        
    Raises:
        ValueError: If no object_storage config exists for the tenant
    """
    from app.domains.tenants.infrastructure.config_service import InfrastructureConfigService
    
    service = InfrastructureConfigService()
    configs = service.list_configs(
        service_type="object_storage",
        tenant_id=str(tenant_id),
        include_global=False,
        page=1,
        per_page=1,
    )
    
    if not configs.get("items"):
        raise ValueError(
            f"No object_storage configuration found for tenant {tenant_id}. "
            "Please configure S3/MinIO storage for this tenant first."
        )
    
    config = configs["items"][0]
    settings = config.get("settings", {})
    
    # Decrypt credentials if needed
    from app.domains.tenants.infrastructure.config_service import InfrastructureConfigService
    decrypted_settings = service.decrypt_settings(settings, "object_storage")
    
    return {
        "bucket": decrypted_settings.get("bucket"),
        "region": decrypted_settings.get("region", "us-east-1"),
        "endpoint_url": decrypted_settings.get("endpoint_url"),
        "access_key": decrypted_settings.get("access_key"),
        "secret_key": decrypted_settings.get("secret_key"),
        "prefix": decrypted_settings.get("prefix", ""),
        "path_style": decrypted_settings.get("path_style", True),
    }


def get_catalog_for_tenant(tenant_id: UUID) -> "SqlCatalog":
    """
    Get a pyiceberg SqlCatalog instance for the specified tenant.
    
    The catalog uses:
    - Postgres backend: Uses ICEBERG_CATALOG_URL env var or falls back to DATABASE_URL
    - S3 warehouse: Tenant's configured bucket from InfrastructureConfig
    
    Args:
        tenant_id: The tenant's UUID
        
    Returns:
        Configured SqlCatalog instance
        
    Raises:
        ValueError: If tenant has no object_storage configuration
        ImportError: If pyiceberg is not installed
    """
    try:
        from pyiceberg.catalog.sql import SqlCatalog
    except ImportError as e:
        raise ImportError(
            "pyiceberg is required for Iceberg catalog support. "
            "Install with: pip install 'pyiceberg[sql,s3fs]'"
        ) from e
    
    # Get S3 configuration for this tenant
    s3_config = _get_tenant_s3_config(tenant_id)
    
    # Get catalog database URL
    catalog_url = os.getenv(
        "ICEBERG_CATALOG_URL",
        os.getenv("DATABASE_URL", "postgresql://novasight:novasight@localhost:5432/novasight_platform")
    )
    
    # Build warehouse location (S3 path for Iceberg data files)
    if s3_config.get("prefix"):
        warehouse = f"s3://{s3_config['bucket']}/{s3_config['prefix']}/iceberg"
    else:
        warehouse = f"s3://{s3_config['bucket']}/iceberg"
    
    # Pyiceberg SqlCatalog configuration
    catalog_config = {
        "uri": catalog_url,
        "warehouse": warehouse,
        # Use iceberg_catalog schema for metadata tables
        "sql-catalog.schema": "iceberg_catalog",
    }
    
    # Add S3 filesystem configuration
    # Note: pyiceberg uses s3. prefix for S3 configuration
    catalog_config["s3.region"] = s3_config["region"]
    catalog_config["s3.access-key-id"] = s3_config["access_key"]
    catalog_config["s3.secret-access-key"] = s3_config["secret_key"]
    
    if s3_config.get("endpoint_url"):
        catalog_config["s3.endpoint"] = s3_config["endpoint_url"]
    
    if s3_config.get("path_style"):
        catalog_config["s3.path-style-access"] = "true"
    
    # Create and return the catalog
    catalog = SqlCatalog(
        name=f"novasight_tenant_{tenant_id}",
        **catalog_config
    )
    
    logger.debug(
        "Created Iceberg catalog for tenant %s with warehouse %s",
        tenant_id, warehouse
    )
    
    return catalog


def ensure_namespace(catalog: "SqlCatalog", tenant_slug: str, namespace_suffix: str = "raw") -> str:
    """
    Ensure the tenant namespace exists in the Iceberg catalog.
    
    Creates the namespace if it doesn't exist. This operation is idempotent.
    
    Args:
        catalog: The pyiceberg SqlCatalog instance
        tenant_slug: The tenant's slug (e.g., "acme_corp")
        namespace_suffix: The namespace suffix (default: "raw")
        
    Returns:
        The full namespace name (e.g., "tenant_acme_corp.raw")
    """
    from pyiceberg.exceptions import NamespaceAlreadyExistsError
    
    # Sanitize tenant slug for namespace
    safe_slug = re.sub(r'[^a-z0-9_]', '_', tenant_slug.lower())
    namespace = f"tenant_{safe_slug}.{namespace_suffix}"
    
    try:
        catalog.create_namespace(namespace)
        logger.info("Created Iceberg namespace: %s", namespace)
    except NamespaceAlreadyExistsError:
        logger.debug("Iceberg namespace already exists: %s", namespace)
    except Exception as e:
        # Log but don't fail - namespace might already exist
        logger.warning("Could not create namespace %s: %s", namespace, e)
    
    return namespace


def get_tenant_namespace(tenant_slug: str, namespace_suffix: str = "raw") -> str:
    """
    Get the namespace name for a tenant without creating it.
    
    Args:
        tenant_slug: The tenant's slug (e.g., "acme_corp")
        namespace_suffix: The namespace suffix (default: "raw")
        
    Returns:
        The full namespace name (e.g., "tenant_acme_corp.raw")
    """
    safe_slug = re.sub(r'[^a-z0-9_]', '_', tenant_slug.lower())
    return f"tenant_{safe_slug}.{namespace_suffix}"


def validate_namespace_ownership(tenant_slug: str, namespace: str) -> bool:
    """
    Validate that a namespace belongs to the specified tenant.
    
    This is a security check to prevent cross-tenant access.
    
    Args:
        tenant_slug: The tenant's slug
        namespace: The namespace to validate
        
    Returns:
        True if the namespace belongs to the tenant, False otherwise
    """
    safe_slug = re.sub(r'[^a-z0-9_]', '_', tenant_slug.lower())
    expected_prefix = f"tenant_{safe_slug}."
    return namespace.startswith(expected_prefix)
