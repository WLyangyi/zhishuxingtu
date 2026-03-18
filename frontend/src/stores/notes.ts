import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { notesApi } from '@/api/notes'
import { useNotificationStore } from '@/stores/notification'
import type { Note, NoteCreate, NoteUpdate, Backlink } from '@/types'

export const useNotesStore = defineStore('notes', () => {
  const notes = ref<Note[]>([])
  const currentNote = ref<Note | null>(null)
  const backlinks = ref<Backlink[]>([])
  const loading = ref(false)

  const notesByFolder = computed(() => {
    const map: Record<string, Note[]> = { 'root': [] }
    notes.value.forEach(note => {
      const folderId = note.folder_id || 'root'
      if (!map[folderId]) {
        map[folderId] = []
      }
      map[folderId].push(note)
    })
    return map
  })

  async function fetchNotes(params?: { folder_id?: string; tag_id?: string }) {
    loading.value = true
    try {
      const response = await notesApi.list(params)
      notes.value = response.data.items
    } catch (error: any) {
      const notification = useNotificationStore()
      notification.error('获取笔记列表失败', error.response?.data?.detail || '网络错误，请稍后重试')
    } finally {
      loading.value = false
    }
  }

  async function getNote(id: string) {
    loading.value = true
    try {
      const response = await notesApi.get(id)
      currentNote.value = response.data
      return response.data
    } catch (error: any) {
      const notification = useNotificationStore()
      notification.error('获取笔记详情失败', error.response?.data?.detail || '笔记不存在或已被删除')
      return null
    } finally {
      loading.value = false
    }
  }

  async function createNote(data: NoteCreate) {
    const notification = useNotificationStore()
    try {
      const response = await notesApi.create(data)
      notes.value.unshift(response.data)
      notification.success('笔记创建成功', `「${data.title}」已保存`)
      return response.data
    } catch (error: any) {
      notification.error('创建笔记失败', error.response?.data?.detail || '网络错误，请稍后重试')
      throw error
    }
  }

  async function updateNote(id: string, data: NoteUpdate) {
    const notification = useNotificationStore()
    try {
      const response = await notesApi.update(id, data)
      const index = notes.value.findIndex(n => n.id === id)
      if (index !== -1) {
        notes.value[index] = response.data
      }
      if (currentNote.value?.id === id) {
        currentNote.value = response.data
      }
      notification.success('笔记更新成功', '内容已保存')
      return response.data
    } catch (error: any) {
      notification.error('更新笔记失败', error.response?.data?.detail || '网络错误，请稍后重试')
      throw error
    }
  }

  async function deleteNote(id: string) {
    const notification = useNotificationStore()
    const noteTitle = notes.value.find(n => n.id === id)?.title || '笔记'
    try {
      await notesApi.delete(id)
      notes.value = notes.value.filter(n => n.id !== id)
      if (currentNote.value?.id === id) {
        currentNote.value = null
      }
      notification.success('笔记删除成功', `「${noteTitle}」已删除`)
    } catch (error: any) {
      notification.error('删除笔记失败', error.response?.data?.detail || '网络错误，请稍后重试')
      throw error
    }
  }

  async function fetchBacklinks(id: string) {
    try {
      const response = await notesApi.getBacklinks(id)
      backlinks.value = response.data
    } catch (error: any) {
      console.error('获取反向链接失败:', error)
    }
  }

  return {
    notes,
    currentNote,
    backlinks,
    loading,
    notesByFolder,
    fetchNotes,
    getNote,
    createNote,
    updateNote,
    deleteNote,
    fetchBacklinks
  }
})
