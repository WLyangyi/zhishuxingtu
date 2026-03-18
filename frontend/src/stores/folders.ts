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
    const response = await foldersApi.create(data)
    await fetchFolders(currentCategoryId.value)
    return response.data
  }

  async function updateFolder(id: string, data: FolderUpdate) {
    const response = await foldersApi.update(id, data)
    await fetchFolders(currentCategoryId.value)
    return response.data
  }

  async function deleteFolder(id: string) {
    await foldersApi.delete(id)
    await fetchFolders(currentCategoryId.value)
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
