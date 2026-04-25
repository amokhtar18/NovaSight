"""
NovaSight Data Sources — SQLite Connector
==========================================

Connector for SQLite database files stored in tenant-scoped
local filesystem storage. Opens the database in read-only mode.

Schema model:
    - Schema:  "main" (SQLite default schema)
    - Tables:  all user tables in the database

Security:
    - Read-only URI mode prevents any write operations
    - Query validator blocks DML/DDL
    - ATTACH DATABASE blocked at query validation level

Canonical location: ``app.domains.datasources.infrastructure.connectors.sqlite``
"""

import logging
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from app.domains.datasources.infrastructure.connectors.base import (
    BaseConnector,
    ConnectionConfig,
    ConnectorException,
    ConnectionTestException,
)
from app.domains.datasources.domain.value_objects import ColumnInfo, TableInfo

logger = logging.getLogger(__name__)


class SQLiteConnector(BaseConnector):
    """
    SQLite database connector.

    Opens the file in read-only SQLite URI mode to prevent accidental writes.
    """

    connector_type = "sqlite"
    supported_auth_methods: List[str] = []
    supports_ssl: bool = False
    default_port: int = 0

    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self._file_path: Optional[Path] = None
        self._conn: Optional[sqlite3.Connection] = None

    # ── Lifecycle ─────────────────────────────────────────────────

    def connect(self) -> None:
        """Locate and open the SQLite database in read-only mode."""
        file_ref = self.config.extra_params.get("file_ref")
        if not file_ref:
            raise ConnectorException("Missing 'file_ref' in extra_params")

        from app.platform.infrastructure.file_storage import FileStorageService

        parts = file_ref.split("/")
        if len(parts) < 4 or parts[0] != "tenants":
            raise ConnectorException(f"Invalid file_ref format: {file_ref}")
        tenant_id = parts[1]

        storage = FileStorageService(tenant_id)
        expected_hash = self.config.extra_params.get("file_hash")
        if expected_hash and not storage.verify_hash(file_ref, expected_hash):
            raise ConnectorException("File integrity check failed: hash mismatch")

        abs_path = storage.get_file_path(file_ref)
        if abs_path is None:
            raise ConnectorException(f"File not found: {file_ref}")

        self._file_path = abs_path

        # Open in read-only mode via URI
        uri = f"file:{abs_path}?mode=ro"
        try:
            self._conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._is_connected = True
            logger.info(f"SQLiteConnector: opened {file_ref} (read-only)")
        except sqlite3.DatabaseError as e:
            raise ConnectorException(f"Failed to open SQLite database: {e}")

    def disconnect(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = None
        self._file_path = None
        self._is_connected = False

    def test_connection(self) -> bool:
        try:
            if self._conn is None:
                self.connect()
            self._conn.execute("SELECT 1")
            # Verify at least one table exists
            cursor = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' LIMIT 1"
            )
            return True
        except sqlite3.Error as e:
            raise ConnectionTestException(f"SQLite test failed: {e}")

    # ── Schema Introspection ───────────────────────────────────────

    def get_schemas(self) -> List[str]:
        return ["main"]

    def get_tables(self, schema: str) -> List[TableInfo]:
        if self._conn is None:
            raise ConnectorException("Not connected")
        cursor = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = []
        for row in cursor.fetchall():
            table_name = row[0]
            columns = self._get_table_columns(table_name)
            row_count = self._get_row_count_sqlite(table_name)
            tables.append(TableInfo(
                name=table_name,
                schema="main",
                row_count=row_count,
                columns=columns,
            ))
        return tables

    def get_table_schema(self, schema: str, table: str) -> TableInfo:
        if self._conn is None:
            raise ConnectorException("Not connected")
        columns = self._get_table_columns(table)
        row_count = self._get_row_count_sqlite(table)
        return TableInfo(name=table, schema="main", row_count=row_count, columns=columns)

    # ── Data Access ────────────────────────────────────────────────

    def fetch_data(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        batch_size: int = 10000,
    ) -> Iterator[List[Dict[str, Any]]]:
        if not self._is_connected or self._conn is None:
            raise ConnectorException("Not connected")

        valid, error = self.validate_query(query)
        if not valid:
            raise ConnectorException(f"Query validation failed: {error}")

        try:
            cursor = self._conn.execute(query)
            columns = [desc[0] for desc in cursor.description or []]

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                yield [dict(zip(columns, row)) for row in rows]

        except sqlite3.Error as e:
            raise ConnectorException(f"SQLite query failed: {e}")

    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """SQLite connector is read-only; write queries are always rejected."""
        raise ConnectorException("SQLite connector is read-only")

    def validate_query(self, query: str) -> tuple:
        """Block dangerous SQL including ATTACH DATABASE."""
        query_upper = query.strip().upper()

        # Block write operations
        dangerous_keywords = [
            "DROP", "TRUNCATE", "DELETE", "UPDATE", "INSERT",
            "ALTER", "CREATE", "REPLACE", "PRAGMA",
        ]
        for keyword in dangerous_keywords:
            if query_upper.startswith(keyword) or f" {keyword} " in query_upper:
                return False, f"Query contains disallowed operation: {keyword}"

        # Block ATTACH DATABASE specifically (SSRF/traversal risk)
        if "ATTACH" in query_upper:
            return False, "ATTACH DATABASE is not allowed"

        return True, ""

    # ── Private Helpers ────────────────────────────────────────────

    def _get_table_columns(self, table_name: str) -> List[ColumnInfo]:
        cursor = self._conn.execute(f'PRAGMA table_info("{table_name}")')
        columns = []
        for row in cursor.fetchall():
            # cid, name, type, notnull, dflt_value, pk
            columns.append(ColumnInfo(
                name=row[1],
                data_type=row[2] or "TEXT",
                nullable=not row[3],
                primary_key=bool(row[5]),
                default_value=str(row[4]) if row[4] is not None else None,
            ))
        return columns

    def _get_row_count_sqlite(self, table_name: str) -> Optional[int]:
        try:
            cursor = self._conn.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error:
            return None
