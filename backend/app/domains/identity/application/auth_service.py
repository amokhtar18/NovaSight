"""
NovaSight Authentication Service
================================

Canonical location: ``app.domains.identity.application.auth_service``

User authentication, registration, and token management.
Delegates password operations to ``platform.security.passwords``.
"""

from typing import Optional, Tuple
from datetime import datetime

from app.extensions import db
from app.domains.identity.domain.models import User
from app.platform.security.passwords import password_service
from app.platform.auth.token_service import login_tracker

import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service for user login, registration, and validation."""

    # ── Registration ──────────────────────────────────

    def register_user(
        self,
        email: str,
        password: str,
        name: str,
        tenant_slug: str,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new user.

        Args:
            email: User email address
            password: User password (plain text)
            name: User display name
            tenant_slug: Tenant slug

        Returns:
            Tuple of (User, None) on success, (None, error_message) on failure
        """
        try:
            # Validate password strength
            is_valid, error_msg = password_service.validate_strength(password)
            if not is_valid:
                return None, error_msg

            # Resolve tenant through lazy import (avoids cross-domain coupling)
            tenant = self._resolve_tenant(tenant_slug)
            if tenant is None:
                return None, "Tenant not found"

            if getattr(tenant, "status", None) != "active":
                return None, "Tenant is not active"

            # Check duplicate
            existing = User.query.filter(
                User.email == email.lower(),
                User.tenant_id == tenant.id,
            ).first()
            if existing:
                return None, "User with this email already exists"

            user = User(
                email=email.lower(),
                password_hash=password_service.hash(password),
                name=name.strip(),
                tenant_id=tenant.id,
                status="active",
            )

            db.session.add(user)
            db.session.commit()

            logger.info(f"New user registered: {email} in tenant {tenant_slug}")
            return user, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {e}")
            return None, "Registration failed. Please try again."

    # ── Authentication ────────────────────────────────

    def authenticate(
        self,
        email: str,
        password: str,
        tenant_slug: Optional[str] = None,
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user with email and password.

        Returns:
            Tuple of (User, None) on success, (None, error_message) on failure
        """
        identifier = email.lower()

        try:
            # Check for lockout
            if login_tracker.is_locked_out(identifier):
                remaining = login_tracker.get_lockout_remaining(identifier)
                minutes = remaining // 60 + 1
                return None, f"Account locked. Try again in {minutes} minutes."

            # Build the candidate set. The (tenant_id, email) uniqueness
            # constraint means the same email may legitimately exist in
            # multiple tenants, so we MUST scope by tenant before picking
            # a single user — otherwise login silently authenticates the
            # caller into an arbitrary tenant (typically the demo one).
            query = User.query.filter(User.email == identifier)

            if tenant_slug:
                tenant = self._resolve_tenant(tenant_slug)
                if not tenant:
                    login_tracker.record_attempt(identifier, success=False)
                    return None, "Invalid credentials"
                query = query.filter(User.tenant_id == tenant.id)

            candidates = query.all()

            if not candidates:
                logger.warning(f"Authentication failed: user {email} not found")
                login_tracker.record_attempt(identifier, success=False)
                return None, "Invalid credentials"

            # When the caller did not specify a tenant and the email exists
            # in more than one tenant, refuse to guess. Returning the first
            # match is a tenant-isolation bug.
            if len(candidates) > 1 and not tenant_slug:
                logger.warning(
                    "Authentication ambiguous: email %s exists in %d tenants; "
                    "tenant_slug required",
                    email,
                    len(candidates),
                )
                login_tracker.record_attempt(identifier, success=False)
                return None, (
                    "This email is registered in multiple workspaces. "
                    "Please specify your tenant."
                )

            user = candidates[0]

            if user.status != "active":
                logger.warning(f"Authentication failed: user {email} is not active")
                login_tracker.record_attempt(identifier, success=False)
                return None, "Account is not active"

            if not password_service.verify(password, user.password_hash):
                logger.warning(f"Authentication failed: invalid password for {email}")
                login_tracker.record_attempt(identifier, success=False)
                return None, "Invalid credentials"

            # Check tenant status
            if user.tenant and getattr(user.tenant, "status", None) != "active":
                logger.warning(
                    f"Authentication failed: tenant {getattr(user.tenant, 'slug', '?')} is not active"
                )
                return None, "Tenant is not active"

            # Record successful login
            login_tracker.record_attempt(identifier, success=True)

            # Update last login & rehash if needed
            user.last_login_at = datetime.utcnow()
            if password_service.needs_rehash(user.password_hash):
                user.password_hash = password_service.hash(password)

            db.session.commit()

            logger.info(
                "User %s authenticated successfully into tenant %s",
                email,
                getattr(user.tenant, "slug", user.tenant_id),
            )
            return user, None

        except Exception as e:
            logger.error(f"Authentication error: {e}")
            db.session.rollback()
            return None, "Authentication failed"

    # ── Token identity ────────────────────────────────

    def validate_token_identity(self, identity: dict) -> Optional[User]:
        """Validate JWT token identity and return associated user."""
        user_id = identity.get("user_id")
        tenant_id = identity.get("tenant_id")

        if not user_id:
            return None

        user = User.query.filter(
            User.id == user_id,
            User.tenant_id == tenant_id,
        ).first()

        if not user or user.status != "active":
            return None

        return user

    # ── Password change ───────────────────────────────

    def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Change user password.

        Returns:
            Tuple of (success, error_message)
        """
        try:
            if not password_service.verify(current_password, user.password_hash):
                return False, "Current password is incorrect"

            is_valid, error_msg = password_service.validate_strength(new_password)
            if not is_valid:
                return False, error_msg

            if password_service.verify(new_password, user.password_hash):
                return False, "New password must be different from current password"

            user.password_hash = password_service.hash(new_password)
            db.session.commit()

            logger.info(f"Password changed for user {user.email}")
            return True, None

        except Exception as e:
            db.session.rollback()
            logger.error(f"Password change error: {e}")
            return False, "Password change failed"

    # ── Private helpers ───────────────────────────────

    @staticmethod
    def _resolve_tenant(slug: str):
        """
        Resolve a Tenant by slug.

        Uses a lazy import to avoid coupling the identity domain
        directly to the tenant domain model at module level.
        """
        from app.domains.tenants.domain.models import Tenant

        return Tenant.query.filter(Tenant.slug == slug.lower()).first()
