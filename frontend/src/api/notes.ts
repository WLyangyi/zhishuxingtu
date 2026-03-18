import api from './index'
import type { Response, PaginatedResponse } from '@/types/api'
import type { Note, NoteCreate, NoteUpdate, Backlink } from '@/types/note'

export const notesApi = {
  list: async (params?: { folder_id?: string; tag_id?: string; page?: number; page_size?: number }): Promise<Response<PaginatedResponse<Note>>> => {
    const response = await api.get('/notes', { params })
    return response.data
  },

  get: async (id: string): Promise<Response<Note>> => {
    const response = await api.get(`/notes/${id}`)
    return response.data
  },

  create: async (data: NoteCreate): Promise<Response<Note>> => {
    const response = await api.post('/notes', data)
    return response.data
  },

  update: async (id: string, data: NoteUpdate): Promise<Response<Note>> => {
    const response = await api.put(`/notes/${id}`, data)
    return response.data
  },

  delete: async (id: string): Promise<Response<null>> => {
    const response = await api.delete(`/notes/${id}`)
    return response.data
  },

  getBacklinks: async (id: string): Promise<Response<Backlink[]>> => {
    const response = await api.get(`/notes/${id}/backlinks`)
    return response.data
  }
}
