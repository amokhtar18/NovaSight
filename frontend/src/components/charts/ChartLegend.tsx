/**
 * ChartLegend Component
 * 
 * Custom legend for charts.
 */

import React from 'react';
import { DEFAULT_CHART_COLORS } from './types';

interface LegendItem {
  name: string;
  color?: string;
  value?: number | string;
  active?: boolean;
}

interface ChartLegendProps {
  items: LegendItem[];
  position?: 'top' | 'bottom' | 'left' | 'right';
  onItemClick?: (item: LegendItem, index: number) => void;
  className?: string;
}

export const ChartLegend: React.FC<ChartLegendProps> = ({
  items,
  position = 'bottom',
  onItemClick,
  className = '',
}) => {
  const isVertical = position === 'left' || position === 'right';
  
  return (
    <div
      className={`
        flex gap-4 text-sm
        ${isVertical ? 'flex-col' : 'flex-wrap justify-center'}
        ${className}
      `}
    >
      {items.map((item, index) => (
        <button
          key={item.name}
          type="button"
          className={`
            flex items-center gap-2 transition-opacity
            ${onItemClick ? 'cursor-pointer hover:opacity-80' : 'cursor-default'}
            ${item.active === false ? 'opacity-50' : 'opacity-100'}
          `}
          onClick={() => onItemClick?.(item, index)}
        >
          <span
            className="w-3 h-3 rounded-full flex-shrink-0"
            style={{ backgroundColor: item.color || DEFAULT_CHART_COLORS[index % DEFAULT_CHART_COLORS.length] }}
          />
          <span className="text-gray-700 dark:text-gray-300">{item.name}</span>
          {item.value !== undefined && (
            <span className="text-gray-500 dark:text-gray-400 font-medium">
              ({formatLegendValue(item.value)})
            </span>
          )}
        </button>
      ))}
    </div>
  );
};

function formatLegendValue(value: number | string): string {
  if (typeof value === 'string') return value;
  
  if (Math.abs(value) >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  
  return value.toLocaleString();
}

export default ChartLegend;
