/**
 * Visual Model API Client
 *
 * API service for the visual model builder CRUD endpoints,
 * warehouse introspection, execution history, test builder,
 * source freshness, and package management.
 */

import { apiClient } from '@/services/apiClient'
import type {
  VisualModelCreatePayload,
  VisualModelUpdatePayload,
  VisualModelRecord,
  GeneratedCodePreview,
  CanvasStatePayload,
  DagResponse,
  WarehouseSchema,
  WarehouseTable,
  WarehouseColumn,
  DbtExecutionRecord,
  ExecutionLogResponse,
  SingularTestCreatePayload,
  TestResultsResponse,
  SourceFreshnessPayload,
  DbtPackage,
} from '../types/visualModel'

const BASE = '/api/v1/dbt'

// ═══════════════════════════════════════════════════════════════
// Visual Model CRUD
// ═══════════════════════════════════════════════════════════════

export const visualModelApi = {
  /** List all visual models for the current tenant. */
  listModels: async (): Promise<VisualModelRecord[]> => {
    const { data } = await apiClient.get(`${BASE}/visual-models`)
    return data
  },

  /** Get a single visual model by ID. */
  getModel: async (modelId: string): Promise<VisualModelRecord> => {
    const { data } = await apiClient.get(`${BASE}/visual-models/${modelId}`)
    return data
  },

  /** Create a new visual model from builder config. */
  createModel: async (payload: VisualModelCreatePayload): Promise<VisualModelRecord> => {
    const { data } = await apiClient.post(`${BASE}/visual-models`, payload)
    return data
  },

  /** Update an existing visual model and regenerate dbt files. */
  updateModel: async (modelId: string, payload: VisualModelUpdatePayload): Promise<VisualModelRecord> => {
    const { data } = await apiClient.put(`${BASE}/visual-models/${modelId}`, payload)
    return data
  },

  /** Delete a visual model and its generated files. */
  deleteModel: async (modelId: string): Promise<void> => {
    await apiClient.delete(`${BASE}/visual-models/${modelId}`)
  },

  /** Preview generated SQL/YAML without writing to disk. */
  previewCode: async (modelId: string): Promise<GeneratedCodePreview> => {
    const { data } = await apiClient.post(`${BASE}/visual-models/${modelId}/preview`)
    return data
  },

  /** Preview generated SQL/YAML for an in-progress (unsaved) model. */
  previewCodeFromPayload: async (
    payload: VisualModelCreatePayload,
  ): Promise<GeneratedCodePreview> => {
    const { data } = await apiClient.post(
      `${BASE}/visual-models/preview`,
      payload,
    )
    return data
  },

  /** Save canvas position only (no regeneration). */
  saveCanvasState: async (modelId: string, payload: CanvasStatePayload): Promise<void> => {
    await apiClient.put(`${BASE}/visual-models/${modelId}/canvas`, payload)
  },

  /** Get full DAG for React Flow canvas. */
  getDag: async (): Promise<DagResponse> => {
    const { data } = await apiClient.get(`${BASE}/visual-models/dag`)
    return data
  },
}

// ═══════════════════════════════════════════════════════════════
// Warehouse Introspection
// ═══════════════════════════════════════════════════════════════

export const warehouseApi = {
  /** List schemas/databases from ClickHouse. */
  listSchemas: async (): Promise<WarehouseSchema[]> => {
    const { data } = await apiClient.get(`${BASE}/warehouse/schemas`)
    return data
  },

  /** List tables in a schema. */
  listTables: async (schema: string): Promise<WarehouseTable[]> => {
    const { data } = await apiClient.get(`${BASE}/warehouse/tables`, {
      params: { schema },
    })
    return data
  },

  /** List columns for a table. */
  listColumns: async (schema: string, table: string): Promise<WarehouseColumn[]> => {
    const { data } = await apiClient.get(`${BASE}/warehouse/columns`, {
      params: { schema, table },
    })
    return data
  },
}

