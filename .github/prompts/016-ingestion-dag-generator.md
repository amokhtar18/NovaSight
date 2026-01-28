# 016 - Ingestion DAG Generator

## Metadata

```yaml
prompt_id: "016"
phase: 2
agent: "@orchestration"
model: "sonnet 4.5"
priority: P0
estimated_effort: "2 days"
dependencies: ["011", "013", "017"]
```

## Objective

Implement automated Airflow DAG generation that orchestrates execution of pre-defined PySpark jobs created via the PySpark App Builder service.

## Task Description

Create a service that generates Airflow DAGs to schedule and run PySpark applications that were previously created and validated through the PySpark App Builder (Prompt 017). The DAG generator does NOT create PySpark code - it only orchestrates execution of existing PySpark jobs.

## Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  PySpark App        │────▶│  DAG Generator       │────▶│  Airflow DAG    │
│  Builder (017)      │     │  Service (016)       │     │  Files          │
│  - Generates code   │     │  - Creates DAGs      │     │  - Schedules    │
│  - Stores config    │     │  - Sets schedule     │     │  - Submits jobs │
└─────────────────────┘     └──────────────────────┘     └─────────────────┘
                                      │
                                      ▼
                            ┌──────────────────────┐
                            │  Spark Cluster       │
                            │  - Runs PySpark jobs │
                            └──────────────────────┘
```

## Requirements

### DAG Generator Service

```python
# backend/app/services/dag_generator.py
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
import json
from app.services.template_engine import TemplateEngine
from app.services.pyspark_app_service import PySparkAppService
from app.models import PySparkApp
from app.utils.airflow_client import AirflowClient
from app.errors import NotFoundError, ValidationError

