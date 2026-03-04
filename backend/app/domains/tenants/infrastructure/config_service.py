"""
NovaSight Tenants Domain — Infrastructure Config Service
==========================================================

Canonical location: ``app.domains.tenants.infrastructure.config_service``

CRUD, connection testing, and credential management for
ClickHouse / Spark / Dagster / Ollama server configs.
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any

from flask import current_app

from app.extensions import db
from app.domains.tenants.domain.models import (
    InfrastructureConfig,
    InfrastructureType,
    DEFAULT_INFRASTRUCTURE_CONFIGS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InfrastructureConfigError(Exception):
    """Base exception for infrastructure configuration errors."""
    pass


class InfrastructureConfigNotFoundError(InfrastructureConfigError):
    """Raised when configuration is not found."""
    pass


class InfrastructureConnectionError(InfrastructureConfigError):
    """Raised when connection test fails."""
    pass


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class InfrastructureConfigService:
    """
    Manage infrastructure server configurations.

    Provides CRUD, connection testing, credential handling,
    and default initialisation.
    
    Changes are automatically propagated via Redis pub/sub for
    real-time updates to Dagster resources and other consumers.
    """

    def __init__(self) -> None:
        self._credential_manager = None
        self._config_cache = None

    def _get_config_cache(self):
        """Get the infrastructure config cache (lazy load)."""
        if self._config_cache is None:
            try:
                from app.platform.infrastructure.config_cache import (
                    get_config_cache,
                )
                self._config_cache = get_config_cache()
            except Exception as e:
                logger.warning("Failed to initialize config cache: %s", e)
        return self._config_cache

    def _invalidate_and_publish(
        self,
        service_type: str,
        tenant_id: Optional[str],
        action: str,
        config_id: Optional[str] = None,
    ) -> None:
        """Invalidate cache and publish change event."""
        cache = self._get_config_cache()
        if cache:
            cache.invalidate(service_type, tenant_id)
            cache.publish_change(
                service_type=service_type,
                tenant_id=tenant_id,
                action=action,
                config_id=config_id,
            )

    def _get_credential_manager(self, tenant_id: Optional[str] = None):
        from app.services.credential_manager import CredentialManager

        return CredentialManager(tenant_id=tenant_id)

    # =================================================================
    # CRUD
    # =================================================================

    def list_configs(
        self,
        service_type: Optional[str] = None,
        tenant_id: Optional[str] = None,
        include_global: bool = True,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        """List infra configs with filtering and pagination."""
        query = InfrastructureConfig.query

        if service_type:
            query = query.filter(
                InfrastructureConfig.service_type == service_type
            )

        if tenant_id:
            if include_global:
                query = query.filter(
                    db.or_(
                        InfrastructureConfig.tenant_id == tenant_id,
                        InfrastructureConfig.tenant_id.is_(None),
                    )
                )
            else:
                query = query.filter(
                    InfrastructureConfig.tenant_id == tenant_id
                )
        elif not include_global:
            query = query.filter(
                InfrastructureConfig.tenant_id.isnot(None)
            )

        query = query.order_by(
            InfrastructureConfig.service_type,
            InfrastructureConfig.is_system_default.desc(),
            InfrastructureConfig.created_at.desc(),
        )

        pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return {
            "items": [c.to_dict() for c in pagination.items],
            "total": pagination.total,
            "page": page,
            "per_page": per_page,
            "pages": pagination.pages,
        }

    def get_config(
        self, config_id: str
    ) -> Optional[InfrastructureConfig]:
        """Get a config by ID."""
        try:
            return InfrastructureConfig.query.filter(
                InfrastructureConfig.id == config_id
            ).first()
        except Exception as e:
            logger.error("Error fetching config %s: %s", config_id, e)
            return None

    def get_active_config(
        self,
        service_type: str,
        tenant_id: Optional[str] = None,
    ) -> Optional[InfrastructureConfig]:
        """Get active config with tenant → global fallback."""
        return InfrastructureConfig.get_active_config(
            service_type, tenant_id
        )

    def get_effective_settings(
        self,
        service_type: str,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return merged settings (stored + decrypted credentials)."""
        config = self.get_active_config(service_type, tenant_id)

        if config:
            settings: Dict[str, Any] = {
                "host": config.host,
                "port": config.port,
                **config.settings,
            }
            if config.settings:
                try:
                    cm = self._get_credential_manager(tenant_id)
                    settings.update(
                        cm.retrieve_credentials(config.settings)
                    )
                except Exception as e:
                    logger.warning("Failed to retrieve credentials: %s", e)
            return settings

        return self._get_default_settings(service_type)

    def create_config(
        self,
        service_type: str,
        name: str,
        host: str,
        port: int,
        settings: Dict[str, Any],
        tenant_id: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        created_by: Optional[str] = None,
    ) -> InfrastructureConfig:
        """Create a new infrastructure configuration."""
        cm = self._get_credential_manager(tenant_id)
        encrypted_settings = cm.store_credentials(settings)

        if is_active:
            self._deactivate_other_configs(service_type, tenant_id)

        config = InfrastructureConfig(
            service_type=service_type,
            name=name,
            host=host,
            port=port,
            settings=encrypted_settings,
            tenant_id=tenant_id,
            description=description,
            is_active=is_active,
            is_system_default=False,
            created_by=created_by,
            updated_by=created_by,
        )

        db.session.add(config)
        db.session.commit()

        # Invalidate cache and publish change
        self._invalidate_and_publish(
            service_type=service_type,
            tenant_id=tenant_id,
            action="created",
            config_id=str(config.id),
        )

        logger.info("Created infrastructure config: %s:%s", service_type, name)
        return config

    def update_config(
        self,
        config_id: str,
        updated_by: Optional[str] = None,
        **kwargs: Any,
    ) -> InfrastructureConfig:
        """Update an existing config (including system defaults)."""
        config = self.get_config(config_id)
        if not config:
            raise InfrastructureConfigNotFoundError(
                f"Config not found: {config_id}"
            )

        if "settings" in kwargs:
            new_settings = kwargs.pop("settings")
            cm = self._get_credential_manager(
                str(config.tenant_id) if config.tenant_id else None
            )
            encrypted = cm.store_credentials(new_settings)
            config.settings = {**config.settings, **encrypted}

        if kwargs.get("is_active", False) and not config.is_active:
            self._deactivate_other_configs(
                config.service_type, config.tenant_id
            )

        for field in ("name", "description", "host", "port", "is_active"):
            if field in kwargs:
                setattr(config, field, kwargs[field])

        config.updated_by = updated_by
        config.updated_at = datetime.utcnow()

        db.session.commit()

        # Invalidate cache and publish change
        self._invalidate_and_publish(
            service_type=config.service_type,
            tenant_id=str(config.tenant_id) if config.tenant_id else None,
            action="updated",
            config_id=config_id,
        )

        logger.info("Updated infrastructure config: %s", config_id)
        return config

    def delete_config(self, config_id: str) -> bool:
        """Delete a non-system-default config."""
        config = self.get_config(config_id)
        if not config:
            raise InfrastructureConfigNotFoundError(
                f"Config not found: {config_id}"
            )
        if config.is_system_default:
            raise InfrastructureConfigError(
                "Cannot delete system default configuration"
            )

        # Capture info before deletion
        service_type = config.service_type
        tenant_id = str(config.tenant_id) if config.tenant_id else None

        db.session.delete(config)
        db.session.commit()

        # Invalidate cache and publish change
        self._invalidate_and_publish(
            service_type=service_type,
            tenant_id=tenant_id,
            action="deleted",
            config_id=config_id,
        )

        logger.info("Deleted infrastructure config: %s", config_id)
        return True

    def _deactivate_other_configs(
        self,
        service_type: str,
        tenant_id: Optional[str],
    ) -> None:
        """Deactivate other active configs of same type + scope."""
        query = InfrastructureConfig.query.filter(
            InfrastructureConfig.service_type == service_type,
            InfrastructureConfig.is_active == True,  # noqa: E712
        )
        if tenant_id:
            query = query.filter(
                InfrastructureConfig.tenant_id == tenant_id
            )
        else:
            query = query.filter(
                InfrastructureConfig.tenant_id.is_(None)
            )

        for config in query.all():
            config.is_active = False
        db.session.flush()

    # =================================================================
    # Connection testing
    # =================================================================

    def test_connection(
        self,
        config_id: Optional[str] = None,
        service_type: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Test connectivity — either by config_id or inline params."""
        config = None
        if config_id:
            config = self.get_config(config_id)
            if not config:
                raise InfrastructureConfigNotFoundError(
                    f"Config not found: {config_id}"
                )
            service_type = config.service_type
            host = config.host
            port = config.port
            settings = dict(config.settings)
            try:
                cm = self._get_credential_manager(
                    str(config.tenant_id) if config.tenant_id else None
                )
                settings = cm.retrieve_credentials(settings)
            except Exception as e:
                logger.warning(
                    "Failed to decrypt credentials for test: %s", e
                )

        if not all([service_type, host, port]):
            raise ValueError("service_type, host, and port are required")

        settings = settings or {}

        test_methods = {
            InfrastructureType.CLICKHOUSE.value: self._test_clickhouse,
            InfrastructureType.SPARK.value: self._test_spark,
            InfrastructureType.DAGSTER.value: self._test_dagster,
            InfrastructureType.AIRFLOW.value: self._test_airflow,
            InfrastructureType.OLLAMA.value: self._test_ollama,
        }

        test_method = test_methods.get(str(service_type))
        if not test_method:
            raise ValueError(f"Unknown service type: {service_type}")

        start = time.time()
        try:
            result = test_method(
                str(host) if host else "localhost",
                int(port) if port else 8080,
                settings,
            )
            result["latency_ms"] = round((time.time() - start) * 1000, 2)
            if config_id:
                self._update_test_result(config_id, result)
            return result
        except Exception as e:
            result = {
                "success": False,
                "message": str(e),
                "latency_ms": round((time.time() - start) * 1000, 2),
            }
            if config_id:
                self._update_test_result(config_id, result)
            return result

    # --- per-service testers -------------------------------------------

    def _test_clickhouse(
        self, host: str, port: int, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        import httpx

        database = settings.get("database", "default")
        user = settings.get("user", "default")
        password = settings.get("password", "")
        secure = settings.get("secure", False)
        timeout = settings.get("connect_timeout", 10)
        protocol = "https" if secure else "http"
        url = f"{protocol}://{host}:{port}"

        try:
            resp = httpx.get(
                url,
                params={"query": "SELECT version()"},
                auth=(user, password) if user else None,
                timeout=timeout,
            )
            resp.raise_for_status()
            version = resp.text.strip()

            db_resp = httpx.get(
                url,
                params={
                    "query": (
                        "SELECT 1 FROM system.databases "
                        f"WHERE name = '{database}'"
                    )
                },
                auth=(user, password) if user else None,
                timeout=timeout,
            )
            db_exists = db_resp.text.strip() == "1"

            return {
                "success": True,
                "message": "Connection successful",
                "server_version": version,
                "details": {
                    "database_exists": db_exists,
                    "database": database,
                },
            }
        except httpx.HTTPStatusError as e:
            raise InfrastructureConnectionError(
                f"HTTP error: {e.response.status_code}"
            )
        except httpx.ConnectError as e:
            raise InfrastructureConnectionError(
                f"Connection failed: {e}"
            )
        except Exception as e:
            raise InfrastructureConnectionError(
                f"Connection test failed: {e}"
            )

    def _test_spark(
        self, host: str, port: int, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        import httpx
        import socket

        master_url = settings.get(
            "master_url", f"spark://{host}:{port}"
        )
        ui_port = 8080

        try:
            ui_url = f"http://{host}:{ui_port}/json/"
            resp = httpx.get(ui_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "message": "Connection successful",
                "server_version": data.get("spark", "unknown"),
                "details": {
                    "status": data.get("status", "UNKNOWN"),
                    "workers": len(data.get("workers", [])),
                    "cores": data.get("cores", 0),
                    "memory": data.get("memory", 0),
                    "master_url": master_url,
                },
            }
        except Exception:
            pass

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return {
                    "success": True,
                    "message": "Spark Master port is open",
                    "server_version": "unknown",
                    "details": {"master_url": master_url},
                }
            raise InfrastructureConnectionError(
                f"Cannot connect to {host}:{port}"
            )
        except socket.error as e:
            raise InfrastructureConnectionError(f"Socket error: {e}")

    def _test_airflow(
        self, host: str, port: int, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        import httpx

        base_url = settings.get(
            "base_url", f"http://{host}:{port}"
        ).rstrip("/")
        username = settings.get("username", "airflow")
        password = settings.get("password", "airflow")
        timeout = settings.get("request_timeout", 30)

        try:
            api_resp = httpx.get(
                f"{base_url}/api/v1/health",
                auth=(username, password),
                timeout=timeout,
            )
            api_resp.raise_for_status()
            health = api_resp.json()

            version = "unknown"
            try:
                vr = httpx.get(
                    f"{base_url}/api/v1/version",
                    auth=(username, password),
                    timeout=timeout,
                )
                if vr.status_code == 200:
                    version = vr.json().get("version", "unknown")
            except Exception:
                pass

            return {
                "success": True,
                "message": "Connection successful",
                "server_version": version,
                "details": {
                    "metadatabase": health.get("metadatabase", {}).get(
                        "status"
                    ),
                    "scheduler": health.get("scheduler", {}).get(
                        "status"
                    ),
                },
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise InfrastructureConnectionError(
                    "Authentication failed"
                )
            raise InfrastructureConnectionError(
                f"HTTP error: {e.response.status_code}"
            )
        except httpx.ConnectError as e:
            raise InfrastructureConnectionError(
                f"Connection failed: {e}"
            )
        except Exception as e:
            raise InfrastructureConnectionError(
                f"Connection test failed: {e}"
            )

    def _test_dagster(
        self, host: str, port: int, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test Dagster GraphQL API connection."""
        import httpx

        graphql_url = settings.get(
            "graphql_url", f"http://{host}:{port}/graphql"
        )
        timeout = settings.get("request_timeout", 30)

        # GraphQL query to check Dagster is running and get version info
        query = """
        query DagsterHealthCheck {
            version
            workspaceLocationOrError: workspaceOrError {
                ... on Workspace {
                    locationEntries {
                        name
                        loadStatus
                    }
                }
            }
        }
        """

        try:
            resp = httpx.post(
                graphql_url,
                json={"query": query},
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            if "errors" in data:
                raise InfrastructureConnectionError(
                    f"GraphQL errors: {data['errors']}"
                )

            version = data.get("data", {}).get("version", "unknown")
            workspace_info = data.get("data", {}).get("workspaceLocationOrError", {})
            locations = workspace_info.get("locationEntries", []) if workspace_info else []

            loaded_locations = [
                loc for loc in locations
                if loc.get("loadStatus") == "LOADED"
            ]

            return {
                "success": True,
                "message": "Dagster is running and accessible",
                "server_version": version,
                "details": {
                    "graphql_url": graphql_url,
                    "total_locations": len(locations),
                    "loaded_locations": len(loaded_locations),
                    "locations": [loc.get("name") for loc in locations[:5]],
                },
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise InfrastructureConnectionError(
                    "Dagster GraphQL endpoint not found - check URL"
                )
            raise InfrastructureConnectionError(
                f"HTTP error: {e.response.status_code}"
            )
        except httpx.ConnectError as e:
            raise InfrastructureConnectionError(
                f"Connection failed: {e}"
            )
        except Exception as e:
            raise InfrastructureConnectionError(
                f"Connection test failed: {e}"
            )

    def _test_ollama(
        self, host: str, port: int, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        import httpx

        base_url = settings.get(
            "base_url", f"http://{host}:{port}"
        ).rstrip("/")
        timeout = settings.get("request_timeout", 30)
        default_model = settings.get("default_model", "llama3.2")

        try:
            resp = httpx.get(f"{base_url}/", timeout=timeout)
            resp.raise_for_status()

            version = "unknown"
            try:
                vr = httpx.get(
                    f"{base_url}/api/version", timeout=timeout
                )
                if vr.status_code == 200:
                    version = vr.json().get("version", "unknown")
            except Exception:
                pass

            models: list = []
            model_available = False
            try:
                mr = httpx.get(
                    f"{base_url}/api/tags", timeout=timeout
                )
                if mr.status_code == 200:
                    model_list = mr.json().get("models", [])
                    models = [m.get("name", "") for m in model_list]
                    model_available = any(
                        default_model in m for m in models
                    )
            except Exception:
                pass

            return {
                "success": True,
                "message": "Ollama server is running",
                "server_version": version,
                "details": {
                    "models_available": len(models),
                    "models": models[:10],
                    "default_model": default_model,
                    "default_model_available": model_available,
                },
            }
        except httpx.HTTPStatusError as e:
            raise InfrastructureConnectionError(
                f"HTTP error: {e.response.status_code}"
            )
        except httpx.ConnectError as e:
            raise InfrastructureConnectionError(
                f"Connection failed: {e}"
            )
        except Exception as e:
            raise InfrastructureConnectionError(
                f"Connection test failed: {e}"
            )

    # --- helpers -------------------------------------------------------

    def _update_test_result(
        self, config_id: str, result: Dict[str, Any]
    ) -> None:
        try:
            config = self.get_config(config_id)
            if config:
                config.last_test_at = datetime.utcnow()
                config.last_test_success = result.get("success", False)
                config.last_test_message = result.get("message", "")
                db.session.commit()
        except Exception as e:
            logger.warning("Failed to update test result: %s", e)

    def _get_default_settings(
        self, service_type: str
    ) -> Dict[str, Any]:
        """Fall back to env/config defaults."""
        if service_type == InfrastructureType.CLICKHOUSE.value:
            return {
                "host": current_app.config.get(
                    "CLICKHOUSE_HOST", "localhost"
                ),
                "port": current_app.config.get("CLICKHOUSE_PORT", 8123),
                "database": current_app.config.get(
                    "CLICKHOUSE_DATABASE", "novasight"
                ),
                "user": current_app.config.get(
                    "CLICKHOUSE_USER", "default"
                ),
                "password": current_app.config.get(
                    "CLICKHOUSE_PASSWORD", ""
                ),
                "secure": False,
                "connect_timeout": 10,
                "send_receive_timeout": 300,
            }
        if service_type == InfrastructureType.SPARK.value:
            return {
                "host": "spark-master",
                "port": 7077,
                "master_url": "spark://spark-master:7077",
                "deploy_mode": "client",
                "driver_memory": "2g",
                "executor_memory": "2g",
                "executor_cores": 2,
                "dynamic_allocation": True,
                "min_executors": 1,
                "max_executors": 10,
                "spark_home": "/opt/spark",
            }
        if service_type == InfrastructureType.DAGSTER.value:
            return {
                "host": current_app.config.get("DAGSTER_HOST", "localhost"),
                "port": current_app.config.get("DAGSTER_PORT", 3000),
                "graphql_url": current_app.config.get(
                    "DAGSTER_GRAPHQL_URL", "http://localhost:3000/graphql"
                ),
                "request_timeout": 30,
                "verify_ssl": True,
                "max_concurrent_runs": current_app.config.get(
                    "DAGSTER_MAX_CONCURRENT_RUNS", 10
                ),
                "spark_concurrency_limit": current_app.config.get(
                    "DAGSTER_SPARK_CONCURRENCY_LIMIT", 3
                ),
                "dbt_concurrency_limit": current_app.config.get(
                    "DAGSTER_DBT_CONCURRENCY_LIMIT", 2
                ),
                "compute_logs_dir": "/var/dagster/logs",
            }
        if service_type == InfrastructureType.AIRFLOW.value:
            return {
                "host": "localhost",
                "port": 8080,
                "base_url": current_app.config.get(
                    "AIRFLOW_BASE_URL", "http://localhost:8080"
                ),
                "username": current_app.config.get(
                    "AIRFLOW_USERNAME", "airflow"
                ),
                "password": current_app.config.get(
                    "AIRFLOW_PASSWORD", "airflow"
                ),
                "api_version": "v1",
                "dag_folder": "/opt/airflow/dags",
                "request_timeout": 30,
            }
        if service_type == InfrastructureType.OLLAMA.value:
            return {
                "host": current_app.config.get(
                    "OLLAMA_HOST", "localhost"
                ),
                "port": current_app.config.get("OLLAMA_PORT", 11434),
                "base_url": current_app.config.get(
                    "OLLAMA_BASE_URL", "http://localhost:11434"
                ),
                "default_model": current_app.config.get(
                    "OLLAMA_DEFAULT_MODEL", "llama3.2"
                ),
                "request_timeout": 120,
                "num_ctx": 4096,
                "temperature": 0.7,
                "keep_alive": "5m",
            }
        raise ValueError(f"Unknown service type: {service_type}")

    def initialize_defaults(self) -> None:
        """Create system-default configs for each infra type if missing."""
        for svc_type, defaults in DEFAULT_INFRASTRUCTURE_CONFIGS.items():
            existing = InfrastructureConfig.query.filter(
                InfrastructureConfig.service_type == svc_type,
                InfrastructureConfig.is_system_default == True,  # noqa: E712
            ).first()

            if not existing:
                config = InfrastructureConfig(
                    service_type=svc_type,
                    name=defaults["name"],
                    description=defaults["description"],
                    host=defaults["host"],
                    port=defaults["port"],
                    settings=defaults["settings"],
                    is_active=True,
                    is_system_default=True,
                )
                db.session.add(config)
                logger.info("Created default config for %s", svc_type)

        db.session.commit()
