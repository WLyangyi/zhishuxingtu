<template>
  <div class="folder-list">
    <div
      class="folder-item"
      :class="{ active: !sidebarStore.selectedFolderId && isActiveCategory, 'drag-over': dragOverFolderId === null }"
      @click="sidebarStore.clearFilter()"
      @dragover="onDragOver($event, null)"
      @dragleave="onDragLeave"
      @drop="onDrop($event, null)"
    >
      <span class="folder-icon">
        <Folder :size="16" />
      </span>
      <span>全部内容</span>
      <span class="note-count">{{ totalNoteCount }}</span>
    </div>
    <template v-for="folder in folders" :key="folder.id">
      <div
        class="folder-item"
        :class="{
          active: sidebarStore.selectedFolderId === folder.id,
          editing: editingFolderId === folder.id,
          ['level-' + folder.level]: true,
          'drag-over': dragOverFolderId === folder.id
        }"
        :style="{ paddingLeft: (16 + folder.level * 16) + 'px' }"
        @click="handleFolderClick(folder.id)"
        @contextmenu.prevent="showFolderMenu($event, folder)"
        @dragover="onDragOver($event, folder.id)"
        @dragleave="onDragLeave"
        @drop="onDrop($event, folder.id)"
      >
        <template v-if="editingFolderId === folder.id">
          <input
            ref="renameInput"
            v-model="renameValue"
            type="text"
            class="rename-input"
            placeholder="输入文件夹名称"
            @click.stop
            @keyup.enter="confirmRename"
            @keyup.escape="cancelRename"
            @blur="confirmRename"
          />
        </template>
        <template v-else>
          <span class="folder-icon">
            <Folder :size="16" />
          </span>
          <span class="folder-name">{{ folder.name }}</span>
          <span class="note-count">{{ folder.note_count || 0 }}</span>
          <button
            class="folder-menu-btn"
            @click.stop="showFolderMenu($event, folder)"
          >
            ⋮
          </button>
        </template>
      </div>
    </template>

    <FolderContextMenu
      :visible="contextMenu.visible"
      :x="contextMenu.x"
      :y="contextMenu.y"
      :folder="contextMenu.folder"
      @rename="startRename"
      @create-subfolder="openSubfolderDialog"
      @delete="deleteFolder"
    />

    <CreateFolderDialog
      :visible="showCreateDialog"
      :parent-folder="parentFolder"
      @confirm="handleCreateFolder"
      @cancel="closeCreateDialog"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useSidebarStore } from '@/stores/sidebar'
import { useFoldersStore } from '@/stores/folders'
import { useNotesStore } from '@/stores/notes'
import { useNotificationStore } from '@/stores/notification'
import type { FolderTree } from '@/types'
import { Folder } from 'lucide-vue-next'
import FolderContextMenu from './FolderContextMenu.vue'
import CreateFolderDialog from './CreateFolderDialog.vue'

interface FlatFolder extends FolderTree {
  level: number
}

const props = defineProps<{
  categoryId: string
  isActiveCategory: boolean
}>()

const sidebarStore = useSidebarStore()
const foldersStore = useFoldersStore()
const notesStore = useNotesStore()
const notification = useNotificationStore()

const editingFolderId = ref<string | null>(null)
const renameValue = ref('')
const renameInput = ref<HTMLInputElement[] | null>(null)
const dragOverFolderId = ref<string | null>(null)

const showCreateDialog = ref(false)
const parentFolderId = ref<string | null>(null)
const createMenuCategoryId = ref<string | null>(null)

const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  folder: null as FolderTree | null
})

const flatFolders = computed(() => {
  const result: FlatFolder[] = []
  function flatten(folders: FolderTree[], level: number = 0) {
    for (const folder of folders) {
      result.push({ ...folder, level })
      if (folder.children && folder.children.length > 0) {
        flatten(folder.children, level + 1)
      }
    }
  }
  flatten(foldersStore.folders)
  return result
})

const folders = computed(() => flatFolders.value.filter(f => f.category_id === props.categoryId))

const totalNoteCount = computed(() => {
  return folders.value.reduce((sum, f) => sum + (f.note_count || 0), 0)
})

const parentFolder = computed(() => {
  if (!parentFolderId.value) return null
  return flatFolders.value.find(f => f.id === parentFolderId.value) || null
})

function handleFolderClick(folderId: string) {
  if (editingFolderId.value) return
  sidebarStore.selectFolder(folderId)
}

function showFolderMenu(event: MouseEvent, folder: FolderTree) {
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    folder
  }
}

function hideContextMenu() {
  contextMenu.value.visible = false
}

function startRename() {
  if (!contextMenu.value.folder) return
  editingFolderId.value = contextMenu.value.folder.id
  renameValue.value = contextMenu.value.folder.name
  hideContextMenu()
  nextTick(() => {
    const inputs = renameInput.value
    if (inputs && inputs.length > 0) {
      inputs[0].focus()
      inputs[0].select()
    }
  })
}

