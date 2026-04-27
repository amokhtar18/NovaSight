"""
NovaSight Data Sources — Connectors Package
=============================================

Pluggable connector architecture for database integrations.

Canonical location: ``app.domains.datasources.infrastructure.connectors``
"""

from app.domains.datasources.infrastructure.connectors.base import (
    BaseConnector,
    ConnectionConfig,
    ConnectorException,
    ConnectionTestException,
)
from app.domains.datasources.domain.value_objects import ColumnInfo, TableInfo
from app.domains.datasources.infrastructure.connectors.registry import ConnectorRegistry
from app.domains.datasources.infrastructure.connectors.postgresql import PostgreSQLConnector
from app.domains.datasources.infrastructure.connectors.mysql import MySQLConnector
from app.domains.datasources.infrastructure.connectors.oracle import OracleConnector

__all__ = [
    "BaseConnector",
    "ConnectionConfig",
    "ColumnInfo",
    "TableInfo",
    "ConnectorException",
    "ConnectionTestException",
    "ConnectorRegistry",
    "PostgreSQLConnector",
    "MySQLConnector",
    "OracleConnector",
]