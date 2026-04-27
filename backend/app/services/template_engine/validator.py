"""
NovaSight Template Engine - Parameter Validators
=================================================

Pydantic models for validating template parameters.
Implements strict validation to prevent injection attacks.
"""

import re
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Literal, Optional, Set, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# =============================================================================
# SQL Validators
# =============================================================================

class TenantSchemaDefinition(BaseModel):
    """Validates tenant schema creation parameters."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant UUID"
    )
    tenant_slug: str = Field(
        ...,
        min_length=1,
        max_length=63,
        description="Tenant slug for schema naming"
    )
    
    @field_validator('tenant_slug')
    @classmethod
    def validate_tenant_slug(cls, v: str) -> str:
        """Validate that the slug is a safe identifier."""
        pattern = r'^[a-z][a-z0-9_-]*$'
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid tenant slug '{v}'. Must start with a lowercase letter "
                "and contain only lowercase letters, numbers, underscores, and hyphens."
            )
        return v


class SQLIdentifier(BaseModel):
    """Validates SQL identifiers (table/column names)."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(
        ...,
        min_length=1,
        max_length=63,
        description="SQL identifier (table/column name)"
    )
    
    @field_validator('name')
    @classmethod
    def validate_sql_identifier(cls, v: str) -> str:
        """Validate that the name is a safe SQL identifier."""
        pattern = r'^[a-z][a-z0-9_]*$'
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid SQL identifier '{v}'. Must start with a lowercase letter "
                "and contain only lowercase letters, numbers, and underscores."
            )
        
        # Check for SQL reserved words
        reserved = {
            'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'table', 'index', 'database', 'schema', 'user', 'grant', 'revoke',
            'from', 'where', 'and', 'or', 'not', 'null', 'true', 'false',
            'order', 'group', 'having', 'limit', 'offset', 'join', 'on',
            'primary', 'foreign', 'key', 'references', 'cascade', 'constraint'
        }
        if v.lower() in reserved:
            raise ValueError(f"'{v}' is a SQL reserved word and cannot be used as an identifier.")
        
        return v


