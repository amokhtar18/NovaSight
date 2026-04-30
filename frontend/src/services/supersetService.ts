/**
 * NovaSight ↔ Apache Superset proxy service
 *
 * Wraps `/api/v1/superset/*` (see
 * `app/domains/analytics/superset/proxy_routes.py`). Today the existing
 * NovaSight chart / dashboard / SQL Lab UIs continue to use their
 * native NovaSight endpoints; this service is the foundation for the
 * upcoming "swap" phases (4-6 in the integration plan) that re-route
 * `chartService`, `useDashboards`, and the SQL editor through the
 * Superset proxy without changing the React UI.
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
  database_id: number;
  sql: string;
  schema?: string;
  templateParams?: Record<string, unknown>;
  runAsync?: boolean;
}

/**
 * Generic Superset REST passthrough. The proxy on the backend strips
 * hop-by-hop headers and forwards the JWT so Superset's
 * `NovaSightSecurityManager` can mirror the user.
 */
export const supersetService = {
  async listDatabases(): Promise<SupersetDatabase[]> {
    const { data } = await apiClient.get<{ result: SupersetDatabase[] }>(
      `${BASE_PATH}/database/`,
    );
    return data.result || [];
  },

  async executeSql(payload: SupersetSqlLabRequest): Promise<unknown> {
    const { data } = await apiClient.post<unknown>(
      `${BASE_PATH}/sqllab/execute/`,
      payload,
    );
    return data;
  },

  async listCharts(): Promise<unknown[]> {
    const { data } = await apiClient.get<{ result: unknown[] }>(
      `${BASE_PATH}/chart/`,
    );
    return data.result || [];
  },

  async listDashboards(): Promise<unknown[]> {
    const { data } = await apiClient.get<{ result: unknown[] }>(
      `${BASE_PATH}/dashboard/`,
    );
    return data.result || [];
  },
};

export default supersetService;
