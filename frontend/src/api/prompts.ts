import api from './index'
import type { Response } from '@/types/api'
import type {
  Prompt, PromptCreate, PromptUpdate, PromptListResponse,
  PromptTemplate, PromptCategory
} from '@/types/prompt'

export const promptsApi = {
  async getTemplates(): Promise<Response<PromptTemplate[]>> {
    const response = await api.get('/prompts/templates')
    return response.data
  },

  async getPrompts(params?: {
    category?: string
    is_system?: boolean
    page?: number
    page_size?: number
  }): Promise<Response<PromptListResponse>> {
    const response = await api.get('/prompts', { params })
    return response.data
  },

  async getCategories(): Promise<Response<PromptCategory[]>> {
    const response = await api.get('/prompts/categories')
    return response.data
  },

  async getPrompt(id: string): Promise<Response<Prompt>> {
    const response = await api.get(`/prompts/${id}`)
    return response.data
  },

  async createPrompt(data: PromptCreate): Promise<Response<Prompt>> {
    const response = await api.post('/prompts', data)
    return response.data
  },

  async createFromTemplate(templateIndex: number): Promise<Response<Prompt>> {
    const response = await api.post(`/prompts/from-template/${templateIndex}`)
    return response.data
  },

  async updatePrompt(id: string, data: PromptUpdate): Promise<Response<Prompt>> {
    const response = await api.put(`/prompts/${id}`, data)
    return response.data
  },

  async deletePrompt(id: string): Promise<Response<null>> {
    const response = await api.delete(`/prompts/${id}`)
    return response.data
  },

  async initializePrompts(): Promise<Response<{ created_count: number }>> {
    const response = await api.post('/prompts/initialize')
    return response.data
  }
}
