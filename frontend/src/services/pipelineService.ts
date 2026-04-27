/**
 * Pipeline API Service
 * 
 * API client for dlt pipeline management.
 */

import { apiClient } from './apiClient'
import type {
  Pipeline,
  PipelineListResponse,
  PipelineFormData,
  PipelinePreviewRequest,
  PipelinePreviewResponse,
  PipelineRunResponse,
  FileUploadResult,
} from '@/types/pipeline'

const PIPELINES_BASE = '/api/v1/pipelines'
const UPLOADS_BASE = '/api/v1/dlt/uploads'

export const pipelineService = {
  /**
   * List pipelines for the current tenant
   */
  async list(params?: {
    status?: string
    connection_id?: string
    search?: string
    page?: number
    per_page?: number
  }): Promise<PipelineListResponse> {
    const response = await apiClient.get<PipelineListResponse>(PIPELINES_BASE, { params })
    return response.data
  },

  /**
   * Get a single pipeline by ID
   */
  async get(id: string): Promise<Pipeline> {
    const response = await apiClient.get<Pipeline>(`${PIPELINES_BASE}/${id}`)
    return response.data
  },

  /**
   * Create a new pipeline
   */
  async create(data: PipelineFormData): Promise<Pipeline> {
    const isFile = data.sourceKind === 'file'
    const payload = {
      name: data.name,
      description: data.description,
      source_kind: data.sourceKind,
      // SQL-source
      connection_id: isFile ? null : data.connectionId,
      source_type: data.sourceType,
      source_schema: isFile ? null : data.sourceSchema,
      source_table: isFile ? null : data.sourceTable,
      source_query: isFile ? null : data.sourceQuery,
      // File-source
      file_format: isFile ? data.fileFormat : null,
      file_object_key: isFile ? data.fileObjectKey : null,
      file_options: isFile ? (data.fileOptions || {}) : {},
      // Common
      columns_config: data.columnsConfig,
      primary_key_columns: data.primaryKeyColumns,
      incremental_cursor_column: data.incrementalCursorColumn,
      incremental_cursor_type: data.incrementalCursorType,
      write_disposition: data.writeDisposition,
      partition_columns: data.partitionColumns,
      iceberg_namespace: data.icebergNamespace,
      iceberg_table_name: data.icebergTableName,
      options: data.options,
    }
    const response = await apiClient.post<Pipeline>(PIPELINES_BASE, payload)
    return response.data
  },

  /**
   * Update an existing pipeline
   */
  async update(id: string, data: Partial<PipelineFormData>): Promise<Pipeline> {
    const payload: Record<string, unknown> = {}
    
    if (data.name !== undefined) payload.name = data.name
    if (data.description !== undefined) payload.description = data.description
    if (data.sourceType !== undefined) payload.source_type = data.sourceType
    if (data.sourceSchema !== undefined) payload.source_schema = data.sourceSchema
    if (data.sourceTable !== undefined) payload.source_table = data.sourceTable
    if (data.sourceQuery !== undefined) payload.source_query = data.sourceQuery
    if (data.columnsConfig !== undefined) payload.columns_config = data.columnsConfig
    if (data.primaryKeyColumns !== undefined) payload.primary_key_columns = data.primaryKeyColumns
    if (data.incrementalCursorColumn !== undefined) payload.incremental_cursor_column = data.incrementalCursorColumn
    if (data.incrementalCursorType !== undefined) payload.incremental_cursor_type = data.incrementalCursorType
    if (data.writeDisposition !== undefined) payload.write_disposition = data.writeDisposition
    if (data.partitionColumns !== undefined) payload.partition_columns = data.partitionColumns
    if (data.icebergNamespace !== undefined) payload.iceberg_namespace = data.icebergNamespace
    if (data.icebergTableName !== undefined) payload.iceberg_table_name = data.icebergTableName
    if (data.options !== undefined) payload.options = data.options
    
    const response = await apiClient.put<Pipeline>(`${PIPELINES_BASE}/${id}`, payload)
    return response.data
  },

  /**
   * Delete a pipeline
   */
  async delete(id: string): Promise<void> {
    await apiClient.delete(`${PIPELINES_BASE}/${id}`)
  },

  /**
   * Preview generated code without saving
   */
  async previewCode(data: PipelinePreviewRequest): Promise<PipelinePreviewResponse> {
    const response = await apiClient.post<PipelinePreviewResponse>(
      `${PIPELINES_BASE}/preview`,
      data
    )
    return response.data
  },

  /**
   * Generate and save pipeline code
   */
  async generateCode(id: string): Promise<{ code: string }> {
    const response = await apiClient.post<{ code: string }>(
      `${PIPELINES_BASE}/${id}/generate`
    )
    return response.data
  },

  /**
   * Activate a pipeline
   */
  async activate(id: string): Promise<Pipeline> {
    const response = await apiClient.post<Pipeline>(`${PIPELINES_BASE}/${id}/activate`)
    return response.data
  },

  /**
   * Deactivate a pipeline
   */
  async deactivate(id: string): Promise<Pipeline> {
    const response = await apiClient.post<Pipeline>(`${PIPELINES_BASE}/${id}/deactivate`)
    return response.data
  },

  /**
   * Trigger a pipeline run
   */
  async run(id: string): Promise<PipelineRunResponse> {
    const response = await apiClient.post<PipelineRunResponse>(`${PIPELINES_BASE}/${id}/run`)
    return response.data
  },

  /**
   * Upload a flat file / spreadsheet to the tenant S3 bucket. The returned
   * ``object_key`` is what gets stored on a file-source pipeline.
   */
  async uploadFile(
    file: File,
    onProgress?: (percent: number) => void,
  ): Promise<FileUploadResult> {
    const form = new FormData()
    form.append('file', file)
    const response = await apiClient.post<FileUploadResult>(UPLOADS_BASE, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (evt) => {
        if (onProgress && evt.total) {
          onProgress(Math.round((evt.loaded * 100) / evt.total))
        }
      },
    })
    return response.data
  },

  /**
   * Delete a previously uploaded file by its object_key.
   */
  async deleteUpload(objectKey: string): Promise<void> {
    await apiClient.delete(`${UPLOADS_BASE}/${objectKey}`)
  },
}
