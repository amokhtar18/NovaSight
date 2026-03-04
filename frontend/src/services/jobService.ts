/**
 * NovaSight Unified Job Service
 * ==============================
 *
 * Frontend API client for Dagster jobs with remote Spark execution.
 * Replaces separate DAG and PySpark orchestration services with a unified interface.
 */

import { apiClient } from './apiClient'

// =============================================================================
// Types
// =============================================================================

export interface Job {
  id: string
  dag_id: string
  job_name: string
  description?: string
  type: 'spark' | 'pipeline'
  status: 'draft' | 'active' | 'paused' | 'archived'
  schedule_type: 'cron' | 'preset' | 'manual'
  schedule_cron?: string
  schedule_preset?: string
  timezone: string
  tags: string[]
  created_at: string
  updated_at: string
  deployed_at?: string
  last_run?: JobRunSummary
}

export interface JobRunSummary {
  run_id: string
  status: string
  start_time?: string
  end_time?: string
}

export interface JobRun {
  run_id: string
  status: 'QUEUED' | 'NOT_STARTED' | 'STARTING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | 'CANCELED'
  start_time?: string
  end_time?: string
  stats?: {
    stepsSucceeded: number
    stepsFailed: number
    materializations: number
    expectations: number
  }
  step_stats?: StepStat[]
}

export interface StepStat {
  stepKey: string
  status: string
  startTime?: string
  endTime?: string
}

export interface JobLog {
  timestamp: string
  level: string
  message: string
  step?: string
}

export interface CreateJobRequest {
  pyspark_app_id: string
  schedule?: string
  spark_config?: Record<string, unknown>
  name?: string
  description?: string
  notifications?: {
    emails?: string[]
    on_failure?: boolean
    on_success?: boolean
  }
  retries?: number
  retry_delay_minutes?: number
}

export interface CreatePipelineRequest {
  pyspark_app_ids: string[]
  name: string
  description?: string
  schedule?: string
  parallel?: boolean
  spark_config?: Record<string, unknown>
}

export interface TriggerJobRequest {
  run_config?: Record<string, unknown>
  tags?: Record<string, string>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

// =============================================================================
// Job Service
// =============================================================================

class JobService {
  private baseUrl = '/api/v1/jobs'

  // ---------------------------------------------------------------------------
  // Job CRUD
  // ---------------------------------------------------------------------------

  async list(params?: {
    page?: number
    per_page?: number
    status?: string
    type?: 'spark' | 'pipeline'
  }): Promise<PaginatedResponse<Job>> {
    const response = await apiClient.get<{
      jobs: Job[]
      total: number
      page: number
      per_page: number
      pages: number
    }>(this.baseUrl, { params })

    return {
      items: response.data.jobs,
      total: response.data.total,
      page: response.data.page,
      per_page: response.data.per_page,
      pages: response.data.pages,
    }
  }

  async get(jobId: string): Promise<Job> {
    const response = await apiClient.get<{ job: Job }>(`${this.baseUrl}/${jobId}`)
    return response.data.job
  }

  async create(data: CreateJobRequest): Promise<Job> {
    const response = await apiClient.post<{ job: Job }>(this.baseUrl, data)
    return response.data.job
  }

  async createPipeline(data: CreatePipelineRequest): Promise<Job> {
    const response = await apiClient.post<{ job: Job }>(`${this.baseUrl}/pipeline`, data)
    return response.data.job
  }

  async update(jobId: string, data: Partial<CreateJobRequest>): Promise<Job> {
    const response = await apiClient.put<{ job: Job }>(`${this.baseUrl}/${jobId}`, data)
    return response.data.job
  }

  async delete(jobId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${jobId}`)
  }

  // ---------------------------------------------------------------------------
  // Job Execution
  // ---------------------------------------------------------------------------

  async trigger(
    jobId: string,
    request?: TriggerJobRequest
  ): Promise<{ success: boolean; run_id?: string; error?: string }> {
    const response = await apiClient.post<{
      success: boolean
      run_id?: string
      status?: string
      error?: string
    }>(`${this.baseUrl}/${jobId}/trigger`, request || {})
    return response.data
  }

  async pause(jobId: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${jobId}/pause`)
  }

  async resume(jobId: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${jobId}/resume`)
  }

  // ---------------------------------------------------------------------------
  // Run History
  // ---------------------------------------------------------------------------

  async listRuns(
    jobId: string,
    params?: { page?: number; per_page?: number; status?: string }
  ): Promise<PaginatedResponse<JobRunSummary>> {
    const response = await apiClient.get<{
      runs: JobRunSummary[]
      total: number
      page: number
      per_page: number
    }>(`${this.baseUrl}/${jobId}/runs`, { params })

    return {
      items: response.data.runs,
      total: response.data.total,
      page: response.data.page,
      per_page: response.data.per_page,
      pages: Math.ceil(response.data.total / (params?.per_page || 25)),
    }
  }

  async getRun(jobId: string, runId: string): Promise<JobRun> {
    const response = await apiClient.get<JobRun>(`${this.baseUrl}/${jobId}/runs/${runId}`)
    return response.data
  }

  async getRunLogs(jobId: string, runId: string): Promise<JobLog[]> {
    const response = await apiClient.get<{ logs: JobLog[] }>(
      `${this.baseUrl}/${jobId}/runs/${runId}/logs`
    )
    return response.data.logs
  }

  async cancelRun(jobId: string, runId: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${jobId}/runs/${runId}/cancel`)
  }
}

export const jobService = new JobService()
