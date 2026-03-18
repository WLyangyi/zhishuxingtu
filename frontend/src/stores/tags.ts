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
    const response = await tagsApi.create(data)
    tags.value.push(response.data)
    return response.data
  }

  async function updateTag(id: string, data: TagUpdate) {
    const response = await tagsApi.update(id, data)
    const index = tags.value.findIndex(t => t.id === id)
    if (index !== -1) {
      tags.value[index] = response.data
    }
    return response.data
  }

  async function deleteTag(id: string) {
    await tagsApi.delete(id)
    tags.value = tags.value.filter(t => t.id !== id)
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
