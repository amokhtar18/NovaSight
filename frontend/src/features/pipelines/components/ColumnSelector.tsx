/**
 * Pipeline Wizard - Step 2: Column Configuration
 */

import { useState } from 'react'
import { Search, Check, X, Key, Clock } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import type { WizardState, ColumnConfig } from '@/types/pipeline'

interface ColumnSelectorProps {
  state: WizardState
  onStateChange: (updates: Partial<WizardState>) => void
}

export function ColumnSelector({ state, onStateChange }: ColumnSelectorProps) {
  const [searchTerm, setSearchTerm] = useState('')

  const columns = state.columnsConfig || []
  const filteredColumns = columns.filter(col =>
    col.name.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const selectedCount = columns.filter(col => col.include).length

  // Toggle single column
  const toggleColumn = (columnName: string, include: boolean) => {
    const updated = columns.map(col =>
      col.name === columnName ? { ...col, include } : col
    )
    onStateChange({ columnsConfig: updated })
  }

  // Select all columns
  const selectAll = () => {
    const updated = columns.map(col => ({ ...col, include: true }))
    onStateChange({ columnsConfig: updated })
  }

  // Deselect all columns
  const deselectAll = () => {
    const updated = columns.map(col => ({ ...col, include: false }))
    onStateChange({ columnsConfig: updated })
  }

  // Toggle primary key
  const togglePrimaryKey = (columnName: string) => {
    const currentPKs = state.primaryKeyColumns || []
    const isPK = currentPKs.includes(columnName)
    
    const updated = isPK
      ? currentPKs.filter(pk => pk !== columnName)
      : [...currentPKs, columnName]
    
    onStateChange({ primaryKeyColumns: updated })
  }

  // Set incremental cursor
  const setIncrementalCursor = (columnName: string) => {
    const current = state.incrementalCursorColumn
    onStateChange({
      incrementalCursorColumn: current === columnName ? undefined : columnName,
    })
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">Select Columns</h3>
        <p className="text-sm text-muted-foreground">
          Choose which columns to include in the pipeline. You can also mark primary keys
          and select an incremental cursor column.
        </p>
      </div>

      {/* Records preview (file-source pipelines) */}
      {state.sourceKind === 'file' && (() => {
        const rows = (state.fileOptions?.rows_preview as Array<Record<string, unknown>> | undefined) ?? []
        const previewCols = (state.fileOptions?.columns_preview as string[] | undefined) ?? []
        if (!rows.length || !previewCols.length) {
          return (
            <div className="rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
              No records preview is available for this file. Columns are inferred from the
              file header. Rows will be visible after the first run.
            </div>
          )
        }
        const renderCell = (v: unknown): string => {
          if (v === null || v === undefined) return ''
          if (typeof v === 'object') {
            try {
              return JSON.stringify(v)
            } catch {
              return String(v)
            }
          }
          return String(v)
        }
        return (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm font-medium">Records preview</Label>
              <Badge variant="outline">First {rows.length} rows</Badge>
            </div>
            <ScrollArea className="border rounded-md max-h-[260px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    {previewCols.map((c) => (
                      <TableHead key={c} className="font-mono text-xs whitespace-nowrap">
                        {c}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((row, idx) => (
                    <TableRow key={idx}>
                      {previewCols.map((c) => (
                        <TableCell key={c} className="font-mono text-xs whitespace-nowrap max-w-[240px] truncate">
                          {renderCell(row[c])}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </div>
        )
      })()}

      {/* Search and bulk actions */}
      <div className="flex items-center justify-between">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search columns..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-8"
          />
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline">
            {selectedCount} / {columns.length} selected
          </Badge>
          <Button variant="outline" size="sm" onClick={selectAll}>
            Select All
          </Button>
          <Button variant="outline" size="sm" onClick={deselectAll}>
            Deselect All
          </Button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        <div className="flex items-center gap-1">
          <Key className="h-3 w-3 text-amber-500" />
          <span>Primary Key</span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3 text-blue-500" />
          <span>Incremental Cursor</span>
        </div>
      </div>

      {/* Columns table */}
      <ScrollArea className="h-[400px] border rounded-md">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]">Include</TableHead>
              <TableHead>Column Name</TableHead>
              <TableHead>Data Type</TableHead>
              <TableHead className="w-[100px]">Primary Key</TableHead>
              <TableHead className="w-[100px]">Incremental</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredColumns.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  {columns.length === 0
                    ? 'No columns available. Select a source table first.'
                    : 'No columns match your search.'}
                </TableCell>
              </TableRow>
            ) : (
              filteredColumns.map((col) => {
                const isPK = (state.primaryKeyColumns || []).includes(col.name)
                const isCursor = state.incrementalCursorColumn === col.name
                
                return (
                  <TableRow key={col.name}>
                    <TableCell>
                      <Checkbox
                        checked={col.include}
                        onCheckedChange={(checked) =>
                          toggleColumn(col.name, checked as boolean)
                        }
                      />
                    </TableCell>
                    <TableCell className="font-mono text-sm">
                      {col.name}
                      {!col.nullable && (
                        <Badge variant="outline" className="ml-2 text-xs">
                          NOT NULL
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {col.data_type}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant={isPK ? 'default' : 'ghost'}
                        size="sm"
                        className={isPK ? 'bg-amber-500 hover:bg-amber-600' : ''}
                        onClick={() => togglePrimaryKey(col.name)}
                        disabled={!col.include}
                      >
                        <Key className="h-3 w-3" />
                      </Button>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant={isCursor ? 'default' : 'ghost'}
                        size="sm"
                        className={isCursor ? 'bg-blue-500 hover:bg-blue-600' : ''}
                        onClick={() => setIncrementalCursor(col.name)}
                        disabled={!col.include}
                      >
                        <Clock className="h-3 w-3" />
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </ScrollArea>

      {/* Validation messages */}
      {state.primaryKeyColumns && state.primaryKeyColumns.length > 0 && (
        <div className="flex items-center gap-2 text-sm">
          <Key className="h-4 w-4 text-amber-500" />
          <span>Primary key: {state.primaryKeyColumns.join(', ')}</span>
        </div>
      )}
      {state.incrementalCursorColumn && (
        <div className="flex items-center gap-2 text-sm">
          <Clock className="h-4 w-4 text-blue-500" />
          <span>Incremental cursor: {state.incrementalCursorColumn}</span>
        </div>
      )}
    </div>
  )
}
