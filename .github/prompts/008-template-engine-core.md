# 008 - Template Engine Core

## Metadata

```yaml
prompt_id: "008"
phase: 2
agent: "@template-engine"
model: "opus 4.5"
priority: P0
estimated_effort: "4 days"
dependencies: ["003"]
```

## Objective

Implement the core template engine using Jinja2 for secure code generation with strict validation.

## Task Description

Create the template engine foundation that ensures ALL generated code comes from pre-approved templates, never from LLM-generated arbitrary code.

## Critical Security Mandate

**ADR-002 Compliance**: The template engine is the ONLY mechanism for code generation. All LLM interactions produce PARAMETERS ONLY, which are validated and then passed to templates.

## Requirements

### Template Engine Architecture

```python
# backend/app/services/template_engine/engine.py
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateSyntaxError
from pathlib import Path
from typing import Any, Dict
import hashlib
import json

class TemplateEngine:
    """Secure template engine for code generation."""
    
    TEMPLATE_VERSION = "1.0.0"
    
    def __init__(self, template_dir: str):
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        
        # Register custom filters
        self._register_filters()
        
        # Load template manifest for validation
        self.manifest = self._load_manifest()
    
    def _register_filters(self):
        """Register custom Jinja2 filters."""
        self.env.filters['snake_case'] = to_snake_case
        self.env.filters['camel_case'] = to_camel_case
        self.env.filters['pascal_case'] = to_pascal_case
        self.env.filters['sql_safe'] = sql_identifier_safe
    
    def _load_manifest(self) -> Dict:
        """Load template manifest for validation."""
        manifest_path = self.template_dir / 'manifest.json'
        if manifest_path.exists():
            return json.loads(manifest_path.read_text())
        return {}
    
    def render(
        self, 
        template_name: str, 
        parameters: Dict[str, Any],
        validate: bool = True
    ) -> str:
        """Render template with validated parameters."""
        if validate:
            self._validate_parameters(template_name, parameters)
        
        template = self.env.get_template(template_name)
        return template.render(**parameters)
    
    def _validate_parameters(self, template_name: str, params: Dict):
        """Validate parameters against template schema."""
        schema = self.manifest.get(template_name, {}).get('schema', {})
        if schema:
            from pydantic import create_model, ValidationError
            # Dynamic validation using Pydantic
            ...
```

### Parameter Validator

```python
# backend/app/services/template_engine/validator.py
from pydantic import BaseModel, validator, constr
from typing import List, Optional
import re

class SQLIdentifier(BaseModel):
    """Validates SQL identifiers (table/column names)."""
    name: constr(regex=r'^[a-z][a-z0-9_]*$', max_length=63)

class ColumnDefinition(BaseModel):
    """Validated column definition for table templates."""
    name: str
    type: str
    nullable: bool = True
    default: Optional[str] = None
    primary_key: bool = False
    
    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError('Invalid column name')
        return v
    
    @validator('type')
    def validate_type(cls, v):
        allowed_types = [
            'UUID', 'VARCHAR', 'TEXT', 'INTEGER', 'BIGINT', 
            'BOOLEAN', 'TIMESTAMP', 'JSONB', 'NUMERIC'
        ]
        base_type = v.split('(')[0].upper()
        if base_type not in allowed_types:
            raise ValueError(f'Invalid type: {v}')
        return v
```

### Template Directory Structure

```
backend/templates/
├── manifest.json               # Template registry + schemas
├── sql/
│   ├── create_table.sql.j2
│   ├── create_index.sql.j2
│   └── tenant_schema.sql.j2
├── dbt/
│   ├── model.sql.j2
│   ├── schema.yml.j2
│   └── sources.yml.j2
├── airflow/
│   ├── dag.py.j2
│   └── task.py.j2
└── clickhouse/
    ├── create_table.sql.j2
    └── materialized_view.sql.j2
```

### Template Manifest

```json
{
  "version": "1.0.0",
  "templates": {
    "sql/create_table.sql.j2": {
      "description": "Creates PostgreSQL table",
      "schema": {
        "table_name": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
        "columns": {"type": "array", "items": {"$ref": "#/definitions/Column"}},
        "tenant_aware": {"type": "boolean", "default": true}
      }
    }
  },
  "definitions": {
    "Column": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "type": {"type": "string"},
        "nullable": {"type": "boolean"}
      },
      "required": ["name", "type"]
    }
  }
}
```

## Expected Output

```
backend/
├── app/
│   └── services/
│       └── template_engine/
│           ├── __init__.py
│           ├── engine.py
│           ├── validator.py
│           └── filters.py
└── templates/
    ├── manifest.json
    ├── sql/
    ├── dbt/
    ├── airflow/
    └── clickhouse/
```

## Acceptance Criteria

- [ ] Template engine renders templates correctly
- [ ] Parameter validation blocks invalid input
- [ ] SQL injection attempts rejected
- [ ] Template manifest loaded and validated
- [ ] Custom filters work (snake_case, etc.)
- [ ] Error messages are clear and actionable
- [ ] 100% test coverage on validator

## Reference Documents

- [Template Engine Agent](../agents/template-engine-agent.agent.md)
- [Template Engine Skill](../skills/template-engine/SKILL.md)
- [ADR-002](../../docs/requirements/Architecture_Decisions.md)
