/**
 * Chart type definitions
 */

export type ChartType = 
  | 'bar'
  | 'line'
  | 'pie'
  | 'area'
  | 'scatter'
  | 'donut'
  | 'metric'
  | 'table'
  | 'heatmap'
  | 'gauge'
  | 'treemap'
  | 'funnel';

export type ChartSourceType = 'semantic_model' | 'sql_query';

export interface ChartDataColumn {
  name: string;
  type: 'string' | 'number' | 'datetime' | 'boolean';
  label?: string;
}

export interface ChartData {
  data: Record<string, unknown>[];
  columns: ChartDataColumn[];
  rowCount: number;
  executionTimeMs?: number;
  cached?: boolean;
  cacheExpiresAt?: string;
}

export interface ChartVizConfig {
  title?: string;
  subtitle?: string;
  colors?: string[];
  showLegend?: boolean;
  legendPosition?: 'top' | 'bottom' | 'left' | 'right';
  xAxisLabel?: string;
  yAxisLabel?: string;
  showDataLabels?: boolean;
  stacked?: boolean;
  curved?: boolean;
  showGrid?: boolean;
  animate?: boolean;
  // Pie/Donut specific
  innerRadius?: number;
  // Metric card specific
  prefix?: string;
  suffix?: string;
  format?: 'currency' | 'percentage' | 'number' | 'compact';
  // Table specific
  pageSize?: number;
}

export interface ChartQueryConfig {
  dimensions: string[];
  measures: string[];
  filters?: ChartFilter[];
  orderBy?: ChartOrderBy[];
  limit?: number;
  timeDimension?: string;
  dateRange?: {
    from?: string;
    to?: string;
    preset?: string;
  };
}

export interface ChartFilter {
  field: string;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'not_in' | 'like' | 'between';
  value?: unknown;
  values?: unknown[];
}

export interface ChartOrderBy {
  field: string;
  direction: 'asc' | 'desc';
}

export interface ChartConfig {
  id?: string;
  name: string;
  description?: string;
  chartType: ChartType;
  sourceType: ChartSourceType;
  semanticModelId?: string;
  sqlQuery?: string;
  queryConfig: ChartQueryConfig;
  vizConfig: ChartVizConfig;
  folderId?: string;
  tags?: string[];
  isPublic?: boolean;
}

export interface Chart {
  id: string;
  name: string;
  description?: string;
  chartType: ChartType;
  sourceType: ChartSourceType;
  semanticModelId?: string;
  queryConfig: ChartQueryConfig;
  vizConfig: ChartVizConfig;
  folderId?: string;
  tags: string[];
  isPublic: boolean;
  createdBy: string;
  tenantId: string;
  createdAt: string;
  updatedAt?: string;
}

export interface ChartFolder {
  id: string;
  name: string;
  description?: string;
  parentId?: string;
  tenantId: string;
  createdBy: string;
  createdAt: string;
  chartCount: number;
  childrenCount: number;
}

// Default colors palette
export const DEFAULT_CHART_COLORS = [
  '#3B82F6', // Blue
  '#10B981', // Emerald
  '#F59E0B', // Amber
  '#EF4444', // Red
  '#8B5CF6', // Violet
  '#06B6D4', // Cyan
  '#F97316', // Orange
  '#84CC16', // Lime
  '#EC4899', // Pink
  '#6366F1', // Indigo
];
