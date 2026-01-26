# 013 - Data Source Connectors

## Metadata

```yaml
prompt_id: "013"
phase: 2
agent: "@data-sources"
model: "sonnet 4.5"
priority: P0
estimated_effort: "4 days"
dependencies: ["003", "005"]
```

## Objective

Implement data source connection framework with PostgreSQL and MySQL connectors.

## Task Description

Create a pluggable connector architecture for ingesting data from various sources.

## Requirements

### Connector Base Class

```python
# backend/app/connectors/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Iterator
from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class ColumnInfo:
    name: str
    data_type: str
    nullable: bool
    primary_key: bool = False
    comment: str = ""

@dataclass
class TableInfo:
    name: str
    schema: str
    columns: List[ColumnInfo]
    row_count: int = 0

class ConnectionConfig(BaseModel):
    """Base configuration for database connections."""
    host: str
    port: int
    database: str
    username: str
    password: str  # Encrypted at rest
    ssl: bool = True
    extra_params: Dict[str, Any] = {}

class BaseConnector(ABC):
    """Abstract base class for data source connectors."""
    
    connector_type: str
    supported_auth_methods: List[str]
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._connection = None
    
    @abstractmethod
    def connect(self) -> None:
        """Establish connection to data source."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if connection is valid."""
        pass
    
    @abstractmethod
    def get_schemas(self) -> List[str]:
        """List available schemas."""
        pass
    
    @abstractmethod
    def get_tables(self, schema: str) -> List[TableInfo]:
        """List tables in schema."""
        pass
    
    @abstractmethod
    def get_table_schema(self, schema: str, table: str) -> TableInfo:
        """Get detailed table schema."""
        pass
    
    @abstractmethod
    def fetch_data(
        self, 
        query: str, 
        params: Dict[str, Any] = None,
        batch_size: int = 10000
    ) -> Iterator[List[Dict]]:
        """Fetch data in batches."""
        pass
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
```

### PostgreSQL Connector

```python
# backend/app/connectors/postgresql.py
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Iterator, Dict, Any

class PostgreSQLConnector(BaseConnector):
    """PostgreSQL database connector."""
    
    connector_type = "postgresql"
    supported_auth_methods = ["password", "iam"]
    
    def connect(self) -> None:
        self._connection = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.username,
            password=self.config.password,
            sslmode='require' if self.config.ssl else 'disable',
            **self.config.extra_params
        )
    
    def disconnect(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def test_connection(self) -> bool:
        try:
            with self._connection.cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except Exception:
            return False
    
    def get_schemas(self) -> List[str]:
        with self._connection.cursor() as cur:
            cur.execute("""
                SELECT schema_name 
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
            """)
            return [row[0] for row in cur.fetchall()]
    
    def get_tables(self, schema: str) -> List[TableInfo]:
        with self._connection.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    t.table_name,
                    t.table_schema,
                    (SELECT reltuples FROM pg_class WHERE relname = t.table_name) as row_count
                FROM information_schema.tables t
                WHERE t.table_schema = %s
                AND t.table_type = 'BASE TABLE'
            """, (schema,))
            
            tables = []
            for row in cur.fetchall():
                columns = self._get_columns(schema, row['table_name'])
                tables.append(TableInfo(
                    name=row['table_name'],
                    schema=row['table_schema'],
                    columns=columns,
                    row_count=int(row['row_count'] or 0)
                ))
            return tables
    
    def fetch_data(
        self, 
        query: str, 
        params: Dict[str, Any] = None,
        batch_size: int = 10000
    ) -> Iterator[List[Dict]]:
        with self._connection.cursor(
            name='fetch_cursor',
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(query, params or {})
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                yield [dict(row) for row in rows]
```

### Connector Registry

```python
# backend/app/connectors/registry.py
from typing import Dict, Type

class ConnectorRegistry:
    """Registry for data source connectors."""
    
    _connectors: Dict[str, Type[BaseConnector]] = {}
    
    @classmethod
    def register(cls, connector_class: Type[BaseConnector]):
        """Register a connector class."""
        cls._connectors[connector_class.connector_type] = connector_class
        return connector_class
    
    @classmethod
    def get(cls, connector_type: str) -> Type[BaseConnector]:
        """Get connector class by type."""
        if connector_type not in cls._connectors:
            raise ValueError(f"Unknown connector type: {connector_type}")
        return cls._connectors[connector_type]
    
    @classmethod
    def list_connectors(cls) -> List[str]:
        """List all registered connector types."""
        return list(cls._connectors.keys())

# Auto-register connectors
ConnectorRegistry.register(PostgreSQLConnector)
```

## Expected Output

```
backend/app/
├── connectors/
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   ├── postgresql.py
│   ├── mysql.py
│   └── utils/
│       ├── encryption.py
│       └── type_mapping.py
```

## Acceptance Criteria

- [ ] PostgreSQL connector connects and queries
- [ ] MySQL connector connects and queries
- [ ] Schema introspection works
- [ ] Batch data fetching works
- [ ] Connection pooling implemented
- [ ] Credentials encrypted at rest
- [ ] SSL/TLS connections work

## Reference Documents

- [Data Sources Agent](../agents/data-sources-agent.agent.md)
- [BRD - Epic 2](../../docs/requirements/BRD.md)
