<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">✦</span>
        <span class="logo-text">知枢星图</span>
      </div>
      <div class="header-actions">
        <button class="create-btn" @click="toggleCreateMenu">
          <span class="btn-icon">+</span>
          新建
        </button>
        <div v-if="showCreateDropdown" class="create-dropdown" @click.stop>
          <div class="dropdown-item" @click="createNewNote">
            <FileText :size="16" />
            新建内容
          </div>
          <div class="dropdown-item" @click="openNewFolderDialog(currentCategoryId || undefined)">
            <Folder :size="16" />
            新建文件夹
          </div>
        </div>
      </div>
    </div>

    <div class="sidebar-content">
      <div
        v-for="cat in categories"
        :key="cat.id"
        class="category-section"
        :class="{ active: currentCategoryId === cat.id }"
      >
        <div class="category-header" @click="switchCategory(cat.id)">
          <div class="category-info">
            <component :is="getCategoryIcon(cat.name)" :size="16" class="category-icon" />
            <span class="category-name">{{ cat.name }}</span>
            <span class="category-count">{{ getCategoryNoteCount(cat.id) }}</span>
          </div>
          <div class="category-actions">
            <button class="action-btn" @click.stop="toggleCategoryCreateMenu(cat.id)">
              <Plus :size="14" />
            </button>
            <div v-if="activeCreateMenu === cat.id" class="create-menu" @click.stop>
              <div class="menu-item" @click="openNewNoteDialog(cat.id)">
                <FileText :size="14" />
                新建笔记
              </div>
              <div class="menu-item" @click="openNewFolderDialog(cat.id)">
                <Folder :size="14" />
                新建文件夹
              </div>
            </div>
          </div>
        </div>
        <div v-if="currentCategoryId === cat.id" class="folder-list">
          <div
            class="folder-item"
            :class="{ active: !selectedFolderId && currentCategoryId === cat.id, 'drag-over': dragOverFolderId === null }"
            @click="clearFilter"
            @dragover="onDragOver($event, null)"
            @dragleave="onDragLeave"
            @drop="onDrop($event, null)"
          >
            <span class="folder-icon">
              <Folder :size="16" />
            </span>
            <span>全部内容</span>
            <span class="note-count">{{ getCategoryNoteCount(cat.id) }}</span>
          </div>
          <template v-for="folder in getFoldersByCategory(cat.id)" :key="folder.id">
            <div
              class="folder-item"
              :class="{
                active: selectedFolderId === folder.id,
                editing: editingFolderId === folder.id,
                ['level-' + folder.level]: true,
                'drag-over': dragOverFolderId === folder.id
              }"
              :style="{ paddingLeft: (16 + folder.level * 16) + 'px' }"
              @click="selectFolder(folder.id)"
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
        </div>
      </div>
    </div>

    <div class="sidebar-section tools-section">
      <div class="section-header">
        <h3>工具</h3>
      </div>
      <div class="tool-list">
        <div
          class="tool-item"
          :class="{ active: isCurrentRoute('/personal/search') }"
          @click="goToSearch"
        >
          <Search :size="16" />
          <span>智能检索</span>
        </div>
        <div
          class="tool-item"
          :class="{ active: isCurrentRoute('/graph') || isCurrentRoute('/personal/graph') }"
          @click="goToGraph"
        >
          <GitBranch :size="16" />
          <span>知识图谱</span>
        </div>
        <div
          class="tool-item ai-tool"
          :class="{ active: isCurrentRoute('/personal/ai') }"
          @click="goToAI"
        >
          <Bot :size="16" />
          <span>AI 助手</span>
        </div>
      </div>
    </div>

    <div class="sidebar-section">
      <div class="section-header">
        <h3>标签</h3>
        <button @click="showNewTagDialog = true" class="add-btn">+</button>
      </div>
      <div class="tag-list">
        <span
          v-for="tag in tagsStore.tags"
          :key="tag.id"
          class="tag-item"
          :class="{ active: selectedTagId === tag.id }"
          :style="{
            backgroundColor: selectedTagId === tag.id ? tag.color + '40' : tag.color + '15',
            borderColor: tag.color,
            color: tag.color
          }"
          @click="selectTag(tag.id)"
          @contextmenu.prevent="showTagMenu($event, tag)"
        >
          {{ tag.name }}
          <span class="tag-count">{{ tag.note_count || 0 }}</span>
          <button
            class="tag-menu-btn"
            @click.stop="showTagMenu($event, tag)"
          >
            ⋮
          </button>
        </span>
      </div>
    </div>

    <div class="sidebar-section">
      <div class="section-header">
        <h3>最近内容</h3>
      </div>
      <div class="recent-notes">
        <div
          v-for="note in recentNotes"
          :key="note.id"
          class="note-item"
          tabindex="0"
          role="button"
          @click="openNote(note.id)"
          @keydown.enter="openNote(note.id)"
        >
          <span class="note-dot"></span>
          <span class="note-title-text">{{ note.title }}</span>
        </div>
        <div v-if="notesStore.notes.length === 0" class="empty-hint">
          暂无内容
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="contextMenu.visible"
        class="context-menu"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        @click.stop
      >
        <div class="menu-item" @click="startRename">
          <Edit2 :size="14" />
          重命名
        </div>
        <div class="menu-item" @click="openSubfolderDialog" v-if="contextMenu.folder && contextMenu.folder.level < 3">
          <FolderPlus :size="14" />
          新建子文件夹
        </div>
        <div class="menu-item danger" @click="deleteFolder">
          <Trash2 :size="14" />
          删除文件夹
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div
        v-if="tagContextMenu.visible"
        class="context-menu"
        :style="{ left: tagContextMenu.x + 'px', top: tagContextMenu.y + 'px' }"
        @click.stop
      >
        <div class="menu-item" @click="startEditTag">
          <Edit2 :size="14" />
          编辑标签
        </div>
        <div class="menu-item danger" @click="deleteTag">
          <Trash2 :size="14" />
          删除标签
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showNewFolderDialog" class="modal-overlay" @click="closeFolderDialog">
        <div class="modal-content" @click.stop>
          <h3 class="modal-title">{{ parentFolderId ? '新建子文件夹' : '新建文件夹' }}</h3>
          <div v-if="parentFolder" class="parent-info">
            <span class="parent-label">父文件夹：</span>
            <span class="parent-name">{{ parentFolder.name }}</span>
          </div>
          <input
            v-model="newFolderName"
            type="text"
            class="modal-input"
            placeholder="输入文件夹名称"
            @keyup.enter="createFolder"
            ref="newFolderInput"
          />
          <div class="modal-actions">
            <button class="btn-cancel" @click="closeFolderDialog">取消</button>
            <button class="btn-confirm" @click="createFolder">创建</button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showNewTagDialog" class="modal-overlay" @click="showNewTagDialog = false">
        <div class="modal-content" @click.stop>
          <h3 class="modal-title">新建标签</h3>
          <input
            v-model="newTagName"
            type="text"
            class="modal-input"
            placeholder="输入标签名称"
            @keyup.enter="createTag"
            ref="newTagInput"
          />
          <div class="color-picker">
            <span
              v-for="color in tagColors"
              :key="color"
              class="color-option"
              :class="{ active: newTagColor === color }"
              :style="{ backgroundColor: color }"
              @click="newTagColor = color"
            />
          </div>
          <div class="modal-actions">
            <button class="btn-cancel" @click="showNewTagDialog = false">取消</button>
            <button class="btn-confirm" @click="createTag">创建</button>
          </div>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showEditTagDialog" class="modal-overlay" @click="showEditTagDialog = false">
        <div class="modal-content" @click.stop>
          <h3 class="modal-title">编辑标签</h3>
          <input
            v-model="editTagName"
            type="text"
            class="modal-input"
            placeholder="输入标签名称"
            @keyup.enter="confirmEditTag"
          />
          <div class="color-picker">
            <span
              v-for="color in tagColors"
              :key="color"
              class="color-option"
              :class="{ active: editTagColor === color }"
              :style="{ backgroundColor: color }"
              @click="editTagColor = color"
            />
          </div>
          <div class="modal-actions">
            <button class="btn-cancel" @click="showEditTagDialog = false">取消</button>
            <button class="btn-confirm" @click="confirmEditTag">保存</button>
          </div>
        </div>
      </div>
    </Teleport>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch, h } from 'vue'
