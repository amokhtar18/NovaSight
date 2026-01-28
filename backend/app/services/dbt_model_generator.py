"""
NovaSight dbt Model Generator Service
======================================

Automated dbt model generation from data source schemas using templates.
Implements generation of staging, intermediate, and marts models.

This service follows the Template Engine Rule (ADR-002):
All generated code comes from pre-approved Jinja2 templates only.
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from app.models.data_source import DataSourceTable, DataSourceColumn, DataSourceSchema
from app.services.template_engine import TemplateEngine, template_engine
from app.utils.naming import to_snake_case

logger = logging.getLogger(__name__)


class DbtModelGeneratorError(Exception):
    """Base exception for dbt model generator errors."""
    pass


class ModelGenerationError(DbtModelGeneratorError):
    """Raised when model generation fails."""
    pass


class TemplateNotFoundError(DbtModelGeneratorError):
    """Raised when a required template is not found."""
    pass


class DbtModelGenerator:
    """
    Generates dbt models from data source schemas.
    
    This generator creates:
    - Staging models: 1:1 with source tables, minimal transformations
    - Intermediate models: Business logic, joins, aggregations
    - Marts models: Final business entities and facts for BI tools
    
    All models are generated from pre-approved Jinja2 templates.
    
    Usage:
        generator = DbtModelGenerator(template_engine, '/path/to/dbt')
        result = generator.generate_staging_model(table, 'salesforce')
    """
    
    # Type mapping from source database types to ClickHouse types
    TYPE_MAPPING: Dict[str, str] = {
        # String types
        'varchar': 'String',
        'text': 'String',
        'char': 'String',
        'character varying': 'String',
        'character': 'String',
        'nvarchar': 'String',
        'nchar': 'String',
        'ntext': 'String',
        'clob': 'String',
        'longtext': 'String',
        'mediumtext': 'String',
        'tinytext': 'String',
        
        # Numeric types - Integer
        'integer': 'Int32',
        'int': 'Int32',
        'int4': 'Int32',
        'bigint': 'Int64',
        'int8': 'Int64',
        'smallint': 'Int16',
        'int2': 'Int16',
        'tinyint': 'Int8',
        'serial': 'Int32',
        'bigserial': 'Int64',
        'smallserial': 'Int16',
        
        # Numeric types - Floating point
        'real': 'Float32',
        'float4': 'Float32',
        'float': 'Float64',
        'double': 'Float64',
        'double precision': 'Float64',
        'float8': 'Float64',
        'numeric': 'Float64',
        'decimal': 'Decimal',
        'money': 'Decimal64(4)',
        'number': 'Float64',
        
        # Boolean
        'boolean': 'UInt8',
        'bool': 'UInt8',
        'bit': 'UInt8',
        
        # Date/Time types
        'date': 'Date',
        'time': 'String',  # ClickHouse doesn't have native TIME
        'timestamp': 'DateTime',
        'timestamp without time zone': 'DateTime',
        'timestamp with time zone': 'DateTime64(3)',
        'timestamptz': 'DateTime64(3)',
        'datetime': 'DateTime',
        'datetime2': 'DateTime64(3)',
        'datetimeoffset': 'DateTime64(3)',
        'smalldatetime': 'DateTime',
        'interval': 'Int64',  # Store as seconds
        
        # Binary types
        'bytea': 'String',
        'blob': 'String',
        'binary': 'String',
        'varbinary': 'String',
        'image': 'String',
        
        # JSON types
        'json': 'String',
        'jsonb': 'String',
        
        # UUID
        'uuid': 'UUID',
        'uniqueidentifier': 'UUID',
        
        # Array (generic)
        'array': 'Array(String)',
        
        # Geographic (store as JSON strings)
        'geometry': 'String',
        'geography': 'String',
        'point': 'String',
        
        # XML
        'xml': 'String',
        
        # Default
        'unknown': 'String',
    }
    
    # Standard dbt tests for specific column patterns
    COLUMN_TEST_PATTERNS: Dict[str, List[str]] = {
        r'^id$': ['unique', 'not_null'],
        r'_id$': ['not_null'],
        r'^email$': ['not_null'],
        r'^status$': ['not_null'],
        r'^type$': ['not_null'],
        r'^created_at$': ['not_null'],
        r'^updated_at$': ['not_null'],
        r'^tenant_id$': ['not_null'],
    }
    
    def __init__(
        self,
        template_eng: Optional[TemplateEngine] = None,
        dbt_path: Optional[str] = None,
    ):
        """
        Initialize the dbt model generator.
        
        Args:
            template_eng: Template engine instance. Uses singleton if not provided.
            dbt_path: Path to the dbt project directory. Defaults to ./dbt
        """
        self.template_engine = template_eng or template_engine
        
        if dbt_path:
            self.dbt_path = Path(dbt_path)
        else:
            # Default to project root dbt directory
            self.dbt_path = Path(__file__).parent.parent.parent.parent / 'dbt'
        
        logger.info(f"DbtModelGenerator initialized with dbt_path: {self.dbt_path}")
    
    # =========================================================================
    # Staging Model Generation
    # =========================================================================
    
    def generate_staging_model(
        self,
        table: DataSourceTable,
        source_name: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Generate a staging model and schema for a table.
        
        Staging models are 1:1 with source tables and include:
        - Column renaming to snake_case
        - Type casting to ClickHouse types
        - Basic schema documentation
        
        Args:
            table: Data source table definition
            source_name: Name of the source (e.g., 'salesforce', 'postgres')
            options: Optional configuration:
                - materialization: 'view' (default), 'table', 'ephemeral'
                - include_metadata: Add _loaded_at, _source columns
                - generate_tests: Auto-generate column tests (default: True)
        
        Returns:
            Dictionary with paths to generated files:
                - model_path: Path to the SQL model file
                - schema_path: Path to the schema YAML file
        
        Raises:
            ModelGenerationError: If generation fails
        """
        options = options or {}
        
        # Validate inputs
        source_name_clean = self._sanitize_identifier(source_name)
        table_name_clean = self._sanitize_identifier(table.name)
        
        model_name = f"stg_{source_name_clean}__{table_name_clean}"
        
        logger.info(f"Generating staging model: {model_name}")
        
        # Prepare column definitions
        columns = self._prepare_staging_columns(table, options)
        
        # Determine primary key
        primary_key = None
        for col in table.columns:
            if col.primary_key:
                primary_key = self._sanitize_identifier(col.name)
                break
        
        # Build template context
        template_context = {
            'model_name': model_name,
            'description': table.description or f"Staging model for {table.source_name}",
            'source_name': source_name_clean,
            'source_table': table.source_name or table.name,
            'columns': columns,
            'materialization': options.get('materialization', 'view'),
            'primary_key': primary_key,
            'tenant_column': options.get('tenant_column', 'tenant_id'),
            '_generated_at': datetime.utcnow().isoformat(),
            '_template_version': '1.0.0',
        }
        
        # Add metadata columns if requested
        if options.get('include_metadata', False):
            template_context['include_metadata'] = True
        
        try:
            # Generate model SQL
            model_sql = self.template_engine.render(
                'dbt/staging_model.sql.j2',
                template_context
            )
            
            # Generate schema YAML
            schema_yaml = self.template_engine.render(
                'dbt/schema.yml.j2',
                {
                    'model_name': model_name,
                    'description': template_context['description'],
                    'columns': columns,
                    'tags': ['staging', source_name_clean],
                    '_generated_at': datetime.utcnow().isoformat(),
                    '_template_version': '1.0.0',
                }
            )
        except Exception as e:
            logger.error(f"Template rendering failed for {model_name}: {e}")
            raise ModelGenerationError(f"Failed to render templates: {e}")
        
        # Write files
        model_dir = self.dbt_path / 'models' / 'staging' / source_name_clean
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_file = model_dir / f'{model_name}.sql'
        schema_file = model_dir / f'{model_name}.yml'
        
        try:
            model_file.write_text(model_sql, encoding='utf-8')
            schema_file.write_text(schema_yaml, encoding='utf-8')
        except IOError as e:
            logger.error(f"Failed to write model files: {e}")
            raise ModelGenerationError(f"Failed to write files: {e}")
        
        logger.info(f"Generated staging model: {model_file}")
        
        return {
            'model_path': str(model_file),
            'schema_path': str(schema_file),
            'model_name': model_name,
        }
    
    def generate_source_yaml(
        self,
        source_name: str,
        database: str,
        tables: List[DataSourceTable],
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate sources.yml for a data source.
        
        The sources.yml file defines the raw data sources that dbt models
        read from, including freshness checks and documentation.
        
        Args:
            source_name: Name of the source (e.g., 'salesforce')
            database: Database name
            tables: List of tables in the source
            options: Optional configuration:
                - schema: Schema name (default: 'raw')
                - freshness_warn_hours: Hours before freshness warning (default: 24)
                - freshness_error_hours: Hours before freshness error (default: 48)
                - loaded_at_field: Column for freshness checks (default: 'ingested_at')
        
        Returns:
            Path to the generated sources.yml file
        
        Raises:
            ModelGenerationError: If generation fails
        """
        options = options or {}
        
        source_name_clean = self._sanitize_identifier(source_name)
        
        logger.info(f"Generating sources.yml for: {source_name_clean}")
        
        # Prepare table definitions
        table_defs = []
        for table in tables:
            table_def = {
                'name': table.source_name or table.name,
                'description': table.description or '',
                'identifier': table.source_name if table.source_name != table.name else None,
                'loaded_at_field': options.get('loaded_at_field', 'ingested_at'),
                'freshness': {
                    'warn_after': {
                        'count': options.get('freshness_warn_hours', 24),
                        'period': 'hour',
                    },
                    'error_after': {
                        'count': options.get('freshness_error_hours', 48),
                        'period': 'hour',
                    },
                },
                'columns': [
                    {
                        'name': col.source_name or col.name,
                        'description': col.description or '',
                    }
                    for col in table.columns
                ],
            }
            table_defs.append(table_def)
        
        # Build template context
        template_context = {
            'source_name': source_name_clean,
            'database': database,
            'schema': options.get('schema', 'raw'),
            'description': options.get('description', f'Data source: {source_name}'),
            'loader': options.get('loader', 'NovaSight Ingestion'),
            'tables': table_defs,
            'meta': {
                'owner': options.get('owner', 'data-engineering'),
                'source_type': options.get('source_type', 'database'),
            },
            '_generated_at': datetime.utcnow().isoformat(),
            '_template_version': '1.0.0',
        }
        
        try:
            source_yaml = self.template_engine.render(
                'dbt/sources.yml.j2',
                template_context
            )
        except Exception as e:
            logger.error(f"Template rendering failed for sources.yml: {e}")
            raise ModelGenerationError(f"Failed to render sources.yml: {e}")
        
        # Write file
        sources_dir = self.dbt_path / 'models' / 'staging' / source_name_clean
        sources_dir.mkdir(parents=True, exist_ok=True)
        
        sources_file = sources_dir / 'sources.yml'
        
        try:
            sources_file.write_text(source_yaml, encoding='utf-8')
        except IOError as e:
            logger.error(f"Failed to write sources.yml: {e}")
            raise ModelGenerationError(f"Failed to write sources.yml: {e}")
        
        logger.info(f"Generated sources.yml: {sources_file}")
        
        return str(sources_file)
    
    def generate_staging_layer(
        self,
        schema: DataSourceSchema,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate complete staging layer for a data source schema.
        
        This convenience method generates:
        - sources.yml for all tables
        - Staging model for each table
        - Schema YAML for each model
        
        Args:
            schema: Complete data source schema
            options: Generation options passed to individual generators
        
        Returns:
            Dictionary with generation results:
                - sources_file: Path to sources.yml
                - models: List of generated model info
                - errors: Any errors encountered
        """
        options = options or {}
        
        logger.info(f"Generating staging layer for source: {schema.source_name}")
        
        results = {
            'sources_file': None,
            'models': [],
            'errors': [],
        }
        
        # Generate sources.yml
        try:
            results['sources_file'] = self.generate_source_yaml(
                source_name=schema.source_name,
                database=schema.database,
                tables=schema.tables,
                options=options,
            )
        except ModelGenerationError as e:
            results['errors'].append({
                'type': 'sources',
                'error': str(e),
            })
        
        # Generate staging models for each table
        for table in schema.tables:
            try:
                model_result = self.generate_staging_model(
                    table=table,
                    source_name=schema.source_name,
                    options=options,
                )
                results['models'].append(model_result)
            except ModelGenerationError as e:
                results['errors'].append({
                    'type': 'model',
                    'table': table.name,
                    'error': str(e),
                })
        
        logger.info(
            f"Staging layer generation complete: "
            f"{len(results['models'])} models, {len(results['errors'])} errors"
        )
        
        return results
    
    # =========================================================================
    # Intermediate Model Generation
    # =========================================================================
    
    def generate_intermediate_model(
        self,
        name: str,
        description: str,
        source_models: List[Dict[str, Any]],
        columns: List[Dict[str, Any]],
        joins: Optional[List[Dict[str, Any]]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Generate an intermediate model with joins and transformations.
        
        Intermediate models combine staging models and apply business rules.
        
        Args:
            name: Model name (should start with 'int_')
            description: Model description
            source_models: List of source model references:
                - name: Model name (e.g., 'stg_salesforce__accounts')
                - alias: Optional alias for the CTE
                - where: Optional WHERE clause
            columns: Output column definitions:
                - name: Column name
                - source_alias: Source CTE alias
                - source_column: Source column name
                - expression: SQL expression (alternative to source_column)
                - alias: Output alias
            joins: Join definitions:
                - model: Model name to join
                - model_alias: Alias for joined model
                - type: Join type (LEFT, INNER, etc.)
                - left_key: Key from primary model
                - right_key: Key from joined model
                - additional_conditions: Extra join conditions
            options: Optional configuration:
                - materialization: 'view' (default), 'table', 'ephemeral'
                - tags: List of tags
        
        Returns:
            Dictionary with path to generated file
        
        Raises:
            ModelGenerationError: If generation fails
        """
        options = options or {}
        joins = joins or []
        
        # Validate model name
        if not name.startswith('int_'):
            logger.warning(f"Intermediate model name '{name}' should start with 'int_'")
        
        model_name = self._sanitize_identifier(name)
        
        logger.info(f"Generating intermediate model: {model_name}")
        
        # Build template context
        template_context = {
            'model_name': model_name,
            'description': description,
            'source_models': source_models,
            'columns': columns,
            'joins': joins,
            'materialized': options.get('materialization', 'view'),
            'tags': options.get('tags', []),
            'where_clause': options.get('where_clause'),
            'group_by': options.get('group_by', []),
            '_generated_at': datetime.utcnow().isoformat(),
            '_template_version': '1.0.0',
        }
        
        try:
            model_sql = self.template_engine.render(
                'dbt/intermediate_model.sql.j2',
                template_context
            )
        except Exception as e:
            logger.error(f"Template rendering failed for {model_name}: {e}")
            raise ModelGenerationError(f"Failed to render template: {e}")
        
        # Determine output directory
        subdomain = options.get('subdomain', 'core')
        model_dir = self.dbt_path / 'models' / 'intermediate' / subdomain
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_file = model_dir / f'{model_name}.sql'
        
        try:
            model_file.write_text(model_sql, encoding='utf-8')
        except IOError as e:
            logger.error(f"Failed to write model file: {e}")
            raise ModelGenerationError(f"Failed to write file: {e}")
        
        logger.info(f"Generated intermediate model: {model_file}")
        
        return {
            'model_path': str(model_file),
            'model_name': model_name,
        }
    
    # =========================================================================
    # Marts Model Generation
    # =========================================================================
    
    def generate_mart_model(
        self,
        name: str,
        description: str,
        source_models: List[Dict[str, Any]],
        columns: List[Dict[str, Any]],
        joins: Optional[List[Dict[str, Any]]] = None,
        metrics: Optional[List[Dict[str, Any]]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Optional[str]]:
        """
        Generate a mart model with business logic.
        
        Marts are the final layer consumed by BI tools and applications.
        They should be named with prefixes:
        - dim_: Dimension tables
        - fct_: Fact tables
        - rpt_: Report tables
        
        Args:
            name: Model name (should start with dim_, fct_, or rpt_)
            description: Model description
            source_models: List of source model references
            columns: Output column definitions
            joins: Join definitions
            metrics: Metric definitions for the semantic layer:
                - name: Metric name
                - type: count, sum, avg, min, max
                - expression: SQL expression
                - description: Metric description
            options: Optional configuration:
                - materialization: 'table' (default), 'incremental'
                - unique_key: For incremental models
                - incremental_strategy: 'merge', 'delete+insert', 'append'
                - partition_by: Partition column
                - cluster_by: List of cluster columns
                - schema: Target schema
        
        Returns:
            Dictionary with paths to generated files
        
        Raises:
            ModelGenerationError: If generation fails
        """
        options = options or {}
        joins = joins or []
        metrics = metrics or []
        
        # Validate model name prefix
        valid_prefixes = ('dim_', 'fct_', 'rpt_', 'mart_')
        if not any(name.startswith(p) for p in valid_prefixes):
            logger.warning(
                f"Mart model name '{name}' should start with one of: {valid_prefixes}"
            )
        
        model_name = self._sanitize_identifier(name)
        
        logger.info(f"Generating mart model: {model_name}")
        
        # Build template context
        template_context = {
            'model_name': model_name,
            'description': description,
            'source_models': source_models,
            'columns': columns,
            'joins': joins,
            'metrics': metrics,
            'materialized': options.get('materialization', 'table'),
            'unique_key': options.get('unique_key'),
            'incremental_strategy': options.get('incremental_strategy', 'merge'),
            'partition_by': options.get('partition_by'),
            'cluster_by': options.get('cluster_by', []),
            'schema': options.get('schema'),
            'where_clause': options.get('where_clause'),
            'group_by': options.get('group_by', []),
            '_generated_at': datetime.utcnow().isoformat(),
            '_template_version': '1.0.0',
        }
        
        try:
            model_sql = self.template_engine.render(
                'dbt/marts_model.sql.j2',
                template_context
            )
        except Exception as e:
            logger.error(f"Template rendering failed for {model_name}: {e}")
            raise ModelGenerationError(f"Failed to render template: {e}")
        
        # Determine output directory based on model prefix
        if name.startswith('dim_'):
            subdomain = 'dimensions'
        elif name.startswith('fct_'):
            subdomain = 'facts'
        elif name.startswith('rpt_'):
            subdomain = 'reports'
        else:
            subdomain = 'core'
        
        subdomain = options.get('subdomain', subdomain)
        model_dir = self.dbt_path / 'models' / 'marts' / subdomain
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_file = model_dir / f'{model_name}.sql'
        
        try:
            model_file.write_text(model_sql, encoding='utf-8')
        except IOError as e:
            logger.error(f"Failed to write model file: {e}")
            raise ModelGenerationError(f"Failed to write file: {e}")
        
        logger.info(f"Generated mart model: {model_file}")
        
        # Generate schema YAML if columns have tests or descriptions
        schema_path = None
        if any(col.get('tests') or col.get('description') for col in columns):
            try:
                schema_yaml = self.template_engine.render(
                    'dbt/schema.yml.j2',
                    {
                        'model_name': model_name,
                        'description': description,
                        'columns': columns,
                        'tags': ['marts', subdomain],
                        '_generated_at': datetime.utcnow().isoformat(),
                        '_template_version': '1.0.0',
                    }
                )
                schema_file = model_dir / f'{model_name}.yml'
                schema_file.write_text(schema_yaml, encoding='utf-8')
                schema_path = str(schema_file)
            except Exception as e:
                logger.warning(f"Failed to generate schema YAML: {e}")
        
        return {
            'model_path': str(model_file),
            'schema_path': schema_path,
            'model_name': model_name,
        }
    
    # =========================================================================
    # Metric Generation
    # =========================================================================
    
    def generate_metric_yaml(
        self,
        name: str,
        description: str,
        model: str,
        calculation: str,
        expression: str,
        dimensions: List[str],
        time_grains: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a metric YAML definition for the semantic layer.
        
        Args:
            name: Metric name
            description: Metric description
            model: Reference model name
            calculation: Calculation type (count, sum, avg, etc.)
            expression: SQL expression for the metric
            dimensions: List of dimension columns
            time_grains: List of time grains (day, week, month, etc.)
            options: Additional options:
                - filters: Metric filters
                - label: Display label
        
        Returns:
            Path to the generated metric YAML file
        """
        options = options or {}
        time_grains = time_grains or ['day', 'week', 'month']
        
        metric_name = self._sanitize_identifier(name)
        
        logger.info(f"Generating metric: {metric_name}")
        
        template_context = {
            'metric_name': metric_name,
            'description': description,
            'model': model,
            'label': options.get('label', name.replace('_', ' ').title()),
            'calculation': calculation,
            'expression': expression,
            'timestamp': options.get('timestamp', 'created_at'),
            'time_grains': time_grains,
            'dimensions': dimensions,
            'filters': options.get('filters', []),
            '_generated_at': datetime.utcnow().isoformat(),
            '_template_version': '1.0.0',
        }
        
        try:
            metric_yaml = self.template_engine.render(
                'dbt/metric.yml.j2',
                template_context
            )
        except Exception as e:
            logger.error(f"Template rendering failed for metric {metric_name}: {e}")
            raise ModelGenerationError(f"Failed to render metric template: {e}")
        
        # Write file
        metrics_dir = self.dbt_path / 'models' / 'metrics'
        metrics_dir.mkdir(parents=True, exist_ok=True)
        
        metric_file = metrics_dir / f'{metric_name}.yml'
        
        try:
            metric_file.write_text(metric_yaml, encoding='utf-8')
        except IOError as e:
            logger.error(f"Failed to write metric file: {e}")
            raise ModelGenerationError(f"Failed to write metric file: {e}")
        
        logger.info(f"Generated metric: {metric_file}")
        
        return str(metric_file)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _prepare_staging_columns(
        self,
        table: DataSourceTable,
        options: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Prepare column definitions for staging model template.
        
        Args:
            table: Source table definition
            options: Generation options
        
        Returns:
            List of column dictionaries for the template
        """
        columns = []
        generate_tests = options.get('generate_tests', True)
        
        for col in table.columns:
            # Convert column name to snake_case
            target_name = self._sanitize_identifier(col.name)
            source_name = col.source_name or col.name
            
            # Map source type to ClickHouse type
            clickhouse_type = self._map_type(col.type)
            
            # Determine if alias is needed
            alias = target_name if target_name != source_name else None
            
            # Generate tests based on column properties
            tests = []
            if generate_tests:
                tests = self._generate_column_tests(col, target_name)
            
            column_def = {
                'name': target_name,
                'source_name': source_name,
                'data_type': clickhouse_type,
                'description': col.description or '',
                'tests': tests,
                'alias': alias,
            }
            
            # Add cast if type conversion needed
            if clickhouse_type != 'String' and col.type.lower() != clickhouse_type.lower():
                column_def['cast'] = clickhouse_type
            
            columns.append(column_def)
        
        return columns
    
    def _map_type(self, source_type: str) -> str:
        """
        Map source database type to ClickHouse type.
        
        Args:
            source_type: Source database column type
        
        Returns:
            Corresponding ClickHouse type
        """
        if not source_type:
            return 'String'
        
        # Normalize the type name
        normalized = source_type.lower().strip()
        
        # Remove size specifications for lookup
        # e.g., varchar(255) -> varchar, numeric(10,2) -> numeric
        base_type = re.split(r'[\(\[]', normalized)[0].strip()
        
        # Look up in mapping
        clickhouse_type = self.TYPE_MAPPING.get(base_type, 'String')
        
        # Handle Decimal precision
        if clickhouse_type == 'Decimal' and 'numeric' in normalized or 'decimal' in normalized:
            # Try to extract precision and scale
            match = re.search(r'\((\d+),?\s*(\d+)?\)', normalized)
            if match:
                precision = int(match.group(1))
                scale = int(match.group(2)) if match.group(2) else 0
                if precision <= 9:
                    clickhouse_type = f'Decimal32({scale})'
                elif precision <= 18:
                    clickhouse_type = f'Decimal64({scale})'
                elif precision <= 38:
                    clickhouse_type = f'Decimal128({scale})'
                else:
                    clickhouse_type = f'Decimal256({scale})'
        
        return clickhouse_type
    
    def _generate_column_tests(
        self,
        column: DataSourceColumn,
        target_name: str,
    ) -> List[str]:
        """
        Generate default dbt tests for a column based on its properties.
        
        Args:
            column: Source column definition
            target_name: Target column name
        
        Returns:
            List of dbt test names
        """
        tests = []
        
        # Primary key columns get unique and not_null
        if column.primary_key:
            tests.extend(['unique', 'not_null'])
        # Non-nullable columns get not_null
        elif not column.nullable:
            tests.append('not_null')
        
        # Apply pattern-based tests
        for pattern, pattern_tests in self.COLUMN_TEST_PATTERNS.items():
            if re.match(pattern, target_name):
                for test in pattern_tests:
                    if test not in tests:
                        tests.append(test)
        
        return tests
    
    def _sanitize_identifier(self, name: str) -> str:
        """
        Sanitize a name to be a valid SQL/dbt identifier.
        
        Converts to snake_case, removes invalid characters,
        and ensures it starts with a letter.
        
        Args:
            name: Original name
        
        Returns:
            Sanitized identifier
        """
        if not name:
            return 'unnamed'
        
        # Convert to snake_case
        result = to_snake_case(name)
        
        # Remove any characters that aren't alphanumeric or underscore
        result = re.sub(r'[^a-z0-9_]', '', result.lower())
        
        # Ensure it starts with a letter
        if result and not result[0].isalpha():
            result = 'col_' + result
        
        # Ensure it's not empty
        if not result:
            result = 'unnamed'
        
        # Truncate to max identifier length (63 chars for most databases)
        return result[:63]
    
    def validate_model_compiles(self, model_name: str) -> Tuple[bool, str]:
        """
        Validate that a generated model compiles successfully.
        
        Uses `dbt compile --select <model>` to verify the model.
        
        Args:
            model_name: Name of the model to validate
        
        Returns:
            Tuple of (success, message)
        """
        from app.services.dbt_service import get_dbt_service
        
        try:
            dbt_service = get_dbt_service(str(self.dbt_path))
            result = dbt_service.compile(
                tenant_id='system',
                select=model_name,
            )
            
            if result.success:
                return True, "Model compiles successfully"
            else:
                return False, f"Compilation failed: {result.stderr}"
                
        except Exception as e:
            return False, f"Validation error: {e}"


# Module-level singleton instance
_dbt_model_generator: Optional[DbtModelGenerator] = None


def get_dbt_model_generator(
    template_eng: Optional[TemplateEngine] = None,
    dbt_path: Optional[str] = None,
) -> DbtModelGenerator:
    """
    Get or create the dbt model generator singleton.
    
    Args:
        template_eng: Optional template engine instance
        dbt_path: Optional path to dbt project
    
    Returns:
        DbtModelGenerator instance
    """
    global _dbt_model_generator
    if _dbt_model_generator is None or dbt_path:
        _dbt_model_generator = DbtModelGenerator(template_eng, dbt_path)
    return _dbt_model_generator
