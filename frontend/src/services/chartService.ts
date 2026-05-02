/**
 * NovaSight Chart Service
 * 
 * API client for chart management operations.
 *
 * Internals: when the per-tenant `FEATURE_SUPERSET_BACKEND` flag is
 * on, CRUD calls are transparently re-routed through
 * `supersetService` (Phase 4 of the Superset integration). The public
 * function signatures are unchanged so consumers (`pages/charts/*`,
 * `features/charts/*`, dashboards, SQL Editor) keep working without
 * modification.
 */

import { apiClient } from './apiClient';
import { supersetService, isSupersetBackendEnabled } from './supersetService';
import type {
  Chart,
  ChartFolder,
  ChartType,
  ChartSourceType,
  ChartVizConfig,
  ChartQueryConfig,
} from '@/components/charts/types';

const BASE_PATH = '/api/v1/charts';
const FOLDERS_PATH = '/api/v1/chart-folders';

// =============================================================================
// Request/Response Types
// =============================================================================

export interface ChartCreateRequest {
  name: string;
  description?: string;
  chart_type: ChartType;
  source_type: ChartSourceType;
  semantic_model_id?: string;
  sql_query?: string;
  query_config: ChartQueryConfig;
  viz_config: ChartVizConfig;
  folder_id?: string;
  tags?: string[];
  is_public?: boolean;
}

export interface ChartUpdateRequest {
  name?: string;
  description?: string;
  chart_type?: ChartType;
  source_type?: ChartSourceType;
  semantic_model_id?: string;
  sql_query?: string;
  query_config?: ChartQueryConfig;
  viz_config?: ChartVizConfig;
  folder_id?: string;
  tags?: string[];
  is_public?: boolean;
}