class DAGGenerator:
    """
    Generates Airflow DAGs to orchestrate pre-defined PySpark jobs.
    
    This service does NOT generate PySpark code. It only creates Airflow DAGs
    that schedule and run PySpark applications created via the PySpark App Builder.
    All PySpark code comes from pre-approved templates (ADR-002 compliant).
    """
    
    def __init__(
        self, 
        tenant_id: str,
        template_engine: TemplateEngine, 
        airflow_client: AirflowClient
    ):
        self.tenant_id = tenant_id
        self.template_engine = template_engine
        self.airflow_client = airflow_client
        self.pyspark_service = PySparkAppService(tenant_id)
        self.dags_path = Path('/opt/airflow/dags')
        self.spark_apps_path = Path('/opt/airflow/spark_apps')
    
    def generate_dag_for_pyspark_app(
        self,
        pyspark_app_id: str,
        schedule: str = '@hourly',
        spark_config: Optional[Dict[str, str]] = None,
        notifications: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate an Airflow DAG to run a pre-defined PySpark application.
        
        Args:
            pyspark_app_id: UUID of the PySpark app created via PySpark App Builder
            schedule: Cron expression or Airflow preset (@hourly, @daily, etc.)
            spark_config: Optional Spark configuration overrides
            notifications: Optional notification settings (email, slack, etc.)
            
        Returns:
            Generated DAG ID
            
        Raises:
            NotFoundError: If PySpark app not found
            ValidationError: If PySpark app has no generated code
        """
        # Fetch the PySpark app configuration
        pyspark_app = self.pyspark_service.get_app(pyspark_app_id)
        if not pyspark_app:
            raise NotFoundError(f"PySpark app {pyspark_app_id} not found")
        
        # Ensure code has been generated
        if not pyspark_app.generated_code:
            raise ValidationError(
                f"PySpark app {pyspark_app_id} has no generated code. "
                "Generate code first using the PySpark App Builder."
            )
        
        # Default Spark configuration
        default_spark_config = {
            'spark.executor.memory': '2g',
            'spark.executor.cores': '2',
            'spark.dynamicAllocation.enabled': 'true',
            'spark.dynamicAllocation.minExecutors': '1',
            'spark.dynamicAllocation.maxExecutors': '5',
        }
        
        # Merge with custom config
        final_spark_config = {**default_spark_config, **(spark_config or {})}
        
        # Prepare DAG template context
        dag_id = f'pyspark_{self.tenant_id}_{pyspark_app.id}'
        
        context = {
            'dag_id': dag_id,
            'tenant_id': self.tenant_id,
            'pyspark_app_id': str(pyspark_app.id),
            'pyspark_app_name': pyspark_app.name,
            'pyspark_app_description': pyspark_app.description or '',
            'schedule': schedule,
            'spark_app_path': f'/opt/airflow/spark_apps/jobs/{dag_id}.py',
            'spark_conf': final_spark_config,
            'scd_type': pyspark_app.scd_type.value,
            'write_mode': pyspark_app.write_mode.value,
            'source_type': pyspark_app.source_type.value,
            'target_database': pyspark_app.target_database,
            'target_table': pyspark_app.target_table,
            'notifications': notifications or {},
            'generated_at': datetime.utcnow().isoformat(),
            'template_version': pyspark_app.template_version,
        }
        
        # Render DAG from template
        dag_content = self.template_engine.render(
            'airflow/pyspark_job_dag.py.j2',
            context
        )
        
        # Write DAG file
        dag_file = self.dags_path / f'{dag_id}.py'
        dag_file.parent.mkdir(parents=True, exist_ok=True)
        dag_file.write_text(dag_content)
        
        # Write the pre-generated PySpark code to spark_apps directory
        spark_app_file = self.spark_apps_path / 'jobs' / f'{dag_id}.py'
        spark_app_file.parent.mkdir(parents=True, exist_ok=True)
        spark_app_file.write_text(pyspark_app.generated_code)
        
        # Trigger DAG parsing in Airflow
        self.airflow_client.trigger_dag_parse()
        
        return dag_id
    
    def generate_dag_for_multiple_apps(
        self,
        pyspark_app_ids: List[str],
        dag_name: str,
        schedule: str = '@daily',
        parallel: bool = False,
        spark_config: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate a single DAG that runs multiple PySpark apps.
        
        Args:
            pyspark_app_ids: List of PySpark app UUIDs to run
            dag_name: Name for the combined DAG
            schedule: Cron expression or Airflow preset
            parallel: If True, run apps in parallel; if False, run sequentially
            spark_config: Optional Spark configuration overrides
            
        Returns:
            Generated DAG ID
        """
        # Validate all apps exist and have generated code
        apps = []
        for app_id in pyspark_app_ids:
            app = self.pyspark_service.get_app(app_id)
            if not app:
                raise NotFoundError(f"PySpark app {app_id} not found")
            if not app.generated_code:
                raise ValidationError(f"PySpark app {app_id} has no generated code")
            apps.append(app)
        
        # Default Spark configuration
        default_spark_config = {
            'spark.executor.memory': '2g',
            'spark.executor.cores': '2',
            'spark.dynamicAllocation.enabled': 'true',
            'spark.dynamicAllocation.minExecutors': '1',
            'spark.dynamicAllocation.maxExecutors': '5',
        }
        
        final_spark_config = {**default_spark_config, **(spark_config or {})}
        
        dag_id = f'pipeline_{self.tenant_id}_{dag_name}'
        
        # Prepare app contexts
        app_contexts = []
        for app in apps:
            app_file = f'{dag_id}_{app.id}.py'
            app_contexts.append({
                'app_id': str(app.id),
                'app_name': app.name,
                'task_id': f'run_{app.name.lower().replace(" ", "_")}',
                'spark_app_path': f'/opt/airflow/spark_apps/jobs/{app_file}',
            })
            
            # Write PySpark code file
            spark_app_file = self.spark_apps_path / 'jobs' / app_file
            spark_app_file.parent.mkdir(parents=True, exist_ok=True)
            spark_app_file.write_text(app.generated_code)
        
        context = {
            'dag_id': dag_id,
            'dag_name': dag_name,
            'tenant_id': self.tenant_id,
            'schedule': schedule,
            'parallel': parallel,
            'apps': app_contexts,
            'spark_conf': final_spark_config,
            'generated_at': datetime.utcnow().isoformat(),
        }
        
        # Render multi-app DAG template
        dag_content = self.template_engine.render(
            'airflow/pyspark_pipeline_dag.py.j2',
            context
        )
        
        dag_file = self.dags_path / f'{dag_id}.py'
        dag_file.write_text(dag_content)
        
        self.airflow_client.trigger_dag_parse()
        
        return dag_id
    
    def update_dag_schedule(self, dag_id: str, new_schedule: str) -> None:
        """Update the schedule of an existing DAG."""
        dag_file = self.dags_path / f'{dag_id}.py'
        if not dag_file.exists():
            raise NotFoundError(f"DAG {dag_id} not found")
        
        # Read current DAG content
        content = dag_file.read_text()
        
        # Update schedule_interval
        import re
        updated_content = re.sub(
            r"schedule_interval='[^']*'",
            f"schedule_interval='{new_schedule}'",
            content
        )
        
        dag_file.write_text(updated_content)
        self.airflow_client.trigger_dag_parse()
    
    def delete_dag(self, dag_id: str) -> None:
        """Delete a DAG and its associated PySpark files."""
        # Delete DAG file
        dag_file = self.dags_path / f'{dag_id}.py'
        if dag_file.exists():
            dag_file.unlink()
        
        # Delete associated PySpark job files
        jobs_dir = self.spark_apps_path / 'jobs'
        for job_file in jobs_dir.glob(f'{dag_id}*.py'):
            job_file.unlink()
        
        # Pause and delete from Airflow
        try:
            self.airflow_client.pause_dag(dag_id)
            self.airflow_client.delete_dag(dag_id)
        except Exception:
            pass  # DAG may not exist in Airflow yet
    
    def list_dags_for_tenant(self) -> List[Dict[str, Any]]:
        """List all DAGs for the current tenant."""
        dags = []
        prefix = f'pyspark_{self.tenant_id}_'
        pipeline_prefix = f'pipeline_{self.tenant_id}_'
        
        for dag_file in self.dags_path.glob('*.py'):
            if dag_file.name.startswith(prefix) or dag_file.name.startswith(pipeline_prefix):
                dag_id = dag_file.stem
                dags.append({
                    'dag_id': dag_id,
                    'file_path': str(dag_file),
                    'is_pipeline': dag_file.name.startswith(pipeline_prefix),
                })
        
        return dags
```

### Airflow DAG Template (Single PySpark App)

```jinja2
{# backend/app/templates/airflow/pyspark_job_dag.py.j2 #}
"""
Auto-generated Airflow DAG for PySpark Application: {{ pyspark_app_name }}
Generated for tenant: {{ tenant_id }}
PySpark App ID: {{ pyspark_app_id }}
Generated at: {{ generated_at }}

This DAG runs a pre-defined PySpark job created via the PySpark App Builder.
The PySpark code was generated from approved templates (ADR-002 compliant).
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# Default arguments for the DAG
default_args = {
    'owner': 'novasight',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': {{ 'True' if notifications.get('email_on_failure') else 'False' }},
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    {% if notifications.get('email') %}
    'email': ['{{ notifications.email }}'],
    {% endif %}
}

# DAG definition
with DAG(
    dag_id='{{ dag_id }}',
    default_args=default_args,
    description='{{ pyspark_app_description | default("PySpark data pipeline", true) }}',
    schedule_interval='{{ schedule }}',
    catchup=False,
    max_active_runs=1,
    tags=[
        'pyspark', 
        'tenant_{{ tenant_id }}', 
        '{{ scd_type }}',
        '{{ write_mode }}',
    ],
) as dag:
    
    # Task to submit pre-generated PySpark job to Spark cluster
    run_pyspark_job = SparkSubmitOperator(
        task_id='run_{{ pyspark_app_name | lower | replace(" ", "_") }}',
        application='{{ spark_app_path }}',
        name='{{ pyspark_app_name }}',
        conn_id='spark_default',  # Airflow connection to Spark cluster
        conf={
            {% for key, value in spark_conf.items() %}
            '{{ key }}': '{{ value }}',
            {% endfor %}
        },
        jars='/opt/spark/jars/postgresql-42.6.0.jar,/opt/spark/jars/mysql-connector-j-8.2.0.jar,/opt/spark/jars/clickhouse-jdbc-0.4.6-all.jar',
        driver_memory='1g',
        executor_memory='{{ spark_conf.get("spark.executor.memory", "2g") }}',
        executor_cores={{ spark_conf.get("spark.executor.cores", "2") }},
        num_executors=None,  # Dynamic allocation enabled
        verbose=True,
    )
    
    def log_completion(**context):
        """Log completion of PySpark job."""
        ti = context['ti']
        print(f"PySpark job completed: {{ pyspark_app_name }}")
        print(f"Target: {{ target_database }}.{{ target_table }}")
        print(f"SCD Type: {{ scd_type }}, Write Mode: {{ write_mode }}")
    
    log_task = PythonOperator(
        task_id='log_completion',
        python_callable=log_completion,
        provide_context=True,
    )
    
    # Task dependencies
    run_pyspark_job >> log_task
```

### Airflow DAG Template (Multi-App Pipeline)

```jinja2
{# backend/app/templates/airflow/pyspark_pipeline_dag.py.j2 #}
"""
Auto-generated Airflow Pipeline DAG: {{ dag_name }}
Generated for tenant: {{ tenant_id }}
Generated at: {{ generated_at }}

This DAG runs multiple pre-defined PySpark jobs created via the PySpark App Builder.
All PySpark code was generated from approved templates (ADR-002 compliant).
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'novasight',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='{{ dag_id }}',
    default_args=default_args,
    description='Pipeline: {{ dag_name }}',
    schedule_interval='{{ schedule }}',
    catchup=False,
    max_active_runs=1,
    tags=['pipeline', 'pyspark', 'tenant_{{ tenant_id }}'],
) as dag:
    
    tasks = []
    
    {% for app in apps %}
    {{ app.task_id }} = SparkSubmitOperator(
        task_id='{{ app.task_id }}',
        application='{{ app.spark_app_path }}',
        name='{{ app.app_name }}',
        conn_id='spark_default',
        conf={
            {% for key, value in spark_conf.items() %}
            '{{ key }}': '{{ value }}',
            {% endfor %}
        },
        jars='/opt/spark/jars/postgresql-42.6.0.jar,/opt/spark/jars/mysql-connector-j-8.2.0.jar,/opt/spark/jars/clickhouse-jdbc-0.4.6-all.jar',
        driver_memory='1g',
        executor_memory='{{ spark_conf.get("spark.executor.memory", "2g") }}',
        executor_cores={{ spark_conf.get("spark.executor.cores", "2") }},
        verbose=True,
    )
    tasks.append({{ app.task_id }})
    
    {% endfor %}
    
    def log_pipeline_completion(**context):
        """Log completion of pipeline."""
        print(f"Pipeline '{{ dag_name }}' completed")
        print(f"Executed {{ apps | length }} PySpark jobs")
    
    log_task = PythonOperator(
        task_id='log_pipeline_completion',
        python_callable=log_pipeline_completion,
        provide_context=True,
    )
    
    # Task dependencies
    {% if parallel %}
    # Parallel execution - all tasks run simultaneously, then log
    for task in tasks:
        task >> log_task
    {% else %}
    # Sequential execution - tasks run in order
    {% for i in range(apps | length) %}
    {% if i > 0 %}
    {{ apps[i-1].task_id }} >> {{ apps[i].task_id }}
    {% endif %}
    {% endfor %}
    {% if apps %}
    {{ apps[-1].task_id }} >> log_task
    {% endif %}
    {% endif %}
```

### Airflow Client

```python
# backend/app/utils/airflow_client.py
import requests
from typing import Optional, Dict, Any, List

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
    
    def trigger_dag_parse(self) -> None:
        """Trigger Airflow to re-parse DAG files."""
        # Airflow automatically parses DAG files, but we can trigger refresh
        pass
    
    def pause_dag(self, dag_id: str) -> None:
        """Pause a DAG."""
        requests.patch(
            f'{self.base_url}/api/v1/dags/{dag_id}',
            json={'is_paused': True},
            auth=self.auth
        )
    
    def unpause_dag(self, dag_id: str) -> None:
        """Unpause a DAG."""
        requests.patch(
            f'{self.base_url}/api/v1/dags/{dag_id}',
            json={'is_paused': False},
            auth=self.auth
        )
    
    def delete_dag(self, dag_id: str) -> None:
        """Delete a DAG."""
        requests.delete(
            f'{self.base_url}/api/v1/dags/{dag_id}',
            auth=self.auth
        )
    
    def list_dags(self, tags: List[str] = None) -> List[Dict[str, Any]]:
        """List all DAGs, optionally filtered by tags."""
        params = {}
        if tags:
            params['tags'] = tags
        response = requests.get(
            f'{self.base_url}/api/v1/dags',
            params=params,
            auth=self.auth
        )
        response.raise_for_status()
        return response.json().get('dags', [])
```

### API Endpoints

```python
# backend/app/api/v1/dag_generator.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.dag_generator import DAGGenerator
from app.services.template_engine import TemplateEngine
from app.utils.airflow_client import AirflowClient
from app.config import Config
from app.errors import ValidationError, NotFoundError

bp = Blueprint('dag_generator', __name__, url_prefix='/api/v1/dags')


def get_dag_generator(tenant_id: str) -> DAGGenerator:
    """Create DAG generator instance."""
    template_engine = TemplateEngine()
    airflow_client = AirflowClient(
        base_url=Config.AIRFLOW_API_URL,
        username=Config.AIRFLOW_USERNAME,
        password=Config.AIRFLOW_PASSWORD,
    )
    return DAGGenerator(tenant_id, template_engine, airflow_client)


@bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_dag():
    """
    Generate a DAG for a PySpark app.
    
    Request body:
    {
        "pyspark_app_id": "uuid",
        "schedule": "@hourly",
        "spark_config": { ... },
        "notifications": { ... }
    }
    """
    identity = get_jwt_identity()
    tenant_id = identity.get('tenant_id')
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    pyspark_app_id = data.get('pyspark_app_id')
    if not pyspark_app_id:
        raise ValidationError("pyspark_app_id is required")
    
    generator = get_dag_generator(tenant_id)
    
    dag_id = generator.generate_dag_for_pyspark_app(
        pyspark_app_id=pyspark_app_id,
        schedule=data.get('schedule', '@hourly'),
        spark_config=data.get('spark_config'),
        notifications=data.get('notifications'),
    )
    
    return jsonify({
        'dag_id': dag_id,
        'message': f'DAG generated successfully',
    }), 201


@bp.route('/generate-pipeline', methods=['POST'])
@jwt_required()
def generate_pipeline_dag():
    """
    Generate a DAG that runs multiple PySpark apps.
    
    Request body:
    {
        "pyspark_app_ids": ["uuid1", "uuid2"],
        "dag_name": "my_pipeline",
        "schedule": "@daily",
        "parallel": false,
        "spark_config": { ... }
    }
    """
    identity = get_jwt_identity()
    tenant_id = identity.get('tenant_id')
    
    data = request.get_json()
    if not data:
        raise ValidationError("Request body required")
    
    pyspark_app_ids = data.get('pyspark_app_ids')
    dag_name = data.get('dag_name')
    
    if not pyspark_app_ids or not isinstance(pyspark_app_ids, list):
        raise ValidationError("pyspark_app_ids must be a list of UUIDs")
    if not dag_name:
        raise ValidationError("dag_name is required")
    
    generator = get_dag_generator(tenant_id)
    
    dag_id = generator.generate_dag_for_multiple_apps(
        pyspark_app_ids=pyspark_app_ids,
        dag_name=dag_name,
        schedule=data.get('schedule', '@daily'),
        parallel=data.get('parallel', False),
        spark_config=data.get('spark_config'),
    )
    
    return jsonify({
        'dag_id': dag_id,
        'message': f'Pipeline DAG generated successfully',
    }), 201


@bp.route('/<dag_id>', methods=['DELETE'])
@jwt_required()
def delete_dag(dag_id: str):
    """Delete a DAG."""
    identity = get_jwt_identity()
    tenant_id = identity.get('tenant_id')
    
    # Verify DAG belongs to tenant
    if not dag_id.startswith(f'pyspark_{tenant_id}_') and \
       not dag_id.startswith(f'pipeline_{tenant_id}_'):
        raise NotFoundError(f"DAG {dag_id} not found")
    
    generator = get_dag_generator(tenant_id)
    generator.delete_dag(dag_id)
    
    return jsonify({'message': f'DAG {dag_id} deleted'}), 200


@bp.route('/', methods=['GET'])
@jwt_required()
def list_dags():
    """List all DAGs for the current tenant."""
    identity = get_jwt_identity()
    tenant_id = identity.get('tenant_id')
    
    generator = get_dag_generator(tenant_id)
    dags = generator.list_dags_for_tenant()
    
    return jsonify({'dags': dags}), 200


@bp.route('/<dag_id>/schedule', methods=['PATCH'])
@jwt_required()
def update_schedule(dag_id: str):
    """Update the schedule of a DAG."""
    identity = get_jwt_identity()
    tenant_id = identity.get('tenant_id')
    
    # Verify DAG belongs to tenant
    if not dag_id.startswith(f'pyspark_{tenant_id}_') and \
       not dag_id.startswith(f'pipeline_{tenant_id}_'):
        raise NotFoundError(f"DAG {dag_id} not found")
    
    data = request.get_json()
    new_schedule = data.get('schedule')
    if not new_schedule:
        raise ValidationError("schedule is required")
    
    generator = get_dag_generator(tenant_id)
    generator.update_dag_schedule(dag_id, new_schedule)
    
    return jsonify({'message': f'Schedule updated to {new_schedule}'}), 200
```

## Expected Output

```
backend/app/
├── services/
│   └── dag_generator.py              # Generates DAGs for PySpark apps
├── api/v1/
│   └── dag_generator.py              # API endpoints
├── templates/
│   └── airflow/
│       ├── pyspark_job_dag.py.j2     # Single app DAG template
│       └── pyspark_pipeline_dag.py.j2 # Multi-app pipeline template
└── utils/
    └── airflow_client.py

infrastructure/airflow/
├── dags/                              # Generated DAG files
│   ├── pyspark_{tenant}_{app_id}.py
│   └── pipeline_{tenant}_{name}.py
└── spark_apps/
    └── jobs/                          # Pre-generated PySpark code
        ├── pyspark_{tenant}_{app_id}.py
        └── pipeline_{tenant}_{name}_{app_id}.py

infrastructure/spark/
└── jars/                              # JDBC drivers
    ├── postgresql-42.6.0.jar
    ├── mysql-connector-j-8.2.0.jar
    ├── clickhouse-jdbc-0.4.6-all.jar
    └── ojdbc8.jar
```

## Key Design Decisions

### 1. Separation of Concerns
- **PySpark App Builder (017)**: Creates and validates PySpark code from templates
- **DAG Generator (016)**: Only schedules execution of pre-generated code
- No code generation happens in DAG Generator

### 2. ADR-002 Compliance
All executable PySpark code comes from the Template Engine via PySpark App Builder.
The DAG Generator only creates scheduling wrappers (Airflow DAGs).

### 3. Template-Based DAGs
Even the Airflow DAG files are generated from Jinja2 templates for consistency.

## Acceptance Criteria

- [ ] DAG generation only works for PySpark apps with generated code
- [ ] DAGs reference pre-generated PySpark files (no inline code generation)
- [ ] Generated DAGs pass Airflow syntax check
- [ ] DAGs submit to Spark cluster successfully
- [ ] DAGs appear in Airflow UI with correct tags
- [ ] Pipeline DAGs support both parallel and sequential execution
- [ ] Schedule updates work without regenerating code
- [ ] Delete removes both DAG and associated PySpark files
- [ ] Tenant isolation enforced (can't access other tenant's DAGs)
- [ ] API endpoints properly secured with JWT

## Workflow Example

```
1. User creates PySpark app via PySpark App Builder UI
   → POST /api/v1/pyspark-apps
   
2. User generates code for the app
   → POST /api/v1/pyspark-apps/{id}/generate
   
3. User schedules the app via DAG Generator
   → POST /api/v1/dags/generate
   {
     "pyspark_app_id": "...",
     "schedule": "@hourly"
   }
   
4. Airflow runs the DAG on schedule
   → SparkSubmitOperator submits the pre-generated PySpark code
   
5. Spark cluster executes the job
   → Data flows from source to ClickHouse
```

## Reference Documents

- [PySpark App Builder](./017-pyspark-app-builder.md)
- [Airflow Templates](./011-airflow-templates.md)
- [Template Engine](./013-template-engine.md)
- [Architecture Decisions - ADR-002](../docs/requirements/Architecture_Decisions.md)