class ColumnDefinition(BaseModel):
    """Validated column definition for table templates."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, max_length=63)
    type: str = Field(..., description="SQL data type")
    nullable: bool = Field(default=True)
    default: Optional[str] = Field(default=None, description="Default value expression")
    primary_key: bool = Field(default=False)
    unique: bool = Field(default=False)
    description: Optional[str] = Field(default=None, max_length=500)
    
    # Allowed base types for PostgreSQL
    ALLOWED_TYPES: ClassVar[Set[str]] = {
        'UUID', 'VARCHAR', 'TEXT', 'INTEGER', 'BIGINT', 'SMALLINT',
        'BOOLEAN', 'TIMESTAMP', 'TIMESTAMPTZ', 'DATE', 'TIME',
        'JSONB', 'JSON', 'NUMERIC', 'DECIMAL', 'REAL', 'DOUBLE',
        'BYTEA', 'SERIAL', 'BIGSERIAL', 'ARRAY', 'INET', 'CIDR'
    }
    
    @field_validator('name')
    @classmethod
    def validate_column_name(cls, v: str) -> str:
        """Validate column name format."""
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(
                f"Invalid column name '{v}'. Must start with a lowercase letter "
                "and contain only lowercase letters, numbers, and underscores."
            )
        return v
    
    @field_validator('type')
    @classmethod
    def validate_column_type(cls, v: str) -> str:
        """Validate that the type is an allowed SQL type."""
        # Extract base type (handle VARCHAR(255), NUMERIC(10,2), etc.)
        base_type = re.split(r'[\(\[]', v.upper())[0].strip()
        
        # Handle TIMESTAMP WITH TIME ZONE
        if 'TIMESTAMP' in v.upper():
            base_type = 'TIMESTAMP'
        
        # Handle DOUBLE PRECISION
        if 'DOUBLE' in v.upper():
            base_type = 'DOUBLE'
        
        if base_type not in cls.ALLOWED_TYPES:
            raise ValueError(
                f"Invalid column type '{v}'. Allowed types: {', '.join(sorted(cls.ALLOWED_TYPES))}"
            )
        return v
    
    @field_validator('default')
    @classmethod
    def validate_default(cls, v: Optional[str]) -> Optional[str]:
        """Validate default value expression (basic safety check)."""
        if v is None:
            return v
        
        # Block potentially dangerous patterns
        dangerous = ['--', ';', 'drop', 'delete', 'truncate', 'exec', 'execute']
        lower_v = v.lower()
        for pattern in dangerous:
            if pattern in lower_v:
                raise ValueError(f"Default value contains potentially dangerous pattern: {pattern}")
        
        return v


class IndexDefinition(BaseModel):
    """Index definition for table templates."""
    
    name: str = Field(..., min_length=1, max_length=63)
    columns: List[str] = Field(..., min_length=1)
    unique: bool = Field(default=False)
    method: Literal['btree', 'hash', 'gist', 'gin', 'spgist', 'brin'] = Field(default='btree')
    where: Optional[str] = Field(default=None, description="Partial index condition")
    
    @field_validator('name')
    @classmethod
    def validate_index_name(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Invalid index name '{v}'")
        return v
    
    @field_validator('columns')
    @classmethod
    def validate_columns(cls, v: List[str]) -> List[str]:
        for col in v:
            if not re.match(r'^[a-z][a-z0-9_]*$', col):
                raise ValueError(f"Invalid column name in index: '{col}'")
        return v


class TableDefinition(BaseModel):
    """Complete table definition for SQL templates."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    table_name: str = Field(..., min_length=1, max_length=63)
    schema_name: str = Field(default="public", min_length=1, max_length=63)
    columns: List[ColumnDefinition] = Field(..., min_length=1)
    indexes: List[IndexDefinition] = Field(default_factory=list)
    tenant_aware: bool = Field(default=True, description="Add tenant_id column")
    description: Optional[str] = Field(default=None, max_length=1000)
    
    @field_validator('table_name')
    @classmethod
    def validate_table_name(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Invalid table name '{v}'")
        return v
    
    @field_validator('schema_name')
    @classmethod
    def validate_schema_name(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Invalid schema name '{v}'")
        return v
    
    @model_validator(mode='after')
    def validate_table(self) -> 'TableDefinition':
        """Validate table-level constraints."""
        # Ensure at least one primary key if tenant_aware
        pk_columns = [c for c in self.columns if c.primary_key]
        if self.tenant_aware and not pk_columns:
            raise ValueError("Tenant-aware tables must have at least one primary key column")
        
        # Check for duplicate column names
        names = [c.name for c in self.columns]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate column names detected")
        
        return self


# =============================================================================
# dbt Validators
# =============================================================================

class DbtColumnDefinition(BaseModel):
    """Column definition for dbt models."""
    
    name: str = Field(..., min_length=1, max_length=63)
    description: Optional[str] = Field(default=None)
    tests: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Invalid dbt column name '{v}'")
        return v
    
    @field_validator('tests')
    @classmethod
    def validate_tests(cls, v: List[str]) -> List[str]:
        allowed_tests = {
            'unique', 'not_null', 'accepted_values', 'relationships',
            'dbt_utils.unique_combination_of_columns', 'dbt_utils.expression_is_true'
        }
        for test in v:
            # Extract test name (handle tests with arguments)
            test_name = test.split(':')[0].split('(')[0].strip()
            if test_name not in allowed_tests and not test_name.startswith('dbt_'):
                raise ValueError(f"Unknown or disallowed dbt test: '{test_name}'")
        return v


class DbtModelDefinition(BaseModel):
    """Definition for dbt model templates."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    model_name: str = Field(..., min_length=1, max_length=63)
    description: Optional[str] = Field(default=None, max_length=2000)
    materialized: Literal['view', 'table', 'incremental', 'ephemeral'] = Field(default='view')
    schema_name: Optional[str] = Field(default=None, alias="schema")
    columns: List[DbtColumnDefinition] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    # Source table reference
    source_name: Optional[str] = Field(default=None)
    source_table: Optional[str] = Field(default=None)
    
    # Incremental config
    unique_key: Optional[Union[str, List[str]]] = Field(default=None)
    incremental_strategy: Literal['append', 'delete+insert', 'merge'] = Field(default='append')
    
    @field_validator('model_name')
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Invalid dbt model name '{v}'")
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        for tag in v:
            if not re.match(r'^[a-z][a-z0-9_-]*$', tag):
                raise ValueError(f"Invalid tag '{tag}'. Tags must be lowercase alphanumeric with hyphens/underscores.")
        return v


# =============================================================================
# Pipeline Validators
# =============================================================================

class PipelineTaskDefinition(BaseModel):
    """Task definition for pipeline templates."""
    
    task_id: str = Field(..., min_length=1, max_length=250)
    task_type: Literal[
        'dlt_run', 'dbt_run', 'dbt_test', 'dbt_run_lake', 'dbt_run_warehouse'
    ] = Field(...)
    config: Dict[str, Any] = Field(default_factory=dict)
    upstream_tasks: List[str] = Field(default_factory=list)
    timeout_minutes: int = Field(default=60, ge=1, le=1440)
    retries: int = Field(default=3, ge=0, le=10)
    retry_delay_minutes: int = Field(default=5, ge=1, le=60)
    trigger_rule: Literal[
        'all_success', 'all_failed', 'all_done', 'one_success',
        'one_failed', 'none_failed', 'none_skipped', 'dummy'
    ] = Field(default='all_success')
    
    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Invalid task_id '{v}'. Must be lowercase alphanumeric with underscores.")
        return v


class PipelineDefaultArgs(BaseModel):
    """Default arguments for pipeline job."""
    
    retries: int = Field(default=3, ge=0, le=10)
    retry_delay_minutes: int = Field(default=5, ge=1, le=60)
    email: Optional[List[str]] = Field(default=None)
    email_on_failure: bool = Field(default=False)
    email_on_success: bool = Field(default=False)
    
    @field_validator('email')
    @classmethod
    def validate_emails(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        for email in v:
            if not re.match(email_pattern, email):
                raise ValueError(f"Invalid email address: '{email}'")
        return v


class PipelineJobDefinition(BaseModel):
    """Complete job definition for pipeline templates."""
    
    dag_id: str = Field(..., min_length=1, max_length=250)
    description: str = Field(default="", max_length=2000)
    schedule: Optional[str] = Field(default=None)
    start_date: datetime = Field(...)
    catchup: bool = Field(default=False)
    max_active_runs: int = Field(default=1, ge=1, le=10)
    default_args: PipelineDefaultArgs = Field(default_factory=PipelineDefaultArgs)
    tags: List[str] = Field(default_factory=list)
    tasks: List[PipelineTaskDefinition] = Field(..., min_length=1)
    
    @field_validator('dag_id')
    @classmethod
    def validate_dag_id(cls, v: str) -> str:
        # DAG IDs are more flexible but still need validation
        if not re.match(r'^[a-z][a-z0-9_.-]*$', v):
            raise ValueError(f"Invalid dag_id '{v}'. Must start with lowercase letter, contain only lowercase letters, numbers, underscores, hyphens, and periods.")
        return v
    
    @field_validator('schedule')
    @classmethod
    def validate_schedule(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        
        # Allow schedule presets
        presets = {'@once', '@hourly', '@daily', '@weekly', '@monthly', '@yearly', 'None'}
        if v in presets:
            return v
        
        # Validate cron expression (basic check)
        cron_pattern = r'^(\S+\s+){4}\S+$'
        if not re.match(cron_pattern, v):
            raise ValueError(f"Invalid schedule '{v}'. Must be a valid cron expression or schedule preset.")
        
        return v
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        for tag in v:
            if not re.match(r'^[a-z][a-z0-9_-]*$', tag):
                raise ValueError(f"Invalid tag '{tag}'")
        return v
    
    @model_validator(mode='after')
    def validate_dag(self) -> 'PipelineJobDefinition':
        """Validate DAG-level constraints."""
        # Check for duplicate task IDs
        task_ids = [t.task_id for t in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Duplicate task_ids detected in DAG")
        
        # Validate upstream references exist
        valid_ids = set(task_ids)
        for task in self.tasks:
            for upstream in task.upstream_tasks:
                if upstream not in valid_ids:
                    raise ValueError(f"Task '{task.task_id}' references unknown upstream task '{upstream}'")
        
        return self


# =============================================================================
# ClickHouse Validators
# =============================================================================

class ClickHouseColumnDefinition(BaseModel):
    """Column definition for ClickHouse tables."""
    
    name: str = Field(..., min_length=1, max_length=63)
    type: str = Field(...)
    nullable: bool = Field(default=False)  # ClickHouse columns non-nullable by default
    default: Optional[str] = Field(default=None)
    codec: Optional[str] = Field(default=None, description="Compression codec")
    ttl: Optional[str] = Field(default=None, description="TTL expression")
    
    ALLOWED_TYPES: ClassVar[Set[str]] = {
        'UInt8', 'UInt16', 'UInt32', 'UInt64', 'UInt128', 'UInt256',
        'Int8', 'Int16', 'Int32', 'Int64', 'Int128', 'Int256',
        'Float32', 'Float64', 'Decimal', 'Decimal32', 'Decimal64', 'Decimal128',
        'String', 'FixedString', 'UUID', 'Date', 'Date32', 'DateTime', 'DateTime64',
        'Enum8', 'Enum16', 'Array', 'Tuple', 'Map', 'Nested', 'Nullable',
        'LowCardinality', 'AggregateFunction', 'SimpleAggregateFunction', 'IPv4', 'IPv6'
    }
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Invalid ClickHouse column name '{v}'")
        return v
    
    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        # Extract base type
        base_type = re.match(r'^(\w+)', v)
        if base_type:
            type_name = base_type.group(1)
            if type_name not in cls.ALLOWED_TYPES:
                raise ValueError(f"Invalid ClickHouse type '{type_name}'")
        return v


class ClickHouseTableDefinition(BaseModel):
    """Definition for ClickHouse table templates."""
    
    table_name: str = Field(..., min_length=1, max_length=63)
    database: str = Field(default="default", min_length=1, max_length=63)
    columns: List[ClickHouseColumnDefinition] = Field(..., min_length=1)
    engine: str = Field(default="MergeTree")
    order_by: List[str] = Field(...)
    partition_by: Optional[str] = Field(default=None)
    primary_key: Optional[List[str]] = Field(default=None)
    sample_by: Optional[str] = Field(default=None)
    ttl: Optional[str] = Field(default=None)
    settings: Dict[str, str] = Field(default_factory=dict)
    tenant_aware: bool = Field(default=True)
    
    ALLOWED_ENGINES: ClassVar[Set[str]] = {
        'MergeTree', 'ReplacingMergeTree', 'SummingMergeTree', 'AggregatingMergeTree',
        'CollapsingMergeTree', 'VersionedCollapsingMergeTree', 'GraphiteMergeTree',
        'ReplicatedMergeTree', 'ReplicatedReplacingMergeTree', 'Log', 'TinyLog', 'StripeLog',
        'Memory', 'Buffer', 'Distributed', 'MaterializedView', 'Null', 'URL', 'JDBC'
    }
    
    @field_validator('table_name', 'database')
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Invalid identifier '{v}'")
        return v
    
    @field_validator('engine')
    @classmethod
    def validate_engine(cls, v: str) -> str:
        # Extract base engine name
        base_engine = v.split('(')[0].strip()
        if base_engine not in cls.ALLOWED_ENGINES:
            raise ValueError(f"Invalid ClickHouse engine '{base_engine}'")
        return v
    
    @field_validator('order_by')
    @classmethod
    def validate_order_by(cls, v: List[str]) -> List[str]:
        for col in v:
            if not re.match(r'^[a-z][a-z0-9_]*$', col):
                raise ValueError(f"Invalid column in ORDER BY: '{col}'")
        return v


class ClickHouseTenantDatabaseDefinition(BaseModel):
    """Definition for ClickHouse tenant database templates."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    tenant_id: str = Field(..., description="Tenant UUID")
    tenant_slug: str = Field(
        ...,
        min_length=1,
        max_length=63,
        description="Tenant slug for database naming"
    )
    retention_days: Optional[int] = Field(default=730, ge=1)
    buffer_settings: Optional[Dict[str, Any]] = Field(default=None)
    
    @field_validator('tenant_slug')
    @classmethod
    def validate_tenant_slug(cls, v: str) -> str:
        """Validate that the slug is a safe identifier."""
        pattern = r'^[a-z][a-z0-9_-]*$'
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid tenant slug '{v}'. Must start with a lowercase letter "
                "and contain only lowercase letters, numbers, underscores, and hyphens."
            )
        return v


# =============================================================================
# PySpark Validators
# =============================================================================

class PySparkConnectionDefinition(BaseModel):
    """Validated connection configuration for PySpark templates."""
    
    model_config = ConfigDict(str_strip_whitespace=True, extra='allow', populate_by_name=True)
    
    host: str = Field(..., min_length=1)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1)
    username: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)  # Injected at runtime
    db_type: str = Field(default="postgresql")
    id: Optional[str] = Field(default=None)
    schema_name: Optional[str] = Field(default=None, alias="schema")


