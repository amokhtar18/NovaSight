"""
NovaSight Template Engine - Core Engine
========================================

Secure Jinja2-based template engine for code generation.
Implements ADR-002: All generated code comes from pre-approved templates only.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union

from jinja2 import (
    BaseLoader,
    Environment,
    FileSystemLoader,
    TemplateError,
    TemplateNotFound,
    TemplateSyntaxError,
    select_autoescape,
)
from pydantic import BaseModel, ValidationError

from app.services.template_engine.filters import (
    indent_lines,
    quote_identifier,
    sql_identifier_safe,
    sql_string_escape,
    sql_type_mapping,
    to_camel_case,
    to_pascal_case,
    to_snake_case,
)
from app.services.template_engine.validator import TemplateParameterValidator

logger = logging.getLogger(__name__)


class TemplateEngineError(Exception):
    """Base exception for template engine errors."""
    pass


class TemplateValidationError(TemplateEngineError):
    """Raised when template parameter validation fails."""
    
    def __init__(self, message: str, errors: Optional[List[Dict]] = None):
        super().__init__(message)
        self.errors = errors or []


class TemplateRenderError(TemplateEngineError):
    """Raised when template rendering fails."""
    pass


class TemplateNotFoundError(TemplateEngineError):
    """Raised when a template is not found."""
    pass


class TemplateSecurityError(TemplateEngineError):
    """Raised when a security violation is detected."""
    pass


class TemplateEngine:
    """
    Secure template engine for code generation using Jinja2.
    
    This engine ensures that ALL generated code comes from pre-approved templates,
    never from LLM-generated arbitrary code. It implements strict parameter
    validation and security measures.
    
    Usage:
        engine = TemplateEngine('/path/to/templates')
        result = engine.render('sql/create_table.sql.j2', {
            'table_name': 'users',
            'columns': [{'name': 'id', 'type': 'UUID', 'primary_key': True}]
        })
    
    Attributes:
        TEMPLATE_VERSION: Version of the template engine
        template_dir: Path to the template directory
        env: Jinja2 Environment instance
        manifest: Loaded template manifest
    """
    
    TEMPLATE_VERSION = "1.0.0"
    
    # Templates that require validation (security-critical)
    VALIDATED_TEMPLATES: Set[str] = {
        'sql/create_table.sql.j2',
        'sql/create_index.sql.j2',
        'sql/tenant_schema.sql.j2',
        'sql/analytics_query.sql.j2',
        'sql/comparison_query.sql.j2',
        'sql/trend_query.sql.j2',
        'sql/top_n_query.sql.j2',
        'dbt/model.sql.j2',
        'dbt/schema.yml.j2',
        'dbt/sources.yml.j2',
        'airflow/dag.py.j2',
        'clickhouse/create_table.sql.j2',
        'clickhouse/materialized_view.sql.j2',
        'pyspark/extract_job.py.j2',
        'pyspark/scd_type1.py.j2',
        'pyspark/scd_type2.py.j2',
    }
    
    def __init__(
        self,
        template_dir: Optional[Union[str, Path]] = None,
        auto_reload: bool = False,
    ):
        """
        Initialize the template engine.
        
        Args:
            template_dir: Path to template directory. If None, uses default.
            auto_reload: Whether to auto-reload templates on change (dev only).
        """
        if template_dir is None:
            # Default to backend/templates
            template_dir = Path(__file__).parent.parent.parent / "templates"
        
        self.template_dir = Path(template_dir)
        
        if not self.template_dir.exists():
            logger.warning(f"Template directory does not exist: {self.template_dir}")
            self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure Jinja2 environment with security settings
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            auto_reload=auto_reload,
            # Security: disable potentially dangerous features
            extensions=[],
        )
        
        # Register custom filters
        self._register_filters()
        
        # Register custom tests
        self._register_tests()
        
        # Register custom globals
        self._register_globals()
        
        # Load template manifest
        self.manifest = self._load_manifest()
        
        logger.info(
            f"Template engine initialized: dir={self.template_dir}, "
            f"templates={len(self.manifest.get('templates', {}))}"
        )
    
    def _register_filters(self) -> None:
        """Register custom Jinja2 filters."""
        self.env.filters['snake_case'] = to_snake_case
        self.env.filters['camel_case'] = to_camel_case
        self.env.filters['pascal_case'] = to_pascal_case
        self.env.filters['sql_safe'] = sql_identifier_safe
        self.env.filters['sql_escape'] = sql_string_escape
        self.env.filters['sql_value'] = sql_string_escape  # Alias for templates
        self.env.filters['sql_type'] = sql_type_mapping
        self.env.filters['quote_id'] = quote_identifier
        self.env.filters['indent_lines'] = indent_lines
    
    def _register_tests(self) -> None:
        """Register custom Jinja2 tests."""
        self.env.tests['valid_identifier'] = lambda x: bool(
            x and isinstance(x, str) and x[0].isalpha() and x.replace('_', '').isalnum()
        )
    
    def _register_globals(self) -> None:
        """Register custom global variables and functions."""
        self.env.globals['now'] = datetime.utcnow
        self.env.globals['template_version'] = self.TEMPLATE_VERSION
    
    def _load_manifest(self) -> Dict[str, Any]:
        """
        Load template manifest for validation and metadata.
        
        Returns:
            Manifest dictionary or empty dict if not found.
        """
        manifest_path = self.template_dir / 'manifest.json'
        
        if manifest_path.exists():
            try:
                content = manifest_path.read_text(encoding='utf-8')
                manifest = json.loads(content)
                logger.debug(f"Loaded manifest with {len(manifest.get('templates', {}))} templates")
                return manifest
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Failed to load manifest: {e}")
                return {}
        
        logger.debug("No manifest.json found, using empty manifest")
        return {}
    
    def _get_template_hash(self, template_name: str) -> str:
        """
        Calculate hash of a template for integrity verification.
        
        Args:
            template_name: Name of the template
            
        Returns:
            SHA-256 hash of the template content
        """
        template_path = self.template_dir / template_name
        if template_path.exists():
            content = template_path.read_bytes()
            return hashlib.sha256(content).hexdigest()
        return ""
    
    def _validate_parameters(
        self,
        template_name: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate parameters against template schema.
        
        Args:
            template_name: Name of the template
            parameters: Parameters to validate
            
        Returns:
            Validated and normalized parameters
            
        Raises:
            TemplateValidationError: If validation fails
        """
        try:
            # Try using registered validator
            validated_model = TemplateParameterValidator.validate(template_name, parameters)
            return validated_model.model_dump()
        except ValueError as e:
            if "No schema defined" in str(e):
                # Check manifest for schema
                template_info = self.manifest.get('templates', {}).get(template_name, {})
                if not template_info.get('schema'):
                    # No schema, return parameters as-is (with warning for critical templates)
                    if template_name in self.VALIDATED_TEMPLATES:
                        logger.warning(
                            f"Template '{template_name}' should have validation schema"
                        )
                    return parameters
            raise TemplateValidationError(f"Parameter validation failed: {e}")
        except ValidationError as e:
            errors = [
                {"field": ".".join(str(x) for x in err["loc"]), "message": err["msg"]}
                for err in e.errors()
            ]
            raise TemplateValidationError(
                f"Invalid parameters for template '{template_name}'",
                errors=errors,
            )
    
    def _check_security(self, template_name: str, parameters: Dict[str, Any]) -> None:
        """
        Perform security checks on template rendering request.
        
        Args:
            template_name: Name of the template
            parameters: Parameters being passed
            
        Raises:
            TemplateSecurityError: If security violation detected
        """
        # Check for suspicious patterns in string parameters
        dangerous_patterns = [
            '${', '$(', '`',  # Shell injection
            '{{', '{%',       # Template injection
            '<script', 'javascript:',  # XSS
            '--', '; DROP', 'UNION SELECT',  # SQL injection
        ]
        
        def check_value(value: Any, path: str = "") -> None:
            if isinstance(value, str):
                lower_value = value.lower()
                for pattern in dangerous_patterns:
                    if pattern.lower() in lower_value:
                        raise TemplateSecurityError(
                            f"Potential injection detected in parameter '{path}': "
                            f"pattern '{pattern}' found"
                        )
            elif isinstance(value, dict):
                for k, v in value.items():
                    check_value(v, f"{path}.{k}" if path else k)
            elif isinstance(value, (list, tuple)):
                for i, item in enumerate(value):
                    check_value(item, f"{path}[{i}]")
        
        check_value(parameters)
    
    def render(
        self,
        template_name: str,
        parameters: Dict[str, Any],
        validate: bool = True,
        check_security: bool = True,
    ) -> str:
        """
        Render a template with validated parameters.
        
        Args:
            template_name: Name of the template (e.g., 'sql/create_table.sql.j2')
            parameters: Dictionary of parameters for the template
            validate: Whether to validate parameters against schema
            check_security: Whether to perform security checks
            
        Returns:
            Rendered template content
            
        Raises:
            TemplateNotFoundError: If template doesn't exist
            TemplateValidationError: If parameter validation fails
            TemplateSecurityError: If security check fails
            TemplateRenderError: If rendering fails
        """
        logger.debug(f"Rendering template: {template_name}")
        
        # Security checks
        if check_security:
            self._check_security(template_name, parameters)
        
        # Parameter validation
        if validate:
            parameters = self._validate_parameters(template_name, parameters)
        
        # Add metadata to parameters
        render_params = {
            **parameters,
            '_template_name': template_name,
            '_template_version': self.TEMPLATE_VERSION,
            '_generated_at': datetime.utcnow().isoformat(),
        }
        
        try:
            template = self.env.get_template(template_name)
            result = template.render(**render_params)
            
            logger.info(f"Successfully rendered template: {template_name}")
            return result
            
        except TemplateNotFound:
            raise TemplateNotFoundError(f"Template not found: {template_name}")
        except TemplateSyntaxError as e:
            raise TemplateRenderError(f"Template syntax error in {template_name}: {e}")
        except TemplateError as e:
            raise TemplateRenderError(f"Template rendering failed for {template_name}: {e}")
        except Exception as e:
            raise TemplateRenderError(f"Unexpected error rendering {template_name}: {e}")
    
    def render_string(
        self,
        template_string: str,
        parameters: Dict[str, Any],
        check_security: bool = True,
    ) -> str:
        """
        Render a template from a string.
        
        NOTE: This should only be used for internal/trusted templates.
        User-provided template strings are a security risk.
        
        Args:
            template_string: Jinja2 template string
            parameters: Template parameters
            check_security: Whether to check for injection attacks
            
        Returns:
            Rendered content
        """
        if check_security:
            self._check_security("_string_template", parameters)
        
        try:
            template = self.env.from_string(template_string)
            return template.render(**parameters)
        except TemplateError as e:
            raise TemplateRenderError(f"String template rendering failed: {e}")
    
    def list_templates(self, category: Optional[str] = None) -> List[str]:
        """
        List available templates.
        
        Args:
            category: Optional category filter (e.g., 'sql', 'dbt', 'airflow')
            
        Returns:
            List of template names
        """
        templates = []
        
        for path in self.template_dir.rglob('*.j2'):
            rel_path = path.relative_to(self.template_dir).as_posix()
            if category is None or rel_path.startswith(f"{category}/"):
                templates.append(rel_path)
        
        return sorted(templates)
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """
        Get information about a template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template metadata including schema, description, hash
        """
        info = {
            "name": template_name,
            "exists": (self.template_dir / template_name).exists(),
            "hash": self._get_template_hash(template_name),
            "requires_validation": template_name in self.VALIDATED_TEMPLATES,
        }
        
        # Add manifest info if available
        manifest_info = self.manifest.get('templates', {}).get(template_name, {})
        if manifest_info:
            info["description"] = manifest_info.get("description", "")
            info["schema"] = manifest_info.get("schema", {})
        
        # Add validator schema if available
        schema = TemplateParameterValidator.get_schema(template_name)
        if schema:
            info["validator_schema"] = schema.__name__
        
        return info
    
    def validate_manifest(self) -> Dict[str, Any]:
        """
        Validate the template manifest and check template integrity.
        
        Returns:
            Validation report with any issues found
        """
        report = {
            "valid": True,
            "template_count": 0,
            "missing_templates": [],
            "missing_schemas": [],
            "hash_mismatches": [],
        }
        
        manifest_templates = self.manifest.get('templates', {})
        report["template_count"] = len(manifest_templates)
        
        for template_name, template_info in manifest_templates.items():
            template_path = self.template_dir / template_name
            
            # Check template exists
            if not template_path.exists():
                report["missing_templates"].append(template_name)
                report["valid"] = False
                continue
            
            # Check hash if specified
            expected_hash = template_info.get("hash")
            if expected_hash:
                actual_hash = self._get_template_hash(template_name)
                if actual_hash != expected_hash:
                    report["hash_mismatches"].append({
                        "template": template_name,
                        "expected": expected_hash,
                        "actual": actual_hash,
                    })
                    report["valid"] = False
            
            # Check schema for critical templates
            if template_name in self.VALIDATED_TEMPLATES:
                if not template_info.get("schema") and not TemplateParameterValidator.get_schema(template_name):
                    report["missing_schemas"].append(template_name)
        
        return report


# =============================================================================
# Singleton Instance
# =============================================================================

# Global template engine instance
_template_engine: Optional[TemplateEngine] = None


def get_template_engine() -> TemplateEngine:
    """
    Get the global template engine instance.
    
    Returns:
        TemplateEngine instance
    """
    global _template_engine
    
    if _template_engine is None:
        _template_engine = TemplateEngine()
    
    return _template_engine


def init_template_engine(template_dir: Optional[str] = None) -> TemplateEngine:
    """
    Initialize the global template engine with custom settings.
    
    Args:
        template_dir: Custom template directory path
        
    Returns:
        TemplateEngine instance
    """
    global _template_engine
    _template_engine = TemplateEngine(template_dir=template_dir)
    return _template_engine


# Convenience alias
template_engine = get_template_engine
