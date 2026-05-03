/**
 * dbt Studio API Service
 * 
 * Client for dbt-MCP server interactions including:
 * - Semantic layer queries
 * - Model introspection
 * - Lineage exploration
 * - Visual model building
 */

import { apiClient } from '@/services/apiClient'
import type {
  MCPQueryRequest,
  MCPQueryResponse,
  MCPModel,
  MCPModelListResponse,
  MCPMetric,
  MCPDimension,
  LineageGraph,
  MCPTestResultsResponse,
  VisualModelCreateRequest,
  VisualModelCreateResponse,
  MCPServerStatus,
  ResourceType,
} from '../types'

const BASE_URL = '/api/v1/dbt/mcp'

/**
 * dbt Studio API client
 */
export const dbtStudioApi = {
  // ============================================================================
  // Semantic Layer Query
  // ============================================================================

  /**
   * Execute a semantic layer query
   */
  async query(request: MCPQueryRequest): Promise<MCPQueryResponse> {
    const response = await apiClient.post(`${BASE_URL}/query`, request)
    return response.data
  },

  /**
   * Compile a query to SQL without executing
   */
  async compileQuery(request: MCPQueryRequest): Promise<{ success: boolean; compiled_sql: string }> {
    const response = await apiClient.post(`${BASE_URL}/compile`, {
      ...request,
      compile_only: true,
    })
    return response.data
  },

  // ============================================================================
  // Model Operations
  // ============================================================================

  /**
   * List all dbt models
   */
  async listModels(params?: {
    resource_type?: ResourceType
    tags?: string[]
  }): Promise<MCPModelListResponse> {
    const queryParams = new URLSearchParams()
    if (params?.resource_type) {
      queryParams.set('resource_type', params.resource_type)
    }
    if (params?.tags?.length) {
      queryParams.set('tags', params.tags.join(','))
    }
    const url = queryParams.toString() ? `${BASE_URL}/models?${queryParams}` : `${BASE_URL}/models`
    const response = await apiClient.get(url)
    return response.data
  },

  /**
   * Get a specific model by name
   */
  async getModel(modelName: string): Promise<MCPModel> {
    const response = await apiClient.get(`${BASE_URL}/models/${encodeURIComponent(modelName)}`)
    return response.data
  },

  /**
   * Get compiled SQL for a model
   */
  async getModelSql(modelName: string): Promise<{ model_name: string; sql: string }> {
    const response = await apiClient.get(`${BASE_URL}/models/${encodeURIComponent(modelName)}/sql`)
    return response.data
  },

  // ============================================================================
  // Semantic Layer Metadata
  // ============================================================================

  /**
   * List semantic layer metrics
   */
  async listMetrics(): Promise<{ metrics: MCPMetric[] }> {
    const response = await apiClient.get(`${BASE_URL}/metrics`)
    return response.data
  },

  /**
   * List semantic layer dimensions
   */
  async listDimensions(metricName?: string): Promise<{ dimensions: MCPDimension[] }> {
    const url = metricName 
      ? `${BASE_URL}/dimensions?metric=${encodeURIComponent(metricName)}`
      : `${BASE_URL}/dimensions`
    const response = await apiClient.get(url)
    return response.data
  },

  // ============================================================================
  // Lineage Operations
  // ============================================================================

  /**
   * Get lineage graph for a model
   */
  async getLineage(
    modelName: string,
    options?: {
      upstream?: boolean
      downstream?: boolean
      depth?: number
    }
  ): Promise<LineageGraph> {
    const params = new URLSearchParams()
    if (options?.upstream !== undefined) params.set('upstream', String(options.upstream))
    if (options?.downstream !== undefined) params.set('downstream', String(options.downstream))
    if (options?.depth !== undefined) params.set('depth', String(options.depth))
    
    const url = params.toString()
      ? `${BASE_URL}/lineage/${encodeURIComponent(modelName)}?${params}`
      : `${BASE_URL}/lineage/${encodeURIComponent(modelName)}`
    
    const response = await apiClient.get(url)
    return response.data
  },

  /**
   * Get the complete project DAG
   */
  async getFullDag(): Promise<LineageGraph> {
    const response = await apiClient.get(`${BASE_URL}/lineage`)
    return response.data
  },

  // ============================================================================
  // Test Operations
  // ============================================================================

  /**
   * List dbt tests
   */
  async listTests(modelName?: string): Promise<{ tests: unknown[]; total_count: number }> {
    const url = modelName
      ? `${BASE_URL}/tests?model=${encodeURIComponent(modelName)}`
      : `${BASE_URL}/tests`
    const response = await apiClient.get(url)
    return response.data
  },

  /**
   * Get latest test results
   */
  async getTestResults(modelName?: string): Promise<MCPTestResultsResponse> {
    const url = modelName
      ? `${BASE_URL}/tests/results?model=${encodeURIComponent(modelName)}`
      : `${BASE_URL}/tests/results`
    const response = await apiClient.get(url)
    return response.data
  },

  // ============================================================================
  // Visual Model Builder
  // ============================================================================

  /**
   * Create a model from visual definition
   */
  async createVisualModel(request: VisualModelCreateRequest): Promise<VisualModelCreateResponse> {
    const response = await apiClient.post(`${BASE_URL}/visual-models`, request)
    return response.data
  },

  /**
   * Validate a visual model definition without creating files
   */
  async validateVisualModel(definition: VisualModelCreateRequest['definition']): Promise<VisualModelCreateResponse> {
    const response = await apiClient.post(`${BASE_URL}/visual-models`, {
      definition,
      validate_only: true,
    })
    return response.data
  },

  // ============================================================================
  // Server Management
  // ============================================================================

  /**
   * Get MCP server status
   */
  async getServerStatus(): Promise<MCPServerStatus> {
    const response = await apiClient.get(`${BASE_URL}/status`)
    return response.data
  },

  /**
   * Start the MCP server
   */
  async startServer(): Promise<{ success: boolean; status: string }> {
    const response = await apiClient.post(`${BASE_URL}/start`)
    return response.data
  },

  /**
   * Stop the MCP server
   */
  async stopServer(): Promise<{ success: boolean; status: string }> {
    const response = await apiClient.post(`${BASE_URL}/stop`)
    return response.data
  },
}

