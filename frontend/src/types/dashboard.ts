/**
 * Dashboard and Widget types
 */

export interface Dashboard {
  id: string
  name: string
  description?: string
  tenant_id: string
  created_by: string
  created_at: string
  updated_at: string
  is_public: boolean
  auto_refresh: boolean
  refresh_interval: number
  widgets: Widget[]
  shared_with?: DashboardShare[]
}

export interface Widget {
  id: string
  dashboard_id: string
  name: string
  type: WidgetType
  query_config: QueryConfig
  viz_config: VizConfig
  grid_position: GridPosition
  created_at: string
  updated_at: string
}

export type WidgetType = 
  | 'metric_card'
  | 'bar_chart'
  | 'line_chart'
  | 'pie_chart'
  | 'area_chart'
  | 'table'
  | 'scatter_chart'

export interface QueryConfig {
  dimensions: string[]
  measures: string[]
  filters?: Filter[]
  limit?: number
  order_by?: OrderBy[]
}

export interface Filter {
  field: string
  operator: FilterOperator
  value: any
}

export type FilterOperator = 
  | 'eq' 
  | 'ne' 
  | 'gt' 
  | 'gte' 
  | 'lt' 
  | 'lte' 
  | 'in' 
  | 'not_in'
  | 'contains'
  | 'starts_with'
  | 'ends_with'

export interface OrderBy {
  field: string
  direction: 'asc' | 'desc'
}

export interface VizConfig {
  // Chart-specific configurations
  xAxis?: string
  yAxis?: string | string[]
  colorBy?: string
  columns?: TableColumn[]
  
  // Metric card
  metric?: string
  comparison?: ComparisonConfig
  
  // Chart styling
  colors?: string[]
  showLegend?: boolean
  showGrid?: boolean
  stacked?: boolean
}

export interface TableColumn {
  field: string
  label: string
  type: 'string' | 'number' | 'date' | 'boolean'
  format?: string
}

export interface ComparisonConfig {
  type: 'previous_period' | 'previous_year' | 'target'
  value?: number
}

export interface GridPosition {
  x: number
  y: number
  w: number
  h: number
  minW?: number
  minH?: number
  maxW?: number
  maxH?: number
}

export interface DashboardShare {
  id: string
  dashboard_id: string
  user_id: string
  permission: 'view' | 'edit'
  created_at: string
}

export interface WidgetData {
  data: any[]
  metadata?: {
    execution_time: number
    row_count: number
  }
}
