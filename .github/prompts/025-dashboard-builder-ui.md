# 025 - Dashboard Builder UI

## Metadata

```yaml
prompt_id: "025"
phase: 4
agent: "@dashboard"
model: "sonnet 4.5"
priority: P0
estimated_effort: "5 days"
dependencies: ["006", "024"]
```

## Objective

Implement the interactive dashboard builder with drag-and-drop widget placement.

## Task Description

Create React components for building, configuring, and viewing dashboards.

## Requirements

### Dashboard Builder Page

```tsx
// src/features/dashboards/pages/DashboardBuilderPage.tsx
import { useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import GridLayout from 'react-grid-layout'
import { DashboardToolbar } from '../components/DashboardToolbar'
import { WidgetRenderer } from '../components/WidgetRenderer'
import { WidgetConfigPanel } from '../components/WidgetConfigPanel'
import { AddWidgetDialog } from '../components/AddWidgetDialog'
import { api } from '@/lib/api'

import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

export function DashboardBuilderPage() {
  const { dashboardId } = useParams()
  const [isEditing, setIsEditing] = useState(false)
  const [selectedWidget, setSelectedWidget] = useState(null)
  const queryClient = useQueryClient()
  
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ['dashboard', dashboardId],
    queryFn: () => api.get(`/dashboards/${dashboardId}`).then(r => r.data),
  })
  
  const layoutMutation = useMutation({
    mutationFn: (layout) => api.put(
      `/dashboards/${dashboardId}/layout`,
      { layout }
    ),
    onSuccess: () => {
      queryClient.invalidateQueries(['dashboard', dashboardId])
    },
  })
  
  const handleLayoutChange = useCallback((newLayout) => {
    if (isEditing) {
      layoutMutation.mutate(newLayout)
    }
  }, [isEditing, layoutMutation])
  
  if (isLoading) return <DashboardSkeleton />
  
  const layout = dashboard.widgets.map(w => ({
    i: w.id,
    ...w.grid_position
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
          rowHeight={100}
          width={1200}
          isDraggable={isEditing}
          isResizable={isEditing}
          onLayoutChange={handleLayoutChange}
        >
          {dashboard.widgets.map((widget) => (
            <div 
              key={widget.id}
              className={`bg-card rounded-lg shadow-sm border ${
                selectedWidget?.id === widget.id ? 'ring-2 ring-primary' : ''
              }`}
              onClick={() => isEditing && setSelectedWidget(widget)}
            >
              <WidgetRenderer 
                widget={widget}
                isEditing={isEditing}
              />
            </div>
          ))}
        </GridLayout>
        
        {isEditing && (
          <AddWidgetDialog dashboardId={dashboardId} />
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
```

### Widget Renderer Component

```tsx
// src/features/dashboards/components/WidgetRenderer.tsx
import { useQuery } from '@tanstack/react-query'
import { BarChart, LineChart, PieChart, AreaChart } from 'recharts'
import { MetricCard } from './widgets/MetricCard'
import { DataTable } from './widgets/DataTable'
import { ChartWrapper } from './widgets/ChartWrapper'
import { api } from '@/lib/api'

interface WidgetRendererProps {
  widget: Widget
  isEditing?: boolean
}

export function WidgetRenderer({ widget, isEditing }: WidgetRendererProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['widget-data', widget.id],
    queryFn: () => api.get(
      `/dashboards/${widget.dashboard_id}/widgets/${widget.id}/data`
    ).then(r => r.data),
    refetchInterval: widget.dashboard?.auto_refresh 
      ? widget.dashboard.refresh_interval * 1000 
      : false,
  })
  
  if (isLoading) return <WidgetSkeleton />
  if (error) return <WidgetError error={error} />
  
  const ChartComponent = getChartComponent(widget.type)
  
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-3 border-b">
        <h3 className="font-medium text-sm">{widget.name}</h3>
        {isEditing && <WidgetMenu widget={widget} />}
      </div>
      
      <div className="flex-1 p-3 overflow-hidden">
        {widget.type === 'metric_card' ? (
          <MetricCard data={data.data} config={widget.viz_config} />
        ) : widget.type === 'table' ? (
          <DataTable data={data.data} columns={widget.viz_config.columns} />
        ) : (
          <ChartWrapper type={widget.type} data={data.data} config={widget.viz_config} />
        )}
      </div>
    </div>
  )
}

function getChartComponent(type: string) {
  const components = {
    bar_chart: BarChart,
    line_chart: LineChart,
    pie_chart: PieChart,
    area_chart: AreaChart,
  }
  return components[type]
}
```

### Widget Configuration Panel

