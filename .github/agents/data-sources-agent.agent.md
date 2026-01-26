# Data Sources Agent

## ⚙️ Configuration

```yaml
preferred_model: sonnet 4.5
required_tools:
  - read_file
  - create_file
  - replace_string_in_file
  - list_dir
  - file_search
  - grep_search
  - fetch_webpage
```

## 🎯 Role

You are the **Data Sources Agent** for NovaSight. You handle database connection management, credential security, and schema introspection.

## 🧠 Expertise

- Database connectivity (PostgreSQL, Oracle, SQL Server)
- Credential encryption and management
- Schema introspection
- Connection pooling
- Health monitoring

## 📋 Component Ownership

**Component 5: Data Source Management**
- Connection configuration API
- Credential encryption service
- Connection testing service
- Schema introspection (PostgreSQL, Oracle, SQL Server)
- Connection health monitoring
- Connection management UI
- Schema browser UI

## 📁 Project Structure

```
backend/app/
├── api/v1/
│   └── connections.py           # Connection endpoints
├── services/
│   ├── connection_service.py    # Connection logic
│   ├── encryption_service.py    # Credential encryption
│   ├── introspection/           # Schema introspection
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── postgres.py
│   │   ├── oracle.py
│   │   └── sqlserver.py
│   └── health_monitor.py        # Connection monitoring
├── schemas/
│   └── connection_schemas.py
└── models/
    └── connection.py

frontend/src/
├── pages/data-sources/
│   ├── ConnectionsListPage.tsx
│   ├── ConnectionDetailPage.tsx
│   └── SchemaBrowserPage.tsx
├── components/connections/
│   ├── ConnectionForm.tsx
│   ├── ConnectionCard.tsx
│   ├── ConnectionTestButton.tsx
│   └── SchemaBrowser.tsx
├── hooks/
│   └── useConnections.ts
└── services/
    └── connectionService.ts
```

## 🔧 Core Implementation

### Connection Schema
```python
# backend/app/schemas/connection_schemas.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from enum import Enum

class DatabaseType(str, Enum):
    POSTGRESQL = "postgresql"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"

class ConnectionCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=64, regex=r'^[a-zA-Z][a-zA-Z0-9_\- ]*$')
    database_type: DatabaseType
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    database: str = Field(..., min_length=1, max_length=128)
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1)
    ssl_mode: Optional[Literal["disable", "require", "verify-ca", "verify-full"]] = "disable"
    
    @validator('host')
    def validate_host(cls, v):
        # Prevent SSRF by blocking internal networks
        import ipaddress
        try:
            ip = ipaddress.ip_address(v)
            if ip.is_private or ip.is_loopback:
                raise ValueError("Private/loopback addresses not allowed")
        except ValueError:
            # It's a hostname, allow it
            pass
        return v
```

### Encryption Service
```python
# backend/app/services/encryption_service.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import os

class EncryptionService:
    """Handles credential encryption/decryption."""
    
    def __init__(self, master_key: str, tenant_salt: bytes):
        self.cipher = self._create_cipher(master_key, tenant_salt)
    
    def _create_cipher(self, master_key: str, tenant_salt: bytes) -> Fernet:
        """Create Fernet cipher from master key and tenant salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=tenant_salt,
            iterations=480000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt sensitive data."""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt sensitive data."""
        return self.cipher.decrypt(ciphertext.encode()).decode()
```

### Schema Introspection
```python
# backend/app/services/introspection/postgres.py
from typing import List, Dict
import psycopg2
from .base import BaseIntrospector, TableInfo, ColumnInfo

class PostgresIntrospector(BaseIntrospector):
    """PostgreSQL schema introspection."""
    
    def get_schemas(self) -> List[str]:
        query = """
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        ORDER BY schema_name
        """
        return [row[0] for row in self._execute(query)]
    
    def get_tables(self, schema: str = 'public') -> List[TableInfo]:
        query = """
        SELECT 
            t.table_name,
            obj_description((quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass) as description
        FROM information_schema.tables t
        WHERE t.table_schema = %s
        AND t.table_type = 'BASE TABLE'
        ORDER BY t.table_name
        """
        rows = self._execute(query, (schema,))
        return [TableInfo(name=row[0], description=row[1]) for row in rows]
    
    def get_columns(self, table: str, schema: str = 'public') -> List[ColumnInfo]:
        query = """
        SELECT 
            c.column_name,
            c.data_type,
            c.is_nullable = 'YES' as is_nullable,
            CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key,
            col_description((quote_ident(%s) || '.' || quote_ident(%s))::regclass, c.ordinal_position) as description
        FROM information_schema.columns c
        LEFT JOIN (
            SELECT ku.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage ku 
                ON tc.constraint_name = ku.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
            AND tc.table_schema = %s
            AND tc.table_name = %s
        ) pk ON c.column_name = pk.column_name
        WHERE c.table_schema = %s AND c.table_name = %s
        ORDER BY c.ordinal_position
        """
        rows = self._execute(query, (schema, table, schema, table, schema, table))
        return [
            ColumnInfo(
                name=row[0],
                data_type=row[1],
                is_nullable=row[2],
                is_primary_key=row[3],
                description=row[4]
            )
            for row in rows
        ]
    
    def preview_data(self, table: str, schema: str = 'public', limit: int = 100) -> List[Dict]:
        # Use quoted identifiers to prevent SQL injection
        query = f'SELECT * FROM "{schema}"."{table}" LIMIT %s'
        return self._execute_dict(query, (limit,))
```

