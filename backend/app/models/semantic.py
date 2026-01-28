"""
NovaSight Semantic Layer Models
================================

Database models for the semantic layer: semantic models, dimensions, measures,
and relationships.

The semantic layer provides a business-friendly abstraction over the data warehouse,
enabling self-service analytics with governed metrics and dimensions.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.extensions import db
from app.models.mixins import TenantMixin, TimestampMixin


class DimensionType(str, Enum):
    """Types of dimensions in the semantic layer."""
    CATEGORICAL = "categorical"  # Discrete values (e.g., country, status)
    TEMPORAL = "temporal"        # Date/time dimensions
    NUMERIC = "numeric"          # Numeric ranges or bins
    HIERARCHICAL = "hierarchical"  # Part of a hierarchy


class AggregationType(str, Enum):
    """Supported aggregation types for measures."""
    SUM = "sum"
    COUNT = "count"
    COUNT_DISTINCT = "count_distinct"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    STDDEV = "stddev"
    VARIANCE = "variance"


class ModelType(str, Enum):
    """Types of semantic models."""
    FACT = "fact"           # Fact tables with measures
    DIMENSION = "dimension"  # Dimension tables
    AGGREGATE = "aggregate"  # Pre-aggregated tables


class RelationshipType(str, Enum):
    """Types of relationships between models."""
    ONE_TO_ONE = "one_to_one"
    ONE_TO_MANY = "one_to_many"
    MANY_TO_ONE = "many_to_one"
    MANY_TO_MANY = "many_to_many"


class SemanticModel(TenantMixin, TimestampMixin, db.Model):
    """
    Represents a semantic model (fact/dimension table).
    
    Semantic models are the core entities in the semantic layer, representing
    either fact tables (with measures) or dimension tables (with dimensions).
    """
    __tablename__ = 'semantic_models'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    label = Column(String(100), nullable=True)  # Human-readable name
    description = Column(Text, nullable=True)
    
    # Reference to underlying dbt model
    dbt_model = Column(String(100), nullable=False)
    
    # Model type
    model_type = Column(
        SQLEnum(ModelType),
        default=ModelType.FACT,
        nullable=False
    )
    
    # Target table in ClickHouse
    target_schema = Column(String(100), nullable=True)
    target_table = Column(String(100), nullable=True)
    
    # Cache settings
    cache_enabled = Column(Boolean, default=True)
    cache_ttl_seconds = Column(Integer, default=3600)  # 1 hour default
    
    # Metadata
    tags = Column(ARRAY(String), default=[])
    meta = Column(JSONB, default={})
    
    # Active flag
    is_active = Column(Boolean, default=True)
    
    # Relationships
    dimensions = relationship(
        'Dimension',
        backref='semantic_model',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    measures = relationship(
        'Measure',
        backref='semantic_model',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    # Unique name per tenant
    __table_args__ = (
        db.UniqueConstraint('tenant_id', 'name', name='uq_semantic_model_tenant_name'),
    )
    
    def __repr__(self):
        return f"<SemanticModel {self.name}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "dbt_model": self.dbt_model,
            "model_type": self.model_type.value if self.model_type else None,
            "target_schema": self.target_schema,
            "target_table": self.target_table,
            "cache_enabled": self.cache_enabled,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "tags": self.tags or [],
            "meta": self.meta or {},
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Dimension(TenantMixin, TimestampMixin, db.Model):
    """
    Represents a dimension in the semantic layer.
    
    Dimensions are attributes used for slicing and dicing data, such as
    date, geography, product category, etc.
    """
    __tablename__ = 'dimensions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Parent semantic model
    semantic_model_id = Column(
        UUID(as_uuid=True),
        ForeignKey('semantic_models.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # Identity
    name = Column(String(100), nullable=False)
    label = Column(String(100), nullable=True)  # Human-readable name
    description = Column(Text, nullable=True)
    
    # Type
    type = Column(
        SQLEnum(DimensionType),
        default=DimensionType.CATEGORICAL,
        nullable=False
    )
    
    # SQL expression for the dimension
    expression = Column(String(500), nullable=False)
    
    # Data type of the dimension
    data_type = Column(String(50), default='String')
    
    # Flags
    is_primary_key = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)  # Hide from UI
    is_filterable = Column(Boolean, default=True)
    is_groupable = Column(Boolean, default=True)
    
    # Hierarchy support for drill-down
    hierarchy_name = Column(String(100), nullable=True)
    hierarchy_level = Column(Integer, nullable=True)
    parent_dimension_id = Column(
        UUID(as_uuid=True),
        ForeignKey('dimensions.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # Default values and formatting
    default_value = Column(String(100), nullable=True)
    format_string = Column(String(100), nullable=True)  # e.g., "YYYY-MM-DD"
    
    # Metadata
    meta = Column(JSONB, default={})
    
    # Relationships
    children = relationship(
        'Dimension',
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic'
    )
    
    # Unique name per semantic model
    __table_args__ = (
        db.UniqueConstraint('semantic_model_id', 'name', name='uq_dimension_model_name'),
    )
    
    def __repr__(self):
        return f"<Dimension {self.name}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "semantic_model_id": str(self.semantic_model_id),
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "type": self.type.value if self.type else None,
            "expression": self.expression,
            "data_type": self.data_type,
            "is_primary_key": self.is_primary_key,
            "is_hidden": self.is_hidden,
            "is_filterable": self.is_filterable,
            "is_groupable": self.is_groupable,
            "hierarchy_name": self.hierarchy_name,
            "hierarchy_level": self.hierarchy_level,
            "parent_dimension_id": str(self.parent_dimension_id) if self.parent_dimension_id else None,
            "default_value": self.default_value,
            "format_string": self.format_string,
            "meta": self.meta or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Measure(TenantMixin, TimestampMixin, db.Model):
    """
    Represents a measure/metric in the semantic layer.
    
    Measures are quantitative values that can be aggregated, such as
    revenue, count of orders, average order value, etc.
    """
    __tablename__ = 'measures'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Parent semantic model
    semantic_model_id = Column(
        UUID(as_uuid=True),
        ForeignKey('semantic_models.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # Identity
    name = Column(String(100), nullable=False)
    label = Column(String(100), nullable=True)  # Human-readable name
    description = Column(Text, nullable=True)
    
    # Aggregation type
    aggregation = Column(
        SQLEnum(AggregationType),
        nullable=False
    )
    
    # SQL expression for the measure
    expression = Column(String(500), nullable=False)
    
    # Formatting
    format = Column(String(50), nullable=True)  # number, currency, percent
    format_string = Column(String(100), nullable=True)  # e.g., "$#,##0.00"
    decimal_places = Column(Integer, default=2)
    
    # Unit information
    unit = Column(String(50), nullable=True)  # e.g., "USD", "kg"
    unit_suffix = Column(String(20), nullable=True)
    
    # Flags
    is_hidden = Column(Boolean, default=False)
    is_additive = Column(Boolean, default=True)  # Can be summed across dimensions
    
    # Percentile-specific config
    percentile_value = Column(Integer, nullable=True)  # e.g., 95 for p95
    
    # Default filters to apply to this measure
    default_filters = Column(JSONB, default=[])
    
    # Time dimension for time-series calculations
    time_dimension = Column(String(100), nullable=True)
    
    # Metadata
    meta = Column(JSONB, default={})
    
    # Unique name per semantic model
    __table_args__ = (
        db.UniqueConstraint('semantic_model_id', 'name', name='uq_measure_model_name'),
    )
    
    def __repr__(self):
        return f"<Measure {self.name}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "semantic_model_id": str(self.semantic_model_id),
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "aggregation": self.aggregation.value if self.aggregation else None,
            "expression": self.expression,
            "format": self.format,
            "format_string": self.format_string,
            "decimal_places": self.decimal_places,
            "unit": self.unit,
            "unit_suffix": self.unit_suffix,
            "is_hidden": self.is_hidden,
            "is_additive": self.is_additive,
            "percentile_value": self.percentile_value,
            "default_filters": self.default_filters or [],
            "time_dimension": self.time_dimension,
            "meta": self.meta or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_sql_expression(self) -> str:
        """Generate the SQL aggregation expression."""
        expr = self.expression
        
        aggregation_map = {
            AggregationType.SUM: f"SUM({expr})",
            AggregationType.COUNT: f"COUNT({expr})",
            AggregationType.COUNT_DISTINCT: f"COUNT(DISTINCT {expr})",
            AggregationType.AVG: f"AVG({expr})",
            AggregationType.MIN: f"MIN({expr})",
            AggregationType.MAX: f"MAX({expr})",
            AggregationType.MEDIAN: f"median({expr})",
            AggregationType.PERCENTILE: f"quantile({(self.percentile_value or 50) / 100})({expr})",
            AggregationType.STDDEV: f"stddevPop({expr})",
            AggregationType.VARIANCE: f"varPop({expr})",
        }
        
        return aggregation_map.get(self.aggregation, f"SUM({expr})")


class Relationship(TenantMixin, db.Model):
    """
    Defines relationships between semantic models.
    
    Relationships enable automatic join generation when querying
    across multiple semantic models.
    """
    __tablename__ = 'semantic_relationships'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Source model (from)
    from_model_id = Column(
        UUID(as_uuid=True),
        ForeignKey('semantic_models.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # Target model (to)
    to_model_id = Column(
        UUID(as_uuid=True),
        ForeignKey('semantic_models.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # Join columns
    from_column = Column(String(100), nullable=False)
    to_column = Column(String(100), nullable=False)
    
    # Relationship type
    relationship_type = Column(
        SQLEnum(RelationshipType),
        default=RelationshipType.MANY_TO_ONE,
        nullable=False
    )
    
    # Join type
    join_type = Column(String(20), default='LEFT')  # LEFT, INNER, FULL
    
    # Additional join conditions (optional)
    additional_conditions = Column(Text, nullable=True)
    
    # Flags
    is_active = Column(Boolean, default=True)
    
    # Relationships
    from_model = relationship(
        'SemanticModel',
        foreign_keys=[from_model_id],
        backref='outgoing_relationships'
    )
    to_model = relationship(
        'SemanticModel',
        foreign_keys=[to_model_id],
        backref='incoming_relationships'
    )
    
    def __repr__(self):
        return f"<Relationship {self.from_model_id} -> {self.to_model_id}>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "from_model_id": str(self.from_model_id),
            "to_model_id": str(self.to_model_id),
            "from_column": self.from_column,
            "to_column": self.to_column,
            "relationship_type": self.relationship_type.value if self.relationship_type else None,
            "join_type": self.join_type,
            "additional_conditions": self.additional_conditions,
            "is_active": self.is_active,
        }
    
    def get_join_sql(self, from_alias: str, to_alias: str) -> str:
        """Generate the SQL join clause."""
        join_clause = f"{self.join_type} JOIN {to_alias} ON {from_alias}.{self.from_column} = {to_alias}.{self.to_column}"
        
        if self.additional_conditions:
            join_clause += f" AND {self.additional_conditions}"
        
        return join_clause
