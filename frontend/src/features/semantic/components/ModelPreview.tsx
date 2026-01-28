/**
 * Model Preview Component
 * Shows a preview of the semantic model data
 */

import { useState } from 'react'
import { Play, RefreshCw, Clock, Database } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useSemanticQuery } from '../hooks/useSemanticModels'
import type { SemanticModel, QueryResult } from '../types'

interface ModelPreviewProps {
  model: SemanticModel
}

export function ModelPreview({ model }: ModelPreviewProps) {
  const [result, setResult] = useState<QueryResult | null>(null)
  const semanticQuery = useSemanticQuery()
  
  const dimensions = model.dimensions || []
  const measures = model.measures || []
  
  const handleRunPreview = async () => {
    if (measures.length === 0) return
    
    try {
      // Use first 3 dimensions and first 3 measures for preview
      const previewDimensions = dimensions
        .filter(d => !d.is_hidden)
        .slice(0, 3)
        .map(d => d.name)
      
      const previewMeasures = measures
        .filter(m => !m.is_hidden)
        .slice(0, 3)
        .map(m => m.name)
      
      if (previewMeasures.length === 0) {
        return
      }
      
      const queryResult = await semanticQuery.mutateAsync({
        dimensions: previewDimensions.length > 0 ? previewDimensions : undefined,
        measures: previewMeasures,
        limit: 10,
      })
      
      setResult(queryResult)
    } catch (error) {
      console.error('Preview query failed:', error)
    }
  }
  
  const canRunPreview = measures.filter(m => !m.is_hidden).length > 0
  
  return (
    <div className="space-y-4">
      {/* Model Info */}
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">{model.dbt_model}</span>
        </div>
        
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline">
            {dimensions.length} Dimensions
          </Badge>
          <Badge variant="outline">
            {measures.length} Measures
          </Badge>
          {model.cache_enabled && (
            <Badge variant="secondary" className="text-xs">
              <Clock className="h-3 w-3 mr-1" />
              Cached ({model.cache_ttl_seconds}s)
            </Badge>
          )}
        </div>
      </div>
      
      {/* Run Preview Button */}
      <Button 
        onClick={handleRunPreview} 
        disabled={!canRunPreview || semanticQuery.isPending}
        className="w-full"
        variant="outline"
      >
        {semanticQuery.isPending ? (
          <>
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            Running...
          </>
        ) : (
          <>
            <Play className="h-4 w-4 mr-2" />
            Run Preview Query
          </>
        )}
      </Button>
      
      {!canRunPreview && (
        <p className="text-xs text-muted-foreground text-center">
          Add measures to enable preview
        </p>
      )}
      
      {/* Query Result */}
      {result && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{result.row_count} rows</span>
            <span>{result.execution_time_ms.toFixed(1)}ms</span>
            {result.from_cache && (
              <Badge variant="secondary" className="text-xs">
                Cached
              </Badge>
            )}
          </div>
          
          <div className="border rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    {result.columns.map((col) => (
                      <TableHead key={col} className="text-xs whitespace-nowrap">
                        {col}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.rows.slice(0, 10).map((row, i) => (
                    <TableRow key={i}>
                      {row.map((cell, j) => (
                        <TableCell key={j} className="text-xs whitespace-nowrap">
                          {formatCell(cell)}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
          
          {result.rows.length > 10 && (
            <p className="text-xs text-muted-foreground text-center">
              Showing first 10 of {result.row_count} rows
            </p>
          )}
        </div>
      )}
      
      {/* Field Summary */}
      {!result && (
        <div className="space-y-3">
          {dimensions.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground mb-2">
                DIMENSIONS
              </h4>
              <div className="space-y-1">
                {dimensions.slice(0, 5).map((dim) => (
                  <div 
                    key={dim.id} 
                    className="flex items-center justify-between text-sm p-2 bg-muted/30 rounded"
                  >
                    <span className={dim.is_hidden ? 'text-muted-foreground' : ''}>
                      {dim.label || dim.name}
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {dim.type}
                    </Badge>
                  </div>
                ))}
                {dimensions.length > 5 && (
                  <p className="text-xs text-muted-foreground text-center">
                    +{dimensions.length - 5} more
                  </p>
                )}
              </div>
            </div>
          )}
          
          {measures.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground mb-2">
                MEASURES
              </h4>
              <div className="space-y-1">
                {measures.slice(0, 5).map((measure) => (
                  <div 
                    key={measure.id} 
                    className="flex items-center justify-between text-sm p-2 bg-muted/30 rounded"
                  >
                    <span className={measure.is_hidden ? 'text-muted-foreground' : ''}>
                      {measure.label || measure.name}
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {measure.aggregation.toUpperCase()}
                    </Badge>
                  </div>
                ))}
                {measures.length > 5 && (
                  <p className="text-xs text-muted-foreground text-center">
                    +{measures.length - 5} more
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) {
    return '—'
  }
  if (typeof value === 'number') {
    return value.toLocaleString()
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  return String(value)
}
