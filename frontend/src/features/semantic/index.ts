/**
 * Semantic Layer Feature - Barrel Export
 * 
 * This module exports all components, pages, hooks, and types
 * for the semantic layer management feature.
 */

// Types
export * from './types'

// Hooks
export { 
  useSemanticModels,
  useSemanticModel,
  useCreateSemanticModel,
  useUpdateSemanticModel,
  useDeleteSemanticModel,
  useDimensions,
  useAddDimension,
  useUpdateDimension,
  useDeleteDimension,
  useMeasures,
  useAddMeasure,
  useUpdateMeasure,
  useDeleteMeasure,
  useRelationships,
  useCreateRelationship,
  useDeleteRelationship,
  useSemanticQuery,
  useSemanticExplore,
  useClearSemanticCache,
} from './hooks/useSemanticModels'

// Components
export { ModelCard } from './components/ModelCard'
export { CreateModelDialog } from './components/CreateModelDialog'
export { ModelBuilder } from './components/ModelBuilder'
export { ModelSettings } from './components/ModelSettings'
export { ModelPreview } from './components/ModelPreview'
export { DimensionList } from './components/DimensionList'
export { DimensionEditor } from './components/DimensionEditor'
export { MeasureList } from './components/MeasureList'
export { MeasureEditor } from './components/MeasureEditor'
export { RelationshipDiagram } from './components/RelationshipDiagram'

// Pages
export { SemanticModelsPage } from './pages/SemanticModelsPage'
export { ModelDetailPage } from './pages/ModelDetailPage'
