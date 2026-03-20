import api from './index'
import type {
  FewShotExample, FewShotExampleCreate, FewShotExampleUpdate,
  PromptVersion, PromptVersionCreate,
  ABExperiment, ABExperimentCreate, ABExperimentStats,
  PromptChain, PromptChainCreate, PromptChainUpdate,
  ChainExecution, ChainExecutionResult,
  PromptEvaluationStats
} from '@/types/promptLab'

export const promptLabApi = {
  fewShot: {
    async create(data: FewShotExampleCreate): Promise<FewShotExample> {
      const response = await api.post('/prompts/few-shot', data)
      return response.data.data
    },

    async list(params?: { scenario?: string; prompt_id?: string; min_quality?: number }): Promise<FewShotExample[]> {
      const response = await api.get('/prompts/few-shot', { params })
      return response.data.data
    },

    async get(id: string): Promise<FewShotExample> {
      const response = await api.get(`/prompts/few-shot/${id}`)
      return response.data.data
    },

    async update(id: string, data: FewShotExampleUpdate): Promise<FewShotExample> {
      const response = await api.put(`/prompts/few-shot/${id}`, data)
      return response.data.data
    },

    async delete(id: string): Promise<void> {
      await api.delete(`/prompts/few-shot/${id}`)
    },

    async getScenarios(): Promise<string[]> {
      const response = await api.get('/prompts/few-shot/scenarios/list')
      return response.data.data
    }
  },

  abTest: {
    async createVersion(data: PromptVersionCreate): Promise<PromptVersion> {
      const response = await api.post('/ab-experiments/versions', data)
      return response.data.data
    },

    async listVersions(promptId?: string): Promise<PromptVersion[]> {
      const response = await api.get('/ab-experiments/versions', { params: { prompt_id: promptId } })
      return response.data.data
    },

    async createExperiment(data: ABExperimentCreate): Promise<ABExperiment> {
      const response = await api.post('/ab-experiments/experiments', data)
      return response.data.data
    },

    async listExperiments(status?: string): Promise<ABExperiment[]> {
      const response = await api.get('/ab-experiments/experiments', { params: { status } })
      return response.data.data
    },

    async startExperiment(id: string): Promise<void> {
      await api.post(`/ab-experiments/experiments/${id}/start`)
    },

    async pauseExperiment(id: string): Promise<void> {
      await api.post(`/ab-experiments/experiments/${id}/pause`)
    },

    async assignVersion(experimentId: string, sessionId: string): Promise<{ assigned_version: string; version_id: string }> {
      const response = await api.post(`/ab-experiments/experiments/${experimentId}/assign`, null, {
        params: { session_id: sessionId }
      })
      return response.data.data
    },

    async getStats(experimentId: string): Promise<ABExperimentStats> {
      const response = await api.get(`/ab-experiments/experiments/${experimentId}/stats`)
      return response.data.data
    }
  },

  promptChain: {
    async list(isActive?: boolean): Promise<PromptChain[]> {
      const response = await api.get('/prompt-chains', { params: { is_active: isActive } })
      return response.data.data
    },

    async get(id: string): Promise<PromptChain> {
      const response = await api.get(`/prompt-chains/${id}`)
      return response.data.data
    },

    async create(data: PromptChainCreate): Promise<PromptChain> {
      const response = await api.post('/prompt-chains', data)
      return response.data.data
    },

    async update(id: string, data: PromptChainUpdate): Promise<PromptChain> {
      const response = await api.put(`/prompt-chains/${id}`, data)
      return response.data.data
    },

    async delete(id: string): Promise<void> {
      await api.delete(`/prompt-chains/${id}`)
    },

    async getPresets(): Promise<any[]> {
      const response = await api.get('/prompt-chains/presets')
      return response.data.data
    },

    async createFromPreset(chainType: string): Promise<PromptChain> {
      const response = await api.post(`/prompt-chains/presets/${chainType}`)
      return response.data.data
    },

    async execute(chainId: string, inputData: Record<string, any>, sessionId?: string): Promise<ChainExecutionResult> {
      const response = await api.post(`/prompt-chains/${chainId}/execute`, inputData, {
        params: { session_id: sessionId }
      })
      return response.data.data
    },

    async getExecutions(chainId: string, limit: number = 20): Promise<ChainExecution[]> {
      const response = await api.get(`/prompt-chains/${chainId}/executions`, { params: { limit } })
      return response.data.data
    },

    async getExecution(id: string): Promise<ChainExecution> {
      const response = await api.get(`/prompt-chains/executions/${id}`)
      return response.data.data
    }
  },

  promptEval: {
    async getStats(days: number = 7, promptVersionId?: string): Promise<PromptEvaluationStats> {
      const response = await api.get('/prompt-evaluations/stats', {
        params: { days, prompt_version_id: promptVersionId }
      })
      return response.data.data
    }
  }
}
