/**
 * VisualQueryBuilder — Main no-code SQL builder.
 *
 * Orchestrates the SELECT, JOIN, WHERE, GROUP BY sub-builders
 * and emits a VisualModelCreatePayload on save.
 */

import { useState, useCallback, useEffect, useMemo } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Database, Layers, Save, Eye, Code, GitBranch, X, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { SelectBuilder } from './SelectBuilder'
import { JoinBuilder } from './JoinBuilder'
import { WhereBuilder } from './WhereBuilder'
import { GroupByBuilder } from './GroupByBuilder'
import { SavedQueryPicker } from '../shared/SavedQueryPicker'
import type { SavedQuery } from '../../hooks/useDbtSavedQueries'
import {
  useWarehouseSchemas,
  useWarehouseTables,
  useLakeTables,
} from '../../hooks/useWarehouseSchema'
import type {
  VisualModelCreatePayload,
  VisualColumnConfig,
  VisualJoinConfig,
  WarehouseColumn,
} from '../../types/visualModel'
import type { Materialization } from '../../types'

/**
 * Convert a free-form identifier (e.g. "Revenue By Branch") to the
 * snake_case form required by dbt and the backend Pydantic schema
 * (`^[a-z][a-z0-9_]*$` for models, `^[a-z_][a-z0-9_]*$` for columns).
 *
 * - Trims, lowercases, replaces non-alphanumeric runs with `_`.
 * - Collapses repeated `_` and trims leading/trailing `_`.
 * - For models, prepends `m_` if the result starts with a digit so it
 *   still satisfies the leading-letter constraint.
 */
function sanitizeIdentifier(
  value: string,
  kind: 'model' | 'column' = 'column',
): string {
  if (!value) return ''
  // Insert underscore at lower→Upper boundaries so PascalCase becomes snake.
  const snaked = value
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1_$2')
  let safe = snaked
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '')
  if (!safe) return ''
  if (kind === 'model' && /^[0-9]/.test(safe)) {
    safe = `m_${safe}`
  }
  return safe
}

export interface VisualQueryBuilderProps {
  /** Available columns from ClickHouse for the selected source. */
  availableColumns: WarehouseColumn[]
  /** Available upstream models for ref() joins. */
  availableModels: string[]
  /** Initial values (for editing). */
  initialValues?: Partial<VisualModelCreatePayload>
  /** Auto-fill source schema from Schema Explorer selection. */
  selectedSourceSchema?: string
  /** Auto-fill source table from Schema Explorer selection. */
  selectedSourceTable?: string
  /** Notify parent when source schema is changed via the dropdown. */
  onSchemaChange?: (schema: string) => void
  /** Notify parent when source table is changed via the dropdown. */
  onTableChange?: (table: string) => void
  /** Called when user saves the model configuration. */
  onSave: (payload: VisualModelCreatePayload) => void
  /** Called when user requests code preview. */
  onPreview: (payload: VisualModelCreatePayload) => void
  /** Whether a save is in progress. */
  isSaving?: boolean
}