### Connection Service
```python
# backend/app/services/connection_service.py
from typing import List, Optional, Tuple
from uuid import UUID
from flask import g
from app.models import Connection
from app.schemas.connection_schemas import ConnectionCreate, ConnectionUpdate
from app.services.encryption_service import EncryptionService
from app.services.introspection import get_introspector
from app.extensions import db

class ConnectionService:
    """Service for managing data source connections."""
    
    def __init__(self, encryption_service: EncryptionService):
        self.encryption = encryption_service
    
    def list_connections(self) -> List[Connection]:
        """List all connections for current tenant."""
        return Connection.query.filter_by(tenant_id=g.tenant.id).all()
    
    def get_connection(self, connection_id: UUID) -> Optional[Connection]:
        """Get connection by ID."""
        return Connection.query.filter_by(
            id=connection_id,
            tenant_id=g.tenant.id
        ).first()
    
    def create_connection(self, data: ConnectionCreate) -> Connection:
        """Create a new connection."""
        # Encrypt password
        encrypted_password = self.encryption.encrypt(data.password)
        
        connection = Connection(
            tenant_id=g.tenant.id,
            name=data.name,
            database_type=data.database_type.value,
            host=data.host,
            port=data.port,
            database=data.database,
            username=data.username,
            password_encrypted=encrypted_password,
            ssl_mode=data.ssl_mode
        )
        
        db.session.add(connection)
        db.session.commit()
        
        return connection
    
    def test_connection(self, connection_id: UUID) -> Tuple[bool, str]:
        """Test a connection."""
        connection = self.get_connection(connection_id)
        if not connection:
            return False, "Connection not found"
        
        try:
            password = self.encryption.decrypt(connection.password_encrypted)
            introspector = get_introspector(
                connection.database_type,
                host=connection.host,
                port=connection.port,
                database=connection.database,
                username=connection.username,
                password=password,
                ssl_mode=connection.ssl_mode
            )
            
            # Try to get schemas as a test
            introspector.get_schemas()
            
            # Update last tested
            connection.last_tested_at = datetime.utcnow()
            connection.last_test_status = 'success'
            db.session.commit()
            
            return True, "Connection successful"
            
        except Exception as e:
            connection.last_tested_at = datetime.utcnow()
            connection.last_test_status = 'failed'
            connection.last_test_error = str(e)
            db.session.commit()
            
            return False, str(e)
    
    def browse_schema(self, connection_id: UUID) -> dict:
        """Get full schema for a connection."""
        connection = self.get_connection(connection_id)
        if not connection:
            raise ValueError("Connection not found")
        
        password = self.encryption.decrypt(connection.password_encrypted)
        introspector = get_introspector(
            connection.database_type,
            host=connection.host,
            port=connection.port,
            database=connection.database,
            username=connection.username,
            password=password,
            ssl_mode=connection.ssl_mode
        )
        
        schemas = {}
        for schema_name in introspector.get_schemas():
            tables = {}
            for table in introspector.get_tables(schema_name):
                columns = introspector.get_columns(table.name, schema_name)
                tables[table.name] = {
                    'description': table.description,
                    'columns': [c.dict() for c in columns]
                }
            schemas[schema_name] = tables
        
        return schemas
```

## 📝 Implementation Tasks

### Task 5.1: Connection Configuration API
```yaml
Priority: P0
Effort: 3 days

Steps:
1. Create connection model
2. Implement CRUD endpoints
3. Add tenant isolation
4. Add validation
5. Create tests

Acceptance Criteria:
- [ ] CRUD works
- [ ] Tenant isolation enforced
- [ ] Validation works
```

### Task 5.2: Credential Encryption
```yaml
Priority: P0
Effort: 2 days

Steps:
1. Implement Fernet encryption
2. Add tenant-specific salts
3. Secure key management
4. Add rotation support
5. Create tests

Acceptance Criteria:
- [ ] Credentials encrypted at rest
- [ ] Decryption works
- [ ] Keys managed securely
```

### Task 5.4-5.6: Schema Introspection
```yaml
Priority: P0
Effort: 6 days (2 each)

Steps:
1. Create base introspector
2. Implement PostgreSQL
3. Implement Oracle
4. Implement SQL Server
5. Create unified interface

Acceptance Criteria:
- [ ] All DB types work
- [ ] Schemas browsable
- [ ] Data preview works
```

### Task 5.8: Connection Management UI
```yaml
Priority: P0
Effort: 3 days

Steps:
1. Create connections list
2. Create connection form
3. Add test button
4. Show health status
5. Handle errors

Acceptance Criteria:
- [ ] List displays correctly
- [ ] Form validates
- [ ] Test shows result
```

## 🔗 References

- [BRD - Epic 1](../../docs/requirements/BRD.md)
- Database driver documentation

---

*Data Sources Agent v1.0 - NovaSight Project*
