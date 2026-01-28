/**
 * Key Configuration Component
 * 
 * Step 3 of the PySpark App Builder wizard.
 * Allows defining primary keys, CDC column, and partition columns.
 */

import { Key, Clock, Layers } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import type { PySparkWizardState, CDCType } from '@/types/pyspark'

interface KeyConfigurationProps {
  state: PySparkWizardState
  onStateChange: (updates: Partial<PySparkWizardState>) => void
}

export function KeyConfiguration({ state, onStateChange }: KeyConfigurationProps) {
  const selectedColumns = state.selectedColumns.filter(c => c.include)
  
  // Toggle primary key
  const togglePrimaryKey = (columnName: string) => {
    const currentPks = state.primaryKeyColumns
    const newPks = currentPks.includes(columnName)
      ? currentPks.filter(pk => pk !== columnName)
      : [...currentPks, columnName]
    onStateChange({ primaryKeyColumns: newPks })
  }
  
  // Toggle partition column
  const togglePartition = (columnName: string) => {
    const current = state.partitionColumns
    const updated = current.includes(columnName)
      ? current.filter(p => p !== columnName)
      : [...current, columnName]
    onStateChange({ partitionColumns: updated })
  }
  
  // Handle CDC type change
  const handleCDCTypeChange = (cdcType: CDCType) => {
    onStateChange({
      cdcType,
      cdcColumn: cdcType === 'none' ? '' : state.cdcColumn,
    })
  }
  
  // Get timestamp-like columns for CDC
  const timestampColumns = selectedColumns.filter(col => {
    const type = col.data_type.toLowerCase()
    return type.includes('timestamp') || type.includes('datetime') || type.includes('date')
  })
  
  // Get numeric columns for version-based CDC
  const numericColumns = selectedColumns.filter(col => {
    const type = col.data_type.toLowerCase()
    return type.includes('int') || type.includes('numeric') || type.includes('serial')
  })
  
  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-medium">Key & Tracking Configuration</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Define primary keys for record identification and change tracking settings.
        </p>
      </div>
      
      {/* Primary Key Selection */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Key className="h-5 w-5 text-primary" />
          <Label className="text-base font-medium">Primary Key Columns</Label>
        </div>
        <p className="text-sm text-muted-foreground">
          Select columns that uniquely identify each record. Required for SCD and merge operations.
        </p>
        
        <ScrollArea className="h-[200px] border rounded-lg">
          <div className="p-4 space-y-2">
            {selectedColumns.map((column) => (
              <div
                key={column.name}
                className={cn(
                  "flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors",
                  state.primaryKeyColumns.includes(column.name)
                    ? "bg-primary/10 border-primary"
                    : "hover:bg-muted/50"
                )}
                onClick={() => togglePrimaryKey(column.name)}
              >
                <div className="flex items-center gap-3">
                  <Checkbox
                    checked={state.primaryKeyColumns.includes(column.name)}
                    onCheckedChange={() => togglePrimaryKey(column.name)}
                  />
                  <span className="font-medium">{column.name}</span>
                </div>
                <Badge variant="outline">{column.data_type}</Badge>
              </div>
            ))}
          </div>
        </ScrollArea>
        
        {state.primaryKeyColumns.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Selected:</span>
            {state.primaryKeyColumns.map(pk => (
              <Badge key={pk} variant="secondary">{pk}</Badge>
            ))}
          </div>
        )}
      </div>
      
      {/* CDC Configuration */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Clock className="h-5 w-5 text-primary" />
          <Label className="text-base font-medium">Change Data Capture (CDC)</Label>
        </div>
        <p className="text-sm text-muted-foreground">
          Configure how to track changes for incremental loads.
        </p>
        
        <RadioGroup
          value={state.cdcType}
          onValueChange={(v: string) => handleCDCTypeChange(v as CDCType)}
          className="space-y-3"
        >
          <div className="flex items-center space-x-3 p-3 border rounded-lg">
            <RadioGroupItem value="none" id="cdc-none" />
            <div>
              <Label htmlFor="cdc-none" className="cursor-pointer font-medium">
                No CDC
              </Label>
              <p className="text-xs text-muted-foreground">
                Full load every time
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3 p-3 border rounded-lg">
            <RadioGroupItem value="timestamp" id="cdc-timestamp" />
            <div className="flex-1">
              <Label htmlFor="cdc-timestamp" className="cursor-pointer font-medium">
                Timestamp-based
              </Label>
              <p className="text-xs text-muted-foreground">
                Use a timestamp column to track changes
              </p>
            </div>
            {state.cdcType === 'timestamp' && (
              <Select
                value={state.cdcColumn}
                onValueChange={(v) => onStateChange({ cdcColumn: v })}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select column" />
                </SelectTrigger>
                <SelectContent>
                  {timestampColumns.map(col => (
                    <SelectItem key={col.name} value={col.name}>
                      {col.name}
                    </SelectItem>
                  ))}
                  {timestampColumns.length === 0 && (
                    <SelectItem value="" disabled>
                      No timestamp columns found
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
            )}
          </div>
          
          <div className="flex items-center space-x-3 p-3 border rounded-lg">
            <RadioGroupItem value="version" id="cdc-version" />
            <div className="flex-1">
              <Label htmlFor="cdc-version" className="cursor-pointer font-medium">
                Version-based
              </Label>
              <p className="text-xs text-muted-foreground">
                Use a version/sequence column
              </p>
            </div>
            {state.cdcType === 'version' && (
              <Select
                value={state.cdcColumn}
                onValueChange={(v) => onStateChange({ cdcColumn: v })}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select column" />
                </SelectTrigger>
                <SelectContent>
                  {numericColumns.map(col => (
                    <SelectItem key={col.name} value={col.name}>
                      {col.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
          
          <div className="flex items-center space-x-3 p-3 border rounded-lg">
            <RadioGroupItem value="hash" id="cdc-hash" />
            <div>
              <Label htmlFor="cdc-hash" className="cursor-pointer font-medium">
                Hash-based
              </Label>
              <p className="text-xs text-muted-foreground">
                Compare row hashes to detect changes
              </p>
            </div>
          </div>
        </RadioGroup>
      </div>
      
      {/* Partition Configuration */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-primary" />
          <Label className="text-base font-medium">Partition Columns</Label>
          <Badge variant="outline">Optional</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          Select columns to partition data for better query performance.
        </p>
        
        <div className="flex flex-wrap gap-2">
          {selectedColumns.map((column) => (
            <Badge
              key={column.name}
              variant={state.partitionColumns.includes(column.name) ? "default" : "outline"}
              className="cursor-pointer"
              onClick={() => togglePartition(column.name)}
            >
              {column.name}
            </Badge>
          ))}
        </div>
        
        {state.partitionColumns.length > 0 && (
          <Alert>
            <AlertDescription>
              Data will be partitioned by: {state.partitionColumns.join(' → ')}
            </AlertDescription>
          </Alert>
        )}
      </div>
    </div>
  )
}

export default KeyConfiguration
