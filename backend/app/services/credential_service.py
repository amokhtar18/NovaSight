"""
NovaSight Credential Service
============================

Encryption and decryption of sensitive credentials.
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app
import logging

logger = logging.getLogger(__name__)


class CredentialService:
    """Service for encrypting and decrypting credentials."""
    
    def __init__(self, tenant_id: str):
        """
        Initialize credential service for a specific tenant.
        
        Args:
            tenant_id: Tenant UUID (used as salt for key derivation)
        """
        self.tenant_id = tenant_id
        self._fernet = None
    
    @property
    def fernet(self) -> Fernet:
        """Get Fernet encryption instance."""
        if self._fernet is None:
            self._fernet = self._create_fernet()
        return self._fernet
    
    def _create_fernet(self) -> Fernet:
        """Create Fernet instance with tenant-specific key."""
        # Get master key from config
        master_key = current_app.config.get("CREDENTIAL_ENCRYPTION_KEY")
        
        if not master_key:
            # Use a default key for development (NOT for production!)
            logger.warning("Using default encryption key - NOT SECURE FOR PRODUCTION")
            master_key = "default-dev-key-change-in-production-32bytes!"
        
        # Derive tenant-specific key using PBKDF2
        salt = self.tenant_id.encode()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.
        
        Args:
            plaintext: String to encrypt
        
        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""
        
        encrypted = self.fernet.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.
        
        Args:
            ciphertext: Base64-encoded encrypted string
        
        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""
        
        try:
            encrypted = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt credential")
