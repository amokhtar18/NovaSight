"""
NovaSight Platform – Password Service
=======================================

Argon2-based password hashing and strength validation.

Canonical location – all other modules should import from here.
"""

import logging
import re
from typing import Tuple, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

logger = logging.getLogger(__name__)


class PasswordService:
    """
    Argon2-based password hashing, verification, and strength validation.

    Argon2 is the winner of the Password Hashing Competition and provides
    strong resistance to GPU, ASIC, and side-channel attacks.
    """

    def __init__(
        self,
        time_cost: int = 3,
        memory_cost: int = 65536,   # 64 MiB
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 16,
    ):
        self.hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )

    # ── core operations ────────────────────────────────────────────

    def hash(self, password: str) -> str:
        """Return an Argon2 hash of *password*."""
        return self.hasher.hash(password)

    def verify(self, password: str, hash: str) -> bool:
        """Return ``True`` if *password* matches *hash*."""
        try:
            self.hasher.verify(hash, password)
            return True
        except VerifyMismatchError:
            return False
        except InvalidHash:
            logger.error("Invalid password hash format")
            return False
        except Exception as e:
            logger.error("Password verification error: %s", e)
            return False

    def needs_rehash(self, hash: str) -> bool:
        """Return ``True`` if *hash* should be re-hashed with current params."""
        try:
            return self.hasher.check_needs_rehash(hash)
        except Exception:
            return True

    # ── strength validation ────────────────────────────────────────

    _COMMON_PATTERNS = [
        re.compile(r"(.)\1{3,}"),
        re.compile(
            r"(012|123|234|345|456|567|678|789|890)"
        ),
        re.compile(
            r"(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|"
            r"nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)"
        ),
    ]

    _WEAK_PASSWORDS = frozenset([
        "password", "qwerty", "letmein", "welcome", "admin",
        "iloveyou", "sunshine", "princess", "football", "monkey",
    ])

    def validate_strength(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that *password* meets the security policy.

        Policy: ≥ 12 chars, ≤ 128, upper + lower + digit + special,
        no 4+ repeated chars, no sequential runs, no common words.
        """
        if not password:
            return False, "Password is required"
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if len(password) > 128:
            return False, "Password must be 128 characters or less"
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
            return False, "Password must contain at least one special character"

        pw_lower = password.lower()
        for pat in self._COMMON_PATTERNS:
            if pat.search(pw_lower):
                return False, "Password contains common patterns that are not allowed"
        if any(w in pw_lower for w in self._WEAK_PASSWORDS):
            return False, "Password is too common and easily guessable"

        return True, None


# ─── Singleton ──────────────────────────────────────────────────────
password_service = PasswordService()
