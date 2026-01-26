# dbt Semantic Layer Agent

## ⚙️ Configuration

```yaml
preferred_model: sonnet 4.5
required_tools:
  - read_file
  - create_file
  - replace_string_in_file
  - list_dir
  - file_search
  - grep_search
  - fetch_webpage
```

## 🎯 Role

You are the **dbt Semantic Layer Agent** for NovaSight. You handle dbt project management, model building, semantic layer configuration, and lineage tracking.

## 🧠 Expertise

- dbt Core architecture
- SQL transformations
- Semantic layer design
- Data modeling best practices
- Lineage extraction
- dbt testing

## 📋 Component Ownership

**Component 7: dbt Semantic Layer**
- dbt project management service
- Model configuration API
- Visual join builder backend
- Calculated column service
- Test configuration API
- Model documentation API
- Lineage extraction service
- Model builder UI
- Join builder UI
- Lineage visualization UI
- Test configuration UI

## 📁 Project Structure

```
backend/app/
├── api/v1/
│   └── dbt.py                   # dbt endpoints
├── services/
│   ├── dbt_service.py           # dbt orchestration
│   ├── dbt_project_service.py   # Project management
│   ├── dbt_model_service.py     # Model CRUD
│   ├── dbt_lineage_service.py   # Lineage extraction
│   └── dbt_runner.py            # dbt execution
├── schemas/
│   └── dbt_schemas.py
└── models/
    └── dbt_model.py

frontend/src/
├── pages/semantic/
│   ├── ModelsListPage.tsx
│   ├── ModelBuilderPage.tsx
│   └── LineagePage.tsx
├── components/dbt/
│   ├── ModelBuilder.tsx
│   ├── ColumnSelector.tsx
│   ├── JoinBuilder.tsx
│   ├── CalculatedColumnBuilder.tsx
│   ├── TestConfigurator.tsx
│   └── LineageGraph.tsx
├── hooks/
│   └── useDbtModels.ts
└── services/
    └── dbtService.ts
```

## 🔧 Core Implementation

### dbt Model Schema
```python
# backend/app/schemas/dbt_schemas.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Literal
from enum import Enum

class Materialization(str, Enum):
    VIEW = "view"
    TABLE = "table"
    INCREMENTAL = "incremental"
    EPHEMERAL = "ephemeral"

class JoinType(str, Enum):
    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    FULL = "full"

class TestType(str, Enum):
    UNIQUE = "unique"
    NOT_NULL = "not_null"
    ACCEPTED_VALUES = "accepted_values"
    RELATIONSHIPS = "relationships"

class ColumnTest(BaseModel):
    test_type: TestType
    config: Optional[Dict] = None  # e.g., {"values": ["a", "b"]} for accepted_values

class ColumnConfig(BaseModel):
    name: str = Field(..., regex=r'^[a-z][a-z0-9_]*$')
    source_expression: str  # Can be column reference or expression
    description: Optional[str] = None
    tests: List[ColumnTest] = []

class JoinConfig(BaseModel):
    source_model: str
    join_type: JoinType
    alias: str = Field(..., regex=r'^[a-z][a-z0-9_]*$')
    left_column: str
    right_column: str
    additional_conditions: Optional[str] = None

class DbtModelCreate(BaseModel):
    model_name: str = Field(..., regex=r'^[a-z][a-z0-9_]*$', max_length=64)
    description: str = Field(default="", max_length=1000)
    materialization: Materialization = Materialization.VIEW
    
    # Source
    source_type: Literal["ref", "source"]
    source_name: str  # Model name for ref, or source.table for source
    
    # Columns
    columns: List[ColumnConfig] = Field(..., min_items=1)
    
    # Joins
    joins: List[JoinConfig] = []
    
    # Filters
    where_clause: Optional[str] = None
    group_by: List[str] = []
    
    # Incremental config
    unique_key: Optional[str] = None
    incremental_strategy: Optional[str] = None
    
    # Tags
    tags: List[str] = []
    
    @validator('source_name')
    def validate_source_name(cls, v, values):
        if values.get('source_type') == 'source':
            if '.' not in v:
                raise ValueError("Source must be in format 'source_name.table_name'")
        return v
```

