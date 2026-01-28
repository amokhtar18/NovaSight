/**
 * SCD Configuration Component
 * 
 * Step 4 of the PySpark App Builder wizard.
 * Allows configuring SCD type and write mode.
 */

import { RefreshCw, Database, AlertTriangle } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { PySparkWizardState, SCDType, WriteMode } from '@/types/pyspark'

interface SCDConfigurationProps {
  state: PySparkWizardState
  onStateChange: (updates: Partial<PySparkWizardState>) => void
}

export function SCDConfiguration({ state, onStateChange }: SCDConfigurationProps) {
  const hasPrimaryKeys = state.primaryKeyColumns.length > 0
  
  // Handle SCD type change
  const handleSCDTypeChange = (scdType: SCDType) => {
    // Auto-adjust write mode based on SCD type
    let writeMode = state.writeMode
    if (scdType === 'type2') {
      writeMode = 'append'  // SCD2 always appends new versions
    } else if (scdType === 'type1' && writeMode === 'append') {
      writeMode = 'merge'  // SCD1 typically uses merge
    }
    
    onStateChange({ scdType, writeMode })
  }
  
  // Handle write mode change
  const handleWriteModeChange = (writeMode: WriteMode) => {
    onStateChange({ writeMode })
  }
  
  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-medium">SCD & Write Mode</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Configure how changes are tracked and how data is written to the target.
        </p>
      </div>
      
      {/* SCD Type Selection */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <RefreshCw className="h-5 w-5 text-primary" />
          <Label className="text-base font-medium">Slowly Changing Dimension (SCD) Type</Label>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card
            className={cn(
              "cursor-pointer transition-colors",
              state.scdType === 'none' && "border-primary bg-primary/5"
            )}
            onClick={() => handleSCDTypeChange('none')}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <RadioGroupItem
                  value="none"
                  checked={state.scdType === 'none'}
                  className="pointer-events-none"
                />
                No SCD
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Simple extraction without change tracking.
                Data is loaded as-is based on write mode.
              </CardDescription>
            </CardContent>
          </Card>
          
          <Card
            className={cn(
              "cursor-pointer transition-colors",
              state.scdType === 'type1' && "border-primary bg-primary/5",
              !hasPrimaryKeys && "opacity-50"
            )}
            onClick={() => hasPrimaryKeys && handleSCDTypeChange('type1')}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <RadioGroupItem
                  value="type1"
                  checked={state.scdType === 'type1'}
                  disabled={!hasPrimaryKeys}
                  className="pointer-events-none"
                />
                SCD Type 1
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                <strong>Overwrite</strong> existing records.
                No history - only current values are kept.
              </CardDescription>
              {!hasPrimaryKeys && (
                <p className="text-xs text-destructive mt-2">
                  Requires primary key
                </p>
              )}
            </CardContent>
          </Card>
          
          <Card
            className={cn(
              "cursor-pointer transition-colors",
              state.scdType === 'type2' && "border-primary bg-primary/5",
              !hasPrimaryKeys && "opacity-50"
            )}
            onClick={() => hasPrimaryKeys && handleSCDTypeChange('type2')}
          >
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center gap-2">
                <RadioGroupItem
                  value="type2"
                  checked={state.scdType === 'type2'}
                  disabled={!hasPrimaryKeys}
                  className="pointer-events-none"
                />
                SCD Type 2
              </CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                <strong>Historical tracking</strong> with versioning.
                Old records are expired, new versions added.
              </CardDescription>
              {!hasPrimaryKeys && (
                <p className="text-xs text-destructive mt-2">
                  Requires primary key
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
      
      {/* Write Mode Selection */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-primary" />
          <Label className="text-base font-medium">Write Mode</Label>
        </div>
        
        <RadioGroup
          value={state.writeMode}
          onValueChange={(v: string) => handleWriteModeChange(v as WriteMode)}
          className="space-y-3"
          disabled={state.scdType === 'type2'}
        >
          <div className={cn(
            "flex items-center space-x-3 p-4 border rounded-lg",
            state.writeMode === 'append' && "border-primary bg-primary/5"
          )}>
            <RadioGroupItem value="append" id="write-append" />
            <div className="flex-1">
              <Label htmlFor="write-append" className="cursor-pointer font-medium">
                Append
              </Label>
              <p className="text-sm text-muted-foreground">
                Add new records without modifying existing data.
                Best for event logs, time-series, and SCD Type 2.
              </p>
            </div>
          </div>
          
          <div className={cn(
            "flex items-center space-x-3 p-4 border rounded-lg",
            state.writeMode === 'overwrite' && "border-primary bg-primary/5",
            state.scdType === 'type2' && "opacity-50"
          )}>
            <RadioGroupItem 
              value="overwrite" 
              id="write-overwrite"
              disabled={state.scdType === 'type2'}
            />
            <div className="flex-1">
              <Label htmlFor="write-overwrite" className="cursor-pointer font-medium">
                Overwrite
              </Label>
              <p className="text-sm text-muted-foreground">
                Replace all existing data with new data.
                Use for full snapshot refreshes.
              </p>
            </div>
          </div>
          
          <div className={cn(
            "flex items-center space-x-3 p-4 border rounded-lg",
            state.writeMode === 'merge' && "border-primary bg-primary/5",
            (!hasPrimaryKeys || state.scdType === 'type2') && "opacity-50"
          )}>
            <RadioGroupItem 
              value="merge" 
              id="write-merge"
              disabled={!hasPrimaryKeys || state.scdType === 'type2'}
            />
            <div className="flex-1">
              <Label htmlFor="write-merge" className="cursor-pointer font-medium">
                Merge (Upsert)
              </Label>
              <p className="text-sm text-muted-foreground">
                Insert new records, update existing based on primary key.
                Best for maintaining current state.
              </p>
              {!hasPrimaryKeys && (
                <p className="text-xs text-destructive mt-1">
                  Requires primary key
                </p>
              )}
            </div>
          </div>
        </RadioGroup>
      </div>
      
      {/* Configuration Summary */}
      {state.scdType !== 'none' && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {state.scdType === 'type1' && (
              <>
                <strong>SCD Type 1:</strong> Records matching on{' '}
                <strong>{state.primaryKeyColumns.join(', ')}</strong> will be updated in place.
                No history will be preserved.
              </>
            )}
            {state.scdType === 'type2' && (
              <>
                <strong>SCD Type 2:</strong> Changes will create new versions.
                Additional columns will be added: <code>_scd_valid_from</code>,{' '}
                <code>_scd_valid_to</code>, <code>_scd_is_current</code>, <code>_scd_version</code>.
              </>
            )}
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}

export default SCDConfiguration
