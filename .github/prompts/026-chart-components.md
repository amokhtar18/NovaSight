# 026 - Chart Components

## Metadata

```yaml
prompt_id: "026"
phase: 4
agent: "@dashboard"
model: "sonnet 4.5"
priority: P0
estimated_effort: "4 days"
dependencies: ["025"]
```

## Objective

Implement reusable chart components using Recharts with consistent styling.

## Task Description

Create a library of chart components for dashboards with unified theming and interactions.

## Requirements

### Chart Wrapper Component

```tsx
// src/features/dashboards/components/widgets/ChartWrapper.tsx
import { useMemo } from 'react'
import {
  ResponsiveContainer,
  BarChart, Bar,
  LineChart, Line,
  AreaChart, Area,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts'
import { useTheme } from '@/hooks/useTheme'

const COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
  '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1'
]

interface ChartWrapperProps {
  type: 'bar_chart' | 'line_chart' | 'area_chart' | 'pie_chart'
  data: any[]
  config: {
    xAxisKey?: string
    yAxisKeys?: string[]
    colors?: string[]
    showLegend?: boolean
    showGrid?: boolean
    stacked?: boolean
    xAxisLabel?: string
    yAxisLabel?: string
  }
}

export function ChartWrapper({ type, data, config }: ChartWrapperProps) {
  const { theme } = useTheme()
  const colors = config.colors || COLORS
  
  const commonProps = {
    data,
    margin: { top: 10, right: 30, left: 0, bottom: 0 },
  }
  
  const axisProps = {
    stroke: theme === 'dark' ? '#6B7280' : '#9CA3AF',
    fontSize: 12,
  }
  
  const renderChart = () => {
    switch (type) {
      case 'bar_chart':
        return (
          <BarChart {...commonProps}>
            {config.showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis 
              dataKey={config.xAxisKey} 
              {...axisProps}
              label={config.xAxisLabel ? { value: config.xAxisLabel, position: 'bottom' } : undefined}
            />
            <YAxis 
              {...axisProps}
              label={config.yAxisLabel ? { value: config.yAxisLabel, angle: -90, position: 'left' } : undefined}
            />
            <Tooltip content={<CustomTooltip />} />
            {config.showLegend && <Legend />}
            {config.yAxisKeys?.map((key, index) => (
              <Bar 
                key={key}
                dataKey={key}
                fill={colors[index % colors.length]}
                stackId={config.stacked ? 'stack' : undefined}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        )
      
      case 'line_chart':
        return (
          <LineChart {...commonProps}>
            {config.showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey={config.xAxisKey} {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip content={<CustomTooltip />} />
            {config.showLegend && <Legend />}
            {config.yAxisKeys?.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        )
      
      case 'area_chart':
        return (
          <AreaChart {...commonProps}>
            {config.showGrid && <CartesianGrid strokeDasharray="3 3" />}
            <XAxis dataKey={config.xAxisKey} {...axisProps} />
            <YAxis {...axisProps} />
            <Tooltip content={<CustomTooltip />} />
            {config.showLegend && <Legend />}
            {config.yAxisKeys?.map((key, index) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                fill={colors[index % colors.length]}
                fillOpacity={0.3}
                stackId={config.stacked ? 'stack' : undefined}
              />
            ))}
          </AreaChart>
        )
      
      case 'pie_chart':
        return (
          <PieChart>
            <Pie
              data={data}
              dataKey={config.yAxisKeys?.[0] || 'value'}
              nameKey={config.xAxisKey || 'name'}
              cx="50%"
              cy="50%"
              outerRadius={80}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            >
              {data.map((_, index) => (
                <Cell key={index} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            <Tooltip />
            {config.showLegend && <Legend />}
          </PieChart>
        )
    }
  }
  
  return (
    <ResponsiveContainer width="100%" height="100%">
      {renderChart()}
    </ResponsiveContainer>
  )
}
```

### Custom Tooltip