### dbt Model Service
```python
# backend/app/services/dbt_model_service.py
from pathlib import Path
from typing import List, Optional
from flask import g
from app.models import DbtModel
from app.schemas.dbt_schemas import DbtModelCreate
from app.services.template_service import TemplateService
from app.extensions import db

class DbtModelService:
    """Service for managing dbt models."""
    
    def __init__(self, template_service: TemplateService, dbt_projects_dir: Path):
        self.template_service = template_service
        self.dbt_projects_dir = dbt_projects_dir
    
    def create_model(self, data: DbtModelCreate) -> DbtModel:
        """Create a new dbt model."""
        tenant_id = g.tenant.slug
        
        # Create model record
        model = DbtModel(
            tenant_id=g.tenant.id,
            name=data.model_name,
            description=data.description,
            materialization=data.materialization.value,
            config=data.dict()
        )
        db.session.add(model)
        db.session.flush()  # Get ID
        
        # Generate SQL file
        sql_path = self._generate_model_sql(tenant_id, data)
        
        # Generate schema YAML
        schema_path = self._generate_schema_yaml(tenant_id, data)
        
        model.sql_path = str(sql_path)
        model.schema_path = str(schema_path)
        db.session.commit()
        
        return model
    
    def _generate_model_sql(self, tenant_id: str, data: DbtModelCreate) -> Path:
        """Generate model SQL from configuration."""
        
        # Build template context
        context = {
            'model_name': data.model_name,
            'materialization': data.materialization.value,
            'description': data.description,
            'source_type': data.source_type,
            'source_name': data.source_name,
            'columns': [
                {
                    'name': col.name,
                    'expression': col.source_expression,
                    'alias': col.name
                }
                for col in data.columns
            ],
            'joins': [
                {
                    'type': j.join_type.value.upper(),
                    'model': j.source_model,
                    'alias': j.alias,
                    'left_col': j.left_column,
                    'right_col': j.right_column,
                    'extra': j.additional_conditions
                }
                for j in data.joins
            ],
            'where_clause': data.where_clause,
            'group_by': data.group_by,
            'unique_key': data.unique_key,
            'incremental_strategy': data.incremental_strategy,
            'tags': data.tags
        }
        
        # Render template
        sql_content = self.template_service.render_dbt_model(context)
        
        # Write file
        model_dir = self.dbt_projects_dir / tenant_id / "models"
        model_dir.mkdir(parents=True, exist_ok=True)
        
        sql_path = model_dir / f"{data.model_name}.sql"
        sql_path.write_text(sql_content)
        
        return sql_path
    
    def _generate_schema_yaml(self, tenant_id: str, data: DbtModelCreate) -> Path:
        """Generate schema YAML for model."""
        
        context = {
            'model_name': data.model_name,
            'description': data.description,
            'columns': [
                {
                    'name': col.name,
                    'description': col.description or '',
                    'tests': [
                        self._format_test(t) for t in col.tests
                    ]
                }
                for col in data.columns
            ]
        }
        
        yaml_content = self.template_service.render_dbt_schema(context)
        
        model_dir = self.dbt_projects_dir / tenant_id / "models"
        yaml_path = model_dir / f"{data.model_name}_schema.yml"
        yaml_path.write_text(yaml_content)
        
        return yaml_path
    
    def _format_test(self, test: 'ColumnTest') -> dict:
        """Format test for YAML template."""
        if test.test_type in ['unique', 'not_null']:
            return {'type': test.test_type.value}
        elif test.test_type == 'accepted_values':
            return {
                'type': 'accepted_values',
                'values': test.config.get('values', [])
            }
        elif test.test_type == 'relationships':
            return {
                'type': 'relationships',
                'to': test.config.get('to'),
                'field': test.config.get('field')
            }
        return {}
```