import { useRouter } from 'vue-router'
import { useFoldersStore } from '@/stores/folders'
import { useTagsStore } from '@/stores/tags'
import { useNotesStore } from '@/stores/notes'
import { useCategoryStore } from '@/stores/category'
import { useNotificationStore } from '@/stores/notification'
import type { FolderTree, Tag } from '@/types'
import { FileText, Folder, Plus, Edit2, FolderPlus, Trash2, User, Briefcase, TrendingUp, Search, GitBranch, Bot } from 'lucide-vue-next'

const router = useRouter()
const foldersStore = useFoldersStore()
const tagsStore = useTagsStore()
const notesStore = useNotesStore()
const categoryStore = useCategoryStore()
const notification = useNotificationStore()

const selectedFolderId = ref<string | null>(null)
const selectedTagId = ref<string | null>(null)
const showNewFolderDialog = ref(false)
const showNewTagDialog = ref(false)
const newFolderName = ref('')
const newTagName = ref('')
const newTagColor = ref('#f59e0b')
const renameInput = ref<HTMLInputElement | null>(null)
const newFolderInput = ref<HTMLInputElement | null>(null)
const newTagInput = ref<HTMLInputElement | null>(null)
const showCreateDropdown = ref(false)
const parentFolderId = ref<string | null>(null)

