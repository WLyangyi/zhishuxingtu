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

export interface HybridSearchResultItem {
  id: string
  title: string
  content: string
  score: number
  folder_id?: string
  created_at?: string
  updated_at?: string
}

export interface HybridSearchResult {
  results: HybridSearchResultItem[]
  engine: 'hybrid' | 'bm25' | 'vector' | 'error'
  query?: string
  total?: number
  fusion_method?: string
  vector_weight?: number
  bm25_weight?: number
  index_stats?: any
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

  aiChat: async (message: string, history?: Array<{ role: string; content: string }>, sessionId?: string): Promise<Response<AIChatResult>> => {
    const params: any = { message }
    if (history) {
      params.history = JSON.stringify(history)
    }
    if (sessionId) {
      params.session_id = sessionId
    }
    const response = await api.post('/search/chat', null, { params })
    return response.data
  },

  // 混合检索 API (V3.7)
  
  // 混合检索 - 融合向量语义和BM25关键词
  hybridSearch: async (q: string, k?: number): Promise<Response<HybridSearchResult>> => {
    const response = await api.get('/search/hybrid', { params: { q, k } })
    return response.data
  },
  
  // 纯BM25关键词检索
  bm25Search: async (q: string, k?: number): Promise<Response<HybridSearchResult>> => {
    const response = await api.get('/search/bm25', { params: { q, k } })
    return response.data
  },
  
  // BM25索引状态
  bm25Status: async (): Promise<Response<any>> => {
    const response = await api.get('/search/bm25/status')
    return response.data
  },
  
  // 重建BM25索引
  rebuildBm25Index: async (): Promise<Response<any>> => {
    const response = await api.post('/search/bm25/rebuild')
    return response.data
  }
}
