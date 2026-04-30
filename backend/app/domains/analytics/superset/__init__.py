"""
NovaSight ↔ Apache Superset integration package
================================================

Thin, additive bridge between the existing NovaSight Flask backend and
Apache Superset (vendored as a pip dependency — see
``backend/requirements-superset.txt``).

This package is **purely additive**: nothing inside it edits an existing
NovaSight domain. It only:

    * boots / talks to a Superset instance (sidecar or in-process),
    * mirrors NovaSight users into Superset's FAB tables on demand,
    * auto-provisions one Superset ``Database`` row per tenant pointing
      at that tenant's ClickHouse database,
    * forces every Superset query to run against the caller's tenant
      ClickHouse DB (defence-in-depth via ``DB_CONNECTION_MUTATOR``),
    * exposes a thin ``/api/v1/superset/*`` proxy blueprint so the
      existing React frontend can keep using NovaSight URLs.

The package is loaded lazily only when ``SUPERSET_ENABLED=true`` so the
default development build does not require the Superset dependency.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    """Return True when the Superset integration should be activated."""
    return os.getenv("SUPERSET_ENABLED", "false").strip().lower() in (
        "true",
        "1",
        "yes",
    )


__all__ = ["is_enabled"]