export interface ChartListResponse {
  items: Chart[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface ChartDataResponse {
  chart_id: string;
  data: Record<string, unknown>[];
  columns: { name: string; type: string }[];
  row_count: number;
  execution_time_ms: number;
  cached: boolean;
  cache_expires_at?: string;
}

export interface ChartPreviewRequest {
  source_type: ChartSourceType;
  semantic_model_id?: string;
  sql_query?: string;
  query_config?: ChartQueryConfig;
  limit?: number;
}

export interface ChartFolderCreateRequest {
  name: string;
  description?: string;
  parent_id?: string;
}

export interface ChartFolderUpdateRequest {
  name?: string;
  description?: string;
  parent_id?: string;
}

export interface SQLEditorSaveAsChartRequest {
  name: string;
  description?: string;
  chart_type: 'bar' | 'line' | 'pie';
  sql_query: string;
  x_column: string;
  y_columns: string[];
  viz_config?: ChartVizConfig;
  folder_id?: string;
  tags?: string[];
}

// =============================================================================
// Superset adapter (used when FEATURE_SUPERSET_BACKEND is on)
// =============================================================================

function novaToSuperset(payload: ChartCreateRequest | ChartUpdateRequest): Record<string, unknown> {
  return {
    name: (payload as ChartCreateRequest).name,
    description: payload.description,
    chart_type: payload.chart_type,
    source_type: payload.source_type,
    semantic_model_id: payload.semantic_model_id,
    sql_query: payload.sql_query,
    query_config: payload.query_config,
    viz_config: payload.viz_config,
    folder_id: payload.folder_id,
    tags: payload.tags,
    is_public: payload.is_public,
  };
}

function supersetToNova(raw: Record<string, unknown>): Chart {
  const queryConfig = (raw.query_config as ChartQueryConfig) || {
    dimensions: [],
    measures: [],
  };
  const vizConfig = (raw.viz_config as ChartVizConfig) || {};
  return {
    id: String(raw.id || ''),
    name: String(raw.name || ''),
    description: (raw.description as string) || undefined,
    chartType: (raw.chart_type as ChartType) || 'table',
    sourceType: (raw.source_type as ChartSourceType) || 'semantic_model',
    semanticModelId: (raw.semantic_model_id as string) || undefined,
    queryConfig,
    vizConfig,
    folderId: (raw.folder_id as string) || undefined,
    tags: (raw.tags as string[]) || [],
    isPublic: Boolean(raw.is_public),
    createdBy: (raw.created_by as string) || '',
    tenantId: (raw.tenant_id as string) || '',
    createdAt: (raw.created_at as string) || '',
    updatedAt: (raw.updated_at as string) || undefined,
  };
}

// =============================================================================
// Chart Service
// =============================================================================

export const chartService = {
  // ===========================================================================
  // Chart CRUD
  // ===========================================================================

  /**
   * List charts with pagination and filters.
   */
  async list(params?: {
    folder_id?: string;
    include_public?: boolean;
    tags?: string;
    chart_types?: string;
    search?: string;
    page?: number;
    per_page?: number;
  }): Promise<ChartListResponse> {
    if (await isSupersetBackendEnabled()) {
      const { items, total } = await supersetService.listCharts();
      const charts = (items as Record<string, unknown>[]).map(supersetToNova);
      return {
        items: charts,
        total,
        page: 1,
        per_page: charts.length,
        pages: 1,
      };
    }
    const response = await apiClient.get<ChartListResponse>(BASE_PATH, { params });
    return response.data;
  },

  /**
   * Get all charts (flat list for selection UI).
   */
  async listAll(params?: {
    include_folders?: boolean;
    search?: string;
    limit?: number;
  }): Promise<{ charts: Chart[]; folders?: ChartFolder[] }> {
    const response = await apiClient.get<{ charts: Chart[]; folders?: ChartFolder[] }>(
      `${BASE_PATH}/all`,
      { params }
    );
    return response.data;
  },

  /**
   * Get a single chart by ID.
   */
  async getById(id: string): Promise<Chart> {
    if (await isSupersetBackendEnabled()) {
      const raw = await supersetService.getChart(id);
      return supersetToNova(raw);
    }
    const response = await apiClient.get<Chart>(`${BASE_PATH}/${id}`);
    return response.data;
  },

  /**
   * Create a new chart.
   */
  async create(data: ChartCreateRequest): Promise<Chart> {
    if (await isSupersetBackendEnabled()) {
      const { id } = await supersetService.createChart(novaToSuperset(data));
      return supersetToNova(await supersetService.getChart(id));
    }
    const response = await apiClient.post<Chart>(BASE_PATH, data);
    return response.data;
  },

  /**
   * Update an existing chart.
   */
  async update(id: string, data: ChartUpdateRequest): Promise<Chart> {
    if (await isSupersetBackendEnabled()) {
      await supersetService.updateChart(id, novaToSuperset(data));
      return supersetToNova(await supersetService.getChart(id));
    }
    const response = await apiClient.put<Chart>(`${BASE_PATH}/${id}`, data);
    return response.data;
  },

  /**
   * Delete a chart.
   */
  async delete(id: string, hard: boolean = false): Promise<void> {
    if (await isSupersetBackendEnabled()) {
      await supersetService.deleteChart(id);
      return;
    }
    await apiClient.delete(`${BASE_PATH}/${id}`, { params: { hard } });
  },

  /**
   * Duplicate a chart.
   */
  async duplicate(id: string, newName?: string): Promise<Chart> {
    const response = await apiClient.post<Chart>(`${BASE_PATH}/${id}/duplicate`, {
      name: newName,
    });
    return response.data;
  },

  // ===========================================================================
  // Chart Data
  // ===========================================================================

  /**
   * Get chart data (execute query).
   */
  async getData(id: string, refresh: boolean = false): Promise<ChartDataResponse> {
    const response = await apiClient.get<ChartDataResponse>(`${BASE_PATH}/${id}/data`, {
      params: { refresh },
    });
    return response.data;
  },

  /**
   * Get chart data with runtime filters.
   */
  async getDataWithFilters(
    id: string,
    filters?: Record<string, unknown>,
    refresh: boolean = false
  ): Promise<ChartDataResponse> {
    const response = await apiClient.post<ChartDataResponse>(`${BASE_PATH}/${id}/data`, {
      filters,
      refresh,
    });
    return response.data;
  },

  /**
   * Preview query data without saving.
   */
  async preview(data: ChartPreviewRequest): Promise<ChartDataResponse> {
    const response = await apiClient.post<ChartDataResponse>(`${BASE_PATH}/preview`, data);
    return response.data;
  },

  // ===========================================================================
  // Chart Folders
  // ===========================================================================

  /**
   * List chart folders.
   */
  async listFolders(parentId?: string): Promise<ChartFolder[]> {
    const response = await apiClient.get<ChartFolder[]>(FOLDERS_PATH, {
      params: { parent_id: parentId },
    });
    return response.data;
  },

  /**
   * Get a folder by ID.
   */
  async getFolder(id: string): Promise<ChartFolder> {
    const response = await apiClient.get<ChartFolder>(`${FOLDERS_PATH}/${id}`);
    return response.data;
  },

  /**
   * Create a new folder.
   */
  async createFolder(data: ChartFolderCreateRequest): Promise<ChartFolder> {
    const response = await apiClient.post<ChartFolder>(FOLDERS_PATH, data);
    return response.data;
  },

  /**
   * Update a folder.
   */
  async updateFolder(id: string, data: ChartFolderUpdateRequest): Promise<ChartFolder> {
    const response = await apiClient.put<ChartFolder>(`${FOLDERS_PATH}/${id}`, data);
    return response.data;
  },

  /**
   * Delete a folder.
   */
  async deleteFolder(id: string, moveTo?: string): Promise<void> {
    await apiClient.delete(`${FOLDERS_PATH}/${id}`, {
      params: { move_to: moveTo },
    });
  },

  // ===========================================================================
  // SQL Editor Integration
  // ===========================================================================

  /**
   * Save SQL query result as a chart (from SQL Editor).
   */
  async saveFromSQLEditor(data: SQLEditorSaveAsChartRequest): Promise<Chart> {
    const response = await apiClient.post<Chart>('/api/v1/sql-editor/save-as-chart', data);
    return response.data;
  },

  // ===========================================================================
  // Dashboard Integration
  // ===========================================================================

  /**
   * Add a chart to a dashboard.
   */
  async addToDashboard(
    dashboardId: string,
    chartId: string,
    config?: {
      grid_position?: { x: number; y: number; w: number; h: number };
      local_filters?: Record<string, unknown>;
      local_viz_config?: Record<string, unknown>;
    }
  ): Promise<{
    id: string;
    dashboard_id: string;
    chart_id: string;
    grid_position: { x: number; y: number; w: number; h: number };
  }> {
    const response = await apiClient.post(`/api/v1/dashboards/${dashboardId}/charts`, {
      chart_id: chartId,
      ...config,
    });
    return response.data;
  },

  /**
   * Remove a chart from a dashboard.
   */
  async removeFromDashboard(dashboardId: string, chartId: string): Promise<void> {
    await apiClient.delete(`/api/v1/dashboards/${dashboardId}/charts/${chartId}`);
  },

  /**
   * Get all charts on a dashboard.
   */
  async getDashboardCharts(
    dashboardId: string
  ): Promise<
    Array<{
      dashboard_chart_id: string;
      chart: Chart;
      grid_position: { x: number; y: number; w: number; h: number };
      local_filters: Record<string, unknown>;
      local_viz_config: Record<string, unknown>;
    }>
  > {
    const response = await apiClient.get(`/api/v1/dashboards/${dashboardId}/charts`);
    return response.data;
  },
};

export default chartService;
