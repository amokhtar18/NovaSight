/**
 * PySpark App Types
 * 
 * TypeScript type definitions for PySpark application configuration.
 */

export type SourceType = 'table' | 'query'

export type WriteMode = 'append' | 'overwrite' | 'merge'

export type SCDType = 'none' | 'type1' | 'type2'

export type CDCType = 'none' | 'timestamp' | 'version' | 'hash'

export type PySparkAppStatus = 'draft' | 'active' | 'inactive' | 'error'

export interface ColumnConfig {
  name: string
  data_type: string
  include: boolean
  nullable: boolean
  comment?: string
}

export interface PySparkApp {
  id: string
  tenant_id: string
  connection_id: string
  name: string
  description?: string
  status: PySparkAppStatus
  
  // Source configuration
  source_type: SourceType
  source_schema?: string
  source_table?: string
  source_query?: string
  
  // Column configuration
  columns_config: ColumnConfig[]
  primary_key_columns: string[]
  
  // CDC configuration
  cdc_type: CDCType
  cdc_column?: string
  
  // Partition configuration
  partition_columns: string[]
  
  // SCD configuration
  scd_type: SCDType
  write_mode: WriteMode
  
  // Target configuration
  target_database?: string
  target_table?: string
  target_engine: string
  
  // Additional options
  options: Record<string, unknown>
  
  // Generated artifacts
  generated_at?: string
  template_version?: string
  
  // Execution stats
  last_run_at?: string
  last_run_status?: string
  last_run_rows?: number
  last_run_duration_ms?: number
  
  // Audit
  created_by: string
  created_at: string
  updated_at: string
}

export interface PySparkAppWithCode extends PySparkApp {
  generated_code?: string
  generated_code_hash?: string
}

export interface PySparkAppCreate {
  name: string
  connection_id: string
  description?: string
  
  source_type: SourceType
  source_schema?: string
  source_table?: string
  source_query?: string
  
  columns_config: ColumnConfig[]
  primary_key_columns: string[]
  
  cdc_type?: CDCType
  cdc_column?: string
  
  partition_columns?: string[]
  scd_type?: SCDType
  write_mode?: WriteMode
  
  target_database?: string
  target_table?: string
  target_engine?: string
  
  options?: Record<string, unknown>
}

export interface PySparkAppUpdate {
  name?: string
  description?: string
  status?: PySparkAppStatus
  
  source_type?: SourceType
  source_schema?: string
  source_table?: string
  source_query?: string
  
  columns_config?: ColumnConfig[]
  primary_key_columns?: string[]
  
  cdc_type?: CDCType
  cdc_column?: string
  
  partition_columns?: string[]
  scd_type?: SCDType
  write_mode?: WriteMode
  
  target_database?: string
  target_table?: string
  target_engine?: string
  
  options?: Record<string, unknown>
}

export interface PySparkCodePreview {
  connection_id: string
  source_type: SourceType
  source_schema?: string
  source_table?: string
  source_query?: string
  
  columns_config: ColumnConfig[]
  primary_key_columns: string[]
  
  cdc_type?: CDCType
  cdc_column?: string
  
  partition_columns?: string[]
  scd_type?: SCDType
  write_mode?: WriteMode
  
  target_database: string
  target_table: string
  target_engine?: string
  
  options?: Record<string, unknown>
}

export interface PySparkCodeResponse {
  code: string
  template_name: string
  template_version: string
  parameters_hash: string
  is_preview?: boolean
}

export interface PySparkAppsListResponse {
  apps: PySparkApp[]
  pagination: {
    page: number
    per_page: number
    total: number
    pages: number
    has_next: boolean
    has_prev: boolean
  }
}

export interface QueryValidationRequest {
  connection_id: string
  query: string
}

export interface QueryValidationResponse {
  valid: boolean
  message: string
  columns?: ColumnConfig[]
  estimated_rows?: number
}

// Wizard step types
export type PySparkWizardStep = 
  | 'source'
  | 'columns'
  | 'keys'
  | 'scd'
  | 'target'
  | 'preview'

export interface PySparkWizardState {
  currentStep: PySparkWizardStep
  
  // Step 1: Source
  connectionId: string
  sourceType: SourceType
  sourceSchema: string
  sourceTable: string
  sourceQuery: string
  
  // Step 2: Columns
  availableColumns: ColumnConfig[]
  selectedColumns: ColumnConfig[]
  
  // Step 3: Keys
  primaryKeyColumns: string[]
  cdcType: CDCType
  cdcColumn: string
  partitionColumns: string[]
  
  // Step 4: SCD
  scdType: SCDType
  writeMode: WriteMode
  
  // Step 5: Target
  targetDatabase: string
  targetTable: string
  targetEngine: string
  
  // App metadata
  name: string
  description: string
  
  // Options
  options: Record<string, unknown>
}

export const INITIAL_WIZARD_STATE: PySparkWizardState = {
  currentStep: 'source',
  
  connectionId: '',
  sourceType: 'table',
  sourceSchema: '',
  sourceTable: '',
  sourceQuery: '',
  
  availableColumns: [],
  selectedColumns: [],
  
  primaryKeyColumns: [],
  cdcType: 'none',
  cdcColumn: '',
  partitionColumns: [],
  
  scdType: 'none',
  writeMode: 'append',
  
  targetDatabase: '',
  targetTable: '',
  targetEngine: 'MergeTree',
  
  name: '',
  description: '',
  options: {},
}

// Helper type for step navigation
export interface WizardStepConfig {
  id: PySparkWizardStep
  title: string
  description: string
  isValid: (state: PySparkWizardState) => boolean
}

export const WIZARD_STEPS: WizardStepConfig[] = [
  {
    id: 'source',
    title: 'Data Source',
    description: 'Select connection and source table/query',
    isValid: (state) => {
      if (!state.connectionId) return false
      if (state.sourceType === 'table') {
        return !!state.sourceTable
      }
      return !!state.sourceQuery
    }
  },
  {
    id: 'columns',
    title: 'Columns',
    description: 'Select columns to extract',
    isValid: (state) => state.selectedColumns.length > 0
  },
  {
    id: 'keys',
    title: 'Keys & CDC',
    description: 'Define primary keys and change tracking',
    isValid: (state) => {
      // PK required for SCD or merge
      if (state.scdType !== 'none' || state.writeMode === 'merge') {
        return state.primaryKeyColumns.length > 0
      }
      return true
    }
  },
  {
    id: 'scd',
    title: 'SCD & Write Mode',
    description: 'Configure change tracking strategy',
    isValid: () => true
  },
  {
    id: 'target',
    title: 'Target',
    description: 'Define target database and table',
    isValid: (state) => !!state.targetDatabase && !!state.targetTable && !!state.name
  },
  {
    id: 'preview',
    title: 'Preview & Save',
    description: 'Review and generate code',
    isValid: () => true
  }
]
