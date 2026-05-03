/**
 * dbt Studio React Hooks
 * 
 * TanStack Query hooks for dbt-MCP server interactions.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { dbtStudioApi, dbtCoreApi } from '../services/dbtStudioApi'
import type {
  MCPQueryRequest,
  VisualModelCreateRequest,
  ResourceType,
} from '../types'

// Query keys
export const dbtStudioKeys = {
  all: ['dbt-studio'] as const,
  models: () => [...dbtStudioKeys.all, 'models'] as const,
  model: (name: string) => [...dbtStudioKeys.models(), name] as const,
  modelSql: (name: string) => [...dbtStudioKeys.model(name), 'sql'] as const,
  metrics: () => [...dbtStudioKeys.all, 'metrics'] as const,
  dimensions: (metricName?: string) => [...dbtStudioKeys.all, 'dimensions', metricName] as const,
  lineage: (modelName?: string) => [...dbtStudioKeys.all, 'lineage', modelName] as const,
  fullDag: () => [...dbtStudioKeys.all, 'dag'] as const,
  tests: (modelName?: string) => [...dbtStudioKeys.all, 'tests', modelName] as const,
  testResults: (modelName?: string) => [...dbtStudioKeys.all, 'test-results', modelName] as const,
  serverStatus: () => [...dbtStudioKeys.all, 'status'] as const,
}

// ============================================================================
// Model Hooks
// ============================================================================

/**
 * List all dbt models
 */
export function useModels(params?: { resource_type?: ResourceType; tags?: string[] }) {
  return useQuery({
    queryKey: [...dbtStudioKeys.models(), params],
    queryFn: () => dbtStudioApi.listModels(params),
    staleTime: 60_000, // 1 minute
  })
}

/**
 * Get a specific model
 */
export function useModel(modelName: string, enabled = true) {
  return useQuery({
    queryKey: dbtStudioKeys.model(modelName),
    queryFn: () => dbtStudioApi.getModel(modelName),
    enabled: enabled && !!modelName,
    staleTime: 60_000,
  })
}

/**
 * Get compiled SQL for a model
 */
export function useModelSql(modelName: string, enabled = true) {
  return useQuery({
    queryKey: dbtStudioKeys.modelSql(modelName),
    queryFn: () => dbtStudioApi.getModelSql(modelName),
    enabled: enabled && !!modelName,
    staleTime: 60_000,
  })
}

// ============================================================================
// Semantic Layer Hooks
// ============================================================================

/**
 * List semantic layer metrics
 */
export function useMetrics() {
  return useQuery({
    queryKey: dbtStudioKeys.metrics(),
    queryFn: () => dbtStudioApi.listMetrics(),
    staleTime: 60_000,
  })
}

/**
 * List semantic layer dimensions
 */
export function useDimensions(metricName?: string) {
  return useQuery({
    queryKey: dbtStudioKeys.dimensions(metricName),
    queryFn: () => dbtStudioApi.listDimensions(metricName),
    staleTime: 60_000,
  })
}

/**
 * Execute a semantic layer query
 */
export function useSemanticQuery() {
  return useMutation({
    mutationFn: (request: MCPQueryRequest) => dbtStudioApi.query(request),
  })
}

/**
 * Compile a query to SQL
 */
export function useCompileQuery() {
  return useMutation({
    mutationFn: (request: MCPQueryRequest) => dbtStudioApi.compileQuery(request),
  })
}

// ============================================================================
// Lineage Hooks
// ============================================================================

/**
 * Get lineage graph for a model
 */
export function useLineage(
  modelName: string,
  options?: { upstream?: boolean; downstream?: boolean; depth?: number },
  enabled = true
) {
  return useQuery({
    queryKey: [...dbtStudioKeys.lineage(modelName), options],
    queryFn: () => dbtStudioApi.getLineage(modelName, options),
    enabled: enabled && !!modelName,
    staleTime: 60_000,
  })
}

/**
 * Get full project DAG
 */
export function useFullDag(enabled = true) {
  return useQuery({
    queryKey: dbtStudioKeys.fullDag(),
    queryFn: () => dbtStudioApi.getFullDag(),
    enabled,
    staleTime: 60_000,
  })
}

// ============================================================================
// Test Hooks
// ============================================================================

/**
 * List dbt tests
 */
export function useTests(modelName?: string) {
  return useQuery({
    queryKey: dbtStudioKeys.tests(modelName),
    queryFn: () => dbtStudioApi.listTests(modelName),
    staleTime: 60_000,
  })
}

/**
 * Get test results
 */
export function useTestResults(modelName?: string) {
  return useQuery({
    queryKey: dbtStudioKeys.testResults(modelName),
    queryFn: () => dbtStudioApi.getTestResults(modelName),
    staleTime: 30_000, // Refresh more often
  })
}

// ============================================================================
// Visual Model Builder Hooks
// ============================================================================

/**
 * Create a visual model
 */
export function useCreateVisualModel() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (request: VisualModelCreateRequest) => dbtStudioApi.createVisualModel(request),
    onSuccess: () => {
      // Invalidate models list
      queryClient.invalidateQueries({ queryKey: dbtStudioKeys.models() })
      queryClient.invalidateQueries({ queryKey: dbtStudioKeys.fullDag() })
    },
  })
}

/**
 * Validate a visual model
 */
export function useValidateVisualModel() {
  return useMutation({
    mutationFn: (definition: VisualModelCreateRequest['definition']) => 
      dbtStudioApi.validateVisualModel(definition),
  })
}

