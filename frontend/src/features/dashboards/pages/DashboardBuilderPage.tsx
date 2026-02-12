/**
 * Dashboard Builder Page
 */

import { useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import GridLayout, { Layout } from 'react-grid-layout'
import { useDashboard, useUpdateDashboardLayout, useDeleteWidget } from '../hooks/useDashboards'
import { DashboardToolbar } from '../components/DashboardToolbar'
import { WidgetRenderer } from '../components/WidgetRenderer'
import { WidgetConfigPanel } from '../components/WidgetConfigPanel'
import { AddWidgetDialog } from '../components/AddWidgetDialog'
import { AddChartToDashboardDialog } from '../components/AddChartToDashboardDialog'
import { Skeleton } from '@/components/ui/skeleton'
import type { Widget } from '@/types/dashboard'

import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'
import '../styles/grid-layout.css'

export function DashboardBuilderPage() {
  const { dashboardId } = useParams<{ dashboardId: string }>()
  const [isEditing, setIsEditing] = useState(false)
  const [selectedWidget, setSelectedWidget] = useState<Widget | null>(null)
  
  const { data: dashboard, isLoading } = useDashboard(dashboardId)
  const layoutMutation = useUpdateDashboardLayout(dashboardId!)
  const deleteMutation = useDeleteWidget(dashboardId!)
  
  const handleLayoutChange = useCallback((newLayout: Layout[]) => {
    if (isEditing && dashboard) {
      // Map layout changes back to widgets
      const updatedLayout = newLayout.map(item => ({
        widget_id: item.i,
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
      }))
      layoutMutation.mutate(updatedLayout)
    }
  }, [isEditing, dashboard, layoutMutation])
  
  const handleWidgetDelete = async (widgetId: string) => {
    if (confirm('Are you sure you want to delete this widget?')) {
      await deleteMutation.mutateAsync(widgetId)
      if (selectedWidget?.id === widgetId) {
        setSelectedWidget(null)
      }
    }
  }
  
  if (isLoading) {
    return <DashboardSkeleton />
  }
  
  if (!dashboard) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-muted-foreground">Dashboard not found</p>
      </div>
    )
  }
  
  const layout: Layout[] = dashboard.widgets.map((w: Widget) => ({
    i: w.id,
    x: w.grid_position.x,
    y: w.grid_position.y,
    w: w.grid_position.w,
    h: w.grid_position.h,
    minW: w.grid_position.minW,
    minH: w.grid_position.minH,
    maxW: w.grid_position.maxW,
    maxH: w.grid_position.maxH,
  }))
  
  return (
    <div className="flex flex-col h-screen">
      <DashboardToolbar 
        dashboard={dashboard}
        isEditing={isEditing}
        onEditToggle={() => setIsEditing(!isEditing)}
      />
      
      <div className="flex-1 overflow-auto p-4 bg-muted/50">
        <GridLayout
          className="layout"
          layout={layout}
          cols={12}
          rowHeight={80}
          width={1200}
          isDraggable={isEditing}
          isResizable={isEditing}
          onLayoutChange={handleLayoutChange}
          draggableHandle=".widget-drag-handle"
        >
          {dashboard.widgets.map((widget: Widget) => (
            <div 
              key={widget.id}
              className={`bg-card rounded-lg shadow-sm border transition-all ${
                selectedWidget?.id === widget.id ? 'ring-2 ring-primary' : ''
              } ${isEditing ? 'cursor-move' : ''}`}
              onClick={() => isEditing && setSelectedWidget(widget)}
            >
              <div className={isEditing ? 'widget-drag-handle' : ''}>
                <WidgetRenderer 
                  widget={widget}
                  isEditing={isEditing}
                  onEdit={() => setSelectedWidget(widget)}
                  onDelete={() => handleWidgetDelete(widget.id)}
                />
              </div>
            </div>
          ))}
        </GridLayout>
        
        {isEditing && (
          <>
            <AddWidgetDialog dashboardId={dashboardId!} />
            <AddChartToDashboardDialog dashboardId={dashboardId!} />
          </>
        )}
      </div>
      
      {selectedWidget && isEditing && (
        <WidgetConfigPanel
          widget={selectedWidget}
          onClose={() => setSelectedWidget(null)}
        />
      )}
    </div>
  )
}

function DashboardSkeleton() {
  return (
    <div className="flex flex-col h-screen">
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <Skeleton className="h-8 w-64" />
        <div className="flex gap-2">
          <Skeleton className="h-10 w-24" />
          <Skeleton className="h-10 w-24" />
        </div>
      </div>
      <div className="flex-1 p-4 space-y-4">
        <Skeleton className="h-64 w-full" />
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
          <Skeleton className="h-48" />
        </div>
      </div>
    </div>
  )
}
