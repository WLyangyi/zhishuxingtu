import { defineStore } from 'pinia'
import { ref } from 'vue'
import { foldersApi } from '@/api/folders'
import type { FolderTree, FolderCreate, FolderUpdate } from '@/types'

export const useFoldersStore = defineStore('folders', () => {
  const folders = ref<FolderTree[]>([])
  const loading = ref(false)

  async function fetchFolders(categoryId?: string) {
    loading.value = true
    try {
      const response = await foldersApi.list(categoryId)
      folders.value = response.data
    } finally {
      loading.value = false
    }
  }

  async function createFolder(data: FolderCreate) {
    const response = await foldersApi.create(data)
    await fetchFolders()
    return response.data
  }

  async function updateFolder(id: string, data: FolderUpdate) {
    const response = await foldersApi.update(id, data)
    await fetchFolders()
    return response.data
  }

  async function deleteFolder(id: string) {
    await foldersApi.delete(id)
    await fetchFolders()
  }

  return {
    folders,
    loading,
    fetchFolders,
    createFolder,
    updateFolder,
    deleteFolder
  }
})
