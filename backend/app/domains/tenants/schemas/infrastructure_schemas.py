"""
NovaSight Tenants Domain — Infrastructure Schemas
===================================================

Canonical location: ``app.domains.tenants.schemas.infrastructure_schemas``

Marshmallow schemas for infrastructure server configuration API.
"""

from marshmallow import (
    Schema,
    fields,
    validate,
    validates,
    validates_schema,
    ValidationError,
    EXCLUDE,
)


# =====================================================
# Common base
# =====================================================


class BaseInfrastructureConfigSchema(Schema):
    """Base schema with common fields for all infrastructure configs."""

    id = fields.UUID(dump_only=True)
    service_type = fields.Str(
        required=True,
        validate=validate.OneOf(
            ["clickhouse", "spark", "dagster", "ollama", "airflow"]
        ),
        metadata={"description": "Infrastructure service type"},
    )
    tenant_id = fields.UUID(
        allow_none=True,
        load_default=None,
        metadata={
            "description": "Tenant ID (null for global)"
        },
    )
    name = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
        metadata={"description": "Configuration display name"},
    )
    description = fields.Str(
        allow_none=True,
        validate=validate.Length(max=1000),
        metadata={"description": "Configuration description"},
    )
    host = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=255),
        metadata={"description": "Server hostname or IP"},
    )
    port = fields.Int(
        required=True,
        validate=validate.Range(min=1, max=65535),
        metadata={"description": "Server port"},
    )
    is_active = fields.Bool(
        load_default=True,
        metadata={"description": "Whether this configuration is active"},
    )
    is_system_default = fields.Bool(
        dump_only=True,
        metadata={"description": "System default (read-only)"},
    )
    settings = fields.Dict(
        load_default=dict,
        metadata={"description": "Service-specific settings"},
    )
    created_at = fields.Str(dump_only=True)
    updated_at = fields.Str(dump_only=True)
    last_test_at = fields.Str(dump_only=True, allow_none=True)
    last_test_success = fields.Bool(dump_only=True)
    last_test_message = fields.Str(dump_only=True)


# =====================================================
# ClickHouse
# =====================================================


class ClickHouseSettingsSchema(Schema):
    """ClickHouse-specific settings."""

    class Meta:
        unknown = EXCLUDE

    database = fields.Str(
        required=True,
        validate=validate.Length(min=1, max=100),
    )
    user = fields.Str(load_default="default", validate=validate.Length(max=100))
    password = fields.Str(load_only=True, allow_none=True)
    secure = fields.Bool(load_default=False)
    connect_timeout = fields.Int(
        load_default=10, validate=validate.Range(min=1, max=300)
    )
    send_receive_timeout = fields.Int(
        load_default=300, validate=validate.Range(min=1, max=3600)
    )
    verify_ssl = fields.Bool(load_default=True)


class ClickHouseConfigCreateSchema(BaseInfrastructureConfigSchema):
    service_type = fields.Str(
        dump_default="clickhouse",
        load_default="clickhouse",
        validate=validate.Equal("clickhouse"),
    )
    settings = fields.Nested(ClickHouseSettingsSchema, required=True)

    @validates_schema
    def validate_clickhouse_config(self, data, **kwargs):
        settings = data.get("settings", {})
        if not settings.get("database"):
            raise ValidationError(
                {
                    "settings": {
                        "database": [
                            "Database name is required for ClickHouse"
                        ]
                    }
                }
            )


# =====================================================
# Spark
# =====================================================


