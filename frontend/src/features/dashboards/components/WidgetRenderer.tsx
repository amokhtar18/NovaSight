/**
 * Widget Renderer Component
 */

import { MoreVertical, AlertCircle } from 'lucide-react'
import { useWidgetData } from '../hooks/useDashboards'
import { MetricCard, DataTable, ChartWrapper } from './widgets'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { Widget } from '@/types/dashboard'

interface WidgetRendererProps {
  widget: Widget
  isEditing?: boolean
  onEdit?: () => void
  onDelete?: () => void
}

export function WidgetRenderer({ 
  widget, 
  isEditing,
  onEdit,
  onDelete,
}: WidgetRendererProps) {
  const { data, isLoading, error } = useWidgetData(
    widget.dashboard_id,
    widget.id,
    // Only auto-refresh if not in editing mode
    !isEditing,
    30 // default 30 seconds
  )
  
  if (isLoading) {
    return <WidgetSkeleton />
  }
  
  if (error) {
    return <WidgetError error={error as Error} />
  }
  
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="font-medium text-sm truncate">{widget.name}</h3>
        {isEditing && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-6 w-6">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onEdit}>
                Edit Widget
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onDelete} className="text-destructive">
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
      
      <div className="flex-1 p-3 overflow-hidden">
        {widget.type === 'metric_card' && (
          <MetricCard data={data?.data || []} config={widget.viz_config} />
        )}
        {widget.type === 'table' && (
          <DataTable 
            data={data?.data || []} 
            columns={widget.viz_config.columns || []} 
          />
        )}
        {['bar_chart', 'line_chart', 'pie_chart', 'area_chart', 'scatter_chart'].includes(widget.type) && (
          <ChartWrapper 
            type={widget.type}
            data={data?.data || []} 
            config={widget.viz_config} 
          />
        )}
      </div>
    </div>
  )
}

function WidgetSkeleton() {
  return (
    <div className="h-full flex flex-col">
      <div className="p-3 border-b">
        <Skeleton className="h-5 w-32" />
      </div>
      <div className="flex-1 p-3">
        <Skeleton className="h-full w-full" />
      </div>
    </div>
  )
}

function WidgetError({ error }: { error: Error }) {
  return (
    <div className="h-full flex flex-col items-center justify-center p-4 text-center">
      <AlertCircle className="h-8 w-8 text-destructive mb-2" />
      <p className="text-sm text-muted-foreground">
        Failed to load widget data
      </p>
      <p className="text-xs text-muted-foreground mt-1">
        {error.message}
      </p>
    </div>
  )
}
