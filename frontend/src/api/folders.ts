import api from './index'
import type { Response } from '@/types/api'
import type { Folder, FolderCreate, FolderUpdate, FolderTree } from '@/types/folder'

export const foldersApi = {
  list: async (categoryId?: string): Promise<Response<FolderTree[]>> => {
    const params = categoryId ? { category_id: categoryId } : {}
    const response = await api.get('/folders', { params })
    return response.data
  },

  create: async (data: FolderCreate): Promise<Response<Folder>> => {
    const response = await api.post('/folders', data)
    return response.data
  },

  update: async (id: string, data: FolderUpdate): Promise<Response<Folder>> => {
    const response = await api.put(`/folders/${id}`, data)
    return response.data
  },

  delete: async (id: string): Promise<Response<null>> => {
    const response = await api.delete(`/folders/${id}`)
    return response.data
  }
}
