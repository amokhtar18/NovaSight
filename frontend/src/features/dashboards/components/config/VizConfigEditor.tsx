/**
 * Visualization Configuration Editor
 */

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import type { VizConfig, WidgetType } from '@/types/dashboard'

interface VizConfigEditorProps {
  type: WidgetType
  config: VizConfig
  onChange: (config: VizConfig) => void
}

export function VizConfigEditor({ type, config, onChange }: VizConfigEditorProps) {
  const isChart = ['bar_chart', 'line_chart', 'area_chart', 'pie_chart', 'scatter_chart'].includes(type)
  
  return (
    <div className="space-y-4">
      {type === 'metric_card' && (
        <>
          <div>
            <Label htmlFor="metric">Metric Field</Label>
            <Input
              id="metric"
              value={config.metric || ''}
              onChange={(e) => onChange({ ...config, metric: e.target.value })}
              placeholder="e.g., total_revenue"
            />
          </div>
        </>
      )}
      
      {isChart && (
        <>
          <div>
            <Label htmlFor="xAxis">X-Axis Field</Label>
            <Input
              id="xAxis"
              value={config.xAxis || ''}
              onChange={(e) => onChange({ ...config, xAxis: e.target.value })}
              placeholder="e.g., date"
            />
          </div>
          
          <div>
            <Label htmlFor="yAxis">Y-Axis Field(s)</Label>
            <Input
              id="yAxis"
              value={Array.isArray(config.yAxis) ? config.yAxis.join(', ') : config.yAxis || ''}
              onChange={(e) => {
                const value = e.target.value
                const yAxis = value.includes(',') 
                  ? value.split(',').map(s => s.trim()).filter(Boolean)
                  : value
                onChange({ ...config, yAxis })
              }}
              placeholder="e.g., revenue, profit (comma-separated for multiple)"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Use comma-separated values for multiple series
            </p>
          </div>
          
          <Separator />
          
          <div className="flex items-center justify-between">
            <Label htmlFor="showLegend">Show Legend</Label>
            <Switch
              id="showLegend"
              checked={config.showLegend !== false}
              onCheckedChange={(checked) => onChange({ ...config, showLegend: checked })}
            />
          </div>
          
          <div className="flex items-center justify-between">
            <Label htmlFor="showGrid">Show Grid</Label>
            <Switch
              id="showGrid"
              checked={config.showGrid !== false}
              onCheckedChange={(checked) => onChange({ ...config, showGrid: checked })}
            />
          </div>
          
          {type === 'area_chart' && (
            <div className="flex items-center justify-between">
              <Label htmlFor="stacked">Stacked</Label>
              <Switch
                id="stacked"
                checked={config.stacked || false}
                onCheckedChange={(checked) => onChange({ ...config, stacked: checked })}
              />
            </div>
          )}
        </>
      )}
      
      {type === 'table' && (
        <div>
          <Label>Table Columns</Label>
          <p className="text-sm text-muted-foreground mt-1">
            Columns will be automatically generated from query results
          </p>
        </div>
      )}
    </div>
  )
}
