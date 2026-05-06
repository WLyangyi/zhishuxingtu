import { defineStore } from 'pinia'
import { ref } from 'vue'
import { foldersApi } from '@/api/folders'
import type { FolderTree, FolderCreate, FolderUpdate } from '@/types'

export const useFoldersStore = defineStore('folders', () => {
  const folders = ref<FolderTree[]>([])
  const loading = ref(false)
  const currentCategoryId = ref<string | undefined>(undefined)

  async function fetchFolders(categoryId?: string) {
    loading.value = true
    currentCategoryId.value = categoryId
    try {
      const response = await foldersApi.list(categoryId)
      folders.value = response.data
    } finally {
      loading.value = false
    }
  }

  async function createFolder(data: FolderCreate) {
    try {
      const response = await foldersApi.create(data)
      await fetchFolders(currentCategoryId.value)
      return response.data
    } catch (error: any) {
      const message = error?.response?.data?.detail || '创建文件夹失败'
      throw new Error(message)
    }
  }

  async function updateFolder(id: string, data: FolderUpdate) {
    try {
      const response = await foldersApi.update(id, data)
      await fetchFolders(currentCategoryId.value)
      return response.data
    } catch (error: any) {
      const message = error?.response?.data?.detail || '更新文件夹失败'
      throw new Error(message)
    }
  }

  async function deleteFolder(id: string) {
    try {
      await foldersApi.delete(id)
      await fetchFolders(currentCategoryId.value)
    } catch (error: any) {
      const message = error?.response?.data?.detail || '删除文件夹失败'
      throw new Error(message)
    }
  }

  return {
    folders,
    loading,
    currentCategoryId,
    fetchFolders,
    createFolder,
    updateFolder,
    deleteFolder
  }
})