class PySparkSourceDefinition(BaseModel):
    """Validated source configuration for PySpark templates."""
    
    model_config = ConfigDict(str_strip_whitespace=True, extra='allow', populate_by_name=True)
    
    type: str = Field(..., pattern=r'^(table|query)$')
    schema_name: Optional[str] = Field(default=None, alias="schema")
    table: Optional[str] = Field(default=None)
    query: Optional[str] = Field(default=None)


class PySparkColumnDefinition(BaseModel):
    """Validated column configuration for PySpark templates."""
    
    model_config = ConfigDict(str_strip_whitespace=True, extra='allow')
    
    name: str = Field(..., min_length=1)
    data_type: Optional[str] = Field(default=None)
    alias: Optional[str] = Field(default=None)
    nullable: bool = Field(default=True)
    include: bool = Field(default=True)


class PySparkCDCDefinition(BaseModel):
    """Validated CDC configuration for PySpark templates."""
    
    model_config = ConfigDict(str_strip_whitespace=True, extra='allow')
    
    type: Optional[str] = Field(default="none")
    column: Optional[str] = Field(default=None)


class PySparkTargetDefinition(BaseModel):
    """Validated target configuration for PySpark templates."""
    
    model_config = ConfigDict(str_strip_whitespace=True, extra='allow')
    
    database: str = Field(..., min_length=1)
    table: str = Field(..., min_length=1)
    engine: str = Field(default="MergeTree")
    write_mode: Optional[str] = Field(default="append")


