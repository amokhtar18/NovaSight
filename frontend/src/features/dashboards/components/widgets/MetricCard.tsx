/**
 * Metric Card Widget
 */

import { ArrowUp, ArrowDown, Minus } from 'lucide-react'
import type { VizConfig } from '@/types/dashboard'

interface MetricCardProps {
  data: any[]
  config: VizConfig
}

export function MetricCard({ data, config }: MetricCardProps) {
  if (!data || data.length === 0) {
    return <div className="flex items-center justify-center h-full text-muted-foreground">No data</div>
  }
  
  const value = data[0]?.[config.metric || 'value'] || 0
  const comparison = config.comparison
  
  let changePercent = 0
  let changeDirection: 'up' | 'down' | 'neutral' = 'neutral'
  
  if (comparison) {
    const previousValue = data[0]?.previous_value || 0
    if (previousValue > 0) {
      changePercent = ((value - previousValue) / previousValue) * 100
      changeDirection = changePercent > 0 ? 'up' : changePercent < 0 ? 'down' : 'neutral'
    }
  }
  
  const formatValue = (val: number) => {
    if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`
    if (val >= 1000) return `${(val / 1000).toFixed(1)}K`
    return val.toFixed(0)
  }
  
  return (
    <div className="flex flex-col justify-center items-center h-full p-4">
      <div className="text-4xl font-bold text-foreground mb-2">
        {formatValue(value)}
      </div>
      
      {comparison && (
        <div className={`flex items-center gap-1 text-sm ${
          changeDirection === 'up' ? 'text-green-600' :
          changeDirection === 'down' ? 'text-red-600' :
          'text-muted-foreground'
        }`}>
          {changeDirection === 'up' && <ArrowUp className="h-4 w-4" />}
          {changeDirection === 'down' && <ArrowDown className="h-4 w-4" />}
          {changeDirection === 'neutral' && <Minus className="h-4 w-4" />}
          <span>{Math.abs(changePercent).toFixed(1)}%</span>
          <span className="text-muted-foreground ml-1">
            vs {comparison.type.replace('_', ' ')}
          </span>
        </div>
      )}
    </div>
  )
}
