import api from './index'
import type { Response } from '@/types/api'

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface User {
  id: string
  username: string
  created_at: string
}

export const authApi = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  register: async (username: string, password: string): Promise<Response<User>> => {
    const response = await api.post('/auth/register', { username, password })
    return response.data
  },

  getMe: async (): Promise<Response<User>> => {
    const response = await api.get('/auth/me')
    return response.data
  },

  logout: async (): Promise<Response<null>> => {
    const response = await api.post('/auth/logout')
    return response.data
  }
}
