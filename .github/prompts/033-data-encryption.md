# 033 - Data Encryption

## Metadata

```yaml
prompt_id: "033"
phase: 5
agent: "@security"
model: "opus 4.5"
priority: P0
estimated_effort: "3 days"
dependencies: ["003", "013"]
```

## Objective

Implement encryption for sensitive data at rest and in transit.

## Task Description

Create encryption services for credentials, PII, and other sensitive data using industry-standard cryptography.

## Requirements

### Encryption Service

```python
# backend/app/services/encryption_service.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os
import json
from typing import Any, Dict

class EncryptionService:
    """Service for encrypting sensitive data."""
    
    def __init__(self, master_key: str = None):
        """
        Initialize encryption service.
        
        Args:
            master_key: Base64-encoded master key or from env var
        """
        self.master_key = master_key or os.environ.get('ENCRYPTION_MASTER_KEY')
        if not self.master_key:
            raise ValueError("Master key not configured")
        
        # Derive encryption key from master key
        self._fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """Create Fernet cipher from master key."""
        # Use PBKDF2 to derive key from master key
        salt = b'novasight_v1'  # Static salt is OK since master key is already high-entropy
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(self.master_key.encode())
        )
        return Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string value.
        
        Returns base64-encoded encrypted data with version prefix.
        """
        encrypted = self._fernet.encrypt(data.encode())
        # Add version prefix for future key rotation
        return f"v1:{encrypted.decode()}"
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string.
        
        Handles versioned encrypted data for key rotation.
        """
        if encrypted_data.startswith('v1:'):
            data = encrypted_data[3:]
            return self._fernet.decrypt(data.encode()).decode()
        else:
            # Legacy unversioned format
            return self._fernet.decrypt(encrypted_data.encode()).decode()
    
    def encrypt_dict(self, data: Dict[str, Any], fields: list = None) -> Dict[str, Any]:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary to encrypt
            fields: List of field names to encrypt (encrypts all if None)
        """
        result = data.copy()
        fields_to_encrypt = fields or list(data.keys())
        
        for field in fields_to_encrypt:
            if field in result and result[field] is not None:
                value = result[field]
                if not isinstance(value, str):
                    value = json.dumps(value)
                result[field] = self.encrypt(value)
        
        return result
    
    def decrypt_dict(self, data: Dict[str, Any], fields: list = None) -> Dict[str, Any]:
        """Decrypt specific fields in a dictionary."""
        result = data.copy()
        fields_to_decrypt = fields or list(data.keys())
        
        for field in fields_to_decrypt:
            if field in result and result[field] is not None:
                try:
                    result[field] = self.decrypt(result[field])
                    # Try to parse as JSON
                    try:
                        result[field] = json.loads(result[field])
                    except json.JSONDecodeError:
                        pass
                except Exception:
                    pass  # Field might not be encrypted
        
        return result
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new master key."""
        return base64.urlsafe_b64encode(os.urandom(32)).decode()


# Key rotation support
class KeyRotationService:
    """Service for rotating encryption keys."""
    
    def __init__(self, old_key: str, new_key: str):
        self.old_service = EncryptionService(old_key)
        self.new_service = EncryptionService(new_key)
    
    def rotate_value(self, encrypted_value: str) -> str:
        """Re-encrypt a value with the new key."""
        decrypted = self.old_service.decrypt(encrypted_value)
        return self.new_service.encrypt(decrypted)
    
    def rotate_table_column(
        self,
        model_class,
        column_name: str,
        batch_size: int = 100
    ) -> int:
        """Rotate encryption for all values in a table column."""
        from app.extensions import db
        
        count = 0
        offset = 0
        
        while True:
            rows = model_class.query.limit(batch_size).offset(offset).all()
            if not rows:
                break
            
            for row in rows:
                old_value = getattr(row, column_name)
                if old_value:
                    new_value = self.rotate_value(old_value)
                    setattr(row, column_name, new_value)
                    count += 1
            
            db.session.commit()
            offset += batch_size
        
        return count
```

