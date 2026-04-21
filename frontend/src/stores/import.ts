import { defineStore } from 'pinia'
import { ref } from 'vue'
import { importApi } from '@/api/import'
import { useNotificationStore } from '@/stores/notification'
import { handleApiError } from '@/utils/errorHandler'
import type { ImportTask, ImportHistoryItem, SSEProgressMessage } from '@/types/import'

export const useImportStore = defineStore('import', () => {
  const currentTask = ref<ImportTask | null>(null)
  const isImporting = ref(false)
  const showImportModal = ref(false)
  const showResultModal = ref(false)
  const history = ref<ImportHistoryItem[]>([])
  const historyTotal = ref(0)
  const historyLoading = ref(false)

  let _sseAbortController: AbortController | null = null

  function _startSSE(taskId: string) {
    stopSSE()
    _sseAbortController = new AbortController()

    const token = localStorage.getItem('token')
    const url = `/api/import/status/${taskId}`

    fetch(url, {
      headers: token ? { 'Authorization': `Bearer ${token}` } : {},
      signal: _sseAbortController.signal
    }).then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            if (data === '[DONE]') return

            try {
              const msg = JSON.parse(data) as SSEProgressMessage
              handleSSEMessage(msg)
            } catch {
              // ignore parse errors
            }
          }
        }
      }
    }).catch((error) => {
      if (error.name !== 'AbortError') {
        console.error('SSE connection error:', error)
        fallbackToPolling(taskId)
      }
    })
  }

  function handleSSEMessage(msg: SSEProgressMessage) {
    const notification = useNotificationStore()

    if (msg.type === 'progress') {
      if (currentTask.value) {
        currentTask.value.progress = msg.progress || 0
        currentTask.value.progress_message = msg.message || ''
        currentTask.value.status = 'summarizing'
      }
    } else if (msg.type === 'completed') {
      isImporting.value = false
      showImportModal.value = false
      showResultModal.value = true

      if (currentTask.value && msg.result) {
        currentTask.value.status = 'completed'
        currentTask.value.progress = 100
        currentTask.value.progress_message = '处理完成'
        currentTask.value.result = msg.result
      }
      stopSSE()
    } else if (msg.type === 'error') {
      isImporting.value = false
      stopSSE()
      notification.error('导入失败', msg.message || '处理过程中发生错误')

      if (currentTask.value) {
        currentTask.value.status = 'failed'
        currentTask.value.error = msg.message
      }
    }
  }

  function fallbackToPolling(taskId: string) {
    let pollCount = 0
    const maxPolls = 120

    const timer = setInterval(async () => {
      pollCount++
      if (pollCount > maxPolls) {
        clearInterval(timer)
        return
      }

      try {
        const response = await importApi.getTask(taskId)
        const task = response.data
        currentTask.value = task

        if (task.status === 'completed') {
          clearInterval(timer)
          isImporting.value = false
          showImportModal.value = false
          showResultModal.value = true
        } else if (task.status === 'failed') {
          clearInterval(timer)
          isImporting.value = false
          const notification = useNotificationStore()
          notification.error('导入失败', task.error || '处理过程中发生错误')
        }
      } catch {
        clearInterval(timer)
        isImporting.value = false
      }
    }, 1500)
  }

  function stopSSE() {
    if (_sseAbortController) {
      _sseAbortController.abort()
      _sseAbortController = null
    }
  }

  async function uploadPdf(file: File) {
    const notification = useNotificationStore()
    isImporting.value = true
    currentTask.value = null

    try {
      const response = await importApi.uploadPdf(file)
      const taskId = response.data.task_id

      currentTask.value = {
        task_id: taskId,
        source_type: 'pdf',
        status: 'pending',
        progress: 0,
        progress_message: '正在上传...',
        result: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      _startSSE(taskId)
      notification.success('PDF 上传成功', '正在处理中...')
    } catch (error) {
      isImporting.value = false
      handleApiError(error, '上传失败', '请检查文件格式和大小')
    }
  }

  async function submitUrl(url: string) {
    const notification = useNotificationStore()
    isImporting.value = true
    currentTask.value = null

    try {
      const response = await importApi.submitUrl(url)
      const taskId = response.data.task_id

      currentTask.value = {
        task_id: taskId,
        source_type: 'url',
        status: 'pending',
        progress: 0,
        progress_message: '正在解析...',
        result: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      _startSSE(taskId)
      notification.success('URL 提交成功', '正在处理中...')
    } catch (error) {
      isImporting.value = false
      handleApiError(error, '提交失败', '请检查URL是否正确')
    }
  }

  async function uploadVideo(file: File) {
    const notification = useNotificationStore()
    isImporting.value = true
    currentTask.value = null

    try {
      const response = await importApi.uploadVideo(file)
      const taskId = response.data.task_id

      currentTask.value = {
        task_id: taskId,
        source_type: 'video',
        status: 'pending',
        progress: 0,
        progress_message: '正在上传...',
        result: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      _startSSE(taskId)
      notification.success('视频上传成功', '正在处理中...')
    } catch (error) {
      isImporting.value = false
      handleApiError(error, '上传失败', '请检查文件格式和大小')
    }
  }

  async function submitVideoUrl(url: string) {
    const notification = useNotificationStore()
    isImporting.value = true
    currentTask.value = null

    try {
      const response = await importApi.submitVideoUrl(url)
      const taskId = response.data.task_id

      currentTask.value = {
        task_id: taskId,
        source_type: 'video_url',
        status: 'pending',
        progress: 0,
        progress_message: '正在下载...',
        result: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }

      _startSSE(taskId)
      notification.success('视频链接提交成功', '正在处理中...')
    } catch (error) {
      isImporting.value = false
      handleApiError(error, '提交失败', '请检查URL是否正确')
    }
  }

  async function saveAsNote(data: {
    task_id: string
    title?: string
    summary?: string
    key_points?: string[]
    tags?: string[]
    folder_id?: string | null
  }) {
    const notification = useNotificationStore()
    try {
      const response = await importApi.saveAsNote(data)
      notification.success('保存成功', '已保存为笔记')
      showResultModal.value = false
      currentTask.value = null
      return response.data
    } catch (error) {
      handleApiError(error, '保存失败', '请重试')
      throw error
    }
  }

  async function deleteTask(taskId: string) {
    try {
      await importApi.deleteTask(taskId)
      stopSSE()
      isImporting.value = false
      currentTask.value = null
    } catch (error) {
      console.error('删除任务失败:', error)
    }
  }

  async function fetchHistory(params?: { source_type?: string; page?: number; page_size?: number }) {
    historyLoading.value = true
    try {
      const response = await importApi.getHistory(params)
      history.value = response.data.items
      historyTotal.value = response.data.total
    } catch (error) {
      handleApiError(error, '获取历史失败', '请稍后重试')
    } finally {
      historyLoading.value = false
    }
  }

  function openImportModal() {
    showImportModal.value = true
  }

  function closeImportModal() {
    showImportModal.value = false
    if (currentTask.value && currentTask.value.status !== 'completed') {
      deleteTask(currentTask.value.task_id)
    }
  }

  function closeResultModal() {
    showResultModal.value = false
    currentTask.value = null
  }

  function reset() {
    stopSSE()
    isImporting.value = false
    currentTask.value = null
    showImportModal.value = false
    showResultModal.value = false
  }

  return {
    currentTask,
    isImporting,
    showImportModal,
    showResultModal,
    history,
    historyTotal,
    historyLoading,
    uploadPdf,
    submitUrl,
    uploadVideo,
    submitVideoUrl,
    saveAsNote,
    deleteTask,
    fetchHistory,
    openImportModal,
    closeImportModal,
    closeResultModal,
    reset
  }
})
