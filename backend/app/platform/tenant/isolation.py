"""
NovaSight Platform – Tenant Isolation Service
===============================================

Provides tenant isolation enforcement across all artifacts:
- PySpark scripts
- DAG files
- dbt models
- Connections

This module enforces ADR-003: Multi-Tenant Isolation Strategy.
"""

import logging
import re
from typing import Optional, List, Dict, Any
from functools import wraps

from flask import g, has_request_context

logger = logging.getLogger(__name__)


class TenantIsolationError(Exception):
    """Raised when a tenant isolation violation is detected."""
    pass


class TenantIsolationService:
    """
    Service for enforcing tenant isolation across all NovaSight artifacts.
    
    This service ensures that:
    1. Connections can only access data for their owning tenant
    2. PySpark scripts target only the tenant's ClickHouse database
    3. DAGs are scoped to tenant folders
    4. dbt models are isolated per tenant
    """
    
    # Pattern for valid tenant database names
    TENANT_DB_PATTERN = re.compile(r'^tenant_[a-z0-9_]+$')
    
    # Pattern for safe SQL identifiers
    SAFE_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    
    def __init__(self, tenant_id: str, tenant_slug: Optional[str] = None):
        """
        Initialize tenant isolation service.
        
        Args:
            tenant_id: The tenant UUID
            tenant_slug: Optional tenant slug for database naming
        """
        self.tenant_id = tenant_id
        self._tenant_slug = tenant_slug
    
    @property
    def tenant_slug(self) -> str:
        """Get the tenant slug, fetching from DB if needed."""
        if self._tenant_slug:
            return self._tenant_slug
        
        from app.domains.tenants.domain.models import Tenant
        tenant = Tenant.query.filter(Tenant.id == self.tenant_id).first()
        if tenant:
            self._tenant_slug = tenant.slug
            return tenant.slug
        return str(self.tenant_id)
    
    @staticmethod
    def _sanitize_slug(slug: str) -> str:
        """Sanitize slug for use in database/schema names.
        
        This mirrors the sql_safe filter used in templates.
        """
        if not slug:
            return "unnamed"
        # Convert to lowercase
        result = slug.lower()
        # Replace hyphens and spaces with underscores
        result = re.sub(r'[-\s]+', '_', result)
        # Remove non-alphanumeric characters except underscores
        result = re.sub(r'[^a-z0-9_]', '', result)
        # Ensure starts with a letter
        if result and not result[0].isalpha():
            result = 't_' + result
        return result or "unnamed"
    
    @property
    def tenant_database(self) -> str:
        """Get the ClickHouse database name for this tenant."""
        return f"tenant_{self._sanitize_slug(self.tenant_slug)}"
    
    @property
    def tenant_schema(self) -> str:
        """Get the PostgreSQL schema name for this tenant."""
        return f"tenant_{self._sanitize_slug(self.tenant_slug)}"
    
    @property
    def tenant_dag_folder(self) -> str:
        """Get the Airflow DAGs folder for this tenant."""
        return f"tenant_{self._sanitize_slug(self.tenant_slug)}"
    
    @property
    def tenant_dbt_folder(self) -> str:
        """Get the dbt models folder for this tenant."""
        return f"tenant_{self._sanitize_slug(self.tenant_slug)}"
    
    # ------------------------------------------------------------------
    # Validation methods
    # ------------------------------------------------------------------
    
    def validate_target_database(self, database: str) -> bool:
        """
        Validate that the target database belongs to this tenant.
        
        Args:
            database: The database name to validate
            
        Returns:
            True if valid
            
        Raises:
            TenantIsolationError: If database is not allowed
        """
        if not database:
            return True  # Will use default tenant database
        
        expected_db = self.tenant_database
        
        # Allow exact match
        if database == expected_db:
            return True
        
        # Check if trying to access another tenant's database
        if self.TENANT_DB_PATTERN.match(database) and database != expected_db:
            raise TenantIsolationError(
                f"Access denied: Cannot write to database '{database}'. "
                f"Tenant can only access '{expected_db}'."
            )
        
        # Allow system databases for read-only operations (handled at query level)
        system_dbs = {'system', 'information_schema', 'default'}
        if database.lower() in system_dbs:
            logger.warning(
                f"Tenant {self.tenant_id} accessing system database: {database}"
            )
            return True
        
        # For any other database, log a warning but allow (for shared datasets)
        logger.info(
            f"Tenant {self.tenant_id} accessing non-tenant database: {database}"
        )
        return True
    
    def validate_connection_ownership(self, connection_id: str) -> bool:
        """
        Validate that a connection belongs to this tenant.
        
        Args:
            connection_id: The connection UUID
            
        Returns:
            True if valid
            
        Raises:
            TenantIsolationError: If connection doesn't belong to tenant
        """
        from app.domains.datasources.domain.models import DataConnection
        
        connection = DataConnection.query.filter(
            DataConnection.id == connection_id
        ).first()
        
        if not connection:
            raise TenantIsolationError(f"Connection {connection_id} not found")
        
        if str(connection.tenant_id) != str(self.tenant_id):
            raise TenantIsolationError(
                f"Access denied: Connection {connection_id} belongs to another tenant"
            )
        
        return True
    
    def validate_pyspark_app_ownership(self, app_id: str) -> bool:
        """
        Validate that a PySpark app belongs to this tenant.
        
        Args:
            app_id: The PySpark app UUID
            
        Returns:
            True if valid
            
        Raises:
            TenantIsolationError: If app doesn't belong to tenant
        """
        from app.domains.compute.domain.models import PySparkApp
        
        app = PySparkApp.query.filter(PySparkApp.id == app_id).first()
        
        if not app:
            raise TenantIsolationError(f"PySpark app {app_id} not found")
        
        if str(app.tenant_id) != str(self.tenant_id):
            raise TenantIsolationError(
                f"Access denied: PySpark app {app_id} belongs to another tenant"
            )
        
        return True
    
    def validate_dag_config_ownership(self, dag_config_id: str) -> bool:
        """
        Validate that a DAG config belongs to this tenant.
        
        Args:
            dag_config_id: The DAG config UUID
            
        Returns:
            True if valid
            
        Raises:
            TenantIsolationError: If DAG config doesn't belong to tenant
        """
        from app.domains.orchestration.domain.models import DagConfig
        
        dag_config = DagConfig.query.filter(DagConfig.id == dag_config_id).first()
        
        if not dag_config:
            raise TenantIsolationError(f"DAG config {dag_config_id} not found")
        
        if str(dag_config.tenant_id) != str(self.tenant_id):
            raise TenantIsolationError(
                f"Access denied: DAG config {dag_config_id} belongs to another tenant"
            )
        
        return True
    
    def validate_dag_id(self, dag_id: str) -> bool:
        """
        Validate that a DAG ID belongs to this tenant.
        
        DAG IDs should follow the pattern: {type}_{tenant_id}_{identifier}
        
        Args:
            dag_id: The Airflow DAG ID
            
        Returns:
            True if valid
            
        Raises:
            TenantIsolationError: If DAG doesn't belong to tenant
        """
        # DAGs should contain tenant ID
        if str(self.tenant_id) not in dag_id and self.tenant_slug not in dag_id:
            raise TenantIsolationError(
                f"Access denied: DAG {dag_id} does not belong to this tenant"
            )
        
        return True
    
    def validate_sql_query(self, query: str) -> bool:
        """
        Validate that a SQL query doesn't access other tenant databases.
        
        Args:
            query: The SQL query to validate
            
        Returns:
            True if valid
            
        Raises:
            TenantIsolationError: If query accesses unauthorized databases
        """
        # Look for database references in the query
        # Pattern: database_name.table_name
        db_references = re.findall(r'\b(tenant_[a-z0-9_]+)\s*\.', query.lower())
        
        for db_ref in db_references:
            if db_ref != self.tenant_database:
                raise TenantIsolationError(
                    f"Access denied: Query references unauthorized database '{db_ref}'"
                )
        
        return True
    
    # ------------------------------------------------------------------
    # Enforcement methods
    # ------------------------------------------------------------------
    
    def enforce_target_database(self, target_database: Optional[str]) -> str:
        """
        Enforce that target database is the tenant's database.
        
        Args:
            target_database: The requested target database (or None)
            
        Returns:
            The validated/enforced target database name
        """
        if not target_database:
            return self.tenant_database
        
        self.validate_target_database(target_database)
        return target_database
    
    def get_dag_file_path(self, dag_id: str) -> str:
        """
        Get the file path for a tenant's DAG file.
        
        DAG files are stored in tenant-specific folders for isolation.
        
        Args:
            dag_id: The DAG ID
            
        Returns:
            The full path for the DAG file
        """
        return f"/opt/airflow/dags/{self.tenant_dag_folder}/{dag_id}.py"
    
    def get_pyspark_job_path(self, job_id: str) -> str:
        """
        Get the file path for a tenant's PySpark job file.
        
        Args:
            job_id: The job ID
            
        Returns:
            The full path for the PySpark job file
        """
        return f"/opt/airflow/spark_apps/{self.tenant_dag_folder}/{job_id}.py"
    
    def get_dbt_model_path(self, model_name: str) -> str:
        """
        Get the file path for a tenant's dbt model.
        
        Args:
            model_name: The model name
            
        Returns:
            The full path for the dbt model file
        """
        return f"models/{self.tenant_dbt_folder}/{model_name}.sql"
    
    # ------------------------------------------------------------------
    # Context injection
    # ------------------------------------------------------------------
    
    def get_template_context(self) -> Dict[str, Any]:
        """
        Get template context variables for tenant isolation.
        
        Returns:
            Dictionary of context variables for templates
        """
        return {
            "tenant_id": self.tenant_id,
            "tenant_slug": self.tenant_slug,
            "tenant_database": self.tenant_database,
            "tenant_schema": self.tenant_schema,
            "tenant_dag_folder": self.tenant_dag_folder,
            "tenant_dbt_folder": self.tenant_dbt_folder,
        }


def get_current_tenant_isolation() -> Optional[TenantIsolationService]:
    """
    Get TenantIsolationService for the current request context.
    
    Returns:
        TenantIsolationService if in request context with tenant, else None
    """
    if not has_request_context():
        return None
    
    if not hasattr(g, 'tenant') or not g.tenant:
        if hasattr(g, 'tenant_id') and g.tenant_id:
            return TenantIsolationService(str(g.tenant_id))
        return None
    
    return TenantIsolationService(
        tenant_id=str(g.tenant.id),
        tenant_slug=g.tenant.slug
    )


def require_tenant_isolation(f):
    """
    Decorator to require tenant isolation for a function.
    
    Injects 'isolation' parameter with TenantIsolationService.
    
    Usage:
        @require_tenant_isolation
        def my_function(isolation: TenantIsolationService, ...):
            isolation.validate_connection_ownership(connection_id)
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        isolation = get_current_tenant_isolation()
        if not isolation:
            raise TenantIsolationError("No tenant context available")
        
        kwargs['isolation'] = isolation
        return f(*args, **kwargs)
    
    return decorated