class PySparkExtractJobDefinition(BaseModel):
    """Validates PySpark extract job template parameters."""
    
    model_config = ConfigDict(str_strip_whitespace=True, extra='allow')
    
    app_name: str = Field(..., min_length=1)
    app_id: str = Field(...)
    tenant_id: str = Field(...)
    connection: PySparkConnectionDefinition
    source: PySparkSourceDefinition
    columns: List[PySparkColumnDefinition]
    primary_keys: List[str] = Field(default_factory=list)
    cdc: Optional[PySparkCDCDefinition] = Field(default=None)
    partitions: List[str] = Field(default_factory=list)
    target: PySparkTargetDefinition
    options: Dict[str, Any] = Field(default_factory=dict)
    generated_at: Optional[str] = Field(default=None)
    template_version: Optional[str] = Field(default=None)
    scd_type: Optional[str] = Field(default=None)
    write_mode: Optional[str] = Field(default=None)


class PySparkSCD1JobDefinition(PySparkExtractJobDefinition):
    """Validates PySpark SCD Type 1 template parameters."""
    
    primary_keys: List[str] = Field(default_factory=list)


class PySparkSCD2JobDefinition(PySparkExtractJobDefinition):
    """Validates PySpark SCD Type 2 template parameters."""
    
    primary_keys: List[str] = Field(default_factory=list)