/**
 * dbt Core API client (for running dbt commands)
 */
export const dbtCoreApi = {
  /**
   * Run dbt models
   */
  async run(params?: {
    select?: string
    exclude?: string
    full_refresh?: boolean
    vars?: Record<string, unknown>
    target?: string
  }) {
    const response = await apiClient.post('/api/v1/dbt/run', params || {})
    return response.data
  },

  /**
   * Run dbt tests
   */
  async test(params?: {
    select?: string
    exclude?: string
    store_failures?: boolean
  }) {
    const response = await apiClient.post('/api/v1/dbt/test', params || {})
    return response.data
  },

  /**
   * Run dbt build (run + test)
   */
  async build(params?: {
    select?: string
    exclude?: string
    full_refresh?: boolean
  }) {
    const response = await apiClient.post('/api/v1/dbt/build', params || {})
    return response.data
  },

  /**
   * Compile dbt models
   */
  async compile(params?: { select?: string }) {
    const response = await apiClient.post('/api/v1/dbt/compile', params || {})
    return response.data
  },

  /**
   * Generate dbt docs
   */
  async generateDocs() {
    const response = await apiClient.post('/api/v1/dbt/docs/generate')
    return response.data
  },

  /**
   * Get model lineage with depth control
   */
  async getLineage(
    modelName: string,
    options?: { upstreamDepth?: number; downstreamDepth?: number }
  ) {
    const params = new URLSearchParams()
    if (options?.upstreamDepth !== undefined) {
      params.set('upstream_depth', String(options.upstreamDepth))
    }
    if (options?.downstreamDepth !== undefined) {
      params.set('downstream_depth', String(options.downstreamDepth))
    }
    const url = params.toString()
      ? `/api/v1/dbt/lineage/${encodeURIComponent(modelName)}?${params}`
      : `/api/v1/dbt/lineage/${encodeURIComponent(modelName)}`
    const response = await apiClient.get(url)
    return response.data
  },

  /**
   * Get impact analysis for a model (downstream dependency counts)
   */
  async getImpactAnalysis(modelName: string) {
    const response = await apiClient.get(
      `/api/v1/dbt/lineage/${encodeURIComponent(modelName)}/impact`
    )
    return response.data
  },
}

