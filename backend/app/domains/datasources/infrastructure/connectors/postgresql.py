"""
NovaSight Data Sources — PostgreSQL Connector
===============================================

PostgreSQL database connector implementation.

Canonical location: ``app.domains.datasources.infrastructure.connectors.postgresql``
"""

import psycopg2
from psycopg2.extras import RealDictCursor
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


class PostgreSQLConnector(BaseConnector):
    """PostgreSQL database connector."""

    connector_type = "postgresql"
    supported_auth_methods = ["password", "iam", "certificate"]
    supports_ssl = True
    default_port = 5432

    def connect(self) -> None:
        """Establish connection to PostgreSQL database."""
        try:
            connection_params = {
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "user": self.config.username,
                "password": self.config.password,
                "sslmode": self.config.ssl_mode or ("require" if self.config.ssl else "disable"),
                "connect_timeout": 10,
                "application_name": "NovaSight",
                **self.config.driver_extra_params,
            }

            self._connection = psycopg2.connect(**connection_params)
            self._is_connected = True
            logger.info(
                f"Connected to PostgreSQL: "
                f"{self.config.host}:{self.config.port}/{self.config.database}"
            )

        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise ConnectorException(f"PostgreSQL connection failed: {str(e)}")

    def disconnect(self) -> None:
        """Close PostgreSQL connection."""
        if self._connection:
            try:
                self._connection.close()
                self._is_connected = False
                logger.info("Disconnected from PostgreSQL")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._connection = None

    def test_connection(self) -> bool:
        """Test PostgreSQL connection."""
        try:
            if not self._connection or self._connection.closed:
                self.connect()

            with self._connection.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                logger.info(f"PostgreSQL connection test successful: {version}")
                return True

        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            raise ConnectionTestException(f"Connection test failed: {str(e)}")

    def get_schemas(self) -> List[str]:
        """List all schemas in PostgreSQL database."""
        try:
            with self._connection.cursor() as cur:
                cur.execute("""
                    SELECT schema_name
                    FROM information_schema.schemata
                    WHERE schema_name NOT IN (
                        'pg_catalog', 'information_schema', 'pg_toast'
                    )
                    AND schema_name NOT LIKE 'pg_temp%%'
                    AND schema_name NOT LIKE 'pg_toast_temp%%'
                    ORDER BY schema_name
                """)
                return [row[0] for row in cur.fetchall()]

        except psycopg2.Error as e:
            logger.error(f"Failed to get schemas: {e}")
            raise ConnectorException(f"Failed to get schemas: {str(e)}")

    def get_tables(self, schema: str) -> List[TableInfo]:
        """List all tables in a PostgreSQL schema."""
        try:
            with self._connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        t.table_name,
                        t.table_schema,
                        t.table_type,
                        obj_description(
                            (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass
                        ) as comment,
                        pg_stat_user_tables.n_live_tup as row_count
                    FROM information_schema.tables t
                    LEFT JOIN pg_stat_user_tables
                        ON pg_stat_user_tables.schemaname = t.table_schema
                        AND pg_stat_user_tables.relname = t.table_name
                    WHERE t.table_schema = %s
                    AND t.table_type IN ('BASE TABLE', 'VIEW')
                    ORDER BY t.table_name
                    """,
                    (schema,),
                )

                tables = []
                for row in cur.fetchall():
                    tables.append(
                        TableInfo(
                            name=row["table_name"],
                            schema=row["table_schema"],
                            columns=[],
                            row_count=int(row["row_count"] or 0),
                            comment=row["comment"] or "",
                            table_type=row["table_type"],
                        )
                    )

                return tables

        except psycopg2.Error as e:
            logger.error(f"Failed to get tables for schema {schema}: {e}")
            raise ConnectorException(f"Failed to get tables: {str(e)}")

    def get_table_schema(self, schema: str, table: str) -> TableInfo:
        """Get detailed schema for a PostgreSQL table."""
        try:
            with self._connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        table_type,
                        obj_description(
                            (quote_ident(%s) || '.' || quote_ident(%s))::regclass
                        ) as comment
                    FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                    """,
                    (schema, table, schema, table),
                )

                table_row = cur.fetchone()
                if not table_row:
                    raise ConnectorException(f"Table {schema}.{table} not found")

                columns = self._get_columns(schema, table)
                row_count = self.get_row_count(schema, table)

                return TableInfo(
                    name=table,
                    schema=schema,
                    columns=columns,
                    row_count=row_count,
                    comment=table_row["comment"] or "",
                    table_type=table_row["table_type"],
                )

        except psycopg2.Error as e:
            logger.error(f"Failed to get schema for table {schema}.{table}: {e}")
            raise ConnectorException(f"Failed to get table schema: {str(e)}")

    def _get_columns(self, schema: str, table: str) -> List[ColumnInfo]:
        """Get column information for a table."""
        with self._connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    c.column_name,
                    c.data_type,
                    c.is_nullable = 'YES' as is_nullable,
                    c.column_default,
                    c.character_maximum_length,
                    c.numeric_precision,
                    c.numeric_scale,
                    CASE WHEN pk.column_name IS NOT NULL
                         THEN true ELSE false END as is_primary_key,
                    col_description(
                        (quote_ident(%s) || '.' || quote_ident(%s))::regclass,
                        c.ordinal_position
                    ) as comment
                FROM information_schema.columns c
                LEFT JOIN (
                    SELECT ku.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage ku
                        ON tc.constraint_name = ku.constraint_name
                        AND tc.table_schema = ku.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_schema = %s
                    AND tc.table_name = %s
                ) pk ON c.column_name = pk.column_name
                WHERE c.table_schema = %s AND c.table_name = %s
                ORDER BY c.ordinal_position
                """,
                (schema, table, schema, table, schema, table),
            )

            columns = []
            for row in cur.fetchall():
                columns.append(
                    ColumnInfo(
                        name=row["column_name"],
                        data_type=row["data_type"],
                        nullable=row["is_nullable"],
                        primary_key=row["is_primary_key"],
                        comment=row["comment"] or "",
                        default_value=row["column_default"],
                        max_length=row["character_maximum_length"],
                        precision=row["numeric_precision"],
                        scale=row["numeric_scale"],
                    )
                )

            return columns

    def get_tables_with_columns(self, schema: str) -> List[TableInfo]:
        """
        Get all tables with columns in optimized batch queries for PostgreSQL.
        Fetches all columns for all tables in a single query.
        """
        try:
            # First get all tables
            tables = self.get_tables(schema)
            if not tables:
                return []

            # Build a map of table names to TableInfo objects
            table_map = {t.name: t for t in tables}

            # Fetch all columns for all tables in the schema in one query
            with self._connection.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT
                        c.table_name,
                        c.column_name,
                        c.data_type,
                        c.is_nullable = 'YES' as is_nullable,
                        c.column_default,
                        c.character_maximum_length,
                        c.numeric_precision,
                        c.numeric_scale,
                        CASE WHEN pk.column_name IS NOT NULL
                             THEN true ELSE false END as is_primary_key,
                        col_description(
                            (quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass,
                            c.ordinal_position
                        ) as comment
                    FROM information_schema.columns c
                    LEFT JOIN (
                        SELECT ku.table_name, ku.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage ku
                            ON tc.constraint_name = ku.constraint_name
                            AND tc.table_schema = ku.table_schema
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                        AND tc.table_schema = %s
                    ) pk ON c.table_name = pk.table_name AND c.column_name = pk.column_name
                    WHERE c.table_schema = %s
                    ORDER BY c.table_name, c.ordinal_position
                    """,
                    (schema, schema),
                )

                # Group columns by table
                for row in cur.fetchall():
                    table_name = row["table_name"]
                    if table_name in table_map:
                        table_map[table_name].columns.append(
                            ColumnInfo(
                                name=row["column_name"],
                                data_type=row["data_type"],
                                nullable=row["is_nullable"],
                                primary_key=row["is_primary_key"],
                                comment=row["comment"] or "",
                                default_value=row["column_default"],
                                max_length=row["character_maximum_length"],
                                precision=row["numeric_precision"],
                                scale=row["numeric_scale"],
                            )
                        )

            return tables

        except psycopg2.Error as e:
            logger.error(f"Failed to get tables with columns for schema {schema}: {e}")
            # Fall back to individual queries
            return super().get_tables_with_columns(schema)

    def fetch_data(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        batch_size: int = 10000,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Fetch data from PostgreSQL in batches."""
        try:
            cursor_name = f"fetch_cursor_{id(self)}"

            with self._connection.cursor(
                name=cursor_name, cursor_factory=RealDictCursor
            ) as cur:
                cur.itersize = batch_size

                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)

                while True:
                    rows = cur.fetchmany(batch_size)
                    if not rows:
                        break
                    yield [dict(row) for row in rows]

        except psycopg2.Error as e:
            logger.error(f"Failed to fetch data: {e}")
            raise ConnectorException(f"Failed to fetch data: {str(e)}")

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Execute a query that doesn't return results."""
        try:
            with self._connection.cursor() as cur:
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)

                self._connection.commit()
                return cur.rowcount

        except psycopg2.Error as e:
            self._connection.rollback()
            logger.error(f"Failed to execute query: {e}")
            raise ConnectorException(f"Failed to execute query: {str(e)}")

    def get_row_count(self, schema: str, table: str) -> int:
        """Get approximate row count for a table."""
        try:
            with self._connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT reltuples::bigint
                    FROM pg_class
                    WHERE oid = (quote_ident(%s) || '.' || quote_ident(%s))::regclass
                    """,
                    (schema, table),
                )

                row = cur.fetchone()
                if row and row[0] > 0:
                    return row[0]

                return super().get_row_count(schema, table)

        except Exception as e:
            logger.warning(f"Failed to get row count estimate: {e}")
            return super().get_row_count(schema, table)
