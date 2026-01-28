"""
NovaSight Pipeline Generator
============================

Generates complete ingestion + transformation pipelines.
Orchestrates DagGenerator and TransformationDAGGenerator to create
end-to-end data pipelines.

Implements Prompt 021: Full Pipeline Generation.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from app.models.connection import DataConnection
from app.models.data_source import DataSourceTable
from app.services.dag_generator import DagGenerator
from app.services.transformation_dag_generator import TransformationDAGGenerator
from app.services.template_engine import TemplateEngine
from app.services.dbt_service import DbtService
from app.services.airflow_client import AirflowClient

logger = logging.getLogger(__name__)


class PipelineGeneratorError(Exception):
    """Base exception for pipeline generator errors."""
    pass


class PipelineValidationError(PipelineGeneratorError):
    """Raised when pipeline validation fails."""
    pass


class PipelineGenerator:
    """
    Generates complete ingestion + transformation pipelines.
    
    This service coordinates:
    1. Ingestion DAG generation (extract from source → load to ClickHouse)
    2. Transformation DAG generation (dbt models → staging → marts)
    
    The transformation DAG waits for the ingestion DAG to complete
    via ExternalTaskSensor before running.
    
    All generated code comes from pre-approved templates (ADR-002 compliant).
    """
    
    def __init__(
        self,
        ingestion_generator: Optional[DagGenerator] = None,
        transform_generator: Optional[TransformationDAGGenerator] = None,
        template_engine: Optional[TemplateEngine] = None,
        airflow_client: Optional[AirflowClient] = None,
    ):
        """
        Initialize pipeline generator.
        
        Args:
            ingestion_generator: DAG generator for ingestion pipelines
            transform_generator: DAG generator for transformation pipelines
            template_engine: Template engine instance
            airflow_client: Airflow client instance
        """
        self.template_engine = template_engine or TemplateEngine()
        self.airflow_client = airflow_client or AirflowClient()
        
        # These will be initialized per-tenant when needed
        self._ingestion_generator = ingestion_generator
        self._transform_generator = transform_generator or TransformationDAGGenerator(
            template_engine=self.template_engine,
            airflow_client=self.airflow_client,
        )
    
    def _get_ingestion_generator(self, tenant_id: str) -> DagGenerator:
        """Get or create ingestion generator for tenant."""
        if self._ingestion_generator is None:
            return DagGenerator(
                tenant_id=tenant_id,
                airflow_client=self.airflow_client,
            )
        return self._ingestion_generator
    
    def generate_full_pipeline(
        self,
        datasource: DataConnection,
        tables: List[DataSourceTable],
        schedule: str = '@hourly',
        run_dbt_tests: bool = True,
        include_marts: bool = True,
    ) -> Dict[str, str]:
        """
        Generate both ingestion and transformation DAGs.
        
        This creates a complete data pipeline:
        1. Ingestion DAG: Extracts data from source and loads to ClickHouse
        2. Transformation DAG: Runs dbt models after ingestion completes
        
        Args:
            datasource: Data source configuration
            tables: List of tables to ingest
            schedule: Airflow schedule expression (e.g., '@hourly', '0 * * * *')
            run_dbt_tests: Whether to run dbt tests after transformations
            include_marts: Whether to include mart models in transformation
            
        Returns:
            Dictionary with ingestion_dag_id and transformation_dag_id
        """
        tenant_id = str(datasource.tenant_id)
        
        # Validate inputs
        if not tables:
            raise PipelineValidationError("At least one table is required for pipeline generation")
        
        logger.info(
            f"Generating full pipeline for datasource {datasource.name} "
            f"(tenant: {tenant_id}, tables: {len(tables)})"
        )
        
        # Generate ingestion DAG
        ingestion_generator = self._get_ingestion_generator(tenant_id)
        ingest_dag_id = ingestion_generator.generate_ingestion_dag(
            datasource=datasource,
            tables=tables,
            schedule=schedule,
        )
        logger.info(f"Generated ingestion DAG: {ingest_dag_id}")
        
        # Generate transformation DAG (triggered after ingestion)
        # The transformation DAG uses ExternalTaskSensor to wait for ingestion
        transform_dag_id = self._transform_generator.generate_transformation_dag(
            tenant_id=tenant_id,
            datasource=datasource,
            models=None,  # Run all models for this datasource
            schedule=None,  # Triggered by sensor (not scheduled independently)
            run_tests=run_dbt_tests,
        )
        logger.info(f"Generated transformation DAG: {transform_dag_id}")
        
        return {
            'ingestion_dag_id': ingest_dag_id,
            'transformation_dag_id': transform_dag_id,
            'tenant_id': tenant_id,
            'datasource_id': str(datasource.id),
            'tables_count': len(tables),
            'schedule': schedule,
            'generated_at': datetime.utcnow().isoformat(),
        }
    
    def generate_pipeline_with_dependencies(
        self,
        datasource: DataConnection,
        tables: List[DataSourceTable],
        upstream_dags: Optional[List[str]] = None,
        downstream_dags: Optional[List[str]] = None,
        schedule: str = '@hourly',
    ) -> Dict[str, Any]:
        """
        Generate a pipeline with upstream and downstream dependencies.
        
        Args:
            datasource: Data source configuration
            tables: List of tables to ingest
            upstream_dags: DAG IDs that must complete before this pipeline starts
            downstream_dags: DAG IDs to trigger after this pipeline completes
            schedule: Airflow schedule expression
            
        Returns:
            Dictionary with DAG IDs and dependency configuration
        """
        tenant_id = str(datasource.tenant_id)
        
        # Generate base pipeline
        result = self.generate_full_pipeline(
            datasource=datasource,
            tables=tables,
            schedule=schedule,
        )
        
        # Add dependency information
        result['upstream_dags'] = upstream_dags or []
        result['downstream_dags'] = downstream_dags or []
        
        # Generate orchestration DAG if there are dependencies
        if upstream_dags or downstream_dags:
            orchestration_dag_id = self._generate_orchestration_dag(
                tenant_id=tenant_id,
                pipeline_dags=[result['ingestion_dag_id'], result['transformation_dag_id']],
                upstream_dags=upstream_dags or [],
                downstream_dags=downstream_dags or [],
                schedule=schedule,
            )
            result['orchestration_dag_id'] = orchestration_dag_id
        
        return result
    
    def _generate_orchestration_dag(
        self,
        tenant_id: str,
        pipeline_dags: List[str],
        upstream_dags: List[str],
        downstream_dags: List[str],
        schedule: str,
    ) -> str:
        """
        Generate an orchestration DAG that coordinates multiple pipelines.
        
        Args:
            tenant_id: Tenant identifier
            pipeline_dags: DAG IDs in this pipeline
            upstream_dags: Upstream DAG dependencies
            downstream_dags: Downstream DAG triggers
            schedule: Airflow schedule expression
            
        Returns:
            Orchestration DAG ID
        """
        dag_id = f'orchestrate_{tenant_id}_{pipeline_dags[0].split("_")[-1]}'
        
        context = {
            'dag_id': dag_id,
            'tenant_id': tenant_id,
            'pipeline_dags': pipeline_dags,
            'upstream_dags': upstream_dags,
            'downstream_dags': downstream_dags,
            'schedule': schedule,
            'generated_at': datetime.utcnow().isoformat(),
        }
        
        dag_content = self.template_engine.render(
            'airflow/orchestration_dag.py.j2',
            context
        )
        
        from pathlib import Path
        dags_path = Path('/opt/airflow/dags')
        dags_path.mkdir(parents=True, exist_ok=True)
        
        dag_file = dags_path / f'{dag_id}.py'
        dag_file.write_text(dag_content)
        logger.info(f"Generated orchestration DAG: {dag_id}")
        
        return dag_id
    
    def update_pipeline(
        self,
        datasource: DataConnection,
        tables: List[DataSourceTable],
        schedule: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Update an existing pipeline.
        
        Deletes existing DAGs and regenerates them.
        
        Args:
            datasource: Data source configuration
            tables: List of tables to ingest
            schedule: Optional new schedule
            
        Returns:
            Dictionary with updated DAG IDs
        """
        tenant_id = str(datasource.tenant_id)
        
        # Delete existing DAGs
        self.delete_pipeline(tenant_id, datasource)
        
        # Generate new pipeline
        return self.generate_full_pipeline(
            datasource=datasource,
            tables=tables,
            schedule=schedule or '@hourly',
        )
    
    def delete_pipeline(
        self,
        tenant_id: str,
        datasource: DataConnection,
    ) -> None:
        """
        Delete all DAGs associated with a pipeline.
        
        Args:
            tenant_id: Tenant identifier
            datasource: Data source configuration
        """
        # Delete ingestion DAG
        ingestion_generator = self._get_ingestion_generator(tenant_id)
        ingest_dag_id = f'ingest_{tenant_id}_{datasource.id}'
        ingestion_generator.delete_dag(ingest_dag_id)
        
        # Delete transformation DAG
        transform_dag_id = f'transform_{tenant_id}_{datasource.id}'
        self._transform_generator.delete_dag(transform_dag_id)
        
        logger.info(f"Deleted pipeline for datasource {datasource.id}")
    
    def get_pipeline_status(
        self,
        tenant_id: str,
        datasource: DataConnection,
    ) -> Dict[str, Any]:
        """
        Get status of a pipeline's DAGs.
        
        Args:
            tenant_id: Tenant identifier
            datasource: Data source configuration
            
        Returns:
            Dictionary with status of each DAG
        """
        ingest_dag_id = f'ingest_{tenant_id}_{datasource.id}'
        transform_dag_id = f'transform_{tenant_id}_{datasource.id}'
        
        try:
            ingest_status = self.airflow_client.get_dag_status(ingest_dag_id)
        except Exception as e:
            ingest_status = {'error': str(e)}
        
        try:
            transform_status = self.airflow_client.get_dag_status(transform_dag_id)
        except Exception as e:
            transform_status = {'error': str(e)}
        
        return {
            'ingestion': {
                'dag_id': ingest_dag_id,
                'status': ingest_status,
            },
            'transformation': {
                'dag_id': transform_dag_id,
                'status': transform_status,
            },
        }