// ============================================================================
// Project Management API
// ============================================================================

export const dbtProjectApi = {
  /**
   * Initialize tenant dbt project
   */
  async initProject(): Promise<{
    success: boolean
    project_path: string
    source_database: string
    target_database: string
    tenant_slug: string
  }> {
    const response = await apiClient.post('/api/v1/dbt/project/init')
    return response.data
  },

  /**
   * Get project structure
   */
  async getStructure(): Promise<{
    exists: boolean
    path: string
    tenant_slug: string
    source_database: string
    target_database: string
    structure: ProjectNode
  }> {
    const response = await apiClient.get('/api/v1/dbt/project/structure')
    return response.data
  },

  /**
   * Get file content from project
   */
  async getFileContent(path: string): Promise<{ path: string; content: string }> {
    const response = await apiClient.get('/api/v1/dbt/project/file', {
      params: { path },
    })
    return response.data
  },

  /**
   * Update (overwrite) a file in the tenant project. Only files under the
   * dbt user-managed directories (models, tests, snapshots, seeds, macros,
   * analyses) with safe text extensions can be edited.
   */
  async saveFile(
    path: string,
    content: string,
  ): Promise<{ success: boolean; path: string; size: number }> {
    const response = await apiClient.put(
      '/api/v1/dbt/project/file',
      { content },
      { params: { path } },
    )
    return response.data
  },

  /**
   * Delete a file (dbt model, test, snapshot, seed, macro, or analysis)
   * from the tenant project. For .sql models, the paired schema YAML
   * (`_<name>.yml`) is also removed when present.
   */
  async deleteFile(path: string): Promise<{ success: boolean; deleted: string[] }> {
    const response = await apiClient.delete('/api/v1/dbt/project/file', {
      params: { path },
    })
    return response.data
  },

  /**
   * List project models
   */
  async listModels(): Promise<{
    models: ProjectModel[]
    total_count: number
  }> {
    const response = await apiClient.get('/api/v1/dbt/project/models')
    return response.data
  },

  /**
   * List semantic models
   */
  async listSemanticModels(): Promise<{
    semantic_models: SemanticModelConfig[]
    total_count: number
  }> {
    const response = await apiClient.get('/api/v1/dbt/project/semantic-models')
    return response.data
  },

  /**
   * Discover source tables from tenant ClickHouse
   */
  async discoverSources(): Promise<{
    success: boolean
    source_database: string
    target_database: string
    tables_discovered: number
    tables: SourceTable[]
  }> {
    const response = await apiClient.post('/api/v1/dbt/project/sources/discover')
    return response.data
  },

  /**
   * Generate Dagster pipeline for dbt transformations
   */
  async generateDag(params: {
    dag_id: string
    schedule_interval?: string
    dbt_command?: string
    dbt_select?: string
    dbt_exclude?: string
    dbt_full_refresh?: boolean
    include_test?: boolean
    generate_docs?: boolean
    tags?: string[]
    retries?: number
    email_on_failure?: boolean
  }): Promise<{
    success: boolean
    dag_id: string
    dag_path: string
    dag_content: string
    source_database: string
    target_database: string
  }> {
    const response = await apiClient.post('/api/v1/dbt/dag/generate', params)
    return response.data
  },
}

// Types for project API
export interface ProjectNode {
  name: string
  path: string
  type: 'directory' | 'file'
  children?: ProjectNode[]
  size?: number
  extension?: string
}

export interface ProjectModel {
  name: string
  path: string
  layer: string
  full_path: string
}

export interface SemanticModelConfig {
  name: string
  source_file: string
  [key: string]: unknown
}

export interface SourceTable {
  name: string
  engine: string
  total_rows: number
  total_bytes: number
}

export default dbtStudioApi
