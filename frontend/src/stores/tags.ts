import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tagsApi } from '@/api/tags'
import type { Tag, TagCreate, TagUpdate } from '@/types'

export const useTagsStore = defineStore('tags', () => {
  const tags = ref<Tag[]>([])
  const loading = ref(false)

  async function fetchTags() {
    loading.value = true
    try {
      const response = await tagsApi.list()
      tags.value = response.data
    } finally {
      loading.value = false
    }
  }

  async function createTag(data: TagCreate) {
    try {
      const response = await tagsApi.create(data)
      tags.value.push(response.data)
      return response.data
    } catch (error: any) {
      const message = error?.response?.data?.detail || '创建标签失败'
      throw new Error(message)
    }
  }

  async function updateTag(id: string, data: TagUpdate) {
    try {
      const response = await tagsApi.update(id, data)
      const index = tags.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tags.value[index] = response.data
      }
      return response.data
    } catch (error: any) {
      const message = error?.response?.data?.detail || '更新标签失败'
      throw new Error(message)
    }
  }

  async function deleteTag(id: string) {
    try {
      await tagsApi.delete(id)
      tags.value = tags.value.filter(t => t.id !== id)
    } catch (error: any) {
      const message = error?.response?.data?.detail || '删除标签失败'
      throw new Error(message)
    }
  }

  return {
    tags,
    loading,
    fetchTags,
    createTag,
    updateTag,
    deleteTag
  }
})
