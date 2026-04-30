/**
 * Query Feature Module
 * Natural language query interface for ad-hoc analytics
 */

// Pages
export { QueryPage } from './pages/QueryPage'
export { AIWorkbenchPage } from './pages/AIWorkbenchPage'

// Components
export { QueryResult } from './components/QueryResult'
export { QuerySuggestions } from './components/QuerySuggestions'
export { QueryHistory } from './components/QueryHistory'
export { QueryLoadingState } from './components/QueryLoadingState'
export { QueryError } from './components/QueryError'
export { SaveToDashboardDialog } from './components/SaveToDashboardDialog'
export { CodeBlock } from './components/CodeBlock'

// Hooks
export { useQueryHistory } from './hooks/useQueryHistory'

// Types
export type {
  QueryIntent,
  QueryData,
  QueryResult as QueryResultType,
  QueryHistoryItem,
  SaveToWidgetConfig,
} from './types'
