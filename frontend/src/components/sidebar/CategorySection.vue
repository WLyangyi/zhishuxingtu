<template>
  <div
    class="category-section"
    :class="{ active: isActive }"
  >
    <div class="category-header" @click="$emit('switch', category.id)">
      <div class="category-info">
        <component :is="getCategoryIcon(category.name)" :size="16" class="category-icon" />
        <span class="category-name">{{ category.name }}</span>
        <span class="category-count">{{ noteCount }}</span>
      </div>
      <div class="category-actions">
        <button class="action-btn" @click.stop="toggleCreateMenu">
          <Plus :size="14" />
        </button>
        <div v-if="showCreateMenu" class="create-menu" @click.stop>
          <div class="menu-item" @click="openNewNoteDialog">
            <FileText :size="14" />
            新建笔记
          </div>
          <div class="menu-item" @click="handleOpenNewFolderDialog">
            <Folder :size="14" />
            新建文件夹
          </div>
        </div>
      </div>
    </div>
    <div v-if="isActive" class="folder-list-wrapper">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useFoldersStore } from '@/stores/folders'
import { useNotesStore } from '@/stores/notes'
import type { Category } from '@/types/category'
import { FileText, Folder, Plus, User, Briefcase, TrendingUp } from 'lucide-vue-next'

const props = defineProps<{
  category: Category
  isActive: boolean
}>()

const emit = defineEmits<{
  switch: [categoryId: string]
  openNewFolderDialog: [categoryId: string]
}>()

const router = useRouter()
const foldersStore = useFoldersStore()
const notesStore = useNotesStore()
const showCreateMenu = ref(false)

function getCategoryIcon(name: string) {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('个人')) return User
  if (nameLower.includes('工作')) return Briefcase
  if (nameLower.includes('素材')) return TrendingUp
  return Folder
}

function toggleCreateMenu() {
  showCreateMenu.value = !showCreateMenu.value
}

function openNewNoteDialog() {
  showCreateMenu.value = false
  router.push({ name: 'NewNote', query: { category_id: props.category.id } })
}

function handleOpenNewFolderDialog() {
  showCreateMenu.value = false
  emit('openNewFolderDialog', props.category.id)
}

const noteCount = computed(() => {
  const categoryFolders = foldersStore.folders.filter(f => f.category_id === props.category.id)
  let count = 0
  for (const folder of categoryFolders) {
    count += folder.note_count || 0
  }
  const uncategorizedNotes = notesStore.notes.filter(n => {
    const folder = foldersStore.folders.find(f => f.id === n.folder_id)
    return !folder || folder.category_id === props.category.id
  })
  count += uncategorizedNotes.length
  return count
})

function hideCreateMenu() {
  showCreateMenu.value = false
}

onMounted(() => {
  document.addEventListener('click', hideCreateMenu)
})

onUnmounted(() => {
  document.removeEventListener('click', hideCreateMenu)
})
</script>

<style scoped lang="scss">
.category-section {
  border-bottom: 1px solid var(--border-subtle);

  &.active {
    .category-header {
      background: var(--bg-hover);
    }
  }
}

.category-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
  }
}

.category-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.category-icon {
  color: var(--text-tertiary);
}

.category-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.category-count {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-hover);
  padding: 2px 6px;
  border-radius: 8px;
}

.category-actions {
  position: relative;
}

.action-btn {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.create-menu {
  position: absolute;
  right: 0;
  top: 100%;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 4px 0;
  min-width: 130px;
  z-index: 100;

  .menu-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }
  }
}

.folder-list-wrapper {
  overflow: hidden;
}
</style>
