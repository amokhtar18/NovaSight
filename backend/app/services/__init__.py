"""
NovaSight Services
==================

Business logic services for the application.
"""

from app.services.auth_service import AuthService
from app.services.tenant_service import TenantService
from app.services.user_service import UserService
from app.services.connection_service import ConnectionService
from app.services.dag_service import DagService
from app.services.dag_generator import DagGenerator, PySparkDAGGenerator
from app.services.airflow_client import AirflowClient
from app.services.password_service import PasswordService, password_service
from app.services.token_service import TokenBlacklist, LoginAttemptTracker, token_blacklist, login_tracker

# Template Engine (ADR-002 compliant code generation)
from app.services.template_engine import (
    TemplateEngine,
    template_engine,
    TemplateParameterValidator,
    SQLIdentifier,
    ColumnDefinition,
    TableDefinition,
    DbtModelDefinition,
    AirflowDagDefinition,
)

# dbt Service
from app.services.dbt_service import DbtService, get_dbt_service, DbtResult

# dbt Model Generator
from app.services.dbt_model_generator import (
    DbtModelGenerator,
    get_dbt_model_generator,
    DbtModelGeneratorError,
    ModelGenerationError,
)

# ClickHouse Client
from app.services.clickhouse_client import (
    ClickHouseClient,
    QueryResult,
    get_clickhouse_client,
)

# Semantic Layer Service
from app.services.semantic_service import (
    SemanticService,
    SemanticServiceError,
    ModelNotFoundError,
    DimensionNotFoundError,
    MeasureNotFoundError,
    QueryBuildError,
)

# Transformation DAG Generator (Prompt 021)
from app.services.transformation_dag_generator import (
    TransformationDAGGenerator,
    TransformationDAGGeneratorError,
    get_transformation_dag_generator,
)

# Pipeline Generator (Prompt 021)
from app.services.pipeline_generator import (
    PipelineGenerator,
    PipelineGeneratorError,
    PipelineValidationError,
    FullPipelineBuilder,
    get_pipeline_generator,
)

__all__ = [
    # Auth & User Services
    "AuthService",
    "TenantService",
    "UserService",
    "PasswordService",
    "password_service",
    "TokenBlacklist",
    "LoginAttemptTracker",
    "token_blacklist",
    "login_tracker",
    # Data Services
    "ConnectionService",
    "DagService",
    "AirflowClient",
    # Template Engine
    "TemplateEngine",
    "template_engine",
    "TemplateParameterValidator",
    "SQLIdentifier",
    "ColumnDefinition",
    "TableDefinition",
    "DbtModelDefinition",
    "AirflowDagDefinition",
    # DAG Generator
    "DagGenerator",
    "PySparkDAGGenerator",
    # dbt Service
    "DbtService",
    "get_dbt_service",
    "DbtResult",
    # dbt Model Generator
    "DbtModelGenerator",
    "get_dbt_model_generator",
    "DbtModelGeneratorError",
    "ModelGenerationError",
    # ClickHouse Client
    "ClickHouseClient",
    "QueryResult",
    "get_clickhouse_client",
    # Semantic Layer Service
    "SemanticService",
    "SemanticServiceError",
    "ModelNotFoundError",
    "DimensionNotFoundError",
    "MeasureNotFoundError",
    "QueryBuildError",
    # Transformation DAG Generator (Prompt 021)
    "TransformationDAGGenerator",
    "TransformationDAGGeneratorError",
    "get_transformation_dag_generator",
    # Pipeline Generator (Prompt 021)
    "PipelineGenerator",
    "PipelineGeneratorError",
    "PipelineValidationError",
    "FullPipelineBuilder",
    "get_pipeline_generator",
]
