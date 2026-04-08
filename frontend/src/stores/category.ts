import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { categoriesApi, contentsApi } from '@/api/categories'
import type { 
  Category, CategoryCreate, CategoryUpdate,
  ContentType, ContentTypeCreate,
  Content, ContentCreate, ContentUpdate
} from '@/types/category'
import { useNotificationStore } from './notification'

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
      categories.value = await categoriesApi.getCategories()
    } catch (error: any) {
      notification.error('获取分类失败', error.response?.data?.detail || '操作失败')
    } finally {
      loading.value = false
    }
  }

  async function createCategory(data: CategoryCreate) {
    try {
      const category = await categoriesApi.createCategory(data)
      categories.value.push(category)
      notification.success('分类创建成功')
      return category
    } catch (error: any) {
      notification.error('创建分类失败', error.response?.data?.detail || '操作失败')
      throw error
    }
  }

  async function updateCategory(id: string, data: CategoryUpdate) {
    try {
      const category = await categoriesApi.updateCategory(id, data)
      const index = categories.value.findIndex(c => c.id === id)
      if (index !== -1) {
        categories.value[index] = category
      }
      notification.success('分类更新成功')
      return category
    } catch (error: any) {
      notification.error('更新分类失败', error.response?.data?.detail || '操作失败')
      throw error
    }
  }

  async function deleteCategory(id: string) {
    try {
      await categoriesApi.deleteCategory(id)
      categories.value = categories.value.filter(c => c.id !== id)
      notification.success('分类删除成功')
    } catch (error: any) {
      notification.error('删除分类失败', error.response?.data?.detail || '操作失败')
      throw error
    }
  }

  async function fetchContentTypes(categoryId: string) {
    try {
      contentTypes.value = await categoriesApi.getContentTypes(categoryId)
    } catch (error: any) {
      notification.error('获取内容类型失败', error.response?.data?.detail || '操作失败')
    }
  }

  async function createContentType(data: ContentTypeCreate) {
    try {
      const contentType = await categoriesApi.createContentType(data)
      const category = categories.value.find(c => c.id === data.category_id)
      if (category) {
        category.content_types.push(contentType)
      }
      notification.success('内容类型创建成功')
      return contentType
    } catch (error: any) {
      notification.error('创建内容类型失败', error.response?.data?.detail || '操作失败')
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
      contents.value = response.items
      totalContents.value = response.total
    } catch (error: any) {
      notification.error('获取内容失败', error.response?.data?.detail || '操作失败')
    } finally {
      loading.value = false
    }
  }

  async function getContent(id: string) {
    try {
      loading.value = true
      currentContent.value = await contentsApi.getContent(id)
      return currentContent.value
    } catch (error: any) {
      notification.error('获取内容详情失败', error.response?.data?.detail || '操作失败')
      return null
    } finally {
      loading.value = false
    }
  }

  async function createContent(data: ContentCreate) {
    try {
      const content = await contentsApi.createContent(data)
      contents.value.unshift(content)
      totalContents.value++
      notification.success('内容创建成功')
      return content
    } catch (error: any) {
      notification.error('创建内容失败', error.response?.data?.detail || '操作失败')
      throw error
    }
  }

  async function updateContent(id: string, data: ContentUpdate) {
    try {
      const content = await contentsApi.updateContent(id, data)
      const index = contents.value.findIndex(c => c.id === id)
      if (index !== -1) {
        contents.value[index] = content
      }
      if (currentContent.value?.id === id) {
        currentContent.value = content
      }
      notification.success('内容更新成功')
      return content
    } catch (error: any) {
      notification.error('更新内容失败', error.response?.data?.detail || '操作失败')
      throw error
    }
  }

  async function deleteContent(id: string) {
    try {
      await contentsApi.deleteContent(id)
      contents.value = contents.value.filter(c => c.id !== id)
      totalContents.value--
      notification.success('内容删除成功')
    } catch (error: any) {
      notification.error('删除内容失败', error.response?.data?.detail || '操作失败')
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
