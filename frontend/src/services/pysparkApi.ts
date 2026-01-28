/**
 * PySpark Apps API Service
 * 
 * API client for PySpark application management.
 */

import { apiClient } from './api'
import type {
  PySparkApp,
  PySparkAppWithCode,
  PySparkAppCreate,
  PySparkAppUpdate,
  PySparkAppsListResponse,
  PySparkCodePreview,
  PySparkCodeResponse,
  QueryValidationRequest,
  QueryValidationResponse,
} from '@/types/pyspark'

const BASE_URL = '/api/v1/pyspark-apps'

export interface ListPySparkAppsParams {
  page?: number
  per_page?: number
  status?: string
  connection_id?: string
  search?: string
}

/**
 * List all PySpark apps for the current tenant
 */
export async function listPySparkApps(
  params: ListPySparkAppsParams = {}
): Promise<PySparkAppsListResponse> {
  const searchParams = new URLSearchParams()
  
  if (params.page) searchParams.set('page', String(params.page))
  if (params.per_page) searchParams.set('per_page', String(params.per_page))
  if (params.status) searchParams.set('status', params.status)
  if (params.connection_id) searchParams.set('connection_id', params.connection_id)
  if (params.search) searchParams.set('search', params.search)
  
  const queryString = searchParams.toString()
  const url = queryString ? `${BASE_URL}?${queryString}` : BASE_URL
  
  return apiClient.get<PySparkAppsListResponse>(url)
}

/**
 * Get a single PySpark app by ID
 */
export async function getPySparkApp(
  appId: string,
  includeCode: boolean = false
): Promise<PySparkAppWithCode> {
  const url = includeCode 
    ? `${BASE_URL}/${appId}?include_code=true`
    : `${BASE_URL}/${appId}`
  
  return apiClient.get<PySparkAppWithCode>(url)
}

/**
 * Create a new PySpark app
 */
export async function createPySparkApp(
  data: PySparkAppCreate
): Promise<PySparkApp> {
  return apiClient.post<PySparkApp>(BASE_URL, data)
}

/**
 * Update an existing PySpark app
 */
export async function updatePySparkApp(
  appId: string,
  data: PySparkAppUpdate
): Promise<PySparkApp> {
  return apiClient.put<PySparkApp>(`${BASE_URL}/${appId}`, data)
}

/**
 * Delete a PySpark app
 */
export async function deletePySparkApp(
  appId: string
): Promise<{ message: string }> {
  return apiClient.delete<{ message: string }>(`${BASE_URL}/${appId}`)
}

/**
 * Generate PySpark code for an app
 */
export async function generatePySparkCode(
  appId: string
): Promise<PySparkCodeResponse> {
  return apiClient.post<PySparkCodeResponse>(`${BASE_URL}/${appId}/generate`, {})
}

/**
 * Get previously generated code for an app
 */
export async function getPySparkCode(
  appId: string
): Promise<{
  code: string
  code_hash: string
  template_version: string
  generated_at: string
}> {
  return apiClient.get(`${BASE_URL}/${appId}/code`)
}

/**
 * Preview PySpark code without saving
 */
export async function previewPySparkCode(
  data: PySparkCodePreview
): Promise<PySparkCodeResponse> {
  return apiClient.post<PySparkCodeResponse>(`${BASE_URL}/preview`, data)
}

/**
 * Validate a SQL query and get column metadata
 */
export async function validateQuery(
  data: QueryValidationRequest
): Promise<QueryValidationResponse> {
  return apiClient.post<QueryValidationResponse>(`${BASE_URL}/validate-query`, data)
}

// Export all functions as a namespace
export const pysparkApi = {
  list: listPySparkApps,
  get: getPySparkApp,
  create: createPySparkApp,
  update: updatePySparkApp,
  delete: deletePySparkApp,
  generateCode: generatePySparkCode,
  getCode: getPySparkCode,
  previewCode: previewPySparkCode,
  validateQuery,
}

export default pysparkApi
