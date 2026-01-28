/**
 * Target Configuration Component
 * 
 * Step 5 of the PySpark App Builder wizard.
 * Allows configuring target database, table, and app metadata.
 */

import { Database, FileCode, Settings } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import type { PySparkWizardState } from '@/types/pyspark'

interface TargetConfigurationProps {
  state: PySparkWizardState
  onStateChange: (updates: Partial<PySparkWizardState>) => void
}

// ClickHouse table engines
const TABLE_ENGINES = [
  { value: 'MergeTree', label: 'MergeTree', description: 'Default engine for analytics' },
  { value: 'ReplacingMergeTree', label: 'ReplacingMergeTree', description: 'Deduplicates by primary key' },
  { value: 'SummingMergeTree', label: 'SummingMergeTree', description: 'Pre-aggregates numeric columns' },
  { value: 'AggregatingMergeTree', label: 'AggregatingMergeTree', description: 'Stores aggregation states' },
  { value: 'CollapsingMergeTree', label: 'CollapsingMergeTree', description: 'Collapses row pairs' },
  { value: 'VersionedCollapsingMergeTree', label: 'VersionedCollapsingMergeTree', description: 'Versioned collapsing' },
]

export function TargetConfiguration({ state, onStateChange }: TargetConfigurationProps) {
  // Generate suggested table name from source
  const suggestTableName = () => {
    if (state.sourceTable) {
      return `stg_${state.sourceTable.toLowerCase().replace(/[^a-z0-9]/g, '_')}`
    }
    return ''
  }
  
  // Auto-suggest table name if empty
  const handleDatabaseChange = (database: string) => {
    const updates: Partial<PySparkWizardState> = { targetDatabase: database }
    
    if (!state.targetTable && state.sourceTable) {
      updates.targetTable = suggestTableName()
    }
    
    onStateChange(updates)
  }
  
  // Get recommended engine based on configuration
  const getRecommendedEngine = () => {
    if (state.scdType === 'type1') {
      return 'ReplacingMergeTree'
    }
    if (state.writeMode === 'merge') {
      return 'ReplacingMergeTree'
    }
    return 'MergeTree'
  }
  
  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-medium">Target & App Configuration</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Configure the target destination and name your PySpark app.
        </p>
      </div>
      
      {/* App Identity */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <FileCode className="h-5 w-5 text-primary" />
          <Label className="text-base font-medium">App Identity</Label>
        </div>
        
        <div className="grid grid-cols-1 gap-4">
          <div className="space-y-2">
            <Label htmlFor="app-name">App Name *</Label>
            <Input
              id="app-name"
              value={state.name}
              onChange={(e) => onStateChange({ name: e.target.value })}
              placeholder="e.g., extract_customers_to_warehouse"
            />
            <p className="text-xs text-muted-foreground">
              A unique name for this PySpark application
            </p>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="app-description">Description</Label>
            <Textarea
              id="app-description"
              value={state.description}
              onChange={(e) => onStateChange({ description: e.target.value })}
              placeholder="Describe what this app does..."
              className="min-h-[80px]"
            />
          </div>
        </div>
      </div>
      
      {/* Target Configuration */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-primary" />
          <Label className="text-base font-medium">Target Destination (ClickHouse)</Label>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="target-database">Database *</Label>
            <Input
              id="target-database"
              value={state.targetDatabase}
              onChange={(e) => handleDatabaseChange(e.target.value)}
              placeholder="e.g., analytics"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="target-table">Table *</Label>
            <Input
              id="target-table"
              value={state.targetTable}
              onChange={(e) => onStateChange({ targetTable: e.target.value })}
              placeholder={suggestTableName() || 'e.g., customers'}
            />
          </div>
        </div>
      </div>
      
      {/* Table Engine */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Settings className="h-5 w-5 text-primary" />
          <Label className="text-base font-medium">Table Engine</Label>
        </div>
        
        <Select
          value={state.targetEngine}
          onValueChange={(v) => onStateChange({ targetEngine: v })}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select table engine" />
          </SelectTrigger>
          <SelectContent>
            {TABLE_ENGINES.map((engine) => (
              <SelectItem key={engine.value} value={engine.value}>
                <div className="flex flex-col">
                  <span className="font-medium">
                    {engine.label}
                    {engine.value === getRecommendedEngine() && (
                      <span className="ml-2 text-xs text-primary">(Recommended)</span>
                    )}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {engine.description}
                  </span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        
        {state.targetEngine !== getRecommendedEngine() && (
          <Alert>
            <AlertDescription>
              Based on your configuration ({state.scdType === 'none' ? state.writeMode : `SCD ${state.scdType}`}), 
              we recommend using <strong>{getRecommendedEngine()}</strong> for optimal performance.
            </AlertDescription>
          </Alert>
        )}
      </div>
      
      {/* Configuration Summary */}
      <div className="bg-muted/50 rounded-lg p-4 space-y-2">
        <h4 className="font-medium text-sm">Configuration Summary</h4>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-muted-foreground">Source:</dt>
          <dd>
            {state.sourceType === 'table' 
              ? `${state.sourceSchema ? state.sourceSchema + '.' : ''}${state.sourceTable}`
              : 'Custom SQL Query'
            }
          </dd>
          
          <dt className="text-muted-foreground">Target:</dt>
          <dd>{state.targetDatabase}.{state.targetTable || '(not set)'}</dd>
          
          <dt className="text-muted-foreground">Columns:</dt>
          <dd>{state.selectedColumns.filter(c => c.include).length} selected</dd>
          
          <dt className="text-muted-foreground">Primary Keys:</dt>
          <dd>{state.primaryKeyColumns.length > 0 ? state.primaryKeyColumns.join(', ') : 'None'}</dd>
          
          <dt className="text-muted-foreground">SCD Type:</dt>
          <dd className="capitalize">{state.scdType === 'none' ? 'None' : state.scdType.toUpperCase()}</dd>
          
          <dt className="text-muted-foreground">Write Mode:</dt>
          <dd className="capitalize">{state.writeMode}</dd>
          
          {state.cdcType !== 'none' && (
            <>
              <dt className="text-muted-foreground">CDC:</dt>
              <dd>{state.cdcType} ({state.cdcColumn})</dd>
            </>
          )}
        </dl>
      </div>
    </div>
  )
}

export default TargetConfiguration
