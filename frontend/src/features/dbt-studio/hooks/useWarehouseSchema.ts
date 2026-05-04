/**
 * TanStack Query hooks for ClickHouse warehouse introspection.
 *
 * Provides hooks for listing schemas, tables, and columns
 * from the tenant's ClickHouse database.
 */

import { useQuery, useQueries } from '@tanstack/react-query'
import { warehouseApi, lakeApi } from '../services/visualModelApi'

const KEYS = {
  schemas: () => ['warehouse', 'schemas'] as const,
  tables: (schema: string) => ['warehouse', 'tables', schema] as const,
  columns: (schema: string, table: string) => ['warehouse', 'columns', schema, table] as const,
  modelColumns: (model: string) => ['warehouse', 'model-columns', model] as const,
  lakeTables: () => ['lake', 'tables'] as const,
}

/** List ClickHouse schemas/databases. */
export function useWarehouseSchemas() {
  return useQuery({
    queryKey: KEYS.schemas(),
    queryFn: warehouseApi.listSchemas,
  })
}

/** List tables in a schema. */
export function useWarehouseTables(schema: string | undefined) {
  return useQuery({
    queryKey: KEYS.tables(schema!),
    queryFn: () => warehouseApi.listTables(schema!),
    enabled: !!schema,
  })
}

/** List columns for a specific table. */
export function useWarehouseColumns(schema: string | undefined, table: string | undefined) {
  return useQuery({
    queryKey: KEYS.columns(schema!, table!),
    queryFn: () => warehouseApi.listColumns(schema!, table!),
    enabled: !!schema && !!table,
  })
}

/**
 * List output columns for a saved dbt model by name.
 *
 * Used by the SQL Builder when the user references an upstream model
 * via ``ref()`` — the builder needs to know what columns that model
 * exposes so SELECT/JOIN/WHERE/GROUP BY can offer real choices instead
 * of free-text fields.
 */
export function useModelColumns(modelName: string | undefined) {
  return useQuery({
    queryKey: KEYS.modelColumns(modelName!),
    queryFn: () => warehouseApi.listModelColumns(modelName!),
    enabled: !!modelName,
    staleTime: 60_000,
  })
}

/**
 * Resolve columns for a list of model names in parallel and flatten
 * the result. Each returned column is annotated with its source model
 * via the ``comment`` field (``"<model>:<original comment>"``) so the
 * SELECT builder can render a label like ``stg_orders.customer_id``.
 *
 * Returns ``{ columns, isLoading }``. Empty list when ``modelNames`` is
 * empty.
 */
export function useColumnsForModels(modelNames: string[]) {
  const results = useQueries({
    queries: modelNames.map((name) => ({
      queryKey: KEYS.modelColumns(name),
      queryFn: () => warehouseApi.listModelColumns(name),
      enabled: !!name,
      staleTime: 60_000,
    })),
  })
  const isLoading = results.some((r) => r.isLoading)
  const byModel: Record<string, Array<{ name: string; type: string; comment: string }>> = {}
  modelNames.forEach((name, idx) => {
    byModel[name] = (results[idx].data as Array<{ name: string; type: string; comment: string }>) || []
  })
  // Flatten with deduping by ``<model>.<column>`` so the SELECT builder
  // can show every column even when two refs share a column name.
  const seen = new Set<string>()
  const flat: Array<{ name: string; type: string; comment: string }> = []
  for (const name of modelNames) {
    for (const col of byModel[name] || []) {
      const key = `${name}.${col.name}`
      if (seen.has(key)) continue
      seen.add(key)
      flat.push({
        name: col.name,
        type: col.type,
        comment: name + (col.comment ? ` — ${col.comment}` : ''),
      })
    }
  }
  return { columns: flat, byModel, isLoading }
}

/**
 * List Iceberg tables on the tenant's S3 lake.
 *
 * These are surfaced in the dbt Studio Schema Explorer alongside
 * ClickHouse tables. Selecting one in the model builder renders the
 * generated SQL with ``iceberg('s3://...')`` and still materializes
 * into the tenant's ClickHouse database.
 */
export function useLakeTables() {
  return useQuery({
    queryKey: KEYS.lakeTables(),
    queryFn: lakeApi.listTables,
  })
}