// ═══════════════════════════════════════════════════════════════
// Iceberg Lake Introspection
// ═══════════════════════════════════════════════════════════════

/**
 * One Iceberg table on the tenant's S3 lake. Used as a staging-model
 * source. dbt Studio renders this as ``iceberg('<s3_uri>')`` in the
 * generated ClickHouse SQL.
 */
export interface LakeTable {
  pipeline_id: string
  pipeline_name: string
  namespace: string
  table: string
  s3_uri: string | null
  endpoint_url: string | null
  status: string
  last_run_status: string | null
  last_run_at: string | null
  columns: Array<{ name: string; type?: string; description?: string }>
}

export const lakeApi = {
  /** List Iceberg tables available to the tenant. */
  listTables: async (): Promise<LakeTable[]> => {
    const { data } = await apiClient.get(`${BASE}/lake/tables`)
    return data
  },
}

// ═══════════════════════════════════════════════════════════════
// Execution History
// ═══════════════════════════════════════════════════════════════

export const executionApi = {
  /** List dbt execution history. */
  listExecutions: async (params?: {
    limit?: number
    offset?: number
    command?: string
    status?: string
  }): Promise<DbtExecutionRecord[]> => {
    const { data } = await apiClient.get(`${BASE}/executions`, { params })
    return data
  },

  /** Get a single execution detail. */
  getExecution: async (execId: string): Promise<DbtExecutionRecord> => {
    const { data } = await apiClient.get(`${BASE}/executions/${execId}`)
    return data
  },

  /** Cancel a running execution. */
  cancelExecution: async (execId: string): Promise<DbtExecutionRecord> => {
    const { data } = await apiClient.delete(`${BASE}/executions/${execId}`)
    return data
  },

  /** Get log lines since an offset (polling fallback for WebSocket). */
  getExecutionLogs: async (execId: string, offset = 0): Promise<ExecutionLogResponse> => {
    const { data } = await apiClient.get(`${BASE}/executions/${execId}/logs`, {
      params: { offset },
    })
    return data
  },
}

// ═══════════════════════════════════════════════════════════════
// Test Builder
// ═══════════════════════════════════════════════════════════════

export const testBuilderApi = {
  /** Create a singular (custom SQL) data test. */
  createSingularTest: async (payload: SingularTestCreatePayload): Promise<{ test_name: string; path: string }> => {
    const { data } = await apiClient.post(`${BASE}/tests/singular`, payload)
    return data
  },

  /** Get latest test results. */
  getTestResults: async (): Promise<TestResultsResponse> => {
    const { data } = await apiClient.get(`${BASE}/tests/results`)
    return data
  },
}

// ═══════════════════════════════════════════════════════════════
// Source Freshness
// ═══════════════════════════════════════════════════════════════

export const freshnessApi = {
  /** Configure freshness for a source table. */
  configureFreshness: async (sourceName: string, payload: SourceFreshnessPayload): Promise<Record<string, unknown>> => {
    const { data } = await apiClient.post(`${BASE}/sources/${sourceName}/freshness`, payload)
    return data
  },

  /** Run freshness checks. */
  runFreshness: async (): Promise<Record<string, unknown>> => {
    const { data } = await apiClient.post(`${BASE}/sources/freshness/run`)
    return data
  },
}

// ═══════════════════════════════════════════════════════════════
// Package Manager
// ═══════════════════════════════════════════════════════════════

export const packageApi = {
  /** List installed dbt packages. */
  listPackages: async (): Promise<DbtPackage[]> => {
    const { data } = await apiClient.get(`${BASE}/packages`)
    return data
  },

  /** Update packages.yml. */
  updatePackages: async (packages: DbtPackage[]): Promise<DbtPackage[]> => {
    const { data } = await apiClient.put(`${BASE}/packages`, { packages })
    return data
  },

  /** Run dbt deps to install packages. */
  installPackages: async (): Promise<Record<string, unknown>> => {
    const { data } = await apiClient.post(`${BASE}/packages/install`)
    return data
  },
}