const editingFolderId = ref<string | null>(null)
const renameValue = ref('')
const dragOverFolderId = ref<string | null>(null)
const activeCreateMenu = ref<string | null>(null)
const createMenuCategoryId = ref<string | null>(null)

const tagContextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  tag: null as Tag | null
})

const showEditTagDialog = ref(false)
const editTagName = ref('')
const editTagColor = ref('#f59e0b')
const editingTagId = ref<string | null>(null)

const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  folder: null as FolderTree | null
})

const tagColors = [
  '#f59e0b', '#3b82f6', '#10b981', '#ef4444',
  '#8b5cf6', '#ec4899', '#06b6d4', '#6366f1'
]

const categories = computed(() => categoryStore.categories)
const currentCategoryId = computed(() => categoryStore.currentCategory?.id)

const recentNotes = computed(() => notesStore.notes.slice(0, 5))
const totalNoteCount = computed(() => notesStore.notes.length)

const parentFolder = computed(() => {
  if (!parentFolderId.value) return null
  return flatFolders.value.find(f => f.id === parentFolderId.value)
})

interface FlatFolder extends FolderTree {
  level: number
}

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

function getCategoryIcon(name: string) {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('个人')) return User
  if (nameLower.includes('工作')) return Briefcase
  if (nameLower.includes('素材')) return TrendingUp
  return Folder
}

function toggleCategoryCreateMenu(categoryId: string) {
  if (activeCreateMenu.value === categoryId) {
    activeCreateMenu.value = null
  } else {
    activeCreateMenu.value = categoryId
  }
}

function openNewNoteDialog(categoryId: string) {
  activeCreateMenu.value = null
  router.push({ name: 'NewNote', query: { category_id: categoryId } })
}

function openNewFolderDialog(categoryId?: string) {
  showCreateDropdown.value = false
  activeCreateMenu.value = null
  createMenuCategoryId.value = categoryId || currentCategoryId.value || null
  parentFolderId.value = null
  showNewFolderDialog.value = true
}

function openSubfolderDialog() {
  if (!contextMenu.value.folder) return
  parentFolderId.value = contextMenu.value.folder.id
  createMenuCategoryId.value = contextMenu.value.folder.category_id || null
  hideContextMenu()
  showNewFolderDialog.value = true
}

function closeFolderDialog() {
  showNewFolderDialog.value = false
  newFolderName.value = ''
  parentFolderId.value = null
  createMenuCategoryId.value = null
}

function getFoldersByCategory(categoryId: string): FlatFolder[] {
  return flatFolders.value.filter(f => f.category_id === categoryId)
}

function getCategoryNoteCount(categoryId: string): number {
  const categoryFolders = getFoldersByCategory(categoryId)
  let count = 0
  for (const folder of categoryFolders) {
    count += folder.note_count || 0
  }
  const uncategorizedNotes = notesStore.notes.filter(n => {
    const folder = flatFolders.value.find(f => f.id === n.folder_id)
    return !folder || folder.category_id === categoryId
  })
  count += uncategorizedNotes.length
  return count
}

async function switchCategory(categoryId: string) {
  const category = categories.value.find(c => c.id === categoryId)
  if (category) {
    categoryStore.currentCategory = category
    await foldersStore.fetchFolders(categoryId)
    await notesStore.fetchNotes({ folder_id: undefined })
  }
}

onMounted(async () => {
  document.addEventListener('click', hideContextMenu)
  document.addEventListener('click', hideTagContextMenu)
  document.addEventListener('click', hideCreateDropdown)
  await categoryStore.fetchCategories()
  await tagsStore.fetchTags()
  if (categoryStore.categories.length > 0 && !categoryStore.currentCategory) {
    categoryStore.currentCategory = categoryStore.categories[0]
    await foldersStore.fetchFolders(categoryStore.currentCategory.id)
    await notesStore.fetchNotes({ category_id: categoryStore.currentCategory.id })
  } else {
    await foldersStore.fetchFolders()
    await notesStore.fetchNotes()
  }
})