class FullPipelineBuilder:
    """
    Fluent builder for creating complex pipelines.
    
    Usage:
        pipeline = (
            FullPipelineBuilder(datasource)
            .add_tables(tables)
            .with_schedule('@hourly')
            .with_tests(True)
            .with_upstream_dependency('dag_id')
            .build()
        )
    """
    
    def __init__(self, datasource: DataConnection):
        """Initialize builder with datasource."""
        self.datasource = datasource
        self.tables: List[DataSourceTable] = []
        self.schedule = '@hourly'
        self.run_tests = True
        self.include_marts = True
        self.upstream_dags: List[str] = []
        self.downstream_dags: List[str] = []
        self._pipeline_generator: Optional[PipelineGenerator] = None
    
    def add_tables(self, tables: List[DataSourceTable]) -> 'FullPipelineBuilder':
        """Add tables to ingest."""
        self.tables.extend(tables)
        return self
    
    def add_table(self, table: DataSourceTable) -> 'FullPipelineBuilder':
        """Add a single table to ingest."""
        self.tables.append(table)
        return self
    
    def with_schedule(self, schedule: str) -> 'FullPipelineBuilder':
        """Set the pipeline schedule."""
        self.schedule = schedule
        return self
    
    def with_tests(self, enabled: bool = True) -> 'FullPipelineBuilder':
        """Enable or disable dbt tests."""
        self.run_tests = enabled
        return self
    
    def with_marts(self, enabled: bool = True) -> 'FullPipelineBuilder':
        """Enable or disable mart model runs."""
        self.include_marts = enabled
        return self
    
    def with_upstream_dependency(self, dag_id: str) -> 'FullPipelineBuilder':
        """Add an upstream DAG dependency."""
        self.upstream_dags.append(dag_id)
        return self
    
    def with_downstream_trigger(self, dag_id: str) -> 'FullPipelineBuilder':
        """Add a downstream DAG to trigger."""
        self.downstream_dags.append(dag_id)
        return self
    
    def with_generator(self, generator: PipelineGenerator) -> 'FullPipelineBuilder':
        """Set a custom pipeline generator."""
        self._pipeline_generator = generator
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and generate the pipeline."""
        if not self.tables:
            raise PipelineValidationError("No tables specified for pipeline")
        
        generator = self._pipeline_generator or PipelineGenerator()
        
        if self.upstream_dags or self.downstream_dags:
            return generator.generate_pipeline_with_dependencies(
                datasource=self.datasource,
                tables=self.tables,
                upstream_dags=self.upstream_dags,
                downstream_dags=self.downstream_dags,
                schedule=self.schedule,
            )
        else:
            return generator.generate_full_pipeline(
                datasource=self.datasource,
                tables=self.tables,
                schedule=self.schedule,
                run_dbt_tests=self.run_tests,
                include_marts=self.include_marts,
            )


# Factory function for easy instantiation
def get_pipeline_generator() -> PipelineGenerator:
    """Get a pipeline generator instance."""
    return PipelineGenerator()
