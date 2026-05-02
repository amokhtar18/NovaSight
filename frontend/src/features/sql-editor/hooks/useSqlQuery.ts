/**
 * SQL Query Execution Hook
 *
 * Internals: when the per-tenant `FEATURE_SUPERSET_BACKEND` flag is on,
 * execution is transparently re-routed to Superset SQL Lab
 * (Phase 6 of the Superset integration). The hook return shape is
 * unchanged so the SQL Editor UI keeps working without modification.
 */

import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import api from '@/lib/api'
import {
  isSupersetBackendEnabled,
  supersetService,
} from '@/services/supersetService'
import type { SqlQueryResult } from '../types'

interface ExecuteQueryParams {
  sql: string
  datasourceId?: string
  isClickhouse?: boolean
  limit?: number
}

interface ExecuteQueryResponse {
  columns: Array<{ name: string; type: string }>
  rows: Record<string, unknown>[]
  row_count: number
  execution_time_ms: number
  truncated: boolean
}

export function useSqlQuery() {
  const [result, setResult] = useState<SqlQueryResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: async ({ sql, datasourceId, isClickhouse, limit = 1000 }: ExecuteQueryParams) => {
      // Phase 6: route tenant-CH queries via Superset SQL Lab when the flag is on.
      if (isClickhouse && (await isSupersetBackendEnabled())) {
        const result = await supersetService.executeSql({ sql, runAsync: false })
        const columns = (result.columns || []).map((c) => ({
          name: c.name,
          type: c.type,
        }))
        const rows = (result.data || []) as Record<string, unknown>[]
        return {
          columns,
          rows,
          row_count: rows.length,
          execution_time_ms: 0,
          truncated: rows.length >= limit,
        } as ExecuteQueryResponse
      }

      // Use ClickHouse endpoint for tenant ClickHouse
      if (isClickhouse) {
        const response = await api.post<ExecuteQueryResponse>('/api/v1/clickhouse/query', {
          sql,
          limit,
        })
        return response.data
      }
      
      // Use connection endpoint for configured datasources
      if (!datasourceId) {
        throw new Error('No datasource selected')
      }
      
      const response = await api.post<ExecuteQueryResponse>('/api/v1/query/execute', {
        sql,
        connection_id: datasourceId,
        limit,
      })
      return response.data
    },
    onSuccess: (data) => {
      setResult({
        columns: data.columns,
        rows: data.rows,
        rowCount: data.row_count,
        executionTimeMs: data.execution_time_ms,
        truncated: data.truncated,
      })
      setError(null)
    },
    onError: (err: unknown) => {
      const errorMessage = err instanceof Error ? err.message : 'Query execution failed'
      // Try to extract error from API response
      const apiError = err as { response?: { data?: { error?: { message?: string } } } }
      const message = apiError.response?.data?.error?.message || errorMessage
      setError(message)
      setResult(null)
    },
  })

  const execute = useCallback(
    (params: ExecuteQueryParams) => {
      setError(null)
      mutation.mutate(params)
    },
    [mutation]
  )

  const clear = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return {
    execute,
    result,
    error,
    isLoading: mutation.isPending,
    clear,
  }
}
