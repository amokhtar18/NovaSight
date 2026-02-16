"""
NovaSight Data Sources — Base Connector
========================================

Abstract base class for all data source connectors.

Canonical location: ``app.domains.datasources.infrastructure.connectors.base``

Value objects (``ColumnInfo``, ``TableInfo``) are defined in the domain
layer (``app.domains.datasources.domain.value_objects``) and re-exported
here for backward compatibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Iterator, Optional
from pydantic import BaseModel, Field, validator
import logging

# Import value objects from domain layer — canonical source
from app.domains.datasources.domain.value_objects import ColumnInfo, TableInfo

logger = logging.getLogger(__name__)


# ─── Exceptions ────────────────────────────────────────────────────

class ConnectorException(Exception):
    """Base exception for connector errors."""
    pass


class ConnectionTestException(ConnectorException):
    """Exception raised when connection test fails."""
    pass


# ─── Connection Config ────────────────────────────────────────────

class ConnectionConfig(BaseModel):
    """Base configuration for database connections."""
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1, max_length=128)
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1)
    ssl: bool = True
    ssl_mode: Optional[str] = None
    schema_name: Optional[str] = Field(default=None, alias="schema")
    extra_params: Dict[str, Any] = Field(default_factory=dict)

    # NovaSight-specific extra_params keys that should NOT be passed to database drivers
    _novasight_extra_keys = frozenset(["allowed_schemas", "thick_mode", "service_name"])

    @property
    def driver_extra_params(self) -> Dict[str, Any]:
        """Return extra_params filtered to exclude NovaSight-specific keys."""
        return {k: v for k, v in self.extra_params.items() if k not in self._novasight_extra_keys}

    @validator('host')
    def validate_host(cls, v):
        import ipaddress
        try:
            ip = ipaddress.ip_address(v)
            if ip.is_private or ip.is_loopback:
                logger.warning(f"Private/loopback IP address detected: {v}")
        except ValueError:
            pass
        return v

    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}


# ─── Abstract Base Connector ──────────────────────────────────────

class BaseConnector(ABC):
    """Abstract base class for data source connectors."""

    connector_type: str = "base"
    supported_auth_methods: List[str] = ["password"]
    supports_ssl: bool = True
    default_port: int = 0

    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._connection = None
        self._is_connected = False

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def test_connection(self) -> bool: ...

    @abstractmethod
    def get_schemas(self) -> List[str]: ...

    @abstractmethod
    def get_tables(self, schema: str) -> List[TableInfo]: ...

    @abstractmethod
    def get_table_schema(self, schema: str, table: str) -> TableInfo: ...

    def get_tables_with_columns(self, schema: str) -> List[TableInfo]:
        """
        Get all tables with their columns in a single optimized query.
        Override this method in connectors for better performance.
        Default implementation falls back to individual queries.
        """
        tables = self.get_tables(schema)
        for table in tables:
            try:
                table_with_cols = self.get_table_schema(schema, table.name)
                table.columns = table_with_cols.columns
            except Exception as e:
                logger.warning(f"Failed to get columns for {schema}.{table.name}: {e}")
                table.columns = []
        return tables

    @abstractmethod
    def fetch_data(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        batch_size: int = 10000,
    ) -> Iterator[List[Dict[str, Any]]]: ...

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> int:
        raise NotImplementedError("execute_query not implemented")

    def get_row_count(self, schema: str, table: str) -> int:
        query = f'SELECT COUNT(*) FROM "{schema}"."{table}"'
        try:
            for batch in self.fetch_data(query, batch_size=1):
                if batch:
                    return list(batch[0].values())[0]
        except Exception as e:
            logger.warning(f"Failed to get row count: {e}")
            return 0
        return 0

    def validate_query(self, query: str) -> tuple[bool, str]:
        query_upper = query.strip().upper()
        dangerous_keywords = [
            "DROP", "TRUNCATE", "DELETE", "UPDATE", "INSERT", "ALTER",
        ]
        for keyword in dangerous_keywords:
            if query_upper.startswith(keyword):
                return False, f"Query contains dangerous operation: {keyword}"
        return True, ""

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __repr__(self):
        return (
            f"<{self.__class__.__name__} "
            f"host={self.config.host} database={self.config.database}>"
        )
