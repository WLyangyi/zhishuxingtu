import api from './index'
import type { 
  Category, CategoryCreate, CategoryUpdate,
  ContentType, ContentTypeCreate, ContentTypeUpdate,
  Content, ContentCreate, ContentUpdate, ContentListResponse
} from '@/types/category'

export const categoriesApi = {
  async getCategories(): Promise<Category[]> {
    const response = await api.get('/categories')
    return response.data
  },

  async createCategory(data: CategoryCreate): Promise<Category> {
    const response = await api.post('/categories', data)
    return response.data
  },

  async updateCategory(id: string, data: CategoryUpdate): Promise<Category> {
    const response = await api.put(`/categories/${id}`, data)
    return response.data
  },

  async deleteCategory(id: string): Promise<void> {
    await api.delete(`/categories/${id}`)
  },

  async getContentTypes(categoryId: string): Promise<ContentType[]> {
    const response = await api.get(`/categories/${categoryId}/types`)
    return response.data
  },

  async createContentType(data: ContentTypeCreate): Promise<ContentType> {
    const response = await api.post('/categories/types', data)
    return response.data
  },

  async updateContentType(id: string, data: ContentTypeUpdate): Promise<ContentType> {
    const response = await api.put(`/categories/types/${id}`, data)
    return response.data
  },

  async deleteContentType(id: string): Promise<void> {
    await api.delete(`/categories/types/${id}`)
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
  }): Promise<ContentListResponse> {
    const response = await api.get('/contents', { params })
    return response.data
  },

  async getContent(id: string): Promise<Content> {
    const response = await api.get(`/contents/${id}`)
    return response.data
  },

  async createContent(data: ContentCreate): Promise<Content> {
    const response = await api.post('/contents', data)
    return response.data
  },

  async updateContent(id: string, data: ContentUpdate): Promise<Content> {
    const response = await api.put(`/contents/${id}`, data)
    return response.data
  },

  async deleteContent(id: string): Promise<void> {
    await api.delete(`/contents/${id}`)
  },

  async getBacklinks(id: string): Promise<{ items: { id: string; title: string }[]; total: number }> {
    const response = await api.get(`/contents/${id}/backlinks`)
    return response.data
  }
}
