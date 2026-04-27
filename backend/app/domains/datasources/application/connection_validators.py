"""
NovaSight Data Sources — Per-Type Connection Validators
========================================================

Registry that validates request payloads based on the ``db_type``.
All connections are SQL database connections; file ingestion is handled
via the dlt pipeline builder (source_kind='file').

Canonical location: ``app.domains.datasources.application.connection_validators``
"""

from typing import Any, Callable, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


# ─── Validator type ────────────────────────────────────────────────

# A validator returns (is_valid: bool, error_message: str)
ValidatorFn = Callable[[Dict[str, Any]], Tuple[bool, str]]


# ─── Individual validators ─────────────────────────────────────────

def _validate_database_fields(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Ensure traditional database fields are present."""
    required = ["host", "port", "database", "username", "password"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return False, f"Missing required fields for database source: {', '.join(missing)}"
    return True, ""


# ─── Registry ──────────────────────────────────────────────────────

_VALIDATORS: Dict[str, ValidatorFn] = {
    "postgresql": _validate_database_fields,
    "mysql": _validate_database_fields,
    "oracle": _validate_database_fields,
    "sqlserver": _validate_database_fields,
    "clickhouse": _validate_database_fields,
}


def validate_connection_data(db_type: str, data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate connection request data for the given db_type.

    Returns:
        (True, "") on success, (False, error_message) on failure.
    """
    validator = _VALIDATORS.get(db_type)
    if validator is None:
        return False, f"Unsupported db_type: {db_type}"
    return validator(data)


def get_supported_types() -> List[str]:
    """Return all registered db_type values."""
    return sorted(_VALIDATORS.keys())