// ============================================================================
// dbt Core Command Hooks
// ============================================================================

/**
 * Run dbt models
 */
export function useDbtRun() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (params?: {
      select?: string
      exclude?: string
      full_refresh?: boolean
      vars?: Record<string, unknown>
      target?: string
    }) => dbtCoreApi.run(params),
    onSuccess: () => {
      // Invalidate test results as they may have changed
      queryClient.invalidateQueries({ queryKey: dbtStudioKeys.testResults() })
    },
  })
}

/**
 * Run dbt tests
 */
export function useDbtTest() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (params?: {
      select?: string
      exclude?: string
      store_failures?: boolean
    }) => dbtCoreApi.test(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtStudioKeys.testResults() })
    },
  })
}

/**
 * Run dbt build
 */
export function useDbtBuild() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (params?: {
      select?: string
      exclude?: string
      full_refresh?: boolean
    }) => dbtCoreApi.build(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtStudioKeys.testResults() })
    },
  })
}

/**
 * Compile dbt models
 */
export function useDbtCompile() {
  return useMutation({
    mutationFn: (params?: { select?: string }) => dbtCoreApi.compile(params),
  })
}

/**
 * Generate dbt docs
 */
export function useDbtDocs() {
  return useMutation({
    mutationFn: () => dbtCoreApi.generateDocs(),
  })
}

// ============================================================================
// Server Management Hooks
// ============================================================================

/**
 * Get MCP server status
 */
export function useServerStatus(enabled = true) {
  return useQuery({
    queryKey: dbtStudioKeys.serverStatus(),
    queryFn: () => dbtStudioApi.getServerStatus(),
    enabled,
    refetchInterval: 10_000, // Poll every 10 seconds
    staleTime: 5_000,
  })
}

/**
 * Start MCP server
 */
export function useStartServer() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => dbtStudioApi.startServer(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtStudioKeys.serverStatus() })
    },
  })
}

/**
 * Stop MCP server
 */
export function useStopServer() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => dbtStudioApi.stopServer(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtStudioKeys.serverStatus() })
    },
  })
}


// ============================================================================
// Project Management Hooks
// ============================================================================

import { dbtProjectApi } from '../services/dbtStudioApi'

// Project query keys
export const dbtProjectKeys = {
  all: ['dbt-project'] as const,
  structure: () => [...dbtProjectKeys.all, 'structure'] as const,
  file: (path: string) => [...dbtProjectKeys.all, 'file', path] as const,
  models: () => [...dbtProjectKeys.all, 'models'] as const,
  semanticModels: () => [...dbtProjectKeys.all, 'semantic-models'] as const,
}

/**
 * Get project structure
 */
export function useProjectStructure(enabled = true) {
  return useQuery({
    queryKey: dbtProjectKeys.structure(),
    queryFn: () => dbtProjectApi.getStructure(),
    enabled,
    staleTime: 120_000, // 2 minutes
  })
}

/**
 * Get file content
 */
export function useFileContent(path: string, enabled = true) {
  return useQuery({
    queryKey: dbtProjectKeys.file(path),
    queryFn: () => dbtProjectApi.getFileContent(path),
    enabled: enabled && !!path,
    staleTime: 60_000,
  })
}

/**
 * Delete a project file (dbt model, test, snapshot, seed, macro, analysis).
 *
 * Invalidates the project structure and models queries on success so the
 * tree and model lists refresh automatically.
 */
export function useDeleteProjectFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (path: string) => dbtProjectApi.deleteFile(path),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtProjectKeys.structure() })
      queryClient.invalidateQueries({ queryKey: dbtProjectKeys.models() })
    },
  })
}

/**
 * Save (overwrite) a project file. On success, refreshes the cached file
 * content for that path and invalidates the project structure (file size
 * shown in the tree may change).
 */
export function useSaveProjectFile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ path, content }: { path: string; content: string }) =>
      dbtProjectApi.saveFile(path, content),
    onSuccess: (_data, vars) => {
      queryClient.setQueryData(dbtProjectKeys.file(vars.path), {
        path: vars.path,
        content: vars.content,
      })
      queryClient.invalidateQueries({ queryKey: dbtProjectKeys.structure() })
      queryClient.invalidateQueries({ queryKey: dbtProjectKeys.models() })
    },
  })
}

/**
 * List project models
 */
export function useProjectModels(enabled = true) {
  return useQuery({
    queryKey: dbtProjectKeys.models(),
    queryFn: () => dbtProjectApi.listModels(),
    enabled,
    staleTime: 60_000,
  })
}

/**
 * List semantic models
 */
export function useProjectSemanticModels(enabled = true) {
  return useQuery({
    queryKey: dbtProjectKeys.semanticModels(),
    queryFn: () => dbtProjectApi.listSemanticModels(),
    enabled,
    staleTime: 60_000,
  })
}

/**
 * Initialize project
 */
export function useInitProject() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => dbtProjectApi.initProject(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtProjectKeys.all })
    },
  })
}

/**
 * Discover sources
 */
export function useDiscoverSources() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: () => dbtProjectApi.discoverSources(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtProjectKeys.structure() })
    },
  })
}

/**
 * Generate DAG
 */
export function useGenerateDag() {
  return useMutation({
    mutationFn: (params: Parameters<typeof dbtProjectApi.generateDag>[0]) =>
      dbtProjectApi.generateDag(params),
  })
}
