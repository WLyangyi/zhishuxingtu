import api from './index'
import type { Response, PaginatedResponse } from '@/types/api'
import type { Note } from '@/types/note'

export interface AISearchResult {
  answer: string
  context: string
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
  }
}
