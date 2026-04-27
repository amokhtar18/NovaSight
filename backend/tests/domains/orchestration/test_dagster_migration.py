"""
Tests for Dagster migration.
Verifies that all Airflow functionality is preserved.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


class TestDagsterClient:
    """Test DagsterClient methods match AirflowClient interface."""

    def test_client_initialization(self):
        """Test DagsterClient initializes correctly."""
        from app.domains.orchestration.infrastructure.dagster_client import DagsterClient
        
        client = DagsterClient(host="localhost", port=3000, tenant_id="test-tenant")
        assert client._host == "localhost"
        assert client._port == 3000
        assert client._tenant_id == "test-tenant"

    def test_graphql_url_construction(self):
        """Test GraphQL URL is constructed correctly."""
        from app.domains.orchestration.infrastructure.dagster_client import DagsterClient
        
        with patch('flask.current_app') as mock_app:
            mock_app.config.get.side_effect = lambda key, default: default
            
            client = DagsterClient(
                host="dagster-server",
                port=3000,
                use_infrastructure_config=False,
            )
            assert client.graphql_url == "http://dagster-server:3000/graphql"

    def test_trigger_job_success(self):
        """Test trigger_job returns proper format on success."""
        from app.domains.orchestration.infrastructure.dagster_client import DagsterClient
        
        client = DagsterClient(host="localhost", port=3000, use_infrastructure_config=False)
        
        with patch.object(client, '_execute_query') as mock_query:
            mock_query.return_value = {
                "launchRun": {
                    "run": {
                        "runId": "test-run-123",
                        "status": "STARTED",
                    }
                }
            }
            
            with patch('flask.current_app'):
                result = client.trigger_job("test_job")
            
            assert result["success"] is True
            assert result["run_id"] == "test-run-123"
            assert result["status"] == "STARTED"

    def test_trigger_job_failure(self):
        """Test trigger_job handles errors properly."""
        from app.domains.orchestration.infrastructure.dagster_client import DagsterClient
        
        client = DagsterClient(host="localhost", port=3000, use_infrastructure_config=False)
        
        with patch.object(client, '_execute_query') as mock_query:
            mock_query.return_value = {
                "launchRun": {
                    "message": "Job not found",
                }
            }
            
            with patch('flask.current_app'):
                result = client.trigger_job("nonexistent_job")
            
            assert result["success"] is False
            assert "error" in result

    def test_get_job_runs_returns_list(self):
        """Test get_job_runs returns properly formatted list."""
        from app.domains.orchestration.infrastructure.dagster_client import DagsterClient
        
        client = DagsterClient(host="localhost", port=3000, use_infrastructure_config=False)
        
        with patch.object(client, '_execute_query') as mock_query:
            mock_query.return_value = {
                "pipelineOrError": {
                    "runs": [
                        {
                            "runId": "run-1",
                            "status": "SUCCESS",
                            "startTime": "1708365600",
                            "endTime": "1708369200",
                        },
                        {
                            "runId": "run-2",
                            "status": "FAILURE",
                            "startTime": "1708362000",
                            "endTime": "1708363800",
                        },
                    ]
                }
            }
            
            with patch('flask.current_app'):
                runs = client.get_job_runs("test_job", limit=10)
            
            assert len(runs) == 2
            assert runs[0].run_id == "run-1"
            assert runs[0].state == "success"
            assert runs[1].run_id == "run-2"
            assert runs[1].state == "failed"

    def test_start_schedule(self):
        """Test start_schedule returns proper format."""
        from app.domains.orchestration.infrastructure.dagster_client import DagsterClient
        
        client = DagsterClient(host="localhost", port=3000, use_infrastructure_config=False)
        
        with patch.object(client, '_execute_query') as mock_query:
            mock_query.return_value = {
                "startSchedule": {
                    "scheduleState": {
                        "status": "RUNNING",
                    }
                }
            }
            
            with patch('flask.current_app'):
                result = client.start_schedule("test_schedule")
            
            assert result["success"] is True
            assert result["status"] == "RUNNING"

    def test_stop_schedule(self):
        """Test stop_schedule returns proper format."""
        from app.domains.orchestration.infrastructure.dagster_client import DagsterClient
        
        client = DagsterClient(host="localhost", port=3000, use_infrastructure_config=False)
        
        with patch.object(client, '_execute_query') as mock_query:
            mock_query.return_value = {
                "stopRunningSchedule": {
                    "scheduleState": {
                        "status": "STOPPED",
                    }
                }
            }
            
            with patch('flask.current_app'):
                result = client.stop_schedule("test_schedule")
            
            assert result["success"] is True
            assert result["status"] == "STOPPED"

    def test_reload_code_location(self):
        """Test reload_code_location returns success on LOADED status."""
        from app.domains.orchestration.infrastructure.dagster_client import DagsterClient
        
        client = DagsterClient(host="localhost", port=3000, use_infrastructure_config=False)
        
        with patch.object(client, '_execute_query') as mock_query:
            mock_query.return_value = {
                "reloadRepositoryLocation": {
                    "loadStatus": "LOADED",
                }
            }
            
            with patch('flask.current_app'):
                result = client.reload_code_location()
            
            assert result["success"] is True


class TestJobRun:
    """Test JobRun dataclass and state mapping."""

    def test_state_mapping_success(self):
        """Test SUCCESS maps to success."""
        from app.domains.orchestration.infrastructure.dagster_client import JobRun
        
        run = JobRun(
            job_name="test_job",
            run_id="run-1",
            status="SUCCESS",
            start_time=datetime.now(),
            end_time=datetime.now(),
        )
        assert run.state == "success"

    def test_state_mapping_failure(self):
        """Test FAILURE maps to failed."""
        from app.domains.orchestration.infrastructure.dagster_client import JobRun
        
        run = JobRun(
            job_name="test_job",
            run_id="run-1",
            status="FAILURE",
            start_time=datetime.now(),
            end_time=datetime.now(),
        )
        assert run.state == "failed"

    def test_state_mapping_running(self):
        """Test STARTED maps to running."""
        from app.domains.orchestration.infrastructure.dagster_client import JobRun
        
        run = JobRun(
            job_name="test_job",
            run_id="run-1",
            status="STARTED",
            start_time=datetime.now(),
            end_time=None,
        )
        assert run.state == "running"


class TestAssetFactory:
    """Test asset generation from DagConfig."""

    def test_factory_initialization(self):
        """Test AssetFactory initializes correctly."""
        from app.domains.orchestration.infrastructure.asset_factory import AssetFactory
        
        factory = AssetFactory("test-tenant")
        assert factory.tenant_id == "test-tenant"

    def test_build_assets_from_dag_config(self):
        """Test building assets from a mock DagConfig (dlt task)."""
        from app.domains.orchestration.infrastructure.asset_factory import AssetFactory
        from app.domains.orchestration.domain.models import TaskType

        factory = AssetFactory("test-tenant")

        mock_task = Mock()
        mock_task.task_id = "dlt_task"
        mock_task.task_type = TaskType.DLT_RUN
        mock_task.config = {"pipeline_id": "00000000-0000-0000-0000-000000000001"}
        mock_task.depends_on = []

        mock_dag = Mock()
        mock_dag.dag_id = "test_dag"
        mock_dag.tasks = [mock_task]

        assets = factory.build_assets_from_dag_config(mock_dag)
        assert len(assets) == 1

    def test_build_dbt_asset(self):
        """Test building a dbt asset."""
        from app.domains.orchestration.infrastructure.asset_factory import AssetFactory
        from app.domains.orchestration.domain.models import TaskType
        
        factory = AssetFactory("test-tenant")
        
        mock_task = Mock()
        mock_task.task_id = "dbt_run"
        mock_task.task_type = TaskType.DBT_RUN
        mock_task.config = {"models": ["staging.*"], "full_refresh": False}
        mock_task.depends_on = []
        
        mock_dag = Mock()
        mock_dag.dag_id = "dbt_pipeline"
        mock_dag.tasks = [mock_task]
        
        assets = factory.build_assets_from_dag_config(mock_dag)
        assert len(assets) == 1

    def test_asset_dependencies(self):
        """Test that task dependencies become asset dependencies."""
        from app.domains.orchestration.infrastructure.asset_factory import AssetFactory
        from app.domains.orchestration.domain.models import TaskType

        factory = AssetFactory("test-tenant")

        # Two dlt tasks chained — extract → transform
        mock_task1 = Mock()
        mock_task1.task_id = "extract"
        mock_task1.task_type = TaskType.DLT_RUN
        mock_task1.config = {"pipeline_id": "00000000-0000-0000-0000-000000000001"}
        mock_task1.depends_on = []

        mock_task2 = Mock()
        mock_task2.task_id = "transform"
        mock_task2.task_type = TaskType.DBT_RUN
        mock_task2.config = {"models": ["staging.*"]}
        mock_task2.depends_on = ["extract"]

        mock_dag = Mock()
        mock_dag.dag_id = "etl_pipeline"
        mock_dag.tasks = [mock_task1, mock_task2]

        assets = factory.build_assets_from_dag_config(mock_dag)
        assert len(assets) == 2

    def test_only_dlt_and_dbt_task_types_supported(self):
        """Scheduler must reject any task type that is not dlt or dbt."""
        from app.domains.orchestration.infrastructure.asset_factory import (
            AssetFactory,
            ALLOWED_TASK_TYPES,
        )

        factory = AssetFactory("test-tenant")

        # Allowed set is exactly the dlt + dbt task types.
        assert ALLOWED_TASK_TYPES == frozenset({
            "dlt_run",
            "dbt_run",
            "dbt_test",
            "dbt_run_lake",
            "dbt_run_warehouse",
        })

        # An unknown / legacy task type produces zero assets.
        legacy_task = Mock()
        legacy_task.task_id = "legacy"
        legacy_task.task_type = Mock()
        legacy_task.task_type.value = "spark_submit"
        legacy_task.config = {}
        legacy_task.depends_on = []

        mock_dag = Mock()
        mock_dag.dag_id = "legacy_dag"
        mock_dag.tasks = [legacy_task]

        assert factory.build_assets_from_dag_config(mock_dag) == []

    def test_task_type_enum_only_contains_dlt_and_dbt(self):
        """Domain TaskType enum is restricted to dlt + dbt members."""
        from app.domains.orchestration.domain.models import TaskType

        names = {member.name for member in TaskType}
        assert names == {
            "DLT_RUN",
            "DBT_RUN",
            "DBT_TEST",
            "DBT_RUN_LAKE",
            "DBT_RUN_WAREHOUSE",
        }


class TestScheduleFactory:
    """Test schedule generation from DagConfig."""

    def test_factory_initialization(self):
        """Test ScheduleFactory initializes correctly."""
        from app.domains.orchestration.infrastructure.schedule_factory import ScheduleFactory
        
        factory = ScheduleFactory("test-tenant")
        assert factory.tenant_id == "test-tenant"

    def test_preset_to_cron_mapping(self):
        """Test preset schedule values map to correct cron expressions."""
        from app.domains.orchestration.infrastructure.schedule_factory import ScheduleFactory
        
        factory = ScheduleFactory("test-tenant")
        
        assert factory.PRESET_TO_CRON["hourly"] == "0 * * * *"
        assert factory.PRESET_TO_CRON["daily"] == "0 0 * * *"
        assert factory.PRESET_TO_CRON["weekly"] == "0 0 * * 0"
        assert factory.PRESET_TO_CRON["@daily"] == "0 0 * * *"

    def test_manual_schedule_returns_none(self):
        """Test manual schedule type returns None."""
        from app.domains.orchestration.infrastructure.schedule_factory import ScheduleFactory
        from app.domains.orchestration.domain.models import ScheduleType
        
        factory = ScheduleFactory("test-tenant")
        
        mock_dag = Mock()
        mock_dag.dag_id = "manual_dag"
        mock_dag.schedule_type = ScheduleType.MANUAL
        
        schedule = factory.build_schedule_from_dag_config(mock_dag)
        assert schedule is None

    def test_cron_schedule_creation(self):
        """Test creating a schedule from cron expression."""
        from app.domains.orchestration.infrastructure.schedule_factory import ScheduleFactory
        from app.domains.orchestration.domain.models import ScheduleType, DagStatus
        
        factory = ScheduleFactory("test-tenant")
        
        mock_dag = Mock()
        mock_dag.dag_id = "scheduled_dag"
        mock_dag.full_dag_id = "test-tenant_scheduled_dag"
        mock_dag.schedule_type = ScheduleType.CRON
        mock_dag.schedule_cron = "0 6 * * *"
        mock_dag.status = DagStatus.ACTIVE
        mock_dag.timezone = "UTC"
        mock_dag.description = "Test scheduled DAG"
        
        schedule = factory.build_schedule_from_dag_config(mock_dag)
        
        assert schedule is not None
        assert schedule.cron_schedule == "0 6 * * *"


class TestAPICompatibility:
    """Verify API contract is maintained after migration."""

    @pytest.fixture
    def mock_dag_service(self):
        """Create a mock DagService with Dagster backend."""
        with patch('app.domains.orchestration.application.dag_service.DagsterClient'):
            with patch('app.domains.orchestration.application.dag_service.AssetFactory'):
                with patch('app.domains.orchestration.application.dag_service.ScheduleFactory'):
                    from app.domains.orchestration.application.dag_service import DagService
                    service = DagService(tenant_id="test-tenant")
                    yield service

    def test_trigger_dag_returns_run_id(self, mock_dag_service):
        """Test trigger_dag returns run_id in expected format."""
        mock_dag_service.dagster_client.trigger_job.return_value = {
            "success": True,
            "run_id": "dagster-run-123",
            "status": "STARTED",
        }
        
        mock_dag = Mock()
        mock_dag.full_dag_id = "test-tenant_test_dag"
        
        with patch.object(mock_dag_service, 'get_dag', return_value=mock_dag):
            result = mock_dag_service.trigger_dag("test_dag", conf={})
        
        assert result["success"] is True
        assert "run_id" in result

    def test_pause_dag_calls_stop_schedule(self, mock_dag_service):
        """Test pause_dag calls stop_schedule on DagsterClient."""
        mock_dag_service.dagster_client.stop_schedule.return_value = {
            "success": True,
            "status": "STOPPED",
        }
        
        mock_dag = Mock()
        mock_dag.full_dag_id = "test-tenant_test_dag"
        
        with patch.object(mock_dag_service, 'get_dag', return_value=mock_dag):
            with patch('app.extensions.db'):
                result = mock_dag_service.pause_dag("test_dag")
        
        mock_dag_service.dagster_client.stop_schedule.assert_called_once()
        assert result["success"] is True

    def test_unpause_dag_calls_start_schedule(self, mock_dag_service):
        """Test unpause_dag calls start_schedule on DagsterClient."""
        mock_dag_service.dagster_client.start_schedule.return_value = {
            "success": True,
            "status": "RUNNING",
        }
        
        mock_dag = Mock()
        mock_dag.full_dag_id = "test-tenant_test_dag"
        
        with patch.object(mock_dag_service, 'get_dag', return_value=mock_dag):
            with patch('app.extensions.db'):
                result = mock_dag_service.unpause_dag("test_dag")
        
        mock_dag_service.dagster_client.start_schedule.assert_called_once()
        assert result["success"] is True
