/**
 * SQL Editor Feature Module
 * Direct SQL query interface with Monaco editor
 */

// Pages
export { SqlEditorPage } from './pages/SqlEditorPage'

// Components
export { SQLEditor } from './components/SQLEditor'
export { ResultsTable } from './components/ResultsTable'
export { SQLResultsChart } from './components/SQLResultsChart'
export { SchemaExplorer } from './components/SchemaExplorer'
export { QueryTabs } from './components/QueryTabs'
export { SavedQueriesList } from './components/SavedQueriesList'

// Hooks
export { useSqlQuery } from './hooks/useSqlQuery'
export { useSchemaExplorer } from './hooks/useSchemaExplorer'
export { useSavedQueries, useCreateSavedQuery, useUpdateSavedQuery, useDeleteSavedQuery } from './hooks/useSavedQueries'
export { useTenantClickHouseInfo, useClickHouseQuery } from './hooks/useTenantClickHouse'

// Types
export type { SqlQueryResult, SchemaInfo, TableSchema, ColumnInfo, SavedQuery, DatasourceOption } from './types'
