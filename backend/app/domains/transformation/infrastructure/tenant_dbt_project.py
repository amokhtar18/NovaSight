"""
NovaSight Tenant dbt Project Manager
=====================================

Manages per-tenant dbt projects with complete isolation:
- Separate project directory per tenant
- Tenant-specific profiles.yml pointing to dbt_{tenant_db} in ClickHouse 
- Source configurations from tenant's ClickHouse database
- Auto-creation of dbt_{tenant_db} database in ClickHouse

Enforces ADR-003: Multi-Tenant Isolation Strategy for dbt artifacts.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from app.platform.auth.identity import get_current_identity

logger = logging.getLogger(__name__)


class TenantDbtProjectError(Exception):
    """Raised when tenant dbt project operations fail."""
    pass


class TenantDbtProjectManager:
    """
    Manages tenant-isolated dbt projects.
    
    Each tenant gets their own dbt project with:
    - Project directory: /dbt/tenants/{tenant_slug}/
    - Source database: tenant_{tenant_slug} (ClickHouse)
    - Target database: dbt_tenant_{tenant_slug} (ClickHouse)
    - Isolated models, seeds, tests, and macros
    """
    
    # Base path for all tenant dbt projects
    BASE_PROJECTS_PATH = Path(__file__).parent.parent.parent.parent.parent / 'dbt' / 'tenants'
    
    # Template project path for scaffolding
    TEMPLATE_PROJECT_PATH = Path(__file__).parent.parent.parent.parent.parent / 'dbt'
    
    def __init__(
        self,
        tenant_id: str,
        tenant_slug: str,
        clickhouse_host: str = "clickhouse",
        clickhouse_port: int = 8123,
        clickhouse_user: str = "default",
        clickhouse_password: str = "",
    ):
        """
        Initialize tenant dbt project manager.
        
        Args:
            tenant_id: Tenant UUID
            tenant_slug: Tenant slug for naming
            clickhouse_host: ClickHouse hostname
            clickhouse_port: ClickHouse HTTP port
            clickhouse_user: ClickHouse username
            clickhouse_password: ClickHouse password
        """
        self.tenant_id = tenant_id
        self.tenant_slug = self._sanitize_slug(tenant_slug)
        self.clickhouse_host = clickhouse_host
        self.clickhouse_port = clickhouse_port
        self.clickhouse_user = clickhouse_user
        self.clickhouse_password = clickhouse_password
        
        # Computed paths and names
        self.project_path = self.BASE_PROJECTS_PATH / self.tenant_slug
        self.source_database = f"tenant_{self.tenant_slug}"
        self.target_database = f"dbt_{self.source_database}"  # dbt_tenant_{slug}
        
        logger.info(
            f"TenantDbtProjectManager initialized: tenant={self.tenant_slug}, "
            f"source_db={self.source_database}, target_db={self.target_database}"
        )
    
    @staticmethod
    def _sanitize_slug(slug: str) -> str:
        """Sanitize slug for use in database/project names."""
        import re
        if not slug:
            return "unnamed"
        result = slug.lower()
        result = re.sub(r'[-\s]+', '_', result)
        result = re.sub(r'[^a-z0-9_]', '', result)
        if result and not result[0].isalpha():
            result = 't_' + result
        return result or "unnamed"
    
    @classmethod
    def from_current_tenant(cls) -> 'TenantDbtProjectManager':
        """
        Create manager for the current request's tenant.
        
        Returns:
            TenantDbtProjectManager for current tenant
            
        Raises:
            TenantDbtProjectError: If no tenant context
        """
        identity = get_current_identity()
        if not identity or not identity.tenant_id:
            raise TenantDbtProjectError("No tenant context available")
        
        from app.domains.tenants.domain.models import Tenant
        tenant = Tenant.query.get(identity.tenant_id)
        if not tenant:
            raise TenantDbtProjectError(f"Tenant not found: {identity.tenant_id}")
        
        # Get ClickHouse config from environment.
        #
        # NOTE: ``CLICKHOUSE_PORT`` is the native protocol port used by the
        # rest of the platform (clickhouse-driver, port 9000). dbt-clickhouse
        # speaks the HTTP protocol and needs port 8123. We therefore prefer
        # ``DBT_CLICKHOUSE_PORT`` and only fall back to the well-known HTTP
        # default (8123) — never to ``CLICKHOUSE_PORT``.
        return cls(
            tenant_id=str(tenant.id),
            tenant_slug=tenant.slug,
            clickhouse_host=os.getenv('CLICKHOUSE_HOST', 'clickhouse'),
            clickhouse_port=int(os.getenv('DBT_CLICKHOUSE_PORT', '8123')),
            clickhouse_user=os.getenv('CLICKHOUSE_USER', 'default'),
            clickhouse_password=os.getenv('CLICKHOUSE_PASSWORD', ''),
        )
    
    # =========================================================================
    # Database Management
    # =========================================================================
    
    async def ensure_target_database(self) -> bool:
        """
        Ensure the dbt target database exists in ClickHouse.
        
        Creates dbt_tenant_{slug} database if it doesn't exist.
        
        Returns:
            True if database exists or was created
        """
        import httpx
        
        query = f"CREATE DATABASE IF NOT EXISTS {self.target_database}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{self.clickhouse_host}:{self.clickhouse_port}/",
                    params={
                        "user": self.clickhouse_user,
                        "password": self.clickhouse_password,
                        "query": query,
                    },
                    timeout=30.0,
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to create database: {response.text}")
                    return False
                
                logger.info(f"Ensured target database exists: {self.target_database}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating target database: {e}")
            raise TenantDbtProjectError(f"Failed to create target database: {e}")
    
    def ensure_target_database_sync(self) -> bool:
        """Synchronous version of ensure_target_database."""
        import requests
        
        query = f"CREATE DATABASE IF NOT EXISTS {self.target_database}"
        
        try:
            response = requests.post(
                f"http://{self.clickhouse_host}:{self.clickhouse_port}/",
                params={
                    "user": self.clickhouse_user,
                    "password": self.clickhouse_password,
                    "query": query,
                },
                timeout=30.0,
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to create database: {response.text}")
                return False
            
            logger.info(f"Ensured target database exists: {self.target_database}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating target database: {e}")
            raise TenantDbtProjectError(f"Failed to create target database: {e}")
    
    # =========================================================================
    # Project Structure Management
    # =========================================================================
    
    def ensure_project_exists(self) -> Path:
        """
        Ensure tenant dbt project exists, creating if necessary.
        
        Returns:
            Path to tenant project directory
        """
        if self.project_path.exists():
            logger.debug(f"Tenant project exists: {self.project_path}")
            return self.project_path
        
        logger.info(f"Creating tenant dbt project: {self.project_path}")
        return self._scaffold_project()
    
    def _scaffold_project(self) -> Path:
        """
        Create a new tenant dbt project from template.
        
        Returns:
            Path to created project
        """
        # Create project directory structure
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        subdirs = ['models', 'models/staging', 'models/intermediate', 'models/marts',
                   'seeds', 'tests', 'macros', 'analyses', 'snapshots', 'docs']
        for subdir in subdirs:
            (self.project_path / subdir).mkdir(parents=True, exist_ok=True)
        
        # Generate dbt_project.yml
        self._generate_project_yml()
        
        # Generate profiles.yml
        self._generate_profiles_yml()
        
        # Generate source configuration
        self._generate_sources_yml()
        
        # Copy shared macros from template
        self._copy_shared_macros()
        
        # Generate packages.yml
        self._generate_packages_yml()
        
        logger.info(f"Scaffolded tenant dbt project at: {self.project_path}")
        return self.project_path
    
    def _generate_project_yml(self) -> None:
        """Generate dbt_project.yml for tenant."""
        project_config = {
            'name': f'novasight_{self.tenant_slug}',
            'version': '1.0.0',
            'config-version': 2,
            'profile': f'novasight_{self.tenant_slug}',
            'model-paths': ['models'],
            'analysis-paths': ['analyses'],
            'test-paths': ['tests'],
            'seed-paths': ['seeds'],
            'macro-paths': ['macros'],
            'snapshot-paths': ['snapshots'],
            'target-path': 'target',
            'clean-targets': ['target', 'dbt_packages'],
            'vars': {
                'tenant_id': self.tenant_id,
                'tenant_slug': self.tenant_slug,
                'source_database': self.source_database,
                'target_database': self.target_database,
            },
            'models': {
                f'novasight_{self.tenant_slug}': {
                    'staging': {
                        '+materialized': 'view',
                        '+schema': 'staging',
                    },
                    'intermediate': {
                        '+materialized': 'ephemeral',
                    },
                    'marts': {
                        '+materialized': 'table',
                        '+schema': 'marts',
                    },
                },
            },
        }
        
        project_file = self.project_path / 'dbt_project.yml'
        with open(project_file, 'w') as f:
            yaml.dump(project_config, f, default_flow_style=False, sort_keys=False)
        
        logger.debug(f"Generated dbt_project.yml: {project_file}")
    
    def _generate_profiles_yml(self) -> None:
        """Generate profiles.yml for tenant targeting dbt_{tenant_db}."""
        profiles_config = {
            f'novasight_{self.tenant_slug}': {
                'target': 'dev',
                'outputs': {
                    'dev': {
                        'type': 'clickhouse',
                        'schema': self.target_database,  # dbt_tenant_{slug}
                        'host': self.clickhouse_host,
                        'port': self.clickhouse_port,
                        'user': self.clickhouse_user,
                        'password': self.clickhouse_password,
                        'secure': False,
                        'verify': False,
                    },
                    'prod': {
                        'type': 'clickhouse',
                        'schema': self.target_database,
                        'host': "{{ env_var('CLICKHOUSE_HOST') }}",
                        'port': "{{ env_var('DBT_CLICKHOUSE_PORT', '8123') | int }}",
                        'user': "{{ env_var('CLICKHOUSE_USER') }}",
                        'password': "{{ env_var('CLICKHOUSE_PASSWORD') }}",
                        'secure': True,
                        'verify': True,
                    },
                },
            },
        }
        
        profiles_file = self.project_path / 'profiles.yml'
        with open(profiles_file, 'w') as f:
            yaml.dump(profiles_config, f, default_flow_style=False, sort_keys=False)
        
        logger.debug(f"Generated profiles.yml: {profiles_file}")
    
    def _generate_sources_yml(self) -> None:
        """Generate sources.yml pointing to tenant's ClickHouse database."""
        sources_config = {
            'version': 2,
            'sources': [
                {
                    'name': 'tenant_raw',
                    'description': f'Raw data from tenant {self.tenant_slug} ClickHouse database',
                    'database': self.source_database,  # tenant_{slug}
                    'schema': 'default',
                    'tables': [
                        {
                            'name': '{{ table_name }}',
                            'description': 'Auto-discovered table (placeholder)',
                        },
                    ],
                },
            ],
        }
        
        sources_file = self.project_path / 'models' / '_sources.yml'
        with open(sources_file, 'w') as f:
            yaml.dump(sources_config, f, default_flow_style=False, sort_keys=False)
        
        logger.debug(f"Generated _sources.yml: {sources_file}")
    
    def _generate_packages_yml(self) -> None:
        """Generate packages.yml with common dbt packages."""
        packages_config = {
            'packages': [
                {'package': 'dbt-labs/dbt_utils', 'version': '1.1.1'},
                {'package': 'calogica/dbt_expectations', 'version': '0.10.3'},
            ],
        }
        
        packages_file = self.project_path / 'packages.yml'
        with open(packages_file, 'w') as f:
            yaml.dump(packages_config, f, default_flow_style=False, sort_keys=False)
        
        logger.debug(f"Generated packages.yml: {packages_file}")
    
    def _copy_shared_macros(self) -> None:
        """Copy shared macros from template project."""
        template_macros = self.TEMPLATE_PROJECT_PATH / 'macros'
        if template_macros.exists():
            target_macros = self.project_path / 'macros'
            for macro_file in template_macros.glob('*.sql'):
                shutil.copy2(macro_file, target_macros / macro_file.name)
            logger.debug(f"Copied shared macros to: {target_macros}")
    
    # =========================================================================
    # Source Discovery
    # =========================================================================
    
    def discover_source_tables(self) -> List[Dict[str, Any]]:
        """
        Discover tables in tenant's source ClickHouse database.
        
        Returns:
            List of table metadata dictionaries
        """
        import requests
        
        query = f"""
            SELECT 
                name,
                engine,
                total_rows,
                total_bytes
            FROM system.tables
            WHERE database = '{self.source_database}'
            FORMAT JSON
        """
        
        try:
            response = requests.post(
                f"http://{self.clickhouse_host}:{self.clickhouse_port}/",
                params={
                    "user": self.clickhouse_user,
                    "password": self.clickhouse_password,
                },
                data=query,
                timeout=30.0,
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to discover tables: {response.text}")
                return []
            
            result = response.json()
            tables = result.get('data', [])
            logger.info(f"Discovered {len(tables)} tables in {self.source_database}")
            return tables
            
        except Exception as e:
            logger.error(f"Error discovering tables: {e}")
            return []
    
    def update_sources_from_discovery(self) -> None:
        """Update sources.yml with discovered tables."""
        tables = self.discover_source_tables()
        if not tables:
            logger.warning("No tables discovered, skipping sources update")
            return
        
        sources_config = {
            'version': 2,
            'sources': [
                {
                    'name': 'tenant_raw',
                    'description': f'Raw data from tenant {self.tenant_slug} ClickHouse database',
                    'database': self.source_database,
                    'schema': 'default',
                    'tables': [
                        {'name': table['name'], 'description': f"Table with {table.get('total_rows', 0)} rows"}
                        for table in tables
                    ],
                },
            ],
        }
        
        sources_file = self.project_path / 'models' / '_sources.yml'
        with open(sources_file, 'w') as f:
            yaml.dump(sources_config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Updated sources.yml with {len(tables)} tables")
    
    # =========================================================================
    # Project Structure Access
    # =========================================================================
    
    def get_project_structure(self) -> Dict[str, Any]:
        """
        Get the complete project structure for display.
        
        Returns:
            Dictionary with project file tree and metadata
        """
        if not self.project_path.exists():
            return {'exists': False, 'path': str(self.project_path)}
        
        def scan_directory(path: Path, relative_to: Path) -> Dict[str, Any]:
            """Recursively scan directory."""
            result = {
                'name': path.name,
                'path': str(path.relative_to(relative_to)),
                'type': 'directory' if path.is_dir() else 'file',
            }
            
            if path.is_dir():
                children = []
                for child in sorted(path.iterdir()):
                    # Skip hidden files and target directory
                    if child.name.startswith('.') or child.name == 'target' or child.name == 'dbt_packages':
                        continue
                    children.append(scan_directory(child, relative_to))
                result['children'] = children
            else:
                result['size'] = path.stat().st_size
                result['extension'] = path.suffix
            
            return result
        
        structure = scan_directory(self.project_path, self.project_path)
        
        return {
            'exists': True,
            'path': str(self.project_path),
            'tenant_slug': self.tenant_slug,
            'source_database': self.source_database,
            'target_database': self.target_database,
            'structure': structure,
        }
    
    def get_file_content(self, relative_path: str) -> Optional[str]:
        """
        Read file content from project.
        
        Args:
            relative_path: Path relative to project root
            
        Returns:
            File content or None if not found
        """
        file_path = self.project_path / relative_path
        
        # Security: Ensure path is within project
        try:
            file_path.resolve().relative_to(self.project_path.resolve())
        except ValueError:
            logger.warning(f"Attempted path traversal: {relative_path}")
            return None
        
        if not file_path.exists() or not file_path.is_file():
            return None
        
        return file_path.read_text(encoding='utf-8')

    # Directories under the tenant project where users are allowed to delete
    # files via the API. Anything else (dbt_project.yml, profiles.yml,
    # packages.yml, target/, logs/) is intentionally protected.
    _DELETABLE_ROOT_DIRS = (
        "models",
        "tests",
        "snapshots",
        "seeds",
        "macros",
        "analyses",
    )

    # Directories under the tenant project where users are allowed to write
    # (edit) files via the API. Mirrors ``_DELETABLE_ROOT_DIRS`` — the same
    # safe set used for delete.
    _WRITABLE_ROOT_DIRS = _DELETABLE_ROOT_DIRS

    # File extensions accepted for in-place edit. Other extensions (binaries,
    # parquet seeds, etc.) are rejected so we do not accidentally corrupt
    # non-text artifacts.
    _WRITABLE_EXTENSIONS = (".sql", ".yml", ".yaml", ".md", ".csv", ".sh", ".py")

    # Hard cap on file size accepted by ``write_file``. dbt SQL/YAML files are
    # always tiny; this prevents accidental DoS via huge payloads.
    _MAX_WRITE_BYTES = 1 * 1024 * 1024  # 1 MiB

    def _resolve_within_project(self, relative_path: str) -> Path:
        """Resolve a relative path and ensure it lives under the project root.

        Raises:
            TenantDbtProjectError: If path is empty, escapes the root, or is
                otherwise invalid.
        """
        if not relative_path or not relative_path.strip():
            raise TenantDbtProjectError("File path is required")
        rel = relative_path.strip().lstrip("/\\")
        target = self.project_path / rel
        try:
            resolved = target.resolve()
            project_root = self.project_path.resolve()
            resolved.relative_to(project_root)
        except (ValueError, OSError):
            logger.warning("Refusing path outside project root: %s", relative_path)
            raise TenantDbtProjectError("Invalid file path")
        return resolved

    def write_file(self, relative_path: str, content: str) -> Dict[str, Any]:
        """
        Overwrite (or create) a file inside the tenant dbt project.

        Allowed only for files under ``models/``, ``tests/``, ``snapshots/``,
        ``seeds/``, ``macros/`` and ``analyses/``, and only for the extensions
        listed in ``_WRITABLE_EXTENSIONS``. The maximum payload is
        ``_MAX_WRITE_BYTES``.

        Args:
            relative_path: Path relative to the project root, e.g.
                ``models/staging/stg_orders.sql``.
            content: New file contents (UTF-8 text).

        Returns:
            ``{"path": <relative path>, "size": <bytes written>}``.

        Raises:
            TenantDbtProjectError: On any validation or IO failure.
        """
        if content is None:
            raise TenantDbtProjectError("File content is required")
        if not isinstance(content, str):
            raise TenantDbtProjectError("File content must be text")

        encoded = content.encode("utf-8", errors="replace")
        if len(encoded) > self._MAX_WRITE_BYTES:
            raise TenantDbtProjectError(
                f"File too large ({len(encoded)} bytes); max is "
                f"{self._MAX_WRITE_BYTES} bytes"
            )

        resolved = self._resolve_within_project(relative_path)
        project_root = self.project_path.resolve()
        sub = resolved.relative_to(project_root)

        if not sub.parts or sub.parts[0] not in self._WRITABLE_ROOT_DIRS:
            raise TenantDbtProjectError(
                f"Files under '{sub.parts[0] if sub.parts else ''}' "
                f"cannot be edited via this API"
            )

        if resolved.suffix.lower() not in self._WRITABLE_EXTENSIONS:
            raise TenantDbtProjectError(
                f"Editing files with extension '{resolved.suffix}' is not allowed"
            )

        # Refuse to overwrite a directory or symlink target that points
        # outside the project root.
        if resolved.exists() and not resolved.is_file():
            raise TenantDbtProjectError(f"Not a regular file: {relative_path}")

        # Ensure parent directory exists for new files.
        resolved.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: write to a temp file in the same directory, then
        # rename — avoids leaving a half-written file if the process crashes.
        tmp = resolved.with_suffix(resolved.suffix + ".tmp")
        try:
            tmp.write_bytes(encoded)
            os.replace(tmp, resolved)
        except OSError as exc:
            try:
                if tmp.exists():
                    tmp.unlink()
            except OSError:
                pass
            raise TenantDbtProjectError(f"Failed to write file: {exc}")

        rel_str = str(sub).replace("\\", "/")
        logger.info(
            "Updated dbt project file for tenant %s: %s (%d bytes)",
            self.tenant_slug, rel_str, len(encoded),
        )
        return {"path": rel_str, "size": len(encoded)}

    def delete_file(self, relative_path: str) -> Dict[str, Any]:
        """
        Delete a file (typically a dbt model) from the tenant project.

        For ``.sql`` files inside ``models/``, the matching schema YAML
        (``_<name>.yml``) in the same directory is also removed when present —
        these pairs are how the visual model builder writes models.

        Args:
            relative_path: Path relative to the project root, e.g.
                ``models/staging/stg_orders.sql``.

        Returns:
            Dict with the deleted paths::

                {
                    "deleted": ["models/staging/stg_orders.sql",
                                "models/staging/_stg_orders.yml"],
                }

        Raises:
            TenantDbtProjectError: If the path is invalid, escapes the project
                root, points at a protected location, or the target file is
                missing.
        """
        if not relative_path or not relative_path.strip():
            raise TenantDbtProjectError("File path is required")

        rel = relative_path.strip().lstrip("/\\")
        target = self.project_path / rel

        # Block path traversal: resolved file must live under the project root.
        try:
            resolved = target.resolve()
            project_root = self.project_path.resolve()
            resolved.relative_to(project_root)
        except (ValueError, OSError):
            logger.warning("Refusing delete outside project root: %s", relative_path)
            raise TenantDbtProjectError("Invalid file path")

        # Restrict deletion to the user-managed directories. Compare against
        # the resolved project root so symlink-resolved paths still match.
        try:
            sub = resolved.relative_to(project_root)
        except ValueError:
            raise TenantDbtProjectError("Invalid file path")
        if not sub.parts or sub.parts[0] not in self._DELETABLE_ROOT_DIRS:
            raise TenantDbtProjectError(
                f"Files under '{sub.parts[0] if sub.parts else ''}' "
                f"cannot be deleted via this API"
            )

        if not resolved.exists():
            raise TenantDbtProjectError(f"File not found: {relative_path}")
        if not resolved.is_file():
            raise TenantDbtProjectError(f"Not a regular file: {relative_path}")

        deleted: List[str] = []
        resolved.unlink()
        deleted.append(str(sub).replace("\\", "/"))

        # Best-effort cleanup of the paired schema YAML for visual models.
        if resolved.suffix.lower() == ".sql" and sub.parts[0] == "models":
            sibling = resolved.parent / f"_{resolved.stem}.yml"
            if sibling.exists() and sibling.is_file():
                try:
                    sibling.relative_to(project_root)
                    sibling.unlink()
                    deleted.append(
                        str(sibling.relative_to(project_root)).replace("\\", "/")
                    )
                except (ValueError, OSError) as exc:
                    logger.warning(
                        "Could not remove paired schema YAML %s: %s", sibling, exc
                    )

        logger.info(
            "Deleted dbt project file(s) for tenant %s: %s",
            self.tenant_slug, deleted,
        )
        return {"deleted": deleted}

    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all models in the project.
        
        Returns:
            List of model metadata
        """
        models = []
        models_path = self.project_path / 'models'
        
        if not models_path.exists():
            return models
        
        for sql_file in models_path.rglob('*.sql'):
            # Skip sources files
            if sql_file.name.startswith('_'):
                continue
            
            relative_path = sql_file.relative_to(models_path)
            layer = relative_path.parts[0] if len(relative_path.parts) > 1 else 'default'
            
            models.append({
                'name': sql_file.stem,
                'path': str(relative_path),
                'layer': layer,
                'full_path': str(sql_file.relative_to(self.project_path)),
            })
        
        return models
    
    def list_semantic_models(self) -> List[Dict[str, Any]]:
        """
        List semantic model configurations.
        
        Returns:
            List of semantic model definitions
        """
        semantic_models = []
        models_path = self.project_path / 'models'
        
        if not models_path.exists():
            return semantic_models
        
        # Look for schema.yml files containing semantic models
        for yml_file in models_path.rglob('*.yml'):
            try:
                content = yaml.safe_load(yml_file.read_text())
                if content and 'semantic_models' in content:
                    for model in content['semantic_models']:
                        model['source_file'] = str(yml_file.relative_to(self.project_path))
                        semantic_models.append(model)
            except Exception as e:
                logger.warning(f"Error parsing {yml_file}: {e}")
        
        return semantic_models


# =========================================================================
# Module-level functions
# =========================================================================

def get_tenant_project_manager() -> TenantDbtProjectManager:
    """
    Get the tenant dbt project manager for the current request.
    
    Returns:
        TenantDbtProjectManager instance
    """
    return TenantDbtProjectManager.from_current_tenant()