### Encrypted Column Type

```python
# backend/app/utils/encrypted_types.py
from sqlalchemy import TypeDecorator, Text
from app.services.encryption_service import EncryptionService

class EncryptedString(TypeDecorator):
    """SQLAlchemy type for encrypted string columns."""
    
    impl = Text
    cache_ok = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._encryption = None
    
    @property
    def encryption(self):
        if self._encryption is None:
            self._encryption = EncryptionService()
        return self._encryption
    
    def process_bind_param(self, value, dialect):
        """Encrypt value before storing."""
        if value is not None:
            return self.encryption.encrypt(value)
        return value
    
    def process_result_value(self, value, dialect):
        """Decrypt value when loading."""
        if value is not None:
            return self.encryption.decrypt(value)
        return value

class EncryptedJSON(TypeDecorator):
    """SQLAlchemy type for encrypted JSON columns."""
    
    impl = Text
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is not None:
            import json
            return EncryptionService().encrypt(json.dumps(value))
        return value
    
    def process_result_value(self, value, dialect):
        if value is not None:
            import json
            decrypted = EncryptionService().decrypt(value)
            return json.loads(decrypted)
        return value


# Usage in models:
# class DataSource(db.Model):
#     connection_config = db.Column(EncryptedJSON)
#     password = db.Column(EncryptedString)
```

### Credential Manager

```python
# backend/app/services/credential_manager.py
from typing import Dict, Any
from app.services.encryption_service import EncryptionService
from app.extensions import db

class CredentialManager:
    """Manages encrypted credentials for data sources."""
    
    SENSITIVE_FIELDS = ['password', 'secret', 'api_key', 'token', 'private_key']
    
    def __init__(self):
        self.encryption = EncryptionService()
    
    def store_credentials(
        self,
        datasource_id: str,
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store credentials with sensitive fields encrypted.
        
        Returns the credentials dict with encrypted values.
        """
        encrypted = {}
        
        for key, value in credentials.items():
            if self._is_sensitive(key):
                encrypted[key] = self.encryption.encrypt(str(value))
            else:
                encrypted[key] = value
        
        return encrypted
    
    def retrieve_credentials(
        self,
        encrypted_credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Retrieve and decrypt credentials."""
        decrypted = {}
        
        for key, value in encrypted_credentials.items():
            if self._is_sensitive(key) and value:
                try:
                    decrypted[key] = self.encryption.decrypt(value)
                except Exception:
                    decrypted[key] = value  # Not encrypted or corrupted
            else:
                decrypted[key] = value
        
        return decrypted
    
    def _is_sensitive(self, field_name: str) -> bool:
        """Check if a field contains sensitive data."""
        field_lower = field_name.lower()
        return any(
            sensitive in field_lower 
            for sensitive in self.SENSITIVE_FIELDS
        )
    
    def mask_credentials(
        self,
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return credentials with sensitive values masked."""
        masked = {}
        
        for key, value in credentials.items():
            if self._is_sensitive(key):
                masked[key] = '********'
            else:
                masked[key] = value
        
        return masked
```

## Expected Output

```
backend/app/
├── services/
│   ├── encryption_service.py
│   └── credential_manager.py
└── utils/
    └── encrypted_types.py
```

## Acceptance Criteria

- [ ] Encryption uses AES-256 (via Fernet)
- [ ] Master key stored securely (env var or vault)
- [ ] Key rotation without downtime
- [ ] Encrypted columns work transparently
- [ ] Sensitive fields auto-detected
- [ ] Credentials never logged or exposed
- [ ] Version prefix supports future upgrades
- [ ] Performance acceptable for bulk operations

## Reference Documents

- [Security Agent](../agents/security-agent.agent.md)
- [Data Source Connectors](./013-data-source-connectors.md)
