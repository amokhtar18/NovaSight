/**
 * Form-data and chart-props shapes — minimal, NovaSight-tailored versions of
 * the upstream Superset interfaces. Kept intentionally small so plugins can
 * grow into them without breaking changes.
 */
import type { ChartDataColumn } from '@/components/charts/types';

/** Free-form chart configuration (the "form_data" Superset persists). */
export interface QueryFormData {
  viz_type: string;
  datasource?: string;
  /** Free-form key/value config (controlPanel inputs). */
  [key: string]: unknown;
}

/** Standardised query response Superset's `transformProps` consumes. */
export interface ChartDataResponseResult<TRow = Record<string, unknown>> {
  data: TRow[];
  columns?: ChartDataColumn[];
  rowcount?: number;
  error?: string | null;
  cached?: boolean;
}

/** Input handed to a chart React component. */
export interface ChartProps<F extends QueryFormData = QueryFormData> {
  width: number;
  height: number;
  formData: F;
  queriesData: ChartDataResponseResult[];
  /** Datasource metadata, freshly resolved at render time. */
  datasource?: {
    columns?: ChartDataColumn[];
    metrics?: { name: string; label?: string }[];
  };
  /** Chart-level event handlers (selection, drill, etc.). */
  hooks?: Record<string, (...args: unknown[]) => void>;
}