onUnmounted(() => {
  document.removeEventListener('click', hideContextMenu)
  document.removeEventListener('click', hideTagContextMenu)
  document.removeEventListener('click', hideCreateDropdown)
})

function hideCreateDropdown() {
  showCreateDropdown.value = false
}

watch(() => categoryStore.currentCategory, async (newCat) => {
  if (newCat) {
    await foldersStore.fetchFolders(newCat.id)
  }
})

function selectFolder(folderId: string) {
  if (editingFolderId.value) return
  if (selectedFolderId.value === folderId) {
    clearFilter()
    return
  }
  selectedFolderId.value = folderId
  selectedTagId.value = null
  notesStore.fetchNotes({ folder_id: folderId })
}

function selectTag(tagId: string) {
  if (selectedTagId.value === tagId) {
    clearFilter()
    return
  }
  selectedTagId.value = tagId
  selectedFolderId.value = null
  notesStore.fetchNotes({ tag_id: tagId })
}

function clearFilter() {
  selectedFolderId.value = null
  selectedTagId.value = null
  notesStore.fetchNotes()
}

function openNote(noteId: string) {
  router.push(`/notes/${noteId}`)
}

function createNewNote() {
  showCreateDropdown.value = false
  router.push({ name: 'NewNote', query: { category_id: currentCategoryId.value } })
}

function toggleCreateMenu() {
  showCreateDropdown.value = !showCreateDropdown.value
}

function goToCategories() {
  router.push('/categories')
}

function goToGraph() {
  router.push('/graph')
}

function goToSkills() {
  router.push('/skills')
}

function goToSearch() {
  router.push('/personal/search')
}

function goToAI() {
  router.push('/personal/ai')
}

function isCurrentRoute(path: string): boolean {
  return router.currentRoute.value.path === path
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
    renameInput.value?.focus()
    renameInput.value?.select()
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
    if (selectedFolderId.value === folder.id) {
      clearFilter()
    }
  } catch (error: any) {
    notification.error('删除失败', error.response?.data?.detail || '操作失败')
  }
}

async function createFolder() {
  const name = newFolderName.value.trim()
  if (!name) {
    notification.warning('请输入文件夹名称')
    return
  }

  try {
    const folderData: any = { name }
    const targetCategoryId = createMenuCategoryId.value || currentCategoryId.value
    if (targetCategoryId) {
      folderData.category_id = targetCategoryId
    }
    if (parentFolderId.value) {
      folderData.parent_id = parentFolderId.value
    }
    await foldersStore.createFolder(folderData)
    notification.success('创建成功', `文件夹「${name}」已创建`)
    closeFolderDialog()
  } catch (error: any) {
    notification.error('创建失败', error.response?.data?.detail || '操作失败')
  }
}

async function createTag() {
  const name = newTagName.value.trim()
  if (!name) {
    notification.warning('请输入标签名称')
    return
  }

  try {
    await tagsStore.createTag({ name, color: newTagColor.value })
    notification.success('创建成功', `标签「${name}」已创建`)
    showNewTagDialog.value = false
    newTagName.value = ''
    newTagColor.value = '#f59e0b'
  } catch (error: any) {
    notification.error('创建失败', error.response?.data?.detail || '操作失败')
  }
}

function showTagMenu(event: MouseEvent, tag: Tag) {
  tagContextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    tag
  }
}

function hideTagContextMenu() {
  tagContextMenu.value.visible = false
}

function startEditTag() {
  if (!tagContextMenu.value.tag) return
  editingTagId.value = tagContextMenu.value.tag.id
  editTagName.value = tagContextMenu.value.tag.name
  editTagColor.value = tagContextMenu.value.tag.color
  showEditTagDialog.value = true
  hideTagContextMenu()
}

async function confirmEditTag() {
  const name = editTagName.value.trim()
  if (!name) {
    notification.warning('请输入标签名称')
    return
  }

  if (!editingTagId.value) return

  try {
    await tagsStore.updateTag(editingTagId.value, { name, color: editTagColor.value })
    notification.success('编辑成功', `标签已更新为「${name}」`)
    showEditTagDialog.value = false
    editingTagId.value = null
    editTagName.value = ''
    editTagColor.value = '#f59e0b'
  } catch (error: any) {
    notification.error('编辑失败', error.response?.data?.detail || '操作失败')
  }
}

