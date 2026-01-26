/**
 * Domain model type definitions
 */

// Connection types
export interface Connection {
  id: string
  name: string
  type: ConnectionType
  host: string
  port: number
  database: string
  username: string
  status: ConnectionStatus
  lastTestedAt?: string
  createdAt: string
  updatedAt: string
}

export type ConnectionType = 
  | 'postgresql'
  | 'mysql'
  | 'sqlserver'
  | 'clickhouse'
  | 'snowflake'
  | 'bigquery'
  | 'redshift'

export type ConnectionStatus = 'connected' | 'disconnected' | 'error' | 'testing'

// DAG types
export interface Dag {
  id: string
  name: string
  description?: string
  schedule?: string
  status: DagStatus
  nodes: DagNode[]
  edges: DagEdge[]
  createdAt: string
  updatedAt: string
  lastRunAt?: string
}

export type DagStatus = 'active' | 'paused' | 'draft' | 'error'

export interface DagNode {
  id: string
  type: DagNodeType
  position: { x: number; y: number }
  data: Record<string, unknown>
}

export type DagNodeType = 
  | 'source'
  | 'transformation'
  | 'destination'
  | 'python'
  | 'sql'
  | 'dbt'

export interface DagEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
}

// Dashboard types
export interface Dashboard {
  id: string
  name: string
  description?: string
  widgets: Widget[]
  createdAt: string
  updatedAt: string
}

export interface Widget {
  id: string
  type: WidgetType
  title: string
  position: { x: number; y: number; w: number; h: number }
  config: Record<string, unknown>
}

export type WidgetType = 
  | 'chart'
  | 'table'
  | 'kpi'
  | 'text'
  | 'filter'

// Tenant types
export interface Tenant {
  id: string
  name: string
  slug: string
  plan: TenantPlan
  quotas: TenantQuotas
  createdAt: string
}

export type TenantPlan = 'free' | 'starter' | 'professional' | 'enterprise'

export interface TenantQuotas {
  maxUsers: number
  maxConnections: number
  maxDags: number
  maxDashboards: number
  storageGb: number
}