export function VisualQueryBuilder({
  availableColumns,
  availableModels,
  initialValues,
  selectedSourceSchema,
  selectedSourceTable,
  onSchemaChange,
  onTableChange,
  onSave,
  onPreview,
  isSaving = false,
}: VisualQueryBuilderProps) {
  const [modelName, setModelName] = useState(initialValues?.model_name || '')
  const [description, setDescription] = useState(initialValues?.description || '')
  const [layer, setLayer] = useState<'staging' | 'intermediate' | 'marts'>(
    (initialValues?.model_layer as 'staging' | 'intermediate' | 'marts') || 'staging'
  )
  const [materialization, setMaterialization] = useState<Materialization>(
    (initialValues?.materialization as Materialization) || 'view'
  )
  const [sourceName, setSourceName] = useState(initialValues?.source_name || '')
  const [sourceTable, setSourceTable] = useState(initialValues?.source_table || '')
  const [refs, setRefs] = useState<string[]>(initialValues?.refs || [])
  const [refToAdd, setRefToAdd] = useState<string>('')
  // 'table' = read from a ClickHouse schema or Iceberg namespace,
  // 'ref'   = read from one or more upstream dbt models via ref().
  // Default: staging models usually come from raw sources, intermediate /
  // marts usually compose upstream refs.
  const [sourceMode, setSourceMode] = useState<'table' | 'ref'>(() => {
    if ((initialValues?.refs?.length ?? 0) > 0) return 'ref'
    if (initialValues?.source_table) return 'table'
    const initialLayer = (initialValues?.model_layer as string) || 'staging'
    return initialLayer === 'staging' ? 'table' : 'ref'
  })
  const [columns, setColumns] = useState<VisualColumnConfig[]>(
    (initialValues?.columns as VisualColumnConfig[]) || []
  )
  const [joins, setJoins] = useState<VisualJoinConfig[]>(
    (initialValues?.joins as VisualJoinConfig[]) || []
  )
  const [whereClause, setWhereClause] = useState(initialValues?.where_clause || '')
  const [groupBy, setGroupBy] = useState<string[]>(initialValues?.group_by || [])
  const [tags, setTags] = useState(initialValues?.tags?.join(', ') || '')
  const [referenceSql, setReferenceSql] = useState<string | null>(null)
  const [referenceSource, setReferenceSource] = useState<string | null>(null)
  // Whether the currently selected source is an Iceberg lake namespace or
  // a ClickHouse warehouse schema. Drives column resolution below.
  const [sourceKind, setSourceKind] = useState<'warehouse' | 'lake'>('warehouse')

  // Auto-fill source from Schema Explorer selection
  useEffect(() => {
    if (selectedSourceSchema) setSourceName(selectedSourceSchema)
  }, [selectedSourceSchema])
  useEffect(() => {
    if (selectedSourceTable) setSourceTable(selectedSourceTable)
  }, [selectedSourceTable])

  // Warehouse + Iceberg introspection for the source dropdowns
  const { data: warehouseSchemas = [] } = useWarehouseSchemas()
  const { data: warehouseTables = [] } = useWarehouseTables(
    sourceKind === 'warehouse' && sourceName ? sourceName : undefined,
  )
  const { data: lakeTables = [] } = useLakeTables()

  // Group ClickHouse schemas by their dbt layer so the dropdown shows
  // dedicated sections for Warehouse / Staging / Intermediate / Marts /
  // Other. Backend tags each schema with a ``layer`` field; legacy
  // responses without it fall back to "Other".
  const warehouseSchemaGroups = useMemo(() => {
    const order: Array<{
      key: 'warehouse' | 'staging' | 'intermediate' | 'marts' | 'raw'
      label: string
    }> = [
      { key: 'warehouse', label: 'Warehouse (raw)' },
      { key: 'staging', label: 'Staging (dbt)' },
      { key: 'intermediate', label: 'Intermediate (dbt)' },
      { key: 'marts', label: 'Marts (dbt)' },
      { key: 'raw', label: 'Other' },
    ]
    const buckets = new Map<string, typeof warehouseSchemas>()
    for (const s of warehouseSchemas) {
      const layer = (s as { layer?: string }).layer || 'raw'
      const arr = buckets.get(layer) || []
      arr.push(s)
      buckets.set(layer, arr)
    }
    return order
      .map((g) => ({ ...g, items: buckets.get(g.key) || [] }))
      .filter((g) => g.items.length > 0)
  }, [warehouseSchemas])

  // Group lake tables by namespace so they render under their namespace
  // header in the schema dropdown.
  const lakeNamespaces = useMemo(() => {
    const groups = new Map<string, typeof lakeTables>()
    for (const t of lakeTables) {
      const ns = t.namespace || 'default'
      if (!groups.has(ns)) groups.set(ns, [])
      groups.get(ns)!.push(t)
    }
    return Array.from(groups.entries()).map(([namespace, tables]) => ({
      namespace,
      tables,
    }))
  }, [lakeTables])

  // Tables to render in the table dropdown depend on the selected source kind.
  const tableOptions = useMemo(() => {
    if (!sourceName) return [] as Array<{ name: string; subtitle?: string }>
    if (sourceKind === 'lake') {
      return lakeTables
        .filter((t) => (t.namespace || 'default') === sourceName)
        .map((t) => ({
          name: t.table,
          subtitle: t.s3_uri || undefined,
        }))
    }
    return warehouseTables.map((t) => ({
      name: t.name,
      subtitle: t.engine,
    }))
  }, [sourceKind, sourceName, warehouseTables, lakeTables])

  // Columns available to the SELECT/WHERE/GROUP BY builders.
  // For Iceberg sources the Lake API returns columns inline on the table
  // descriptor, so we map them to the WarehouseColumn shape here. For
  // ClickHouse sources we fall back to the parent-supplied list (which is
  // populated via ``useWarehouseColumns``).
  const effectiveAvailableColumns = useMemo<WarehouseColumn[]>(() => {
    if (sourceKind === 'lake' && sourceName && sourceTable) {
      const t = lakeTables.find(
        (x) =>
          (x.namespace || 'default') === sourceName && x.table === sourceTable,
      )
      if (t && t.columns?.length) {
        return t.columns.map((c) => ({
          name: c.name,
          type: c.type || 'String',
          comment: c.description || '',
        }))
      }
      return []
    }
    return availableColumns
  }, [sourceKind, sourceName, sourceTable, lakeTables, availableColumns])

  // Encoded values for the schema dropdown: ``wh::<schema>`` or ``lake::<ns>``
  const schemaSelectValue =
    sourceName ? `${sourceKind === 'lake' ? 'lake' : 'wh'}::${sourceName}` : undefined

  const handleSchemaSelect = (encoded: string) => {
    const [kind, ...rest] = encoded.split('::')
    const name = rest.join('::')
    setSourceKind(kind === 'lake' ? 'lake' : 'warehouse')
    setSourceName(name)
    setSourceTable('')
    onSchemaChange?.(name)
  }

  const handleTableSelect = (value: string) => {
    setSourceTable(value)
    onTableChange?.(value)
  }

  // Loading a saved query pre-fills model metadata and keeps the raw
  // SQL as a read-only reference. The raw SQL is NOT injected into the
  // generated dbt model (ADR-002 — all code goes through approved
  // Jinja templates). Analysts transcribe the logic using the builder
  // below, or save the query as a singular test instead.
  const handleSavedQuery = useCallback((q: SavedQuery) => {
    setReferenceSql(q.sql)
    setReferenceSource(q.name)
    if (!modelName) {
      const safe = q.name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '')
      setModelName(safe)
    }
    if (!description && q.description) setDescription(q.description)
    if (!tags && q.tags.length > 0) setTags(q.tags.join(', '))
  }, [modelName, description, tags])

  const buildPayload = useCallback((): VisualModelCreatePayload => {
    const lakeMatch =
      sourceKind === 'lake'
        ? lakeTables.find(
            (t) => t.namespace === sourceName && t.table === sourceTable,
          )
        : undefined
    // Sanitize identifiers up-front so the user never sees a backend
    // VALIDATION_ERROR for casing/spaces. We also keep the user's
    // original alias when present so the rendered SQL reads naturally.
    const safeModelName = sanitizeIdentifier(modelName, 'model')
    const safeColumns = columns.map((c) => ({
      ...c,
      name: sanitizeIdentifier(c.name, 'column') || c.name,
    }))
    const safeGroupBy = groupBy
      .map((g) => sanitizeIdentifier(g, 'column'))
      .filter(Boolean)
    const useTable = sourceMode === 'table'
    const joinRefs = joins.map((j) => j.source_model)
    const allRefs = useTable
      ? Array.from(new Set(joinRefs))
      : Array.from(new Set([...refs, ...joinRefs]))
    return {
      model_name: safeModelName,
      model_layer: layer,
      description,
      materialization,
      source_kind: useTable && sourceKind === 'lake' ? 'iceberg' : 'warehouse',
      source_name: useTable && sourceName ? sourceName : undefined,
      source_table: useTable && sourceTable ? sourceTable : undefined,
      iceberg_s3_uri:
        useTable && sourceKind === 'lake'
          ? lakeMatch?.s3_uri ?? undefined
          : undefined,
      columns: safeColumns,
      joins,
      where_clause: whereClause || undefined,
      group_by: safeGroupBy,
      tags: tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean),
      refs: allRefs,
    }
  }, [
    modelName,
    layer,
    description,
    materialization,
    sourceKind,
    sourceMode,
    sourceName,
    sourceTable,
    lakeTables,
    columns,
    joins,
    whereClause,
    groupBy,
    tags,
    refs,
  ])

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center justify-between gap-2">
          <span className="flex items-center gap-2">
            <Code className="h-5 w-5" />
            Visual Query Builder
          </span>
          <SavedQueryPicker onSelect={handleSavedQuery} size="sm" />
        </CardTitle>
      </CardHeader>
      <CardContent>
        {referenceSql && (
          <div className="mb-4 rounded-md border border-dashed bg-muted/40 p-3">
            <div className="flex items-center justify-between mb-1">
              <Label className="text-[11px] font-medium">
                Reference SQL from{' '}
                <span className="font-mono">{referenceSource}</span>
              </Label>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="h-6 text-[11px]"
                onClick={() => {
                  setReferenceSql(null)
                  setReferenceSource(null)
                }}
              >
                Dismiss
              </Button>
            </div>
            <pre className="text-[11px] font-mono max-h-40 overflow-auto whitespace-pre-wrap text-muted-foreground">
              {referenceSql}
            </pre>
            <p className="text-[10px] text-muted-foreground mt-2">
              Raw SQL is shown for reference only. Recreate the logic using the
              builder below, or save as a singular test in the Tests tab
              (ADR-002: all generated dbt code must pass through approved
              templates).
            </p>
          </div>
        )}

        {/* Model Identity */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="space-y-1">
            <Label className="text-xs">Model Name</Label>
            <Input
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
              placeholder="stg_orders"
              className="font-mono text-sm"
            />
            {modelName && sanitizeIdentifier(modelName, 'model') !== modelName && (
              <p className="text-[10px] text-muted-foreground">
                Will be saved as{' '}
                <span className="font-mono text-foreground">
                  {sanitizeIdentifier(modelName, 'model') || '(invalid)'}
                </span>{' '}
                — dbt requires snake_case identifiers.
              </p>
            )}
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Layer</Label>
            <Select value={layer} onValueChange={(v) => setLayer(v as typeof layer)}>
              <SelectTrigger className="text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="staging">Staging (stg_)</SelectItem>
                <SelectItem value="intermediate">Intermediate (int_)</SelectItem>
                <SelectItem value="marts">Marts (dim_/fct_)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Materialization</Label>
            <Select value={materialization} onValueChange={(v) => setMaterialization(v as Materialization)}>
              <SelectTrigger className="text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="view">View</SelectItem>
                <SelectItem value="table">Table</SelectItem>
                <SelectItem value="incremental">Incremental</SelectItem>
                <SelectItem value="ephemeral">Ephemeral</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Tags</Label>
            <Input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="finance, daily"
              className="text-sm"
            />
          </div>
        </div>

        {/* Source — available for staging, intermediate and marts */}
        <div className="space-y-3 mb-4 rounded-md border bg-muted/20 p-3">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-medium">Source</Label>
            <div className="inline-flex rounded-md border bg-background p-0.5">
              <Button
                type="button"
                size="sm"
                variant={sourceMode === 'table' ? 'default' : 'ghost'}
                className="h-7 text-[11px]"
                onClick={() => setSourceMode('table')}
              >
                <Database className="h-3 w-3 mr-1" />
                Source table
              </Button>
              <Button
                type="button"
                size="sm"
                variant={sourceMode === 'ref' ? 'default' : 'ghost'}
                className="h-7 text-[11px]"
                onClick={() => setSourceMode('ref')}
              >
                <GitBranch className="h-3 w-3 mr-1" />
                Reference model
              </Button>
            </div>
          </div>
          <p className="text-[10px] text-muted-foreground">
            {sourceMode === 'table'
              ? 'Read raw data from a ClickHouse schema or Iceberg lake namespace via source().'
              : 'Compose one or more upstream dbt models via ref(). Recommended for intermediate and marts.'}
          </p>

          {sourceMode === 'table' ? (
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Source Schema</Label>
                <Select value={schemaSelectValue} onValueChange={handleSchemaSelect}>
                  <SelectTrigger className="text-sm font-mono">
                    <SelectValue placeholder="Select a source…" />
                  </SelectTrigger>
                  <SelectContent>
                    {warehouseSchemaGroups.map((group, idx) => (
                      <div key={`wh-group-${group.key}`}>
                        {idx > 0 && <SelectSeparator />}
                        <SelectGroup>
                          <SelectLabel className="flex items-center gap-1.5 text-[11px]">
                            <Database className="h-3 w-3" />
                            ClickHouse — {group.label}
                          </SelectLabel>
                          {group.items.map((s) => {
                            const exists = (s as { exists?: boolean }).exists
                            return (
                              <SelectItem
                                key={`wh::${s.name}`}
                                value={`wh::${s.name}`}
                                className="font-mono text-xs"
                              >
                                <div className="flex flex-col">
                                  <span>{s.name}</span>
                                  {exists === false && (
                                    <span className="text-[10px] text-muted-foreground">
                                      not materialized yet — run dbt first
                                    </span>
                                  )}
                                </div>
                              </SelectItem>
                            )
                          })}
                        </SelectGroup>
                      </div>
                    ))}
                    {warehouseSchemaGroups.length > 0 && lakeNamespaces.length > 0 && (
                      <SelectSeparator />
                    )}
                    {lakeNamespaces.length > 0 && (
                      <SelectGroup>
                        <SelectLabel className="flex items-center gap-1.5 text-[11px]">
                          <Layers className="h-3 w-3" />
                          Iceberg lake
                        </SelectLabel>
                        {lakeNamespaces.map((g) => (
                          <SelectItem
                            key={`lake::${g.namespace}`}
                            value={`lake::${g.namespace}`}
                            className="font-mono text-xs"
                          >
                            {g.namespace}{' '}
                            <span className="text-muted-foreground">
                              ({g.tables.length})
                            </span>
                          </SelectItem>
                        ))}
                      </SelectGroup>
                    )}
                    {warehouseSchemaGroups.length === 0 && lakeNamespaces.length === 0 && (
                      <div className="px-2 py-1.5 text-xs text-muted-foreground">
                        No sources available
                      </div>
                    )}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Source Table</Label>
                <Select
                  value={sourceTable || undefined}
                  onValueChange={handleTableSelect}
                  disabled={!sourceName}
                >
                  <SelectTrigger className="text-sm font-mono">
                    <SelectValue
                      placeholder={
                        sourceName ? 'Select a table…' : 'Pick a source first'
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {tableOptions.length === 0 ? (
                      <div className="px-2 py-1.5 text-xs text-muted-foreground">
                        {sourceName
                          ? sourceKind === 'lake'
                            ? 'No Iceberg tables in this namespace'
                            : 'No tables in this schema'
                          : 'Pick a source first'}
                      </div>
                    ) : (
                      tableOptions.map((t) => (
                        <SelectItem
                          key={t.name}
                          value={t.name}
                          className="font-mono text-xs"
                        >
                          <div className="flex flex-col">
                            <span>{t.name}</span>
                            {t.subtitle && (
                              <span className="text-[10px] text-muted-foreground truncate">
                                {t.subtitle}
                              </span>
                            )}
                          </div>
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-end gap-2">
                <div className="flex-1 space-y-1">
                  <Label className="text-xs">Reference Model</Label>
                  <Select
                    value={refToAdd || undefined}
                    onValueChange={(v) => setRefToAdd(v)}
                    disabled={availableModels.length === 0}
                  >
                    <SelectTrigger className="text-sm font-mono">
                      <SelectValue
                        placeholder={
                          availableModels.length === 0
                            ? 'No models available'
                            : 'Pick an upstream model…'
                        }
                      />
                    </SelectTrigger>
                    <SelectContent>
                      {availableModels
                        .filter((m) => !refs.includes(m))
                        .map((m) => (
                          <SelectItem
                            key={m}
                            value={m}
                            className="font-mono text-xs"
                          >
                            {m}
                          </SelectItem>
                        ))}
                      {availableModels.filter((m) => !refs.includes(m)).length ===
                        0 && (
                        <div className="px-2 py-1.5 text-xs text-muted-foreground">
                          No more models to add
                        </div>
                      )}
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-9"
                  disabled={!refToAdd || refs.includes(refToAdd)}
                  onClick={() => {
                    if (refToAdd && !refs.includes(refToAdd)) {
                      setRefs((prev) => [...prev, refToAdd])
                      setRefToAdd('')
                    }
                  }}
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  Add
                </Button>
              </div>
              {refs.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {refs.map((r) => (
                    <Badge
                      key={r}
                      variant="secondary"
                      className="font-mono text-[11px] gap-1"
                    >
                      ref('{r}')
                      <button
                        type="button"
                        onClick={() =>
                          setRefs((prev) => prev.filter((x) => x !== r))
                        }
                        className="hover:text-destructive"
                        aria-label={`Remove ${r}`}
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="space-y-1 mb-4">
          <Label className="text-xs">Description</Label>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What does this model do?"
            rows={2}
            className="text-sm"
          />
        </div>

        {/* SQL Builder Tabs */}
        <Tabs defaultValue="select" className="mt-2">
          <TabsList className="w-full">
            <TabsTrigger value="select" className="flex-1 text-xs">SELECT</TabsTrigger>
            <TabsTrigger value="joins" className="flex-1 text-xs">JOINS</TabsTrigger>
            <TabsTrigger value="where" className="flex-1 text-xs">WHERE</TabsTrigger>
            <TabsTrigger value="groupby" className="flex-1 text-xs">GROUP BY</TabsTrigger>
          </TabsList>

          <TabsContent value="select" className="mt-3">
            <SelectBuilder
              availableColumns={effectiveAvailableColumns}
              selectedColumns={columns}
              onChange={setColumns}
            />
          </TabsContent>

          <TabsContent value="joins" className="mt-3">
            <JoinBuilder
              availableModels={availableModels}
              joins={joins}
              onChange={setJoins}
            />
          </TabsContent>

          <TabsContent value="where" className="mt-3">
            <WhereBuilder
              value={whereClause}
              onChange={setWhereClause}
              columns={columns}
            />
          </TabsContent>

          <TabsContent value="groupby" className="mt-3">
            <GroupByBuilder
              columns={columns}
              selectedColumns={groupBy}
              onChange={setGroupBy}
            />
          </TabsContent>
        </Tabs>

        {/* Actions */}
        <div className="flex gap-2 mt-4 pt-4 border-t">
          <Button
            onClick={() => onSave(buildPayload())}
            disabled={!modelName || isSaving}
            className="flex-1"
          >
            <Save className="h-4 w-4 mr-2" />
            {isSaving ? 'Saving...' : 'Save Model'}
          </Button>
          <Button
            variant="outline"
            onClick={() => onPreview(buildPayload())}
            disabled={!modelName}
          >
            <Eye className="h-4 w-4 mr-2" />
            Preview
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
