# 017 - dbt Project Setup

## Metadata

```yaml
prompt_id: "017"
phase: 3
agent: "@dbt"
model: "sonnet 4.5"
priority: P0
estimated_effort: "2 days"
dependencies: ["002", "010"]
```

## Objective

Set up the dbt project structure with ClickHouse adapter and multi-tenant configuration.

## Task Description

Create a dbt project configured for ClickHouse with dynamic profile selection per tenant.

## Requirements

### Project Structure

```
dbt/
├── dbt_project.yml
├── profiles.yml
├── packages.yml
├── macros/
│   ├── generate_schema_name.sql
│   └── tenant_filter.sql
├── models/
│   ├── staging/
│   │   └── .gitkeep
│   ├── intermediate/
│   │   └── .gitkeep
│   └── marts/
│       └── .gitkeep
├── seeds/
│   └── .gitkeep
├── tests/
│   └── .gitkeep
└── docs/
    └── .gitkeep
```

### Project Configuration

```yaml
# dbt/dbt_project.yml
name: 'novasight'
version: '1.0.0'
config-version: 2

profile: 'novasight'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

target-path: "target"
clean-targets:
  - "target"
  - "dbt_packages"

vars:
  tenant_id: "{{ env_var('TENANT_ID', '') }}"
  tenant_database: "tenant_{{ var('tenant_id') }}"

models:
  novasight:
    staging:
      +materialized: view
      +schema: staging
    intermediate:
      +materialized: ephemeral
    marts:
      +materialized: table
      +schema: marts
```

### Profiles Configuration

```yaml
# dbt/profiles.yml
novasight:
  target: "{{ env_var('DBT_TARGET', 'dev') }}"
  outputs:
    dev:
      type: clickhouse
      schema: "{{ env_var('TENANT_DATABASE', 'default') }}"
      host: "{{ env_var('CLICKHOUSE_HOST', 'localhost') }}"
      port: "{{ env_var('CLICKHOUSE_PORT', 8123) | int }}"
      user: "{{ env_var('CLICKHOUSE_USER', 'default') }}"
      password: "{{ env_var('CLICKHOUSE_PASSWORD', '') }}"
      secure: false
      verify: false
      
    prod:
      type: clickhouse
      schema: "{{ env_var('TENANT_DATABASE') }}"
      host: "{{ env_var('CLICKHOUSE_HOST') }}"
      port: "{{ env_var('CLICKHOUSE_PORT', 8123) | int }}"
      user: "{{ env_var('CLICKHOUSE_USER') }}"
      password: "{{ env_var('CLICKHOUSE_PASSWORD') }}"
      secure: true
      verify: true
```

### Custom Schema Macro

```sql
-- dbt/macros/generate_schema_name.sql
{% macro generate_schema_name(custom_schema_name, node) -%}
    {# Use tenant database as schema #}
    {{ var('tenant_database', target.schema) }}
{%- endmacro %}
```

### Tenant Filter Macro

```sql
-- dbt/macros/tenant_filter.sql
{% macro tenant_filter() %}
    {# Returns tenant filter clause - used when needed #}
    tenant_id = '{{ var("tenant_id") }}'
{% endmacro %}

{% macro current_tenant_id() %}
    '{{ var("tenant_id") }}'
{% endmacro %}
```

### Packages

```yaml
# dbt/packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: 1.1.1
  - package: ClickHouse/dbt-clickhouse
    version: 1.6.0
  - package: calogica/dbt_expectations
    version: 0.10.1
```

### Service for dbt Execution

```python
# backend/app/services/dbt_service.py
import subprocess
import os
from typing import Dict, Any, Optional
from pathlib import Path

class DbtService:
    """Service for executing dbt commands."""
    
    def __init__(self, dbt_project_path: str):
        self.project_path = Path(dbt_project_path)
    
    def run(
        self,
        tenant_id: str,
        select: Optional[str] = None,
        exclude: Optional[str] = None,
        full_refresh: bool = False
    ) -> Dict[str, Any]:
        """Run dbt models."""
        cmd = ['dbt', 'run']
        
        if select:
            cmd.extend(['--select', select])
        if exclude:
            cmd.extend(['--exclude', exclude])
        if full_refresh:
            cmd.append('--full-refresh')
        
        return self._execute(cmd, tenant_id)
    
    def test(self, tenant_id: str, select: Optional[str] = None) -> Dict[str, Any]:
        """Run dbt tests."""
        cmd = ['dbt', 'test']
        if select:
            cmd.extend(['--select', select])
        return self._execute(cmd, tenant_id)
    
    def _execute(self, cmd: list, tenant_id: str) -> Dict[str, Any]:
        """Execute dbt command with tenant context."""
        env = os.environ.copy()
        env['TENANT_ID'] = tenant_id
        env['TENANT_DATABASE'] = f'tenant_{tenant_id}'
        
        result = subprocess.run(
            cmd,
            cwd=self.project_path,
            env=env,
            capture_output=True,
            text=True
        )
        
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'return_code': result.returncode
        }
```

## Expected Output

```
dbt/
├── dbt_project.yml
├── profiles.yml
├── packages.yml
├── macros/
│   ├── generate_schema_name.sql
│   └── tenant_filter.sql
├── models/
│   ├── staging/
│   ├── intermediate/
│   └── marts/
└── tests/

backend/app/services/
└── dbt_service.py
```

## Acceptance Criteria

- [ ] `dbt deps` installs packages
- [ ] `dbt debug` passes connection test
- [ ] Profile selects correct tenant database
- [ ] Custom schema macro works
- [ ] Tenant filter macro works
- [ ] DbtService executes commands correctly
- [ ] Multi-tenant isolation verified

## Reference Documents

- [dbt Agent](../agents/dbt-agent.agent.md)
- [dbt Templates](./010-dbt-templates.md)
