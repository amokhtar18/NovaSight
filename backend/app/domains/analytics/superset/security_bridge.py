"""
NovaSight ↔ Superset security bridge
=====================================

Maps NovaSight identities into Superset's Flask-AppBuilder user table
without ever touching the existing NovaSight identity domain.

Key properties:

* **Read-only against NovaSight identity.** Users keep logging in
  through ``/api/v1/auth/login``; this bridge merely *mirrors* the
  identity already encoded in the NovaSight JWT into Superset's FAB
  schema on first hit.
* **Per-tenant uniqueness.** FAB usernames are namespaced as
  ``<tenant_id>::<email>`` so two tenants can have identically-named
  users without collisions.
* **Role mapping is declarative** — see ``ROLE_MAP``.

This module is importable without Superset installed: the
``SupersetSecurityManager`` parent class is imported lazily inside the
class body via ``__init_subclass__`` style guard so unit tests that
only need the role-map / username helpers do not require Superset.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Role mapping — NovaSight role → Superset (FAB) built-in role name
# ---------------------------------------------------------------------------

ROLE_MAP: Dict[str, str] = {
    "super_admin": "Admin",
    "tenant_admin": "Admin",
    "data_engineer": "Gamma",
    "bi_developer": "Gamma",
    "analyst": "Gamma",
    "viewer": "Public",
}

DEFAULT_FAB_ROLE = "Public"


def fab_username(tenant_id: str, email: str) -> str:
    """Canonical FAB username for a NovaSight identity."""
    return f"{tenant_id}::{email}"


def map_roles(novasight_roles) -> str:
    """
    Pick the strongest matching FAB role for a list of NovaSight roles.

    "Strongest" is determined by the order of ``ROLE_MAP`` keys.
    """
    for ns_role in ROLE_MAP:  # ordered: strongest first
        if ns_role in (novasight_roles or []):
            return ROLE_MAP[ns_role]
    return DEFAULT_FAB_ROLE


# ---------------------------------------------------------------------------
# Lazy Superset import guard
# ---------------------------------------------------------------------------

try:  # pragma: no cover — exercised only when Superset is installed
    from superset.security import SupersetSecurityManager  # type: ignore
except ImportError:  # pragma: no cover
    SupersetSecurityManager = object  # type: ignore[misc,assignment]


# ---------------------------------------------------------------------------
# Custom security manager
# ---------------------------------------------------------------------------


class NovaSightSecurityManager(SupersetSecurityManager):  # type: ignore[misc]
    """
    Resolve every Superset request against the incoming NovaSight JWT.

    Flow:
        1. Read ``Authorization: Bearer <jwt>`` from the request.
        2. Decode it with NovaSight's existing JWT helper.
        3. Idempotently upsert the FAB user row.
        4. Stash ``g.tenant_id`` so the connection mutators can lock the
           datasource down.
    """

    # ------------------------------------------------------------------
    # FAB hook — called by Flask-AppBuilder for every request that
    # provides an Authorization header.
    # ------------------------------------------------------------------

    def request_loader(self, request):  # type: ignore[override]
        identity = self._decode_novasight_jwt(request)
        if identity is None:
            return None
        return self._mirror_user(identity)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_novasight_jwt(request) -> Optional[Dict[str, Any]]:
        """Extract a NovaSight identity from the Authorization header."""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return None
        token = auth_header.split(None, 1)[1].strip()

        try:
            # ``flask_jwt_extended.decode_token`` validates signature + expiry
            # against the same JWT_SECRET_KEY used by the rest of NovaSight,
            # so the JWT issued by ``/api/v1/auth/login`` is accepted as-is.
            from flask_jwt_extended import decode_token

            claims = decode_token(token)
        except Exception as exc:
            logger.debug("Rejected non-NovaSight JWT in Superset: %s", exc)
            return None

        email = claims.get("email") or claims.get("sub")
        tenant_id = claims.get("tenant_id")
        if not email or not tenant_id:
            return None

        return {
            "email": email,
            "tenant_id": str(tenant_id),
            "name": claims.get("name", email),
            "roles": claims.get("roles", []),
        }

    def _mirror_user(self, identity: Dict[str, Any]):
        """Upsert a FAB user matching the NovaSight identity."""
        try:
            from flask import g  # local import — only meaningful in request
        except ImportError:  # pragma: no cover
            g = None  # type: ignore[assignment]

        username = fab_username(identity["tenant_id"], identity["email"])
        user = self.find_user(username=username)

        if user is None:
            role_name = map_roles(identity.get("roles", []))
            role = self.find_role(role_name) or self.find_role(DEFAULT_FAB_ROLE)
            user = self.add_user(
                username=username,
                first_name=identity.get("name") or identity["email"],
                last_name="",
                email=identity["email"],
                role=role,
            )
            logger.info(
                "Mirrored NovaSight user %s as Superset FAB user (role=%s)",
                username,
                role_name,
            )

        if g is not None:
            g.tenant_id = identity["tenant_id"]
            g.novasight_email = identity["email"]

        return user


__all__ = [
    "ROLE_MAP",
    "DEFAULT_FAB_ROLE",
    "fab_username",
    "map_roles",
    "NovaSightSecurityManager",
]
