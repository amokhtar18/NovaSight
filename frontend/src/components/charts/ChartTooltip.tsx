/**
 * ChartTooltip Component
 * 
 * Custom tooltip for Recharts visualizations.
 */

import React from 'react';
import { TooltipProps } from 'recharts';

interface ChartTooltipProps extends TooltipProps<number, string> {
  className?: string;
}

export const ChartTooltip: React.FC<ChartTooltipProps> = ({
  active,
  payload,
  label,
  className = '',
}) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div
      className={`bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 ${className}`}
    >
      {label && (
        <p className="text-sm font-medium text-gray-900 dark:text-white mb-2 border-b border-gray-100 dark:border-gray-700 pb-2">
          {label}
        </p>
      )}
      <div className="space-y-1">
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-xs text-gray-600 dark:text-gray-400">
                {entry.name || entry.dataKey}
              </span>
            </div>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {formatValue(entry.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

function formatValue(value: number | string | undefined): string {
  if (value === undefined || value === null) return '-';
  if (typeof value === 'string') return value;
  
  // Format large numbers
  if (Math.abs(value) >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }
  
  // Format decimals
  if (Number.isInteger(value)) {
    return value.toLocaleString();
  }
  return value.toFixed(2);
}

export default ChartTooltip;
