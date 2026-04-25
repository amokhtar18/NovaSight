# Template Engine Skill

> ⚠️ **MIGRATION NOTICE — Spark → dlt**
> The PySpark examples below are **deprecated**. The active ingestion template family is **dlt** (`extract_pipeline`, `merge_pipeline`, `scd2_pipeline`). For new ingestion work use the [dlt-iceberg skill](../dlt-iceberg/SKILL.md) and the schemas/validators it defines (`DltExtractDefinition`, `DltMergeDefinition`, `DltSCD2Definition`). The patterns in this skill — sandboxed Jinja, Pydantic validation, forbidden-pattern regex, registry — still apply; only the PySpark-specific examples are obsolete. Authoritative migration plan: [.github/instructions/MIGRATION_SPARK_TO_DLT.md](../../instructions/MIGRATION_SPARK_TO_DLT.md).

## Description
This skill provides patterns for generating code artifacts (dlt pipelines, Dagster ops, dbt models) using the Template Engine Rule with Jinja2 and Pydantic validation.

## Trigger
- User asks to generate DAGs or pipelines
- User asks to create dlt pipelines / ingestion jobs (use the dlt-iceberg skill in tandem)
- User asks to generate dbt models
- User mentions template-based code generation

## CRITICAL RULE
**NO ARBITRARY CODE GENERATION.** All executable artifacts must be generated from pre-approved, security-audited Jinja2 templates with validated inputs.

## Instructions

### 1. Template Registry
```python
# backend/app/services/templates/registry.py
from pathlib import Path
from typing import Dict

TEMPLATE_DIR = Path(__file__).parent / 'jinja'

TEMPLATE_CATALOG = {
    'pyspark_full_load': {
        'file': 'pyspark/full_load.py.j2',
        'description': 'Full table extraction from source to ClickHouse',
        'schema': 'PySparkJobConfig',
        'version': '1.0.0'
    },
    'pyspark_incremental_load': {
        'file': 'pyspark/incremental_load.py.j2',
        'description': 'Incremental extraction with watermark',
        'schema': 'PySparkIncrementalConfig',
        'version': '1.0.0'
    },
    'dag_pipeline': {
        'file': 'airflow/dag.py.j2',
        'description': 'Airflow DAG for pipeline orchestration',
        'schema': 'DagConfig',
        'version': '1.0.0'
    },
    'dbt_model': {
        'file': 'dbt/model.sql.j2',
        'description': 'dbt model SQL file',
        'schema': 'DbtModelConfig',
        'version': '1.0.0'
    },
    'dbt_schema': {
        'file': 'dbt/schema.yml.j2',
        'description': 'dbt model schema YAML',
        'schema': 'DbtSchemaConfig',
        'version': '1.0.0'
    }
}
```

### 2. Pydantic Validation Schemas
```python
# backend/app/schemas/template_schemas.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
import re

# Forbidden patterns for security
FORBIDDEN_PATTERNS = [
    r'import\s+os',
    r'import\s+subprocess',
    r'__import__',
    r'eval\s*\(',
    r'exec\s*\(',
    r'open\s*\(',
    r'system\s*\(',
    r';\s*--',
    r'DROP\s+TABLE',
]

def validate_no_code_injection(value: str) -> str:
    """Validate string doesn't contain code injection patterns."""
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            raise ValueError(f"Forbidden pattern detected: {pattern}")
    return value

class ColumnMapping(BaseModel):
    source_column: str = Field(..., regex=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    target_column: str = Field(..., regex=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    data_type: Literal['String', 'Int32', 'Int64', 'Float64', 'DateTime', 'Date', 'Boolean']
    nullable: bool = True
    
    @validator('source_column', 'target_column')
    def validate_column_name(cls, v):
        if len(v) > 64:
            raise ValueError('Column name too long')
        return validate_no_code_injection(v)

class PySparkJobConfig(BaseModel):
    job_name: str = Field(..., min_length=3, max_length=64, regex=r'^[a-z][a-z0-9_]*$')
    source_type: Literal['postgresql', 'oracle', 'sqlserver']
    source_table: str = Field(..., regex=r'^[a-zA-Z_][a-zA-Z0-9_.]*$')
    target_table: str = Field(..., regex=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    columns: List[ColumnMapping] = Field(..., min_items=1, max_items=100)
    partition_column: Optional[str] = None
    partition_count: int = Field(default=4, ge=1, le=32)
    
    @validator('source_table', 'target_table')
    def validate_table_name(cls, v):
        return validate_no_code_injection(v)
```