# =============================================================================
# Generic Parameter Validator
# =============================================================================

class TemplateParameterValidator:
    """
    Generic validator for template parameters using Pydantic models.
    Maps template names to their parameter schemas.
    """
    
    SCHEMA_MAP = {
        'sql/create_table.sql.j2': TableDefinition,
        'sql/create_index.sql.j2': IndexDefinition,
        'sql/tenant_schema.sql.j2': TenantSchemaDefinition,
        'dbt/model.sql.j2': DbtModelDefinition,
        'dbt/schema.yml.j2': DbtModelDefinition,
        'clickhouse/create_table.sql.j2': ClickHouseTableDefinition,
        'clickhouse/tenant_database.sql.j2': ClickHouseTenantDatabaseDefinition,
        'pyspark/extract_job.py.j2': PySparkExtractJobDefinition,
        'pyspark/scd_type1.py.j2': PySparkSCD1JobDefinition,
        'pyspark/scd_type2.py.j2': PySparkSCD2JobDefinition,
    }
    
    @classmethod
    def get_schema(cls, template_name: str) -> Optional[type]:
        """Get the Pydantic schema for a template."""
        return cls.SCHEMA_MAP.get(template_name)
    
    @classmethod
    def validate(cls, template_name: str, parameters: Dict[str, Any]) -> BaseModel:
        """
        Validate parameters for a template.
        
        Args:
            template_name: Name of the template
            parameters: Parameters to validate
            
        Returns:
            Validated Pydantic model
            
        Raises:
            ValueError: If template has no schema or validation fails
        """
        schema = cls.get_schema(template_name)
        if schema is None:
            raise ValueError(f"No schema defined for template '{template_name}'")
        
        return schema(**parameters)
    
    @classmethod
    def register_schema(cls, template_name: str, schema: type) -> None:
        """Register a new schema for a template."""
        if not issubclass(schema, BaseModel):
            raise TypeError("Schema must be a Pydantic BaseModel subclass")
        cls.SCHEMA_MAP[template_name] = schema