class SparkSettingsSchema(Schema):
    """Spark-specific settings."""

    class Meta:
        unknown = EXCLUDE

    master_url = fields.Str(
        required=True, validate=validate.Length(min=1, max=255)
    )
    deploy_mode = fields.Str(
        load_default="client",
        validate=validate.OneOf(["client", "cluster"]),
    )
    driver_memory = fields.Str(
        load_default="2g",
        validate=validate.Regexp(
            r"^\d+[gGmMkK]$", error="Invalid memory format (e.g., 2g)"
        ),
    )
    executor_memory = fields.Str(
        load_default="2g",
        validate=validate.Regexp(
            r"^\d+[gGmMkK]$", error="Invalid memory format"
        ),
    )
    executor_cores = fields.Int(
        load_default=2, validate=validate.Range(min=1, max=32)
    )
    dynamic_allocation = fields.Bool(load_default=True)
    min_executors = fields.Int(
        load_default=1, validate=validate.Range(min=0, max=100)
    )
    max_executors = fields.Int(
        load_default=10, validate=validate.Range(min=1, max=500)
    )
    num_executors = fields.Int(
        load_default=2, validate=validate.Range(min=1, max=100)
    )
    spark_home = fields.Str(load_default="/opt/spark")
    additional_configs = fields.Dict(load_default=dict)
    # Remote Spark server configuration
    ssh_host = fields.Str(load_default="", validate=validate.Length(max=255))
    ssh_user = fields.Str(load_default="spark", validate=validate.Length(max=64))
    webui_port = fields.Int(load_default=8080, validate=validate.Range(min=1, max=65535))


class SparkConfigCreateSchema(BaseInfrastructureConfigSchema):
    service_type = fields.Str(
        dump_default="spark",
        load_default="spark",
        validate=validate.Equal("spark"),
    )
    settings = fields.Nested(SparkSettingsSchema, required=True)

    @validates_schema
    def validate_spark_config(self, data, **kwargs):
        settings = data.get("settings", {})
        if settings.get("min_executors", 1) > settings.get(
            "max_executors", 10
        ):
            raise ValidationError(
                {
                    "settings": {
                        "min_executors": [
                            "min_executors cannot be greater than max_executors"
                        ]
                    }
                }
            )


# =====================================================
# Airflow
# =====================================================


class AirflowSettingsSchema(Schema):
    """Airflow-specific settings."""

    class Meta:
        unknown = EXCLUDE

    base_url = fields.Str(
        required=True, validate=validate.URL(schemes=["http", "https"])
    )
    api_version = fields.Str(
        load_default="v1", validate=validate.OneOf(["v1"])
    )
    username = fields.Str(
        load_default="airflow", validate=validate.Length(max=100)
    )
    password = fields.Str(load_only=True, allow_none=True)
    dag_folder = fields.Str(load_default="/opt/airflow/dags")
    request_timeout = fields.Int(
        load_default=30, validate=validate.Range(min=5, max=300)
    )
    verify_ssl = fields.Bool(load_default=True)


class AirflowConfigCreateSchema(BaseInfrastructureConfigSchema):
    """
    .. deprecated:: Use DagsterConfigCreateSchema instead.
    """
    service_type = fields.Str(
        dump_default="airflow",
        load_default="airflow",
        validate=validate.Equal("airflow"),
    )
    settings = fields.Nested(AirflowSettingsSchema, required=True)


# =====================================================
# Dagster (Primary Orchestrator)
# =====================================================


class DagsterSettingsSchema(Schema):
    """Dagster orchestrator-specific settings."""

    class Meta:
        unknown = EXCLUDE

    graphql_url = fields.Str(
        required=True,
        validate=validate.URL(schemes=["http", "https"]),
        metadata={"description": "Dagster GraphQL endpoint URL"},
    )
    request_timeout = fields.Int(
        load_default=30,
        validate=validate.Range(min=5, max=300),
        metadata={"description": "Request timeout in seconds"},
    )
    verify_ssl = fields.Bool(
        load_default=True,
        metadata={"description": "Verify SSL certificates"},
    )
    max_concurrent_runs = fields.Int(
        load_default=10,
        validate=validate.Range(min=1, max=100),
        metadata={"description": "Maximum concurrent pipeline runs"},
    )
    spark_concurrency_limit = fields.Int(
        load_default=3,
        validate=validate.Range(min=1, max=50),
        metadata={"description": "Max concurrent Spark jobs"},
    )
    dbt_concurrency_limit = fields.Int(
        load_default=2,
        validate=validate.Range(min=1, max=20),
        metadata={"description": "Max concurrent dbt runs"},
    )
    compute_logs_dir = fields.Str(
        load_default="/var/dagster/logs",
        validate=validate.Length(max=255),
        metadata={"description": "Directory for compute logs"},
    )


