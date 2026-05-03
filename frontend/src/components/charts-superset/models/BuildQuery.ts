import type { QueryFormData } from './ChartProps';

/** A NovaSight query payload (subset of Superset's QueryContext.queries[]). */
export interface QueryObject {
  metrics?: string[];
  groupby?: string[];
  columns?: string[];
  filters?: Array<{ col: string; op: string; val: unknown }>;
  orderby?: Array<[string, boolean]>;
  row_limit?: number;
  time_range?: string;
  granularity?: string;
  /** Free-form post-processing pipeline (placeholder). */
  post_processing?: Array<Record<string, unknown>>;
  /** Free-form extras for plugin-specific knobs. */
  extras?: Record<string, unknown>;
}

export interface QueryContext {
  datasource?: { id: string; type: string };
  form_data: QueryFormData;
  queries: QueryObject[];
  result_format?: 'json' | 'csv';
  result_type?: 'full' | 'query' | 'samples' | 'results';
}

/** A `buildQuery` function maps form-data → backend query context. */
export type BuildQuery<F extends QueryFormData = QueryFormData> = (
  formData: F,
) => QueryContext;
