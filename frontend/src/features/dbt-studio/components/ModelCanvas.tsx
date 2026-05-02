/**
 * Model Canvas Component
 * 
 * Visual drag-and-drop interface for building dbt models using ReactFlow.
 * Supports source, staging, intermediate, and mart node types.
 */

import { useCallback, useState, useMemo, memo } from 'react'
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  MiniMap,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  NodeProps,
  BackgroundVariant,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { useToast } from '@/components/ui/use-toast'
import {
  Database,
  Table2,
  Layers,
  BarChart2,
  TestTube,
  Plus,
  Trash2,
  Save,
  Code2,
  GripVertical,
  Settings2,
} from 'lucide-react'
import type {
  VisualModelDefinition,
  VisualColumnDefinition,
  VisualTestDefinition,
  CanvasNodeData,
  ModelLayer,
  Materialization,
} from '../types'
import { NODE_TYPE_COLORS } from '@/lib/colors'
import {
  useWarehouseSchemas,
  useWarehouseTables,
  useWarehouseColumns,
} from '../hooks/useWarehouseSchema'

// ============================================================================
// Node Type Definitions
// ============================================================================

interface ModelNodeData extends CanvasNodeData {
  definition?: VisualModelDefinition
  onSelect?: (nodeId: string) => void
}

const layerConfig: Record<ModelLayer, { color: string; icon: typeof Database; label: string }> = {
  source: { color: NODE_TYPE_COLORS.source, icon: Database, label: 'Source' },
  staging: { color: NODE_TYPE_COLORS.staging, icon: Table2, label: 'Staging' },
  intermediate: { color: NODE_TYPE_COLORS.intermediate, icon: Layers, label: 'Intermediate' },
  marts: { color: NODE_TYPE_COLORS.marts, icon: BarChart2, label: 'Marts' },
}

// Custom node component for model nodes
const ModelNode = memo(({ data, selected, id }: NodeProps<ModelNodeData>) => {
  const config = layerConfig[data.layer || 'staging']
  const Icon = config.icon

  return (
    <div
      className={`
        relative min-w-[180px] rounded-lg border-2 shadow-md transition-all
        ${selected ? 'ring-2 ring-offset-2 ring-blue-500' : ''}
      `}
      style={{
        borderColor: config.color,
        backgroundColor: `${config.color}10`,
      }}
      onClick={() => data.onSelect?.(id)}
    >
      {/* Input handle */}
      {data.layer !== 'source' && (
        <Handle
          type="target"
          position={Position.Left}
          className="!w-3 !h-3 !bg-gray-400 hover:!bg-blue-500 transition-colors"
        />
      )}

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !bg-gray-400 hover:!bg-blue-500 transition-colors"
      />

      {/* Node content */}
      <div className="p-3">
        {/* Header */}
        <div className="flex items-center gap-2 mb-2">
          <div
            className="p-1.5 rounded"
            style={{ backgroundColor: config.color }}
          >
            <Icon className="h-4 w-4 text-white" />
          </div>
          <div className="flex-1">
            <div className="font-medium text-sm text-gray-900 dark:text-gray-100 truncate">
              {data.label}
            </div>
            <div className="text-xs text-gray-500">{config.label}</div>
          </div>
        </div>

        {/* Stats */}
        {data.definition && (
          <div className="flex gap-2 text-xs text-gray-500">
            <span>{data.definition.columns?.length || 0} cols</span>
            {(data.definition.tests?.length || 0) > 0 && (
              <Badge variant="outline" className="text-xs px-1 py-0">
                <TestTube className="h-3 w-3 mr-1" />
                {data.definition.tests?.length}
              </Badge>
            )}
          </div>
        )}

        {/* Materialization badge */}
        {data.definition?.materialization && (
          <Badge
            variant="secondary"
            className="mt-2 text-xs"
          >
            {data.definition.materialization}
          </Badge>
        )}
      </div>
    </div>
  )
})
ModelNode.displayName = 'ModelNode'

// Node types mapping
const nodeTypes = {
  model: ModelNode,
}

