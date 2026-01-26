# 018 - dbt Model Generator

## Metadata

```yaml
prompt_id: "018"
phase: 3
agent: "@dbt"
model: "sonnet 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["017", "010"]
```

## Objective

Implement automated dbt model generation from data source schemas using templates.

## Task Description

Create a service that generates staging, intermediate, and mart models from ingested data.

## Requirements

### Model Generator Service

```python
# backend/app/services/dbt_model_generator.py
from typing import Dict, List, Any
from pathlib import Path
from app.services.template_engine import TemplateEngine
from app.models import DataSourceTable
from app.utils.naming import to_snake_case

class DbtModelGenerator:
    """Generates dbt models from data source schemas."""
    
    def __init__(
        self, 
        template_engine: TemplateEngine,
        dbt_path: str
    ):
        self.template_engine = template_engine
        self.dbt_path = Path(dbt_path)
    
    def generate_staging_model(
        self,
        table: DataSourceTable,
        source_name: str
    ) -> Dict[str, str]:
        """Generate staging model and schema for a table."""
        
        model_name = f"stg_{source_name}_{table.name}"
        
        # Prepare column definitions
        columns = [
            {
                'name': col.name,
                'source_name': col.source_name,
                'data_type': self._map_type(col.type),
                'description': col.description or '',
                'tests': self._default_tests(col),
            }
            for col in table.columns
        ]
        
        # Generate model SQL
        model_sql = self.template_engine.render(
            'dbt/staging_model.sql.j2',
            {
                'model_name': model_name,
                'description': f"Staging model for {table.name}",
                'source_name': source_name,
                'source_table': table.name,
                'columns': columns,
                'materialization': 'view',
            }
        )
        
        # Generate schema YAML
        schema_yaml = self.template_engine.render(
            'dbt/schema.yml.j2',
            {
                'model_name': model_name,
                'description': f"Staging model for {table.name}",
                'columns': columns,
            }
        )
        
        # Write files
        model_path = self.dbt_path / 'models' / 'staging' / source_name
        model_path.mkdir(parents=True, exist_ok=True)
        
        (model_path / f'{model_name}.sql').write_text(model_sql)
        (model_path / f'{model_name}.yml').write_text(schema_yaml)
        
        return {
            'model_path': str(model_path / f'{model_name}.sql'),
            'schema_path': str(model_path / f'{model_name}.yml'),
        }
    
    def generate_source_yaml(
        self,
        source_name: str,
        database: str,
        tables: List[DataSourceTable]
    ) -> str:
        """Generate sources.yml for a data source."""
        
        source_yaml = self.template_engine.render(
            'dbt/sources.yml.j2',
            {
                'source_name': source_name,
                'database': database,
                'schema': 'raw',
                'tables': [
                    {
                        'name': t.name,
                        'description': t.description or '',
                        'freshness': {
                            'warn': 24,
                            'error': 48,
                        },
                        'loaded_at_field': 'ingested_at',
                        'columns': [
                            {
                                'name': c.name,
                                'description': c.description or '',
                            }
                            for c in t.columns
                        ]
                    }
                    for t in tables
                ]
            }
        )
        
        sources_path = self.dbt_path / 'models' / 'staging' / source_name
        sources_path.mkdir(parents=True, exist_ok=True)
        
        sources_file = sources_path / 'sources.yml'
        sources_file.write_text(source_yaml)
        
        return str(sources_file)
    
    def generate_mart_model(
        self,
        name: str,
        description: str,
        source_models: List[str],
        joins: List[Dict],
        metrics: List[Dict]
    ) -> Dict[str, str]:
        """Generate a mart model with business logic."""
        
        model_sql = self.template_engine.render(
            'dbt/marts_model.sql.j2',
            {
                'model_name': name,
                'description': description,
                'source_models': source_models,
                'joins': joins,
                'metrics': metrics,
                'materialization': 'table',
            }
        )
        
        # Write model
        mart_path = self.dbt_path / 'models' / 'marts'
        mart_path.mkdir(parents=True, exist_ok=True)
        
        (mart_path / f'{name}.sql').write_text(model_sql)
        
        return {
            'model_path': str(mart_path / f'{name}.sql'),
        }
    
    def _map_type(self, source_type: str) -> str:
        """Map source database type to ClickHouse type."""
        type_mapping = {
            'varchar': 'String',
            'text': 'String',
            'integer': 'Int32',
            'bigint': 'Int64',
            'boolean': 'UInt8',
            'timestamp': 'DateTime',
            'date': 'Date',
            'numeric': 'Float64',
            'json': 'String',
            'jsonb': 'String',
            'uuid': 'UUID',
        }
        return type_mapping.get(source_type.lower(), 'String')
    
    def _default_tests(self, column) -> List[str]:
        """Generate default tests for a column."""
        tests = []
        if column.primary_key:
            tests.extend(['unique', 'not_null'])
        elif not column.nullable:
            tests.append('not_null')
        return tests
```

### Staging Model Template

```jinja2
{# templates/dbt/staging_model.sql.j2 #}
{{- '{{' }} config(
    materialized='{{ materialization }}'
) {{ '}}' }}

{# {{ model_name }}: {{ description }} #}

WITH source AS (
    SELECT * FROM {{ '{{' }} source('{{ source_name }}', '{{ source_table }}') {{ '}}' }}
),

renamed AS (
    SELECT
{% for col in columns %}
        {{ col.source_name }}{% if col.alias %} AS {{ col.alias }}{% endif %}{% if not loop.last %},{% endif %}

{% endfor %}
    FROM source
)

SELECT * FROM renamed
```

## Expected Output

```
backend/app/services/
├── dbt_model_generator.py
└── dbt_service.py

dbt/models/
├── staging/
│   └── {source_name}/
│       ├── sources.yml
│       ├── stg_{source}_{table}.sql
│       └── stg_{source}_{table}.yml
├── intermediate/
└── marts/
```

## Acceptance Criteria

- [ ] Staging models generated correctly
- [ ] Source YAML generated with freshness
- [ ] Schema YAML includes tests
- [ ] Type mapping works for all source types
- [ ] Generated models compile (`dbt compile`)
- [ ] Generated models run successfully
- [ ] Incremental models work

## Reference Documents

- [dbt Templates](./010-dbt-templates.md)
- [dbt Project Setup](./017-dbt-project-setup.md)
