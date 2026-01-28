/**
 * PySpark Code Preview Component
 * 
 * Step 6 of the PySpark App Builder wizard.
 * Shows generated code preview and allows saving.
 */

import { useState, useEffect } from 'react'
import { Code, Copy, Check, Download, Loader2, AlertCircle, Eye } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { usePreviewPySparkCode } from '../hooks'
import type { PySparkWizardState, PySparkCodePreview } from '@/types/pyspark'

interface PySparkPreviewProps {
  state: PySparkWizardState
}

export function PySparkPreview({ state }: PySparkPreviewProps) {
  const [copied, setCopied] = useState(false)
  const previewMutation = usePreviewPySparkCode()
  
  // Build preview request from wizard state
  const buildPreviewRequest = (): PySparkCodePreview => {
    return {
      connection_id: state.connectionId,
      source_type: state.sourceType,
      source_schema: state.sourceSchema || undefined,
      source_table: state.sourceTable || undefined,
      source_query: state.sourceQuery || undefined,
      columns_config: state.selectedColumns.filter(c => c.include),
      primary_key_columns: state.primaryKeyColumns,
      cdc_type: state.cdcType,
      cdc_column: state.cdcColumn || undefined,
      partition_columns: state.partitionColumns,
      scd_type: state.scdType,
      write_mode: state.writeMode,
      target_database: state.targetDatabase,
      target_table: state.targetTable,
      target_engine: state.targetEngine,
      options: state.options,
    }
  }
  
  // Generate preview on mount
  useEffect(() => {
    if (state.connectionId && state.targetDatabase && state.targetTable) {
      previewMutation.mutate(buildPreviewRequest())
    }
  }, [])
  
  // Regenerate preview
  const handleRegenerate = () => {
    previewMutation.mutate(buildPreviewRequest())
  }
  
  // Copy code to clipboard
  const handleCopy = async () => {
    if (previewMutation.data?.code) {
      await navigator.clipboard.writeText(previewMutation.data.code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }
  
  // Download code as file
  const handleDownload = () => {
    if (previewMutation.data?.code) {
      const blob = new Blob([previewMutation.data.code], { type: 'text/x-python' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${state.name || 'pyspark_job'}.py`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">Code Preview</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Review the generated PySpark code before saving.
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleRegenerate}
            disabled={previewMutation.isPending}
          >
            {previewMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-2" />
            ) : (
              <Eye className="h-4 w-4 mr-2" />
            )}
            Regenerate
          </Button>
          
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleCopy}
            disabled={!previewMutation.data?.code}
          >
            {copied ? (
              <Check className="h-4 w-4 mr-2 text-green-500" />
            ) : (
              <Copy className="h-4 w-4 mr-2" />
            )}
            {copied ? 'Copied!' : 'Copy'}
          </Button>
          
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleDownload}
            disabled={!previewMutation.data?.code}
          >
            <Download className="h-4 w-4 mr-2" />
            Download
          </Button>
        </div>
      </div>
      
      {/* Error State */}
      {previewMutation.isError && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to generate code preview. Please check your configuration.
          </AlertDescription>
        </Alert>
      )}
      
      {/* Loading State */}
      {previewMutation.isPending && (
        <div className="flex items-center justify-center py-12 border rounded-lg bg-muted/20">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">Generating code preview...</p>
          </div>
        </div>
      )}
      
      {/* Code Preview */}
      {previewMutation.data && (
        <Tabs defaultValue="code" className="w-full">
          <TabsList>
            <TabsTrigger value="code">
              <Code className="h-4 w-4 mr-2" />
              Generated Code
            </TabsTrigger>
            <TabsTrigger value="metadata">
              Metadata
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="code" className="mt-4">
            <div className="border rounded-lg overflow-hidden">
              <div className="bg-muted px-4 py-2 flex items-center justify-between border-b">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">Python</Badge>
                  <span className="text-sm text-muted-foreground">
                    {state.name || 'pyspark_job'}.py
                  </span>
                </div>
                <Badge variant="secondary">
                  {previewMutation.data.template_name}
                </Badge>
              </div>
              
              <div className="h-[500px] overflow-auto">
                <pre className="p-4 text-sm font-mono bg-slate-950 text-slate-50 overflow-x-auto">
                  <code>{previewMutation.data.code}</code>
                </pre>
              </div>
            </div>
          </TabsContent>
          
          <TabsContent value="metadata" className="mt-4">
            <div className="border rounded-lg p-4 space-y-4">
              <h4 className="font-medium">Generation Metadata</h4>
              
              <dl className="grid grid-cols-2 gap-4 text-sm">
                <dt className="text-muted-foreground">Template:</dt>
                <dd className="font-mono">{previewMutation.data.template_name}</dd>
                
                <dt className="text-muted-foreground">Template Version:</dt>
                <dd>{previewMutation.data.template_version}</dd>
                
                <dt className="text-muted-foreground">Parameters Hash:</dt>
                <dd className="font-mono text-xs truncate">
                  {previewMutation.data.parameters_hash}
                </dd>
                
                <dt className="text-muted-foreground">Preview Mode:</dt>
                <dd>
                  <Badge variant="outline">
                    {previewMutation.data.is_preview ? 'Yes' : 'No'}
                  </Badge>
                </dd>
              </dl>
              
              <Alert>
                <AlertDescription>
                  This code is generated from a pre-approved template.
                  All executable artifacts follow the Template Engine Rule (ADR-002).
                </AlertDescription>
              </Alert>
            </div>
          </TabsContent>
        </Tabs>
      )}
      
      {/* Save Instructions */}
      <Alert>
        <AlertDescription>
          Click <strong>Save PySpark App</strong> below to save this configuration.
          You can regenerate the code at any time after saving.
        </AlertDescription>
      </Alert>
    </div>
  )
}

export default PySparkPreview
