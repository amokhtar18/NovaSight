/**
 * Visual Model API Types
 *
 * Types for the visual model builder CRUD API,
 * warehouse introspection, and code generation preview.
 */

import type { Materialization, JoinType } from './index'

// ============================================================================
// Visual Test Configuration
// ============================================================================

export interface VisualTestConfig {
  type: string
  values?: string[]
  to?: string
  field?: string
  min_value?: number
  max_value?: number
  regex?: string
  column_type?: string
  value_set?: string[]
  row_condition?: string
  severity?: 'ERROR' | 'WARN'
}

// ============================================================================
// Visual Column & Join Configuration
// ============================================================================

export interface VisualColumnConfig {
  name: string
  source_expression?: string
  source_column?: string
  source_alias?: string
  alias?: string
  description?: string
  data_type?: string
  cast?: string
  expression?: string
  tests: VisualTestConfig[]
}

export interface VisualJoinConfig {
  source_model: string
  join_type: JoinType
  model_alias?: string
  left_key: string
  right_key: string
  additional_conditions?: string[]
}

export interface VisualSourceModelConfig {
  name: string
  alias?: string
  where?: string
}

// ============================================================================
// Visual Model Create / Update
// ============================================================================

export interface VisualModelCreatePayload {
  model_name: string
  model_layer: 'staging' | 'intermediate' | 'marts'
  description?: string
  materialization?: Materialization

  // Source (staging)
  source_name?: string
  source_table?: string
  refs?: string[]

  /**
   * Where the staging model reads from. Defaults to ``warehouse``
   * (a dbt source on ClickHouse). When set to ``iceberg`` the model
   * is rendered with a ClickHouse ``iceberg('s3://...')`` table function
   * and ``iceberg_s3_uri`` is required. Materialization always lands in
   * the tenant's ClickHouse database regardless of source kind.
   */
  source_kind?: 'warehouse' | 'iceberg'
  /** Full ``s3://bucket/prefix/`` URI for the Iceberg table root. */
  iceberg_s3_uri?: string

  // Source models (intermediate/marts)
  source_models?: VisualSourceModelConfig[]

  // Columns, joins, filters
  columns?: VisualColumnConfig[]
  joins?: VisualJoinConfig[]
  where_clause?: string
  group_by?: string[]

  // Incremental
  unique_key?: string | string[]
  incremental_strategy?: string

  // Staging-specific
  primary_key?: string
  tenant_column?: string

  // Marts-specific
  partition_by?: string
  cluster_by?: string[]
  schema_name?: string

  // Metadata
  tags?: string[]
  canvas_position?: { x: number; y: number }
}

export type VisualModelUpdatePayload = VisualModelCreatePayload

// ============================================================================
// Visual Model Response
// ============================================================================

export interface VisualModelRecord {
  id: string
  model_name: string
  model_path: string
  model_layer: string
  canvas_position: { x: number; y: number }
  visual_config: Record<string, unknown>
  generated_sql?: string
  generated_yaml?: string
  materialization: string
  tags: string[]
  description: string
  created_at: string | null
  updated_at: string | null
}

// ============================================================================
// Code Preview
// ============================================================================

export interface GeneratedCodePreview {
  model_name: string
  sql: string
  yaml: string
}

// ============================================================================
// Canvas State
// ============================================================================

export interface CanvasStatePayload {
  position: { x: number; y: number }
  zoom?: number
  viewport?: { x: number; y: number; zoom: number }
}

// ============================================================================
// DAG (React Flow)
// ============================================================================

export interface DagNodeData {
  label: string
  materialization: string
  layer: string
  description: string
  tags: string[]
}

export interface DagNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: DagNodeData
}

export interface DagEdge {
  id: string
  source: string
  target: string
  type: string
}

export interface DagResponse {
  nodes: DagNode[]
  edges: DagEdge[]
}

// ============================================================================
// Warehouse Introspection
// ============================================================================

/**
 * Layer classification for a ClickHouse schema in dbt Studio.
 *
 * - ``warehouse``    → tenant's primary DB (raw/landed analytical data)
 * - ``staging``      → dbt staging layer  (``+schema: staging``)
 * - ``intermediate`` → dbt intermediate layer
 * - ``marts``        → dbt marts layer    (``+schema: marts``)
 * - ``raw``          → any other DB visible to the tenant connection
 */
export type WarehouseSchemaLayer =
  | 'warehouse'
  | 'staging'
  | 'intermediate'
  | 'marts'
  | 'raw'

export interface WarehouseSchema {
  name: string
  /** Layer classification (returned by the backend). */
  layer?: WarehouseSchemaLayer
  /**
   * ``true`` if the database currently exists in ClickHouse.
   * dbt-generated schemas (`_staging`, `_marts`) are surfaced eagerly
   * even before the first ``dbt run`` materializes them, so the UI
   * can render a "not materialized yet" hint.
   */
  exists?: boolean
}

export interface WarehouseTable {
  name: string
  engine: string
}

export interface WarehouseColumn {
  name: string
  type: string
  comment: string
}

// ============================================================================
// Execution History
// ============================================================================

export type ExecutionStatus = 'pending' | 'running' | 'success' | 'error' | 'cancelled'

export interface DbtExecutionRecord {
  id: string
  command: string
  status: ExecutionStatus
  started_at: string | null
  finished_at: string | null
  duration_seconds: number | null
  selector: string | null
  exclude: string | null
  full_refresh: boolean
  target: string | null
  models_affected: string[]
  models_succeeded: number
  models_errored: number
  models_skipped: number
  log_output: string
  error_output: string
  run_results: Record<string, unknown> | null
  triggered_by: string | null
  created_at: string | null
}

export interface ExecutionLogResponse {
  execution_id: string
  lines: string[]
  offset: number
  next_offset: number
}

// ============================================================================
// Test Builder
// ============================================================================

export interface SingularTestCreatePayload {
  test_name: string
  model_name?: string
  description?: string
  sql: string
  severity?: 'ERROR' | 'WARN'
  tags?: string[]
}

export interface TestResultEntry {
  unique_id: string
  status: string
  message: string
  execution_time: number
  failures: number | null
}

export interface TestResultsResponse {
  results: TestResultEntry[]
  total: number
  execution_id: string
  executed_at: string | null
}

// ============================================================================
// Source Freshness
// ============================================================================

export interface FreshnessThreshold {
  count: number
  period: 'minute' | 'hour' | 'day'
}

export interface SourceFreshnessPayload {
  source_name?: string
  table_name: string
  loaded_at_field: string
  warn_after: FreshnessThreshold
  error_after: FreshnessThreshold
}

// ============================================================================
// Package Manager
// ============================================================================

export interface DbtPackage {
  package?: string
  git?: string
  version?: string
  revision?: string
}
