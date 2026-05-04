/**
 * NovaSight Unified Job Service
 * ==============================
 *
 * Frontend API client for Dagster jobs.
 *
 * Post Spark→dlt migration the orchestrator schedules **only dlt and dbt
 * jobs** — see ``backend/app/domains/orchestration/domain/models.py``
 * (``TaskType``) and the ``ALLOWED_TASK_TYPES`` constant in
 * ``asset_factory.py``.
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
  type: 'dlt' | 'dbt' | 'pipeline'
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
  /** dlt pipeline UUID. The legacy field name is kept for backwards compat. */
  pipeline_id: string
  schedule?: string
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

export interface CreateDbtJobRequest {
  /** ``"run"`` or ``"test"`` */
  kind: 'run' | 'test'
  /** dbt profile to target */
  profile?: 'default' | 'lake' | 'warehouse'
  name?: string
  description?: string
  schedule?: string
  /** dbt --select expression */
  select?: string
  /** dbt tag selectors (run only); takes precedence over `select` */
  tags?: string[]
  /** Run with --full-refresh (run only) */
  full_refresh?: boolean
  /** Create one task per discovered dbt model. */
  split_by_model?: boolean
  /** Optional dbt layers to include when split_by_model=true. */
  layers?: string[]
  /** Optional model names to include when split_by_model=true. */
  model_names?: string[]
  /** Existing jobs to depend on (job id or dag_id). */
  upstream_job_ids?: string[]
  /** Explicit upstream task refs ({ job_id|dag_id, task_id }). */
  upstream_task_refs?: Array<{
    job_id?: string
    dag_id?: string
    task_id: string
  }>
  /** Raw dependency refs (task_id or job:<dag_id>:<task_id>). */
  depends_on?: string[]
  retries?: number
  retry_delay_minutes?: number
}

export interface CreatePipelineRequest {
  pipeline_ids: string[]
  name: string
  description?: string
  schedule?: string
  parallel?: boolean
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
    type?: 'dlt' | 'dbt' | 'pipeline'
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

  async createDbtJob(data: CreateDbtJobRequest): Promise<Job> {
    const response = await apiClient.post<{ job: Job }>(`${this.baseUrl}/dbt`, data)
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
