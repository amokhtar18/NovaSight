"""
NovaSight Data Sources — Oracle Connector
==========================================

Oracle database connector implementation using python-oracledb.

Canonical location: ``app.domains.datasources.infrastructure.connectors.oracle``
"""

import oracledb
from oracledb import Connection as OracleConnection
from typing import List, Iterator, Dict, Any, Optional
import logging

from app.domains.datasources.infrastructure.connectors.base import (
    BaseConnector,
    ConnectionConfig,
    ConnectorException,
    ConnectionTestException,
)
from app.domains.datasources.domain.value_objects import ColumnInfo, TableInfo

logger = logging.getLogger(__name__)


class OracleConnector(BaseConnector):
    """Oracle database connector."""

    connector_type = "oracle"
    supported_auth_methods = ["password", "wallet", "kerberos"]
    supports_ssl = True
    default_port = 1521

    _connection: Optional[OracleConnection]

    def connect(self) -> None:
        """Establish connection to Oracle database."""
        try:
            # Build connection string - support both SID and service name
            dsn = self._build_dsn()

            # Get connection timeout from extra_params or use default
            connect_timeout = 10  # Default 10 seconds
            if self.config.extra_params:
                connect_timeout = self.config.extra_params.get("connect_timeout", connect_timeout)

            # Build connection parameters dynamically
            connection_kwargs: Dict[str, Any] = {
                "user": self.config.username,
                "password": self.config.password,
                "dsn": dsn,
                # TCP connection timeout (thin mode) - prevents hanging on unreachable hosts
                "tcp_connect_timeout": connect_timeout,
            }

            if self.config.extra_params:
                # Handle wallet location for SSL/TLS
                if "wallet_location" in self.config.extra_params:
                    connection_kwargs["config_dir"] = self.config.extra_params["wallet_location"]
                    connection_kwargs["wallet_location"] = self.config.extra_params["wallet_location"]
                    if wallet_pwd := self.config.extra_params.get("wallet_password"):
                        connection_kwargs["wallet_password"] = wallet_pwd

                # Handle thick mode for older Oracle versions or advanced features
                if self.config.extra_params.get("thick_mode"):
                    self._init_thick_mode()
                    # In thick mode, timeout is controlled via sqlnet.ora or TNS settings
                    # Remove tcp_connect_timeout as it's thin-mode only
                    connection_kwargs.pop("tcp_connect_timeout", None)

            self._connection = oracledb.connect(**connection_kwargs)  # type: ignore[arg-type]
            self._is_connected = True
            logger.info(
                f"Connected to Oracle: "
                f"{self.config.host}:{self.config.port}/{self.config.database}"
            )

        except oracledb.Error as e:
            error_str = str(e)
            logger.error(f"Failed to connect to Oracle: {e}")

            # Check for timeout-related errors
            if any(term in error_str.lower() for term in ["timeout", "timed out", "dpy-4011", "dpy-6005"]):
                raise ConnectorException(
                    f"Oracle connection timed out: {error_str}\n\n"
                    "The connection attempt exceeded the timeout limit. This can happen if:\n"
                    "1. The Oracle server is unreachable (check host/port)\n"
                    "2. A firewall is blocking the connection\n"
                    "3. The Oracle listener is not running\n"
                    "You can increase the timeout by setting 'connect_timeout' in extra_params."
                )

            # Check if this is a thin mode compatibility error
            if "DPY-3010" in error_str or "thin mode" in error_str.lower():
                raise ConnectorException(
                    f"Oracle connection failed: {error_str}\n\n"
                    "This Oracle database version requires 'thick mode' with Oracle Instant Client. "
                    "To enable thick mode:\n"
                    "1. Install Oracle Instant Client in the container\n"
                    "2. Set 'thick_mode': true in extra_params when creating the connection\n"
                    "See: https://python-oracledb.readthedocs.io/en/latest/user_guide/initialization.html"
                )
            raise ConnectorException(f"Oracle connection failed: {error_str}")

    def _init_thick_mode(self) -> None:
        """Initialize Oracle thick mode with Instant Client."""
        try:
            # Check for custom lib_dir in extra_params
            lib_dir = self.config.extra_params.get("instant_client_dir")
            if lib_dir:
                oracledb.init_oracle_client(lib_dir=lib_dir)
            else:
                # Try default locations
                oracledb.init_oracle_client()
            logger.info("Oracle thick mode initialized successfully")
        except oracledb.Error as e:
            if "already been initialized" in str(e).lower():
                # Already initialized, that's fine
                pass
            else:
                raise ConnectorException(
                    f"Failed to initialize Oracle thick mode: {e}\n"
                    "Ensure Oracle Instant Client is installed and accessible."
                )

    def _build_dsn(self) -> str:
        """Build Oracle DSN connection string."""
        # Check if service_name is provided in extra_params
        service_name = self.config.extra_params.get("service_name")

        if service_name:
            # Use service name format
            dsn = oracledb.makedsn(
                host=self.config.host,
                port=self.config.port,
                service_name=service_name,
            )
        else:
            # Use SID format (database field as SID)
            dsn = oracledb.makedsn(
                host=self.config.host,
                port=self.config.port,
                sid=self.config.database,
            )

        return dsn

    def disconnect(self) -> None:
        """Close Oracle connection."""
        if self._connection:
            try:
                self._connection.close()
                self._is_connected = False
                logger.info("Disconnected from Oracle")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._connection = None

    def _ensure_connection(self) -> OracleConnection:
        """Ensure connection exists and return it."""
        if not self._connection:
            self.connect()
        if not self._connection:
            raise ConnectorException("Failed to establish Oracle connection")
        return self._connection

    def test_connection(self) -> bool:
        """Test Oracle connection."""
        try:
            conn = self._ensure_connection()

            with conn.cursor() as cur:
                cur.execute("SELECT * FROM V$VERSION WHERE BANNER LIKE 'Oracle%'")
                row = cur.fetchone()
                version = row[0] if row else "Unknown"
                logger.info(f"Oracle connection test successful: {version}")
                return True

        except Exception as e:
            logger.error(f"Oracle connection test failed: {e}")
            raise ConnectionTestException(f"Connection test failed: {str(e)}")

    def get_schemas(self) -> List[str]:
        """List all schemas (users) in Oracle database."""
        try:
            conn = self._ensure_connection()

            with conn.cursor() as cur:
                cur.execute("""
                    SELECT username
                    FROM all_users
                    WHERE username NOT IN (
                        'SYS', 'SYSTEM', 'OUTLN', 'DIP', 'ORACLE_OCM',
                        'DBSNMP', 'APPQOSSYS', 'WMSYS', 'EXFSYS', 'CTXSYS',
                        'XDB', 'ANONYMOUS', 'ORDSYS', 'ORDDATA', 'ORDPLUGINS',
                        'MDSYS', 'OLAPSYS', 'SYSMAN', 'FLOWS_FILES', 'APEX_PUBLIC_USER',
                        'APEX_040000', 'APEX_040100', 'APEX_040200', 'OWBSYS', 'OWBSYS_AUDIT',
                        'GSMADMIN_INTERNAL', 'AUDSYS', 'DVF', 'DVSYS', 'LBACSYS',
                        'DBSFWUSER', 'REMOTE_SCHEDULER_AGENT', 'OJVMSYS', 'SI_INFORMTN_SCHEMA',
                        'GGSYS', 'GSMCATUSER', 'SYSBACKUP', 'SYSDG', 'SYSKM', 'SYSRAC',
                        'SYS$UMF', 'GSMUSER', 'XS$NULL'
                    )
                    ORDER BY username
                """)
                return [row[0] for row in cur.fetchall()]

        except oracledb.Error as e:
            logger.error(f"Failed to get schemas: {e}")
            raise ConnectorException(f"Failed to get schemas: {str(e)}")

    def get_tables(self, schema: str) -> List[TableInfo]:
        """List all tables in an Oracle schema."""
        try:
            conn = self._ensure_connection()

            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        t.table_name,
                        t.owner,
                        'BASE TABLE' as table_type,
                        c.comments,
                        t.num_rows
                    FROM all_tables t
                    LEFT JOIN all_tab_comments c
                        ON t.owner = c.owner
                        AND t.table_name = c.table_name
                    WHERE t.owner = :schema
                    UNION ALL
                    SELECT
                        v.view_name,
                        v.owner,
                        'VIEW' as table_type,
                        c.comments,
                        NULL as num_rows
                    FROM all_views v
                    LEFT JOIN all_tab_comments c
                        ON v.owner = c.owner
                        AND v.view_name = c.table_name
                    WHERE v.owner = :schema
                    ORDER BY 1
                    """,
                    {"schema": schema.upper()},
                )

                tables = []
                for row in cur.fetchall():
                    tables.append(
                        TableInfo(
                            name=row[0],
                            schema=row[1],
                            columns=[],
                            row_count=int(row[4] or 0),
                            comment=row[3] or "",
                            table_type=row[2],
                        )
                    )

                return tables

        except oracledb.Error as e:
            logger.error(f"Failed to get tables for schema {schema}: {e}")
            raise ConnectorException(f"Failed to get tables: {str(e)}")

    def get_table_schema(self, schema: str, table: str) -> TableInfo:
        """Get detailed schema for an Oracle table."""
        try:
            conn = self._ensure_connection()

            with conn.cursor() as cur:
                # Check if table exists and get metadata
                cur.execute(
                    """
                    SELECT
                        CASE WHEN t.table_name IS NOT NULL THEN 'BASE TABLE' ELSE 'VIEW' END as table_type,
                        c.comments,
                        t.num_rows
                    FROM (
                        SELECT table_name, owner, num_rows
                        FROM all_tables
                        WHERE owner = :owner_name AND table_name = :tbl_name
                        UNION ALL
                        SELECT view_name, owner, NULL
                        FROM all_views
                        WHERE owner = :owner_name AND view_name = :tbl_name
                    ) t
                    LEFT JOIN all_tab_comments c
                        ON t.owner = c.owner AND t.table_name = c.table_name
                    WHERE ROWNUM = 1
                    """,
                    {"owner_name": schema.upper(), "tbl_name": table.upper()},
                )

                table_row = cur.fetchone()
                if not table_row:
                    raise ConnectorException(f"Table {schema}.{table} not found")

                columns = self._get_columns(schema, table)
                row_count = int(table_row[2] or 0)

                return TableInfo(
                    name=table.upper(),
                    schema=schema.upper(),
                    columns=columns,
                    row_count=row_count,
                    comment=table_row[1] or "",
                    table_type=table_row[0],
                )

        except oracledb.Error as e:
            logger.error(f"Failed to get schema for table {schema}.{table}: {e}")
            raise ConnectorException(f"Failed to get table schema: {str(e)}")

    def _get_columns(self, schema: str, table: str) -> List[ColumnInfo]:
        """Get column information for a table."""
        conn = self._ensure_connection()

        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.column_name,
                    c.data_type,
                    c.nullable,
                    c.data_default,
                    c.char_length,
                    c.data_precision,
                    c.data_scale,
                    CASE WHEN pk.column_name IS NOT NULL THEN 1 ELSE 0 END as is_primary_key,
                    cc.comments
                FROM all_tab_columns c
                LEFT JOIN (
                    SELECT cols.owner, cols.table_name, cols.column_name
                    FROM all_constraints cons
                    JOIN all_cons_columns cols
                        ON cons.owner = cols.owner
                        AND cons.constraint_name = cols.constraint_name
                    WHERE cons.constraint_type = 'P'
                    AND cons.owner = :owner_name
                    AND cons.table_name = :tbl_name
                ) pk
                    ON c.owner = pk.owner
                    AND c.table_name = pk.table_name
                    AND c.column_name = pk.column_name
                LEFT JOIN all_col_comments cc
                    ON c.owner = cc.owner
                    AND c.table_name = cc.table_name
                    AND c.column_name = cc.column_name
                WHERE c.owner = :owner_name AND c.table_name = :tbl_name
                ORDER BY c.column_id
                """,
                {"owner_name": schema.upper(), "tbl_name": table.upper()},
            )

            columns = []
            for row in cur.fetchall():
                columns.append(
                    ColumnInfo(
                        name=row[0],
                        data_type=row[1],
                        nullable=row[2] == "Y",
                        primary_key=bool(row[7]),
                        comment=row[8] or "",
                        default_value=row[3],
                        max_length=row[4],
                        precision=row[5],
                        scale=row[6],
                    )
                )

            return columns

    def get_tables_with_columns(self, schema: str) -> List[TableInfo]:
        """
        Get all tables with columns in optimized batch queries for Oracle.
        Fetches all columns for all tables in a single query.
        """
        try:
            conn = self._ensure_connection()
            schema_upper = schema.upper()

            # First get all tables
            tables = self.get_tables(schema)
            if not tables:
                return []

            # Build a map of table names to TableInfo objects
            table_map = {t.name: t for t in tables}

            # Fetch all columns for all tables in one query
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        c.table_name,
                        c.column_name,
                        c.data_type,
                        c.nullable,
                        c.data_default,
                        c.char_length,
                        c.data_precision,
                        c.data_scale,
                        CASE WHEN pk.column_name IS NOT NULL THEN 1 ELSE 0 END as is_primary_key,
                        cc.comments
                    FROM all_tab_columns c
                    LEFT JOIN (
                        SELECT cols.owner, cols.table_name, cols.column_name
                        FROM all_constraints cons
                        JOIN all_cons_columns cols
                            ON cons.owner = cols.owner
                            AND cons.constraint_name = cols.constraint_name
                        WHERE cons.constraint_type = 'P'
                        AND cons.owner = :owner_name
                    ) pk
                        ON c.owner = pk.owner
                        AND c.table_name = pk.table_name
                        AND c.column_name = pk.column_name
                    LEFT JOIN all_col_comments cc
                        ON c.owner = cc.owner
                        AND c.table_name = cc.table_name
                        AND c.column_name = cc.column_name
                    WHERE c.owner = :owner_name
                    ORDER BY c.table_name, c.column_id
                    """,
                    {"owner_name": schema_upper},
                )

                # Group columns by table
                for row in cur.fetchall():
                    table_name = row[0]
                    if table_name in table_map:
                        table_map[table_name].columns.append(
                            ColumnInfo(
                                name=row[1],
                                data_type=row[2],
                                nullable=row[3] == "Y",
                                primary_key=bool(row[8]),
                                comment=row[9] or "",
                                default_value=row[4],
                                max_length=row[5],
                                precision=row[6],
                                scale=row[7],
                            )
                        )

            return tables

        except oracledb.Error as e:
            logger.error(f"Failed to get tables with columns for schema {schema}: {e}")
            # Fall back to individual queries
            return super().get_tables_with_columns(schema)

    def _is_thick_mode(self) -> bool:
        """Check if thick mode is enabled (indicates Oracle 11g or earlier)."""
        return bool(self.config.extra_params and self.config.extra_params.get("thick_mode"))

    def _preprocess_query(self, query: str) -> str:
        """Preprocess query for Oracle compatibility.
        
        Handles:
        - Trailing semicolons (Oracle doesn't allow in programmatic execution)
        - LIMIT clause conversion:
          - ROWNUM for thick mode (Oracle 11g and earlier)
          - FETCH FIRST for thin mode (Oracle 12c+)
        """
        import re
        
        # Strip trailing semicolons (Oracle doesn't like them)
        query = query.strip()
        while query.endswith(';'):
            query = query[:-1].strip()
        
        use_rownum = self._is_thick_mode()
        
        # Convert LIMIT N OFFSET M first (more specific pattern)
        limit_offset_match = re.search(
            r'\bLIMIT\s+(\d+)\s+OFFSET\s+(\d+)\s*$', query, re.IGNORECASE
        )
        if limit_offset_match:
            limit_val = int(limit_offset_match.group(1))
            offset_val = int(limit_offset_match.group(2))
            base_query = query[:limit_offset_match.start()].strip()
            
            if use_rownum:
                # Oracle 11g: Use ROWNUM with subquery for offset
                query = f"""SELECT * FROM (
                    SELECT a.*, ROWNUM rnum FROM (
                        {base_query}
                    ) a WHERE ROWNUM <= {offset_val + limit_val}
                ) WHERE rnum > {offset_val}"""
            else:
                # Oracle 12c+: Use OFFSET/FETCH
                query = f"{base_query} OFFSET {offset_val} ROWS FETCH NEXT {limit_val} ROWS ONLY"
            return query
        
        # Convert LIMIT N (simpler pattern)
        limit_match = re.search(r'\bLIMIT\s+(\d+)\s*$', query, re.IGNORECASE)
        if limit_match:
            limit_val = limit_match.group(1)
            base_query = query[:limit_match.start()].strip()
            
            if use_rownum:
                # Oracle 11g: Use ROWNUM
                query = f"SELECT * FROM ({base_query}) WHERE ROWNUM <= {limit_val}"
            else:
                # Oracle 12c+: Use FETCH FIRST
                query = f"{base_query} FETCH FIRST {limit_val} ROWS ONLY"
            return query
        
        return query

    def fetch_data(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        batch_size: int = 10000,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Fetch data from Oracle in batches."""
        try:
            conn = self._ensure_connection()
            
            # Preprocess query for Oracle compatibility
            query = self._preprocess_query(query)

            with conn.cursor() as cur:
                cur.arraysize = batch_size

                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)

                # Get column names for dict conversion
                columns = [col[0] for col in cur.description]

                while True:
                    rows = cur.fetchmany(batch_size)
                    if not rows:
                        break
                    # Convert tuples to dictionaries
                    yield [dict(zip(columns, row)) for row in rows]

        except oracledb.Error as e:
            logger.error(f"Failed to fetch data: {e}")
            raise ConnectorException(f"Failed to fetch data: {str(e)}")

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Execute a query that doesn't return results."""
        try:
            conn = self._ensure_connection()
            
            # Preprocess query for Oracle compatibility
            query = self._preprocess_query(query)

            with conn.cursor() as cur:
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)

                conn.commit()
                return cur.rowcount

        except oracledb.Error as e:
            conn.rollback()
            logger.error(f"Failed to execute query: {e}")
            raise ConnectorException(f"Failed to execute query: {str(e)}")

    def get_row_count(self, schema: str, table: str) -> int:
        """Get approximate row count for a table."""
        try:
            conn = self._ensure_connection()

            with conn.cursor() as cur:
                # Use statistics if available
                cur.execute(
                    """
                    SELECT num_rows
                    FROM all_tables
                    WHERE owner = :schema AND table_name = :table
                    """,
                    {"schema": schema.upper(), "table": table.upper()},
                )

                row = cur.fetchone()
                if row and row[0] and row[0] > 0:
                    return row[0]

                # Fall back to COUNT(*) for accurate count
                return super().get_row_count(schema, table)

        except Exception as e:
            logger.warning(f"Failed to get row count estimate: {e}")
            return super().get_row_count(schema, table)

    def validate_query(self, query: str) -> tuple[bool, str]:
        """Validate a query for Oracle specifics."""
        # Use base validation first
        is_valid, error_msg = super().validate_query(query)
        if not is_valid:
            return is_valid, error_msg

        # Oracle-specific dangerous operations
        query_upper = query.strip().upper()
        oracle_dangerous = ["EXECUTE IMMEDIATE", "DBMS_SQL", "CREATE OR REPLACE"]
        for keyword in oracle_dangerous:
            if keyword in query_upper:
                return False, f"Query contains potentially dangerous Oracle operation: {keyword}"

        return True, ""
