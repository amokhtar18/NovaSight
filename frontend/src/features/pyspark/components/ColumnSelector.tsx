/**
 * Column Selector Component
 * 
 * Step 2 of the PySpark App Builder wizard.
 * Allows selecting which columns to include in the extraction.
 */

import { useState } from 'react'
import { Search, Columns, Check, X } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { PySparkWizardState } from '@/types/pyspark'

interface ColumnSelectorProps {
  state: PySparkWizardState
  onStateChange: (updates: Partial<PySparkWizardState>) => void
}

export function ColumnSelector({ state, onStateChange }: ColumnSelectorProps) {
  const [searchTerm, setSearchTerm] = useState('')
  
  const filteredColumns = state.availableColumns.filter(col =>
    col.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    col.data_type.toLowerCase().includes(searchTerm.toLowerCase())
  )
  
  const selectedCount = state.selectedColumns.filter(c => c.include).length
  const totalCount = state.availableColumns.length
  
  // Toggle column selection
  const toggleColumn = (columnName: string) => {
    const updatedColumns = state.selectedColumns.map(col =>
      col.name === columnName
        ? { ...col, include: !col.include }
        : col
    )
    onStateChange({ selectedColumns: updatedColumns })
  }
  
  // Select all columns
  const selectAll = () => {
    const updatedColumns = state.selectedColumns.map(col => ({
      ...col,
      include: true,
    }))
    onStateChange({ selectedColumns: updatedColumns })
  }
  
  // Deselect all columns
  const deselectAll = () => {
    const updatedColumns = state.selectedColumns.map(col => ({
      ...col,
      include: false,
    }))
    onStateChange({ selectedColumns: updatedColumns })
  }
  
  // Check if column is selected
  const isSelected = (columnName: string) => {
    return state.selectedColumns.find(c => c.name === columnName)?.include ?? false
  }
  
  // Get data type badge color
  const getTypeBadgeVariant = (dataType: string): "default" | "secondary" | "outline" => {
    const type = dataType.toLowerCase()
    if (type.includes('int') || type.includes('numeric') || type.includes('decimal') || type.includes('float')) {
      return 'default'
    }
    if (type.includes('char') || type.includes('text') || type.includes('string')) {
      return 'secondary'
    }
    return 'outline'
  }
  
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">Select Columns</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Choose which columns to include in the extraction.
          {selectedCount > 0 && (
            <span className="ml-2 font-medium">
              {selectedCount} of {totalCount} selected
            </span>
          )}
        </p>
      </div>
      
      {/* Search and Actions */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search columns..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-9"
          />
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={selectAll}
          >
            <Check className="h-4 w-4 mr-1" />
            Select All
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={deselectAll}
          >
            <X className="h-4 w-4 mr-1" />
            Deselect All
          </Button>
        </div>
      </div>
      
      {/* Column List */}
      <ScrollArea className="h-[400px] border rounded-lg">
        <div className="p-4 space-y-2">
          {filteredColumns.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              <Columns className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No columns found</p>
            </div>
          ) : (
            filteredColumns.map((column) => (
              <div
                key={column.name}
                className={cn(
                  "flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors",
                  isSelected(column.name)
                    ? "bg-primary/5 border-primary/30"
                    : "hover:bg-muted/50"
                )}
                onClick={() => toggleColumn(column.name)}
              >
                <div className="flex items-center gap-3">
                  <Checkbox
                    checked={isSelected(column.name)}
                    onCheckedChange={() => toggleColumn(column.name)}
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{column.name}</span>
                      {!column.nullable && (
                        <Badge variant="destructive" className="text-xs">
                          NOT NULL
                        </Badge>
                      )}
                    </div>
                    {column.comment && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {column.comment}
                      </p>
                    )}
                  </div>
                </div>
                
                <Badge variant={getTypeBadgeVariant(column.data_type)}>
                  {column.data_type}
                </Badge>
              </div>
            ))
          )}
        </div>
      </ScrollArea>
      
      {/* Selection Summary */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {selectedCount === 0 && (
            <span className="text-destructive">Select at least one column</span>
          )}
          {selectedCount > 0 && selectedCount < totalCount && (
            <span>{totalCount - selectedCount} columns excluded</span>
          )}
          {selectedCount === totalCount && (
            <span className="text-green-600">All columns selected</span>
          )}
        </span>
        
        <span>
          Showing {filteredColumns.length} of {totalCount} columns
        </span>
      </div>
    </div>
  )
}

export default ColumnSelector
