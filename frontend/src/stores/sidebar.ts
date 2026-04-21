import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useNotesStore } from './notes'

export const useSidebarStore = defineStore('sidebar', () => {
  const selectedFolderId = ref<string | null>(null)
  const selectedTagId = ref<string | null>(null)

  function selectFolder(folderId: string) {
    if (selectedFolderId.value === folderId) {
      clearFilter()
      return
    }
    selectedFolderId.value = folderId
    selectedTagId.value = null
    const notesStore = useNotesStore()
    notesStore.fetchNotes({ folder_id: folderId })
  }

  function selectTag(tagId: string) {
    if (selectedTagId.value === tagId) {
      clearFilter()
      return
    }
    selectedTagId.value = tagId
    selectedFolderId.value = null
    const notesStore = useNotesStore()
    notesStore.fetchNotes({ tag_id: tagId })
  }

  function clearFilter() {
    selectedFolderId.value = null
    selectedTagId.value = null
    const notesStore = useNotesStore()
    notesStore.fetchNotes()
  }

  return {
    selectedFolderId,
    selectedTagId,
    selectFolder,
    selectTag,
    clearFilter
  }
})