// ============================================================================
// Model Palette Component
// ============================================================================

interface ModelPaletteProps {
  onDragStart: (event: React.DragEvent, layer: ModelLayer) => void
}

function ModelPalette({ onDragStart }: ModelPaletteProps) {
  const paletteItems: { layer: ModelLayer; description: string }[] = [
    { layer: 'source', description: 'External data sources' },
    { layer: 'staging', description: 'Cleaned raw data' },
    { layer: 'intermediate', description: 'Business logic' },
    { layer: 'marts', description: 'Analytics ready' },
  ]

  return (
    <Card className="w-64 shrink-0">
      <CardHeader className="py-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <GripVertical className="h-4 w-4" />
          Model Types
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {paletteItems.map(({ layer, description }) => {
          const config = layerConfig[layer]
          const Icon = config.icon

          return (
            <div
              key={layer}
              draggable
              onDragStart={(e) => onDragStart(e, layer)}
              className={`
                flex items-center gap-3 p-3 rounded-lg border-2 cursor-grab
                hover:shadow-md transition-all active:cursor-grabbing
              `}
              style={{
                borderColor: config.color,
                backgroundColor: `${config.color}10`,
              }}
            >
              <div
                className="p-2 rounded"
                style={{ backgroundColor: config.color }}
              >
                <Icon className="h-4 w-4 text-white" />
              </div>
              <div>
                <div className="font-medium text-sm">{config.label}</div>
                <div className="text-xs text-gray-500">{description}</div>
              </div>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}

// ============================================================================
// Model Properties Panel
// ============================================================================

interface ModelPropertiesPanelProps {
  node: Node<ModelNodeData> | null
  definition: VisualModelDefinition | null
  onUpdate: (definition: VisualModelDefinition) => void
  onDelete: () => void
  onClose: () => void
}

// ----------------------------------------------------------------------------
// Warehouse Binding Section
// ----------------------------------------------------------------------------
// Binds a source/staging model to a ClickHouse schema.table, then offers to
// bulk-populate the column list from the live warehouse introspection
// endpoint. This replaces free-text column typing with verified column names
// and types — a major UX improvement for analysts.
// ----------------------------------------------------------------------------

interface WarehouseBindingSectionProps {
  definition: VisualModelDefinition
  onChange: (definition: VisualModelDefinition) => void
}

function WarehouseBindingSection({
  definition,
  onChange,
}: WarehouseBindingSectionProps) {
  const { toast } = useToast()
  const firstSource = definition.sources?.[0]
  const schema = firstSource?.schema_name
  const table = firstSource?.table_name

  const { data: schemasData, isLoading: schemasLoading } = useWarehouseSchemas()
  const { data: tablesData, isLoading: tablesLoading } = useWarehouseTables(schema)
  const { data: columnsData } = useWarehouseColumns(schema, table)

  const schemas = (schemasData ?? []) as { name: string }[]
  const tables = (tablesData ?? []) as { name: string; engine?: string }[]
  const warehouseColumns = (columnsData ?? []) as {
    name: string
    type: string
    comment?: string
  }[]

  const setSource = (next: { schema_name?: string; table_name?: string }) => {
    const prev = definition.sources?.[0] ?? { schema_name: '', table_name: '' }
    const merged = {
      schema_name: next.schema_name ?? prev.schema_name ?? '',
      table_name: next.table_name ?? prev.table_name ?? '',
      alias: prev.alias,
    }
    const sources = [merged, ...(definition.sources?.slice(1) ?? [])]
    onChange({ ...definition, sources })
  }

  const handleSchemaChange = (value: string) => {
    setSource({ schema_name: value, table_name: '' })
  }

  const handleTableChange = (value: string) => {
    setSource({ table_name: value })
  }

  const populateColumns = (mode: 'replace' | 'append') => {
    if (warehouseColumns.length === 0) {
      toast({ title: 'No columns available', description: 'Select a schema and table first.' })
      return
    }

    const existing = definition.columns ?? []
    const existingByName = new Map(existing.map((c) => [c.name, c]))

    const incoming: VisualColumnDefinition[] = warehouseColumns.map((c) => ({
      name: c.name,
      source_column: c.name,
      data_type: c.type,
      expression: c.name,
      description: c.comment || undefined,
    }))

    let next: VisualColumnDefinition[]
    if (mode === 'replace') {
      next = incoming
    } else {
      const additions = incoming.filter((c) => !existingByName.has(c.name))
      next = [...existing, ...additions]
    }

    onChange({ ...definition, columns: next })
    toast({
      title: mode === 'replace' ? 'Columns replaced' : 'Columns appended',
      description: `${mode === 'replace' ? next.length : next.length - existing.length} column(s) from ${schema}.${table}`,
    })
  }

  return (
    <div className="space-y-3 rounded-md border bg-muted/30 p-3">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-sm flex items-center gap-2">
          <Database className="h-4 w-4" />
          Warehouse Source Binding
        </h4>
        {schema && table && (
          <span className="text-[11px] font-mono text-muted-foreground">
            {schema}.{table}
          </span>
        )}
      </div>
      <p className="text-[11px] text-muted-foreground">
        Bind this model to a ClickHouse table. Columns and data types can then
        be populated automatically from the live warehouse schema.
      </p>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label className="text-xs">Schema</Label>
          <Select
            value={schema ?? ''}
            onValueChange={handleSchemaChange}
            disabled={schemasLoading}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder={schemasLoading ? 'Loading…' : 'Select schema'} />
            </SelectTrigger>
            <SelectContent>
              {schemas.map((s) => (
                <SelectItem key={s.name} value={s.name} className="text-xs font-mono">
                  {s.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Table</Label>
          <Select
            value={table ?? ''}
            onValueChange={handleTableChange}
            disabled={!schema || tablesLoading}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue
                placeholder={
                  !schema
                    ? 'Select schema first'
                    : tablesLoading
                      ? 'Loading…'
                      : 'Select table'
                }
              />
            </SelectTrigger>
            <SelectContent>
              {tables.map((t) => (
                <SelectItem key={t.name} value={t.name} className="text-xs font-mono">
                  {t.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          disabled={!schema || !table || warehouseColumns.length === 0}
          onClick={() => populateColumns('append')}
        >
          <Plus className="h-3.5 w-3.5 mr-1" />
          Append Columns ({warehouseColumns.length})
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 text-xs"
          disabled={!schema || !table || warehouseColumns.length === 0}
          onClick={() => populateColumns('replace')}
        >
          Replace All
        </Button>
      </div>
    </div>
  )
}
function ModelPropertiesPanel({
  node,
  definition,
  onUpdate,
  onDelete,
  onClose,
}: ModelPropertiesPanelProps) {
  if (!node || !definition) return null

  const handleChange = <K extends keyof VisualModelDefinition>(
    key: K,
    value: VisualModelDefinition[K]
  ) => {
    onUpdate({ ...definition, [key]: value })
  }

  const addColumn = () => {
    const newColumn: VisualColumnDefinition = {
      name: `column_${(definition.columns?.length || 0) + 1}`,
      expression: '',
      data_type: 'String',
    }
    handleChange('columns', [...(definition.columns || []), newColumn])
  }

  const updateColumn = (index: number, updates: Partial<VisualColumnDefinition>) => {
    const columns = [...(definition.columns || [])]
    columns[index] = { ...columns[index], ...updates }
    handleChange('columns', columns)
  }

  const removeColumn = (index: number) => {
    const columns = [...(definition.columns || [])]
    columns.splice(index, 1)
    handleChange('columns', columns)
  }

  const addTest = () => {
    const newTest: VisualTestDefinition = {
      type: 'not_null',
      column: definition.columns?.[0]?.name || '',
    }
    handleChange('tests', [...(definition.tests || []), newTest])
  }

  const updateTest = (index: number, updates: Partial<VisualTestDefinition>) => {
    const tests = [...(definition.tests || [])]
    tests[index] = { ...tests[index], ...updates }
    handleChange('tests', tests)
  }

  const removeTest = (index: number) => {
    const tests = [...(definition.tests || [])]
    tests.splice(index, 1)
    handleChange('tests', tests)
  }

  return (
    <Sheet open={!!node} onOpenChange={(open: boolean) => !open && onClose()}>
      <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Model Properties
          </SheetTitle>
          <SheetDescription>Configure model settings, columns, and tests.</SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          {/* Basic Info */}
          <div className="space-y-4">
            <h4 className="font-medium text-sm">Basic Information</h4>

            <div className="space-y-2">
              <Label htmlFor="model-name">Model Name</Label>
              <Input
                id="model-name"
                value={definition.name}
                onChange={(e) => handleChange('name', e.target.value)}
                placeholder="stg_customers"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={definition.description || ''}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="Describe what this model does..."
                rows={2}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Layer</Label>
                <Select
                  value={definition.layer}
                  onValueChange={(value) => handleChange('layer', value as ModelLayer)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="source">Source</SelectItem>
                    <SelectItem value="staging">Staging</SelectItem>
                    <SelectItem value="intermediate">Intermediate</SelectItem>
                    <SelectItem value="marts">Marts</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Materialization</Label>
                <Select
                  value={definition.materialization}
                  onValueChange={(value) =>
                    handleChange('materialization', value as Materialization)
                  }
                >
                  <SelectTrigger>
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
            </div>
          </div>

          {/* Warehouse binding (available on all layers) */}
          <WarehouseBindingSection
            definition={definition}
            onChange={onUpdate}
          />

          {/* Columns */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-medium text-sm">Columns</h4>
              <Button variant="outline" size="sm" onClick={addColumn}>
                <Plus className="h-4 w-4 mr-1" />
                Add Column
              </Button>
            </div>

            {(definition.columns || []).map((column, index) => (
              <Card key={index} className="p-3">
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Input
                      placeholder="Column name"
                      value={column.name}
                      onChange={(e) => updateColumn(index, { name: e.target.value })}
                      className="flex-1"
                    />
                    <Select
                      value={column.data_type || 'String'}
                      onValueChange={(value) => updateColumn(index, { data_type: value })}
                    >
                      <SelectTrigger className="w-28">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="String">String</SelectItem>
                        <SelectItem value="Int64">Int64</SelectItem>
                        <SelectItem value="Float64">Float64</SelectItem>
                        <SelectItem value="DateTime">DateTime</SelectItem>
                        <SelectItem value="Date">Date</SelectItem>
                        <SelectItem value="Bool">Bool</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => removeColumn(index)}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                  <Input
                    placeholder="SQL expression (e.g., LOWER(name))"
                    value={column.expression}
                    onChange={(e) => updateColumn(index, { expression: e.target.value })}
                  />
                  <Input
                    placeholder="Description (optional)"
                    value={column.description || ''}
                    onChange={(e) => updateColumn(index, { description: e.target.value })}
                  />
                </div>
              </Card>
            ))}
          </div>

          {/* Tests */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-medium text-sm">Tests</h4>
              <Button variant="outline" size="sm" onClick={addTest}>
                <TestTube className="h-4 w-4 mr-1" />
                Add Test
              </Button>
            </div>

            {(definition.tests || []).map((test: VisualTestDefinition, index: number) => (
              <Card key={index} className="p-3">
                <div className="flex items-center gap-2">
                  <Select
                    value={test.type}
                    onValueChange={(value) => updateTest(index, { type: value })}
                  >
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="not_null">Not Null</SelectItem>
                      <SelectItem value="unique">Unique</SelectItem>
                      <SelectItem value="accepted_values">Accepted Values</SelectItem>
                      <SelectItem value="relationships">Relationships</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select
                    value={test.column}
                    onValueChange={(value) => updateTest(index, { column: value })}
                  >
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Select column" />
                    </SelectTrigger>
                    <SelectContent>
                      {(definition.columns || []).map((col) => (
                        <SelectItem key={col.name} value={col.name}>
                          {col.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeTest(index)}
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
                {test.type === 'accepted_values' && (
                  <Input
                    className="mt-2"
                    placeholder="Comma-separated values"
                    value={(test.config?.values as string[] | undefined)?.join(', ') || ''}
                    onChange={(e) =>
                      updateTest(index, {
                        config: {
                          ...test.config,
                          values: e.target.value.split(',').map((v) => v.trim()),
                        },
                      })
                    }
                  />
                )}
              </Card>
            ))}
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-4 border-t">
            <Button variant="destructive" onClick={onDelete} className="flex-1">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete Model
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}

// ============================================================================
// Main ModelCanvas Component
// ============================================================================

export interface ModelCanvasProps {
  initialNodes?: Node<ModelNodeData>[]
  initialEdges?: Edge[]
  onSave?: (nodes: Node<ModelNodeData>[], edges: Edge[], definitions: Map<string, VisualModelDefinition>) => void
  onValidate?: (definitions: Map<string, VisualModelDefinition>) => void
  onGenerateCode?: (nodeId: string) => void
  readOnly?: boolean
}

export function ModelCanvas({
  initialNodes = [],
  initialEdges = [],
  onSave,
  onValidate,
  onGenerateCode,
  readOnly = false,
}: ModelCanvasProps) {
  const { toast } = useToast()
  
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [definitions, setDefinitions] = useState<Map<string, VisualModelDefinition>>(() => {
    const map = new Map<string, VisualModelDefinition>()
    initialNodes.forEach((n) => {
      if (n.data.definition) {
        map.set(n.id, n.data.definition)
      }
    })
    return map
  })

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) || null,
    [nodes, selectedNodeId]
  )

  const selectedDefinition = useMemo(
    () => (selectedNodeId ? definitions.get(selectedNodeId) || null : null),
    [selectedNodeId, definitions]
  )

  // Update node data with onSelect callback
  const nodesWithCallbacks = useMemo(
    () =>
      nodes.map((node) => ({
        ...node,
        data: {
          ...node.data,
          onSelect: setSelectedNodeId,
          definition: definitions.get(node.id),
        },
      })),
    [nodes, definitions]
  )

  // Handle edge connections
  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            type: 'smoothstep',
            animated: true,
            style: { stroke: NODE_TYPE_COLORS.edge, strokeWidth: 2 },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: NODE_TYPE_COLORS.edge,
            },
          },
          eds
        )
      )
    },
    [setEdges]
  )

  // Handle drag start from palette
  const onDragStart = (event: React.DragEvent, layer: ModelLayer) => {
    event.dataTransfer.setData('application/dbt-layer', layer)
    event.dataTransfer.effectAllowed = 'move'
  }

  // Handle drop on canvas
  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault()

      const layer = event.dataTransfer.getData('application/dbt-layer') as ModelLayer
      if (!layer) return

      const reactFlowBounds = event.currentTarget.getBoundingClientRect()
      const position = {
        x: event.clientX - reactFlowBounds.left - 90,
        y: event.clientY - reactFlowBounds.top - 40,
      }

      const newId = `${layer}_${Date.now()}`
      const defaultName = `${layer}_model_${nodes.filter((n) => n.data.layer === layer).length + 1}`

      const newDefinition: VisualModelDefinition = {
        name: defaultName,
        layer,
        materialization: layer === 'source' ? 'view' : layer === 'marts' ? 'table' : 'view',
        columns: [],
        tests: [],
        dependencies: [],
      }

      const newNode: Node<ModelNodeData> = {
        id: newId,
        type: 'model',
        position,
        data: {
          label: defaultName,
          layer,
          definition: newDefinition,
        },
      }

      setNodes((nds) => [...nds, newNode])
      setDefinitions((defs) => {
        const updated = new Map(defs)
        updated.set(newId, newDefinition)
        return updated
      })

      toast({
        title: 'Model Added',
        description: `Created new ${layer} model`,
      })
    },
    [nodes, setNodes, toast]
  )

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  // Update model definition
  const handleUpdateDefinition = useCallback(
    (definition: VisualModelDefinition) => {
      if (!selectedNodeId) return

      setDefinitions((defs) => {
        const updated = new Map(defs)
        updated.set(selectedNodeId, definition)
        return updated
      })

      // Update node label
      setNodes((nds) =>
        nds.map((n) =>
          n.id === selectedNodeId
            ? {
                ...n,
                data: {
                  ...n.data,
                  label: definition.name,
                  layer: definition.layer,
                  definition,
                },
              }
            : n
        )
      )
    },
    [selectedNodeId, setNodes]
  )

  // Delete selected model
  const handleDeleteModel = useCallback(() => {
    if (!selectedNodeId) return

    setNodes((nds) => nds.filter((n) => n.id !== selectedNodeId))
    setEdges((eds) =>
      eds.filter((e) => e.source !== selectedNodeId && e.target !== selectedNodeId)
    )
    setDefinitions((defs) => {
      const updated = new Map(defs)
      updated.delete(selectedNodeId)
      return updated
    })
    setSelectedNodeId(null)

    toast({
      title: 'Model Deleted',
      description: 'Model has been removed from the canvas',
    })
  }, [selectedNodeId, setNodes, setEdges, toast])

  // Save all models
  const handleSave = useCallback(() => {
    // Update dependencies based on edges
    const updatedDefinitions = new Map(definitions)
    for (const [nodeId, def] of updatedDefinitions) {
      const incomingEdges = edges.filter((e) => e.target === nodeId)
      const dependencies = incomingEdges.map((e) => {
        const sourceNode = nodes.find((n) => n.id === e.source)
        return sourceNode?.data.definition?.name || e.source
      })
      updatedDefinitions.set(nodeId, { ...def, dependencies })
    }

    onSave?.(nodes, edges, updatedDefinitions)
  }, [nodes, edges, definitions, onSave])

  // Validate all models
  const handleValidate = useCallback(() => {
    onValidate?.(definitions)
  }, [definitions, onValidate])

  return (
    <div className="flex h-full gap-4">
      {/* Palette */}
      {!readOnly && <ModelPalette onDragStart={onDragStart} />}

      {/* Canvas */}
      <Card className="flex-1 overflow-hidden">
        <CardHeader className="py-2 px-4 border-b flex flex-row items-center justify-between">
          <CardTitle className="text-sm">Model Canvas</CardTitle>
          <div className="flex gap-2">
            {onValidate && (
              <Button variant="outline" size="sm" onClick={handleValidate}>
                <TestTube className="h-4 w-4 mr-1" />
                Validate
              </Button>
            )}
            {onGenerateCode && selectedNodeId && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onGenerateCode(selectedNodeId)}
              >
                <Code2 className="h-4 w-4 mr-1" />
                Generate SQL
              </Button>
            )}
            {onSave && (
              <Button size="sm" onClick={handleSave}>
                <Save className="h-4 w-4 mr-1" />
                Save All
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="p-0 h-[calc(100%-53px)]">
          <ReactFlow
            nodes={nodesWithCallbacks}
            edges={edges}
            onNodesChange={readOnly ? undefined : onNodesChange}
            onEdgesChange={readOnly ? undefined : onEdgesChange}
            onConnect={readOnly ? undefined : onConnect}
            onDrop={readOnly ? undefined : onDrop}
            onDragOver={readOnly ? undefined : onDragOver}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
            <Controls />
            <MiniMap
              nodeColor={(node) => layerConfig[node.data?.layer as ModelLayer]?.color || '#gray'}
              maskColor="rgba(0,0,0,0.1)"
            />
          </ReactFlow>
        </CardContent>
      </Card>

      {/* Properties Panel */}
      <ModelPropertiesPanel
        node={selectedNode}
        definition={selectedDefinition}
        onUpdate={handleUpdateDefinition}
        onDelete={handleDeleteModel}
        onClose={() => setSelectedNodeId(null)}
      />
    </div>
  )
}

export default ModelCanvas
