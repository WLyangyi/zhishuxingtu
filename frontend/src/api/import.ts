import api from './index'
import type { Response } from '@/types/api'
import type { ImportTask, ImportHistoryItem, ImportSaveRequest } from '@/types/import'

export const importApi = {
  uploadPdf: async (file: File): Promise<Response<{ task_id: string; filename: string; file_size: number }>> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/import/pdf', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000
    })
    return response.data
  },

  submitUrl: async (url: string): Promise<Response<{ task_id: string; url: string }>> => {
    const response = await api.post('/import/url', { url })
    return response.data
  },

  uploadVideo: async (file: File): Promise<Response<{ task_id: string; filename: string; file_size: number }>> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await api.post('/import/video', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000
    })
    return response.data
  },

  submitVideoUrl: async (url: string): Promise<Response<{ task_id: string; url: string; platform?: string; title?: string }>> => {
    const response = await api.post('/import/video-url', { url })
    return response.data
  },

  getTask: async (taskId: string): Promise<Response<ImportTask>> => {
    const response = await api.get(`/import/${taskId}`)
    return response.data
  },

  saveAsNote: async (data: ImportSaveRequest): Promise<Response<{ note_id: string }>> => {
    const response = await api.post('/import/save', data)
    return response.data
  },

  getHistory: async (params?: { source_type?: string; page?: number; page_size?: number }): Promise<Response<{ items: ImportHistoryItem[]; total: number; page: number; page_size: number }>> => {
    const response = await api.get('/import/history/list', { params })
    return response.data
  },

  deleteTask: async (taskId: string): Promise<Response<null>> => {
    const response = await api.delete(`/import/${taskId}`)
    return response.data
  },

  regenerate: async (taskId: string): Promise<Response<ImportTask>> => {
    const response = await api.post('/import/regenerate', { task_id: taskId })
    return response.data
  },

  getCapabilities: async (): Promise<Response<{ platforms: Array<{ name: string; key: string; support_level: string }> }>> => {
    const response = await api.get('/import/capabilities')
    return response.data
  },

  suggestCategory: async (taskId: string): Promise<Response<{ folder_id: string | null; reason: string }>> => {
    const response = await api.post('/import/suggest-category', { task_id: taskId })
    return response.data
  }
}
