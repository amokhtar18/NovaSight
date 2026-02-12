/**
 * ChartRenderer Component
 * 
 * A universal chart rendering component that supports multiple chart types.
 * Uses Recharts for rendering visualizations.
 */

import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
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
} from 'recharts';
import { ChartType, ChartData, ChartVizConfig, DEFAULT_CHART_COLORS } from './types';
import { ChartTooltip } from './ChartTooltip';
import { MetricCard } from './MetricCard';
import { DataTable } from './DataTable';

interface ChartRendererProps {
  type: ChartType;
  data: ChartData;
  config: ChartVizConfig;
  dimensions?: string[];
  measures?: string[];
  width?: number | string;
  height?: number | string;
  className?: string;
  onDataPointClick?: (data: Record<string, unknown>) => void;
}

export const ChartRenderer: React.FC<ChartRendererProps> = ({
  type,
  data,
  config,
  dimensions = [],
  measures = [],
  width = '100%',
  height = 300,
  className = '',
  onDataPointClick,
}) => {
  const colors = config.colors || DEFAULT_CHART_COLORS;
  
  // Infer dimensions and measures from data if not provided
  const inferredConfig = useMemo(() => {
    if (dimensions.length === 0 && measures.length === 0 && data.columns.length > 0) {
      const dims: string[] = [];
      const meas: string[] = [];
      
      data.columns.forEach((col) => {
        if (col.type === 'number') {
          meas.push(col.name);
        } else {
          dims.push(col.name);
        }
      });
      
      return { dimensions: dims.slice(0, 1), measures: meas };
    }
    return { dimensions, measures };
  }, [data.columns, dimensions, measures]);

  const chartData = data.data;
  const xAxisKey = inferredConfig.dimensions[0] || '';
  const yAxisKeys = inferredConfig.measures;

  // Handle special chart types
  if (type === 'metric') {
    const value = chartData.length > 0 ? chartData[0][yAxisKeys[0]] : 0;
    return (
      <MetricCard
        value={value as number}
        title={config.title}
        subtitle={config.subtitle}
        prefix={config.prefix}
        suffix={config.suffix}
        format={config.format}
        className={className}
      />
    );
  }

  if (type === 'table') {
    return (
      <DataTable
        data={chartData}
        columns={data.columns}
        pageSize={config.pageSize || 10}
        title={config.title}
        className={className}
      />
    );
  }

  // Common chart props
  const commonProps = {
    data: chartData,
    margin: { top: 20, right: 30, left: 20, bottom: 5 },
  };

  const legendProps = config.showLegend !== false ? {
    verticalAlign: (config.legendPosition === 'top' ? 'top' : 'bottom') as 'top' | 'bottom',
    align: 'center' as 'center',
    wrapperStyle: { paddingTop: config.legendPosition === 'bottom' ? 20 : 0 },
  } : undefined;

  const renderChart = () => {
    switch (type) {
      case 'bar':
        return (
          <BarChart {...commonProps}>
            {config.showGrid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis 
              dataKey={xAxisKey} 
              label={config.xAxisLabel ? { value: config.xAxisLabel, position: 'bottom' } : undefined}
              tick={{ fontSize: 12 }}
              stroke="#9ca3af"
            />
            <YAxis 
              label={config.yAxisLabel ? { value: config.yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
              tick={{ fontSize: 12 }}
              stroke="#9ca3af"
            />
            <Tooltip content={<ChartTooltip />} />
            {legendProps && <Legend {...legendProps} />}
            {yAxisKeys.map((key, index) => (
              <Bar
                key={key}
                dataKey={key}
                fill={colors[index % colors.length]}
                stackId={config.stacked ? 'stack' : undefined}
                radius={[4, 4, 0, 0]}
                onClick={(data) => onDataPointClick?.(data)}
              />
            ))}
          </BarChart>
        );

      case 'line':
        return (
          <LineChart {...commonProps}>
            {config.showGrid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis 
              dataKey={xAxisKey}
              label={config.xAxisLabel ? { value: config.xAxisLabel, position: 'bottom' } : undefined}
              tick={{ fontSize: 12 }}
              stroke="#9ca3af"
            />
            <YAxis 
              label={config.yAxisLabel ? { value: config.yAxisLabel, angle: -90, position: 'insideLeft' } : undefined}
              tick={{ fontSize: 12 }}
              stroke="#9ca3af"
            />
            <Tooltip content={<ChartTooltip />} />
            {legendProps && <Legend {...legendProps} />}
            {yAxisKeys.map((key, index) => (
              <Line
                key={key}
                type={config.curved !== false ? 'monotone' : 'linear'}
                dataKey={key}
                stroke={colors[index % colors.length]}
                strokeWidth={2}
                dot={{ r: 4 }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        );

      case 'area':
        return (
          <AreaChart {...commonProps}>
            {config.showGrid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis 
              dataKey={xAxisKey}
              tick={{ fontSize: 12 }}
              stroke="#9ca3af"
            />
            <YAxis tick={{ fontSize: 12 }} stroke="#9ca3af" />
            <Tooltip content={<ChartTooltip />} />
            {legendProps && <Legend {...legendProps} />}
            {yAxisKeys.map((key, index) => (
              <Area
                key={key}
                type={config.curved !== false ? 'monotone' : 'linear'}
                dataKey={key}
                fill={colors[index % colors.length]}
                fillOpacity={0.3}
                stroke={colors[index % colors.length]}
                stackId={config.stacked ? 'stack' : undefined}
              />
            ))}
          </AreaChart>
        );

      case 'pie':
      case 'donut':
        const pieData = chartData.map((item, index) => ({
          name: String(item[xAxisKey]),
          value: Number(item[yAxisKeys[0]] || 0),
          fill: colors[index % colors.length],
        }));
        
        return (
          <PieChart>
            <Pie
              data={pieData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={type === 'donut' ? '60%' : 0}
              outerRadius="80%"
              paddingAngle={type === 'donut' ? 2 : 0}
              label={config.showDataLabels !== false}
              onClick={(_, index) => onDataPointClick?.(chartData[index])}
            >
              {pieData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip content={<ChartTooltip />} />
            {legendProps && <Legend {...legendProps} />}
          </PieChart>
        );

      case 'scatter':
        const xKey = inferredConfig.measures[0] || xAxisKey;
        const yKey = inferredConfig.measures[1] || inferredConfig.measures[0];
        
        return (
          <ScatterChart {...commonProps}>
            {config.showGrid !== false && <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />}
            <XAxis 
              dataKey={xKey} 
              name={xKey}
              tick={{ fontSize: 12 }}
              stroke="#9ca3af"
            />
            <YAxis 
              dataKey={yKey} 
              name={yKey}
              tick={{ fontSize: 12 }}
              stroke="#9ca3af"
            />
            <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3' }} />
            {legendProps && <Legend {...legendProps} />}
            <Scatter
              name={config.title || 'Data'}
              data={chartData}
              fill={colors[0]}
              onClick={(data) => onDataPointClick?.(data)}
            />
          </ScatterChart>
        );

      default:
        return (
          <div className="flex items-center justify-center h-full text-gray-500">
            Chart type "{type}" is not yet supported
          </div>
        );
    }
  };

  return (
    <div className={`chart-renderer ${className}`} style={{ width, height }}>
      {config.title && (
        <div className="mb-2">
          <h3 className="text-sm font-medium text-gray-900 dark:text-white">
            {config.title}
          </h3>
          {config.subtitle && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {config.subtitle}
            </p>
          )}
        </div>
      )}
      <ResponsiveContainer width="100%" height={config.title ? `calc(100% - 40px)` : '100%'}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
};

export default ChartRenderer;
