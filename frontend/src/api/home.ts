import api from './index'
import type { Response } from '@/types/api'
import type { HomeOverview } from '@/types/home'

export const homeApi = {
  overview: async (): Promise<Response<HomeOverview>> => {
    const response = await api.get('/home/overview')
    return response.data
  }
}
