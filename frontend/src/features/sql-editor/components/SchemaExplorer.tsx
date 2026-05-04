/**
 * Schema Explorer Component
 * Sidebar for exploring database schemas, tables, and columns
 * With schema selector, datatype display, and bulk actions
 */

import { useState, useMemo, useEffect } from 'react'
import {
  ChevronRight,
  ChevronDown,
  Database,
  Table2,
  Key,
  Link2,
  RefreshCw,
  Search,
  Loader2,
  FileText,
  Copy,
  Play,
  Hash,
  Type,
  Calendar,
  ToggleLeft,
  Binary,
  MoreHorizontal,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import type { SchemaInfo, TableSchema, ColumnInfo } from '../types'

interface SchemaExplorerProps {
  schemas: SchemaInfo[]
  isLoading?: boolean
  error?: string | null
  onRefresh?: () => void
  onColumnClick?: (tableName: string, columnName: string) => void
  /** Insert SELECT statement for table */
  onInsertSelect?: (sql: string) => void
  className?: string
}

// Get icon for column data type
function getTypeIcon(type: string) {
  const lowerType = type.toLowerCase()
  
  if (lowerType.includes('int') || lowerType.includes('numeric') || lowerType.includes('decimal') || lowerType.includes('float') || lowerType.includes('double')) {
    return Hash
  }
  if (lowerType.includes('char') || lowerType.includes('text') || lowerType.includes('string')) {
    return Type
  }
  if (lowerType.includes('date') || lowerType.includes('time') || lowerType.includes('timestamp')) {
    return Calendar
  }
  if (lowerType.includes('bool')) {
    return ToggleLeft
  }
  if (lowerType.includes('binary') || lowerType.includes('blob') || lowerType.includes('byte')) {
    return Binary
  }
  return FileText
}

// Get color class for column data type
function getTypeColor(type: string): string {
  const lowerType = type.toLowerCase()
  
  if (lowerType.includes('int') || lowerType.includes('numeric') || lowerType.includes('decimal') || lowerType.includes('float') || lowerType.includes('double')) {
    return 'text-blue-500'
  }
  if (lowerType.includes('char') || lowerType.includes('text') || lowerType.includes('string')) {
    return 'text-green-500'
  }
  if (lowerType.includes('date') || lowerType.includes('time') || lowerType.includes('timestamp')) {
    return 'text-orange-500'
  }
  if (lowerType.includes('bool')) {
    return 'text-purple-500'
  }
  if (lowerType.includes('binary') || lowerType.includes('blob') || lowerType.includes('byte')) {
    return 'text-gray-500'
  }
  return 'text-muted-foreground'
}

export function SchemaExplorer({
  schemas,
  isLoading = false,
  error,
  onRefresh,
  onColumnClick,
  onInsertSelect,
  className,
}: SchemaExplorerProps) {
  const [search, setSearch] = useState('')
  const [selectedSchemaName, setSelectedSchemaName] = useState<string>('__all__')
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set())

  // Get list of schema names for selector (exclude empty schemas)
  const schemaNames = useMemo(() => {
    return schemas
      .filter((s) => s.tables.length > 0)
      .map((s) => s.name)
  }, [schemas])

  // Filter schemas to only non-empty ones
  const nonEmptySchemas = useMemo(() => {
    return schemas.filter((s) => s.tables.length > 0)
  }, [schemas])

  // Auto-select first schema or 'public'/'default' if available
  useEffect(() => {
    if (nonEmptySchemas.length > 0 && selectedSchemaName === '__all__') {
      const hasPublic = nonEmptySchemas.some(s => s.name === 'public')
      const hasDefault = nonEmptySchemas.some(s => s.name === 'default')
      if (hasPublic) {
        setSelectedSchemaName('public')
      } else if (hasDefault) {
        setSelectedSchemaName('default')
      } else if (nonEmptySchemas.length === 1) {
        // Auto-select the only available schema
        setSelectedSchemaName(nonEmptySchemas[0].name)
      }
    }
  }, [nonEmptySchemas, selectedSchemaName])

  const toggleTable = (tableKey: string) => {
    setExpandedTables((prev) => {
      const next = new Set(prev)
      if (next.has(tableKey)) {
        next.delete(tableKey)
      } else {
        next.add(tableKey)
      }
      return next
    })
  }

  // Filter schemas and tables based on search and selected schema
  const filteredTables = useMemo(() => {
    let tables: Array<{ schema: string; table: TableSchema }> = []
    
    nonEmptySchemas.forEach((schema) => {
      if (selectedSchemaName !== '__all__' && schema.name !== selectedSchemaName) {
        return
      }
      
      schema.tables.forEach((table) => {
        const matchesSearch = 
          search === '' ||
          table.name.toLowerCase().includes(search.toLowerCase()) ||
          table.columns.some((col) =>
            col.name.toLowerCase().includes(search.toLowerCase())
          )
        
        if (matchesSearch) {
          tables.push({ schema: schema.name, table })
        }
      })
    })
    
    // Sort tables alphabetically
    tables.sort((a, b) => a.table.name.localeCompare(b.table.name))
    
    return tables
  }, [nonEmptySchemas, selectedSchemaName, search])

  // Handle bulk insert SELECT for all visible tables
  const handleInsertSelectAll = () => {
    if (!onInsertSelect) return
    
    const statements = filteredTables.map(({ schema, table }) => {
      const fullTableName = `${schema}.${table.name}`
      return `-- ${table.name}\nSELECT * FROM ${fullTableName} LIMIT 100;`
    }).join('\n\n')
    
    onInsertSelect(statements)
  }

  return (
    <TooltipProvider>
      <div className={cn('flex flex-col h-full bg-muted/30', className)}>
        {/* Header */}
        <div className="p-3 border-b space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-sm">Schema Explorer</h3>
            <div className="flex items-center gap-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-7 w-7"
                    onClick={onRefresh}
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <RefreshCw className="h-4 w-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Refresh schema</TooltipContent>
              </Tooltip>
              
              {/* Bulk actions menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button size="icon" variant="ghost" className="h-7 w-7">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem 
                    onClick={handleInsertSelectAll}
                    disabled={filteredTables.length === 0}
                  >
                    <Play className="h-4 w-4 mr-2" />
                    Insert SELECT for all tables
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => setExpandedTables(new Set(filteredTables.map(t => `${t.schema}.${t.table.name}`)))}
                  >
                    <ChevronDown className="h-4 w-4 mr-2" />
                    Expand all
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setExpandedTables(new Set())}>
                    <ChevronRight className="h-4 w-4 mr-2" />
                    Collapse all
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
          
          {/* Schema Selector */}
          <Select value={selectedSchemaName} onValueChange={setSelectedSchemaName}>
            <SelectTrigger className="h-8 text-xs">
              <Database className="h-3.5 w-3.5 mr-1.5 text-muted-foreground" />
              <SelectValue placeholder="Select schema" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">
                <span className="flex items-center gap-2">
                  <span>All Schemas</span>
                  <Badge variant="secondary" className="text-[10px] h-4">
                    {nonEmptySchemas.reduce((acc, s) => acc + s.tables.length, 0)}
                  </Badge>
                </span>
              </SelectItem>
              {schemaNames.map((name) => {
                const tableCount = nonEmptySchemas.find(s => s.name === name)?.tables.length || 0
                return (
                  <SelectItem key={name} value={name}>
                    <span className="flex items-center gap-2">
                      <span>{name}</span>
                      <Badge variant="secondary" className="text-[10px] h-4">
                        {tableCount}
                      </Badge>
                    </span>
                  </SelectItem>
                )
              })}
            </SelectContent>
          </Select>
          
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search tables & columns..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 h-8 text-xs"
            />
          </div>
        </div>

        {/* Tables List */}
        <ScrollArea className="flex-1" type="always">
          <div className="p-2">
            {error ? (
              <div className="text-center py-8 text-destructive text-sm">
                <p className="font-medium">Failed to load schema</p>
                <p className="text-xs mt-1 text-muted-foreground">{error}</p>
              </div>
            ) : isLoading && schemas.length === 0 ? (
              <div className="flex items-center justify-center py-8 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin mr-2" />
                Loading schema...
              </div>
            ) : filteredTables.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-sm">
                {search ? 'No matching tables found' : 'No tables available'}
              </div>
            ) : (
              <div className="space-y-0.5">
                {filteredTables.map(({ schema, table }) => {
                  const tableKey = `${schema}.${table.name}`
                  return (
                    <TableNode
                      key={tableKey}
                      table={table}
                      schemaName={schema}
                      isExpanded={expandedTables.has(tableKey)}
                      onToggle={() => toggleTable(tableKey)}
                      onColumnClick={onColumnClick}
                      onInsertSelect={onInsertSelect}
                    />
                  )
                })}
              </div>
            )}
          </div>
        </ScrollArea>
        
        {/* Footer with stats */}
        <div className="p-2 border-t text-xs text-muted-foreground flex items-center justify-between">
          <span>{filteredTables.length} tables</span>
          <span>
            {filteredTables.reduce((acc, t) => acc + t.table.columns.length, 0)} columns
          </span>
        </div>
      </div>
    </TooltipProvider>
  )
}

