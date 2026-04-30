/**
 * NovaSight MCP Server Registry Service
 *
 * Thin wrapper around `/api/v1/ai/mcp/*` (see
 * `app/domains/ai/api/mcp_routes.py`). Used by the AI Workbench
 * "MCP Servers" tab.
 */

import { apiClient } from './apiClient';

const BASE_PATH = '/api/v1/ai/mcp';

export interface MCPServer {
  id: string;
  tenant_id: string;
  name: string;
  base_url: string;
  enabled: boolean;
  tools_snapshot: string[];
  auth_header_set?: boolean;
  created_at: string;
  updated_at: string;
}

export interface MCPServerCreate {
  name: string;
  base_url: string;
  auth_header?: string;
  enabled?: boolean;
}

export interface MCPHealthResult {
  name: string;
  healthy: boolean;
}

export const mcpService = {
  async listServers(): Promise<MCPServer[]> {
    const { data } = await apiClient.get<{ servers: MCPServer[] }>(
      `${BASE_PATH}/servers`,
    );
    return data.servers;
  },

  async registerServer(payload: MCPServerCreate): Promise<MCPServer> {
    const { data } = await apiClient.post<MCPServer>(
      `${BASE_PATH}/servers`,
      payload,
    );
    return data;
  },

  async deleteServer(name: string): Promise<void> {
    await apiClient.delete(`${BASE_PATH}/servers/${encodeURIComponent(name)}`);
  },

  async health(name: string): Promise<MCPHealthResult> {
    const { data } = await apiClient.get<MCPHealthResult>(
      `${BASE_PATH}/servers/${encodeURIComponent(name)}/health`,
    );
    return data;
  },

  async refreshTools(name: string): Promise<string[]> {
    const { data } = await apiClient.post<{ tools: string[] }>(
      `${BASE_PATH}/servers/${encodeURIComponent(name)}/refresh`,
      {},
    );
    return data.tools;
  },

  async invoke<T = unknown>(
    name: string,
    tool: string,
    args: Record<string, unknown>,
  ): Promise<T> {
    const { data } = await apiClient.post<{ result: T }>(
      `${BASE_PATH}/${encodeURIComponent(name)}/invoke`,
      { tool, arguments: args },
    );
    return data.result;
  },
};

export default mcpService;
