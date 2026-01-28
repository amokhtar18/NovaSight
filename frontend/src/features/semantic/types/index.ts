/**
 * Semantic Layer Type Definitions
 */

// Dimension types
export type DimensionType = 'categorical' | 'temporal' | 'numeric' | 'hierarchical'

// Aggregation types for measures
export type AggregationType = 
  | 'sum' 
  | 'count' 
  | 'count_distinct' 
  | 'avg' 
  | 'min' 
  | 'max' 
  | 'median' 
  | 'percentile'
  | 'raw'

// Model types
export type ModelType = 'fact' | 'dimension' | 'aggregate' | 'view'

// Relationship types
export type RelationshipType = 'one_to_one' | 'one_to_many' | 'many_to_one' | 'many_to_many'
export type JoinType = 'LEFT' | 'INNER' | 'RIGHT' | 'FULL'

// Format types for measures
export type FormatType = 'number' | 'currency' | 'percent'

// Semantic Model
export interface SemanticModel {
  id: string
  name: string
  label: string
  description?: string
  dbt_model: string
  model_type: ModelType
  target_schema?: string
  target_table?: string
  cache_enabled: boolean
  cache_ttl_seconds: number
  cache_ttl?: number // Alias for compatibility
  default_time_dimension?: string
  tags: string[]
  meta: Record<string, unknown>
  is_active: boolean
  dimensions?: Dimension[]
  measures?: Measure[]
  dimensions_count?: number
  measures_count?: number
  created_at: string
  updated_at: string
}

// Dimension
export interface Dimension {
  id: string
  semantic_model_id: string
  name: string
  label: string
  description?: string
  type: DimensionType
  expression: string
  data_type: string
  is_primary_key: boolean
  is_hidden: boolean
  is_filterable: boolean
  is_groupable: boolean
  hierarchy_name?: string
  hierarchy_level?: number
  parent_dimension_id?: string
  default_value?: string
  format_string?: string
  meta: Record<string, unknown>
  created_at: string
  updated_at: string
}

// Measure
export interface Measure {
  id: string
  semantic_model_id: string
  name: string
  label: string
  description?: string
  aggregation: AggregationType
  expression: string
  data_type: string
  format: FormatType
  format_string?: string
  decimal_places: number
  unit?: string
  is_hidden: boolean
  is_additive: boolean
  filters?: string
  window_function?: string
  meta: Record<string, unknown>
  created_at: string
  updated_at: string
}

// Relationship
export interface Relationship {
  id: string
  from_model_id: string
  to_model_id: string
  from_column: string
  to_column: string
  relationship_type: RelationshipType
  join_type: JoinType
  is_active: boolean
  from_model?: SemanticModel
  to_model?: SemanticModel
  created_at: string
  updated_at: string
}

// Create/Update DTOs
export interface CreateSemanticModelDto {
  name: string
  dbt_model: string
  label?: string
  description?: string
  model_type?: ModelType
  cache_enabled?: boolean
  cache_ttl_seconds?: number
  tags?: string[]
  meta?: Record<string, unknown>
}

export interface UpdateSemanticModelDto {
  label?: string
  description?: string
  model_type?: ModelType
  cache_enabled?: boolean
  cache_ttl_seconds?: number
  tags?: string[]
  meta?: Record<string, unknown>
  is_active?: boolean
}

export interface CreateDimensionDto {
  name: string
  expression: string
  label?: string
  description?: string
  type?: DimensionType
  data_type?: string
  is_primary_key?: boolean
  is_hidden?: boolean
  is_filterable?: boolean
  is_groupable?: boolean
  hierarchy_name?: string
  hierarchy_level?: number
  parent_dimension_id?: string
  default_value?: string
  format_string?: string
  meta?: Record<string, unknown>
}

export interface UpdateDimensionDto extends Partial<CreateDimensionDto> {}

export interface CreateMeasureDto {
  name: string
  aggregation: AggregationType
  expression: string
  label?: string
  description?: string
  format?: FormatType
  format_string?: string
  decimal_places?: number
  unit?: string
  is_hidden?: boolean
  is_additive?: boolean
  filters?: string
  window_function?: string
  meta?: Record<string, unknown>
}

export interface UpdateMeasureDto extends Partial<CreateMeasureDto> {}

export interface CreateRelationshipDto {
  from_model_id: string
  to_model_id: string
  from_column: string
  to_column: string
  relationship_type: RelationshipType
  join_type?: JoinType
}

// Column info from dbt/database
export interface Column {
  name: string
  data_type: string
  description?: string
  is_nullable: boolean
}

// Query types
export interface SemanticQuery {
  dimensions?: string[]
  measures: string[]
  filters?: QueryFilter[]
  order_by?: OrderBy[]
  limit?: number
  offset?: number
  time_dimension?: string
  date_from?: string
  date_to?: string
}

export interface QueryFilter {
  field: string
  operator: FilterOperator
  value: unknown
}

export type FilterOperator = 
  | 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte'
  | 'like' | 'not_like' | 'ilike'
  | 'in' | 'not_in'
  | 'is_null' | 'is_not_null'
  | 'between'

export interface OrderBy {
  field: string
  order: 'asc' | 'desc'
}

export interface QueryResult {
  columns: string[]
  rows: unknown[][]
  row_count: number
  execution_time_ms: number
  from_cache: boolean
  query?: string
}
