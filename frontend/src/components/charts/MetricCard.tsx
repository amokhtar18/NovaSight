/**
 * MetricCard Component
 * 
 * Displays a single metric value in a card format.
 */

import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface MetricCardProps {
  value: number | string;
  title?: string;
  subtitle?: string;
  prefix?: string;
  suffix?: string;
  format?: 'currency' | 'percentage' | 'number' | 'compact';
  trend?: {
    value: number;
    direction: 'up' | 'down' | 'neutral';
    label?: string;
  };
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  value,
  title,
  subtitle,
  prefix,
  suffix,
  format = 'number',
  trend,
  className = '',
  size = 'md',
}) => {
  const formattedValue = formatMetricValue(value, format);
  
  const sizeClasses = {
    sm: 'text-xl',
    md: 'text-3xl',
    lg: 'text-5xl',
  };

  const trendIcon = trend ? (
    trend.direction === 'up' ? (
      <TrendingUp className="h-4 w-4 text-green-500" />
    ) : trend.direction === 'down' ? (
      <TrendingDown className="h-4 w-4 text-red-500" />
    ) : (
      <Minus className="h-4 w-4 text-gray-400" />
    )
  ) : null;

  const trendColor = trend
    ? trend.direction === 'up'
      ? 'text-green-600 dark:text-green-400'
      : trend.direction === 'down'
      ? 'text-red-600 dark:text-red-400'
      : 'text-gray-500 dark:text-gray-400'
    : '';

  return (
    <div
      className={`
        flex flex-col items-center justify-center p-6 h-full
        bg-gradient-to-br from-gray-50 to-gray-100
        dark:from-gray-800 dark:to-gray-900
        rounded-lg
        ${className}
      `}
    >
      {title && (
        <p className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
          {title}
        </p>
      )}
      
      <div className={`font-bold text-gray-900 dark:text-white ${sizeClasses[size]}`}>
        {prefix && <span className="text-gray-500 dark:text-gray-400">{prefix}</span>}
        {formattedValue}
        {suffix && <span className="text-gray-500 dark:text-gray-400">{suffix}</span>}
      </div>
      
      {trend && (
        <div className={`flex items-center gap-1 mt-2 text-sm ${trendColor}`}>
          {trendIcon}
          <span>{trend.value > 0 ? '+' : ''}{trend.value}%</span>
          {trend.label && <span className="text-gray-500 dark:text-gray-400">vs {trend.label}</span>}
        </div>
      )}
      
      {subtitle && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          {subtitle}
        </p>
      )}
    </div>
  );
};

function formatMetricValue(
  value: number | string,
  format: 'currency' | 'percentage' | 'number' | 'compact'
): string {
  if (typeof value === 'string') return value;
  
  switch (format) {
    case 'currency':
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(value);
    
    case 'percentage':
      return `${(value * 100).toFixed(1)}%`;
    
    case 'compact':
      if (Math.abs(value) >= 1000000000) {
        return `${(value / 1000000000).toFixed(1)}B`;
      }
      if (Math.abs(value) >= 1000000) {
        return `${(value / 1000000).toFixed(1)}M`;
      }
      if (Math.abs(value) >= 1000) {
        return `${(value / 1000).toFixed(1)}K`;
      }
      return value.toFixed(0);
    
    case 'number':
    default:
      return value.toLocaleString();
  }
}

export default MetricCard;
