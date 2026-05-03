"""
NovaSight ClickHouse Client
============================

Client for executing queries against ClickHouse data warehouse.
Provides tenant-isolated query execution with connection pooling.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from contextlib import contextmanager

from flask import current_app

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result of a ClickHouse query execution."""
    columns: List[str]
    rows: List[Tuple]
    row_count: int
    query: str
    execution_time_ms: float
    bytes_read: int = 0
    rows_read: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "columns": self.columns,
            "rows": [list(row) for row in self.rows],
            "row_count": self.row_count,
            "query": self.query,
            "execution_time_ms": self.execution_time_ms,
            "bytes_read": self.bytes_read,
            "rows_read": self.rows_read,
        }
    
    def to_records(self) -> List[Dict[str, Any]]:
        """Convert rows to list of dictionaries."""
        return [dict(zip(self.columns, row)) for row in self.rows]


class ClickHouseError(Exception):
    """Base exception for ClickHouse errors."""
    pass


class ClickHouseConnectionError(ClickHouseError):
    """Raised when connection to ClickHouse fails."""
    pass


class ClickHouseQueryError(ClickHouseError):
    """Raised when query execution fails."""
    pass


class ClickHouseClient:
    """
    Client for ClickHouse database operations.
    
    Provides a high-level interface for executing queries against ClickHouse
    with support for:
    - Tenant isolation via database selection
    - Query parameterization
    - Connection management
    - Query metrics
    
    Usage:
        client = ClickHouseClient(database='tenant_acme')
        result = client.execute('SELECT * FROM orders LIMIT 10')
        for row in result.rows:
            print(row)
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        secure: bool = False,
        connect_timeout: int = 10,
        send_receive_timeout: int = 300,
        tenant_id: Optional[str] = None,
        use_infrastructure_config: bool = True,
    ):
        """
        Initialize ClickHouse client.
        
        Args:
            host: ClickHouse server host
            port: ClickHouse native port (default 9000)
            database: Database to use
            user: Username for authentication
            password: Password for authentication
            secure: Use TLS connection
            connect_timeout: Connection timeout in seconds
            send_receive_timeout: Query timeout in seconds
            tenant_id: Optional tenant ID for tenant-specific config
            use_infrastructure_config: Whether to use infrastructure config service
        """
        import os

        # ── 1. Environment / Flask config wins over DB-seeded values ──
        # This client speaks the native ClickHouse binary protocol, so any
        # source-of-truth that points at the HTTP port (8123) will fail with
        # "Unexpected EOF while reading bytes". Operators control the real
        # values via env vars (see backend/entrypoint.sh and docker-compose);
        # the DB infrastructure_config table is only used as a fallback.
        env_host = os.environ.get('CLICKHOUSE_HOST')
        env_port = os.environ.get('CLICKHOUSE_PORT') or os.environ.get('CLICKHOUSE_NATIVE_PORT')
        env_user = os.environ.get('CLICKHOUSE_USER')
        env_password = os.environ.get('CLICKHOUSE_PASSWORD')
        env_database = os.environ.get('CLICKHOUSE_DATABASE')
        env_secure_raw = os.environ.get('CLICKHOUSE_SECURE')

        flask_host = flask_port = flask_user = flask_password = flask_secure = None
        try:
            cfg = current_app.config
            flask_host = cfg.get('CLICKHOUSE_HOST')
            flask_port = cfg.get('CLICKHOUSE_PORT')
            flask_user = cfg.get('CLICKHOUSE_USER')
            flask_password = cfg.get('CLICKHOUSE_PASSWORD')
            flask_secure = cfg.get('CLICKHOUSE_SECURE')
        except RuntimeError:
            pass  # outside app context

        # ── 2. DB-stored infrastructure config is a fallback ──
        infra_settings: Dict[str, Any] = {}
        if use_infrastructure_config:
            try:
                from app.domains.tenants.infrastructure.config_service import (
                    InfrastructureConfigService,
                )
                config_service = InfrastructureConfigService()
                infra_settings = config_service.get_effective_settings(
                    'clickhouse', tenant_id
                ) or {}
            except Exception as e:
                logger.debug(f"Could not load infrastructure config: {e}")

        def _pick(*candidates, default=None):
            for c in candidates:
                if c is not None and c != '':
                    return c
            return default

        self.host = _pick(host, env_host, flask_host, infra_settings.get('host'), default='localhost')

        raw_port = _pick(port, env_port, flask_port, infra_settings.get('port'), default=9000)
        try:
            resolved_port = int(raw_port)
        except (TypeError, ValueError):
            resolved_port = 9000
        # Safety net: clickhouse_driver speaks the native binary protocol on
        # port 9000. If config (especially the seeded DB default) accidentally
        # points at the HTTP port 8123, transparently coerce to 9000 so the
        # connection actually works.
        if resolved_port == 8123:
            logger.warning(
                "ClickHouse port 8123 (HTTP) is not usable by clickhouse_driver "
                "native protocol; coercing to 9000."
            )
            resolved_port = 9000
        self.port = resolved_port

        self.user = _pick(user, env_user, flask_user, infra_settings.get('user'), default='default')
        self.password = _pick(
            password, env_password, flask_password, infra_settings.get('password'), default=''
        )
        self.database = _pick(
            database, env_database, infra_settings.get('database'), default='default'
        )

        if env_secure_raw is not None:
            env_secure = env_secure_raw.lower() in ('1', 'true', 'yes')
        else:
            env_secure = None
        self.secure = bool(_pick(
            secure if secure else None,
            env_secure,
            flask_secure,
            infra_settings.get('secure'),
            default=False,
        ))

        self.connect_timeout = int(infra_settings.get('connect_timeout', connect_timeout))
        self.send_receive_timeout = int(
            infra_settings.get('send_receive_timeout', send_receive_timeout)
        )

        self._client = None
    
    @property
    def client(self):
        """Get or create the ClickHouse client connection."""
        if self._client is None:
            self._client = self._create_client()
        return self._client
    
    def _create_client(self):
        """Create a new ClickHouse client connection."""
        try:
            from clickhouse_driver import Client
            
            client = Client(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                secure=self.secure,
                connect_timeout=self.connect_timeout,
                send_receive_timeout=self.send_receive_timeout,
                settings={
                    'use_numpy': False,
                    'max_block_size': 100000,
                }
            )
            
            logger.debug(f"Connected to ClickHouse: {self.host}:{self.port}/{self.database}")
            return client
            
        except ImportError:
            logger.warning("clickhouse-driver not installed, using mock client")
            return MockClickHouseClient(self.database)
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise ClickHouseConnectionError(f"Connection failed: {e}")
    
    def execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        with_column_types: bool = False,
    ) -> QueryResult:
        """
        Execute a query and return results.
        
        Args:
            query: SQL query to execute
            params: Query parameters for parameterized queries
            with_column_types: Include column type information
        
        Returns:
            QueryResult with columns, rows, and metadata
        
        Raises:
            ClickHouseQueryError: If query execution fails
        """
        import time
        
        logger.debug(f"Executing query: {query[:200]}...")
        
        start_time = time.time()
        
        try:
            result = self.client.execute(
                query,
                params=params,
                with_column_types=True,
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            if with_column_types:
                rows, column_types = result if isinstance(result, tuple) else (result, [])
                columns = [ct[0] for ct in column_types]
            else:
                # Result is list of tuples or list with column types
                if result and isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], tuple) and len(result[0]) == 2:
                        # Might be column types format
                        rows = result
                        columns = [f"col_{i}" for i in range(len(rows[0]) if rows else 0)]
                    else:
                        rows = result
                        columns = [f"col_{i}" for i in range(len(rows[0]) if rows else 0)]
                else:
                    rows = result or []
                    columns = []
            
            # Handle the case where execute returns (data, columns_with_types)
            if isinstance(result, tuple) and len(result) == 2:
                rows_data, columns_info = result
                columns = [c[0] for c in columns_info]
                rows = rows_data
            else:
                rows = result
            
            query_result = QueryResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                query=query,
                execution_time_ms=execution_time,
            )
            
            logger.debug(f"Query completed: {len(rows)} rows in {execution_time:.2f}ms")
            
            return query_result
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise ClickHouseQueryError(f"Query failed: {e}")
    
    def execute_iter(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        chunk_size: int = 10000,
    ):
        """
        Execute a query and iterate over results in chunks.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            chunk_size: Number of rows per chunk
        
        Yields:
            Chunks of rows
        """
        try:
            for chunk in self.client.execute_iter(
                query,
                params=params,
                chunk_size=chunk_size,
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Query iteration failed: {e}")
            raise ClickHouseQueryError(f"Query iteration failed: {e}")
    
    def insert(
        self,
        table: str,
        data: List[Tuple],
        columns: Optional[List[str]] = None,
    ) -> int:
        """
        Insert data into a table.
        
        Args:
            table: Target table name
            data: List of tuples containing row data
            columns: Optional list of column names
        
        Returns:
            Number of rows inserted
        """
        if not data:
            return 0
        
        try:
            if columns:
                column_str = f"({', '.join(columns)})"
            else:
                column_str = ""
            
            query = f"INSERT INTO {table} {column_str} VALUES"
            
            self.client.execute(query, data)
            
            logger.debug(f"Inserted {len(data)} rows into {table}")
            return len(data)
            
        except Exception as e:
            logger.error(f"Insert failed: {e}")
            raise ClickHouseQueryError(f"Insert failed: {e}")
    
    def table_exists(self, table: str) -> bool:
        """Check if a table exists."""
        try:
            result = self.execute(
                f"SELECT 1 FROM system.tables WHERE database = '{self.database}' AND name = '{table}'"
            )
            return result.row_count > 0
        except ClickHouseQueryError:
            return False
    
    def get_table_schema(self, table: str) -> List[Dict[str, str]]:
        """Get column information for a table."""
        result = self.execute(f"DESCRIBE TABLE {table}")
        
        columns = []
        for row in result.rows:
            columns.append({
                "name": row[0],
                "type": row[1],
                "default_type": row[2] if len(row) > 2 else None,
                "default_expression": row[3] if len(row) > 3 else None,
            })
        
        return columns
    
    def close(self):
        """Close the client connection."""
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


class MockClickHouseClient:
    """
    Mock ClickHouse client for testing without a real connection.
    """
    
    def __init__(self, database: str = 'default'):
        self.database = database
        self._tables: Dict[str, List[Dict]] = {}
    
    def execute(
        self,
        query: str,
        params: Optional[Dict] = None,
        with_column_types: bool = False,
    ):
        """Execute a mock query."""
        logger.debug(f"MockClickHouse executing: {query[:100]}...")
        
        # Return empty results for most queries
        if with_column_types:
            return [], []
        return []
    
    def execute_iter(self, query: str, params: Optional[Dict] = None, chunk_size: int = 10000):
        """Mock iterator."""
        yield []
    
    def disconnect(self):
        """Mock disconnect."""
        pass


# Factory function for getting a client
def get_clickhouse_client(
    database: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> ClickHouseClient:
    """
    Get a ClickHouse client for a specific database or tenant.
    
    Args:
        database: Explicit database name
        tenant_id: Tenant ID (will resolve to tenant slug for database name)
    
    Returns:
        ClickHouseClient instance
    """
    if tenant_id and not database:
        # Resolve tenant slug from tenant ID
        try:
            from app.domains.tenants.domain.models import Tenant
            from uuid import UUID
            tenant = Tenant.query.filter(Tenant.id == UUID(str(tenant_id))).first()
            if tenant and tenant.slug:
                # Replace hyphens with underscores for ClickHouse database naming
                slug = tenant.slug.replace('-', '_')
                database = f"tenant_{slug}"
                logger.debug(f"Resolved tenant {tenant_id} to database {database}")
            else:
                # Fallback to UUID-based naming (also replace hyphens)
                clean_id = str(tenant_id).replace('-', '_')
                database = f"tenant_{clean_id}"
                logger.warning(f"Tenant {tenant_id} has no slug, using UUID for database name")
        except Exception as e:
            logger.warning(f"Could not resolve tenant slug: {e}")
            clean_id = str(tenant_id).replace('-', '_')
            database = f"tenant_{clean_id}"
    
    return ClickHouseClient(database=database)
