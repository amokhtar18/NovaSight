/**
 * Source Selector Component
 * 
 * Step 1 of the PySpark App Builder wizard.
 * Allows selecting a connection and specifying source table or query.
 */

import { useState } from 'react'
import { Database, Table, Code, Loader2, CheckCircle } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useDataSources, useDataSourceSchema } from '@/features/datasources/hooks'
import { useValidateQuery } from '../hooks'
import type { SourceType, PySparkWizardState, ColumnConfig } from '@/types/pyspark'
import type { DataSource, TableInfo } from '@/types/datasource'

interface SourceSelectorProps {
  state: PySparkWizardState
  onStateChange: (updates: Partial<PySparkWizardState>) => void
}

export function SourceSelector({ state, onStateChange }: SourceSelectorProps) {
  const [selectedSchema, setSelectedSchema] = useState(state.sourceSchema || '')
  
  // Fetch available connections
  const { data: connectionsData, isLoading: loadingConnections } = useDataSources()
  
  // Fetch schema when connection is selected
  const { data: schemaData, isLoading: loadingSchema } = useDataSourceSchema(
    state.connectionId,
    { include_columns: true }
  )
  
  // Query validation mutation
  const validateQuery = useValidateQuery()
  
  // Get available schemas from data
  const schemas = schemaData?.schemas || []
  const selectedSchemaData = schemas.find(s => s.name === selectedSchema)
  const tables = selectedSchemaData?.tables || []
  
  // Handle connection change
  const handleConnectionChange = (connectionId: string) => {
    onStateChange({
      connectionId,
      sourceSchema: '',
      sourceTable: '',
      sourceQuery: '',
      availableColumns: [],
      selectedColumns: [],
    })
    setSelectedSchema('')
  }
  
  // Handle source type change
  const handleSourceTypeChange = (sourceType: SourceType) => {
    onStateChange({
      sourceType,
      sourceQuery: sourceType === 'query' ? state.sourceQuery : '',
    })
  }
  
  // Handle schema selection
  const handleSchemaChange = (schema: string) => {
    setSelectedSchema(schema)
    onStateChange({
      sourceSchema: schema,
      sourceTable: '',
      availableColumns: [],
      selectedColumns: [],
    })
  }
  
  // Handle table selection
  const handleTableChange = (tableName: string) => {
    const table = tables.find(t => t.name === tableName)
    const columns: ColumnConfig[] = (table?.columns || []).map(col => ({
      name: col.name,
      data_type: col.data_type,
      include: true,
      nullable: col.is_nullable,
      comment: col.comment,
    }))
    
    onStateChange({
      sourceTable: tableName,
      availableColumns: columns,
      selectedColumns: columns,
    })
  }
  
  // Handle query validation
  const handleValidateQuery = async () => {
    if (!state.connectionId || !state.sourceQuery) return
    
    validateQuery.mutate(
      { connection_id: state.connectionId, query: state.sourceQuery },
      {
        onSuccess: (result) => {
          if (result.valid && result.columns) {
            const columns: ColumnConfig[] = result.columns.map(col => ({
              name: col.name,
              data_type: col.data_type,
              include: true,
              nullable: col.nullable ?? true,
            }))
            onStateChange({
              availableColumns: columns,
              selectedColumns: columns,
            })
          }
        },
      }
    )
  }
  
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">Select Data Source</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Choose a connection and specify the source table or SQL query.
        </p>
      </div>
      
      {/* Connection Selection */}
      <div className="space-y-2">
        <Label htmlFor="connection">Connection</Label>
        <Select
          value={state.connectionId}
          onValueChange={handleConnectionChange}
        >
          <SelectTrigger id="connection">
            <SelectValue placeholder="Select a connection" />
          </SelectTrigger>
          <SelectContent>
            {loadingConnections ? (
              <div className="flex items-center justify-center p-4">
                <Loader2 className="h-4 w-4 animate-spin" />
              </div>
            ) : (
              connectionsData?.items?.map((conn: DataSource) => (
                <SelectItem key={conn.id} value={conn.id}>
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4" />
                    <span>{conn.name}</span>
                    <span className="text-xs text-muted-foreground">
                      ({conn.db_type})
                    </span>
                  </div>
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
      </div>
      
      {/* Source Type Selection */}
      {state.connectionId && (
        <div className="space-y-3">
          <Label>Source Type</Label>
          <RadioGroup
            value={state.sourceType}
            onValueChange={(v: string) => handleSourceTypeChange(v as SourceType)}
            className="flex gap-4"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="table" id="source-table" />
              <Label htmlFor="source-table" className="flex items-center gap-2 cursor-pointer">
                <Table className="h-4 w-4" />
                Table
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="query" id="source-query" />
              <Label htmlFor="source-query" className="flex items-center gap-2 cursor-pointer">
                <Code className="h-4 w-4" />
                SQL Query
              </Label>
            </div>
          </RadioGroup>
        </div>
      )}
      
      {/* Table Selection */}
      {state.connectionId && state.sourceType === 'table' && (
        <div className="space-y-4">
          {loadingSchema ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading schema...
            </div>
          ) : (
            <>
              {/* Schema Selection */}
              <div className="space-y-2">
                <Label htmlFor="schema">Schema</Label>
                <Select
                  value={selectedSchema}
                  onValueChange={handleSchemaChange}
                >
                  <SelectTrigger id="schema">
                    <SelectValue placeholder="Select a schema" />
                  </SelectTrigger>
                  <SelectContent>
                    {schemas.map((schema) => (
                      <SelectItem key={schema.name} value={schema.name}>
                        {schema.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Table Selection */}
              {selectedSchema && (
                <div className="space-y-2">
                  <Label htmlFor="table">Table</Label>
                  <Select
                    value={state.sourceTable}
                    onValueChange={handleTableChange}
                  >
                    <SelectTrigger id="table">
                      <SelectValue placeholder="Select a table" />
                    </SelectTrigger>
                    <SelectContent>
                      {tables.map((table: TableInfo) => (
                        <SelectItem key={table.name} value={table.name}>
                          <div className="flex items-center gap-2">
                            <Table className="h-4 w-4" />
                            {table.name}
                            {table.row_count !== undefined && (
                              <span className="text-xs text-muted-foreground">
                                (~{table.row_count.toLocaleString()} rows)
                              </span>
                            )}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </>
          )}
        </div>
      )}
      
      {/* SQL Query Input */}
      {state.connectionId && state.sourceType === 'query' && (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="query">SQL Query</Label>
            <Textarea
              id="query"
              value={state.sourceQuery}
              onChange={(e) => onStateChange({ sourceQuery: e.target.value })}
              placeholder="SELECT column1, column2 FROM schema.table WHERE ..."
              className="font-mono text-sm min-h-[150px]"
            />
          </div>
          
          <div className="flex items-center gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleValidateQuery}
              disabled={!state.sourceQuery || validateQuery.isPending}
            >
              {validateQuery.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <CheckCircle className="h-4 w-4 mr-2" />
              )}
              Validate Query
            </Button>
            
            {validateQuery.data && (
              <span className={`text-sm ${validateQuery.data.valid ? 'text-green-600' : 'text-red-600'}`}>
                {validateQuery.data.message}
              </span>
            )}
          </div>
          
          {validateQuery.isError && (
            <Alert variant="destructive">
              <AlertDescription>
                Failed to validate query. Please check your syntax.
              </AlertDescription>
            </Alert>
          )}
        </div>
      )}
      
      {/* Column Preview */}
      {state.availableColumns.length > 0 && (
        <Alert>
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>
            Found {state.availableColumns.length} columns. Proceed to the next step to select columns.
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}

export default SourceSelector