```tsx
// src/features/dashboards/components/widgets/CustomTooltip.tsx
import { Card } from '@/components/ui/card'
import { formatNumber, formatCurrency, formatPercent } from '@/lib/formatters'

export function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  
  return (
    <Card className="p-3 shadow-lg">
      <p className="font-medium mb-2">{label}</p>
      {payload.map((item, index) => (
        <div key={index} className="flex items-center gap-2 text-sm">
          <span 
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: item.color }}
          />
          <span className="text-muted-foreground">{item.name}:</span>
          <span className="font-medium">{formatValue(item.value, item.dataKey)}</span>
        </div>
      ))}
    </Card>
  )
}

function formatValue(value: number, key: string) {
  if (key.includes('percent') || key.includes('rate')) {
    return formatPercent(value)
  }
  if (key.includes('revenue') || key.includes('sales') || key.includes('amount')) {
    return formatCurrency(value)
  }
  return formatNumber(value)
}
```

### Metric Card Component

```tsx
// src/features/dashboards/components/widgets/MetricCard.tsx
import { ArrowUpIcon, ArrowDownIcon } from 'lucide-react'
import { formatNumber, formatCurrency, formatPercent } from '@/lib/formatters'

interface MetricCardProps {
  data: {
    value: number
    previousValue?: number
    label?: string
  }
  config: {
    format?: 'number' | 'currency' | 'percent'
    showChange?: boolean
    changeFormat?: 'percent' | 'absolute'
    positiveIsGood?: boolean
  }
}

export function MetricCard({ data, config }: MetricCardProps) {
  const formattedValue = formatMetricValue(data.value, config.format)
  
  const change = data.previousValue 
    ? ((data.value - data.previousValue) / data.previousValue) * 100
    : null
  
  const isPositive = change !== null && change > 0
  const isGood = config.positiveIsGood !== false ? isPositive : !isPositive
  
  return (
    <div className="flex flex-col justify-center h-full">
      {data.label && (
        <p className="text-sm text-muted-foreground mb-1">{data.label}</p>
      )}
      
      <p className="text-3xl font-bold">{formattedValue}</p>
      
      {config.showChange && change !== null && (
        <div className={`flex items-center gap-1 mt-2 text-sm ${
          isGood ? 'text-green-600' : 'text-red-600'
        }`}>
          {isPositive ? (
            <ArrowUpIcon className="h-4 w-4" />
          ) : (
            <ArrowDownIcon className="h-4 w-4" />
          )}
          <span>
            {config.changeFormat === 'absolute'
              ? formatNumber(Math.abs(data.value - data.previousValue))
              : formatPercent(Math.abs(change) / 100)}
          </span>
          <span className="text-muted-foreground">vs previous</span>
        </div>
      )}
    </div>
  )
}

function formatMetricValue(value: number, format?: string) {
  switch (format) {
    case 'currency':
      return formatCurrency(value)
    case 'percent':
      return formatPercent(value)
    default:
      return formatNumber(value)
  }
}
```

### Data Table Component

```tsx
// src/features/dashboards/components/widgets/DataTable.tsx
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { formatValue } from '@/lib/formatters'

interface DataTableProps {
  data: Record<string, any>[]
  columns: {
    key: string
    label: string
    format?: 'number' | 'currency' | 'percent' | 'date'
    align?: 'left' | 'center' | 'right'
  }[]
}

export function DataTable({ data, columns }: DataTableProps) {
  return (
    <div className="overflow-auto h-full">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((col) => (
              <TableHead 
                key={col.key}
                className={col.align === 'right' ? 'text-right' : ''}
              >
                {col.label}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row, rowIndex) => (
            <TableRow key={rowIndex}>
              {columns.map((col) => (
                <TableCell 
                  key={col.key}
                  className={col.align === 'right' ? 'text-right' : ''}
                >
                  {formatValue(row[col.key], col.format)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
```

## Expected Output

```
frontend/src/features/dashboards/components/widgets/
├── ChartWrapper.tsx
├── CustomTooltip.tsx
├── MetricCard.tsx
├── DataTable.tsx
├── ScatterPlot.tsx
├── Heatmap.tsx
└── index.ts

frontend/src/lib/
└── formatters.ts
```

## Acceptance Criteria

- [ ] Bar charts render correctly
- [ ] Line charts render correctly
- [ ] Area charts render correctly
- [ ] Pie charts render correctly
- [ ] Metric cards show values and changes
- [ ] Data tables paginate large datasets
- [ ] Tooltips show formatted values
- [ ] Theme colors applied correctly
- [ ] Charts responsive to container size
- [ ] Legend toggles series visibility

## Reference Documents

- [Dashboard Builder UI](./025-dashboard-builder-ui.md)
- [React Components Skill](../skills/react-components/SKILL.md)
