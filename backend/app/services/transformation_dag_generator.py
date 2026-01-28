"""
NovaSight Transformation DAG Generator
======================================

Generates Airflow DAGs for dbt transformation workflows.
Triggered after ingestion DAGs complete via ExternalTaskSensor.

Implements Prompt 021: Transformation DAG Generator.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import json
import logging

from app.models.connection import DataConnection
from app.models.data_source import DataSourceTable
from app.services.template_engine import TemplateEngine
from app.services.dbt_service import DbtService
from app.services.airflow_client import AirflowClient

logger = logging.getLogger(__name__)


class TransformationDAGGeneratorError(Exception):
    """Base exception for transformation DAG generator errors."""
    pass


class TransformationDAGGenerator:
    """
    Generates Airflow DAGs for dbt transformations.
    
    This service creates DAGs that:
    1. Wait for ingestion DAGs to complete (via ExternalTaskSensor)
    2. Run dbt staging models for the data source
    3. Run dbt tests on staging models
    4. Run dbt mart models (downstream aggregations)
    5. Run dbt tests on mart models
    
    All DAG code is generated from pre-approved templates (ADR-002 compliant).
    """
    
    # Default dbt configuration
    DEFAULT_DBT_CONFIG = {
        'project_dir': '/opt/airflow/dbt',
        'profiles_dir': '/opt/airflow/dbt',
        'target': 'prod',
    }
    
    def __init__(
        self,
        template_engine: Optional[TemplateEngine] = None,
        dbt_service: Optional[DbtService] = None,
        airflow_client: Optional[AirflowClient] = None,
    ):
        """
        Initialize transformation DAG generator.
        
        Args:
            template_engine: Template engine for rendering DAG files
            dbt_service: dbt service for model information
            airflow_client: Airflow client for triggering DAG parsing
        """
        self.template_engine = template_engine or TemplateEngine()
        self.dbt_service = dbt_service or DbtService()
        self.airflow_client = airflow_client or AirflowClient()
        self.dags_path = Path('/opt/airflow/dags')
    
    def generate_transformation_dag(
        self,
        tenant_id: str,
        datasource: DataConnection,
        models: Optional[List[str]] = None,
        schedule: Optional[str] = None,
        run_tests: bool = True,
        retries: int = 2,
        retry_delay_minutes: int = 5,
        execution_timeout_hours: int = 3,
    ) -> str:
        """
        Generate transformation DAG for a tenant/datasource.
        
        This DAG waits for the corresponding ingestion DAG to complete,
        then runs dbt models and tests.
        
        Args:
            tenant_id: Tenant identifier
            datasource: Data source configuration
            models: Optional list of specific models to run.
                   If None, runs all models for this data source.
            schedule: Cron expression or Airflow preset.
                     If None, uses the datasource's sync frequency.
            run_tests: Whether to run dbt tests after models
            retries: Number of retries on failure
            retry_delay_minutes: Minutes between retries
            execution_timeout_hours: Maximum execution time in hours
            
        Returns:
            Generated DAG ID
        """
        # Get dependent ingestion DAG ID
        ingestion_dag_id = f'ingest_{tenant_id}_{datasource.id}'
        
        # Build model selector based on datasource name
        datasource_name = self._normalize_name(datasource.name)
        
        if models:
            # Use specific models provided
            staging_select = ' '.join(models)
            mart_select = 'tag:mart'
        else:
            # All staging models for this source
            staging_select = f'stg_{datasource_name}_*'
            mart_select = 'tag:mart'
        
        # Build task configurations
        tasks = self._build_task_configs(
            datasource_name=datasource_name,
            staging_select=staging_select,
            mart_select=mart_select,
            run_tests=run_tests,
        )
        
        # Determine schedule
        effective_schedule = schedule
        if effective_schedule is None:
            # Try to get from datasource if it has sync_frequency
            if hasattr(datasource, 'extra_params') and datasource.extra_params:
                effective_schedule = datasource.extra_params.get('sync_frequency', '@hourly')
            else:
                effective_schedule = '@hourly'
        
        # Prepare template context
        dag_id = f'transform_{tenant_id}_{datasource.id}'
        
        context = {
            'tenant_id': tenant_id,
            'datasource_id': str(datasource.id),
            'datasource_name': datasource_name,
            'dag_id': dag_id,
            'ingestion_dag_id': ingestion_dag_id,
            'schedule': effective_schedule,
            'tasks': tasks,
            'run_tests': run_tests,
            'dbt_project_dir': self.DEFAULT_DBT_CONFIG['project_dir'],
            'dbt_profiles_dir': self.DEFAULT_DBT_CONFIG['profiles_dir'],
            'dbt_target': self.DEFAULT_DBT_CONFIG['target'],
            'retries': retries,
            'retry_delay_minutes': retry_delay_minutes,
            'execution_timeout_hours': execution_timeout_hours,
            'start_date': '2024-01-01',
            'catchup': False,
            'generated_at': datetime.utcnow().isoformat(),
        }
        
        # Render DAG from template
        dag_content = self.template_engine.render(
            'airflow/datasource_transformation_dag.py.j2',
            context
        )
        
        # Ensure directory exists
        self.dags_path.mkdir(parents=True, exist_ok=True)
        
        # Write DAG file
        dag_file = self.dags_path / f'{dag_id}.py'
        dag_file.write_text(dag_content)
        logger.info(f"Generated transformation DAG: {dag_id}")
        
        # Trigger DAG parsing in Airflow
        try:
            self.airflow_client.trigger_dag_parse()
        except Exception as e:
            logger.warning(f"Failed to trigger DAG parse: {e}")
        
        return dag_id
    
    def _build_task_configs(
        self,
        datasource_name: str,
        staging_select: str,
        mart_select: str,
        run_tests: bool,
    ) -> List[Dict[str, Any]]:
        """
        Build task configuration for the transformation DAG.
        
        Args:
            datasource_name: Normalized datasource name
            staging_select: dbt select expression for staging models
            mart_select: dbt select expression for mart models
            run_tests: Whether to include test tasks
            
        Returns:
            List of task configurations
        """
        tasks = [
            {
                'task_id': 'run_staging',
                'dbt_command': 'run',
                'select': staging_select,
                'description': f'Run staging models for {datasource_name}',
            },
        ]
        
        if run_tests:
            tasks.append({
                'task_id': 'test_staging',
                'dbt_command': 'test',
                'select': staging_select,
                'description': f'Test staging models for {datasource_name}',
            })
        
        tasks.append({
            'task_id': 'run_marts',
            'dbt_command': 'run',
            'select': mart_select,
            'description': 'Run mart models',
        })
        
        if run_tests:
            tasks.append({
                'task_id': 'test_marts',
                'dbt_command': 'test',
                'select': mart_select,
                'description': 'Test mart models',
            })
        
        return tasks
    
    def _normalize_name(self, name: str) -> str:
        """
        Normalize a name to be safe for dbt model naming.
        
        Args:
            name: Original name
            
        Returns:
            Normalized name (lowercase, underscores)
        """
        import re
        # Convert to lowercase and replace non-alphanumeric with underscores
        normalized = re.sub(r'[^a-zA-Z0-9]+', '_', name.lower())
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        # Ensure it doesn't start with a number
        if normalized and normalized[0].isdigit():
            normalized = f'ds_{normalized}'
        return normalized or 'default'
    
    def update_transformation_dag(
        self,
        tenant_id: str,
        datasource: DataConnection,
        models: Optional[List[str]] = None,
        schedule: Optional[str] = None,
        run_tests: bool = True,
    ) -> str:
        """
        Update an existing transformation DAG.
        
        Args:
            tenant_id: Tenant identifier
            datasource: Data source configuration
            models: Optional list of specific models to run
            schedule: Optional new schedule
            run_tests: Whether to run dbt tests
            
        Returns:
            Updated DAG ID
        """
        # Delete existing DAG
        dag_id = f'transform_{tenant_id}_{datasource.id}'
        self.delete_dag(dag_id)
        
        # Generate new DAG
        return self.generate_transformation_dag(
            tenant_id=tenant_id,
            datasource=datasource,
            models=models,
            schedule=schedule,
            run_tests=run_tests,
        )
    
    def delete_dag(self, dag_id: str) -> None:
        """
        Delete a transformation DAG file.
        
        Args:
            dag_id: DAG identifier
        """
        dag_file = self.dags_path / f'{dag_id}.py'
        if dag_file.exists():
            dag_file.unlink()
            logger.info(f"Deleted DAG file: {dag_file}")
        
        # Pause and delete from Airflow
        try:
            self.airflow_client.pause_dag(dag_id)
            self.airflow_client.delete_dag(dag_id)
        except Exception as e:
            logger.warning(f"Failed to delete DAG from Airflow: {e}")
    
    def generate_incremental_transformation_dag(
        self,
        tenant_id: str,
        datasource: DataConnection,
        incremental_models: List[str],
        schedule: str = '@hourly',
    ) -> str:
        """
        Generate a DAG for incremental transformations only.
        
        This DAG is optimized for frequent runs on incremental models.
        
        Args:
            tenant_id: Tenant identifier
            datasource: Data source configuration
            incremental_models: List of incremental model names
            schedule: Cron expression (default: hourly)
            
        Returns:
            Generated DAG ID
        """
        datasource_name = self._normalize_name(datasource.name)
        dag_id = f'transform_incr_{tenant_id}_{datasource.id}'
        
        context = {
            'tenant_id': tenant_id,
            'datasource_id': str(datasource.id),
            'datasource_name': datasource_name,
            'dag_id': dag_id,
            'ingestion_dag_id': f'ingest_{tenant_id}_{datasource.id}',
            'schedule': schedule,
            'models': incremental_models,
            'incremental_only': True,
            'dbt_project_dir': self.DEFAULT_DBT_CONFIG['project_dir'],
            'dbt_profiles_dir': self.DEFAULT_DBT_CONFIG['profiles_dir'],
            'dbt_target': self.DEFAULT_DBT_CONFIG['target'],
            'start_date': '2024-01-01',
            'catchup': False,
            'generated_at': datetime.utcnow().isoformat(),
        }
        
        dag_content = self.template_engine.render(
            'airflow/incremental_transformation_dag.py.j2',
            context
        )
        
        self.dags_path.mkdir(parents=True, exist_ok=True)
        dag_file = self.dags_path / f'{dag_id}.py'
        dag_file.write_text(dag_content)
        logger.info(f"Generated incremental transformation DAG: {dag_id}")
        
        try:
            self.airflow_client.trigger_dag_parse()
        except Exception as e:
            logger.warning(f"Failed to trigger DAG parse: {e}")
        
        return dag_id


# Factory function for easy instantiation
def get_transformation_dag_generator(
    template_engine: Optional[TemplateEngine] = None,
    dbt_service: Optional[DbtService] = None,
) -> TransformationDAGGenerator:
    """
    Get a transformation DAG generator instance.
    
    Args:
        template_engine: Optional template engine instance
        dbt_service: Optional dbt service instance
        
    Returns:
        TransformationDAGGenerator instance
    """
    return TransformationDAGGenerator(
        template_engine=template_engine,
        dbt_service=dbt_service,
    )
