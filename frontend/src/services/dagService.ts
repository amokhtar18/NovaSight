import { apiClient } from './apiClient'

export interface DagConfig {
  id: string
  dag_id: string
  description: string
  current_version: number
  schedule_type: 'cron' | 'preset' | 'manual'
  schedule_cron?: string
  schedule_preset?: string
  timezone: string
  status: 'draft' | 'active' | 'paused' | 'archived'
  deployed_at?: string
  deployed_version?: number
  tags: string[]
  created_at: string
  updated_at: string
  created_by: string
}

export interface TaskConfig {
  task_id: string
  task_type: string
  config: Record<string, unknown>
  timeout_minutes: number
  retries: number
  retry_delay_minutes: number
  trigger_rule: string
  depends_on: string[]
  position_x: number
  position_y: number
}

export interface DagRun {
  dag_id: string
  run_id: string
  state: string
  execution_date: string
  start_date?: string
  end_date?: string
}

export interface TaskInstance {
  task_id: string
  state: string
  start_date?: string
  end_date?: string
  try_number: number
}

export interface CreateDagRequest {
  dag_id: string
  description?: string
  schedule_type: 'cron' | 'preset' | 'manual'
  schedule_cron?: string
  schedule_preset?: string
  timezone?: string
  start_date?: string
  catchup?: boolean
  max_active_runs?: number
  default_retries?: number
  default_retry_delay_minutes?: number
  notification_emails?: string[]
  email_on_failure?: boolean
  email_on_success?: boolean
  tags?: string[]
  tasks: TaskConfig[]
}

class DagService {
  private baseUrl = '/api/v1/dags'

  async list(params?: { status?: string; search?: string }): Promise<DagConfig[]> {
    const response = await apiClient.get<{ dags: DagConfig[] }>(this.baseUrl, { params })
    return response.data.dags
  }

  async get(dagId: string): Promise<DagConfig & { tasks: TaskConfig[] }> {
    const response = await apiClient.get(`${this.baseUrl}/${dagId}`)
    return response.data
  }

  async create(data: CreateDagRequest): Promise<DagConfig> {
    const response = await apiClient.post(this.baseUrl, data)
    return response.data
  }

  async update(dagId: string, data: Partial<CreateDagRequest>): Promise<DagConfig> {
    const response = await apiClient.put(`${this.baseUrl}/${dagId}`, data)
    return response.data
  }

  async delete(dagId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/${dagId}`)
  }

  async validate(dagId: string): Promise<{ valid: boolean; errors: string[] }> {
    const response = await apiClient.post(`${this.baseUrl}/${dagId}/validate`)
    return response.data
  }

  async deploy(dagId: string): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.post(`${this.baseUrl}/${dagId}/deploy`)
    return response.data
  }

  async trigger(dagId: string, conf?: Record<string, unknown>): Promise<DagRun> {
    const response = await apiClient.post(`${this.baseUrl}/${dagId}/trigger`, { conf })
    return response.data.run
  }

  async pause(dagId: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${dagId}/pause`)
  }

  async unpause(dagId: string): Promise<void> {
    await apiClient.post(`${this.baseUrl}/${dagId}/unpause`)
  }

  async getRuns(dagId: string, limit = 25): Promise<DagRun[]> {
    const response = await apiClient.get<{ runs: DagRun[] }>(
      `${this.baseUrl}/${dagId}/runs`,
      { params: { limit } }
    )
    return response.data.runs
  }

  async getRunDetail(dagId: string, runId: string): Promise<{
    run: DagRun
    tasks: TaskInstance[]
  }> {
    const response = await apiClient.get(`${this.baseUrl}/${dagId}/runs/${runId}`)
    return response.data
  }

  async getTaskLogs(
    dagId: string,
    runId: string,
    taskId: string,
    tryNumber = 1
  ): Promise<string> {
    const response = await apiClient.get<{ logs: string }>(
      `${this.baseUrl}/${dagId}/runs/${runId}/tasks/${taskId}/logs`,
      { params: { try_number: tryNumber } }
    )
    return response.data.logs
  }
}

export const dagService = new DagService()
