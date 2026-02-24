"""
NovaSight Platform — Infrastructure Configuration Provider
============================================================

Provides runtime infrastructure configurations for use by
Dagster resources, services, and other components.

The provider fetches configurations dynamically from the database
(via cache) allowing hot-reload of connection settings.

Usage:
    from app.platform.infrastructure import InfrastructureConfigProvider
    
    provider = InfrastructureConfigProvider()
    
    # Get ClickHouse config for a tenant
    ch_config = provider.get_clickhouse_config(tenant_id="tenant-123")
    
    # Get global Spark config
    spark_config = provider.get_spark_config()
    
    # Get a ClickHouse client directly
    client = provider.get_clickhouse_client(tenant_id="tenant-123")
"""

import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

from app.platform.infrastructure.config_cache import (
    get_config_cache,
    InfrastructureConfigCache,
)

if TYPE_CHECKING:
    from clickhouse_driver import Client as ClickHouseClient
    from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)


# ─── Configuration Data Classes ───────────────────────────────

class ClickHouseConfig:
    """ClickHouse connection configuration."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self.id = config_dict.get("id")
        self.name = config_dict.get("name", "ClickHouse")
        self.host = config_dict.get("host", "localhost")
        self.port = config_dict.get("port", 8123)
        self.tenant_id = config_dict.get("tenant_id")
        self.is_system_default = config_dict.get("is_system_default", False)
        
        settings = config_dict.get("settings", {})
        self.database = settings.get("database", "default")
        self.user = settings.get("user", "default")
        self.password = settings.get("password", "")
        self.secure = settings.get("secure", False)
        self.connect_timeout = settings.get("connect_timeout", 10)
        self.send_receive_timeout = settings.get("send_receive_timeout", 300)
        
        # Native port (9000) vs HTTP port (8123)
        self.native_port = settings.get("native_port", 9000)
    
    @property
    def http_url(self) -> str:
        """HTTP interface URL."""
        protocol = "https" if self.secure else "http"
        return f"{protocol}://{self.host}:{self.port}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "native_port": self.native_port,
            "database": self.database,
            "user": self.user,
            "secure": self.secure,
            "tenant_id": self.tenant_id,
        }


class SparkConfig:
    """Apache Spark connection configuration."""
    
    def __init__(self, config_dict: Dict[str, Any]):
        self.id = config_dict.get("id")
        self.name = config_dict.get("name", "Spark")
        self.host = config_dict.get("host", "localhost")
        self.port = config_dict.get("port", 7077)
        self.is_system_default = config_dict.get("is_system_default", False)
        
        settings = config_dict.get("settings", {})
        self.master_url = settings.get("master_url", f"spark://{self.host}:{self.port}")
        self.deploy_mode = settings.get("deploy_mode", "client")
        self.driver_memory = settings.get("driver_memory", "2g")
        self.executor_memory = settings.get("executor_memory", "2g")
        self.executor_cores = settings.get("executor_cores", 2)
        self.dynamic_allocation = settings.get("dynamic_allocation", True)
        self.min_executors = settings.get("min_executors", 1)
        self.max_executors = settings.get("max_executors", 10)
        self.num_executors = settings.get("num_executors", 2)
        self.spark_home = settings.get("spark_home", "/opt/spark")
        self.additional_configs = settings.get("additional_configs", {})
        # Remote Spark server configuration
        self.ssh_host = settings.get("ssh_host", "")
        self.ssh_user = settings.get("ssh_user", "spark")
        self.webui_port = settings.get("webui_port", 8080)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "master_url": self.master_url,
            "deploy_mode": self.deploy_mode,
            "driver_memory": self.driver_memory,
            "executor_memory": self.executor_memory,
            "executor_cores": self.executor_cores,
        }


# ─── Configuration Provider ───────────────────────────────────

class InfrastructureConfigProvider:
    """
    Provides infrastructure configurations for runtime use.
    
    This is the primary interface for components that need
    infrastructure connection settings. It handles:
    
    - Per-tenant ClickHouse configurations
    - Global Spark configuration
    - Caching with automatic invalidation
    - Client/connection factory methods
    """
    
    def __init__(self, cache: Optional[InfrastructureConfigCache] = None):
        """
        Initialize the provider.
        
        Args:
            cache: Optional cache instance. Uses global cache if not provided.
        """
        self._cache = cache or get_config_cache()
    
    # ─── ClickHouse (Per-Tenant) ─────────────────────────────
    
    def get_clickhouse_config(
        self,
        tenant_id: Optional[str] = None,
    ) -> ClickHouseConfig:
        """
        Get ClickHouse configuration for a tenant.
        
        ClickHouse is per-tenant - each tenant MUST have their own
        configuration. No fallback to global config.
        
        Args:
            tenant_id: Tenant ID (required for ClickHouse)
        
        Returns:
            ClickHouseConfig object
        
        Raises:
            ValueError: If no configuration found for tenant
        """
        if not tenant_id:
            raise ValueError(
                "No Configured Analytics Platform. "
                "Tenant ID is required for ClickHouse configuration."
            )
        
        config_dict = self._cache.get_config("clickhouse", tenant_id)
        
        # Check if this is a tenant-specific config (not a fallback)
        if config_dict is None or config_dict.get("is_system_default"):
            raise ValueError(
                "No Configured Analytics Platform. "
                "Please configure a ClickHouse instance for this tenant."
            )
        
        return ClickHouseConfig(config_dict)
    
    def get_clickhouse_client(
        self,
        tenant_id: Optional[str] = None,
        use_http: bool = False,
    ) -> "ClickHouseClient":
        """
        Get a ClickHouse client for a tenant.
        
        Args:
            tenant_id: Tenant ID for tenant-specific config
            use_http: If True, return HTTP client instead of native
        
        Returns:
            ClickHouse client instance
        """
        config = self.get_clickhouse_config(tenant_id)
        
        if use_http:
            return self._create_clickhouse_http_client(config)
        return self._create_clickhouse_native_client(config)
    
    def _create_clickhouse_native_client(self, config: ClickHouseConfig):
        """Create native ClickHouse client (port 9000)."""
        from clickhouse_driver import Client
        
        return Client(
            host=config.host,
            port=config.native_port,
            database=config.database,
            user=config.user,
            password=config.password,
            connect_timeout=config.connect_timeout,
            send_receive_timeout=config.send_receive_timeout,
        )
    
    def _create_clickhouse_http_client(self, config: ClickHouseConfig):
        """Create HTTP ClickHouse client (port 8123)."""
        try:
            import clickhouse_connect
            
            return clickhouse_connect.get_client(
                host=config.host,
                port=config.port,
                database=config.database,
                username=config.user,
                password=config.password,
                secure=config.secure,
            )
        except ImportError:
            # Fallback to simple HTTP wrapper
            return _SimpleClickHouseHTTPClient(config)
    
    # ─── Spark (Global Only) ─────────────────────────────────
    
    def get_spark_config(self) -> SparkConfig:
        """
        Get global Spark configuration.
        
        Spark is always global (not per-tenant).
        
        Returns:
            SparkConfig object
        
        Raises:
            ValueError: If no configuration found
        """
        config_dict = self._cache.get_config("spark", tenant_id=None)
        
        if config_dict is None:
            raise ValueError("No Spark configuration found")
        
        return SparkConfig(config_dict)
    
    def get_spark_session(
        self,
        app_name: str = "NovaSight",
        additional_config: Optional[Dict[str, str]] = None,
    ) -> "SparkSession":
        """
        Get or create a SparkSession with current config.
        
        Args:
            app_name: Spark application name
            additional_config: Additional Spark configs to apply
        
        Returns:
            SparkSession instance
        """
        from pyspark.sql import SparkSession
        
        config = self.get_spark_config()
        
        builder = SparkSession.builder \
            .appName(app_name) \
            .master(config.master_url) \
            .config("spark.driver.memory", config.driver_memory) \
            .config("spark.executor.memory", config.executor_memory) \
            .config("spark.executor.cores", str(config.executor_cores))
        
        if config.dynamic_allocation:
            builder = builder \
                .config("spark.dynamicAllocation.enabled", "true") \
                .config("spark.dynamicAllocation.minExecutors", str(config.min_executors)) \
                .config("spark.dynamicAllocation.maxExecutors", str(config.max_executors))
        
        # Apply additional configs from stored settings
        for key, value in config.additional_configs.items():
            builder = builder.config(key, value)
        
        # Apply runtime additional configs
        if additional_config:
            for key, value in additional_config.items():
                builder = builder.config(key, value)
        
        return builder.getOrCreate()
    
    # ─── Other Services ──────────────────────────────────────
    
    def get_dagster_config(self) -> Dict[str, Any]:
        """Get Dagster orchestrator configuration."""
        config_dict = self._cache.get_config("dagster", tenant_id=None)
        if config_dict is None:
            # Return defaults from environment
            from flask import current_app
            return {
                "host": current_app.config.get("DAGSTER_HOST", "localhost"),
                "port": current_app.config.get("DAGSTER_PORT", 3000),
                "graphql_url": current_app.config.get("DAGSTER_GRAPHQL_URL", "http://localhost:3000/graphql"),
                "max_concurrent_runs": current_app.config.get("DAGSTER_MAX_CONCURRENT_RUNS", 10),
                "spark_concurrency_limit": current_app.config.get("DAGSTER_SPARK_CONCURRENCY_LIMIT", 3),
                "dbt_concurrency_limit": current_app.config.get("DAGSTER_DBT_CONCURRENCY_LIMIT", 2),
            }
        return config_dict
    
    def get_airflow_config(self) -> Dict[str, Any]:
        """
        Get Airflow configuration.
        
        .. deprecated:: Use get_dagster_config() instead.
        """
        config_dict = self._cache.get_config("airflow", tenant_id=None)
        if config_dict is None:
            raise ValueError("No Airflow configuration found")
        return config_dict
    
    def get_ollama_config(self) -> Dict[str, Any]:
        """Get Ollama configuration."""
        config_dict = self._cache.get_config("ollama", tenant_id=None)
        if config_dict is None:
            raise ValueError("No Ollama configuration found")
        return config_dict
    
    # ─── Cache Management ────────────────────────────────────
    
    def refresh_config(
        self,
        service_type: str,
        tenant_id: Optional[str] = None,
    ) -> None:
        """
        Force refresh a configuration from database.
        
        Args:
            service_type: Service type to refresh
            tenant_id: Optional tenant ID
        """
        self._cache.invalidate(service_type, tenant_id)
        # Fetch will re-cache on next access


# ─── Helper Classes ───────────────────────────────────────────

class _SimpleClickHouseHTTPClient:
    """Simple HTTP client for ClickHouse when clickhouse-connect unavailable."""
    
    def __init__(self, config: ClickHouseConfig):
        self.config = config
    
    def query(self, query: str, parameters: Optional[Dict] = None):
        import httpx
        
        response = httpx.post(
            f"{self.config.http_url}/",
            params={
                "database": self.config.database,
                "query": query,
            },
            auth=(self.config.user, self.config.password) if self.config.password else None,
            timeout=self.config.send_receive_timeout,
        )
        response.raise_for_status()
        return response.text
    
    def command(self, command: str):
        return self.query(command)


# ─── Global Provider Instance ─────────────────────────────────

_config_provider: Optional[InfrastructureConfigProvider] = None


def get_config_provider() -> InfrastructureConfigProvider:
    """Get the global config provider instance."""
    global _config_provider
    if _config_provider is None:
        _config_provider = InfrastructureConfigProvider()
    return _config_provider
