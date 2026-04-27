/**
 * SchemaExplorer — tree-style warehouse schema browser.
 *
 * Two source kinds are surfaced:
 *
 *  1. **Warehouse**: schemas / tables / columns introspected from the
 *     tenant's ClickHouse database.
 *  2. **Iceberg (Lake)**: Iceberg tables on the tenant's S3 bucket,
 *     produced by dlt ingestion pipelines. Selecting an Iceberg table in
 *     dbt Studio renders the model with a ClickHouse ``iceberg('s3://...')``
 *     table function reference. Materialization always lands in the
 *     tenant's ClickHouse database (single materialization target).
 */

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import {
  ChevronRight,
  ChevronDown,
  Database,
  Table2,
  Columns3,
  Search,
  RefreshCw,
  Layers,
} from 'lucide-react'
import {
  useWarehouseSchemas,
  useWarehouseTables,
  useWarehouseColumns,
  useLakeTables,
} from '../../hooks/useWarehouseSchema'
import type { LakeTable } from '../../services/visualModelApi'

export interface SchemaExplorerProps {
  /** Called when a ClickHouse table is selected. */
  onTableSelect?: (schema: string, table: string) => void
  /** Called when a column is clicked. */
  onColumnClick?: (schema: string, table: string, column: string) => void
  /**
   * Called when an Iceberg lake table is selected. Receives the full
   * lake-table descriptor so callers can capture ``s3_uri``,
   * ``namespace``, etc. Falls back to ``onTableSelect(namespace, table)``
   * when not provided.
   */
  onLakeTableSelect?: (table: LakeTable) => void
  maxHeight?: string
}

export function SchemaExplorer({
  onTableSelect,
  onColumnClick,
  onLakeTableSelect,
  maxHeight = '450px',
}: SchemaExplorerProps) {
  const [search, setSearch] = useState('')
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set())
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set())

  const {
    data: schemas = [],
    isLoading: schemasLoading,
    refetch: refetchSchemas,
  } = useWarehouseSchemas()
  const {
    data: lakeTables = [],
    isLoading: lakeLoading,
    refetch: refetchLake,
  } = useLakeTables()

  const toggleSchema = (schema: string) => {
    setExpandedSchemas((prev) => {
      const next = new Set(prev)
      if (next.has(schema)) next.delete(schema)
      else next.add(schema)
      return next
    })
  }

  const toggleTable = (key: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const filteredSchemas = search
    ? schemas.filter((s) => s.name.toLowerCase().includes(search.toLowerCase()))
    : schemas

  const filteredLake = search
    ? lakeTables.filter(
        (t) =>
          t.table.toLowerCase().includes(search.toLowerCase()) ||
          t.namespace.toLowerCase().includes(search.toLowerCase()) ||
          t.pipeline_name.toLowerCase().includes(search.toLowerCase())
      )
    : lakeTables

  const handleLakeSelect = (table: LakeTable) => {
    if (onLakeTableSelect) {
      onLakeTableSelect(table)
    } else if (onTableSelect) {
      onTableSelect(table.namespace, table.table)
    }
  }

  return (
    <Tabs defaultValue="warehouse" className="space-y-2">
      <div className="flex items-center gap-1">
        <TabsList className="h-7">
          <TabsTrigger value="warehouse" className="text-xs h-6 px-2 gap-1">
            <Database className="h-3 w-3" />
            Warehouse
          </TabsTrigger>
          <TabsTrigger value="lake" className="text-xs h-6 px-2 gap-1">
            <Layers className="h-3 w-3" />
            Iceberg
            {lakeTables.length > 0 && (
              <Badge variant="secondary" className="text-[9px] ml-1 px-1 h-4">
                {lakeTables.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search..."
            className="pl-7 h-7 text-xs"
          />
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => {
            refetchSchemas()
            refetchLake()
          }}
          disabled={schemasLoading || lakeLoading}
        >
          <RefreshCw
            className={`h-3 w-3 ${
              schemasLoading || lakeLoading ? 'animate-spin' : ''
            }`}
          />
        </Button>
      </div>

      <TabsContent value="warehouse" className="m-0">
        <ScrollArea style={{ maxHeight }}>
          <div className="pr-2">
            {schemasLoading ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                Loading schemas...
              </p>
            ) : filteredSchemas.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No schemas found.
              </p>
            ) : (
              filteredSchemas.map((schema) => (
                <SchemaNode
                  key={schema.name}
                  schema={schema.name}
                  isExpanded={expandedSchemas.has(schema.name)}
                  onToggle={() => toggleSchema(schema.name)}
                  expandedTables={expandedTables}
                  onToggleTable={toggleTable}
                  onTableSelect={onTableSelect}
                  onColumnClick={onColumnClick}
                  search={search}
                />
              ))
            )}
          </div>
        </ScrollArea>
      </TabsContent>

      <TabsContent value="lake" className="m-0">
        <ScrollArea style={{ maxHeight }}>
          <div className="pr-2 space-y-0.5">
            {lakeLoading ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                Loading Iceberg tables...
              </p>
            ) : filteredLake.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No Iceberg tables yet. Run a dlt pipeline to populate the
                lake.
              </p>
            ) : (
              filteredLake.map((tbl) => (
                <LakeTableRow
                  key={tbl.pipeline_id}
                  table={tbl}
                  onSelect={() => handleLakeSelect(tbl)}
                />
              ))
            )}
          </div>
        </ScrollArea>
      </TabsContent>
    </Tabs>
  )
}