async function deleteTag() {
  if (!tagContextMenu.value.tag) return

  const tag = tagContextMenu.value.tag
  hideTagContextMenu()

  if (!confirm(`确定要删除标签「${tag.name}」吗？`)) {
    return
  }

  try {
    await tagsStore.deleteTag(tag.id)
    notification.success('删除成功', `标签「${tag.name}」已删除`)
    if (selectedTagId.value === tag.id) {
      clearFilter()
    }
  } catch (error: any) {
    notification.error('删除失败', error.response?.data?.detail || '操作失败')
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
</script>

<style scoped lang="scss">
.sidebar {
  width: 260px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  padding: 0;
  position: relative;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  position: relative;
}

.create-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: var(--primary-color);
  border: none;
  border-radius: var(--radius-sm);
  color: #000;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--primary-hover);
  }

  .btn-icon {
    font-size: 14px;
  }
}

.create-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 4px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 4px 0;
  min-width: 140px;
  z-index: 100;

  .dropdown-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    font-size: 13px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all var(--transition-fast);

    &:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }
  }
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;

  .logo-icon {
    font-size: 20px;
    color: var(--primary-color);
  }

  .logo-text {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

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

.sidebar-section {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.tools-section {
  .tool-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .tool-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    font-size: 13px;
    color: var(--text-secondary);
    transition: all var(--transition-fast);

    &:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }

    &.active {
      background: var(--bg-active);
      color: var(--text-primary);
    }

    &.ai-tool {
      color: var(--primary-color);
      
      &:hover {
        background: var(--primary-muted);
      }
      
      &.active {
        background: var(--primary-muted);
        font-weight: 500;
      }
    }
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;

  h3 {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .add-btn {
    width: 20px;
    height: 20px;
    border: 1px solid var(--border-default);
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--text-tertiary);
    cursor: pointer;
    font-size: 12px;
    line-height: 1;
    transition: all var(--transition-fast);

    &:hover {
      background: var(--bg-hover);
      border-color: var(--border-strong);
      color: var(--text-primary);
    }
  }
}

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

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-item {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: 4px;
  position: relative;

  &:hover {
    transform: translateY(-1px);
  }

  &.active {
    box-shadow: 0 0 0 1px currentColor;
  }

  .tag-count {
    font-size: 10px;
    opacity: 0.7;
  }

  .tag-menu-btn {
    position: absolute;
    right: 2px;
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: inherit;
    cursor: pointer;
    opacity: 0;
    transition: all var(--transition-fast);
    font-size: 10px;
    border-radius: 4px;

    &:hover {
      opacity: 1;
    }
  }
}

.recent-notes {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.note-item {
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: 8px;

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);

    .note-dot {
      background: var(--primary-color);
    }
  }

  &:focus {
    outline: none;
    background: var(--bg-active);
  }

  .note-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--text-muted);
    transition: background var(--transition-fast);
    flex-shrink: 0;
  }

  .note-title-text {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.empty-hint {
  padding: 16px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12px;
}

.context-menu {
  position: fixed;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 4px 0;
  min-width: 150px;
  z-index: 1000;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }

  &.danger {
    color: var(--accent-red);

    &:hover {
      background: rgba(239, 68, 68, 0.1);
    }
  }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 20px;
  min-width: 300px;
}

.modal-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.parent-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-hover);
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  
  .parent-label {
    font-size: 12px;
    color: var(--text-muted);
  }
  
  .parent-name {
    font-size: 13px;
    color: var(--text-primary);
    font-weight: 500;
  }
}

.modal-input {
  width: 100%;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 14px;
  margin-bottom: 12px;

  &:focus {
    outline: none;
    border-color: var(--primary-color);
  }

  &::placeholder {
    color: var(--text-muted);
  }
}

.color-picker {
  display: flex;
  gap: 6px;
  margin-bottom: 16px;
}

.color-option {
  display: inline-block;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 2px solid transparent;

  &:hover {
    transform: scale(1.1);
  }

  &.active {
    border-color: var(--text-primary);
  }
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.btn-cancel, .btn-confirm {
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-cancel {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);

  &:hover {
    border-color: var(--border-strong);
    color: var(--text-primary);
  }
}

.btn-confirm {
  background: var(--primary-color);
  border: none;
  color: #000;

  &:hover {
    background: var(--primary-hover);
  }
}
</style>