async function confirmRename() {
  if (!editingFolderId.value) return
  const newName = renameValue.value.trim()
  if (!newName) {
    notification.error('重命名失败', '文件夹名称不能为空')
    cancelRename()
    return
  }
  try {
    await foldersStore.updateFolder(editingFolderId.value, { name: newName })
    notification.success('重命名成功', `文件夹已重命名为「${newName}」`)
  } catch (error: any) {
    notification.error('重命名失败', error.response?.data?.detail || '操作失败')
  } finally {
    editingFolderId.value = null
    renameValue.value = ''
  }
}

function cancelRename() {
  editingFolderId.value = null
  renameValue.value = ''
}

async function deleteFolder() {
  if (!contextMenu.value.folder) return
  const folder = contextMenu.value.folder
  hideContextMenu()
  if (!confirm(`确定要删除文件夹「${folder.name}」吗？\n文件夹必须为空才能删除。`)) {
    return
  }
  try {
    await foldersStore.deleteFolder(folder.id)
    notification.success('删除成功', `文件夹「${folder.name}」已删除`)
    if (sidebarStore.selectedFolderId === folder.id) {
      sidebarStore.clearFilter()
    }
  } catch (error: any) {
    notification.error('删除失败', error.response?.data?.detail || '操作失败')
  }
}

function openSubfolderDialog() {
  if (!contextMenu.value.folder) return
  parentFolderId.value = contextMenu.value.folder.id
  createMenuCategoryId.value = contextMenu.value.folder.category_id || null
  hideContextMenu()
  showCreateDialog.value = true
}

function openCreateDialog(categoryId?: string) {
  createMenuCategoryId.value = categoryId || props.categoryId || null
  parentFolderId.value = null
  showCreateDialog.value = true
}

function closeCreateDialog() {
  showCreateDialog.value = false
  parentFolderId.value = null
  createMenuCategoryId.value = null
}

async function handleCreateFolder(name: string) {
  if (!name) {
    notification.warning('请输入文件夹名称')
    return
  }
  try {
    const folderData: any = { name }
    const targetCategoryId = createMenuCategoryId.value || props.categoryId
    if (targetCategoryId) {
      folderData.category_id = targetCategoryId
    }
    if (parentFolderId.value) {
      folderData.parent_id = parentFolderId.value
    }
    await foldersStore.createFolder(folderData)
    notification.success('创建成功', `文件夹「${name}」已创建`)
    closeCreateDialog()
  } catch (error: any) {
    notification.error('创建失败', error.response?.data?.detail || '操作失败')
  }
}

function onDragOver(event: DragEvent, folderId: string | null) {
  event.preventDefault()
  dragOverFolderId.value = folderId
}

function onDragLeave() {
  dragOverFolderId.value = null
}

async function onDrop(event: DragEvent, folderId: string | null) {
  event.preventDefault()
  const noteId = event.dataTransfer?.getData('text/plain')
  if (noteId) {
    try {
      await notesStore.updateNote(noteId, { folder_id: folderId })
      notification.success('移动成功', '笔记已移动到目标文件夹')
    } catch (error: any) {
      notification.error('移动失败', error.response?.data?.detail || '操作失败')
    }
  }
  dragOverFolderId.value = null
}

onMounted(() => {
  document.addEventListener('click', hideContextMenu)
})

onUnmounted(() => {
  document.removeEventListener('click', hideContextMenu)
})

defineExpose({
  openCreateDialog
})
</script>

<style scoped lang="scss">
.folder-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.folder-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
  position: relative;
  font-size: 13px;
  color: var(--text-secondary);

  &:hover {
    background: var(--bg-hover);

    .folder-menu-btn {
      opacity: 1;
    }
  }

  &.active {
    background: var(--bg-active);
    border-color: var(--border-default);
    color: var(--text-primary);
  }

  &.editing {
    background: var(--bg-active);
    border-color: var(--primary-color);
    padding: 6px 12px;
  }

  &.drag-over {
    background: var(--primary-muted);
    border-color: var(--primary-color);
  }

  .folder-icon {
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .folder-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .note-count {
    font-size: 11px;
    color: var(--text-muted);
  }

  .folder-menu-btn {
    position: absolute;
    right: 8px;
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    opacity: 0;
    transition: all var(--transition-fast);
    font-size: 12px;

    &:hover {
      color: var(--text-primary);
    }
  }
}

.rename-input {
  flex: 1;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 4px 8px;
  color: var(--text-primary);
  font-size: 13px;

  &:focus {
    outline: none;
    border-color: var(--primary-color);
  }

  &::placeholder {
    color: var(--text-muted);
  }
}
</style>
