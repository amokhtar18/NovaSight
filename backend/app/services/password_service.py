"""
NovaSight Password Service
==========================

Secure password hashing and validation using Argon2.
"""

import re
from typing import Tuple, Optional
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash
import logging

logger = logging.getLogger(__name__)


class PasswordService:
    """
    Password hashing and validation service using Argon2.
    
    Argon2 is the winner of the Password Hashing Competition and 
    provides strong protection against GPU-based attacks.
    """
    
    def __init__(
        self,
        time_cost: int = 3,
        memory_cost: int = 65536,  # 64 MB
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 16
    ):
        """
        Initialize password hasher with security parameters.
        
        Args:
            time_cost: Number of iterations
            memory_cost: Memory usage in KB
            parallelism: Number of parallel threads
            hash_len: Length of the hash in bytes
            salt_len: Length of the salt in bytes
        """
        self.hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len
        )
    
    def hash(self, password: str) -> str:
        """
        Hash a password using Argon2.
        
        Args:
            password: Plain text password
        
        Returns:
            Argon2 hash string
        """
        return self.hasher.hash(password)
    
    def verify(self, password: str, hash: str) -> bool:
        """
        Verify a password against a hash.
        
        Args:
            password: Plain text password
            hash: Argon2 hash string
        
        Returns:
            True if password matches, False otherwise
        """
        try:
            self.hasher.verify(hash, password)
            return True
        except VerifyMismatchError:
            return False
        except InvalidHash:
            logger.error("Invalid password hash format")
            return False
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def needs_rehash(self, hash: str) -> bool:
        """
        Check if a hash needs to be rehashed with new parameters.
        
        Args:
            hash: Existing Argon2 hash
        
        Returns:
            True if rehash is needed
        """
        try:
            return self.hasher.check_needs_rehash(hash)
        except Exception:
            return True
    
    def validate_strength(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password meets security requirements.
        
        Requirements:
        - Minimum 12 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        - No common patterns
        
        Args:
            password: Password to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < 12:
            return False, "Password must be at least 12 characters long"
        
        if len(password) > 128:
            return False, "Password must be 128 characters or less"
        
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
            return False, "Password must contain at least one special character"
        
        # Check for common patterns
        common_patterns = [
            r'(.)\1{3,}',  # 4+ repeated characters
            r'(012|123|234|345|456|567|678|789|890)',  # Sequential numbers
            r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # Sequential letters
        ]
        
        password_lower = password.lower()
        for pattern in common_patterns:
            if re.search(pattern, password_lower):
                return False, "Password contains common patterns that are not allowed"
        
        # Check for common weak passwords
        weak_passwords = [
            'password', 'qwerty', 'letmein', 'welcome', 'admin',
            'iloveyou', 'sunshine', 'princess', 'football', 'monkey'
        ]
        
        if any(weak in password_lower for weak in weak_passwords):
            return False, "Password is too common and easily guessable"
        
        return True, None


# Singleton instance
password_service = PasswordService()
