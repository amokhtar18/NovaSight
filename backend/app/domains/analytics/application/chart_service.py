"""
NovaSight Chart Service
========================

Business logic for chart operations.
Provides CRUD, data execution, caching, and folder management.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from flask import current_app
from sqlalchemy import and_, or_, func

from app.extensions import db
from app.domains.analytics.domain.chart_models import (
    Chart, ChartFolder, ChartType, ChartSourceType, DashboardChart
)
from app.services.semantic_service import SemanticService, QueryBuildError
from app.domains.analytics.infrastructure.clickhouse_client import (
    get_clickhouse_client,
    ClickHouseError,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================

class ChartServiceError(Exception):
    """Base exception for chart service errors."""
    pass


class ChartNotFoundError(ChartServiceError):
    """Raised when a chart is not found."""
    pass


class ChartFolderNotFoundError(ChartServiceError):
    """Raised when a chart folder is not found."""
    pass


class ChartAccessDeniedError(ChartServiceError):
    """Raised when user doesn't have access to chart."""
    pass


class ChartValidationError(ChartServiceError):
    """Raised when chart data validation fails."""
    pass


class ChartExecutionError(ChartServiceError):
    """Raised when chart query execution fails."""
    pass


# =============================================================================
# Chart Service
# =============================================================================

