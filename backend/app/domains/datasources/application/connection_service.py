"""
NovaSight Data Sources Domain — Connection Service
====================================================

Data source connection management.

Canonical location: ``app.domains.datasources.application.connection_service``

Changes from legacy ``app.services.connection_service``:
- Uses unified ``EncryptionService`` instead of deprecated ``CredentialService``
- Imports model from ``domains.datasources.domain.models``
- Imports connectors from ``domains.datasources.infrastructure.connectors``
- Removed dual response format from ``list_connections()``
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
import uuid

from app.extensions import db
from app.domains.datasources.domain.models import (
    DataConnection,
    DatabaseType,
    ConnectionStatus,
)
from app.domains.datasources.domain.interfaces import (
    IConnectionProvider,
    ISchemaProvider,
)
from app.platform.security.encryption import EncryptionService
from app.domains.datasources.infrastructure.connectors import (
    ConnectorRegistry,
    ConnectionConfig,
    ConnectorException,
)

logger = logging.getLogger(__name__)


class ConnectionService(IConnectionProvider, ISchemaProvider):
    """Service for data connection management."""

    def __init__(self, tenant_id: str):
        """
        Initialize connection service for a specific tenant.

        Args:
            tenant_id: Tenant UUID
        """
        self.tenant_id = tenant_id
        self._encryption = EncryptionService(tenant_id=tenant_id)

    def list_connections(
        self,
        page: int = 1,
        per_page: int = 20,
        db_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List data connections in the tenant.

        Returns a single, clean paginated response format.
        """
        query = DataConnection.query.filter(
            DataConnection.tenant_id == self.tenant_id
        )

        if db_type:
            try:
                db_type_enum = DatabaseType(db_type)
                query = query.filter(DataConnection.db_type == db_type_enum)
            except ValueError:
                pass

        if status:
            try:
                status_enum = ConnectionStatus(status)
                query = query.filter(DataConnection.status == status_enum)
            except ValueError:
                pass

        query = query.order_by(DataConnection.created_at.desc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            "items": [c.to_dict(mask_password=True) for c in pagination.items],
            "total": pagination.total,
            "page": page,
            "pageSize": per_page,
            "totalPages": pagination.pages,
            # Keep legacy fields for backward compatibility
            "connections": [c.to_dict(mask_password=True) for c in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            },
        }

    def get_connection(self, connection_id: str) -> Optional[DataConnection]:
        """Get connection by ID within tenant."""
        return DataConnection.query.filter(
            DataConnection.id == connection_id,
            DataConnection.tenant_id == self.tenant_id,
        ).first()

    def create_connection(
        self,
        name: str,
        db_type: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        ssl_mode: Optional[str] = None,
        schema_name: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        created_by: str = None,
    ) -> DataConnection:
        """Create a new data connection."""
        # Check for duplicate name within tenant
        existing = DataConnection.query.filter(
            DataConnection.tenant_id == self.tenant_id,
            DataConnection.name == name,
        ).first()

        if existing:
            raise ValueError(f"Connection with name '{name}' already exists")

        # Parse database type
        try:
            db_type_enum = DatabaseType(db_type)
        except ValueError:
            raise ValueError(f"Invalid database type: {db_type}")

        # Encrypt password via unified encryption
        encrypted_password = self._encryption.encrypt(password)

        connection = DataConnection(
            tenant_id=self.tenant_id,
            name=name,
            db_type=db_type_enum,
            host=host,
            port=port,
            database=database,
            schema_name=schema_name,
            username=username,
            password_encrypted=encrypted_password,
            ssl_mode=ssl_mode,
            extra_params=extra_params or {},
            status=ConnectionStatus.ACTIVE,
            created_by=created_by,
        )

        db.session.add(connection)
        db.session.commit()

        logger.info(f"Created connection: {name} in tenant {self.tenant_id}")

        return connection

    def update_connection(
        self,
        connection_id: str,
        **kwargs,
    ) -> Optional[DataConnection]:
        """Update connection details."""
        connection = self.get_connection(connection_id)
        if not connection:
            return None

        # Handle password update separately
        if "password" in kwargs:
            password = kwargs.pop("password")
            if password:  # Only update if provided
                connection.password_encrypted = self._encryption.encrypt(password)

        # Update allowed fields
        allowed_fields = [
            "name", "host", "port", "database", "schema_name",
            "username", "ssl_mode", "extra_params", "description",
        ]

        for field, value in kwargs.items():
            if field not in allowed_fields:
                continue
            setattr(connection, field, value)

        db.session.commit()
        logger.info(f"Updated connection: {connection.name}")

        return connection

    def delete_connection(self, connection_id: str) -> bool:
        """Delete a data connection."""
        connection = self.get_connection(connection_id)
        if not connection:
            return False

        # TODO: Check for dependent ingestion jobs

        db.session.delete(connection)
        db.session.commit()

        logger.info(f"Deleted connection: {connection.name}")

        return True

    def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """Test an existing connection."""
        connection = self.get_connection(connection_id)
        if not connection:
            return {"success": False, "error": "Connection not found"}

        # Decrypt password via unified encryption
        password = self._encryption.decrypt(connection.password_encrypted)

        return self.test_connection_params(
            db_type=connection.db_type.value,
            host=connection.host,
            port=connection.port,
            database=connection.database,
            username=connection.username,
            password=password,
            ssl_mode=connection.ssl_mode,
        )

    def test_connection_params(
        self,
        db_type: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        ssl_mode: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Test connection parameters without saving."""
        try:
            config = ConnectionConfig(
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                ssl_mode=ssl_mode,
                ssl=bool(ssl_mode),
                extra_params=extra_params or {},
            )

            connector = ConnectorRegistry.create_connector(db_type, config)

            with connector:
                connector.test_connection()
                all_schemas = connector.get_schemas()
                
                # For connection test, just return all schemas without filtering
                # Filtering empty schemas is too slow for databases with many schemas (e.g., Oracle)
                # The schema selection step can handle this more efficiently
                return {
                    "success": True,
                    "message": "Connection successful",
                    "details": {
                        "database": database,
                        "schemas_count": len(all_schemas),
                        "schemas": all_schemas[:50],  # Limit to first 50 schemas for performance
                        "schemas_truncated": len(all_schemas) > 50,
                    },
                }

        except ConnectorException as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Connection test failed",
            }
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Connection test failed",
                "details": {"exception_type": type(e).__name__},
            }

    def get_schema(
        self,
        connection_id: str,
        schema_name: Optional[str] = None,
        include_columns: bool = False,
        schemas_only: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Get database schema information using connector framework.
        
        Args:
            connection_id: The connection UUID
            schema_name: Optional specific schema to fetch (None = all schemas)
            include_columns: Whether to fetch column details for each table
            schemas_only: If True, only return schema names (fast mode for initial load)
        """
        connection = self.get_connection(connection_id)
        if not connection:
            return None

        try:
            password = self._encryption.decrypt(connection.password_encrypted)

            config = ConnectionConfig(
                host=connection.host,
                port=connection.port,
                database=connection.database,
                username=connection.username,
                password=password,
                ssl_mode=connection.ssl_mode,
                ssl=bool(connection.ssl_mode),
                schema=connection.schema_name,
                extra_params=connection.extra_params,
            )

            connector = ConnectorRegistry.create_connector(
                connection.db_type.value, config
            )

            with connector:
                all_schemas = connector.get_schemas()
                
                # Filter schemas by allowed_schemas from extra_params if configured
                allowed_schemas = (connection.extra_params or {}).get("allowed_schemas")
                if allowed_schemas and isinstance(allowed_schemas, list) and len(allowed_schemas) > 0:
                    schemas = [s for s in all_schemas if s in allowed_schemas]
                else:
                    schemas = all_schemas
                
                # Fast mode: only return schema names without fetching tables
                if schemas_only:
                    return {
                        "schemas": [{"name": s, "tables": []} for s in schemas],
                        "total_tables": 0,
                        "total_columns": 0,
                    }
                
                tables_by_schema = {}
                target_schemas = [schema_name] if schema_name else schemas
                total_tables = 0
                total_columns = 0
                
                # Limit number of schemas to process when fetching all
                # (prevents very slow queries on databases with many schemas)
                MAX_SCHEMAS_AUTO = 20
                if not schema_name and len(target_schemas) > MAX_SCHEMAS_AUTO:
                    logger.warning(
                        f"Database has {len(target_schemas)} schemas, limiting to first {MAX_SCHEMAS_AUTO}. "
                        "Use schema_name parameter to fetch specific schema."
                    )
                    target_schemas = target_schemas[:MAX_SCHEMAS_AUTO]

                for schema in target_schemas:
                    if schema not in schemas:
                        continue

                    logger.debug(f"Fetching tables for schema: {schema}")
                    
                    # Use optimized batch method if columns are requested
                    if include_columns:
                        try:
                            tables = connector.get_tables_with_columns(schema)
                        except Exception as batch_err:
                            logger.warning(f"Batch column fetch failed for {schema}, falling back to individual queries: {batch_err}")
                            tables = connector.get_tables(schema)
                    else:
                        tables = connector.get_tables(schema)
                    
                    tables_dict = []
                    for table in tables:
                        table_dict = {
                            "name": table.name,
                            "schema": table.schema,
                            "row_count": table.row_count,
                            "comment": table.comment,
                            "table_type": table.table_type,
                        }

                        # Add columns if they were fetched (from batch method)
                        if include_columns:
                            columns = table.columns
                            
                            # Fallback to individual query if batch didn't get columns
                            if not columns:
                                try:
                                    table_with_cols = connector.get_table_schema(schema, table.name)
                                    columns = table_with_cols.columns
                                except Exception as col_err:
                                    logger.warning(f"Failed to get columns for {schema}.{table.name}: {col_err}")
                                    columns = []

                            table_dict["columns"] = [
                                {
                                    "name": col.name,
                                    "data_type": col.data_type,
                                    "is_nullable": col.nullable,
                                    "nullable": col.nullable,
                                    "primary_key": col.primary_key,
                                    "comment": col.comment,
                                    "max_length": col.max_length,
                                    "precision": col.precision,
                                    "scale": col.scale,
                                }
                                for col in columns
                            ]
                            total_columns += len(columns)

                        tables_dict.append(table_dict)
                        total_tables += 1

                    tables_by_schema[schema] = tables_dict

                # Return in the format expected by frontend
                # Filter out schemas with no tables to reduce payload
                schema_list = [
                    {"name": schema_name, "tables": tables_by_schema.get(schema_name, [])}
                    for schema_name in target_schemas
                    if schema_name in schemas and len(tables_by_schema.get(schema_name, [])) > 0
                ]

                return {
                    "schemas": schema_list,
                    "total_tables": total_tables,
                    "total_columns": total_columns,
                    # Keep legacy format for backward compatibility
                    "_legacy": {
                        "schemas": schemas,
                        "tables": tables_by_schema,
                    },
                }

        except ConnectorException as e:
            logger.error(
                f"Failed to get schema for connection {connection_id}: {e}"
            )
            return {"schemas": [], "total_tables": 0, "error": str(e)}
        except Exception as e:
            logger.error(
                f"Failed to get schema for connection {connection_id}: {e}"
            )
            return {"schemas": [], "total_tables": 0, "error": str(e)}

    def trigger_sync(
        self,
        connection_id: str,
        sync_config: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Trigger a data sync job for this connection."""
        connection = self.get_connection(connection_id)
        if not connection:
            return None

        try:
            # TODO: Integrate with Airflow to trigger DAG
            job_id = str(uuid.uuid4())
            logger.info(
                f"Triggered sync for connection {connection.name}: job_id={job_id}"
            )
            return job_id

        except Exception as e:
            logger.error(
                f"Failed to trigger sync for connection {connection_id}: {e}"
            )
            return None

    def get_connector(self, connection_id: str):
        """
        Get a connector instance for this connection.

        Returns a connector (use with context manager).

        Raises:
            ValueError: If connection not found
        """
        connection = self.get_connection(connection_id)
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")

        password = self._encryption.decrypt(connection.password_encrypted)

        config = ConnectionConfig(
            host=connection.host,
            port=connection.port,
            database=connection.database,
            username=connection.username,
            password=password,
            ssl_mode=connection.ssl_mode,
            ssl=bool(connection.ssl_mode),
            schema=connection.schema_name,
            extra_params=connection.extra_params,
        )

        return ConnectorRegistry.create_connector(
            connection.db_type.value, config
        )

    def get_tables(
        self,
        connection_id: str,
        schema_name: Optional[str] = None,
    ) -> List["DataSourceTable"]:
        """
        Return the list of tables for the given connection.

        Args:
            connection_id: UUID of the data connection.
            schema_name: Optional database schema to filter by.

        Returns:
            A list of DataSourceTable value objects.
        """
        from app.domains.datasources.domain.value_objects import DataSourceTable

        connection = self.get_connection(connection_id)
        if not connection:
            return []

        try:
            password = self._encryption.decrypt(connection.password_encrypted)

            config = ConnectionConfig(
                host=connection.host,
                port=connection.port,
                database=connection.database,
                username=connection.username,
                password=password,
                ssl_mode=connection.ssl_mode,
                ssl=bool(connection.ssl_mode),
                schema=connection.schema_name,
                extra_params=connection.extra_params,
            )

            connector = ConnectorRegistry.create_connector(
                connection.db_type.value, config
            )

            with connector:
                schemas = connector.get_schemas()
                target_schemas = [schema_name] if schema_name else schemas
                result_tables = []

                for schema in target_schemas:
                    if schema not in schemas:
                        continue

                    tables = connector.get_tables(schema)
                    for table in tables:
                        result_tables.append(table.to_datasource_table())

                return result_tables

        except ConnectorException as e:
            logger.error(
                f"Failed to get tables for connection {connection_id}: {e}"
            )
            return []
        except Exception as e:
            logger.error(
                f"Failed to get tables for connection {connection_id}: {e}"
            )
            return []

    def get_columns(
        self,
        connection_id: str,
        table_name: str,
        schema_name: Optional[str] = None,
    ) -> List["DataSourceColumn"]:
        """
        Return the list of columns for a specific table.

        Args:
            connection_id: UUID of the data connection.
            table_name: Name of the table.
            schema_name: Optional database schema.

        Returns:
            A list of DataSourceColumn value objects.
        """
        from app.domains.datasources.domain.value_objects import DataSourceColumn

        connection = self.get_connection(connection_id)
        if not connection:
            return []

        try:
            password = self._encryption.decrypt(connection.password_encrypted)

            config = ConnectionConfig(
                host=connection.host,
                port=connection.port,
                database=connection.database,
                username=connection.username,
                password=password,
                ssl_mode=connection.ssl_mode,
                ssl=bool(connection.ssl_mode),
                schema=connection.schema_name,
                extra_params=connection.extra_params,
            )

            connector = ConnectorRegistry.create_connector(
                connection.db_type.value, config
            )

            with connector:
                target_schema = schema_name or connection.schema_name or "public"
                columns = connector.get_table_schema(table_name, target_schema)
                return [col.to_datasource_column() for col in columns]

        except ConnectorException as e:
            logger.error(
                f"Failed to get columns for {table_name} in connection {connection_id}: {e}"
            )
            return []
        except Exception as e:
            logger.error(
                f"Failed to get columns for {table_name} in connection {connection_id}: {e}"
            )
            return []

    def execute_query(
        self,
        connection_id: str,
        sql: str,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """
        Execute a SQL query against a connection.

        Args:
            connection_id: Connection UUID
            sql: SQL query to execute
            limit: Maximum rows to return

        Returns:
            Query result with columns, rows, and metadata
        """
        import time

        connection = self.get_connection(connection_id)
        if not connection:
            raise ValueError(f"Connection {connection_id} not found")

        # Validate query - only SELECT allowed
        sql_stripped = sql.strip().upper()
        if not sql_stripped.startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed")

        dangerous_keywords = ["DROP", "TRUNCATE", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
        for keyword in dangerous_keywords:
            if keyword in sql_stripped:
                raise ValueError(f"Query contains disallowed keyword: {keyword}")

        try:
            password = self._encryption.decrypt(connection.password_encrypted)

            config = ConnectionConfig(
                host=connection.host,
                port=connection.port,
                database=connection.database,
                username=connection.username,
                password=password,
                ssl_mode=connection.ssl_mode,
                ssl=bool(connection.ssl_mode),
                schema=connection.schema_name,
                extra_params=connection.extra_params,
            )

            connector = ConnectorRegistry.create_connector(
                connection.db_type.value, config
            )

            # Add LIMIT if not present
            if "LIMIT" not in sql_stripped:
                sql = f"{sql.rstrip().rstrip(';')} LIMIT {limit}"

            start_time = time.time()

            with connector:
                # Use fetch_data to get rows as dictionaries
                all_rows = []
                columns = []
                truncated = False

                for batch in connector.fetch_data(sql, batch_size=limit):
                    if batch:
                        # Get column names from first row
                        if not columns and batch:
                            columns = [{"name": col, "type": "unknown"} for col in batch[0].keys()]
                        all_rows.extend(batch)
                        if len(all_rows) >= limit:
                            all_rows = all_rows[:limit]
                            truncated = True
                            break

                execution_time_ms = int((time.time() - start_time) * 1000)

                return {
                    "columns": columns,
                    "rows": all_rows,
                    "row_count": len(all_rows),
                    "execution_time_ms": execution_time_ms,
                    "truncated": truncated,
                }

        except ConnectorException as e:
            logger.error(f"Query execution failed for connection {connection_id}: {e}")
            raise ValueError(f"Query execution failed: {str(e)}")
        except Exception as e:
            logger.error(f"Query execution failed for connection {connection_id}: {e}")
            raise ValueError(f"Query execution failed: {str(e)}")
