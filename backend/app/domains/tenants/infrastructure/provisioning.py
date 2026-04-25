"""
NovaSight Tenants Domain — Provisioning
=========================================

Canonical location: ``app.domains.tenants.infrastructure.provisioning``

Infrastructure provisioning for new tenants:
 * PostgreSQL schema creation / deletion
 * ClickHouse database creation / deletion
 * S3 bucket provisioning (MinIO for dev, AWS S3 for prod)
 * Iceberg namespace creation
"""

import logging
import os
import re
from typing import TYPE_CHECKING, Optional

from sqlalchemy import text

from app.extensions import db

if TYPE_CHECKING:
    from app.domains.tenants.domain.models import Tenant

logger = logging.getLogger(__name__)


class ProvisioningService:
    """Creates and destroys infrastructure resources for tenants."""

    def provision(self, tenant: "Tenant") -> None:
        """
        Full provisioning: PG schema + ClickHouse database.

        Raises on failure so the caller can roll back.
        """
        self.create_pg_schema(tenant)
        self.create_ch_database(tenant)
        logger.info("Provisioned resources for tenant: %s", tenant.slug)

    def deprovision(self, tenant: "Tenant", force: bool = False) -> None:
        """
        Full deprovisioning: Drop PG schema + ClickHouse database.

        Args:
            tenant: The tenant to deprovision
            force: If True, drop even if data exists (DANGEROUS)

        Raises on failure so the caller can handle accordingly.
        """
        # Drop ClickHouse database first (contains analytics data)
        self.drop_ch_database(tenant, force=force)
        # Then drop PostgreSQL schema
        self.drop_pg_schema(tenant, force=force)
        logger.info("Deprovisioned resources for tenant: %s", tenant.slug)

    # ------------------------------------------------------------------
    # PostgreSQL
    # ------------------------------------------------------------------

    def create_pg_schema(self, tenant: "Tenant") -> None:
        """Create a tenant-specific PostgreSQL schema."""
        try:
            from app.services.template_engine import template_engine

            engine = template_engine()  # Call to get the TemplateEngine instance
            sql = engine.render(
                "sql/tenant_schema.sql.j2",
                {
                    "tenant_id": str(tenant.id),
                    "tenant_slug": tenant.slug,
                },
            )
            db.session.execute(text(sql))
            logger.info(
                "Created PostgreSQL schema for tenant: %s", tenant.slug
            )
        except Exception as e:
            logger.error(
                "Failed to create PG schema for %s: %s", tenant.slug, e
            )
            raise

    # ------------------------------------------------------------------
    # ClickHouse
    # ------------------------------------------------------------------

    def create_ch_database(self, tenant: "Tenant") -> None:
        """Create a tenant-specific ClickHouse database."""
        try:
            from app.services.template_engine import template_engine
            from app.domains.analytics.infrastructure.clickhouse_client import ClickHouseClient

            engine = template_engine()  # Call to get the TemplateEngine instance
            sql = engine.render(
                "clickhouse/tenant_database.sql.j2",
                {
                    "tenant_id": str(tenant.id),
                    "tenant_slug": tenant.slug,
                },
            )
            client = ClickHouseClient()

            # clickhouse-driver does NOT support multi-statement execution.
            # The rendered template contains multiple DDL statements separated
            # by semicolons (CREATE DATABASE, CREATE TABLE, CREATE VIEW, etc.).
            # We must split them and execute each one individually.
            executed = 0
            for statement in sql.split(";"):
                statement = statement.strip()
                # Skip empty strings and pure SQL comments
                if not statement or all(
                    line.strip().startswith("--") or not line.strip()
                    for line in statement.splitlines()
                ):
                    continue
                client.execute(statement)
                executed += 1

            logger.info(
                "Created ClickHouse database for tenant: %s (%d statements executed)",
                tenant.slug,
                executed,
            )
        except Exception as e:
            logger.error(
                "Failed to create CH database for %s: %s", tenant.slug, e
            )
            raise

    def drop_pg_schema(self, tenant: "Tenant", force: bool = False) -> None:
        """
        Drop a tenant-specific PostgreSQL schema.
        
        Args:
            tenant: The tenant whose schema to drop
            force: If True, use CASCADE to drop even with dependencies
        """
        import re
        schema_name = f"tenant_{re.sub(r'[^a-z0-9_]', '_', tenant.slug.lower())}"
        
        try:
            cascade = "CASCADE" if force else "RESTRICT"
            sql = f"DROP SCHEMA IF EXISTS {schema_name} {cascade}"
            db.session.execute(text(sql))
            db.session.commit()
            logger.info(
                "Dropped PostgreSQL schema for tenant: %s (force=%s)",
                tenant.slug, force
            )
        except Exception as e:
            logger.error(
                "Failed to drop PG schema for %s: %s", tenant.slug, e
            )
            raise

    def drop_ch_database(self, tenant: "Tenant", force: bool = False) -> None:
        """
        Drop a tenant-specific ClickHouse database.
        
        Args:
            tenant: The tenant whose database to drop
            force: If True, drop even if tables contain data
        """
        import re
        from app.domains.analytics.infrastructure.clickhouse_client import ClickHouseClient
        
        db_name = f"tenant_{re.sub(r'[^a-z0-9_]', '_', tenant.slug.lower())}"
        
        try:
            client = ClickHouseClient()
            
            if not force:
                # Check if database has data before dropping
                check_sql = f"""
                    SELECT sum(rows) as total_rows
                    FROM system.parts
                    WHERE database = '{db_name}'
                    AND active = 1
                """
                result = client.execute(check_sql)
                if result.rows and result.rows[0] and result.rows[0][0] > 0:
                    raise ValueError(
                        f"Database {db_name} contains {result.rows[0][0]} rows. "
                        "Use force=True to drop anyway."
                    )
            
            # Drop the database
            drop_sql = f"DROP DATABASE IF EXISTS {db_name}"
            client.execute(drop_sql)
            
            logger.info(
                "Dropped ClickHouse database for tenant: %s (force=%s)",
                tenant.slug, force
            )
        except Exception as e:
            logger.error(
                "Failed to drop CH database for %s: %s", tenant.slug, e
            )
            raise

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def get_tenant_database_name(self, tenant: "Tenant") -> str:
        """Get the ClickHouse database name for a tenant."""
        return f"tenant_{re.sub(r'[^a-z0-9_]', '_', tenant.slug.lower())}"

    def get_tenant_bucket_name(self, tenant: "Tenant") -> str:
        """Get the S3 bucket name for a tenant."""
        return f"novasight-{re.sub(r'[^a-z0-9-]', '-', tenant.slug.lower())}"

    def database_exists(self, tenant: "Tenant") -> bool:
        """Check if the tenant's ClickHouse database exists."""
        from app.domains.analytics.infrastructure.clickhouse_client import ClickHouseClient
        
        db_name = self.get_tenant_database_name(tenant)
        try:
            client = ClickHouseClient()
            result = client.execute(
                f"SELECT 1 FROM system.databases WHERE name = '{db_name}'"
            )
            return bool(result.rows)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Object Storage (S3/MinIO)
    # ------------------------------------------------------------------

    def provision_tenant_bucket(
        self,
        tenant: "Tenant",
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        region: str = "us-east-1",
    ) -> dict:
        """
        Provision S3 bucket for a tenant and create InfrastructureConfig.
        
        In development (MinIO), auto-creates the bucket.
        In production (AWS S3), validates bucket exists and permissions.
        
        Args:
            tenant: The tenant to provision storage for
            access_key: S3 access key (uses MINIO_ROOT_USER in dev if not provided)
            secret_key: S3 secret key (uses MINIO_ROOT_PASSWORD in dev if not provided)
            endpoint_url: S3 endpoint URL (uses MINIO default in dev if not provided)
            region: AWS region (default: us-east-1)
            
        Returns:
            Dict with bucket configuration details
            
        Raises:
            ValueError: If bucket validation fails in production
            boto3.exceptions.ClientError: On S3 API errors
        """
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError
        
        bucket_name = self.get_tenant_bucket_name(tenant)
        
        # Determine if we're in dev mode (MinIO)
        is_dev = os.getenv("APP_ENV", "development") == "development"
        
        # Get credentials from environment if not provided
        if is_dev:
            access_key = access_key or os.getenv("MINIO_ROOT_USER", "minioadmin")
            secret_key = secret_key or os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")
            endpoint_url = endpoint_url or os.getenv(
                "MINIO_ENDPOINT_URL", "http://minio:9000"
            )
        else:
            # Production: require explicit credentials
            if not access_key or not secret_key:
                raise ValueError(
                    "access_key and secret_key are required for production S3"
                )
        
        # Create S3 client
        s3_config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path' if is_dev else 'virtual'}
        )
        
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=s3_config,
        )
        
        if is_dev:
            # MinIO: Auto-create bucket
            try:
                s3_client.head_bucket(Bucket=bucket_name)
                logger.info("Bucket already exists for tenant %s: %s", tenant.slug, bucket_name)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')
                if error_code in ('404', 'NoSuchBucket'):
                    # Bucket doesn't exist, create it
                    try:
                        if region == "us-east-1":
                            s3_client.create_bucket(Bucket=bucket_name)
                        else:
                            s3_client.create_bucket(
                                Bucket=bucket_name,
                                CreateBucketConfiguration={'LocationConstraint': region}
                            )
                        logger.info(
                            "Created MinIO bucket for tenant %s: %s",
                            tenant.slug, bucket_name
                        )
                    except ClientError as create_error:
                        logger.error(
                            "Failed to create bucket %s: %s",
                            bucket_name, create_error
                        )
                        raise
                else:
                    raise
        else:
            # Production: Validate bucket exists and permissions
            try:
                s3_client.head_bucket(Bucket=bucket_name)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code')
                if error_code in ('404', 'NoSuchBucket'):
                    raise ValueError(
                        f"Bucket {bucket_name} does not exist. "
                        "Please create the bucket before provisioning."
                    )
                elif error_code == '403':
                    raise ValueError(
                        f"Access denied to bucket {bucket_name}. "
                        "Please check IAM permissions."
                    )
                raise
            
            # Test write permissions
            test_key = ".healthcheck"
            try:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=test_key,
                    Body=b"healthcheck"
                )
                s3_client.delete_object(Bucket=bucket_name, Key=test_key)
            except ClientError as e:
                raise ValueError(
                    f"Write permission check failed for bucket {bucket_name}: {e}"
                )
        
        # Create infrastructure config for this tenant
        self._create_object_storage_config(
            tenant=tenant,
            bucket=bucket_name,
            region=region,
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
        )
        
        logger.info(
            "Provisioned object storage for tenant %s: bucket=%s",
            tenant.slug, bucket_name
        )
        
        return {
            "bucket": bucket_name,
            "region": region,
            "endpoint_url": endpoint_url,
        }

    def _create_object_storage_config(
        self,
        tenant: "Tenant",
        bucket: str,
        region: str,
        endpoint_url: Optional[str],
        access_key: str,
        secret_key: str,
    ) -> None:
        """Create InfrastructureConfig row for object storage."""
        from app.domains.tenants.infrastructure.config_service import InfrastructureConfigService
        
        service = InfrastructureConfigService()
        
        # Check if config already exists
        existing = service.list_configs(
            service_type="object_storage",
            tenant_id=str(tenant.id),
            include_global=False,
            page=1,
            per_page=1,
        )
        
        if existing.get("items"):
            # Update existing config
            config_id = existing["items"][0]["id"]
            service.update_config(
                config_id=str(config_id),
                data={
                    "settings": {
                        "bucket": bucket,
                        "region": region,
                        "endpoint_url": endpoint_url,
                        "access_key": access_key,
                        "secret_key": secret_key,
                        "path_style": endpoint_url is not None,  # Path style for MinIO
                    }
                },
                user_id=str(tenant.id),  # Use tenant ID as user for system operations
            )
            logger.info("Updated object storage config for tenant %s", tenant.slug)
        else:
            # Create new config
            service.create_config(
                data={
                    "service_type": "object_storage",
                    "tenant_id": str(tenant.id),
                    "name": f"{tenant.name} Object Storage",
                    "description": f"S3/MinIO storage for tenant {tenant.slug}",
                    "host": "",  # Not used for object storage
                    "port": 443,
                    "is_active": True,
                    "settings": {
                        "bucket": bucket,
                        "region": region,
                        "endpoint_url": endpoint_url,
                        "access_key": access_key,
                        "secret_key": secret_key,
                        "path_style": endpoint_url is not None,
                    }
                },
                user_id=str(tenant.id),
            )
            logger.info("Created object storage config for tenant %s", tenant.slug)

    def provision_iceberg_namespace(self, tenant: "Tenant") -> str:
        """
        Create the Iceberg namespace for a tenant.
        
        Requires object storage to be provisioned first.
        
        Args:
            tenant: The tenant to create namespace for
            
        Returns:
            The namespace name (e.g., "tenant_acme.raw")
        """
        from app.platform.lake.iceberg_catalog import get_catalog_for_tenant, ensure_namespace
        
        catalog = get_catalog_for_tenant(tenant.id)
        namespace = ensure_namespace(catalog, tenant.slug)
        
        logger.info(
            "Created Iceberg namespace for tenant %s: %s",
            tenant.slug, namespace
        )
        
        return namespace

    def test_object_storage_connection(
        self,
        bucket: str,
        region: str,
        endpoint_url: Optional[str],
        access_key: str,
        secret_key: str,
    ) -> dict:
        """
        Test connection to object storage.
        
        Args:
            bucket: S3 bucket name
            region: AWS region
            endpoint_url: S3 endpoint URL (for MinIO)
            access_key: S3 access key
            secret_key: S3 secret key
            
        Returns:
            Dict with test results
        """
        import time
        import boto3
        from botocore.config import Config
        from botocore.exceptions import ClientError
        
        start_time = time.time()
        
        s3_config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path' if endpoint_url else 'virtual'}
        )
        
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=s3_config,
        )
        
        try:
            # Test bucket access
            s3_client.head_bucket(Bucket=bucket)
            
            # Test write/read/delete
            test_key = ".healthcheck"
            s3_client.put_object(Bucket=bucket, Key=test_key, Body=b"test")
            s3_client.get_object(Bucket=bucket, Key=test_key)
            s3_client.delete_object(Bucket=bucket, Key=test_key)
            
            latency_ms = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "message": f"Successfully connected to bucket {bucket}",
                "latency_ms": latency_ms,
                "details": {
                    "bucket": bucket,
                    "region": region,
                    "endpoint": endpoint_url or "AWS S3",
                }
            }
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            return {
                "success": False,
                "message": f"Connection failed: {error_code} - {error_message}",
                "latency_ms": None,
                "details": {"error_code": error_code}
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}",
                "latency_ms": None,
                "details": {}
            }
