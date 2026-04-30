/**
 * NovaSight Ollama Configuration Service
 *
 * Wraps `/api/v1/ai/ollama/*` (see
 * `app/domains/ai/api/ollama_config_routes.py`). Used by the AI
 * Workbench "Ollama" tab.
 */

import { apiClient } from './apiClient';

const BASE_PATH = '/api/v1/ai/ollama';

export interface OllamaConfig {
  base_url: string;
  default_model: string | null;
  embedding_model: string | null;
}

export interface OllamaConfigUpdate {
  default_model?: string | null;
  embedding_model?: string | null;
}

export const ollamaService = {
  async getConfig(): Promise<OllamaConfig> {
    const { data } = await apiClient.get<OllamaConfig>(`${BASE_PATH}/config`);
    return data;
  },

  async updateConfig(updates: OllamaConfigUpdate): Promise<OllamaConfig> {
    const { data } = await apiClient.put<OllamaConfig>(
      `${BASE_PATH}/config`,
      updates,
    );
    return data;
  },

  async pullModel(model: string): Promise<{ status: string; model: string }> {
    const { data } = await apiClient.post<{ status: string; model: string }>(
      `${BASE_PATH}/models/pull`,
      { model },
    );
    return data;
  },
};

export default ollamaService;
