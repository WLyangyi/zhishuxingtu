import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { categoriesApi, contentsApi } from '@/api/categories'
import { useNotificationStore } from './notification'
import { handleApiError } from '@/utils/errorHandler'
import type {
  Category, CategoryCreate, CategoryUpdate,
  ContentType, ContentTypeCreate,
  Content, ContentCreate, ContentUpdate
} from '@/types/category'

export const useCategoryStore = defineStore('category', () => {
  const notification = useNotificationStore()

  const categories = ref<Category[]>([])
  const currentCategory = ref<Category | null>(null)
  const contentTypes = ref<ContentType[]>([])
  const contents = ref<Content[]>([])
  const currentContent = ref<Content | null>(null)
  const totalContents = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const loading = ref(false)

  const categoriesWithTypes = computed(() => categories.value)

  async function fetchCategories() {
    try {
      loading.value = true
      const response = await categoriesApi.getCategories()
      categories.value = response.data || []
    } catch (error) {
      handleApiError(error, '获取分类失败', '操作失败')
    } finally {
      loading.value = false
    }
  }

  async function createCategory(data: CategoryCreate) {
    try {
      const response = await categoriesApi.createCategory(data)
      categories.value.push(response.data)
      notification.success('分类创建成功')
      return response.data
    } catch (error) {
      handleApiError(error, '创建分类失败', '操作失败')
      throw error
    }
  }

  async function updateCategory(id: string, data: CategoryUpdate) {
    try {
      const response = await categoriesApi.updateCategory(id, data)
      const index = categories.value.findIndex(c => c.id === id)
      if (index !== -1) {
        categories.value[index] = response.data
      }
      notification.success('分类更新成功')
      return response.data
    } catch (error) {
      handleApiError(error, '更新分类失败', '操作失败')
      throw error
    }
  }

  async function deleteCategory(id: string) {
    try {
      await categoriesApi.deleteCategory(id)
      categories.value = categories.value.filter(c => c.id !== id)
      notification.success('分类删除成功')
    } catch (error) {
      handleApiError(error, '删除分类失败', '操作失败')
      throw error
    }
  }

  async function fetchContentTypes(categoryId: string) {
    try {
      const response = await categoriesApi.getContentTypes(categoryId)
      contentTypes.value = response.data || []
    } catch (error) {
      handleApiError(error, '获取内容类型失败', '操作失败')
    }
  }

  async function createContentType(data: ContentTypeCreate) {
    try {
      const response = await categoriesApi.createContentType(data)
      const category = categories.value.find(c => c.id === data.category_id)
      if (category) {
        category.content_types.push(response.data)
      }
      notification.success('内容类型创建成功')
      return response.data
    } catch (error) {
      handleApiError(error, '创建内容类型失败', '操作失败')
      throw error
    }
  }

  async function fetchContents(params?: {
    category_id?: string
    type_id?: string
    tag_id?: string
    keyword?: string
  }) {
    try {
      loading.value = true
      const response = await contentsApi.getContents({
        ...params,
        page: currentPage.value,
        page_size: pageSize.value
      })
      contents.value = response.data.items || []
      totalContents.value = response.data.total || 0
    } catch (error) {
      handleApiError(error, '获取内容失败', '操作失败')
    } finally {
      loading.value = false
    }
  }

  async function getContent(id: string) {
    try {
      loading.value = true
      const response = await contentsApi.getContent(id)
      currentContent.value = response.data
      return response.data
    } catch (error) {
      handleApiError(error, '获取内容详情失败', '操作失败')
      return null
    } finally {
      loading.value = false
    }
  }

  async function createContent(data: ContentCreate) {
    try {
      const response = await contentsApi.createContent(data)
      contents.value.unshift(response.data)
      totalContents.value++
      notification.success('内容创建成功')
      return response.data
    } catch (error) {
      handleApiError(error, '创建内容失败', '操作失败')
      throw error
    }
  }

  async function updateContent(id: string, data: ContentUpdate) {
    try {
      const response = await contentsApi.updateContent(id, data)
      const index = contents.value.findIndex(c => c.id === id)
      if (index !== -1) {
        contents.value[index] = response.data
      }
      if (currentContent.value?.id === id) {
        currentContent.value = response.data
      }
      notification.success('内容更新成功')
      return response.data
    } catch (error) {
      handleApiError(error, '更新内容失败', '操作失败')
      throw error
    }
  }

  async function deleteContent(id: string) {
    try {
      await contentsApi.deleteContent(id)
      contents.value = contents.value.filter(c => c.id !== id)
      totalContents.value--
      notification.success('内容删除成功')
    } catch (error) {
      handleApiError(error, '删除内容失败', '操作失败')
      throw error
    }
  }

  function setPage(page: number) {
    currentPage.value = page
  }

  function setPageSize(size: number) {
    pageSize.value = size
  }

  return {
    categories,
    currentCategory,
    contentTypes,
    contents,
    currentContent,
    totalContents,
    currentPage,
    pageSize,
    loading,
    categoriesWithTypes,
    fetchCategories,
    createCategory,
    updateCategory,
    deleteCategory,
    fetchContentTypes,
    createContentType,
    fetchContents,
    getContent,
    createContent,
    updateContent,
    deleteContent,
    setPage,
    setPageSize
  }
})