### 3. Sandboxed Jinja2 Environment
```python
# backend/app/services/templates/engine.py
from jinja2 import Environment, FileSystemLoader, select_autoescape
from jinja2.sandbox import SandboxedEnvironment
from pathlib import Path

class SecureTemplateEngine:
    """Sandboxed Jinja2 template engine."""
    
    FORBIDDEN_ATTRS = {
        '__class__', '__mro__', '__subclasses__', '__bases__',
        '__globals__', '__code__', '__builtins__'
    }
    
    def __init__(self, template_dir: Path):
        self.env = SandboxedEnvironment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # Remove dangerous filters
        for attr in self.FORBIDDEN_ATTRS:
            self.env.globals.pop(attr, None)
    
    def render(self, template_name: str, context: dict) -> str:
        """Render template with validated context."""
        template = self.env.get_template(template_name)
        
        # Additional safety: scan output for forbidden patterns
        output = template.render(**context)
        self._validate_output(output)
        
        return output
    
    def _validate_output(self, output: str):
        """Final validation of generated code."""
        from app.schemas.template_schemas import FORBIDDEN_PATTERNS
        import re
        
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, output, re.IGNORECASE):
                raise ValueError(f"Generated code contains forbidden pattern")
```

### 4. Example PySpark Template
```jinja2
{# templates/jinja/pyspark/full_load.py.j2 #}
"""
PySpark Full Load Job
Generated by NovaSight Template Engine
Job: {{ job_name }}
Source: {{ source_table }}
Target: {{ target_table }}
"""
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField
from pyspark.sql.types import StringType, IntegerType, LongType, DoubleType, TimestampType, DateType, BooleanType

# Type mapping
TYPE_MAP = {
    'String': StringType(),
    'Int32': IntegerType(),
    'Int64': LongType(),
    'Float64': DoubleType(),
    'DateTime': TimestampType(),
    'Date': DateType(),
    'Boolean': BooleanType(),
}

def main():
    spark = SparkSession.builder \
        .appName("{{ job_name }}") \
        .getOrCreate()
    
    # Define schema
    schema = StructType([
        {% for col in columns %}
        StructField("{{ col.source_column }}", TYPE_MAP["{{ col.data_type }}"], {{ col.nullable | lower }}),
        {% endfor %}
    ])
    
    # Read from source
    df = spark.read \
        .format("jdbc") \
        .option("driver", "{{ driver }}") \
        .option("url", "{{ jdbc_url }}") \
        .option("dbtable", "{{ source_table }}") \
        .option("user", "{{ username }}") \
        .option("password", "{{ password }}") \
        {% if partition_column %}
        .option("partitionColumn", "{{ partition_column }}") \
        .option("numPartitions", {{ partition_count }}) \
        {% endif %}
        .load()
    
    # Select and rename columns
    df_selected = df.select(
        {% for col in columns %}
        df["{{ col.source_column }}"].alias("{{ col.target_column }}"),
        {% endfor %}
    )
    
    # Write to ClickHouse
    df_selected.write \
        .format("jdbc") \
        .option("driver", "com.clickhouse.jdbc.ClickHouseDriver") \
        .option("url", "{{ clickhouse_url }}") \
        .option("dbtable", "{{ target_table }}") \
        .mode("overwrite") \
        .save()
    
    spark.stop()

if __name__ == "__main__":
    main()
```

### 5. Artifact Generation Service
```python
# backend/app/services/artifact_service.py
from pathlib import Path
from typing import Dict, Any
from app.services.templates.engine import SecureTemplateEngine
from app.services.templates.registry import TEMPLATE_CATALOG
from app.schemas.template_schemas import PySparkJobConfig, DagConfig
import hashlib

class ArtifactService:
    """Service for generating code artifacts from templates."""
    
    def __init__(self, template_engine: SecureTemplateEngine, output_dir: Path):
        self.engine = template_engine
        self.output_dir = output_dir
    
    def generate_pyspark_job(
        self,
        config: PySparkJobConfig,
        credentials: Dict[str, str],
        tenant_id: str
    ) -> Path:
        """Generate PySpark job from validated config."""
        
        template_info = TEMPLATE_CATALOG['pyspark_full_load']
        
        # Build context
        context = {
            **config.dict(),
            **credentials,
            'tenant_id': tenant_id
        }
        
        # Render
        code = self.engine.render(template_info['file'], context)
        
        # Write to file
        output_path = self.output_dir / tenant_id / 'pyspark' / f"{config.job_name}.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code)
        
        # Store hash for integrity verification
        self._store_hash(output_path, code)
        
        return output_path
    
    def _store_hash(self, path: Path, content: str):
        """Store content hash for integrity verification."""
        hash_value = hashlib.sha256(content.encode()).hexdigest()
        hash_path = path.with_suffix(path.suffix + '.sha256')
        hash_path.write_text(hash_value)
```

## Security Checklist
- [ ] All inputs validated with Pydantic
- [ ] No user-provided code executed
- [ ] Templates are pre-approved and version-controlled
- [ ] Output scanned for forbidden patterns
- [ ] No dynamic template loading from user input
- [ ] Sandboxed Jinja2 environment used

## Reference Files
- [Template Engine Agent](../../agents/template-engine-agent.agent.md)
- [Architecture Decisions - ADR-002](../../docs/requirements/Architecture_Decisions.md)
