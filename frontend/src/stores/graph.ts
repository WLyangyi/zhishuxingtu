import { defineStore } from 'pinia'
import { ref, shallowRef } from 'vue'
import { graphApi } from '@/api/graph'
import type { GraphData } from '@/types/graph'

/**
 * 全局图谱缓存：进入页面先用上次数据渲染，后台带 ETag 静默刷新。
 * 304 不替换 data 引用，视图据此跳过力导向布局重算。
 */
export const useGraphStore = defineStore('graph', () => {
  const data = shallowRef<GraphData | null>(null)
  const etag = ref<string | null>(null)
  const fetchedAt = ref(0)
  const refreshing = ref(false)
  const error = ref('')

  async function fetchGlobal(force = false) {
    refreshing.value = true
    try {
      const result = await graphApi.getGlobal(force ? undefined : etag.value ?? undefined)
      if (!result.notModified && result.response) {
        data.value = result.response.data
      }
      if (result.etag) etag.value = result.etag
      fetchedAt.value = Date.now()
      error.value = ''
    } catch {
      error.value = '星图加载失败，请检查网络或稍后重试。'
    } finally {
      refreshing.value = false
    }
    return data.value
  }

  async function load(force = false) {
    if (data.value && !force) {
      void fetchGlobal(false) // 缓存先行，网络刷新不阻塞首屏
      return data.value
    }
    return fetchGlobal(force)
  }

  return { data, etag, fetchedAt, refreshing, error, load, fetchGlobal }
})
