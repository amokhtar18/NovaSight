"""
NovaSight Semantic Layer Service
=================================

Business logic for semantic layer operations including:
- Semantic model CRUD
- Dimension and measure management
- Query execution with automatic join resolution
- Caching and optimization
"""

import logging
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from flask import current_app
from sqlalchemy import and_, or_

from app.extensions import db
from app.models.semantic import (
    SemanticModel, Dimension, Measure, Relationship,
    DimensionType, AggregationType, ModelType, RelationshipType,
)
from app.services.clickhouse_client import (
    ClickHouseClient, get_clickhouse_client, QueryResult,
    ClickHouseQueryError,
)

logger = logging.getLogger(__name__)


class SemanticServiceError(Exception):
    """Base exception for semantic service errors."""
    pass


class ModelNotFoundError(SemanticServiceError):
    """Raised when a semantic model is not found."""
    pass


class DimensionNotFoundError(SemanticServiceError):
    """Raised when a dimension is not found."""
    pass


class MeasureNotFoundError(SemanticServiceError):
    """Raised when a measure is not found."""
    pass


class QueryBuildError(SemanticServiceError):
    """Raised when query building fails."""
    pass


class SemanticService:
    """
    Service for semantic layer operations.
    
    Provides methods for managing semantic models, dimensions, measures,
    and executing semantic queries with automatic join resolution.
    """
    
    # Simple in-memory cache (replace with Redis in production)
    _query_cache: Dict[str, Tuple[Any, datetime]] = {}
    _cache_ttl_seconds = 3600
    
    # ==========================================================================
    # Semantic Model Operations
    # ==========================================================================
    
    @classmethod
    def list_models(
        cls,
        tenant_id: str,
        include_inactive: bool = False,
        model_type: Optional[str] = None,
    ) -> List[SemanticModel]:
        """
        List all semantic models for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            include_inactive: Include inactive models
            model_type: Filter by model type (fact, dimension, aggregate)
        
        Returns:
            List of SemanticModel instances
        """
        query = SemanticModel.query.filter(SemanticModel.tenant_id == tenant_id)
        
        if not include_inactive:
            query = query.filter(SemanticModel.is_active == True)
        
        if model_type:
            query = query.filter(SemanticModel.model_type == model_type)
        
        return query.order_by(SemanticModel.name).all()
    
    @classmethod
    def get_model(
        cls,
        model_id: str,
        tenant_id: str,
    ) -> SemanticModel:
        """
        Get a semantic model by ID.
        
        Args:
            model_id: Model UUID
            tenant_id: Tenant identifier
        
        Returns:
            SemanticModel instance
        
        Raises:
            ModelNotFoundError: If model not found
        """
        model = SemanticModel.query.filter(
            and_(
                SemanticModel.id == model_id,
                SemanticModel.tenant_id == tenant_id,
            )
        ).first()
        
        if not model:
            raise ModelNotFoundError(f"Semantic model {model_id} not found")
        
        return model
    
    @classmethod
    def get_model_by_name(
        cls,
        name: str,
        tenant_id: str,
    ) -> Optional[SemanticModel]:
        """Get a semantic model by name."""
        return SemanticModel.query.filter(
            and_(
                SemanticModel.name == name,
                SemanticModel.tenant_id == tenant_id,
            )
        ).first()
    
    @classmethod
    def create_model(
        cls,
        tenant_id: str,
        name: str,
        dbt_model: str,
        label: Optional[str] = None,
        description: Optional[str] = None,
        model_type: str = "fact",
        target_schema: Optional[str] = None,
        target_table: Optional[str] = None,
        cache_enabled: bool = True,
        cache_ttl_seconds: int = 3600,
        tags: Optional[List[str]] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> SemanticModel:
        """
        Create a new semantic model.
        
        Args:
            tenant_id: Tenant identifier
            name: Model name (unique per tenant)
            dbt_model: Reference to dbt model
            label: Human-readable label
            description: Model description
            model_type: Type (fact, dimension, aggregate)
            target_schema: ClickHouse schema
            target_table: ClickHouse table
            cache_enabled: Enable query caching
            cache_ttl_seconds: Cache TTL
            tags: Model tags
            meta: Additional metadata
        
        Returns:
            Created SemanticModel
        """
        # Check for duplicate name
        existing = cls.get_model_by_name(name, tenant_id)
        if existing:
            raise SemanticServiceError(f"Model with name '{name}' already exists")
        
        model = SemanticModel(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            label=label or name.replace('_', ' ').title(),
            description=description,
            dbt_model=dbt_model,
            model_type=ModelType(model_type) if isinstance(model_type, str) else model_type,
            target_schema=target_schema,
            target_table=target_table or dbt_model,
            cache_enabled=cache_enabled,
            cache_ttl_seconds=cache_ttl_seconds,
            tags=tags or [],
            meta=meta or {},
            is_active=True,
        )
        
        db.session.add(model)
        db.session.commit()
        
        logger.info(f"Created semantic model: {name} for tenant {tenant_id}")
        
        return model
    
    @classmethod
    def update_model(
        cls,
        model_id: str,
        tenant_id: str,
        **kwargs,
    ) -> SemanticModel:
        """Update a semantic model."""
        model = cls.get_model(model_id, tenant_id)
        
        updatable_fields = [
            'label', 'description', 'model_type', 'target_schema', 'target_table',
            'cache_enabled', 'cache_ttl_seconds', 'tags', 'meta', 'is_active',
        ]
        
        for field in updatable_fields:
            if field in kwargs and kwargs[field] is not None:
                value = kwargs[field]
                if field == 'model_type' and isinstance(value, str):
                    value = ModelType(value)
                setattr(model, field, value)
        
        db.session.commit()
        
        logger.info(f"Updated semantic model: {model.name}")
        
        return model
    
    @classmethod
    def delete_model(cls, model_id: str, tenant_id: str) -> bool:
        """Delete a semantic model."""
        model = cls.get_model(model_id, tenant_id)
        
        db.session.delete(model)
        db.session.commit()
        
        logger.info(f"Deleted semantic model: {model.name}")
        
        return True
    
    # ==========================================================================
    # Dimension Operations
    # ==========================================================================
    
    @classmethod
    def list_dimensions(
        cls,
        tenant_id: str,
        model_id: Optional[str] = None,
        include_hidden: bool = False,
    ) -> List[Dimension]:
        """List dimensions, optionally filtered by model."""
        query = Dimension.query.filter(Dimension.tenant_id == tenant_id)
        
        if model_id:
            query = query.filter(Dimension.semantic_model_id == model_id)
        
        if not include_hidden:
            query = query.filter(Dimension.is_hidden == False)
        
        return query.order_by(Dimension.name).all()
    
    @classmethod
    def get_dimension(
        cls,
        dimension_id: str,
        tenant_id: str,
    ) -> Dimension:
        """Get a dimension by ID."""
        dimension = Dimension.query.filter(
            and_(
                Dimension.id == dimension_id,
                Dimension.tenant_id == tenant_id,
            )
        ).first()
        
        if not dimension:
            raise DimensionNotFoundError(f"Dimension {dimension_id} not found")
        
        return dimension
    
    @classmethod
    def add_dimension(
        cls,
        model_id: str,
        tenant_id: str,
        name: str,
        expression: str,
        label: Optional[str] = None,
        description: Optional[str] = None,
        type: str = "categorical",
        data_type: str = "String",
        is_primary_key: bool = False,
        is_hidden: bool = False,
        is_filterable: bool = True,
        is_groupable: bool = True,
        hierarchy_name: Optional[str] = None,
        hierarchy_level: Optional[int] = None,
        parent_dimension_id: Optional[str] = None,
        default_value: Optional[str] = None,
        format_string: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dimension:
        """Add a dimension to a semantic model."""
        # Verify model exists
        model = cls.get_model(model_id, tenant_id)
        
        # Check for duplicate name in model
        existing = Dimension.query.filter(
            and_(
                Dimension.semantic_model_id == model_id,
                Dimension.name == name,
            )
        ).first()
        
        if existing:
            raise SemanticServiceError(f"Dimension '{name}' already exists in model")
        
        dimension = Dimension(
            id=uuid4(),
            tenant_id=tenant_id,
            semantic_model_id=model_id,
            name=name,
            label=label or name.replace('_', ' ').title(),
            description=description,
            type=DimensionType(type) if isinstance(type, str) else type,
            expression=expression,
            data_type=data_type,
            is_primary_key=is_primary_key,
            is_hidden=is_hidden,
            is_filterable=is_filterable,
            is_groupable=is_groupable,
            hierarchy_name=hierarchy_name,
            hierarchy_level=hierarchy_level,
            parent_dimension_id=parent_dimension_id,
            default_value=default_value,
            format_string=format_string,
            meta=meta or {},
        )
        
        db.session.add(dimension)
        db.session.commit()
        
        logger.info(f"Added dimension: {name} to model {model.name}")
        
        return dimension
    
    @classmethod
    def update_dimension(
        cls,
        dimension_id: str,
        tenant_id: str,
        **kwargs,
    ) -> Dimension:
        """Update a dimension."""
        dimension = cls.get_dimension(dimension_id, tenant_id)
        
        updatable_fields = [
            'label', 'description', 'type', 'expression', 'data_type',
            'is_hidden', 'is_filterable', 'is_groupable', 'hierarchy_name',
            'hierarchy_level', 'parent_dimension_id', 'default_value',
            'format_string', 'meta',
        ]
        
        for field in updatable_fields:
            if field in kwargs and kwargs[field] is not None:
                value = kwargs[field]
                if field == 'type' and isinstance(value, str):
                    value = DimensionType(value)
                setattr(dimension, field, value)
        
        db.session.commit()
        
        return dimension
    
    @classmethod
    def delete_dimension(cls, dimension_id: str, tenant_id: str) -> bool:
        """Delete a dimension."""
        dimension = cls.get_dimension(dimension_id, tenant_id)
        
        db.session.delete(dimension)
        db.session.commit()
        
        logger.info(f"Deleted dimension: {dimension.name}")
        
        return True
    
    # ==========================================================================
    # Measure Operations
    # ==========================================================================
    
    @classmethod
    def list_measures(
        cls,
        tenant_id: str,
        model_id: Optional[str] = None,
        include_hidden: bool = False,
    ) -> List[Measure]:
        """List measures, optionally filtered by model."""
        query = Measure.query.filter(Measure.tenant_id == tenant_id)
        
        if model_id:
            query = query.filter(Measure.semantic_model_id == model_id)
        
        if not include_hidden:
            query = query.filter(Measure.is_hidden == False)
        
        return query.order_by(Measure.name).all()
    
    @classmethod
    def get_measure(
        cls,
        measure_id: str,
        tenant_id: str,
    ) -> Measure:
        """Get a measure by ID."""
        measure = Measure.query.filter(
            and_(
                Measure.id == measure_id,
                Measure.tenant_id == tenant_id,
            )
        ).first()
        
        if not measure:
            raise MeasureNotFoundError(f"Measure {measure_id} not found")
        
        return measure
    
    @classmethod
    def add_measure(
        cls,
        model_id: str,
        tenant_id: str,
        name: str,
        aggregation: str,
        expression: str,
        label: Optional[str] = None,
        description: Optional[str] = None,
        format: Optional[str] = None,
        format_string: Optional[str] = None,
        decimal_places: int = 2,
        unit: Optional[str] = None,
        unit_suffix: Optional[str] = None,
        is_hidden: bool = False,
        is_additive: bool = True,
        percentile_value: Optional[int] = None,
        default_filters: Optional[List[Dict]] = None,
        time_dimension: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Measure:
        """Add a measure to a semantic model."""
        # Verify model exists
        model = cls.get_model(model_id, tenant_id)
        
        # Check for duplicate name in model
        existing = Measure.query.filter(
            and_(
                Measure.semantic_model_id == model_id,
                Measure.name == name,
            )
        ).first()
        
        if existing:
            raise SemanticServiceError(f"Measure '{name}' already exists in model")
        
        measure = Measure(
            id=uuid4(),
            tenant_id=tenant_id,
            semantic_model_id=model_id,
            name=name,
            label=label or name.replace('_', ' ').title(),
            description=description,
            aggregation=AggregationType(aggregation) if isinstance(aggregation, str) else aggregation,
            expression=expression,
            format=format,
            format_string=format_string,
            decimal_places=decimal_places,
            unit=unit,
            unit_suffix=unit_suffix,
            is_hidden=is_hidden,
            is_additive=is_additive,
            percentile_value=percentile_value,
            default_filters=default_filters or [],
            time_dimension=time_dimension,
            meta=meta or {},
        )
        
        db.session.add(measure)
        db.session.commit()
        
        logger.info(f"Added measure: {name} to model {model.name}")
        
        return measure
    
    @classmethod
    def update_measure(
        cls,
        measure_id: str,
        tenant_id: str,
        **kwargs,
    ) -> Measure:
        """Update a measure."""
        measure = cls.get_measure(measure_id, tenant_id)
        
        updatable_fields = [
            'label', 'description', 'aggregation', 'expression', 'format',
            'format_string', 'decimal_places', 'unit', 'unit_suffix',
            'is_hidden', 'is_additive', 'percentile_value', 'default_filters',
            'time_dimension', 'meta',
        ]
        
        for field in updatable_fields:
            if field in kwargs and kwargs[field] is not None:
                value = kwargs[field]
                if field == 'aggregation' and isinstance(value, str):
                    value = AggregationType(value)
                setattr(measure, field, value)
        
        db.session.commit()
        
        return measure
    
    @classmethod
    def delete_measure(cls, measure_id: str, tenant_id: str) -> bool:
        """Delete a measure."""
        measure = cls.get_measure(measure_id, tenant_id)
        
        db.session.delete(measure)
        db.session.commit()
        
        logger.info(f"Deleted measure: {measure.name}")
        
        return True
    
    # ==========================================================================
    # Relationship Operations
    # ==========================================================================
    
    @classmethod
    def list_relationships(cls, tenant_id: str) -> List[Relationship]:
        """List all relationships for a tenant."""
        return Relationship.query.filter(
            Relationship.tenant_id == tenant_id
        ).all()
    
    @classmethod
    def create_relationship(
        cls,
        tenant_id: str,
        from_model_id: str,
        to_model_id: str,
        from_column: str,
        to_column: str,
        relationship_type: str = "many_to_one",
        join_type: str = "LEFT",
        additional_conditions: Optional[str] = None,
    ) -> Relationship:
        """Create a relationship between models."""
        # Verify both models exist
        cls.get_model(from_model_id, tenant_id)
        cls.get_model(to_model_id, tenant_id)
        
        relationship = Relationship(
            id=uuid4(),
            tenant_id=tenant_id,
            from_model_id=from_model_id,
            to_model_id=to_model_id,
            from_column=from_column,
            to_column=to_column,
            relationship_type=RelationshipType(relationship_type),
            join_type=join_type.upper(),
            additional_conditions=additional_conditions,
            is_active=True,
        )
        
        db.session.add(relationship)
        db.session.commit()
        
        logger.info(f"Created relationship: {from_model_id} -> {to_model_id}")
        
        return relationship
    
    @classmethod
    def delete_relationship(cls, relationship_id: str, tenant_id: str) -> bool:
        """Delete a relationship."""
        relationship = Relationship.query.filter(
            and_(
                Relationship.id == relationship_id,
                Relationship.tenant_id == tenant_id,
            )
        ).first()
        
        if not relationship:
            raise SemanticServiceError(f"Relationship {relationship_id} not found")
        
        db.session.delete(relationship)
        db.session.commit()
        
        return True
    
    # ==========================================================================
    # Query Execution
    # ==========================================================================
    
    @classmethod
    def execute_query(
        cls,
        tenant_id: str,
        dimensions: List[str],
        measures: List[str],
        filters: Optional[List[Dict]] = None,
        order_by: Optional[List[Dict]] = None,
        limit: int = 1000,
        offset: int = 0,
        time_dimension: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute a semantic layer query.
        
        Args:
            tenant_id: Tenant identifier
            dimensions: List of dimension names to group by
            measures: List of measure names to aggregate
            filters: List of filter conditions
            order_by: List of ordering specifications
            limit: Maximum rows to return
            offset: Offset for pagination
            time_dimension: Optional time dimension for date filtering
            date_from: Start date filter
            date_to: End date filter
            use_cache: Whether to use query cache
        
        Returns:
            Dictionary with query results
        """
        filters = filters or []
        order_by = order_by or []
        
        # Generate cache key
        cache_key = cls._generate_cache_key(
            tenant_id, dimensions, measures, filters, order_by, limit, offset
        )
        
        # Check cache
        if use_cache:
            cached = cls._get_from_cache(cache_key)
            if cached:
                logger.debug(f"Cache hit for query: {cache_key[:32]}...")
                return {**cached, 'cached': True}
        
        # Resolve dimensions and measures
        dim_objects = cls._resolve_dimensions(tenant_id, dimensions)
        measure_objects = cls._resolve_measures(tenant_id, measures)
        
        if not measure_objects:
            raise QueryBuildError("At least one measure is required")
        
        # Determine which models are needed
        models_needed = cls._get_required_models(dim_objects, measure_objects)
        
        # Build SQL query
        sql = cls._build_query(
            tenant_id=tenant_id,
            dimensions=dim_objects,
            measures=measure_objects,
            models=models_needed,
            filters=filters,
            order_by=order_by,
            limit=limit,
            offset=offset,
            time_dimension=time_dimension,
            date_from=date_from,
            date_to=date_to,
        )
        
        # Execute query
        try:
            client = get_clickhouse_client(tenant_id=tenant_id)
            result = client.execute(sql)
            
            # Build column names
            columns = [d.name for d in dim_objects] + [m.name for m in measure_objects]
            
            # Convert result to serializable format
            rows = [list(row) for row in result.rows]
            
            response = {
                'columns': columns,
                'rows': rows,
                'row_count': len(rows),
                'query': sql,
                'execution_time_ms': result.execution_time_ms,
                'cached': False,
            }
            
            # Cache result
            if use_cache:
                cls._store_in_cache(cache_key, response)
            
            return response
            
        except ClickHouseQueryError as e:
            logger.error(f"Query execution failed: {e}")
            raise QueryBuildError(f"Query execution failed: {e}")
    
    @classmethod
    def _resolve_dimensions(
        cls,
        tenant_id: str,
        dimension_names: List[str],
    ) -> List[Dimension]:
        """Resolve dimension names to Dimension objects."""
        dimensions = []
        
        for name in dimension_names:
            dim = Dimension.query.filter(
                and_(
                    Dimension.tenant_id == tenant_id,
                    Dimension.name == name,
                )
            ).first()
            
            if not dim:
                raise DimensionNotFoundError(f"Dimension '{name}' not found")
            
            dimensions.append(dim)
        
        return dimensions
    
    @classmethod
    def _resolve_measures(
        cls,
        tenant_id: str,
        measure_names: List[str],
    ) -> List[Measure]:
        """Resolve measure names to Measure objects."""
        measures = []
        
        for name in measure_names:
            measure = Measure.query.filter(
                and_(
                    Measure.tenant_id == tenant_id,
                    Measure.name == name,
                )
            ).first()
            
            if not measure:
                raise MeasureNotFoundError(f"Measure '{name}' not found")
            
            measures.append(measure)
        
        return measures
    
    @classmethod
    def _get_required_models(
        cls,
        dimensions: List[Dimension],
        measures: List[Measure],
    ) -> Set[SemanticModel]:
        """Get all models required for the query."""
        model_ids = set()
        
        for dim in dimensions:
            model_ids.add(dim.semantic_model_id)
        
        for measure in measures:
            model_ids.add(measure.semantic_model_id)
        
        models = SemanticModel.query.filter(
            SemanticModel.id.in_(model_ids)
        ).all()
        
        return set(models)
    
    @classmethod
    def _build_query(
        cls,
        tenant_id: str,
        dimensions: List[Dimension],
        measures: List[Measure],
        models: Set[SemanticModel],
        filters: List[Dict],
        order_by: List[Dict],
        limit: int,
        offset: int,
        time_dimension: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> str:
        """Build the SQL query from semantic definitions."""
        
        # Determine primary model (first model with a measure)
        primary_model = next(iter(models))
        for model in models:
            if model.model_type == ModelType.FACT:
                primary_model = model
                break
        
        # Build SELECT clause
        select_parts = []
        
        for dim in dimensions:
            select_parts.append(f"{dim.expression} AS {dim.name}")
        
        for measure in measures:
            select_parts.append(f"{measure.get_sql_expression()} AS {measure.name}")
        
        select_clause = ",\n    ".join(select_parts)
        
        # Build FROM clause with joins if multiple models
        from_clause = f"{primary_model.target_table or primary_model.dbt_model}"
        
        if len(models) > 1:
            # Get relationships and build joins
            relationships = Relationship.query.filter(
                and_(
                    Relationship.tenant_id == tenant_id,
                    Relationship.is_active == True,
                    or_(
                        Relationship.from_model_id.in_([m.id for m in models]),
                        Relationship.to_model_id.in_([m.id for m in models]),
                    )
                )
            ).all()
            
            joined_models = {primary_model.id}
            join_clauses = []
            
            for rel in relationships:
                if rel.from_model_id in joined_models and rel.to_model_id not in joined_models:
                    to_model = next((m for m in models if m.id == rel.to_model_id), None)
                    if to_model:
                        join_clauses.append(
                            f"{rel.join_type} JOIN {to_model.target_table or to_model.dbt_model} "
                            f"ON {primary_model.target_table or primary_model.dbt_model}.{rel.from_column} = "
                            f"{to_model.target_table or to_model.dbt_model}.{rel.to_column}"
                        )
                        joined_models.add(to_model.id)
            
            if join_clauses:
                from_clause += "\n" + "\n".join(join_clauses)
        
        # Build WHERE clause
        where_parts = []
        
        # Add tenant filter
        where_parts.append(f"tenant_id = '{tenant_id}'")
        
        # Add user filters
        for f in filters:
            dim_name = f.get('dimension')
            operator = f.get('operator', 'eq')
            value = f.get('value')
            values = f.get('values', [])
            
            # Find the dimension expression
            dim = next((d for d in dimensions if d.name == dim_name), None)
            if not dim:
                continue
            
            filter_expr = cls._build_filter_expression(dim.expression, operator, value, values)
            if filter_expr:
                where_parts.append(filter_expr)
        
        # Add time range filter
        if time_dimension and (date_from or date_to):
            time_dim = next((d for d in dimensions if d.name == time_dimension), None)
            if time_dim:
                if date_from:
                    where_parts.append(
                        f"{time_dim.expression} >= '{date_from.strftime('%Y-%m-%d')}'"
                    )
                if date_to:
                    where_parts.append(
                        f"{time_dim.expression} <= '{date_to.strftime('%Y-%m-%d')}'"
                    )
        
        where_clause = " AND ".join(where_parts)
        
        # Build GROUP BY clause
        group_by_parts = [dim.expression for dim in dimensions]
        group_by_clause = ", ".join(group_by_parts) if group_by_parts else ""
        
        # Build ORDER BY clause
        order_by_parts = []
        for o in order_by:
            field = o.get('field')
            order = o.get('order', 'asc').upper()
            order_by_parts.append(f"{field} {order}")
        
        order_by_clause = ", ".join(order_by_parts) if order_by_parts else ""
        
        # Assemble query
        sql = f"""SELECT
    {select_clause}
FROM {from_clause}
WHERE {where_clause}"""
        
        if group_by_clause:
            sql += f"\nGROUP BY {group_by_clause}"
        
        if order_by_clause:
            sql += f"\nORDER BY {order_by_clause}"
        
        sql += f"\nLIMIT {limit}"
        
        if offset > 0:
            sql += f" OFFSET {offset}"
        
        return sql
    
    @classmethod
    def _build_filter_expression(
        cls,
        expression: str,
        operator: str,
        value: Any,
        values: List[Any],
    ) -> Optional[str]:
        """Build a SQL filter expression."""
        op_map = {
            'eq': '=',
            'ne': '!=',
            'gt': '>',
            'gte': '>=',
            'lt': '<',
            'lte': '<=',
        }
        
        if operator in op_map:
            if isinstance(value, str):
                return f"{expression} {op_map[operator]} '{value}'"
            else:
                return f"{expression} {op_map[operator]} {value}"
        
        elif operator == 'in':
            vals = values or ([value] if value else [])
            if vals:
                formatted = ", ".join(
                    f"'{v}'" if isinstance(v, str) else str(v) for v in vals
                )
                return f"{expression} IN ({formatted})"
        
        elif operator == 'not_in':
            vals = values or ([value] if value else [])
            if vals:
                formatted = ", ".join(
                    f"'{v}'" if isinstance(v, str) else str(v) for v in vals
                )
                return f"{expression} NOT IN ({formatted})"
        
        elif operator == 'like':
            return f"{expression} LIKE '%{value}%'"
        
        elif operator == 'not_like':
            return f"{expression} NOT LIKE '%{value}%'"
        
        elif operator == 'is_null':
            return f"{expression} IS NULL"
        
        elif operator == 'is_not_null':
            return f"{expression} IS NOT NULL"
        
        elif operator == 'between' and values and len(values) >= 2:
            if isinstance(values[0], str):
                return f"{expression} BETWEEN '{values[0]}' AND '{values[1]}'"
            else:
                return f"{expression} BETWEEN {values[0]} AND {values[1]}"
        
        return None
    
    @classmethod
    def _generate_cache_key(
        cls,
        tenant_id: str,
        dimensions: List[str],
        measures: List[str],
        filters: List[Dict],
        order_by: List[Dict],
        limit: int,
        offset: int,
    ) -> str:
        """Generate a cache key for a query."""
        key_data = {
            'tenant_id': tenant_id,
            'dimensions': sorted(dimensions),
            'measures': sorted(measures),
            'filters': filters,
            'order_by': order_by,
            'limit': limit,
            'offset': offset,
        }
        key_json = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.sha256(key_json.encode()).hexdigest()
    
    @classmethod
    def _get_from_cache(cls, cache_key: str) -> Optional[Dict]:
        """Get a query result from cache."""
        if cache_key in cls._query_cache:
            result, timestamp = cls._query_cache[cache_key]
            age = (datetime.utcnow() - timestamp).total_seconds()
            if age < cls._cache_ttl_seconds:
                return result
            else:
                del cls._query_cache[cache_key]
        return None
    
    @classmethod
    def _store_in_cache(cls, cache_key: str, result: Dict) -> None:
        """Store a query result in cache."""
        cls._query_cache[cache_key] = (result, datetime.utcnow())
        
        # Basic cache cleanup - limit to 1000 entries
        if len(cls._query_cache) > 1000:
            # Remove oldest entries
            sorted_keys = sorted(
                cls._query_cache.keys(),
                key=lambda k: cls._query_cache[k][1]
            )
            for key in sorted_keys[:100]:
                del cls._query_cache[key]
    
    @classmethod
    def clear_cache(cls, tenant_id: Optional[str] = None) -> int:
        """Clear the query cache."""
        if tenant_id:
            # Would need to track tenant in cache key for this
            count = len(cls._query_cache)
            cls._query_cache.clear()
            return count
        else:
            count = len(cls._query_cache)
            cls._query_cache.clear()
            return count
