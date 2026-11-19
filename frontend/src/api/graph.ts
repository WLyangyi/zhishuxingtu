import api from './index'
import type { Response } from '@/types/api'
import type { GraphData } from '@/types/graph'

export interface GraphFetchResult {
  response: Response<GraphData> | null
  etag: string | null
  notModified: boolean
}

export const graphApi = {
  getGlobal: async (etag?: string): Promise<GraphFetchResult> => {
    const response = await api.get('/graph/global', {
      headers: etag ? { 'If-None-Match': etag } : undefined,
      validateStatus: (status: number) => (status >= 200 && status < 300) || status === 304
    })
    if (response.status === 304) {
      return { response: null, etag: response.headers?.etag ?? etag ?? null, notModified: true }
    }
    return { response: response.data, etag: response.headers?.etag ?? null, notModified: false }
  },

  getLocal: async (noteId: string): Promise<Response<GraphData>> => {
    const response = await api.get(`/graph/local/${noteId}`)
    return response.data
  }
}
