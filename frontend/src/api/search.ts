import api from './index'
import type { Response, PaginatedResponse } from '@/types/api'
import type { Note } from '@/types/note'

export interface AISearchResult {
  answer: string
  context: string
  notes: { id: string; title: string }[]
}

export interface AIChatResult {
  answer: string
  notes: { id: string; title: string }[]
}

export const searchApi = {
  search: async (q: string, page?: number, page_size?: number): Promise<Response<PaginatedResponse<Note>>> => {
    const response = await api.get('/search', { params: { q, page, page_size } })
    return response.data
  },

  aiSearch: async (question: string): Promise<Response<AISearchResult>> => {
    const response = await api.post('/search/ai', null, { params: { question } })
    return response.data
  },

  aiChat: async (message: string, history?: Array<{ role: string; content: string }>): Promise<Response<AIChatResult>> => {
    const params: any = { message }
    if (history) {
      params.history = JSON.stringify(history)
    }
    const response = await api.post('/search/chat', null, { params })
    return response.data
  }
}
