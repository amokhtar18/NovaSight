"""
NovaSight Token Blacklist Service
=================================

Redis-based token blacklist for logout functionality.
"""

from typing import Optional
from datetime import timedelta
from app.extensions import redis_client
import logging

logger = logging.getLogger(__name__)


class TokenBlacklist:
    """
    Redis-based token blacklist for invalidating JWTs on logout.
    
    Tokens are stored with their JTI (JWT ID) as the key and
    automatically expire when the original token would have expired.
    """
    
    PREFIX = "token_blacklist:"
    
    def __init__(self):
        """Initialize token blacklist."""
        self._redis = None
    
    @property
    def redis(self):
        """Get Redis client."""
        if self._redis is None:
            self._redis = redis_client.client
        return self._redis
    
    def add(self, jti: str, expires_in: int) -> bool:
        """
        Add a token to the blacklist.
        
        Args:
            jti: JWT ID (unique identifier for the token)
            expires_in: Seconds until the token expires
        
        Returns:
            True if successfully added
        """
        if not self.redis:
            logger.warning("Redis not available for token blacklist")
            return False
        
        try:
            key = f"{self.PREFIX}{jti}"
            self.redis.setex(key, expires_in, "1")
            logger.debug(f"Token {jti} added to blacklist, expires in {expires_in}s")
            return True
        except Exception as e:
            logger.error(f"Failed to add token to blacklist: {e}")
            return False
    
    def is_blacklisted(self, jti: str) -> bool:
        """
        Check if a token is blacklisted.
        
        Args:
            jti: JWT ID to check
        
        Returns:
            True if token is blacklisted
        """
        if not self.redis:
            # If Redis is unavailable, fail open (allow token)
            # In production, you might want to fail closed instead
            return False
        
        try:
            key = f"{self.PREFIX}{jti}"
            return self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check token blacklist: {e}")
            return False
    
    def remove(self, jti: str) -> bool:
        """
        Remove a token from the blacklist.
        
        Args:
            jti: JWT ID to remove
        
        Returns:
            True if successfully removed
        """
        if not self.redis:
            return False
        
        try:
            key = f"{self.PREFIX}{jti}"
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to remove token from blacklist: {e}")
            return False
    
    def clear_all(self) -> int:
        """
        Clear all blacklisted tokens.
        
        Returns:
            Number of tokens cleared
        """
        if not self.redis:
            return 0
        
        try:
            pattern = f"{self.PREFIX}*"
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Failed to clear token blacklist: {e}")
            return 0


class LoginAttemptTracker:
    """
    Track failed login attempts for rate limiting and lockout.
    """
    
    PREFIX = "login_attempts:"
    LOCKOUT_PREFIX = "login_lockout:"
    
    MAX_ATTEMPTS = 5
    ATTEMPT_WINDOW = 300  # 5 minutes
    LOCKOUT_DURATION = 900  # 15 minutes
    
    def __init__(self):
        """Initialize login attempt tracker."""
        self._redis = None
    
    @property
    def redis(self):
        """Get Redis client."""
        if self._redis is None:
            self._redis = redis_client.client
        return self._redis
    
    def record_attempt(self, identifier: str, success: bool) -> None:
        """
        Record a login attempt.
        
        Args:
            identifier: Email or IP address
            success: Whether the attempt was successful
        """
        if not self.redis:
            return
        
        try:
            if success:
                # Clear attempts on successful login
                self.clear_attempts(identifier)
            else:
                # Increment failed attempts
                key = f"{self.PREFIX}{identifier}"
                pipe = self.redis.pipeline()
                pipe.incr(key)
                pipe.expire(key, self.ATTEMPT_WINDOW)
                pipe.execute()
                
                # Check if lockout threshold reached
                attempts = self.get_attempts(identifier)
                if attempts >= self.MAX_ATTEMPTS:
                    self._apply_lockout(identifier)
                    
        except Exception as e:
            logger.error(f"Failed to record login attempt: {e}")
    
    def get_attempts(self, identifier: str) -> int:
        """
        Get number of failed attempts.
        
        Args:
            identifier: Email or IP address
        
        Returns:
            Number of failed attempts
        """
        if not self.redis:
            return 0
        
        try:
            key = f"{self.PREFIX}{identifier}"
            count = self.redis.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Failed to get login attempts: {e}")
            return 0
    
    def is_locked_out(self, identifier: str) -> bool:
        """
        Check if identifier is locked out.
        
        Args:
            identifier: Email or IP address
        
        Returns:
            True if locked out
        """
        if not self.redis:
            return False
        
        try:
            key = f"{self.LOCKOUT_PREFIX}{identifier}"
            return self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check lockout status: {e}")
            return False
    
    def get_lockout_remaining(self, identifier: str) -> int:
        """
        Get remaining lockout time in seconds.
        
        Args:
            identifier: Email or IP address
        
        Returns:
            Seconds remaining, or 0 if not locked out
        """
        if not self.redis:
            return 0
        
        try:
            key = f"{self.LOCKOUT_PREFIX}{identifier}"
            ttl = self.redis.ttl(key)
            return max(0, ttl)
        except Exception as e:
            logger.error(f"Failed to get lockout remaining: {e}")
            return 0
    
    def _apply_lockout(self, identifier: str) -> None:
        """Apply lockout to identifier."""
        try:
            key = f"{self.LOCKOUT_PREFIX}{identifier}"
            self.redis.setex(key, self.LOCKOUT_DURATION, "1")
            logger.warning(f"Account locked out: {identifier}")
        except Exception as e:
            logger.error(f"Failed to apply lockout: {e}")
    
    def clear_attempts(self, identifier: str) -> None:
        """Clear failed attempts for identifier."""
        if not self.redis:
            return
        
        try:
            self.redis.delete(f"{self.PREFIX}{identifier}")
        except Exception as e:
            logger.error(f"Failed to clear attempts: {e}")
    
    def clear_lockout(self, identifier: str) -> None:
        """Manually clear lockout for identifier."""
        if not self.redis:
            return
        
        try:
            self.redis.delete(f"{self.LOCKOUT_PREFIX}{identifier}")
            self.clear_attempts(identifier)
            logger.info(f"Lockout cleared for: {identifier}")
        except Exception as e:
            logger.error(f"Failed to clear lockout: {e}")


# Singleton instances
token_blacklist = TokenBlacklist()
login_tracker = LoginAttemptTracker()