class DagsterConfigCreateSchema(BaseInfrastructureConfigSchema):
    """Schema for creating Dagster configuration."""

    service_type = fields.Str(
        dump_default="dagster",
        load_default="dagster",
        validate=validate.Equal("dagster"),
    )
    settings = fields.Nested(DagsterSettingsSchema, required=True)


# =====================================================
# Ollama
# =====================================================


class OllamaSettingsSchema(Schema):
    """Ollama LLM server-specific settings."""

    class Meta:
        unknown = EXCLUDE

    base_url = fields.Str(
        required=True, validate=validate.URL(schemes=["http", "https"])
    )
    default_model = fields.Str(
        load_default="llama3.2", validate=validate.Length(min=1, max=100)
    )
    request_timeout = fields.Int(
        load_default=120, validate=validate.Range(min=10, max=600)
    )
    num_ctx = fields.Int(
        load_default=4096, validate=validate.Range(min=512, max=131072)
    )
    temperature = fields.Float(
        load_default=0.7, validate=validate.Range(min=0.0, max=2.0)
    )
    keep_alive = fields.Str(
        load_default="5m", validate=validate.Length(max=20)
    )


class OllamaConfigCreateSchema(BaseInfrastructureConfigSchema):
    service_type = fields.Str(
        dump_default="ollama",
        load_default="ollama",
        validate=validate.Equal("ollama"),
    )
    settings = fields.Nested(OllamaSettingsSchema, required=True)


# =====================================================
# Generic CRUD schemas
# =====================================================


class InfrastructureConfigResponseSchema(BaseInfrastructureConfigSchema):
    """Response schema for infrastructure configuration."""

    pass


class InfrastructureConfigListSchema(Schema):
    """Paginated infrastructure config list."""

    items = fields.List(
        fields.Nested(InfrastructureConfigResponseSchema)
    )
    total = fields.Int()
    page = fields.Int()
    per_page = fields.Int()
    pages = fields.Int()


class InfrastructureConfigUpdateSchema(Schema):
    """Schema for updating infrastructure configuration."""

    name = fields.Str(validate=validate.Length(min=1, max=255))
    description = fields.Str(
        allow_none=True, validate=validate.Length(max=1000)
    )
    host = fields.Str(validate=validate.Length(min=1, max=255))
    port = fields.Int(validate=validate.Range(min=1, max=65535))
    is_active = fields.Bool()
    settings = fields.Dict()


class InfrastructureConfigTestSchema(Schema):
    """Schema for testing infrastructure connection."""

    config_id = fields.UUID(allow_none=True)
    service_type = fields.Str(
        validate=validate.OneOf(
            ["clickhouse", "spark", "dagster", "ollama", "airflow"]
        )
    )
    host = fields.Str(validate=validate.Length(min=1, max=255))
    port = fields.Int(validate=validate.Range(min=1, max=65535))
    settings = fields.Dict()

    @validates_schema
    def validate_test_params(self, data, **kwargs):
        config_id = data.get("config_id")
        has_inline = all(
            [data.get("service_type"), data.get("host"), data.get("port")]
        )
        if not config_id and not has_inline:
            raise ValidationError(
                "Either config_id or inline configuration "
                "(service_type, host, port) is required"
            )


class InfrastructureConfigTestResultSchema(Schema):
    """Connection test result."""

    success = fields.Bool(required=True)
    message = fields.Str(required=True)
    latency_ms = fields.Float(allow_none=True)
    server_version = fields.Str(allow_none=True)
    details = fields.Dict(allow_none=True)