class ChartService:
    """
    Service for chart operations.
    
    Provides methods for CRUD operations, data execution,
    caching, and folder management.
    """
    
    # Default cache TTL for chart data (5 minutes)
    DEFAULT_CACHE_TTL_SECONDS = 300
    
    # Maximum SQL query length
    MAX_SQL_LENGTH = 50000
    
    # ==========================================================================
    # Chart CRUD Operations
    # ==========================================================================
    
    @classmethod
    def list_for_user(
        cls,
        tenant_id: str,
        user_id: str,
        folder_id: Optional[str] = None,
        include_public: bool = True,
        tags: Optional[List[str]] = None,
        chart_types: Optional[List[str]] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Chart], int]:
        """
        List all accessible charts for a user.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            folder_id: Filter by folder (None for root level)
            include_public: Include public charts from other users
            tags: Filter by tags
            chart_types: Filter by chart types
            search: Search in name/description
            limit: Maximum results
            offset: Pagination offset
        
        Returns:
            Tuple of (list of Chart instances, total count)
        """
        user_uuid = UUID(str(user_id))
        tenant_uuid = UUID(str(tenant_id))
        
        # Build access conditions
        access_conditions = [Chart.created_by == user_uuid]
        if include_public:
            access_conditions.append(Chart.is_public == True)
        
        query = Chart.query.filter(
            Chart.tenant_id == tenant_uuid,
            Chart.is_deleted == False,
            or_(*access_conditions)
        )
        
        # Apply folder filter
        if folder_id:
            query = query.filter(Chart.folder_id == UUID(str(folder_id)))
        else:
            # Root level charts (no folder)
            query = query.filter(Chart.folder_id.is_(None))
        
        # Apply tag filter
        if tags:
            for tag in tags:
                query = query.filter(Chart.tags.contains([tag]))
        
        # Apply chart type filter
        if chart_types:
            type_enums = [ChartType(t) for t in chart_types]
            query = query.filter(Chart.chart_type.in_(type_enums))
        
        # Apply search filter
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Chart.name.ilike(search_pattern),
                    Chart.description.ilike(search_pattern)
                )
            )
        
        # Get total count before pagination
        total = query.count()
        
        # Order by most recently updated
        query = query.order_by(Chart.updated_at.desc())
        
        charts = query.offset(offset).limit(limit).all()
        
        return charts, total
    
    @classmethod
    def list_all_for_tenant(
        cls,
        tenant_id: str,
        user_id: str,
        include_folders: bool = True,
        search: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        List all charts for a tenant (flat list for selection UI).
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            include_folders: Include folder structure
            search: Search filter
            limit: Maximum results
        
        Returns:
            Dict with charts and folders
        """
        user_uuid = UUID(str(user_id))
        tenant_uuid = UUID(str(tenant_id))
        
        # Get all accessible charts
        access_conditions = [
            Chart.created_by == user_uuid,
            Chart.is_public == True
        ]
        
        query = Chart.query.filter(
            Chart.tenant_id == tenant_uuid,
            Chart.is_deleted == False,
            or_(*access_conditions)
        )
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(Chart.name.ilike(search_pattern))
        
        charts = query.order_by(Chart.name).limit(limit).all()
        
        result = {"charts": charts}
        
        if include_folders:
            folders = ChartFolder.query.filter(
                ChartFolder.tenant_id == tenant_uuid
            ).order_by(ChartFolder.name).all()
            result["folders"] = folders
        
        return result
    
    @classmethod
    def get(
        cls,
        chart_id: str,
        tenant_id: str,
        user_id: Optional[str] = None,
        check_access: bool = True,
    ) -> Chart:
        """
        Get a chart by ID.
        
        Args:
            chart_id: Chart identifier
            tenant_id: Tenant identifier
            user_id: User identifier (for access check)
            check_access: Whether to check user access
        
        Returns:
            Chart instance
        
        Raises:
            ChartNotFoundError: If chart not found
            ChartAccessDeniedError: If user doesn't have access
        """
        chart = Chart.query.filter(
            Chart.id == UUID(str(chart_id)),
            Chart.tenant_id == UUID(str(tenant_id)),
            Chart.is_deleted == False,
        ).first()
        
        if not chart:
            raise ChartNotFoundError(f"Chart not found: {chart_id}")
        
        if check_access and user_id:
            user_uuid = UUID(str(user_id))
            if chart.created_by != user_uuid and not chart.is_public:
                raise ChartAccessDeniedError(
                    f"Access denied to chart: {chart_id}"
                )
        
        return chart
    
    @classmethod
    def create(
        cls,
        tenant_id: str,
        created_by: str,
        name: str,
        chart_type: str,
        source_type: str,
        description: Optional[str] = None,
        semantic_model_id: Optional[str] = None,
        sql_query: Optional[str] = None,
        query_config: Optional[Dict] = None,
        viz_config: Optional[Dict] = None,
        folder_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_public: bool = False,
        cache_ttl: Optional[int] = None,
    ) -> Chart:
        """
        Create a new chart.
        
        Args:
            tenant_id: Tenant identifier
            created_by: Creator user ID
            name: Chart name
            chart_type: Visualization type
            source_type: Data source type
            description: Chart description
            semantic_model_id: Semantic model for query building
            sql_query: Raw SQL for SQL source type
            query_config: Query configuration
            viz_config: Visualization configuration
            folder_id: Parent folder ID
            tags: List of tags
            is_public: Public visibility flag
            cache_ttl: Cache TTL in seconds
        
        Returns:
            Created Chart instance
        """
        # Validate source type and required fields
        if source_type == ChartSourceType.SQL_QUERY.value and not sql_query:
            raise ChartValidationError("SQL query is required for SQL source type")
        
        if source_type == ChartSourceType.SEMANTIC_MODEL.value and not semantic_model_id:
            raise ChartValidationError(
                "Semantic model ID is required for semantic model source type"
            )
        
        if sql_query and len(sql_query) > cls.MAX_SQL_LENGTH:
            raise ChartValidationError(
                f"SQL query exceeds maximum length of {cls.MAX_SQL_LENGTH}"
            )
        
        # Validate folder exists if provided
        if folder_id:
            folder = ChartFolder.query.filter(
                ChartFolder.id == UUID(str(folder_id)),
                ChartFolder.tenant_id == UUID(str(tenant_id))
            ).first()
            if not folder:
                raise ChartFolderNotFoundError(f"Folder not found: {folder_id}")
        
        chart = Chart(
            id=uuid4(),
            tenant_id=UUID(str(tenant_id)),
            created_by=UUID(str(created_by)),
            name=name,
            description=description,
            chart_type=ChartType(chart_type),
            source_type=ChartSourceType(source_type),
            semantic_model_id=UUID(str(semantic_model_id)) if semantic_model_id else None,
            sql_query=sql_query,
            query_config=query_config or {},
            viz_config=viz_config or {},
            folder_id=UUID(str(folder_id)) if folder_id else None,
            tags=tags or [],
            is_public=is_public,
            cache_ttl_seconds=cache_ttl or cls.DEFAULT_CACHE_TTL_SECONDS,
        )
        
        db.session.add(chart)
        db.session.commit()
        
        logger.info(f"Created chart: {chart.id} for tenant {tenant_id}")
        return chart
    
    @classmethod
    def update(
        cls,
        chart_id: str,
        tenant_id: str,
        user_id: str,
        **updates,
    ) -> Chart:
        """
        Update a chart.
        
        Args:
            chart_id: Chart identifier
            tenant_id: Tenant identifier
            user_id: User identifier (for permission check)
            **updates: Fields to update
        
        Returns:
            Updated Chart instance
        """
        chart = cls.get(chart_id, tenant_id, user_id, check_access=False)
        
        # Only owner can edit
        if str(chart.created_by) != str(user_id):
            raise ChartAccessDeniedError(f"Cannot edit chart: {chart_id}")
        
        allowed_fields = {
            'name', 'description', 'chart_type', 'source_type',
            'semantic_model_id', 'sql_query', 'query_config', 'viz_config',
            'folder_id', 'tags', 'is_public', 'cache_ttl_seconds'
        }
        
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                # Handle enum conversions
                if field == 'chart_type' and isinstance(value, str):
                    value = ChartType(value)
                elif field == 'source_type' and isinstance(value, str):
                    value = ChartSourceType(value)
                elif field == 'folder_id' and isinstance(value, str):
                    value = UUID(value)
                elif field == 'semantic_model_id' and isinstance(value, str):
                    value = UUID(value)
                
                setattr(chart, field, value)
        
        # Clear cache on update
        chart.cached_data = None
        chart.cache_expires_at = None
        
        db.session.commit()
        
        logger.info(f"Updated chart: {chart_id}")
        return chart
    
    @classmethod
    def delete(
        cls,
        chart_id: str,
        tenant_id: str,
        user_id: str,
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete a chart.
        
        Args:
            chart_id: Chart identifier
            tenant_id: Tenant identifier
            user_id: User identifier (for permission check)
            soft_delete: Use soft delete (default: True)
        
        Returns:
            True if deleted successfully
        """
        chart = cls.get(chart_id, tenant_id, user_id, check_access=False)
        
        # Only owner can delete
        if str(chart.created_by) != str(user_id):
            raise ChartAccessDeniedError(f"Cannot delete chart: {chart_id}")
        
        if soft_delete:
            chart.is_deleted = True
            chart.deleted_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Soft deleted chart: {chart_id}")
        else:
            # Remove from any dashboards first
            DashboardChart.query.filter(
                DashboardChart.chart_id == chart.id
            ).delete()
            db.session.delete(chart)
            db.session.commit()
            logger.info(f"Hard deleted chart: {chart_id}")
        
        return True
    
    @classmethod
    def duplicate(
        cls,
        chart_id: str,
        tenant_id: str,
        user_id: str,
        new_name: Optional[str] = None,
    ) -> Chart:
        """
        Duplicate an existing chart.
        
        Args:
            chart_id: Chart to duplicate
            tenant_id: Tenant identifier
            user_id: User creating the duplicate
            new_name: Name for the new chart
        
        Returns:
            New Chart instance
        """
        original = cls.get(chart_id, tenant_id, user_id)
        
        return cls.create(
            tenant_id=tenant_id,
            created_by=user_id,
            name=new_name or f"{original.name} (Copy)",
            chart_type=original.chart_type.value,
            source_type=original.source_type.value,
            description=original.description,
            semantic_model_id=str(original.semantic_model_id) if original.semantic_model_id else None,
            sql_query=original.sql_query,
            query_config=original.query_config.copy() if original.query_config else None,
            viz_config=original.viz_config.copy() if original.viz_config else None,
            folder_id=str(original.folder_id) if original.folder_id else None,
            tags=original.tags.copy() if original.tags else None,
            is_public=False,  # Duplicates are private by default
        )
    
    # ==========================================================================
    # Data Execution
    # ==========================================================================
    
    @classmethod
    def execute_chart(
        cls,
        chart_id: str,
        tenant_id: str,
        user_id: str,
        force_refresh: bool = False,
        runtime_filters: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Execute chart query and return data.
        
        Args:
            chart_id: Chart identifier
            tenant_id: Tenant identifier
            user_id: User identifier
            force_refresh: Force bypass cache
            runtime_filters: Additional runtime filters
        
        Returns:
            Dict with data, columns, metadata
        """
        chart = cls.get(chart_id, tenant_id, user_id)
        start_time = time.time()
        
        # Check cache (unless force refresh)
        if not force_refresh and chart.cached_data:
            if chart.cache_expires_at and datetime.utcnow() < chart.cache_expires_at:
                logger.debug(f"Returning cached result for chart {chart_id}")
                return {
                    "chart_id": str(chart.id),
                    "data": chart.cached_data.get("data", []),
                    "columns": chart.cached_data.get("columns", []),
                    "row_count": chart.cached_data.get("row_count", 0),
                    "execution_time_ms": 0,
                    "cached": True,
                    "cache_expires_at": chart.cache_expires_at.isoformat(),
                }
        
        # Execute query based on source type
        try:
            if chart.source_type == ChartSourceType.SEMANTIC_MODEL:
                data, columns = cls._execute_semantic_query(
                    chart, tenant_id, runtime_filters
                )
            else:
                data, columns = cls._execute_sql_query(
                    chart, tenant_id, runtime_filters
                )
        except Exception as e:
            logger.error(f"Chart execution failed: {e}")
            raise ChartExecutionError(f"Query execution failed: {str(e)}")
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Update cache
        chart.cached_data = {
            "data": data,
            "columns": columns,
            "row_count": len(data),
        }
        chart.cache_expires_at = datetime.utcnow() + timedelta(seconds=chart.cache_ttl_seconds)
        db.session.commit()
        
        return {
            "chart_id": str(chart.id),
            "data": data,
            "columns": columns,
            "row_count": len(data),
            "execution_time_ms": execution_time_ms,
            "cached": False,
            "cache_expires_at": chart.cache_expires_at.isoformat(),
        }
    
    @classmethod
    def preview_query(
        cls,
        tenant_id: str,
        user_id: str,
        source_type: str,
        semantic_model_id: Optional[str] = None,
        sql_query: Optional[str] = None,
        query_config: Optional[Dict] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Preview query results without saving a chart.
        
        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            source_type: Data source type
            semantic_model_id: Semantic model ID
            sql_query: SQL query
            query_config: Query configuration
            limit: Row limit
        
        Returns:
            Dict with data and columns
        """
        start_time = time.time()
        
        try:
            if source_type == ChartSourceType.SEMANTIC_MODEL.value:
                if not semantic_model_id:
                    raise ChartValidationError("Semantic model ID required")
                
                # Build and execute via semantic service
                semantic_service = SemanticService()
                query_config = query_config or {}
                query_config['limit'] = limit
                
                result = semantic_service.execute_query(
                    tenant_id=tenant_id,
                    semantic_model_id=semantic_model_id,
                    query_config=query_config,
                )
                data = result.get("data", [])
                columns = result.get("columns", [])
            else:
                if not sql_query:
                    raise ChartValidationError("SQL query required")
                
                # Execute raw SQL with limit
                data, columns = cls._execute_raw_sql(
                    tenant_id, sql_query, limit
                )
        except QueryBuildError as e:
            raise ChartExecutionError(f"Query build failed: {str(e)}")
        except Exception as e:
            logger.error(f"Preview query failed: {e}")
            raise ChartExecutionError(f"Query execution failed: {str(e)}")
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "data": data,
            "columns": columns,
            "row_count": len(data),
            "execution_time_ms": execution_time_ms,
        }
    
    @classmethod
    def _execute_semantic_query(
        cls,
        chart: Chart,
        tenant_id: str,
        runtime_filters: Optional[Dict] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        """Execute query via semantic service."""
        semantic_service = SemanticService()
        
        query_config = chart.query_config.copy() if chart.query_config else {}
        
        # Merge runtime filters
        if runtime_filters:
            existing_filters = query_config.get("filters", [])
            query_config["filters"] = existing_filters + runtime_filters.get("filters", [])
        
        result = semantic_service.execute_query(
            tenant_id=tenant_id,
            semantic_model_id=str(chart.semantic_model_id),
            query_config=query_config,
        )
        
        return result.get("data", []), result.get("columns", [])
    
    @classmethod
    def _execute_sql_query(
        cls,
        chart: Chart,
        tenant_id: str,
        runtime_filters: Optional[Dict] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        """Execute raw SQL query."""
        limit = chart.query_config.get("limit", 1000) if chart.query_config else 1000
        return cls._execute_raw_sql(tenant_id, chart.sql_query, limit)
    
    @classmethod
    def _execute_raw_sql(
        cls,
        tenant_id: str,
        sql_query: str,
        limit: int = 1000,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Execute raw SQL query against data warehouse.
        
        Connects to ClickHouse (or mock if not available) and executes
        the provided SQL query with a row limit.
        
        Args:
            tenant_id: Tenant identifier for database isolation
            sql_query: SQL query to execute
            limit: Maximum number of rows to return
            
        Returns:
            Tuple of (data rows as dicts, column definitions)
        """
        try:
            # Get ClickHouse client for tenant
            client = get_clickhouse_client(tenant_id=tenant_id)
            
            # Add LIMIT clause if not present
            query = sql_query.strip().rstrip(';')
            if 'LIMIT' not in query.upper():
                query = f"{query} LIMIT {limit}"
            
            # Execute query
            result = client.execute(query, with_column_types=True)
            
            # Build column definitions
            columns = [
                {"name": col, "type": "string"}  # Basic type inference TODO
                for col in result.columns
            ]
            
            # Convert to list of dicts
            data = result.to_records()
            
            logger.info(f"SQL query executed: {len(data)} rows returned")
            return data, columns
            
        except ClickHouseError as e:
            logger.error(f"ClickHouse query error: {e}")
            raise ChartExecutionError(f"Query execution failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error executing SQL: {e}")
            # Fallback: return mock data for development
            logger.warning("Returning empty result for SQL execution")
            return [], []
    
    # ==========================================================================
    # Folder Operations
    # ==========================================================================
    
    @classmethod
    def list_folders(
        cls,
        tenant_id: str,
        parent_id: Optional[str] = None,
    ) -> List[ChartFolder]:
        """
        List chart folders.
        
        Args:
            tenant_id: Tenant identifier
            parent_id: Parent folder ID (None for root)
        
        Returns:
            List of ChartFolder instances
        """
        query = ChartFolder.query.filter(
            ChartFolder.tenant_id == UUID(str(tenant_id))
        )
        
        if parent_id:
            query = query.filter(ChartFolder.parent_id == UUID(str(parent_id)))
        else:
            query = query.filter(ChartFolder.parent_id.is_(None))
        
        return query.order_by(ChartFolder.name).all()
    
    @classmethod
    def get_folder(
        cls,
        folder_id: str,
        tenant_id: str,
    ) -> ChartFolder:
        """Get a folder by ID."""
        folder = ChartFolder.query.filter(
            ChartFolder.id == UUID(str(folder_id)),
            ChartFolder.tenant_id == UUID(str(tenant_id))
        ).first()
        
        if not folder:
            raise ChartFolderNotFoundError(f"Folder not found: {folder_id}")
        
        return folder
    
    @classmethod
    def create_folder(
        cls,
        tenant_id: str,
        created_by: str,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[str] = None,
    ) -> ChartFolder:
        """Create a new chart folder."""
        # Check for duplicate name in same parent
        existing = ChartFolder.query.filter(
            ChartFolder.tenant_id == UUID(str(tenant_id)),
            ChartFolder.name == name,
            ChartFolder.parent_id == (UUID(str(parent_id)) if parent_id else None)
        ).first()
        
        if existing:
            raise ChartValidationError(f"Folder with name '{name}' already exists")
        
        folder = ChartFolder(
            id=uuid4(),
            tenant_id=UUID(str(tenant_id)),
            created_by=UUID(str(created_by)),
            name=name,
            description=description,
            parent_id=UUID(str(parent_id)) if parent_id else None,
        )
        
        db.session.add(folder)
        db.session.commit()
        
        logger.info(f"Created chart folder: {folder.id}")
        return folder
    
    @classmethod
    def update_folder(
        cls,
        folder_id: str,
        tenant_id: str,
        user_id: str,
        **updates,
    ) -> ChartFolder:
        """Update a chart folder."""
        folder = cls.get_folder(folder_id, tenant_id)
        
        # Only owner can edit
        if str(folder.created_by) != str(user_id):
            raise ChartAccessDeniedError(f"Cannot edit folder: {folder_id}")
        
        allowed_fields = {'name', 'description', 'parent_id'}
        
        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                if field == 'parent_id' and isinstance(value, str):
                    value = UUID(value)
                setattr(folder, field, value)
        
        db.session.commit()
        return folder
    
    @classmethod
    def delete_folder(
        cls,
        folder_id: str,
        tenant_id: str,
        user_id: str,
        move_contents_to: Optional[str] = None,
    ) -> bool:
        """
        Delete a chart folder.
        
        Args:
            folder_id: Folder to delete
            tenant_id: Tenant identifier
            user_id: User identifier
            move_contents_to: Move charts to this folder (None = root)
        
        Returns:
            True if successful
        """
        folder = cls.get_folder(folder_id, tenant_id)
        
        # Only owner can delete
        if str(folder.created_by) != str(user_id):
            raise ChartAccessDeniedError(f"Cannot delete folder: {folder_id}")
        
        # Move charts to new location
        new_folder_id = UUID(str(move_contents_to)) if move_contents_to else None
        Chart.query.filter(Chart.folder_id == folder.id).update(
            {"folder_id": new_folder_id}
        )
        
        # Move subfolders to new location
        ChartFolder.query.filter(ChartFolder.parent_id == folder.id).update(
            {"parent_id": new_folder_id}
        )
        
        db.session.delete(folder)
        db.session.commit()
        
        logger.info(f"Deleted chart folder: {folder_id}")
        return True
    
    # ==========================================================================
    # Dashboard Chart Operations
    # ==========================================================================
    
    @classmethod
    def add_to_dashboard(
        cls,
        chart_id: str,
        dashboard_id: str,
        tenant_id: str,
        user_id: str,
        grid_position: Optional[Dict] = None,
        local_filters: Optional[Dict] = None,
        local_viz_config: Optional[Dict] = None,
    ) -> DashboardChart:
        """
        Add a chart to a dashboard.
        
        Args:
            chart_id: Chart to add
            dashboard_id: Dashboard to add to
            tenant_id: Tenant identifier
            user_id: User identifier
            grid_position: Position configuration
            local_filters: Dashboard-specific filters
            local_viz_config: Dashboard-specific viz overrides
        
        Returns:
            DashboardChart instance
        """
        # Verify chart access
        chart = cls.get(chart_id, tenant_id, user_id)
        
        # Check if already added
        existing = DashboardChart.query.filter(
            DashboardChart.chart_id == chart.id,
            DashboardChart.dashboard_id == UUID(str(dashboard_id))
        ).first()
        
        if existing:
            raise ChartValidationError("Chart already exists on dashboard")
        
        dashboard_chart = DashboardChart(
            id=uuid4(),
            dashboard_id=UUID(str(dashboard_id)),
            chart_id=chart.id,
            grid_position=grid_position or {"x": 0, "y": 0, "w": 6, "h": 4},
            local_filters=local_filters or {},
            local_viz_config=local_viz_config or {},
        )
        
        db.session.add(dashboard_chart)
        db.session.commit()
        
        return dashboard_chart
    
    @classmethod
    def remove_from_dashboard(
        cls,
        chart_id: str,
        dashboard_id: str,
        tenant_id: str,
        user_id: str,
    ) -> bool:
        """Remove a chart from a dashboard."""
        result = DashboardChart.query.filter(
            DashboardChart.chart_id == UUID(str(chart_id)),
            DashboardChart.dashboard_id == UUID(str(dashboard_id))
        ).delete()
        
        db.session.commit()
        return result > 0
    
    @classmethod
    def get_dashboard_charts(
        cls,
        dashboard_id: str,
        tenant_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all charts on a dashboard with their configurations."""
        dashboard_charts = DashboardChart.query.filter(
            DashboardChart.dashboard_id == UUID(str(dashboard_id))
        ).all()
        
        result = []
        for dc in dashboard_charts:
            chart = Chart.query.get(dc.chart_id)
            if chart and not chart.is_deleted:
                result.append({
                    "dashboard_chart_id": str(dc.id),
                    "chart": chart,
                    "grid_position": dc.grid_position,
                    "local_filters": dc.local_filters,
                    "local_viz_config": dc.local_viz_config,
                })
        
        return result
