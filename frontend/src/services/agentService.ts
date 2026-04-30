/**
 * NovaSight Agent Configuration Service
 *
 * Talks to the new `/api/v1/ai/agent/*` endpoints exposed by
 * `app/domains/ai/api/agent_config_routes.py`.
 *
 * Used by the AI Workbench (`/app/query`) "Agent" tab to read and
 * update the per-tenant agent configuration (default model, system
 * prompt, enabled tools, sampling parameters).
 */

import { apiClient } from './apiClient';

const BASE_PATH = '/api/v1/ai/agent';

export interface AgentConfig {
  id: string;
  tenant_id: string;
  default_model: string | null;
  embedding_model: string | null;
  system_prompt: string | null;
  enabled_tools: Record<string, boolean>;
  sampling: Record<string, number | string>;
  created_at: string;
  updated_at: string;
}

export interface AgentConfigUpdate {
  default_model?: string | null;
  embedding_model?: string | null;
  system_prompt?: string | null;
  enabled_tools?: Record<string, boolean>;
  sampling?: Record<string, number | string>;
}

export const agentService = {
  async getConfig(): Promise<AgentConfig> {
    const { data } = await apiClient.get<AgentConfig>(`${BASE_PATH}/config`);
    return data;
  },

  async updateConfig(updates: AgentConfigUpdate): Promise<AgentConfig> {
    const { data } = await apiClient.put<AgentConfig>(
      `${BASE_PATH}/config`,
      updates,
    );
    return data;
  },
};

export default agentService;
