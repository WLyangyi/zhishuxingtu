import api from './index'
import type { Response } from '@/types/api'
import type { 
  Category, CategoryCreate, CategoryUpdate,
  ContentType, ContentTypeCreate, ContentTypeUpdate,
  Content, ContentCreate, ContentUpdate, ContentListResponse
} from '@/types/category'

export const categoriesApi = {
  async getCategories(): Promise<Response<Category[]>> {
    const response = await api.get('/categories')
    return response.data
  },

  async createCategory(data: CategoryCreate): Promise<Response<Category>> {
    const response = await api.post('/categories', data)
    return response.data
  },

  async updateCategory(id: string, data: CategoryUpdate): Promise<Response<Category>> {
    const response = await api.put(`/categories/${id}`, data)
    return response.data
  },

  async deleteCategory(id: string): Promise<Response<null>> {
    const response = await api.delete(`/categories/${id}`)
    return response.data
  },

  async getContentTypes(categoryId: string): Promise<Response<ContentType[]>> {
    const response = await api.get(`/categories/${categoryId}/types`)
    return response.data
  },

  async createContentType(data: ContentTypeCreate): Promise<Response<ContentType>> {
    const response = await api.post('/categories/types', data)
    return response.data
  },

  async updateContentType(id: string, data: ContentTypeUpdate): Promise<Response<ContentType>> {
    const response = await api.put(`/categories/types/${id}`, data)
    return response.data
  },

  async deleteContentType(id: string): Promise<Response<null>> {
    const response = await api.delete(`/categories/types/${id}`)
    return response.data
  }
}

export const contentsApi = {
  async getContents(params?: {
    category_id?: string
    type_id?: string
    tag_id?: string
    keyword?: string
    page?: number
    page_size?: number
  }): Promise<Response<ContentListResponse>> {
    const response = await api.get('/contents', { params })
    return response.data
  },

  async getContent(id: string): Promise<Response<Content>> {
    const response = await api.get(`/contents/${id}`)
    return response.data
  },

  async createContent(data: ContentCreate): Promise<Response<Content>> {
    const response = await api.post('/contents', data)
    return response.data
  },

  async updateContent(id: string, data: ContentUpdate): Promise<Response<Content>> {
    const response = await api.put(`/contents/${id}`, data)
    return response.data
  },

  async deleteContent(id: string): Promise<Response<null>> {
    const response = await api.delete(`/contents/${id}`)
    return response.data
  },

  async getBacklinks(id: string): Promise<Response<{ items: { id: string; title: string }[]; total: number }>> {
    const response = await api.get(`/contents/${id}/backlinks`)
    return response.data
  }
}