interface TableNodeProps {
  table: TableSchema
  schemaName: string
  isExpanded: boolean
  onToggle: () => void
  onColumnClick?: (tableName: string, columnName: string) => void
  onInsertSelect?: (sql: string) => void
}

function TableNode({
  table,
  schemaName,
  isExpanded,
  onToggle,
  onColumnClick,
  onInsertSelect,
}: TableNodeProps) {
  const fullTableName = `${schemaName}.${table.name}`

  const handleInsertSelect = (e: React.MouseEvent) => {
    e.stopPropagation()
    const sql = `SELECT * FROM ${fullTableName} LIMIT 100;`
    onInsertSelect?.(sql)
  }

  const handleCopyName = async (e: React.MouseEvent) => {
    e.stopPropagation()
    await navigator.clipboard.writeText(fullTableName)
  }

  return (
    <Collapsible open={isExpanded} onOpenChange={onToggle}>
      <div className="flex items-center group rounded hover:bg-accent/50">
        <CollapsibleTrigger className="flex items-center gap-1.5 flex-1 px-2 py-1.5 text-sm">
          {isExpanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
          )}
          <Table2 className="h-3.5 w-3.5 text-green-500 flex-shrink-0" />
          <span className="font-medium break-all min-w-0">{table.name}</span>
          {table.rowCount !== undefined && table.rowCount > 0 && (
            <span className="text-[10px] text-muted-foreground ml-1">
              ({table.rowCount.toLocaleString()} rows)
            </span>
          )}
          <Badge variant="secondary" className="text-[10px] h-4 ml-auto flex-shrink-0">
            {table.columns.length} cols
          </Badge>
        </CollapsibleTrigger>
        
        {/* Quick actions - always visible for all connections */}
        <div className="flex items-center gap-0.5 pr-2 flex-shrink-0">
          {/* Insert SELECT button - always visible regardless of connection type */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="icon"
                variant="ghost"
                className="h-6 w-6 text-blue-500 hover:text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/30"
                onClick={handleInsertSelect}
              >
                <Play className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="left">Insert SELECT * FROM {table.name}</TooltipContent>
          </Tooltip>
          
          {/* More actions dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                size="icon"
                variant="ghost"
                className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreHorizontal className="h-3.5 w-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
              <DropdownMenuItem onClick={handleInsertSelect}>
                <Play className="h-4 w-4 mr-2" />
                Insert SELECT *
              </DropdownMenuItem>
              {table.columns.length > 0 && (
                <DropdownMenuItem onClick={(e) => {
                  e.stopPropagation()
                  const cols = table.columns.map(c => c.name).join(',\n  ')
                  const sql = `SELECT\n  ${cols}\nFROM ${fullTableName}\nLIMIT 100;`
                  onInsertSelect?.(sql)
                }}>
                  <FileText className="h-4 w-4 mr-2" />
                  Insert SELECT with columns
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleCopyName}>
                <Copy className="h-4 w-4 mr-2" />
                Copy table name
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      
      <CollapsibleContent>
        <div className="ml-4 pl-2 border-l border-border/50 space-y-0.5">
          {table.columns.length === 0 ? (
            <div className="text-xs text-muted-foreground py-2 px-2 italic">
              No columns available
            </div>
          ) : (
            table.columns.map((column) => (
              <ColumnNode
                key={column.name}
                column={column}
                tableName={fullTableName}
                onClick={onColumnClick}
              />
            ))
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

interface ColumnNodeProps {
  column: ColumnInfo
  tableName: string
  onClick?: (tableName: string, columnName: string) => void
}

function ColumnNode({ column, tableName, onClick }: ColumnNodeProps) {
  const TypeIcon = getTypeIcon(column.type)
  const typeColor = getTypeColor(column.type)

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          className="flex items-center gap-1.5 w-full px-2 py-1 text-xs rounded hover:bg-accent/50 text-left group flex-wrap"
          onClick={() => onClick?.(tableName, column.name)}
        >
          {/* Key indicator */}
          {column.isPrimaryKey ? (
            <Key className="h-3 w-3 text-yellow-500 flex-shrink-0" />
          ) : column.isForeignKey ? (
            <Link2 className="h-3 w-3 text-purple-500 flex-shrink-0" />
          ) : (
            <TypeIcon className={cn("h-3 w-3 flex-shrink-0", typeColor)} />
          )}
          
          {/* Column name */}
          <span className="flex-1 min-w-0 font-mono break-all">{column.name}</span>
          
          {/* Data type badge */}
          <span className={cn(
            "text-[10px] px-1.5 py-0.5 rounded bg-muted whitespace-normal break-all",
            typeColor
          )}>
            {column.type}
          </span>
          
          {/* Nullable indicator */}
          {column.nullable && (
            <span className="text-[10px] text-muted-foreground">?</span>
          )}
        </button>
      </TooltipTrigger>
      <TooltipContent side="right" className="max-w-xs">
        <div className="space-y-1">
          <p className="font-mono font-medium">{column.name}</p>
          <div className="flex items-center gap-2 text-xs">
            <span className={typeColor}>{column.type}</span>
            {column.nullable && <span className="text-muted-foreground">• Nullable</span>}
          </div>
          {column.isPrimaryKey && (
            <p className="text-xs text-yellow-500 flex items-center gap-1">
              <Key className="h-3 w-3" /> Primary Key
            </p>
          )}
          {column.isForeignKey && (
            <p className="text-xs text-purple-500 flex items-center gap-1">
              <Link2 className="h-3 w-3" /> Foreign Key
            </p>
          )}
          {column.comment && (
            <p className="text-xs text-muted-foreground border-t pt-1 mt-1">
              {column.comment}
            </p>
          )}
          <p className="text-[10px] text-muted-foreground">Click to insert column name</p>
        </div>
      </TooltipContent>
    </Tooltip>
  )
}
