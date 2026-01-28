"""
NovaSight PySpark App Service
=============================

Business logic for PySpark application configuration and code generation.
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from uuid import UUID

from app.extensions import db
from app.models.pyspark_app import (
    PySparkApp,
    PySparkAppStatus,
    SourceType,
    WriteMode,
    SCDType,
    CDCType,
)
from app.models.connection import DataConnection
from app.services.connection_service import ConnectionService
from app.services.template_engine import TemplateEngine
from app.errors import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


class PySparkAppService:
    """
    Service for PySpark app configuration and code generation.
    
    All generated code comes from pre-approved Jinja2 templates,
    adhering to ADR-002: Template Engine Rule.
    """
    
    # Mapping of SCD type to template
    TEMPLATE_MAPPING = {
        SCDType.NONE: "pyspark/extract_job.py.j2",
        SCDType.TYPE1: "pyspark/scd_type1.py.j2",
        SCDType.TYPE2: "pyspark/scd_type2.py.j2",
    }
    
    def __init__(self, tenant_id: str):
        """
        Initialize service for a specific tenant.
        
        Args:
            tenant_id: Tenant UUID
        """
        self.tenant_id = tenant_id
        self.connection_service = ConnectionService(tenant_id)
        self.template_engine = TemplateEngine()
    
    def list_apps(
        self,
        page: int = 1,
        per_page: int = 20,
        status: Optional[str] = None,
        connection_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List PySpark apps for the tenant.
        
        Args:
            page: Page number
            per_page: Items per page
            status: Filter by status
            connection_id: Filter by connection
            search: Search by name/description
            
        Returns:
            Paginated list of apps
        """
        query = PySparkApp.query.filter(PySparkApp.tenant_id == self.tenant_id)
        
        # Apply filters
        if status:
            try:
                status_enum = PySparkAppStatus(status)
                query = query.filter(PySparkApp.status == status_enum)
            except ValueError:
                pass
        
        if connection_id:
            query = query.filter(PySparkApp.connection_id == connection_id)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                db.or_(
                    PySparkApp.name.ilike(search_pattern),
                    PySparkApp.description.ilike(search_pattern),
                )
            )
        
        query = query.order_by(PySparkApp.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            "apps": [app.to_dict() for app in pagination.items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev,
            }
        }
    
    def get_app(self, app_id: str, include_code: bool = False) -> Optional[PySparkApp]:
        """
        Get PySpark app by ID.
        
        Args:
            app_id: App UUID
            include_code: Include generated code
            
        Returns:
            PySparkApp or None
        """
        return PySparkApp.query.filter(
            PySparkApp.id == app_id,
            PySparkApp.tenant_id == self.tenant_id
        ).first()
    
    def create_app(
        self,
        name: str,
        connection_id: str,
        created_by: str,
        description: Optional[str] = None,
        source_type: str = "table",
        source_schema: Optional[str] = None,
        source_table: Optional[str] = None,
        source_query: Optional[str] = None,
        columns_config: Optional[List[Dict]] = None,
        primary_key_columns: Optional[List[str]] = None,
        cdc_type: str = "none",
        cdc_column: Optional[str] = None,
        partition_columns: Optional[List[str]] = None,
        scd_type: str = "none",
        write_mode: str = "append",
        target_database: Optional[str] = None,
        target_table: Optional[str] = None,
        target_engine: str = "MergeTree",
        options: Optional[Dict] = None,
    ) -> PySparkApp:
        """
        Create a new PySpark app configuration.
        
        Args:
            name: App name
            connection_id: Source connection UUID
            created_by: User UUID who creates the app
            ... (other parameters)
            
        Returns:
            Created PySparkApp
        """
        # Validate connection exists and belongs to tenant
        connection = self.connection_service.get_connection(connection_id)
        if not connection:
            raise NotFoundError(f"Connection {connection_id} not found")
        
        # Check for duplicate name
        existing = PySparkApp.query.filter(
            PySparkApp.tenant_id == self.tenant_id,
            PySparkApp.name == name
        ).first()
        
        if existing:
            raise ValidationError(f"PySpark app with name '{name}' already exists")
        
        # Parse enums
        try:
            source_type_enum = SourceType(source_type)
        except ValueError:
            raise ValidationError(f"Invalid source_type: {source_type}")
        
        try:
            cdc_type_enum = CDCType(cdc_type)
        except ValueError:
            raise ValidationError(f"Invalid cdc_type: {cdc_type}")
        
        try:
            scd_type_enum = SCDType(scd_type)
        except ValueError:
            raise ValidationError(f"Invalid scd_type: {scd_type}")
        
        try:
            write_mode_enum = WriteMode(write_mode)
        except ValueError:
            raise ValidationError(f"Invalid write_mode: {write_mode}")
        
        # Create app
        app = PySparkApp(
            tenant_id=self.tenant_id,
            connection_id=connection_id,
            name=name,
            description=description,
            status=PySparkAppStatus.DRAFT,
            source_type=source_type_enum,
            source_schema=source_schema,
            source_table=source_table,
            source_query=source_query,
            columns_config=columns_config or [],
            primary_key_columns=primary_key_columns or [],
            cdc_type=cdc_type_enum,
            cdc_column=cdc_column,
            partition_columns=partition_columns or [],
            scd_type=scd_type_enum,
            write_mode=write_mode_enum,
            target_database=target_database,
            target_table=target_table,
            target_engine=target_engine,
            options=options or {},
            created_by=created_by,
        )
        
        db.session.add(app)
        db.session.commit()
        
        logger.info(f"Created PySpark app: {app.id} - {name}")
        return app
    
    def update_app(
        self,
        app_id: str,
        **kwargs
    ) -> PySparkApp:
        """
        Update an existing PySpark app.
        
        Args:
            app_id: App UUID
            **kwargs: Fields to update
            
        Returns:
            Updated PySparkApp
        """
        app = self.get_app(app_id)
        if not app:
            raise NotFoundError(f"PySpark app {app_id} not found")
        
        # Handle enum conversions
        enum_mappings = {
            "source_type": SourceType,
            "cdc_type": CDCType,
            "scd_type": SCDType,
            "write_mode": WriteMode,
            "status": PySparkAppStatus,
        }
        
        for key, value in kwargs.items():
            if value is None:
                continue
            
            # Convert enum strings
            if key in enum_mappings and isinstance(value, str):
                try:
                    value = enum_mappings[key](value)
                except ValueError:
                    raise ValidationError(f"Invalid {key}: {value}")
            
            if hasattr(app, key):
                setattr(app, key, value)
        
        # Check for duplicate name if name is being updated
        if "name" in kwargs and kwargs["name"]:
            existing = PySparkApp.query.filter(
                PySparkApp.tenant_id == self.tenant_id,
                PySparkApp.name == kwargs["name"],
                PySparkApp.id != app_id
            ).first()
            
            if existing:
                raise ValidationError(f"PySpark app with name '{kwargs['name']}' already exists")
        
        # Clear generated code if configuration changed
        config_fields = [
            "source_type", "source_schema", "source_table", "source_query",
            "columns_config", "primary_key_columns", "cdc_type", "cdc_column",
            "partition_columns", "scd_type", "write_mode", "target_database",
            "target_table", "target_engine"
        ]
        
        if any(k in kwargs for k in config_fields):
            app.generated_code = None
            app.generated_at = None
        
        db.session.commit()
        
        logger.info(f"Updated PySpark app: {app_id}")
        return app
    
    def delete_app(self, app_id: str) -> bool:
        """
        Delete a PySpark app.
        
        Args:
            app_id: App UUID
            
        Returns:
            True if deleted
        """
        app = self.get_app(app_id)
        if not app:
            raise NotFoundError(f"PySpark app {app_id} not found")
        
        db.session.delete(app)
        db.session.commit()
        
        logger.info(f"Deleted PySpark app: {app_id}")
        return True
    
    def generate_code(self, app_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Generate PySpark code for an app configuration.
        
        Args:
            app_id: App UUID
            
        Returns:
            Tuple of (generated_code, metadata)
        """
        app = self.get_app(app_id)
        if not app:
            raise NotFoundError(f"PySpark app {app_id} not found")
        
        # Validate configuration
        errors = app.validate_config()
        if errors:
            raise ValidationError("Configuration validation failed", details={"errors": errors})
        
        # Get connection details (without password)
        connection = self.connection_service.get_connection(str(app.connection_id))
        if not connection:
            raise NotFoundError("Source connection not found")
        
        # Prepare template parameters
        params = self._build_template_params(app, connection)
        
        # Select template based on SCD type
        template_name = self.TEMPLATE_MAPPING.get(app.scd_type, "pyspark/extract_job.py.j2")
        
        # Generate code using template engine
        generated_code = self.template_engine.render(template_name, params)
        
        # Calculate hash
        code_hash = hashlib.sha256(generated_code.encode()).hexdigest()
        
        # Update app with generated code
        app.generated_code = generated_code
        app.generated_code_hash = code_hash
        app.generated_at = datetime.utcnow()
        app.template_version = self.template_engine.TEMPLATE_VERSION
        app.status = PySparkAppStatus.ACTIVE
        
        db.session.commit()
        
        metadata = {
            "template_name": template_name,
            "template_version": self.template_engine.TEMPLATE_VERSION,
            "parameters_hash": code_hash,
            "generated_at": app.generated_at.isoformat(),
        }
        
        logger.info(f"Generated code for PySpark app: {app_id}")
        return generated_code, metadata
    
    def preview_code(
        self,
        connection_id: str,
        source_type: str,
        source_schema: Optional[str] = None,
        source_table: Optional[str] = None,
        source_query: Optional[str] = None,
        columns_config: Optional[List[Dict]] = None,
        primary_key_columns: Optional[List[str]] = None,
        cdc_type: str = "none",
        cdc_column: Optional[str] = None,
        partition_columns: Optional[List[str]] = None,
        scd_type: str = "none",
        write_mode: str = "append",
        target_database: str = "",
        target_table: str = "",
        target_engine: str = "MergeTree",
        options: Optional[Dict] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Preview generated code without saving.
        
        Returns:
            Tuple of (generated_code, metadata)
        """
        # Validate connection
        connection = self.connection_service.get_connection(connection_id)
        if not connection:
            raise NotFoundError(f"Connection {connection_id} not found")
        
        # Parse enums
        try:
            source_type_enum = SourceType(source_type)
            cdc_type_enum = CDCType(cdc_type)
            scd_type_enum = SCDType(scd_type)
            write_mode_enum = WriteMode(write_mode)
        except ValueError as e:
            raise ValidationError(str(e))
        
        # Build params
        params = {
            "app_name": "preview_app",
            "connection": {
                "db_type": connection.db_type.value,
                "host": connection.host,
                "port": connection.port,
                "database": connection.database,
                "schema": connection.schema_name,
            },
            "source": {
                "type": source_type,
                "schema": source_schema,
                "table": source_table,
                "query": source_query,
            },
            "columns": [
                col for col in (columns_config or [])
                if col.get("include", True)
            ],
            "primary_keys": primary_key_columns or [],
            "cdc": {
                "type": cdc_type,
                "column": cdc_column,
            },
            "partitions": partition_columns or [],
            "scd_type": scd_type,
            "write_mode": write_mode,
            "target": {
                "database": target_database,
                "table": target_table,
                "engine": target_engine,
            },
            "options": options or {},
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        # Select template
        template_name = self.TEMPLATE_MAPPING.get(scd_type_enum, "pyspark/extract_job.py.j2")
        
        # Generate preview
        generated_code = self.template_engine.render(template_name, params)
        code_hash = hashlib.sha256(generated_code.encode()).hexdigest()
        
        metadata = {
            "template_name": template_name,
            "template_version": self.template_engine.TEMPLATE_VERSION,
            "parameters_hash": code_hash,
            "is_preview": True,
        }
        
        return generated_code, metadata
    
    def _build_template_params(
        self,
        app: PySparkApp,
        connection: DataConnection
    ) -> Dict[str, Any]:
        """
        Build template parameters from app configuration.
        
        Args:
            app: PySpark app model
            connection: Source connection
            
        Returns:
            Template parameters dictionary
        """
        return {
            "app_name": app.name,
            "app_id": str(app.id),
            "tenant_id": str(app.tenant_id),
            "connection": {
                "id": str(connection.id),
                "db_type": connection.db_type.value,
                "host": connection.host,
                "port": connection.port,
                "database": connection.database,
                "schema": connection.schema_name,
                "username": connection.username,
                # Password will be injected at runtime from secrets
            },
            "source": {
                "type": app.source_type.value,
                "schema": app.source_schema,
                "table": app.source_table,
                "query": app.source_query,
            },
            "columns": app.get_selected_columns(),
            "column_names": app.get_column_names(),
            "primary_keys": app.primary_key_columns or [],
            "cdc": {
                "type": app.cdc_type.value,
                "column": app.cdc_column,
            },
            "partitions": app.partition_columns or [],
            "scd_type": app.scd_type.value,
            "write_mode": app.write_mode.value,
            "target": {
                "database": app.target_database,
                "table": app.target_table,
                "engine": app.target_engine,
            },
            "options": app.options or {},
            "generated_at": datetime.utcnow().isoformat(),
            "template_version": self.template_engine.TEMPLATE_VERSION,
        }
    
    def validate_query(
        self,
        connection_id: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Validate SQL query and return column metadata.
        
        Args:
            connection_id: Connection UUID
            query: SQL query to validate
            
        Returns:
            Validation result with columns
        """
        connection = self.connection_service.get_connection(connection_id)
        if not connection:
            raise NotFoundError(f"Connection {connection_id} not found")
        
        # Use connector to validate and get columns via EXPLAIN
        try:
            connector = self.connection_service.get_connector(connection_id)
            if not connector or not hasattr(connector, 'connect'):
                raise ValidationError("Could not establish connection")
            
            # Try to execute an EXPLAIN or metadata query
            # This is a simplified validation - in production, use proper EXPLAIN parsing
            conn = connector.connect()
            if not conn:
                raise ValidationError("Could not establish connection")
                
            try:
                cursor = conn.cursor()
                # Use database-specific EXPLAIN syntax
                explain_query = f"EXPLAIN {query}"
                try:
                    cursor.execute(explain_query)
                    cursor.fetchall()
                except Exception:
                    # Fall back to LIMIT 0 approach
                    test_query = f"SELECT * FROM ({query}) AS _test LIMIT 0"
                    cursor.execute(test_query)
                    
                    # Try to get column info from description
                    columns = []
                    if cursor.description:
                        for col in cursor.description:
                            columns.append({
                                "name": col[0],
                                "data_type": str(col[1]) if col[1] else "unknown",
                                "nullable": True,
                                "include": True,
                            })
                    
                    return {
                        "valid": True,
                        "message": "Query is valid",
                        "columns": columns,
                        "estimated_rows": None,
                    }
                    
                return {
                    "valid": True,
                    "message": "Query is valid",
                    "columns": [],
                    "estimated_rows": None,
                }
            finally:
                if hasattr(conn, 'close'):
                    conn.close()
        except Exception as e:
            return {
                "valid": False,
                "message": str(e),
                "columns": None,
                "estimated_rows": None,
            }
