"""
NovaSight Data Sources — Per-Type Connection Validators
========================================================

Registry that validates request payloads based on the ``db_type``.
Database sources require host/port/credentials; file-based sources
require an ``upload_token`` instead.

Canonical location: ``app.domains.datasources.application.connection_validators``
"""

from typing import Any, Callable, Dict, List, Optional, Tuple
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


def _validate_file_fields(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Ensure file-based source has an upload token."""
    if not data.get("upload_token"):
        return False, "Field 'upload_token' is required for file-based sources"
    return True, ""


def _validate_flatfile_fields(data: Dict[str, Any]) -> Tuple[bool, str]:
    ok, msg = _validate_file_fields(data)
    if not ok:
        return ok, msg
    return True, ""


def _validate_excel_fields(data: Dict[str, Any]) -> Tuple[bool, str]:
    ok, msg = _validate_file_fields(data)
    if not ok:
        return ok, msg
    return True, ""


def _validate_sqlite_fields(data: Dict[str, Any]) -> Tuple[bool, str]:
    ok, msg = _validate_file_fields(data)
    if not ok:
        return ok, msg
    return True, ""


# ─── Registry ──────────────────────────────────────────────────────

_VALIDATORS: Dict[str, ValidatorFn] = {
    # Database sources
    "postgresql": _validate_database_fields,
    "mysql": _validate_database_fields,
    "oracle": _validate_database_fields,
    "sqlserver": _validate_database_fields,
    "clickhouse": _validate_database_fields,
    # File-based sources
    "flatfile": _validate_flatfile_fields,
    "excel": _validate_excel_fields,
    "sqlite": _validate_sqlite_fields,
}

# Types that are file-based
FILE_BASED_TYPES = frozenset({"flatfile", "excel", "sqlite"})


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


def is_file_based(db_type: str) -> bool:
    """Check whether a db_type is file-based."""
    return db_type in FILE_BASED_TYPES
