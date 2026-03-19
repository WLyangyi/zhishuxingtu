import api from './index'
import type {
  Prompt, PromptCreate, PromptUpdate, PromptListResponse,
  PromptTemplate, PromptCategory
} from '@/types/prompt'

export const promptsApi = {
  async getTemplates(): Promise<PromptTemplate[]> {
    const response = await api.get('/prompts/templates')
    return response.data
  },

  async getPrompts(params?: {
    category?: string
    is_system?: boolean
    page?: number
    page_size?: number
  }): Promise<PromptListResponse> {
    const response = await api.get('/prompts', { params })
    return response.data
  },

  async getCategories(): Promise<PromptCategory[]> {
    const response = await api.get('/prompts/categories')
    return response.data
  },

  async getPrompt(id: string): Promise<Prompt> {
    const response = await api.get(`/prompts/${id}`)
    return response.data
  },

  async createPrompt(data: PromptCreate): Promise<Prompt> {
    const response = await api.post('/prompts', data)
    return response.data
  },

  async createFromTemplate(templateIndex: number): Promise<Prompt> {
    const response = await api.post(`/prompts/from-template/${templateIndex}`)
    return response.data
  },

  async updatePrompt(id: string, data: PromptUpdate): Promise<Prompt> {
    const response = await api.put(`/prompts/${id}`, data)
    return response.data
  },

  async deletePrompt(id: string): Promise<void> {
    await api.delete(`/prompts/${id}`)
  },

  async initializePrompts(): Promise<{ success: boolean; message: string }> {
    const response = await api.post('/prompts/initialize')
    return response.data
  }
}
