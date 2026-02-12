/**
 * Schema Explorer Hook
 */

import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { SchemaInfo } from '../types'

// Backend response: { schema: { schemas: [...], total_tables: N, total_columns: M } }
interface SchemaResponse {
  schema: {
    schemas: Array<{
      name: string
      tables: Array<{
        name: string
        schema: string
        columns?: Array<{
          name: string
          data_type: string
          nullable: boolean
          is_nullable?: boolean
          primary_key?: boolean
          comment?: string
        }>
        row_count?: number
        comment?: string
        table_type?: string
      }>
    }>
    total_tables: number
    total_columns: number
    error?: string
  }
}

export function useSchemaExplorer(datasourceId: string | undefined) {
  // First, fetch only schema names (fast)
  const schemasQuery = useQuery({
    queryKey: ['schemas', datasourceId],
    queryFn: async () => {
      if (!datasourceId) throw new Error('No datasource selected')
      
      const response = await api.get<SchemaResponse>(
        `/api/v1/connections/${datasourceId}/schema`,
        { params: { schemas_only: 'true' } }
      )
      
      if (response.data.schema.error) {
        throw new Error(response.data.schema.error)
      }
      
      return response.data.schema.schemas.map(s => s.name)
    },
    enabled: !!datasourceId,
    staleTime: 5 * 60 * 1000,
  })

  // Then fetch tables with columns for all schemas
  const tablesQuery = useQuery({
    queryKey: ['schema-tables', datasourceId],
    queryFn: async () => {
      if (!datasourceId) throw new Error('No datasource selected')
      
      const response = await api.get<SchemaResponse>(
        `/api/v1/connections/${datasourceId}/schema`,
        { params: { include_columns: 'true' } }
      )
      
      if (response.data.schema.error) {
        throw new Error(response.data.schema.error)
      }
      
      const schemas: SchemaInfo[] = response.data.schema.schemas.map((schema) => ({
        name: schema.name,
        tables: schema.tables.map((table) => ({
          name: table.name,
          schema: table.schema,
          columns: (table.columns || []).map((col) => ({
            name: col.name,
            type: col.data_type,
            nullable: col.nullable ?? col.is_nullable ?? true,
            isPrimaryKey: col.primary_key,
            isForeignKey: false,
            comment: col.comment,
          })),
          rowCount: table.row_count,
          comment: table.comment,
        })),
      }))
      
      return schemas
    },
    enabled: !!datasourceId && schemasQuery.isSuccess,
    staleTime: 5 * 60 * 1000,
  })

  return {
    schemas: tablesQuery.data || [],
    schemaNames: schemasQuery.data || [],
    isLoading: schemasQuery.isLoading || tablesQuery.isLoading,
    isLoadingSchemas: schemasQuery.isLoading,
    isLoadingTables: tablesQuery.isLoading,
    error: schemasQuery.error?.message || tablesQuery.error?.message || null,
    refetch: tablesQuery.refetch,
  }
}

/**
 * Hook to fetch tables for a specific schema on demand
 */
export function useSchemaTablesLazy(datasourceId: string | undefined, schemaName: string | undefined) {
  return useQuery({
    queryKey: ['schema-tables', datasourceId, schemaName],
    queryFn: async () => {
      if (!datasourceId || !schemaName) throw new Error('Missing parameters')
      
      const response = await api.get<SchemaResponse>(
        `/api/v1/connections/${datasourceId}/schema`,
        { params: { schema_name: schemaName, include_columns: 'false' } }
      )
      
      if (response.data.schema.error) {
        throw new Error(response.data.schema.error)
      }
      
      const schema = response.data.schema.schemas[0]
      if (!schema) return []
      
      return schema.tables.map((table) => ({
        name: table.name,
        schema: table.schema,
        columns: [],
        rowCount: table.row_count,
        comment: table.comment,
      }))
    },
    enabled: !!datasourceId && !!schemaName,
    staleTime: 5 * 60 * 1000,
  })
}

export function useTablePreview(datasourceId: string | undefined, tableName: string | undefined) {
  return useQuery({
    queryKey: ['table-preview', datasourceId, tableName],
    queryFn: async () => {
      if (!datasourceId || !tableName) throw new Error('Missing parameters')
      
      const response = await api.get<{ rows: Record<string, unknown>[] }>(
        `/api/v1/connections/${datasourceId}/tables/${tableName}/preview`
      )
      
      return response.data.rows
    },
    enabled: !!datasourceId && !!tableName,
  })
}
