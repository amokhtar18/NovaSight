# 016 - Ingestion DAG Generator

## Metadata

```yaml
prompt_id: "016"
phase: 2
agent: "@orchestration"
model: "sonnet 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["011", "013"]
```

## Objective

Implement automated Airflow DAG generation for data ingestion workflows.

## Task Description

Create a service that generates Airflow DAGs from data source configurations using templates.

## Requirements

### DAG Generator Service

```python
# backend/app/services/dag_generator.py
from typing import Dict, List, Any
from pathlib import Path
from app.services.template_engine import TemplateEngine
from app.models import DataSource, DataSourceTable
from app.utils.airflow_client import AirflowClient

class DAGGenerator:
    """Generates Airflow DAGs for data ingestion."""
    
    def __init__(self, template_engine: TemplateEngine, airflow_client: AirflowClient):
        self.template_engine = template_engine
        self.airflow_client = airflow_client
        self.dags_path = Path('/opt/airflow/dags')
    
    def generate_ingestion_dag(
        self,
        datasource: DataSource,
        tables: List[DataSourceTable],
        schedule: str = '@hourly'
    ) -> str:
        """Generate ingestion DAG for a data source."""
        
        # Prepare table mappings
        table_mappings = [
            {
                'source_table': t.source_name,
                'target_table': t.target_name,
                'incremental_column': t.incremental_column or 'updated_at',
                'mode': 'incremental' if t.incremental_column else 'full',
            }
            for t in tables
        ]
        
        # Render DAG from template
        dag_content = self.template_engine.render(
            'airflow/ingestion_dag.py.j2',
            {
                'tenant_id': str(datasource.tenant_id),
                'datasource_id': str(datasource.id),
                'datasource_type': datasource.type.value,
                'connection_id': f'novasight_{datasource.id}',
                'table_mappings': table_mappings,
                'schedule': schedule,
            }
        )
        
        # Write DAG file
        dag_id = f'ingest_{datasource.tenant_id}_{datasource.id}'
        dag_file = self.dags_path / f'{dag_id}.py'
        dag_file.write_text(dag_content)
        
        # Trigger DAG parsing
        self.airflow_client.trigger_dag_parse()
        
        return dag_id
    
    def update_ingestion_dag(
        self,
        datasource: DataSource,
        tables: List[DataSourceTable],
        schedule: str = None
    ) -> str:
        """Update existing ingestion DAG."""
        # Delete old DAG
        dag_id = f'ingest_{datasource.tenant_id}_{datasource.id}'
        self.delete_dag(dag_id)
        
        # Generate new DAG
        return self.generate_ingestion_dag(
            datasource, 
            tables, 
            schedule or datasource.sync_frequency
        )
    
    def delete_dag(self, dag_id: str) -> None:
        """Delete a DAG file."""
        dag_file = self.dags_path / f'{dag_id}.py'
        if dag_file.exists():
            dag_file.unlink()
        
        # Pause and delete from Airflow
        self.airflow_client.pause_dag(dag_id)
        self.airflow_client.delete_dag(dag_id)
```

### Custom Airflow Operators

```python
# backend/app/operators/ingestion.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
from typing import Optional, List
from app.connectors import ConnectorRegistry
from app.services.clickhouse import ClickHouseWriter

class IngestTableOperator(BaseOperator):
    """Operator to ingest data from source to ClickHouse."""
    
    template_fields = ['source_table', 'target_table', 'tenant_id']
    
    @apply_defaults
    def __init__(
        self,
        connection_id: str,
        source_table: str,
        target_table: str,
        tenant_id: str,
        incremental_column: Optional[str] = None,
        mode: str = 'incremental',
        batch_size: int = 10000,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.connection_id = connection_id
        self.source_table = source_table
        self.target_table = target_table
        self.tenant_id = tenant_id
        self.incremental_column = incremental_column
        self.mode = mode
        self.batch_size = batch_size
    
    def execute(self, context):
        """Execute the ingestion."""
        # Get connection from Airflow
        connection = self.get_connection(self.connection_id)
        
        # Create connector
        connector_class = ConnectorRegistry.get(connection.conn_type)
        connector = connector_class.from_airflow_connection(connection)
        
        # Build query
        if self.mode == 'incremental' and self.incremental_column:
            # Get last ingested timestamp from ClickHouse
            last_value = self._get_last_value()
            query = f"""
                SELECT * FROM {self.source_table}
                WHERE {self.incremental_column} > %s
                ORDER BY {self.incremental_column}
            """
            params = [last_value]
        else:
            query = f"SELECT * FROM {self.source_table}"
            params = []
        
        # Fetch and write data
        writer = ClickHouseWriter(database=f'tenant_{self.tenant_id}')
        
        with connector:
            total_rows = 0
            for batch in connector.fetch_data(query, params, self.batch_size):
                writer.insert_batch(self.target_table, batch)
                total_rows += len(batch)
                self.log.info(f"Ingested {total_rows} rows")
        
        return {'rows_ingested': total_rows}
```

### Airflow Client

```python
# backend/app/utils/airflow_client.py
import requests
from typing import Optional, Dict, Any

class AirflowClient:
    """Client for Airflow REST API."""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.auth = (username, password)
    
    def trigger_dag(self, dag_id: str, conf: Dict[str, Any] = None) -> str:
        """Trigger a DAG run."""
        response = requests.post(
            f'{self.base_url}/api/v1/dags/{dag_id}/dagRuns',
            json={'conf': conf or {}},
            auth=self.auth
        )
        response.raise_for_status()
        return response.json()['dag_run_id']
    
    def get_dag_run_status(self, dag_id: str, run_id: str) -> str:
        """Get status of a DAG run."""
        response = requests.get(
            f'{self.base_url}/api/v1/dags/{dag_id}/dagRuns/{run_id}',
            auth=self.auth
        )
        response.raise_for_status()
        return response.json()['state']
    
    def pause_dag(self, dag_id: str) -> None:
        """Pause a DAG."""
        requests.patch(
            f'{self.base_url}/api/v1/dags/{dag_id}',
            json={'is_paused': True},
            auth=self.auth
        )
    
    def delete_dag(self, dag_id: str) -> None:
        """Delete a DAG."""
        requests.delete(
            f'{self.base_url}/api/v1/dags/{dag_id}',
            auth=self.auth
        )
```

## Expected Output

```
backend/app/
├── services/
│   ├── dag_generator.py
│   └── clickhouse_writer.py
├── operators/
│   ├── __init__.py
│   ├── ingestion.py
│   └── validation.py
├── sensors/
│   ├── __init__.py
│   └── source.py
└── utils/
    └── airflow_client.py
```

## Acceptance Criteria

- [ ] DAG generation from template works
- [ ] Generated DAGs pass syntax check
- [ ] IngestTableOperator fetches data correctly
- [ ] Incremental ingestion works
- [ ] Full refresh mode works
- [ ] DAGs appear in Airflow UI
- [ ] DAG triggering via API works

## Reference Documents

- [Airflow Templates](./011-airflow-templates.md)
- [Airflow DAGs Skill](../skills/airflow-dags/SKILL.md)
