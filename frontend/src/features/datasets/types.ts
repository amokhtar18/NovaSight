/**
 * Dataset types — Superset-inspired Dataset model used by charts and dashboards.
 *
 * Mirrors the backend ``Dataset`` / ``DatasetColumn`` / ``DatasetMetric``
 * payloads exposed by ``/api/v1/datasets`` and ``/api/v1/datasets/sync-dbt``.
 */

export type DatasetKind = 'physical' | 'virtual';
export type DatasetSource = 'dbt' | 'manual' | 'sql_lab';
export type DbtMaterialization =
  | 'table'
  | 'view'
  | 'incremental'
  | 'materialized_view';

export interface DatasetColumn {
  id?: string;
  dataset_id?: string;
  column_name: string;
  verbose_name?: string | null;
  description?: string | null;
  expression?: string | null;
  type?: string | null;
  is_dttm: boolean;
  is_active: boolean;
  groupby: boolean;
  filterable: boolean;
  is_hidden: boolean;
  python_date_format?: string | null;
  column_order: number;
  extra?: Record<string, unknown>;
}

export interface DatasetMetric {
  id?: string;
  dataset_id?: string;
  metric_name: string;
  verbose_name?: string | null;
  description?: string | null;
  expression: string;
  metric_type?: string | null;
  d3format?: string | null;
  currency?: string | null;
  warning_text?: string | null;
  is_restricted: boolean;
  is_hidden: boolean;
  extra?: Record<string, unknown>;
}

export interface Dataset {
  id: string;
  name: string;
  description?: string | null;
  kind: DatasetKind;
  source: DatasetSource;
  database_name?: string | null;
  schema?: string | null;
  table_name?: string | null;
  sql?: string | null;
  dbt_unique_id?: string | null;
  dbt_materialization?: DbtMaterialization | null;
  dbt_meta?: Record<string, unknown>;
  main_dttm_col?: string | null;
  default_endpoint?: string | null;
  cache_timeout_seconds?: number | null;
  extra: Record<string, unknown>;
  is_managed: boolean;
  is_featured: boolean;
  tags: string[];
  owner_id?: string | null;
  tenant_id: string;
  last_synced_at?: string | null;
  created_at?: string;
  updated_at?: string;
  columns?: DatasetColumn[];
  metrics?: DatasetMetric[];
}

export interface DatasetListResponse {
  items: Dataset[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface DatasetCreateRequest {
  name: string;
  description?: string;
  kind?: DatasetKind;
  source?: DatasetSource;
  database_name?: string;
  schema?: string;
  table_name?: string;
  sql?: string;
  main_dttm_col?: string;
  default_endpoint?: string;
  cache_timeout_seconds?: number;
  extra?: Record<string, unknown>;
  tags?: string[];
  is_featured?: boolean;
  columns?: Partial<DatasetColumn>[];
  metrics?: Partial<DatasetMetric>[];
}

export type DatasetUpdateRequest = Partial<DatasetCreateRequest> & {
  _force?: boolean;
};

export interface DatasetPreview {
  sql: string;
  columns: { name: string; type: string }[];
  rows: unknown[][];
  row_count: number;
}

export interface DbtSyncResult {
  created: number;
  updated: number;
  deactivated: number;
  skipped: number;
  inspected: number;
  errors: string[];
}

// ---------------------------------------------------------------------------
// Mart tables (dataset creation source)
// ---------------------------------------------------------------------------

export interface MartTableColumn {
  name: string;
  type: string;
}

export interface MartTable {
  name: string;
  engine: string;
  total_rows?: number | null;
  columns: MartTableColumn[];
}

export interface MartTablesResponse {
  /** Mart database name — locked, the only DB datasets can be built from. */
  database: string;
  /** ``false`` when the mart DB hasn't been materialized yet (no dbt run). */
  exists: boolean;
  tables: MartTable[];
}
