"""
NovaSight Data Sources — Connector Registry
=============================================

Registry for managing data source connectors.

Canonical location: ``app.domains.datasources.infrastructure.connectors.registry``
"""

from typing import Dict, Type, List
import logging

from app.domains.datasources.infrastructure.connectors.base import (
    BaseConnector,
    ConnectionConfig,
)

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """Registry for data source connectors."""

    _connectors: Dict[str, Type[BaseConnector]] = {}

    @classmethod
    def register(cls, connector_class: Type[BaseConnector]) -> Type[BaseConnector]:
        connector_type = connector_class.connector_type
        if not connector_type or connector_type == "base":
            raise ValueError(f"Invalid connector type: {connector_type}")
        if connector_type in cls._connectors:
            logger.warning(
                f"Connector {connector_type} already registered, overwriting"
            )
        cls._connectors[connector_type] = connector_class
        logger.info(f"Registered connector: {connector_type}")
        return connector_class

    @classmethod
    def get(cls, connector_type: str) -> Type[BaseConnector]:
        if connector_type not in cls._connectors:
            available = ", ".join(cls._connectors.keys())
            raise ValueError(
                f"Unknown connector type: {connector_type}. "
                f"Available connectors: {available}"
            )
        return cls._connectors[connector_type]

    @classmethod
    def list_connectors(cls) -> List[str]:
        return sorted(cls._connectors.keys())

    @classmethod
    def get_connector_info(cls, connector_type: str) -> Dict:
        connector_class = cls.get(connector_type)
        return {
            "type": connector_class.connector_type,
            "default_port": connector_class.default_port,
            "supports_ssl": connector_class.supports_ssl,
            "supported_auth_methods": connector_class.supported_auth_methods,
            "class_name": connector_class.__name__,
        }

    @classmethod
    def create_connector(
        cls, connector_type: str, config: ConnectionConfig
    ) -> BaseConnector:
        connector_class = cls.get(connector_type)
        return connector_class(config)


# ─── Auto-register built-in connectors ─────────────────────────────

from app.domains.datasources.infrastructure.connectors.postgresql import (
    PostgreSQLConnector,
)
from app.domains.datasources.infrastructure.connectors.mysql import MySQLConnector
from app.domains.datasources.infrastructure.connectors.oracle import OracleConnector
from app.domains.datasources.infrastructure.connectors.flatfile import FlatFileConnector
from app.domains.datasources.infrastructure.connectors.excel import ExcelConnector
from app.domains.datasources.infrastructure.connectors.sqlite import SQLiteConnector

ConnectorRegistry.register(PostgreSQLConnector)
ConnectorRegistry.register(MySQLConnector)
ConnectorRegistry.register(OracleConnector)
ConnectorRegistry.register(FlatFileConnector)
ConnectorRegistry.register(ExcelConnector)
ConnectorRegistry.register(SQLiteConnector)

logger.info(
    f"Registered {len(ConnectorRegistry.list_connectors())} connectors: "
    f"{', '.join(ConnectorRegistry.list_connectors())}"
)
