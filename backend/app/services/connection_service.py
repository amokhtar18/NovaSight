"""
NovaSight Connection Service
============================

Data source connection management.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from app.extensions import db
from app.models.connection import DataConnection, DatabaseType, ConnectionStatus
from app.services.credential_service import CredentialService
import logging

logger = logging.getLogger(__name__)


class ConnectionService:
    """Service for data connection management."""
    
    def __init__(self, tenant_id: str):
        """
        Initialize connection service for a specific tenant.
        
        Args:
            tenant_id: Tenant UUID
        """
        self.tenant_id = tenant_id
        self.credential_service = CredentialService(tenant_id)
    
    def list_connections(
        self,
        page: int = 1,
        per_page: int = 20,
        db_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List data connections in the tenant.
        
        Args:
            page: Page number
            per_page: Items per page
            db_type: Filter by database type
            status: Filter by status
        
        Returns:
            Paginated list of connections
        """
        query = DataConnection.query.filter(DataConnection.tenant_id == self.tenant_id)
        
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
            "connections": [c.to_dict(mask_password=True) for c in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            }
        }
    
    def get_connection(self, connection_id: str) -> Optional[DataConnection]:
        """
        Get connection by ID within tenant.
        
        Args:
            connection_id: Connection UUID
        
        Returns:
            DataConnection object or None
        """
        return DataConnection.query.filter(
            DataConnection.id == connection_id,
            DataConnection.tenant_id == self.tenant_id
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
        extra_params: Optional[Dict[str, Any]] = None,
        created_by: str = None
    ) -> DataConnection:
        """
        Create a new data connection.
        
        Args:
            name: Connection display name
            db_type: Database type
            host: Database host
            port: Database port
            database: Database name
            username: Connection username
            password: Connection password
            ssl_mode: SSL mode
            extra_params: Additional parameters
            created_by: User ID who created the connection
        
        Returns:
            Created DataConnection object
        """
        # Check for existing connection with same name
        existing = DataConnection.query.filter(
            DataConnection.tenant_id == self.tenant_id,
            DataConnection.name == name
        ).first()
        
        if existing:
            raise ValueError(f"Connection with name '{name}' already exists")
        
        # Parse database type
        try:
            db_type_enum = DatabaseType(db_type)
        except ValueError:
            raise ValueError(f"Invalid database type: {db_type}")
        
        # Encrypt password
        encrypted_password = self.credential_service.encrypt(password)
        
        connection = DataConnection(
            tenant_id=self.tenant_id,
            name=name,
            db_type=db_type_enum,
            host=host,
            port=port,
            database=database,
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
        **kwargs
    ) -> Optional[DataConnection]:
        """
        Update connection details.
        
        Args:
            connection_id: Connection UUID
            **kwargs: Fields to update
        
        Returns:
            Updated DataConnection object or None
        """
        connection = self.get_connection(connection_id)
        if not connection:
            return None
        
        # Handle password update separately
        if "password" in kwargs:
            password = kwargs.pop("password")
            if password:  # Only update if provided
                connection.password_encrypted = self.credential_service.encrypt(password)
        
        # Update allowed fields
        allowed_fields = [
            "name", "host", "port", "database", "schema_name",
            "username", "ssl_mode", "extra_params", "description"
        ]
        
        for field, value in kwargs.items():
            if field not in allowed_fields:
                continue
            setattr(connection, field, value)
        
        db.session.commit()
        logger.info(f"Updated connection: {connection.name}")
        
        return connection
    
    def delete_connection(self, connection_id: str) -> bool:
        """
        Delete a data connection.
        
        Args:
            connection_id: Connection UUID
        
        Returns:
            True if successful
        """
        connection = self.get_connection(connection_id)
        if not connection:
            return False
        
        # TODO: Check for dependent ingestion jobs
        
        db.session.delete(connection)
        db.session.commit()
        
        logger.info(f"Deleted connection: {connection.name}")
        
        return True
    
    def test_connection(self, connection_id: str) -> Dict[str, Any]:
        """
        Test an existing connection.
        
        Args:
            connection_id: Connection UUID
        
        Returns:
            Test result with success status and details
        """
        connection = self.get_connection(connection_id)
        if not connection:
            return {"success": False, "error": "Connection not found"}
        
        # Decrypt password
        password = self.credential_service.decrypt(connection.password_encrypted)
        
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
        ssl_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Test connection parameters without saving.
        
        Args:
            db_type: Database type
            host: Database host
            port: Database port
            database: Database name
            username: Connection username
            password: Connection password
            ssl_mode: SSL mode
        
        Returns:
            Test result with success status and details
        """
        try:
            # Build connection string based on type
            if db_type == "postgresql":
                import psycopg2
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password,
                    sslmode=ssl_mode or "prefer",
                    connect_timeout=10
                )
                cursor = conn.cursor()
                cursor.execute("SELECT version()")
                version = cursor.fetchone()[0]
                conn.close()
                
                return {
                    "success": True,
                    "details": {
                        "version": version,
                        "database": database,
                    }
                }
            
            # Add other database types here
            else:
                return {
                    "success": False,
                    "error": f"Database type '{db_type}' not yet supported for testing"
                }
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "details": {"exception_type": type(e).__name__}
            }
    
    def get_schema(
        self,
        connection_id: str,
        schema_name: Optional[str] = None,
        include_columns: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get database schema information.
        
        Args:
            connection_id: Connection UUID
            schema_name: Filter by schema name
            include_columns: Include column details
        
        Returns:
            Schema information or None
        """
        connection = self.get_connection(connection_id)
        if not connection:
            return None
        
        # TODO: Implement schema introspection for each database type
        # This is a placeholder that would use SQLAlchemy inspection
        
        return {
            "schemas": [],
            "tables": [],
        }
