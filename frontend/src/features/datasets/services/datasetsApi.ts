/**
 * Datasets API client.
 *
 * Talks to the backend ``/api/v1/datasets`` endpoints introduced
 * alongside the Superset-inspired Dataset abstraction.
 */

import { apiClient } from '@/services/apiClient';
import type {
  Dataset,
  DatasetCreateRequest,
  DatasetListResponse,
  DatasetPreview,
  DatasetUpdateRequest,
  DatasetColumn,
  DatasetMetric,
  DbtSyncResult,
  MartTablesResponse,
} from '../types';

const BASE = '/api/v1/datasets';

export interface ListDatasetsParams {
  page?: number;
  per_page?: number;
  kind?: 'physical' | 'virtual';
  source?: 'dbt' | 'manual' | 'sql_lab';
  search?: string;
  include_deleted?: boolean;
}

export const datasetsApi = {
  async list(params: ListDatasetsParams = {}): Promise<DatasetListResponse> {
    const { data } = await apiClient.get<DatasetListResponse>(BASE, { params });
    return data;
  },

  async get(id: string): Promise<Dataset> {
    const { data } = await apiClient.get<Dataset>(`${BASE}/${id}`);
    return data;
  },

  async create(payload: DatasetCreateRequest): Promise<Dataset> {
    const { data } = await apiClient.post<Dataset>(BASE, payload);
    return data;
  },

  async update(id: string, payload: DatasetUpdateRequest): Promise<Dataset> {
    const { data } = await apiClient.patch<Dataset>(`${BASE}/${id}`, payload);
    return data;
  },

  async remove(id: string, hard = false): Promise<void> {
    await apiClient.delete(`${BASE}/${id}`, { params: { hard } });
  },

  async replaceColumns(
    id: string,
    columns: Partial<DatasetColumn>[],
  ): Promise<Dataset> {
    const { data } = await apiClient.put<Dataset>(`${BASE}/${id}/columns`, {
      columns,
    });
    return data;
  },

  async replaceMetrics(
    id: string,
    metrics: Partial<DatasetMetric>[],
  ): Promise<Dataset> {
    const { data } = await apiClient.put<Dataset>(`${BASE}/${id}/metrics`, {
      metrics,
    });
    return data;
  },

  async preview(id: string, limit = 100): Promise<DatasetPreview> {
    const { data } = await apiClient.get<DatasetPreview>(
      `${BASE}/${id}/preview`,
      { params: { limit } },
    );
    return data;
  },

  async syncFromDbt(deactivateMissing = true): Promise<DbtSyncResult> {
    const { data } = await apiClient.post<DbtSyncResult>(`${BASE}/sync-dbt`, {
      deactivate_missing: deactivateMissing,
    });
    return data;
  },

  /**
   * List tables available in the tenant mart database.
   *
   * The dataset wizard is restricted to this single database, so this
   * endpoint is the only source of truth for what users can pick.
   */
  async listMartTables(): Promise<MartTablesResponse> {
    const { data } = await apiClient.get<MartTablesResponse>(
      `${BASE}/mart/tables`,
    );
    return data;
  },
};
