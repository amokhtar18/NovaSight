/**
 * Pipeline TypeScript Types
 */

export type SourceKind = 'sql' | 'file'

export type FileFormat = 'csv' | 'tsv' | 'xlsx' | 'xls' | 'parquet' | 'json' | 'jsonl'

export const FILE_FORMATS: FileFormat[] = ['csv', 'tsv', 'xlsx', 'xls', 'parquet', 'json', 'jsonl']

export interface FileUploadResult {
  object_key: string
  bucket: string
  size_bytes: number
  file_format: FileFormat
  original_filename: string
  sheets: string[]
  columns_preview: string[]
  rows_preview?: Array<Record<string, unknown>>
}

export type SourceType = 'table' | 'query'

export type WriteDisposition = 'append' | 'replace' | 'merge' | 'scd2'

export type IncrementalCursorType = 'none' | 'timestamp' | 'version'

export type PipelineStatus = 'draft' | 'active' | 'inactive' | 'error'

export interface ColumnConfig {
  name: string
  data_type: string
  include: boolean
  nullable: boolean
}

export interface PipelineFormData {
  name: string
  description?: string
  // Source kind discriminator
  sourceKind: SourceKind
  // SQL-source
  connectionId?: string
  sourceType: SourceType
  sourceSchema?: string
  sourceTable?: string
  sourceQuery?: string
  // File-source
  fileFormat?: FileFormat
  fileObjectKey?: string
  fileOptions?: Record<string, unknown>
  fileOriginalName?: string
  fileSizeBytes?: number
  // Common
  columnsConfig: ColumnConfig[]
  primaryKeyColumns: string[]
  incrementalCursorColumn?: string
  incrementalCursorType: IncrementalCursorType
  writeDisposition: WriteDisposition
  partitionColumns: string[]
  icebergNamespace?: string
  icebergTableName?: string
  options: Record<string, unknown>
}

export interface Pipeline {
  id: string
  tenant_id: string
  connection_id: string | null
  name: string
  description?: string
  status: PipelineStatus
  source_kind: SourceKind
  source_type: SourceType
  source_schema?: string
  source_table?: string
  source_query?: string
  file_format?: FileFormat | null
  file_object_key?: string | null
  file_options?: Record<string, unknown>
  columns_config: ColumnConfig[]
  primary_key_columns: string[]
  incremental_cursor_column?: string
  incremental_cursor_type: IncrementalCursorType
  write_disposition: WriteDisposition
  partition_columns: string[]
  iceberg_namespace?: string
  iceberg_table_name?: string
  options: Record<string, unknown>
  generated_at?: string
  template_name?: string
  template_version?: string
  last_run_at?: string
  last_run_status?: string
  last_run_rows?: number
  last_run_duration_ms?: number
  last_run_iceberg_snapshot_id?: string
  created_by: string
  created_at: string
  updated_at: string
  generated_code?: string
  generated_code_hash?: string
}

export interface PipelineListResponse {
  items: Pipeline[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface PipelinePreviewRequest {
  source_kind: SourceKind
  connection_id?: string
  source_type: SourceType
  source_schema?: string
  source_table?: string
  source_query?: string
  file_format?: FileFormat
  file_object_key?: string
  file_options?: Record<string, unknown>
  columns_config: ColumnConfig[]
  primary_key_columns: string[]
  incremental_cursor_column?: string
  incremental_cursor_type: IncrementalCursorType
  write_disposition: WriteDisposition
  partition_columns: string[]
  iceberg_table_name?: string
}

export interface PipelinePreviewResponse {
  code: string
  template_name: string
  template_version: string
  validation_errors: string[]
}

export interface PipelineRunResponse {
  pipeline_id: string
  run_id?: string
  status: string
  message: string
}

// Wizard step types
export type WizardStep = 'kind' | 'source' | 'columns' | 'target' | 'review'

export interface WizardState extends PipelineFormData {
  currentStep: WizardStep
  isValid: boolean
  errors: Record<string, string>
}

export const WRITE_DISPOSITION_OPTIONS = [
  { value: 'append', label: 'Append', description: 'Add new rows to existing data' },
  { value: 'replace', label: 'Replace', description: 'Drop and recreate the table each run' },
  { value: 'merge', label: 'Merge (Upsert)', description: 'Update existing rows, insert new ones' },
  { value: 'scd2', label: 'SCD Type 2', description: 'Track historical changes with validity dates' },
] as const

export const INCREMENTAL_TYPE_OPTIONS = [
  { value: 'none', label: 'Full Load', description: 'Load all data each run' },
  { value: 'timestamp', label: 'Timestamp Column', description: 'Incremental by timestamp' },
  { value: 'version', label: 'Version Column', description: 'Incremental by version number' },
] as const
