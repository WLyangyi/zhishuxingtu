import api from './index'
import type { Response } from '@/types/api'
import type { Tag, TagCreate, TagUpdate } from '@/types/tag'

export const tagsApi = {
  list: async (): Promise<Response<Tag[]>> => {
    const response = await api.get('/tags')
    return response.data
  },

  create: async (data: TagCreate): Promise<Response<Tag>> => {
    const response = await api.post('/tags', data)
    return response.data
  },

  update: async (id: string, data: TagUpdate): Promise<Response<Tag>> => {
    const response = await api.put(`/tags/${id}`, data)
    return response.data
  },

  delete: async (id: string): Promise<Response<null>> => {
    const response = await api.delete(`/tags/${id}`)
    return response.data
  }
}