// ─── Schema Node ─────────────────────────────────────────────────────────────

interface SchemaNodeProps {
  schema: string
  isExpanded: boolean
  onToggle: () => void
  expandedTables: Set<string>
  onToggleTable: (key: string) => void
  onTableSelect?: (schema: string, table: string) => void
  onColumnClick?: (schema: string, table: string, column: string) => void
  search: string
}

function SchemaNode({
  schema,
  isExpanded,
  onToggle,
  expandedTables,
  onToggleTable,
  onTableSelect,
  onColumnClick,
  search,
}: SchemaNodeProps) {
  const { data: tables = [] } = useWarehouseTables(isExpanded ? schema : '')

  const filteredTables = search
    ? tables.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()))
    : tables

  return (
    <div>
      <button
        onClick={onToggle}
        className="flex items-center gap-1.5 w-full px-1 py-1 rounded hover:bg-accent text-sm"
      >
        {isExpanded ? (
          <ChevronDown className="h-3 w-3 shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0" />
        )}
        <Database className="h-3.5 w-3.5 text-blue-500 shrink-0" />
        <span className="font-mono truncate">{schema}</span>
        {isExpanded && (
          <Badge variant="secondary" className="text-[10px] ml-auto">
            {filteredTables.length}
          </Badge>
        )}
      </button>

      {isExpanded && (
        <div className="ml-4">
          {filteredTables.map((table) => {
            const key = `${schema}.${table.name}`
            return (
              <TableNode
                key={key}
                schema={schema}
                table={table.name}
                isExpanded={expandedTables.has(key)}
                onToggle={() => onToggleTable(key)}
                onSelect={() => onTableSelect?.(schema, table.name)}
                onColumnClick={onColumnClick}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Table Node ──────────────────────────────────────────────────────────────

interface TableNodeProps {
  schema: string
  table: string
  isExpanded: boolean
  onToggle: () => void
  onSelect?: () => void
  onColumnClick?: (schema: string, table: string, column: string) => void
}

function TableNode({
  schema,
  table,
  isExpanded,
  onToggle,
  onSelect,
  onColumnClick,
}: TableNodeProps) {
  const { data: columns = [] } = useWarehouseColumns(
    isExpanded ? schema : '',
    isExpanded ? table : ''
  )

  return (
    <div>
      <button
        onClick={onToggle}
        onDoubleClick={onSelect}
        className="flex items-center gap-1.5 w-full px-1 py-0.5 rounded hover:bg-accent text-xs"
      >
        {isExpanded ? (
          <ChevronDown className="h-3 w-3 shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0" />
        )}
        <Table2 className="h-3 w-3 text-green-500 shrink-0" />
        <span className="font-mono truncate">{table}</span>
      </button>

      {isExpanded && (
        <div className="ml-5">
          {columns.map((col) => (
            <button
              key={col.name}
              className="flex items-center gap-1.5 w-full px-1 py-0.5 rounded hover:bg-accent text-xs"
              onClick={() => onColumnClick?.(schema, table, col.name)}
            >
              <Columns3 className="h-3 w-3 text-slate-400 shrink-0" />
              <span className="font-mono truncate flex-1 text-left">{col.name}</span>
              <Badge variant="outline" className="text-[9px] font-mono shrink-0">
                {col.type}
              </Badge>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Lake Table Row ──────────────────────────────────────────────────────────

interface LakeTableRowProps {
  table: LakeTable
  onSelect: () => void
}

function LakeTableRow({ table, onSelect }: LakeTableRowProps) {
  const [expanded, setExpanded] = useState(false)
  const cols = table.columns || []
  return (
    <div className="border-b border-border/50 last:border-0">
      <button
        onClick={() => setExpanded((v) => !v)}
        onDoubleClick={onSelect}
        className="flex items-start gap-1.5 w-full px-1 py-1 rounded hover:bg-accent text-xs text-left"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 shrink-0 mt-0.5" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0 mt-0.5" />
        )}
        <Layers className="h-3.5 w-3.5 text-amber-500 shrink-0 mt-0.5" />
        <div className="flex-1 min-w-0">
          <div className="font-mono truncate">{table.table}</div>
          <div className="text-[10px] text-muted-foreground truncate">
            {table.namespace} · {table.pipeline_name}
          </div>
        </div>
        <Badge
          variant={table.last_run_status === 'success' ? 'default' : 'outline'}
          className="text-[9px] shrink-0"
        >
          {table.last_run_status || table.status}
        </Badge>
      </button>

      {expanded && (
        <div className="ml-5 pb-1 space-y-0.5">
          {table.s3_uri && (
            <div className="px-1 text-[10px] font-mono text-muted-foreground break-all">
              {table.s3_uri}
            </div>
          )}
          {cols.length === 0 ? (
            <div className="px-1 text-[10px] text-muted-foreground italic">
              No column metadata.
            </div>
          ) : (
            cols.map((col) => (
              <div
                key={col.name}
                className="flex items-center gap-1.5 w-full px-1 py-0.5 text-xs"
              >
                <Columns3 className="h-3 w-3 text-slate-400 shrink-0" />
                <span className="font-mono truncate flex-1">{col.name}</span>
                {col.type && (
                  <Badge variant="outline" className="text-[9px] font-mono shrink-0">
                    {col.type}
                  </Badge>
                )}
              </div>
            ))
          )}
          <div className="px-1 pt-1">
            <Button
              variant="secondary"
              size="sm"
              className="h-6 text-[10px] w-full"
              onClick={onSelect}
            >
              Use as model source
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