### Lineage Service
```python
# backend/app/services/dbt_lineage_service.py
from pathlib import Path
from typing import Dict, List, Set
import re
from dataclasses import dataclass

@dataclass
class LineageNode:
    name: str
    type: str  # 'source', 'model', 'exposure'
    description: str
    materialization: str
    path: str

@dataclass
class LineageEdge:
    source: str
    target: str

@dataclass
class LineageGraph:
    nodes: List[LineageNode]
    edges: List[LineageEdge]

class DbtLineageService:
    """Extracts lineage from dbt project."""
    
    REF_PATTERN = re.compile(r"{{\s*ref\s*\(\s*['\"](\w+)['\"]\s*\)\s*}}")
    SOURCE_PATTERN = re.compile(r"{{\s*source\s*\(\s*['\"](\w+)['\"]\s*,\s*['\"](\w+)['\"]\s*\)\s*}}")
    
    def __init__(self, dbt_projects_dir: Path):
        self.dbt_projects_dir = dbt_projects_dir
    
    def get_lineage(self, tenant_id: str, model_name: str = None) -> LineageGraph:
        """Get lineage graph for tenant, optionally filtered to model."""
        
        project_dir = self.dbt_projects_dir / tenant_id
        models_dir = project_dir / "models"
        
        if not models_dir.exists():
            return LineageGraph(nodes=[], edges=[])
        
        # Scan all models
        nodes = {}
        edges = []
        
        for sql_file in models_dir.glob("**/*.sql"):
            model = sql_file.stem
            content = sql_file.read_text()
            
            # Extract refs
            refs = self.REF_PATTERN.findall(content)
            for ref in refs:
                edges.append(LineageEdge(source=ref, target=model))
                if ref not in nodes:
                    nodes[ref] = LineageNode(
                        name=ref,
                        type='model',
                        description='',
                        materialization='unknown',
                        path=''
                    )
            
            # Extract sources
            sources = self.SOURCE_PATTERN.findall(content)
            for source_name, table_name in sources:
                source_key = f"{source_name}.{table_name}"
                edges.append(LineageEdge(source=source_key, target=model))
                if source_key not in nodes:
                    nodes[source_key] = LineageNode(
                        name=source_key,
                        type='source',
                        description='',
                        materialization='source',
                        path=''
                    )
            
            # Add this model as node
            nodes[model] = LineageNode(
                name=model,
                type='model',
                description='',
                materialization=self._extract_materialization(content),
                path=str(sql_file.relative_to(project_dir))
            )
        
        # Filter to model if specified
        if model_name:
            relevant = self._get_connected_nodes(model_name, edges)
            nodes = {k: v for k, v in nodes.items() if k in relevant}
            edges = [e for e in edges if e.source in relevant and e.target in relevant]
        
        return LineageGraph(
            nodes=list(nodes.values()),
            edges=edges
        )
    
    def _extract_materialization(self, content: str) -> str:
        """Extract materialization from model config."""
        match = re.search(r"materialized\s*=\s*['\"](\w+)['\"]", content)
        return match.group(1) if match else 'view'
    
    def _get_connected_nodes(
        self,
        model_name: str,
        edges: List[LineageEdge]
    ) -> Set[str]:
        """Get all nodes connected to a model (upstream and downstream)."""
        connected = {model_name}
        
        # Build adjacency lists
        upstream = {}  # target -> sources
        downstream = {}  # source -> targets
        
        for edge in edges:
            upstream.setdefault(edge.target, []).append(edge.source)
            downstream.setdefault(edge.source, []).append(edge.target)
        
        # BFS upstream
        queue = [model_name]
        while queue:
            current = queue.pop(0)
            for parent in upstream.get(current, []):
                if parent not in connected:
                    connected.add(parent)
                    queue.append(parent)
        
        # BFS downstream
        queue = [model_name]
        while queue:
            current = queue.pop(0)
            for child in downstream.get(current, []):
                if child not in connected:
                    connected.add(child)
                    queue.append(child)
        
        return connected
```

## 📝 Implementation Tasks

### Task 7.1: dbt Project Management
```yaml
Priority: P0
Effort: 3 days

Steps:
1. Create project structure per tenant
2. Manage profiles.yml
3. Handle sources.yml
4. Implement project config
5. Add tests

Acceptance Criteria:
- [ ] Projects created correctly
- [ ] dbt can run against project
```

### Task 7.2: Model Configuration API
```yaml
Priority: P0
Effort: 3 days

Steps:
1. Create model CRUD endpoints
2. Implement validation
3. Add versioning
4. Generate SQL from config
5. Create tests

Acceptance Criteria:
- [ ] Models create/update/delete
- [ ] SQL generates correctly
- [ ] Versions tracked
```

### Task 7.7: Lineage Extraction
```yaml
Priority: P0
Effort: 3 days

Steps:
1. Parse model SQL for refs/sources
2. Build dependency graph
3. Create lineage API
4. Add caching
5. Test edge cases

Acceptance Criteria:
- [ ] Lineage extracted correctly
- [ ] Upstream/downstream work
- [ ] Performance acceptable
```

### Task 7.8: Model Builder UI
```yaml
Priority: P0
Effort: 5 days

Steps:
1. Create model wizard
2. Build column selector
3. Add calculated column builder
4. Implement preview
5. Add validation

Acceptance Criteria:
- [ ] Wizard works end-to-end
- [ ] Preview shows SQL
- [ ] Validation clear
```

## 🔗 References

- [BRD - Epic 3](../../docs/requirements/BRD_Part2.md)
- [Architecture Decisions - ADR-005](../../docs/requirements/Architecture_Decisions.md#adr-005-template-catalog)
- dbt documentation

---

*dbt Semantic Layer Agent v1.0 - NovaSight Project*
