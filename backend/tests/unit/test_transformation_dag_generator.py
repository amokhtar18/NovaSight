"""
Tests for Transformation DAG Generator and Pipeline Generator

Tests Prompt 021: Transformation DAG Generator implementation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from app.services.transformation_dag_generator import (
    TransformationDAGGenerator,
    TransformationDAGGeneratorError,
    get_transformation_dag_generator,
)
from app.services.pipeline_generator import (
    PipelineGenerator,
    PipelineGeneratorError,
    PipelineValidationError,
    FullPipelineBuilder,
    get_pipeline_generator,
)
from app.models.data_source import DataSourceTable, DataSourceColumn


class MockDataSource:
    """Mock DataConnection for testing."""
    
    def __init__(
        self,
        id=None,
        tenant_id=None,
        name="test_source",
        extra_params=None,
    ):
        self.id = id or uuid4()
        self.tenant_id = tenant_id or uuid4()
        self.name = name
        self.extra_params = extra_params or {}


class TestTransformationDAGGenerator:
    """Tests for TransformationDAGGenerator class."""
    
    @pytest.fixture
    def mock_template_engine(self):
        """Create mock template engine."""
        engine = Mock()
        engine.render.return_value = "# Generated DAG content"
        return engine
    
    @pytest.fixture
    def mock_dbt_service(self):
        """Create mock dbt service."""
        return Mock()
    
    @pytest.fixture
    def mock_airflow_client(self):
        """Create mock Airflow client."""
        client = Mock()
        client.trigger_dag_parse.return_value = None
        client.pause_dag.return_value = None
        client.delete_dag.return_value = None
        return client
    
    @pytest.fixture
    def generator(self, mock_template_engine, mock_dbt_service, mock_airflow_client):
        """Create TransformationDAGGenerator instance."""
        gen = TransformationDAGGenerator(
            template_engine=mock_template_engine,
            dbt_service=mock_dbt_service,
            airflow_client=mock_airflow_client,
        )
        # Use temp directory instead of /opt/airflow/dags
        gen.dags_path = Path('/tmp/test_dags')
        return gen
    
    @pytest.fixture
    def datasource(self):
        """Create mock datasource."""
        return MockDataSource(
            name="Sales Database",
            extra_params={"sync_frequency": "@hourly"},
        )
    
    def test_normalize_name_basic(self, generator):
        """Test name normalization."""
        assert generator._normalize_name("Sales Database") == "sales_database"
        assert generator._normalize_name("my-source") == "my_source"
        assert generator._normalize_name("MySource123") == "mysource123"
    
    def test_normalize_name_with_numbers_first(self, generator):
        """Test name normalization when name starts with number."""
        assert generator._normalize_name("123source") == "ds_123source"
    
    def test_normalize_name_empty(self, generator):
        """Test name normalization with empty string."""
        assert generator._normalize_name("") == "default"
        assert generator._normalize_name("---") == "default"
    
    def test_build_task_configs_with_tests(self, generator):
        """Test task config generation with tests enabled."""
        tasks = generator._build_task_configs(
            datasource_name="test_source",
            staging_select="stg_test_source_*",
            mart_select="tag:mart",
            run_tests=True,
        )
        
        assert len(tasks) == 4
        assert tasks[0]['task_id'] == 'run_staging'
        assert tasks[0]['dbt_command'] == 'run'
        assert tasks[1]['task_id'] == 'test_staging'
        assert tasks[1]['dbt_command'] == 'test'
        assert tasks[2]['task_id'] == 'run_marts'
        assert tasks[3]['task_id'] == 'test_marts'
    
    def test_build_task_configs_without_tests(self, generator):
        """Test task config generation without tests."""
        tasks = generator._build_task_configs(
            datasource_name="test_source",
            staging_select="stg_test_source_*",
            mart_select="tag:mart",
            run_tests=False,
        )
        
        assert len(tasks) == 2
        assert tasks[0]['task_id'] == 'run_staging'
        assert tasks[1]['task_id'] == 'run_marts'
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.write_text')
    def test_generate_transformation_dag(
        self, mock_write, mock_mkdir, generator, datasource, mock_template_engine
    ):
        """Test DAG generation."""
        tenant_id = str(uuid4())
        
        dag_id = generator.generate_transformation_dag(
            tenant_id=tenant_id,
            datasource=datasource,
            schedule="@daily",
        )
        
        # Verify DAG ID format
        assert dag_id == f"transform_{tenant_id}_{datasource.id}"
        
        # Verify template was rendered
        mock_template_engine.render.assert_called_once()
        call_args = mock_template_engine.render.call_args
        assert call_args[0][0] == 'airflow/datasource_transformation_dag.py.j2'
        
        # Verify context
        context = call_args[0][1]
        assert context['tenant_id'] == tenant_id
        assert context['schedule'] == '@daily'
        assert 'tasks' in context
        assert 'ingestion_dag_id' in context
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.write_text')
    def test_generate_transformation_dag_with_specific_models(
        self, mock_write, mock_mkdir, generator, datasource, mock_template_engine
    ):
        """Test DAG generation with specific models."""
        tenant_id = str(uuid4())
        models = ['stg_users', 'stg_orders', 'stg_products']
        
        dag_id = generator.generate_transformation_dag(
            tenant_id=tenant_id,
            datasource=datasource,
            models=models,
        )
        
        # Verify template context includes models
        call_args = mock_template_engine.render.call_args
        context = call_args[0][1]
        
        # First task should use the specified models
        tasks = context['tasks']
        assert 'stg_users stg_orders stg_products' in tasks[0]['select']
    
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.write_text')
    def test_generate_transformation_dag_default_schedule(
        self, mock_write, mock_mkdir, generator, datasource, mock_template_engine
    ):
        """Test DAG generation uses datasource sync_frequency if no schedule provided."""
        tenant_id = str(uuid4())
        
        generator.generate_transformation_dag(
            tenant_id=tenant_id,
            datasource=datasource,
            schedule=None,
        )
        
        call_args = mock_template_engine.render.call_args
        context = call_args[0][1]
        
        # Should use sync_frequency from extra_params
        assert context['schedule'] == '@hourly'
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.unlink')
    def test_delete_dag(self, mock_unlink, mock_exists, generator, mock_airflow_client):
        """Test DAG deletion."""
        mock_exists.return_value = True
        
        generator.delete_dag("test_dag_id")
        
        mock_unlink.assert_called_once()
        mock_airflow_client.pause_dag.assert_called_once_with("test_dag_id")
        mock_airflow_client.delete_dag.assert_called_once_with("test_dag_id")


class TestPipelineGenerator:
    """Tests for PipelineGenerator class."""
    
    @pytest.fixture
    def mock_ingestion_generator(self):
        """Create mock ingestion generator."""
        gen = Mock()
        gen.generate_ingestion_dag.return_value = "ingest_test_dag"
        gen.delete_dag.return_value = None
        return gen
    
    @pytest.fixture
    def mock_transform_generator(self):
        """Create mock transformation generator."""
        gen = Mock()
        gen.generate_transformation_dag.return_value = "transform_test_dag"
        gen.delete_dag.return_value = None
        return gen
    
    @pytest.fixture
    def pipeline_generator(self, mock_ingestion_generator, mock_transform_generator):
        """Create PipelineGenerator instance."""
        return PipelineGenerator(
            ingestion_generator=mock_ingestion_generator,
            transform_generator=mock_transform_generator,
        )
    
    @pytest.fixture
    def datasource(self):
        """Create mock datasource."""
        return MockDataSource(name="Test Source")
    
    @pytest.fixture
    def tables(self):
        """Create mock tables."""
        return [
            DataSourceTable(
                name="users",
                source_name="users",
                columns=[
                    DataSourceColumn(name="id", source_name="id", type="integer"),
                    DataSourceColumn(name="email", source_name="email", type="varchar"),
                ],
            ),
            DataSourceTable(
                name="orders",
                source_name="orders",
                columns=[
                    DataSourceColumn(name="id", source_name="id", type="integer"),
                    DataSourceColumn(name="user_id", source_name="user_id", type="integer"),
                ],
            ),
        ]
    
    def test_generate_full_pipeline(
        self, pipeline_generator, datasource, tables,
        mock_ingestion_generator, mock_transform_generator
    ):
        """Test full pipeline generation."""
        result = pipeline_generator.generate_full_pipeline(
            datasource=datasource,
            tables=tables,
            schedule='@hourly',
        )
        
        assert 'ingestion_dag_id' in result
        assert 'transformation_dag_id' in result
        assert result['tables_count'] == 2
        assert result['schedule'] == '@hourly'
        
        # Verify generators were called
        mock_ingestion_generator.generate_ingestion_dag.assert_called_once()
        mock_transform_generator.generate_transformation_dag.assert_called_once()
    
    def test_generate_full_pipeline_no_tables(self, pipeline_generator, datasource):
        """Test pipeline generation fails with no tables."""
        with pytest.raises(PipelineValidationError) as exc_info:
            pipeline_generator.generate_full_pipeline(
                datasource=datasource,
                tables=[],
            )
        
        assert "At least one table is required" in str(exc_info.value)
    
    def test_delete_pipeline(
        self, pipeline_generator, datasource,
        mock_ingestion_generator, mock_transform_generator
    ):
        """Test pipeline deletion."""
        tenant_id = str(datasource.tenant_id)
        
        pipeline_generator.delete_pipeline(tenant_id, datasource)
        
        mock_ingestion_generator.delete_dag.assert_called_once()
        mock_transform_generator.delete_dag.assert_called_once()


class TestFullPipelineBuilder:
    """Tests for FullPipelineBuilder class."""
    
    @pytest.fixture
    def datasource(self):
        """Create mock datasource."""
        return MockDataSource(name="Test Source")
    
    @pytest.fixture
    def table(self):
        """Create mock table."""
        return DataSourceTable(
            name="users",
            source_name="users",
            columns=[
                DataSourceColumn(name="id", source_name="id", type="integer"),
            ],
        )
    
    def test_builder_fluent_interface(self, datasource, table):
        """Test builder fluent interface."""
        builder = (
            FullPipelineBuilder(datasource)
            .add_table(table)
            .with_schedule('@daily')
            .with_tests(True)
            .with_marts(True)
        )
        
        assert builder.schedule == '@daily'
        assert builder.run_tests is True
        assert builder.include_marts is True
        assert len(builder.tables) == 1
    
    def test_builder_with_dependencies(self, datasource, table):
        """Test builder with upstream/downstream dependencies."""
        builder = (
            FullPipelineBuilder(datasource)
            .add_table(table)
            .with_upstream_dependency('upstream_dag')
            .with_downstream_trigger('downstream_dag')
        )
        
        assert 'upstream_dag' in builder.upstream_dags
        assert 'downstream_dag' in builder.downstream_dags
    
    def test_builder_no_tables_error(self, datasource):
        """Test builder fails without tables."""
        builder = FullPipelineBuilder(datasource)
        
        with pytest.raises(PipelineValidationError) as exc_info:
            builder.build()
        
        assert "No tables specified" in str(exc_info.value)
    
    @patch.object(PipelineGenerator, 'generate_full_pipeline')
    def test_builder_build_calls_generator(self, mock_generate, datasource, table):
        """Test builder.build() calls pipeline generator."""
        mock_generate.return_value = {'ingestion_dag_id': 'test', 'transformation_dag_id': 'test2'}
        
        builder = (
            FullPipelineBuilder(datasource)
            .add_table(table)
            .with_schedule('@hourly')
        )
        
        result = builder.build()
        
        mock_generate.assert_called_once()
        assert result == {'ingestion_dag_id': 'test', 'transformation_dag_id': 'test2'}


class TestFactoryFunctions:
    """Tests for factory functions."""
    
    def test_get_transformation_dag_generator(self):
        """Test factory function returns generator instance."""
        generator = get_transformation_dag_generator()
        assert isinstance(generator, TransformationDAGGenerator)
    
    def test_get_pipeline_generator(self):
        """Test factory function returns generator instance."""
        generator = get_pipeline_generator()
        assert isinstance(generator, PipelineGenerator)