```tsx
// src/features/dashboards/components/WidgetConfigPanel.tsx
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { QueryConfigEditor } from './config/QueryConfigEditor'
import { VizConfigEditor } from './config/VizConfigEditor'
import { api } from '@/lib/api'

interface WidgetConfigPanelProps {
  widget: Widget
  onClose: () => void
}

export function WidgetConfigPanel({ widget, onClose }: WidgetConfigPanelProps) {
  const [config, setConfig] = useState({
    name: widget.name,
    type: widget.type,
    query_config: widget.query_config,
    viz_config: widget.viz_config,
  })
  
  const queryClient = useQueryClient()
  
  const mutation = useMutation({
    mutationFn: (data) => api.put(
      `/dashboards/${widget.dashboard_id}/widgets/${widget.id}`,
      data
    ),
    onSuccess: () => {
      queryClient.invalidateQueries(['dashboard', widget.dashboard_id])
      queryClient.invalidateQueries(['widget-data', widget.id])
      onClose()
    },
  })
  
  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-card border-l shadow-lg z-50">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="font-semibold">Configure Widget</h2>
        <Button variant="ghost" size="icon" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>
      
      <div className="p-4 overflow-auto h-[calc(100%-120px)]">
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">Widget Name</label>
            <Input
              value={config.name}
              onChange={(e) => setConfig({ ...config, name: e.target.value })}
            />
          </div>
          
          <Tabs defaultValue="query">
            <TabsList className="w-full">
              <TabsTrigger value="query" className="flex-1">Query</TabsTrigger>
              <TabsTrigger value="viz" className="flex-1">Visualization</TabsTrigger>
            </TabsList>
            
            <TabsContent value="query">
              <QueryConfigEditor
                config={config.query_config}
                onChange={(qc) => setConfig({ ...config, query_config: qc })}
              />
            </TabsContent>
            
            <TabsContent value="viz">
              <VizConfigEditor
                type={config.type}
                config={config.viz_config}
                onChange={(vc) => setConfig({ ...config, viz_config: vc })}
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>
      
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t bg-card">
        <div className="flex gap-2">
          <Button variant="outline" onClick={onClose} className="flex-1">
            Cancel
          </Button>
          <Button onClick={() => mutation.mutate(config)} className="flex-1">
            Save
          </Button>
        </div>
      </div>
    </div>
  )
}
```

### Query Configuration Editor

```tsx
// src/features/dashboards/components/config/QueryConfigEditor.tsx
import { useQuery } from '@tanstack/react-query'
import { MultiSelect } from '@/components/ui/multi-select'
import { FilterBuilder } from './FilterBuilder'
import { api } from '@/lib/api'

export function QueryConfigEditor({ config, onChange }) {
  const { data: models } = useQuery({
    queryKey: ['semantic-models'],
    queryFn: () => api.get('/semantic/models').then(r => r.data),
  })
  
  const allDimensions = models?.flatMap(m => m.dimensions) || []
  const allMeasures = models?.flatMap(m => m.measures) || []
  
  return (
    <div className="space-y-4">
      <div>
        <label className="text-sm font-medium">Dimensions</label>
        <MultiSelect
          options={allDimensions.map(d => ({ value: d.name, label: d.label }))}
          value={config.dimensions}
          onChange={(dims) => onChange({ ...config, dimensions: dims })}
          placeholder="Select dimensions..."
        />
      </div>
      
      <div>
        <label className="text-sm font-medium">Measures</label>
        <MultiSelect
          options={allMeasures.map(m => ({ value: m.name, label: m.label }))}
          value={config.measures}
          onChange={(measures) => onChange({ ...config, measures })}
          placeholder="Select measures..."
        />
      </div>
      
      <div>
        <label className="text-sm font-medium">Filters</label>
        <FilterBuilder
          filters={config.filters || []}
          dimensions={allDimensions}
          onChange={(filters) => onChange({ ...config, filters })}
        />
      </div>
      
      <div>
        <label className="text-sm font-medium">Limit</label>
        <Input
          type="number"
          value={config.limit || 100}
          onChange={(e) => onChange({ ...config, limit: parseInt(e.target.value) })}
        />
      </div>
    </div>
  )
}
```

## Expected Output

```
frontend/src/features/dashboards/
├── components/
│   ├── DashboardToolbar.tsx
│   ├── WidgetRenderer.tsx
│   ├── WidgetConfigPanel.tsx
│   ├── AddWidgetDialog.tsx
│   ├── config/
│   │   ├── QueryConfigEditor.tsx
│   │   ├── VizConfigEditor.tsx
│   │   └── FilterBuilder.tsx
│   └── widgets/
│       ├── MetricCard.tsx
│       ├── DataTable.tsx
│       ├── ChartWrapper.tsx
│       └── index.ts
├── pages/
│   ├── DashboardsListPage.tsx
│   ├── DashboardBuilderPage.tsx
│   └── DashboardViewPage.tsx
├── hooks/
│   └── useDashboards.ts
└── index.ts
```

## Acceptance Criteria

- [ ] Drag-and-drop widget placement works
- [ ] Widget resizing works
- [ ] Layout persists on save
- [ ] Widget data loads correctly
- [ ] Chart visualizations render
- [ ] Configuration panel updates widgets
- [ ] Auto-refresh works
- [ ] Responsive on different screen sizes

## Reference Documents

- [Dashboard API](./024-dashboard-api.md)
- [React Components Skill](../skills/react-components/SKILL.md)
