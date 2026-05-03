"""
dbt Code Generator — Template-Based (ADR-002 Compliant).

Generates dbt SQL and YAML files from visual model configurations
using the approved Jinja2 templates in backend/templates/dbt/.

CRITICAL: This is the ONLY code path for generating dbt files.
No raw SQL string building. All output flows through audited templates.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

TEMPLATES_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent
    / "templates"
    / "dbt"
)


class DbtCodeGenerator:
    """
    Generate dbt model SQL and schema YAML from visual builder config.

    All generation uses the Jinja2 templates in backend/templates/dbt/:
    - staging_model.sql.j2       → stg_* models
    - intermediate_model.sql.j2  → int_* models
    - marts_model.sql.j2         → dim_*, fct_*, rpt_* models
    - model.sql.j2               → generic models
    - schema.yml.j2              → schema documentation + tests
    - sources.yml.j2             → source definitions
    - metric.yml.j2              → semantic model / metric definitions
    """

    LAYER_TEMPLATE_MAP = {
        "staging": "staging_model.sql.j2",
        "intermediate": "intermediate_model.sql.j2",
        "marts": "marts_model.sql.j2",
    }

    # Per-layer destination schema. dbt-clickhouse maps ``schema`` to a
    # ClickHouse database, computing the final database as
    # ``<profile_schema>_<model_schema>`` (e.g. profile schema
    # ``tenant_acme`` + layer schema ``staging`` →
    # ``tenant_acme_staging``). This routes each layer into a
    # separate per-tenant database so layer selection in the UI
    # deterministically drives the destination database.
    LAYER_SCHEMA_MAP = {
        "staging": "staging",
        "intermediate": "intermediate",
        "marts": "marts",
    }

    def __init__(self, templates_dir: Path | None = None):
        tpl_dir = templates_dir or TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(tpl_dir)),
            autoescape=select_autoescape([]),
            keep_trailing_newline=True,
        )
        # Register template globals
        self.env.globals["now"] = datetime.utcnow

    def generate_model_sql(
        self, config: Dict[str, Any], layer: str = "staging"
    ) -> str:
        """
        Generate dbt model SQL from visual config.

        Selects the appropriate layer template:
        - staging       → staging_model.sql.j2
        - intermediate  → intermediate_model.sql.j2
        - marts         → marts_model.sql.j2
        - (fallback)    → model.sql.j2
        """
        template_name = self.LAYER_TEMPLATE_MAP.get(layer, "model.sql.j2")
        template = self.env.get_template(template_name)

        # Inject metadata
        config = dict(config)
        # Auto-route to a per-layer ClickHouse database when the request
        # didn't supply an explicit schema_name. The template emits
        # ``config(schema='<value>')`` which dbt-clickhouse joins onto the
        # profile's schema (the tenant database) → ``tenant_<slug>_<layer>``.
        if not config.get("schema"):
            layer_schema = self.LAYER_SCHEMA_MAP.get(layer)
            if layer_schema:
                config["schema"] = layer_schema
        config["_generated_at"] = datetime.utcnow().isoformat()
        config["_template_version"] = "1.0.0"

        rendered = template.render(**config)
        logger.info(
            "Generated %s model SQL using template %s",
            config.get("model_name", "unknown"),
            template_name,
        )
        return rendered

    def generate_schema_yaml(self, config: Dict[str, Any]) -> str:
        """Generate dbt schema YAML from visual config."""
        template = self.env.get_template("schema.yml.j2")
        config = dict(config)
        config["_generated_at"] = datetime.utcnow().isoformat()
        config["_template_version"] = "1.0.0"
        return template.render(**config)

    def generate_sources_yaml(self, config: Dict[str, Any]) -> str:
        """Generate dbt sources YAML for a data source."""
        template = self.env.get_template("sources.yml.j2")
        config = dict(config)
        config["_generated_at"] = datetime.utcnow().isoformat()
        return template.render(**config)

    def generate_metric_yaml(self, config: Dict[str, Any]) -> str:
        """Generate dbt semantic model / metric YAML."""
        template = self.env.get_template("metric.yml.j2")
        config = dict(config)
        config["_generated_at"] = datetime.utcnow().isoformat()
        return template.render(**config)

    def generate_singular_test(
        self, test_name: str, sql: str, tags: list[str] | None = None
    ) -> str:
        """
        Generate a singular dbt test SQL file.

        Singular tests are plain SQL queries that return failing rows.
        These don't need a full Jinja2 template — just a header comment
        and the user-provided SQL (which has been validated).
        """
        tag_str = ", ".join(tags) if tags else ""
        header = (
            f"-- NovaSight Generated Singular Test: {test_name}\n"
            f"-- Generated: {datetime.utcnow().isoformat()}\n"
            f"-- Tags: {tag_str}\n"
            f"-- WARNING: Auto-generated file\n\n"
        )
        return header + sql.strip() + "\n"
