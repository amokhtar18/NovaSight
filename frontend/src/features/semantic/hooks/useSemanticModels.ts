/**
 * Semantic Layer API Hooks
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import type {
  SemanticModel,
  Dimension,
  Measure,
  Relationship,
  CreateSemanticModelDto,
  UpdateSemanticModelDto,
  CreateDimensionDto,
  UpdateDimensionDto,
  CreateMeasureDto,
  UpdateMeasureDto,
  CreateRelationshipDto,
  SemanticQuery,
  QueryResult,
} from '../types'

const SEMANTIC_MODELS_KEY = 'semantic-models'
const SEMANTIC_EXPLORE_KEY = 'semantic-explore'

// ============================================================================
// Semantic Models
// ============================================================================

export function useSemanticModels(options?: { includeInactive?: boolean; modelType?: string }) {
  return useQuery({
    queryKey: [SEMANTIC_MODELS_KEY, options],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (options?.includeInactive) params.append('include_inactive', 'true')
      if (options?.modelType) params.append('model_type', options.modelType)
      
      const response = await api.get<SemanticModel[]>(`/v1/semantic/models?${params}`)
      return response.data
    },
  })
}

export function useSemanticModel(modelId: string | undefined) {
  return useQuery({
    queryKey: [SEMANTIC_MODELS_KEY, modelId],
    queryFn: async () => {
      const response = await api.get<SemanticModel>(`/v1/semantic/models/${modelId}`)
      return response.data
    },
    enabled: !!modelId,
  })
}

export function useCreateSemanticModel() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: CreateSemanticModelDto) => {
      const response = await api.post<SemanticModel>('/v1/semantic/models', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY] })
    },
  })
}

export function useUpdateSemanticModel() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateSemanticModelDto }) => {
      const response = await api.put<SemanticModel>(`/v1/semantic/models/${id}`, data)
      return response.data
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY] })
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY, id] })
    },
  })
}

export function useDeleteSemanticModel() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/v1/semantic/models/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY] })
    },
  })
}

// ============================================================================
// Dimensions
// ============================================================================

export function useDimensions(modelId: string | undefined, options?: { includeHidden?: boolean }) {
  return useQuery({
    queryKey: [SEMANTIC_MODELS_KEY, modelId, 'dimensions', options],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (options?.includeHidden) params.append('include_hidden', 'true')
      
      const response = await api.get<Dimension[]>(
        `/v1/semantic/models/${modelId}/dimensions?${params}`
      )
      return response.data
    },
    enabled: !!modelId,
  })
}

export function useAddDimension() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ modelId, data }: { modelId: string; data: CreateDimensionDto }) => {
      const response = await api.post<Dimension>(
        `/v1/semantic/models/${modelId}/dimensions`,
        data
      )
      return response.data
    },
    onSuccess: (_, { modelId }) => {
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY, modelId] })
    },
  })
}

export function useUpdateDimension() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ 
      dimensionId, 
      data 
    }: { 
      dimensionId: string
      modelId: string
      data: UpdateDimensionDto 
    }) => {
      const response = await api.put<Dimension>(
        `/v1/semantic/dimensions/${dimensionId}`,
        data
      )
      return response.data
    },
    onSuccess: (_, { modelId }) => {
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY, modelId] })
    },
  })
}

export function useDeleteDimension() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ dimensionId }: { dimensionId: string; modelId: string }) => {
      await api.delete(`/v1/semantic/dimensions/${dimensionId}`)
    },
    onSuccess: (_, { modelId }) => {
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY, modelId] })
    },
  })
}

// ============================================================================
// Measures
// ============================================================================

export function useMeasures(modelId: string | undefined, options?: { includeHidden?: boolean }) {
  return useQuery({
    queryKey: [SEMANTIC_MODELS_KEY, modelId, 'measures', options],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (options?.includeHidden) params.append('include_hidden', 'true')
      
      const response = await api.get<Measure[]>(
        `/v1/semantic/models/${modelId}/measures?${params}`
      )
      return response.data
    },
    enabled: !!modelId,
  })
}

export function useAddMeasure() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ modelId, data }: { modelId: string; data: CreateMeasureDto }) => {
      const response = await api.post<Measure>(
        `/v1/semantic/models/${modelId}/measures`,
        data
      )
      return response.data
    },
    onSuccess: (_, { modelId }) => {
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY, modelId] })
    },
  })
}

export function useUpdateMeasure() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ 
      measureId, 
      data 
    }: { 
      measureId: string
      modelId: string
      data: UpdateMeasureDto 
    }) => {
      const response = await api.put<Measure>(
        `/v1/semantic/measures/${measureId}`,
        data
      )
      return response.data
    },
    onSuccess: (_, { modelId }) => {
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY, modelId] })
    },
  })
}

export function useDeleteMeasure() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async ({ measureId }: { measureId: string; modelId: string }) => {
      await api.delete(`/v1/semantic/measures/${measureId}`)
    },
    onSuccess: (_, { modelId }) => {
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY, modelId] })
    },
  })
}

// ============================================================================
// Relationships
// ============================================================================

export function useRelationships() {
  return useQuery({
    queryKey: [SEMANTIC_MODELS_KEY, 'relationships'],
    queryFn: async () => {
      const response = await api.get<Relationship[]>('/v1/semantic/relationships')
      return response.data
    },
  })
}

export function useCreateRelationship() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (data: CreateRelationshipDto) => {
      const response = await api.post<Relationship>('/v1/semantic/relationships', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY] })
    },
  })
}

export function useDeleteRelationship() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/v1/semantic/relationships/${id}`)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [SEMANTIC_MODELS_KEY] })
    },
  })
}

// ============================================================================
// Query Execution
// ============================================================================

export function useSemanticQuery() {
  return useMutation({
    mutationFn: async (query: SemanticQuery) => {
      const response = await api.post<QueryResult>('/v1/semantic/query', query)
      return response.data
    },
  })
}

// ============================================================================
// Explore / Discovery
// ============================================================================

export function useSemanticExplore() {
  return useQuery({
    queryKey: [SEMANTIC_EXPLORE_KEY],
    queryFn: async () => {
      const response = await api.get<{
        models: SemanticModel[]
        dimensions: Dimension[]
        measures: Measure[]
        relationships: Relationship[]
      }>('/v1/semantic/explore')
      return response.data
    },
  })
}

// ============================================================================
// Cache Management
// ============================================================================

export function useClearSemanticCache() {
  return useMutation({
    mutationFn: async () => {
      const response = await api.post<{ message: string; entries_cleared: number }>(
        '/v1/semantic/cache/clear'
      )
      return response.data
    },
  })
}
