/**
 * Pipeline Wizard - Step 4: Review & Create
 */

import { useState } from 'react'
import { Check, Copy, Code, Loader2, AlertTriangle, RefreshCw } from 'lucide-react'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { usePreviewPipelineCode } from '../hooks'
import type { WizardState, PipelinePreviewRequest, PipelinePreviewResponse } from '@/types/pipeline'

interface ReviewStepProps {
  state: WizardState
}

export function ReviewStep({ state }: ReviewStepProps) {
  const [codePreview, setCodePreview] = useState<PipelinePreviewResponse | null>(null)
  const [copied, setCopied] = useState(false)
  
  const previewMutation = usePreviewPipelineCode()

  // Build preview request
  const handlePreviewCode = async () => {
    const isFile = state.sourceKind === 'file'
    const request: PipelinePreviewRequest = {
      source_kind: state.sourceKind,
      connection_id: isFile ? undefined : state.connectionId,
      source_type: state.sourceType,
      source_schema: isFile ? undefined : state.sourceSchema,
      source_table: isFile ? undefined : state.sourceTable,
      source_query: isFile ? undefined : state.sourceQuery,
      file_format: isFile ? state.fileFormat : undefined,
      file_object_key: isFile ? state.fileObjectKey : undefined,
      file_options: isFile ? (state.fileOptions ?? {}) : undefined,
      columns_config: state.columnsConfig.filter(c => c.include),
      primary_key_columns: state.primaryKeyColumns,
      incremental_cursor_column: state.incrementalCursorColumn,
      incremental_cursor_type: state.incrementalCursorType,
      write_disposition: state.writeDisposition,
      partition_columns: state.partitionColumns,
      iceberg_table_name: state.icebergTableName,
    }
    
    try {
      const result = await previewMutation.mutateAsync(request)
      setCodePreview(result)
    } catch (error) {
      console.error('Preview failed:', error)
    }
  }

  // Copy code to clipboard
  const handleCopyCode = async () => {
    if (codePreview?.code) {
      await navigator.clipboard.writeText(codePreview.code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  // Get selected columns
  const selectedColumns = state.columnsConfig.filter(c => c.include)

  // Validation
  const validationErrors: string[] = []
  if (!state.name) validationErrors.push('Pipeline name is required')
  if (state.sourceKind === 'file') {
    if (!state.fileObjectKey) validationErrors.push('Uploaded file is required')
    if (!state.fileFormat) validationErrors.push('File format is required')
  } else {
    if (!state.connectionId) validationErrors.push('Connection is required')
    if (state.sourceType === 'table' && !state.sourceTable) {
      validationErrors.push('Source table is required')
    }
    if (state.sourceType === 'query' && !state.sourceQuery) {
      validationErrors.push('Source query is required')
    }
  }
  if (selectedColumns.length === 0) {
    validationErrors.push('At least one column must be selected')
  }
  if ((state.writeDisposition === 'merge' || state.writeDisposition === 'scd2') && 
      (!state.primaryKeyColumns || state.primaryKeyColumns.length === 0)) {
    validationErrors.push('Primary key is required for merge/scd2 write disposition')
  }
  if (state.incrementalCursorType !== 'none' && !state.incrementalCursorColumn) {
    validationErrors.push('Incremental cursor column is required when incremental type is set')
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">Review & Create</h3>
        <p className="text-sm text-muted-foreground">
          Review your pipeline configuration and preview the generated code before creating.
        </p>
      </div>

      {/* Validation Errors */}
      {validationErrors.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Please fix the following issues</AlertTitle>
          <AlertDescription>
            <ul className="list-disc list-inside mt-2">
              {validationErrors.map((error, i) => (
                <li key={i}>{error}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Configuration Summary */}
      <Accordion type="single" collapsible defaultValue="summary" className="w-full">
        <AccordionItem value="summary">
          <AccordionTrigger>Configuration Summary</AccordionTrigger>
          <AccordionContent>
            <div className="grid grid-cols-2 gap-4 p-4 bg-muted/50 rounded-lg">
              <div>
                <Label className="text-muted-foreground">Pipeline Name</Label>
                <p className="font-medium">{state.name || '(not set)'}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Source Kind</Label>
                <p className="font-medium capitalize">
                  {state.sourceKind === 'file' ? 'File upload' : 'SQL database'}
                </p>
              </div>
              <div>
                <Label className="text-muted-foreground">Source</Label>
                <p className="font-mono text-sm break-all">
                  {state.sourceKind === 'file'
                    ? `${state.fileOriginalName ?? state.fileObjectKey} (${state.fileFormat?.toUpperCase()})`
                    : state.sourceType === 'table'
                      ? `${state.sourceSchema}.${state.sourceTable}`
                      : 'Custom Query'
                  }
                </p>
              </div>
              <div>
                <Label className="text-muted-foreground">Write Disposition</Label>
                <Badge variant="outline" className="capitalize">
                  {state.writeDisposition}
                </Badge>
              </div>
              <div>
                <Label className="text-muted-foreground">Selected Columns</Label>
                <p className="font-medium">{selectedColumns.length} columns</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Primary Key</Label>
                <p className="font-mono text-sm">
                  {state.primaryKeyColumns?.length > 0 
                    ? state.primaryKeyColumns.join(', ')
                    : '(none)'
                  }
                </p>
              </div>
              <div>
                <Label className="text-muted-foreground">Incremental</Label>
                <p className="capitalize">
                  {state.incrementalCursorType !== 'none' 
                    ? `${state.incrementalCursorType} (${state.incrementalCursorColumn})`
                    : 'Full Load'
                  }
                </p>
              </div>
              <div>
                <Label className="text-muted-foreground">Iceberg Table</Label>
                <p className="font-mono text-sm">
                  {state.icebergTableName || '(auto-generated)'}
                </p>
              </div>
              <div>
                <Label className="text-muted-foreground">Schedule</Label>
                <p className="font-mono text-sm">
                  {(() => {
                    const opts = state.options || {}
                    const cron = typeof opts.schedule_cron === 'string' ? opts.schedule_cron : ''
                    const preset = typeof opts.schedule_preset === 'string' ? opts.schedule_preset : ''
                    if (cron) return `cron: ${cron}`
                    if (preset) return preset
                    return 'manual (no schedule)'
                  })()}
                </p>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="columns">
          <AccordionTrigger>Selected Columns ({selectedColumns.length})</AccordionTrigger>
          <AccordionContent>
            <div className="flex flex-wrap gap-2 p-4 bg-muted/50 rounded-lg">
              {selectedColumns.map((col) => (
                <Badge key={col.name} variant="secondary" className="font-mono">
                  {col.name}
                  <span className="ml-1 text-muted-foreground text-xs">
                    {col.data_type}
                  </span>
                </Badge>
              ))}
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      {/* Code Preview */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label className="text-base font-semibold">Generated Code Preview</Label>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePreviewCode}
              disabled={previewMutation.isPending || validationErrors.length > 0}
            >
              {previewMutation.isPending ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              {codePreview ? 'Refresh' : 'Preview Code'}
            </Button>
            {codePreview && (
              <Button variant="outline" size="sm" onClick={handleCopyCode}>
                {copied ? (
                  <Check className="h-4 w-4 mr-2 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4 mr-2" />
                )}
                {copied ? 'Copied!' : 'Copy'}
              </Button>
            )}
          </div>
        </div>

        {codePreview?.validation_errors && codePreview.validation_errors.length > 0 && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertTitle>Validation Errors</AlertTitle>
            <AlertDescription>
              <ul className="list-disc list-inside">
                {codePreview.validation_errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {codePreview?.code ? (
          <ScrollArea className="h-[400px] border rounded-md">
            <pre className="p-4 text-sm font-mono bg-muted">
              <code>{codePreview.code}</code>
            </pre>
          </ScrollArea>
        ) : (
          <div className="h-[200px] border rounded-md flex items-center justify-center bg-muted/50">
            <div className="text-center text-muted-foreground">
              <Code className="h-8 w-8 mx-auto mb-2" />
              <p>Click "Preview Code" to see the generated dlt pipeline</p>
            </div>
          </div>
        )}

        {codePreview && (
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span>Template: {codePreview.template_name}</span>
            <span>Version: {codePreview.template_version}</span>
          </div>
        )}
      </div>
    </div>
  )
}
