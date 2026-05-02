/**
 * NovaSight ↔ Apache Superset proxy service
 *
 * Wraps `/api/v1/superset/*` (see
 * `app/domains/analytics/superset/proxy_routes.py`).
 *
 * Phase 4–6: exposes typed helpers that `chartService.ts`,
 * `useDashboards.ts`, and `useSqlQuery.ts` use to reroute persistence
 * to Superset when the per-tenant `FEATURE_SUPERSET_BACKEND` flag is
 * enabled. Consumers continue to import the existing services — only
 * the internals change.
 */

import { apiClient } from './apiClient';

const BASE_PATH = '/api/v1/superset';

export interface SupersetDatabase {
  id: number;
  database_name: string;
  backend: string;
  expose_in_sqllab: boolean;
}

export interface SupersetSqlLabRequest {
  sql: string;
  schema?: string;
  templateParams?: Record<string, unknown>;
  runAsync?: boolean;
}

export interface SupersetSqlLabResponse {
  query_id?: string | number;
  status?: string;
  data?: Array<Record<string, unknown>>;
  columns?: Array<{ name: string; type: string }>;
  resultsKey?: string;
}

let _flagCache: { value: boolean; ts: number } | null = null;
const FLAG_TTL_MS = 60_000;

/**
 * Returns whether the Superset-backed paths are enabled for the
 * current tenant. Cached for one minute.
 */
export async function isSupersetBackendEnabled(): Promise<boolean> {
  const now = Date.now();
  if (_flagCache && now - _flagCache.ts < FLAG_TTL_MS) {
    return _flagCache.value;
  }
  try {
    const { data } = await apiClient.get<{ enabled: boolean }>(
      `${BASE_PATH}/enabled`,
    );
    _flagCache = { value: !!data?.enabled, ts: now };
  } catch {
    _flagCache = { value: false, ts: now };
  }
  return _flagCache.value;
}

/** Force-clear the cached flag (used in tests / sign-out flows). */
export function _resetSupersetFlagCache(): void {
  _flagCache = null;
}

export const supersetService = {
  isEnabled: isSupersetBackendEnabled,

  async listDatabases(): Promise<SupersetDatabase[]> {
    const { data } = await apiClient.get<{ result: SupersetDatabase[] }>(
      `${BASE_PATH}/database/`,
    );
    return data.result || [];
  },

  // ----- Charts --------------------------------------------------------
  async listCharts(): Promise<{ items: unknown[]; total: number }> {
    const { data } = await apiClient.get<{ items: unknown[]; total: number }>(
      `${BASE_PATH}/charts`,
    );
    return data;
  },
  async getChart(id: string): Promise<Record<string, unknown>> {
    const { data } = await apiClient.get<Record<string, unknown>>(
      `${BASE_PATH}/charts/${id}`,
    );
    return data;
  },
  async createChart(payload: Record<string, unknown>): Promise<{ id: string }> {
    const { data } = await apiClient.post<{ id: string }>(
      `${BASE_PATH}/charts`,
      payload,
    );
    return data;
  },
  async updateChart(
    id: string,
    payload: Record<string, unknown>,
  ): Promise<{ id: string }> {
    const { data } = await apiClient.put<{ id: string }>(
      `${BASE_PATH}/charts/${id}`,
      payload,
    );
    return data;
  },
  async deleteChart(id: string): Promise<void> {
    await apiClient.delete(`${BASE_PATH}/charts/${id}`);
  },
  async runChartData(
    id: string,
    body: Record<string, unknown> = {},
  ): Promise<Record<string, unknown>> {
    const { data } = await apiClient.post<Record<string, unknown>>(
      `${BASE_PATH}/charts/${id}/data`,
      body,
    );
    return data;
  },

  // ----- Dashboards ----------------------------------------------------
  async listDashboards(): Promise<{ items: unknown[]; total: number }> {
    const { data } = await apiClient.get<{ items: unknown[]; total: number }>(
      `${BASE_PATH}/dashboards`,
    );
    return data;
  },
  async getDashboard(id: string): Promise<Record<string, unknown>> {
    const { data } = await apiClient.get<Record<string, unknown>>(
      `${BASE_PATH}/dashboards/${id}`,
    );
    return data;
  },
  async createDashboard(
    payload: Record<string, unknown>,
  ): Promise<{ id: string }> {
    const { data } = await apiClient.post<{ id: string }>(
      `${BASE_PATH}/dashboards`,
      payload,
    );
    return data;
  },
  async updateDashboard(
    id: string,
    payload: Record<string, unknown>,
  ): Promise<{ id: string }> {
    const { data } = await apiClient.put<{ id: string }>(
      `${BASE_PATH}/dashboards/${id}`,
      payload,
    );
    return data;
  },
  async deleteDashboard(id: string): Promise<void> {
    await apiClient.delete(`${BASE_PATH}/dashboards/${id}`);
  },

  // ----- SQL Lab -------------------------------------------------------
  async executeSql(
    payload: SupersetSqlLabRequest,
  ): Promise<SupersetSqlLabResponse> {
    const { data } = await apiClient.post<SupersetSqlLabResponse>(
      `${BASE_PATH}/sqllab/execute`,
      payload,
    );
    return data;
  },
  async sqlResults(key: string): Promise<SupersetSqlLabResponse> {
    const { data } = await apiClient.get<SupersetSqlLabResponse>(
      `${BASE_PATH}/sqllab/results/${encodeURIComponent(key)}`,
    );
    return data;
  },
  async estimateSql(
    payload: SupersetSqlLabRequest,
  ): Promise<Record<string, unknown>> {
    const { data } = await apiClient.post<Record<string, unknown>>(
      `${BASE_PATH}/sqllab/estimate`,
      payload,
    );
    return data;
  },
};

export default supersetService;
