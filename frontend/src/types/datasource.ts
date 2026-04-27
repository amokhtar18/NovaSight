/**
 * Data Source types
 */

export type DatabaseType =
  | 'postgresql'
  | 'mysql'
  | 'oracle'
  | 'sqlserver'
  | 'mongodb'
  | 'clickhouse'

export type SourceCategory = 'database'

export type ConnectionStatus =
  | 'active'
  | 'inactive'
  | 'testing'
  | 'error'

export interface DataSource {
  id: string
  name: string
  db_type: DatabaseType
  host?: string
  port?: number
  database?: string
  schema_name?: string
  username?: string
  status: ConnectionStatus
  ssl_enabled: boolean
  last_synced_at?: string
  created_at: string
  updated_at: string
  tenant_id: string
  extra_params?: Record<string, unknown>
}

export interface DataSourceCreate {
  name: string
  db_type: DatabaseType
  host?: string
  port?: number
  database?: string
  username?: string
  password?: string
  ssl_enabled?: boolean
  schema_name?: string
  extra_params?: Record<string, unknown>
}

export interface DataSourceUpdate {
  name?: string
  host?: string
  port?: number
  database?: string
  username?: string
  password?: string
  ssl_enabled?: boolean
  extra_params?: Record<string, unknown>
}

export interface ConnectionTestRequest {
  db_type: DatabaseType
  host: string
  port: number
  database: string
  username: string
  password: string
  ssl_enabled?: boolean
  extra_params?: Record<string, unknown>
}

export interface ConnectionTestResult {
  success: boolean
  message: string
  details?: {
    version?: string
    schemas?: string[]
    latency_ms?: number
  }
}

export interface ColumnInfo {
  name: string
  data_type: string
  is_nullable: boolean
  is_primary_key: boolean
  default_value?: string
  max_length?: number
  precision?: number
  scale?: number
  comment?: string
}

export interface TableInfo {
  name: string
  schema: string
  table_type: string
  row_count?: number
  comment?: string
  columns?: ColumnInfo[]
}

export interface SchemaInfo {
  name: string
  tables: TableInfo[]
}

export interface DataSourceSchema {
  schemas: SchemaInfo[]
  total_tables: number
  total_columns?: number
}

export interface SyncConfig {
  tables?: string[]
  schemas?: string[]
  incremental?: boolean
  schedule?: string
}

export interface SyncJob {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at?: string
  completed_at?: string
  message?: string
}

export interface DataSourceStats {
  total_connections: number
  active_connections: number
  failed_connections: number
  total_tables: number
  total_rows: number
}

// Database type metadata
export interface DatabaseTypeInfo {
  type: DatabaseType
  name: string
  icon: string
  defaultPort: number
  supportsSSL: boolean
  supportsSchemas: boolean
  description: string
  category: SourceCategory
}

export const DATABASE_TYPES: Record<DatabaseType, DatabaseTypeInfo> = {
  postgresql: {
    type: 'postgresql',
    name: 'PostgreSQL',
    icon: 'database',
    defaultPort: 5432,
    supportsSSL: true,
    supportsSchemas: true,
    description: 'Open source relational database',
    category: 'database',
  },
  mysql: {
    type: 'mysql',
    name: 'MySQL',
    icon: 'database',
    defaultPort: 3306,
    supportsSSL: true,
    supportsSchemas: false,
    description: 'Popular open source relational database',
    category: 'database',
  },
  oracle: {
    type: 'oracle',
    name: 'Oracle',
    icon: 'database',
    defaultPort: 1521,
    supportsSSL: true,
    supportsSchemas: true,
    description: 'Enterprise relational database',
    category: 'database',
  },
  sqlserver: {
    type: 'sqlserver',
    name: 'SQL Server',
    icon: 'database',
    defaultPort: 1433,
    supportsSSL: true,
    supportsSchemas: true,
    description: 'Microsoft relational database',
    category: 'database',
  },
  mongodb: {
    type: 'mongodb',
    name: 'MongoDB',
    icon: 'database',
    defaultPort: 27017,
    supportsSSL: true,
    supportsSchemas: false,
    description: 'NoSQL document database',
    category: 'database',
  },
  clickhouse: {
    type: 'clickhouse',
    name: 'ClickHouse',
    icon: 'database',
    defaultPort: 9000,
    supportsSSL: true,
    supportsSchemas: true,
    description: 'Columnar OLAP database',
    category: 'database',
  },
}
