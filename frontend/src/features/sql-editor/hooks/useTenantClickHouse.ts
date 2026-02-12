/**
 * Tenant ClickHouse Hook
 */

import { useQuery, useMutation } from '@tanstack/react-query'
import api from '@/lib/api'
import type { SqlQueryResult, SchemaInfo } from '../types'

interface ClickHouseInfo {
  database: string
  tenant_id: string
  type: 'clickhouse'
  name: string
}

interface ExecuteClickHouseQueryParams {
  sql: string
  limit?: number
}

interface ClickHouseSchemaResponse {
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
          primary_key?: boolean
          comment?: string
        }>
        row_count?: number
        comment?: string
        engine?: string
      }>
    }>
    total_tables: number
    total_columns: number
    error?: string
  }
}

export function useTenantClickHouseInfo() {
  return useQuery({
    queryKey: ['tenant-clickhouse-info'],
    queryFn: async () => {
      const response = await api.get<ClickHouseInfo>('/api/v1/clickhouse/info')
      return response.data
    },
  })
}

export function useTenantClickHouseSchema(enabled: boolean = true) {
  return useQuery({
    queryKey: ['tenant-clickhouse-schema'],
    queryFn: async () => {
      const response = await api.get<ClickHouseSchemaResponse>(
        '/api/v1/clickhouse/schema',
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
            nullable: col.nullable ?? true,
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
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useClickHouseQuery() {
  return useMutation({
    mutationFn: async ({ sql, limit = 1000 }: ExecuteClickHouseQueryParams) => {
      const response = await api.post<SqlQueryResult>('/api/v1/clickhouse/query', {
        sql,
        limit,
      })
      return response.data
    },
  })
}
