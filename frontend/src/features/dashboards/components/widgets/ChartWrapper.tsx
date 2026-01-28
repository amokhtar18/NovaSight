/**
 * Chart Wrapper Component
 */

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  AreaChart,
  Area,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import type { VizConfig, WidgetType } from '@/types/dashboard'

interface ChartWrapperProps {
  type: WidgetType
  data: any[]
  config: VizConfig
}

const DEFAULT_COLORS = [
  '#3b82f6', // blue
  '#10b981', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
]

export function ChartWrapper({ type, data, config }: ChartWrapperProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        No data available
      </div>
    )
  }
  
  const colors = config.colors || DEFAULT_COLORS
  const showLegend = config.showLegend !== false
  const showGrid = config.showGrid !== false
  
  const commonProps = {
    data,
    margin: { top: 5, right: 20, left: 0, bottom: 5 },
  }
  
  const renderChart = () => {
    if (type === 'bar_chart') {
      return (
        <BarChart {...commonProps}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" />}
          <XAxis dataKey={config.xAxis} />
          <YAxis />
          <Tooltip />
          {showLegend && <Legend />}
          {Array.isArray(config.yAxis) ? (
            config.yAxis.map((key, idx) => (
              <Bar key={key} dataKey={key} fill={colors[idx % colors.length]} />
            ))
          ) : (
            <Bar dataKey={config.yAxis as string || 'value'} fill={colors[0]} />
          )}
        </BarChart>
      )
    }
    
    if (type === 'line_chart') {
      return (
        <LineChart {...commonProps}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" />}
          <XAxis dataKey={config.xAxis} />
          <YAxis />
          <Tooltip />
          {showLegend && <Legend />}
          {Array.isArray(config.yAxis) ? (
            config.yAxis.map((key, idx) => (
              <Line 
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[idx % colors.length]}
                strokeWidth={2}
              />
            ))
          ) : (
            <Line 
              type="monotone"
              dataKey={config.yAxis as string || 'value'}
              stroke={colors[0]}
              strokeWidth={2}
            />
          )}
        </LineChart>
      )
    }
    
    if (type === 'area_chart') {
      return (
        <AreaChart {...commonProps}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" />}
          <XAxis dataKey={config.xAxis} />
          <YAxis />
          <Tooltip />
          {showLegend && <Legend />}
          {Array.isArray(config.yAxis) ? (
            config.yAxis.map((key, idx) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                fill={colors[idx % colors.length]}
                stroke={colors[idx % colors.length]}
                stackId={config.stacked ? '1' : undefined}
              />
            ))
          ) : (
            <Area
              type="monotone"
              dataKey={config.yAxis as string || 'value'}
              fill={colors[0]}
              stroke={colors[0]}
            />
          )}
        </AreaChart>
      )
    }
    
    if (type === 'pie_chart') {
      return (
        <PieChart>
          <Pie
            data={data}
            dataKey={config.yAxis as string}
            nameKey={config.xAxis}
            cx="50%"
            cy="50%"
            outerRadius={80}
            label
          >
            {data.map((_entry, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
          <Tooltip />
          {showLegend && <Legend />}
        </PieChart>
      )
    }
    
    if (type === 'scatter_chart') {
      return (
        <ScatterChart {...commonProps}>
          {showGrid && <CartesianGrid strokeDasharray="3 3" />}
          <XAxis dataKey={config.xAxis} type="number" />
          <YAxis dataKey={config.yAxis as string} type="number" />
          <Tooltip cursor={{ strokeDasharray: '3 3' }} />
          {showLegend && <Legend />}
          <Scatter data={data} fill={colors[0]} />
        </ScatterChart>
      )
    }
    
    return null
  }
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      {renderChart() || <div>Unsupported chart type</div>}
    </ResponsiveContainer>
  )
}
