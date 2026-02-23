"""
NovaSight Dagster Resources
============================

Resource definitions for Dagster assets and jobs.
"""

from orchestration.resources.spark_resource import SparkResource, DynamicSparkResource
from orchestration.resources.clickhouse_resource import ClickHouseResource, DynamicClickHouseResource
from orchestration.resources.database_resource import DatabaseResource
from orchestration.resources.remote_spark_resource import (
    RemoteSparkResource,
    DynamicRemoteSparkResource,
    SparkJobResult,
)

__all__ = [
    "SparkResource",
    "DynamicSparkResource",
    "ClickHouseResource",
    "DynamicClickHouseResource",
    "DatabaseResource",
    "RemoteSparkResource",
    "DynamicRemoteSparkResource",
    "SparkJobResult",
]
