"""
Unit tests for DAG Generator Service
=====================================

Tests for Spark-based ingestion DAG generation.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
from app.services.dag_generator import DagGenerator
from app.models.connection import DataSource, DataSourceTable
from app.services.airflow_client import AirflowClient


@pytest.fixture
def mock_airflow_client():
    """Mock Airflow client."""
    client = Mock(spec=AirflowClient)
    client.trigger_dag_parse = Mock()
    client.pause_dag = Mock()
    client.delete_dag = Mock()
    return client


@pytest.fixture
def dag_generator(mock_airflow_client):
    """Create DAG generator with mocked client."""
    with patch('app.services.dag_generator.Path.mkdir'):
        generator = DagGenerator(
            tenant_id="test-tenant-123",
            airflow_client=mock_airflow_client
        )
        return generator


@pytest.fixture
def sample_datasource():
    """Sample PostgreSQL datasource."""
    return DataSource(
        id="datasource-456",
        tenant_id="test-tenant-123",
        name="Test PostgreSQL DB",
        type="postgresql",
        host="localhost",
        port=5432,
        database="testdb",
        username="testuser",
        sync_frequency="@hourly"
    )


@pytest.fixture
def sample_tables():
    """Sample tables configuration."""
    return [
        DataSourceTable(
            source_name="public.users",
            target_name="users",
            incremental_column="updated_at",
            primary_keys=["id"]
        ),
        DataSourceTable(
            source_name="public.orders",
            target_name="orders",
            incremental_column=None,
            primary_keys=["order_id"]
        ),
    ]


class TestDagGenerator:
    """Test DAG Generator."""
    
    def test_get_jdbc_driver_postgresql(self, dag_generator):
        """Test JDBC driver for PostgreSQL."""
        driver = dag_generator._get_jdbc_driver("postgresql")
        assert driver == "org.postgresql.Driver"
    
    def test_get_jdbc_driver_mysql(self, dag_generator):
        """Test JDBC driver for MySQL."""
        driver = dag_generator._get_jdbc_driver("mysql")
        assert driver == "com.mysql.cj.jdbc.Driver"
    
    def test_get_jdbc_driver_oracle(self, dag_generator):
        """Test JDBC driver for Oracle."""
        driver = dag_generator._get_jdbc_driver("oracle")
        assert driver == "oracle.jdbc.OracleDriver"
    
    def test_get_jdbc_driver_sqlserver(self, dag_generator):
        """Test JDBC driver for SQL Server."""
        driver = dag_generator._get_jdbc_driver("sqlserver")
        assert driver == "com.microsoft.sqlserver.jdbc.SQLServerDriver"
    
    def test_get_jdbc_driver_unknown(self, dag_generator):
        """Test JDBC driver for unknown database (defaults to PostgreSQL)."""
        driver = dag_generator._get_jdbc_driver("unknown")
        assert driver == "org.postgresql.Driver"
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_generate_ingestion_dag(
        self,
        mock_mkdir,
        mock_write_text,
        dag_generator,
        sample_datasource,
        sample_tables,
        mock_airflow_client
    ):
        """Test DAG generation."""
        # Generate DAG
        dag_id = dag_generator.generate_ingestion_dag(
            datasource=sample_datasource,
            tables=sample_tables,
            schedule="@hourly"
        )
        
        # Verify DAG ID format
        assert dag_id == "ingest_test-tenant-123_datasource-456"
        
        # Verify DAG file was written
        assert mock_write_text.called
        calls = mock_write_text.call_args_list
        assert len(calls) == 2  # DAG file + config file
        
        # Verify Airflow client was called
        mock_airflow_client.trigger_dag_parse.assert_called_once()
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_generate_config_file(
        self,
        mock_mkdir,
        mock_write_text,
        dag_generator,
        sample_datasource,
        sample_tables
    ):
        """Test config file generation."""
        dag_generator.generate_ingestion_dag(
            datasource=sample_datasource,
            tables=sample_tables,
            schedule="@hourly"
        )
        
        # Get config file write call
        config_call = [
            call for call in mock_write_text.call_args_list
            if 'config.json' in str(call)
        ][0]
        
        config_content = config_call[0][0]
        config = json.loads(config_content)
        
        # Verify config structure
        assert config['tenant_id'] == "test-tenant-123"
        assert config['datasource_id'] == "datasource-456"
        assert config['datasource_type'] == "postgresql"
        assert config['connection_config']['host'] == "localhost"
        assert config['connection_config']['port'] == 5432
        assert config['connection_config']['database'] == "testdb"
        assert config['connection_config']['jdbc_driver'] == "org.postgresql.Driver"
        assert config['clickhouse_config']['database'] == "tenant_test-tenant-123"
        
        # Verify tables configuration
        assert len(config['tables']) == 2
        assert config['tables'][0]['source_table'] == "public.users"
        assert config['tables'][0]['target_table'] == "users"
        assert config['tables'][0]['mode'] == "incremental"
        assert config['tables'][0]['incremental_column'] == "updated_at"
        assert config['tables'][1]['mode'] == "full"
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_generate_dag_content(
        self,
        mock_mkdir,
        mock_write_text,
        dag_generator,
        sample_datasource,
        sample_tables
    ):
        """Test DAG file content generation."""
        dag_generator.generate_ingestion_dag(
            datasource=sample_datasource,
            tables=sample_tables,
            schedule="@daily"
        )
        
        # Get DAG file write call
        dag_call = [
            call for call in mock_write_text.call_args_list
            if '.py' in str(call) and 'config.json' not in str(call)
        ][0]
        
        dag_content = dag_call[0][0]
        
        # Verify DAG content
        assert "ingest_test-tenant-123_datasource-456" in dag_content
        assert "SparkSubmitOperator" in dag_content
        assert "@daily" in dag_content
        assert "Test PostgreSQL DB" in dag_content
        assert "spark_default" in dag_content
        assert "ingest_to_clickhouse.py" in dag_content
    
    @patch('pathlib.Path.unlink')
    @patch('pathlib.Path.exists', return_value=True)
    def test_delete_dag(
        self,
        mock_exists,
        mock_unlink,
        dag_generator,
        mock_airflow_client
    ):
        """Test DAG deletion."""
        dag_id = "ingest_test-tenant-123_datasource-456"
        
        dag_generator.delete_dag(dag_id)
        
        # Verify files were deleted
        assert mock_unlink.call_count == 2  # DAG file + config file
        
        # Verify Airflow operations
        mock_airflow_client.pause_dag.assert_called_once_with(dag_id)
        mock_airflow_client.delete_dag.assert_called_once_with(dag_id)
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.unlink')
    @patch('pathlib.Path.exists', return_value=True)
    def test_update_ingestion_dag(
        self,
        mock_exists,
        mock_unlink,
        mock_mkdir,
        mock_write_text,
        dag_generator,
        sample_datasource,
        sample_tables,
        mock_airflow_client
    ):
        """Test DAG update."""
        dag_id = dag_generator.update_ingestion_dag(
            datasource=sample_datasource,
            tables=sample_tables,
            schedule="@daily"
        )
        
        # Verify old DAG was deleted
        assert mock_unlink.call_count == 2
        mock_airflow_client.pause_dag.assert_called_once()
        mock_airflow_client.delete_dag.assert_called_once()
        
        # Verify new DAG was created
        assert mock_write_text.call_count == 2
        assert dag_id == "ingest_test-tenant-123_datasource-456"
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_generate_with_custom_schedule(
        self,
        mock_mkdir,
        mock_write_text,
        dag_generator,
        sample_datasource,
        sample_tables
    ):
        """Test DAG generation with custom cron schedule."""
        dag_generator.generate_ingestion_dag(
            datasource=sample_datasource,
            tables=sample_tables,
            schedule="0 */6 * * *"  # Every 6 hours
        )
        
        # Get DAG content
        dag_call = [
            call for call in mock_write_text.call_args_list
            if '.py' in str(call) and 'config.json' not in str(call)
        ][0]
        dag_content = dag_call[0][0]
        
        assert "0 */6 * * *" in dag_content
    
    def test_generate_with_mysql_datasource(self, dag_generator, sample_tables, mock_airflow_client):
        """Test DAG generation for MySQL datasource."""
        mysql_datasource = DataSource(
            id="mysql-123",
            tenant_id="test-tenant-123",
            name="MySQL DB",
            type="mysql",
            host="mysql.example.com",
            port=3306,
            database="mydb",
            username="mysql_user"
        )
        
        with patch('pathlib.Path.write_text'), patch('pathlib.Path.mkdir'):
            dag_generator.generate_ingestion_dag(
                datasource=mysql_datasource,
                tables=sample_tables,
                schedule="@hourly"
            )
        
        # Verify JDBC driver was correctly identified
        driver = dag_generator._get_jdbc_driver("mysql")
        assert driver == "com.mysql.cj.jdbc.Driver"
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_spark_config_generation(
        self,
        mock_mkdir,
        mock_write_text,
        dag_generator,
        sample_datasource,
        sample_tables
    ):
        """Test Spark configuration in generated DAG."""
        dag_generator.generate_ingestion_dag(
            datasource=sample_datasource,
            tables=sample_tables,
            schedule="@hourly"
        )
        
        # Get DAG content
        dag_call = [
            call for call in mock_write_text.call_args_list
            if '.py' in str(call) and 'config.json' not in str(call)
        ][0]
        dag_content = dag_call[0][0]
        
        # Verify Spark configurations
        assert "spark.executor.memory" in dag_content
        assert "spark.executor.cores" in dag_content
        assert "spark.dynamicAllocation.enabled" in dag_content
        assert "spark.dynamicAllocation.minExecutors" in dag_content
        assert "spark.dynamicAllocation.maxExecutors" in dag_content
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_airflow_parse_failure_handling(
        self,
        mock_mkdir,
        mock_write_text,
        dag_generator,
        sample_datasource,
        sample_tables,
        mock_airflow_client
    ):
        """Test graceful handling of Airflow parse trigger failure."""
        # Make trigger_dag_parse raise an exception
        mock_airflow_client.trigger_dag_parse.side_effect = Exception("Airflow API error")
        
        # Should not raise, just log warning
        dag_id = dag_generator.generate_ingestion_dag(
            datasource=sample_datasource,
            tables=sample_tables,
            schedule="@hourly"
        )
        
        assert dag_id == "ingest_test-tenant-123_datasource-456"


class TestTableConfiguration:
    """Test table configuration logic."""
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_incremental_table_config(self, mock_mkdir, mock_write_text, dag_generator, sample_datasource):
        """Test incremental table configuration."""
        tables = [
            DataSourceTable(
                source_name="public.events",
                target_name="events",
                incremental_column="event_time",
                primary_keys=["event_id"]
            )
        ]
        
        dag_generator.generate_ingestion_dag(
            datasource=sample_datasource,
            tables=tables,
            schedule="@hourly"
        )
        
        # Get config
        config_call = [
            call for call in mock_write_text.call_args_list
            if 'config.json' in str(call)
        ][0]
        config = json.loads(config_call[0][0])
        
        table_config = config['tables'][0]
        assert table_config['mode'] == 'incremental'
        assert table_config['incremental_column'] == 'event_time'
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_full_refresh_table_config(self, mock_mkdir, mock_write_text, dag_generator, sample_datasource):
        """Test full refresh table configuration."""
        tables = [
            DataSourceTable(
                source_name="public.static_data",
                target_name="static_data",
                incremental_column=None,  # No incremental column
                primary_keys=["id"]
            )
        ]
        
        dag_generator.generate_ingestion_dag(
            datasource=sample_datasource,
            tables=tables,
            schedule="@daily"
        )
        
        # Get config
        config_call = [
            call for call in mock_write_text.call_args_list
            if 'config.json' in str(call)
        ][0]
        config = json.loads(config_call[0][0])
        
        table_config = config['tables'][0]
        assert table_config['mode'] == 'full'


# ============================================================================
# PySparkDAGGenerator Tests (Prompt 016)
# ============================================================================

from app.services.dag_generator import PySparkDAGGenerator
from app.models.pyspark_app import PySparkApp, PySparkAppStatus, SourceType, WriteMode, SCDType
from app.errors import NotFoundError, ValidationError


class MockPySparkApp:
    """Mock PySpark App for testing."""
    
    def __init__(self, id, name, generated_code=None, **kwargs):
        self.id = id
        self.name = name
        self.description = kwargs.get('description', f'Test app {name}')
        self.generated_code = generated_code
        self.scd_type = kwargs.get('scd_type', Mock(value='none'))
        self.write_mode = kwargs.get('write_mode', Mock(value='append'))
        self.source_type = kwargs.get('source_type', Mock(value='table'))
        self.target_database = kwargs.get('target_database', 'analytics')
        self.target_table = kwargs.get('target_table', 'target_table')
        self.template_version = kwargs.get('template_version', '1.0.0')


@pytest.fixture
def mock_pyspark_service():
    """Mock PySpark app service."""
    service = Mock()
    return service


@pytest.fixture
def mock_template_engine():
    """Mock template engine."""
    engine = Mock()
    engine.render = Mock(return_value='# Generated DAG\nprint("hello")')
    return engine


@pytest.fixture
def pyspark_dag_generator(mock_airflow_client, mock_pyspark_service, mock_template_engine):
    """Create PySparkDAGGenerator with mocked dependencies."""
    with patch('app.services.dag_generator.Path.mkdir'):
        generator = PySparkDAGGenerator(
            tenant_id="test-tenant-123",
            template_engine=mock_template_engine,
            airflow_client=mock_airflow_client,
            pyspark_service=mock_pyspark_service,
        )
        return generator


class TestPySparkDAGGenerator:
    """Test PySparkDAGGenerator class."""
    
    def test_init(self, pyspark_dag_generator):
        """Test initialization."""
        assert pyspark_dag_generator.tenant_id == "test-tenant-123"
        assert pyspark_dag_generator.dags_path == Path('/opt/airflow/dags')
        assert pyspark_dag_generator.spark_apps_path == Path('/opt/airflow/spark_apps')
    
    def test_is_tenant_dag_pyspark(self, pyspark_dag_generator):
        """Test tenant DAG detection for pyspark DAGs."""
        assert pyspark_dag_generator._is_tenant_dag('pyspark_test-tenant-123_app1') is True
        assert pyspark_dag_generator._is_tenant_dag('pyspark_other-tenant_app1') is False
    
    def test_is_tenant_dag_pipeline(self, pyspark_dag_generator):
        """Test tenant DAG detection for pipeline DAGs."""
        assert pyspark_dag_generator._is_tenant_dag('pipeline_test-tenant-123_my_pipeline') is True
        assert pyspark_dag_generator._is_tenant_dag('pipeline_other-tenant_my_pipeline') is False
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_generate_dag_for_pyspark_app(
        self,
        mock_mkdir,
        mock_write_text,
        pyspark_dag_generator,
        mock_pyspark_service,
        mock_template_engine,
        mock_airflow_client
    ):
        """Test generating DAG for a PySpark app."""
        # Setup mock app
        mock_app = MockPySparkApp(
            id='app-123',
            name='Test App',
            generated_code='# PySpark code here\nprint("Running job")'
        )
        mock_pyspark_service.get_app.return_value = mock_app
        
        # Generate DAG
        dag_id = pyspark_dag_generator.generate_dag_for_pyspark_app(
            pyspark_app_id='app-123',
            schedule='@hourly',
            spark_config={'spark.executor.memory': '4g'},
        )
        
        # Verify DAG ID
        assert dag_id == 'pyspark_test-tenant-123_app-123'
        
        # Verify template was rendered
        mock_template_engine.render.assert_called_once()
        call_args = mock_template_engine.render.call_args
        assert call_args[0][0] == 'airflow/pyspark_job_dag.py.j2'
        context = call_args[0][1]
        assert context['dag_id'] == dag_id
        assert context['tenant_id'] == 'test-tenant-123'
        assert context['schedule'] == '@hourly'
        assert context['spark_conf']['spark.executor.memory'] == '4g'
        
        # Verify files were written
        assert mock_write_text.call_count == 2  # DAG file + PySpark job file
        
        # Verify Airflow parse triggered
        mock_airflow_client.trigger_dag_parse.assert_called_once()
    
    def test_generate_dag_app_not_found(
        self,
        pyspark_dag_generator,
        mock_pyspark_service
    ):
        """Test error when PySpark app not found."""
        mock_pyspark_service.get_app.return_value = None
        
        with pytest.raises(NotFoundError) as exc_info:
            pyspark_dag_generator.generate_dag_for_pyspark_app('nonexistent-app')
        
        assert 'not found' in str(exc_info.value).lower()
    
    def test_generate_dag_no_generated_code(
        self,
        pyspark_dag_generator,
        mock_pyspark_service
    ):
        """Test error when PySpark app has no generated code."""
        mock_app = MockPySparkApp(id='app-123', name='Test App', generated_code=None)
        mock_pyspark_service.get_app.return_value = mock_app
        
        with pytest.raises(ValidationError) as exc_info:
            pyspark_dag_generator.generate_dag_for_pyspark_app('app-123')
        
        assert 'no generated code' in str(exc_info.value).lower()
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_generate_dag_for_multiple_apps(
        self,
        mock_mkdir,
        mock_write_text,
        pyspark_dag_generator,
        mock_pyspark_service,
        mock_template_engine,
        mock_airflow_client
    ):
        """Test generating pipeline DAG for multiple apps."""
        # Setup mock apps
        mock_apps = [
            MockPySparkApp(id='app-1', name='App One', generated_code='# App 1 code'),
            MockPySparkApp(id='app-2', name='App Two', generated_code='# App 2 code'),
        ]
        mock_pyspark_service.get_app.side_effect = lambda app_id: {
            'app-1': mock_apps[0],
            'app-2': mock_apps[1],
        }.get(app_id)
        
        # Generate pipeline DAG
        dag_id = pyspark_dag_generator.generate_dag_for_multiple_apps(
            pyspark_app_ids=['app-1', 'app-2'],
            dag_name='my_pipeline',
            schedule='@daily',
            parallel=True,
        )
        
        # Verify DAG ID
        assert dag_id == 'pipeline_test-tenant-123_my_pipeline'
        
        # Verify template was rendered
        mock_template_engine.render.assert_called_once()
        call_args = mock_template_engine.render.call_args
        assert call_args[0][0] == 'airflow/pyspark_pipeline_dag.py.j2'
        context = call_args[0][1]
        assert context['dag_id'] == dag_id
        assert context['parallel'] is True
        assert len(context['apps']) == 2
        
        # Verify files were written (1 DAG + 2 PySpark job files)
        assert mock_write_text.call_count == 3
    
    def test_generate_pipeline_empty_app_list(self, pyspark_dag_generator):
        """Test error when no app IDs provided."""
        with pytest.raises(ValidationError) as exc_info:
            pyspark_dag_generator.generate_dag_for_multiple_apps(
                pyspark_app_ids=[],
                dag_name='empty_pipeline'
            )
        
        assert 'at least one' in str(exc_info.value).lower()
    
    def test_generate_pipeline_app_not_found(
        self,
        pyspark_dag_generator,
        mock_pyspark_service
    ):
        """Test error when one of the apps is not found."""
        mock_app = MockPySparkApp(id='app-1', name='App One', generated_code='# code')
        mock_pyspark_service.get_app.side_effect = lambda app_id: {
            'app-1': mock_app,
            'app-2': None,  # Not found
        }.get(app_id)
        
        with pytest.raises(NotFoundError):
            pyspark_dag_generator.generate_dag_for_multiple_apps(
                pyspark_app_ids=['app-1', 'app-2'],
                dag_name='test_pipeline'
            )
    
    @patch('pathlib.Path.read_text', return_value="schedule_interval='@hourly'")
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.exists', return_value=True)
    def test_update_dag_schedule(
        self,
        mock_exists,
        mock_write_text,
        mock_read_text,
        pyspark_dag_generator,
        mock_airflow_client
    ):
        """Test updating DAG schedule."""
        dag_id = 'pyspark_test-tenant-123_app-123'
        
        pyspark_dag_generator.update_dag_schedule(dag_id, '@daily')
        
        # Verify file was written
        assert mock_write_text.called
        new_content = mock_write_text.call_args[0][0]
        assert "@daily" in new_content
        
        # Verify Airflow parse triggered
        mock_airflow_client.trigger_dag_parse.assert_called()
    
    def test_update_dag_schedule_not_tenant_dag(self, pyspark_dag_generator):
        """Test error when updating DAG from another tenant."""
        with pytest.raises(NotFoundError):
            pyspark_dag_generator.update_dag_schedule(
                'pyspark_other-tenant_app-123',
                '@daily'
            )
    
    @patch('pathlib.Path.unlink')
    @patch('pathlib.Path.glob', return_value=[Path('/opt/airflow/spark_apps/jobs/pyspark_test-tenant-123_app.py')])
    @patch('pathlib.Path.exists', return_value=True)
    def test_delete_dag(
        self,
        mock_exists,
        mock_glob,
        mock_unlink,
        pyspark_dag_generator,
        mock_airflow_client
    ):
        """Test deleting DAG and associated files."""
        dag_id = 'pyspark_test-tenant-123_app-123'
        
        pyspark_dag_generator.delete_dag(dag_id)
        
        # Verify files were deleted
        assert mock_unlink.call_count >= 1
        
        # Verify Airflow operations
        mock_airflow_client.pause_dag.assert_called_once_with(dag_id)
        mock_airflow_client.delete_dag.assert_called_once_with(dag_id)
    
    def test_delete_dag_not_tenant_dag(self, pyspark_dag_generator):
        """Test error when deleting DAG from another tenant."""
        with pytest.raises(NotFoundError):
            pyspark_dag_generator.delete_dag('pyspark_other-tenant_app-123')
    
    @patch('pathlib.Path.glob')
    @patch('pathlib.Path.exists', return_value=True)
    def test_list_dags_for_tenant(
        self,
        mock_exists,
        mock_glob,
        pyspark_dag_generator
    ):
        """Test listing DAGs for tenant."""
        # Mock DAG files
        mock_dag1 = Mock()
        mock_dag1.stem = 'pyspark_test-tenant-123_app1'
        mock_dag1.stat.return_value.st_mtime = 1706400000
        
        mock_dag2 = Mock()
        mock_dag2.stem = 'pipeline_test-tenant-123_my_pipeline'
        mock_dag2.stat.return_value.st_mtime = 1706500000
        
        mock_dag3 = Mock()
        mock_dag3.stem = 'pyspark_other-tenant_app'  # Different tenant
        
        mock_glob.return_value = [mock_dag1, mock_dag2, mock_dag3]
        
        dags = pyspark_dag_generator.list_dags_for_tenant()
        
        # Should only return DAGs for this tenant
        assert len(dags) == 2
        assert dags[0]['dag_id'] == 'pyspark_test-tenant-123_app1'
        assert dags[0]['is_pipeline'] is False
        assert dags[1]['dag_id'] == 'pipeline_test-tenant-123_my_pipeline'
        assert dags[1]['is_pipeline'] is True
    
    @patch('pathlib.Path.read_text', return_value="schedule_interval='@daily'")
    @patch('pathlib.Path.glob', return_value=[Path('job1.py'), Path('job2.py')])
    @patch('pathlib.Path.exists', return_value=True)
    @patch('pathlib.Path.stat')
    def test_get_dag_info(
        self,
        mock_stat,
        mock_exists,
        mock_glob,
        mock_read_text,
        pyspark_dag_generator
    ):
        """Test getting DAG info."""
        mock_stat.return_value.st_mtime = 1706400000
        
        dag_id = 'pyspark_test-tenant-123_app-123'
        info = pyspark_dag_generator.get_dag_info(dag_id)
        
        assert info is not None
        assert info['dag_id'] == dag_id
        assert info['schedule'] == '@daily'
        assert info['is_pipeline'] is False
        assert info['job_count'] == 2
    
    def test_get_dag_info_not_tenant_dag(self, pyspark_dag_generator):
        """Test getting info for DAG from another tenant."""
        info = pyspark_dag_generator.get_dag_info('pyspark_other-tenant_app')
        assert info is None
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_default_spark_config(
        self,
        mock_mkdir,
        mock_write_text,
        pyspark_dag_generator,
        mock_pyspark_service,
        mock_template_engine
    ):
        """Test default Spark configuration is applied."""
        mock_app = MockPySparkApp(id='app-123', name='Test', generated_code='# code')
        mock_pyspark_service.get_app.return_value = mock_app
        
        pyspark_dag_generator.generate_dag_for_pyspark_app('app-123')
        
        # Check template context includes default config
        call_args = mock_template_engine.render.call_args
        context = call_args[0][1]
        spark_conf = context['spark_conf']
        
        assert spark_conf['spark.executor.memory'] == '2g'
        assert spark_conf['spark.executor.cores'] == '2'
        assert spark_conf['spark.dynamicAllocation.enabled'] == 'true'
    
    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.mkdir')
    def test_custom_spark_config_overrides_defaults(
        self,
        mock_mkdir,
        mock_write_text,
        pyspark_dag_generator,
        mock_pyspark_service,
        mock_template_engine
    ):
        """Test custom Spark config overrides defaults."""
        mock_app = MockPySparkApp(id='app-123', name='Test', generated_code='# code')
        mock_pyspark_service.get_app.return_value = mock_app
        
        pyspark_dag_generator.generate_dag_for_pyspark_app(
            'app-123',
            spark_config={
                'spark.executor.memory': '8g',
                'custom.setting': 'value',
            }
        )
        
        call_args = mock_template_engine.render.call_args
        context = call_args[0][1]
        spark_conf = context['spark_conf']
        
        # Custom value should override default
        assert spark_conf['spark.executor.memory'] == '8g'
        # Custom setting should be added
        assert spark_conf['custom.setting'] == 'value'
        # Other defaults should remain
        assert spark_conf['spark.executor.cores'] == '2'

