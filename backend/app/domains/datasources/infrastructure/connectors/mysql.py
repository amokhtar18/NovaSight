"""
NovaSight Data Sources — MySQL Connector
==========================================

MySQL / MariaDB database connector implementation.

Canonical location: ``app.domains.datasources.infrastructure.connectors.mysql``
"""

import mysql.connector
from mysql.connector import Error as MySQLError
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


class MySQLConnector(BaseConnector):
    """MySQL / MariaDB database connector."""

    connector_type = "mysql"
    supported_auth_methods = ["password", "certificate"]
    supports_ssl = True
    default_port = 3306

    def connect(self) -> None:
        """Establish connection to MySQL database."""
        try:
            connection_params = {
                "host": self.config.host,
                "port": self.config.port,
                "database": self.config.database,
                "user": self.config.username,
                "password": self.config.password,
                "charset": "utf8mb4",
                "collation": "utf8mb4_unicode_ci",
                "autocommit": False,
                "connection_timeout": 10,
                **self.config.driver_extra_params,
            }

            if self.config.ssl:
                connection_params["ssl_disabled"] = False
                connection_params["ssl_verify_cert"] = True
            else:
                connection_params["ssl_disabled"] = True

            self._connection = mysql.connector.connect(**connection_params)
            self._is_connected = True
            logger.info(
                f"Connected to MySQL: "
                f"{self.config.host}:{self.config.port}/{self.config.database}"
            )

        except MySQLError as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            raise ConnectorException(f"MySQL connection failed: {str(e)}")

    def disconnect(self) -> None:
        """Close MySQL connection."""
        if self._connection:
            try:
                if self._connection.is_connected():
                    self._connection.close()
                self._is_connected = False
                logger.info("Disconnected from MySQL")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._connection = None

    def test_connection(self) -> bool:
        """Test MySQL connection."""
        try:
            if not self._connection or not self._connection.is_connected():
                self.connect()

            cursor = self._connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            cursor.close()

            logger.info(f"MySQL connection test successful: {version}")
            return True

        except Exception as e:
            logger.error(f"MySQL connection test failed: {e}")
            raise ConnectionTestException(f"Connection test failed: {str(e)}")

    def get_schemas(self) -> List[str]:
        """List all databases (schemas) in MySQL."""
        try:
            cursor = self._connection.cursor()
            cursor.execute("""
                SELECT SCHEMA_NAME
                FROM information_schema.SCHEMATA
                WHERE SCHEMA_NAME NOT IN (
                    'information_schema', 'mysql', 'performance_schema', 'sys'
                )
                ORDER BY SCHEMA_NAME
            """)
            schemas = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return schemas

        except MySQLError as e:
            logger.error(f"Failed to get schemas: {e}")
            raise ConnectorException(f"Failed to get schemas: {str(e)}")

    def get_tables(self, schema: str) -> List[TableInfo]:
        """List all tables in a MySQL schema."""
        try:
            cursor = self._connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT
                    TABLE_NAME as table_name,
                    TABLE_SCHEMA as table_schema,
                    TABLE_TYPE as table_type,
                    TABLE_COMMENT as comment,
                    TABLE_ROWS as row_count
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                AND TABLE_TYPE IN ('BASE TABLE', 'VIEW')
                ORDER BY TABLE_NAME
                """,
                (schema,),
            )

            tables = []
            for row in cursor.fetchall():
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

            cursor.close()
            return tables

        except MySQLError as e:
            logger.error(f"Failed to get tables for schema {schema}: {e}")
            raise ConnectorException(f"Failed to get tables: {str(e)}")

    def get_table_schema(self, schema: str, table: str) -> TableInfo:
        """Get detailed schema for a MySQL table."""
        try:
            cursor = self._connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT
                    TABLE_TYPE as table_type,
                    TABLE_COMMENT as comment,
                    TABLE_ROWS as row_count
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """,
                (schema, table),
            )

            table_row = cursor.fetchone()
            if not table_row:
                cursor.close()
                raise ConnectorException(f"Table {schema}.{table} not found")

            columns = self._get_columns(schema, table)

            cursor.close()

            return TableInfo(
                name=table,
                schema=schema,
                columns=columns,
                row_count=int(table_row["row_count"] or 0),
                comment=table_row["comment"] or "",
                table_type=table_row["table_type"],
            )

        except MySQLError as e:
            logger.error(f"Failed to get schema for table {schema}.{table}: {e}")
            raise ConnectorException(f"Failed to get table schema: {str(e)}")

    def _get_columns(self, schema: str, table: str) -> List[ColumnInfo]:
        """Get column information for a table."""
        cursor = self._connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                COLUMN_NAME as column_name,
                DATA_TYPE as data_type,
                IS_NULLABLE = 'YES' as is_nullable,
                COLUMN_DEFAULT as column_default,
                CHARACTER_MAXIMUM_LENGTH as max_length,
                NUMERIC_PRECISION as numeric_precision,
                NUMERIC_SCALE as numeric_scale,
                COLUMN_KEY = 'PRI' as is_primary_key,
                COLUMN_COMMENT as comment
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            (schema, table),
        )

        columns = []
        for row in cursor.fetchall():
            columns.append(
                ColumnInfo(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    nullable=bool(row["is_nullable"]),
                    primary_key=bool(row["is_primary_key"]),
                    comment=row["comment"] or "",
                    default_value=row["column_default"],
                    max_length=row["max_length"],
                    precision=row["numeric_precision"],
                    scale=row["numeric_scale"],
                )
            )

        cursor.close()
        return columns

    def get_tables_with_columns(self, schema: str) -> List[TableInfo]:
        """
        Get all tables with columns in optimized batch queries for MySQL.
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
            cursor = self._connection.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT
                    TABLE_NAME as table_name,
                    COLUMN_NAME as column_name,
                    DATA_TYPE as data_type,
                    IS_NULLABLE = 'YES' as is_nullable,
                    COLUMN_DEFAULT as column_default,
                    CHARACTER_MAXIMUM_LENGTH as max_length,
                    NUMERIC_PRECISION as numeric_precision,
                    NUMERIC_SCALE as numeric_scale,
                    COLUMN_KEY = 'PRI' as is_primary_key,
                    COLUMN_COMMENT as comment
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME, ORDINAL_POSITION
                """,
                (schema,),
            )

            # Group columns by table
            for row in cursor.fetchall():
                table_name = row["table_name"]
                if table_name in table_map:
                    table_map[table_name].columns.append(
                        ColumnInfo(
                            name=row["column_name"],
                            data_type=row["data_type"],
                            nullable=bool(row["is_nullable"]),
                            primary_key=bool(row["is_primary_key"]),
                            comment=row["comment"] or "",
                            default_value=row["column_default"],
                            max_length=row["max_length"],
                            precision=row["numeric_precision"],
                            scale=row["numeric_scale"],
                        )
                    )

            cursor.close()
            return tables

        except MySQLError as e:
            logger.error(f"Failed to get tables with columns for schema {schema}: {e}")
            # Fall back to individual queries
            return super().get_tables_with_columns(schema)

    def fetch_data(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        batch_size: int = 10000,
    ) -> Iterator[List[Dict[str, Any]]]:
        """Fetch data from MySQL in batches."""
        try:
            cursor = self._connection.cursor(dictionary=True, buffered=False)

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break
                yield rows

            cursor.close()

        except MySQLError as e:
            logger.error(f"Failed to fetch data: {e}")
            raise ConnectorException(f"Failed to fetch data: {str(e)}")

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Execute a query that doesn't return results."""
        try:
            cursor = self._connection.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            self._connection.commit()
            rowcount = cursor.rowcount
            cursor.close()

            return rowcount

        except MySQLError as e:
            self._connection.rollback()
            logger.error(f"Failed to execute query: {e}")
            raise ConnectorException(f"Failed to execute query: {str(e)}")

    def get_row_count(self, schema: str, table: str) -> int:
        """Get approximate row count for a table."""
        try:
            cursor = self._connection.cursor()

            cursor.execute(
                """
                SELECT TABLE_ROWS
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """,
                (schema, table),
            )

            row = cursor.fetchone()
            cursor.close()

            if row and row[0] is not None:
                return int(row[0])

            return super().get_row_count(schema, table)

        except Exception as e:
            logger.warning(f"Failed to get row count estimate: {e}")
            return super().get_row_count(schema, table)
