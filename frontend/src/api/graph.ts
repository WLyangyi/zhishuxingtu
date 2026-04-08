import api from './index'
import type { Response } from '@/types/api'
import type { GraphData } from '@/types/graph'

export const graphApi = {
  getGlobal: async (): Promise<Response<GraphData>> => {
    const response = await api.get('/graph/global')
    return response.data
  },

  getLocal: async (noteId: string): Promise<Response<GraphData>> => {
    const response = await api.get(`/graph/local/${noteId}`)
    return response.data
  }
}
