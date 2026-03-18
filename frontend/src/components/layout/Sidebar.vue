<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo">
        <span class="logo-icon">✦</span>
        <span class="logo-text">知枢星图</span>
      </div>
    </div>

    <div class="category-tabs">
      <button
        v-for="cat in categories"
        :key="cat.id"
        class="category-tab"
        :class="{ active: currentCategoryId === cat.id }"
        :style="{
          '--tab-color': cat.color
        }"
        @click="switchCategory(cat.id)"
      >
        <component :is="getCategoryIcon(cat.name)" />
      </button>
    </div>

    <div class="sidebar-section quick-nav">
      <div class="nav-item" @click="goToCategories">
        <span class="nav-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/>
          </svg>
        </span>
        <span>内容分类</span>
      </div>
      <div class="nav-item" @click="goToGraph">
        <span class="nav-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <circle cx="19" cy="5" r="2"/>
            <circle cx="5" cy="19" r="2"/>
            <path d="M10.4 10.5 5 5"/>
            <path d="M13.6 13.5 19 19"/>
          </svg>
        </span>
        <span>知识图谱</span>
      </div>
      <div class="nav-item" @click="goToSkills">
        <span class="nav-icon">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>
          </svg>
        </span>
        <span>智能模块</span>
      </div>
    </div>

    <div class="sidebar-section">
      <div class="section-header">
        <h3>文件夹</h3>
        <button @click="showNewFolderDialog = true" class="add-btn">+</button>
      </div>
      <div class="folder-list">
        <div
          class="folder-item"
          :class="{ active: !selectedFolderId, 'drag-over': dragOverFolderId === null }"
          @click="clearFilter"
          @dragover="onDragOver($event, null)"
          @dragleave="onDragLeave"
          @drop="onDrop($event, null)"
        >
          <span class="folder-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19.5 21a3 3 0 0 0 3-3v-4.5a3 3 0 0 0-3-3h-15a3 3 0 0 0-3 3V18a3 3 0 0 0 3 3h15zM1.5 10.146V6a3 3 0 0 1 3-3h5.379a2.25 2.25 0 0 1 1.59.659l2.122 2.121c.14.141.331.22.53.22H19.5a3 3 0 0 1 3 3v1.146A4.483 4.483 0 0 0 19.5 9h-15a4.483 4.483 0 0 0-3 1.146z"/>
            </svg>
          </span>
          <span>全部内容</span>
          <span class="note-count">{{ totalNoteCount }}</span>
        </div>
        <template v-for="folder in flatFolders" :key="folder.id">
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
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19.5 21a3 3 0 0 0 3-3v-4.5a3 3 0 0 0-3-3h-15a3 3 0 0 0-3 3V18a3 3 0 0 0 3 3h15zM1.5 10.146V6a3 3 0 0 1 3-3h5.379a2.25 2.25 0 0 1 1.59.659l2.122 2.121c.14.141.331.22.53.22H19.5a3 3 0 0 1 3 3v1.146A4.483 4.483 0 0 0 19.5 9h-15a4.483 4.483 0 0 0-3 1.146z"/>
                </svg>
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

    <button @click="createNewNote" class="new-note-btn">
      <span class="btn-icon">+</span>
      <span>新建笔记</span>
    </button>

    <Teleport to="body">
      <div
        v-if="contextMenu.visible"
        class="context-menu"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
        @click.stop
      >
        <div class="menu-item" @click="startRename">
          <span class="menu-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
            </svg>
          </span>
          重命名
        </div>
        <div class="menu-item danger" @click="deleteFolder">
          <span class="menu-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 6h18"/>
              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>
              <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
            </svg>
          </span>
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
          <span class="menu-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
            </svg>
          </span>
          编辑标签
        </div>
        <div class="menu-item danger" @click="deleteTag">
          <span class="menu-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 6h18"/>
              <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/>
            </svg>
          </span>
          删除标签
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showNewFolderDialog" class="modal-overlay" @click="showNewFolderDialog = false">
        <div class="modal-content" @click.stop>
          <h3 class="modal-title">新建文件夹</h3>
          <input
            v-model="newFolderName"
            type="text"
            class="modal-input"
            placeholder="输入文件夹名称"
            @keyup.enter="createFolder"
            ref="newFolderInput"
          />
          <div class="modal-actions">
            <button class="btn-cancel" @click="showNewFolderDialog = false">取消</button>
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
const newTagColor = ref('#00d4ff')
const renameInput = ref<HTMLInputElement | null>(null)
const newFolderInput = ref<HTMLInputElement | null>(null)
const newTagInput = ref<HTMLInputElement | null>(null)

const editingFolderId = ref<string | null>(null)
const renameValue = ref('')
const dragOverFolderId = ref<string | null>(null)

const tagContextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  tag: null as Tag | null
})

const showEditTagDialog = ref(false)
const editTagName = ref('')
const editTagColor = ref('#00d4ff')
const editingTagId = ref<string | null>(null)

const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  folder: null as FolderTree | null
})

const tagColors = [
  '#00d4ff', '#7b2cbf', '#10b981', '#f59e0b',
  '#ef4444', '#ec4899', '#8b5cf6', '#06b6d4'
]

const categories = computed(() => categoryStore.categories)
const currentCategoryId = computed(() => categoryStore.currentCategory?.id)

const recentNotes = computed(() => notesStore.notes.slice(0, 5))
const totalNoteCount = computed(() => notesStore.notes.length)

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

const categoryIcons: Record<string, () => any> = {
  user: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('circle', { cx: '12', cy: '8', r: '5' }),
    h('path', { d: 'M20 21a8 8 0 0 0-16 0' })
  ]),
  briefcase: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('rect', { width: '20', height: '14', x: '2', y: '7', rx: '2', ry: '2' }),
    h('path', { d: 'M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16' })
  ]),
  assets: () => h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2' }, [
    h('path', { d: 'm21 8-9 9-4-4-3 3' }),
    h('rect', { width: '6', height: '6', x: '15', y: '3', rx: '1' })
  ])
}

function getCategoryIcon(name: string) {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('个人')) return categoryIcons.user
  if (nameLower.includes('工作')) return categoryIcons.briefcase
  if (nameLower.includes('素材')) return categoryIcons.assets
  return categoryIcons.assets
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
  await categoryStore.fetchCategories()
  if (categoryStore.categories.length > 0 && !categoryStore.currentCategory) {
    categoryStore.currentCategory = categoryStore.categories[0]
    await foldersStore.fetchFolders(categoryStore.currentCategory.id)
  } else {
    await foldersStore.fetchFolders()
  }
})

onUnmounted(() => {
  document.removeEventListener('click', hideContextMenu)
  document.removeEventListener('click', hideTagContextMenu)
})

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
  router.push({ name: 'NewNote' })
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
    if (currentCategoryId.value) {
      folderData.category_id = currentCategoryId.value
    }
    await foldersStore.createFolder(folderData)
    notification.success('创建成功', `文件夹「${name}」已创建`)
    showNewFolderDialog.value = false
    newFolderName.value = ''
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
    newTagColor.value = '#00d4ff'
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
    editTagColor.value = '#00d4ff'
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
  width: 280px;
  background: linear-gradient(180deg, #0d0d1a 0%, #0a0a14 100%);
  border-right: 1px solid rgba(0, 212, 255, 0.1);
  display: flex;
  flex-direction: column;
  padding: 0;
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 1px;
    height: 100%;
    background: linear-gradient(180deg,
      transparent 0%,
      rgba(0, 212, 255, 0.3) 50%,
      transparent 100%
    );
    pointer-events: none;
  }
}

.sidebar-header {
  padding: 20px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;

  .logo-icon {
    font-size: 24px;
    background: linear-gradient(135deg, #00d4ff, #7b2cbf);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .logo-text {
    font-size: 18px;
    font-weight: 700;
    background: linear-gradient(135deg, #00d4ff, #7b2cbf);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
}

.category-tabs {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.category-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  cursor: pointer;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.3s;

  svg {
    width: 16px;
    height: 16px;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.06);
    color: rgba(255, 255, 255, 0.8);
  }

  &.active {
    background: rgba(255, 255, 255, 0.08);
    border-color: var(--tab-color, #00d4ff);
    color: var(--tab-color, #00d4ff);
    box-shadow: 0 0 12px rgba(0, 212, 255, 0.2);
  }
}

.sidebar-section {
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);

  &.quick-nav {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px 16px;
  }
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 10px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  transition: all 0.2s;

  &:hover {
    background: rgba(0, 212, 255, 0.1);
    border-color: rgba(0, 212, 255, 0.3);
    color: #fff;
  }

  .nav-icon {
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;

    svg {
      width: 100%;
      height: 100%;
    }
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;

  h3 {
    font-size: 11px;
    font-weight: 600;
    color: rgba(255, 255, 255, 0.4);
    text-transform: uppercase;
    letter-spacing: 1px;
  }

  .add-btn {
    width: 22px;
    height: 22px;
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 6px;
    background: transparent;
    color: #00d4ff;
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
    transition: all 0.2s;

    &:hover {
      background: rgba(0, 212, 255, 0.1);
      border-color: #00d4ff;
      box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
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
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  position: relative;

  &.level-1 {
    font-size: 13px;

    .folder-icon {
      color: rgba(0, 212, 255, 0.6);
    }
  }

  &:hover {
    background: rgba(255, 255, 255, 0.03);

    .folder-menu-btn {
      opacity: 1;
    }
  }

  &.active {
    background: rgba(0, 212, 255, 0.08);
    border-color: rgba(0, 212, 255, 0.3);

    .folder-icon {
      transform: scale(1.1);
    }
  }

  &.editing {
    background: rgba(0, 212, 255, 0.1);
    border-color: rgba(0, 212, 255, 0.4);
    padding: 6px 12px;
  }

  &.drag-over {
    background: rgba(0, 212, 255, 0.2) !important;
    border-color: #00d4ff !important;
  }

  .folder-icon {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    transition: transform 0.2s;
    color: rgba(0, 212, 255, 0.8);

    svg {
      width: 100%;
      height: 100%;
    }
  }

  .folder-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .note-count {
    font-size: 11px;
    color: rgba(255, 255, 255, 0.3);
    background: rgba(255, 255, 255, 0.05);
    padding: 2px 8px;
    border-radius: 10px;
  }

  .folder-menu-btn {
    position: absolute;
    right: 8px;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.4);
    cursor: pointer;
    opacity: 0;
    transition: all 0.2s;
    font-size: 14px;

    &:hover {
      color: #00d4ff;
    }
  }
}

.rename-input {
  flex: 1;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 212, 255, 0.4);
  border-radius: 6px;
  padding: 6px 10px;
  color: #fff;
  font-size: 13px;

  &:focus {
    outline: none;
    border-color: #00d4ff;
    box-shadow: 0 0 10px rgba(0, 212, 255, 0.2);
  }

  &::placeholder {
    color: rgba(255, 255, 255, 0.3);
  }
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;

  &:hover {
    transform: translateY(-1px);

    .tag-menu-btn {
      opacity: 1;
    }
  }

  &.active {
    box-shadow: 0 0 15px currentColor;
  }

  .tag-count {
    font-size: 10px;
    opacity: 0.7;
  }

  .tag-menu-btn {
    position: absolute;
    right: 4px;
    width: 18px;
    height: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.4);
    cursor: pointer;
    opacity: 0;
    transition: all 0.2s;
    font-size: 12px;
    border-radius: 4px;

    &:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.1);
    }
  }
}

.recent-notes {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.note-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 10px;

  &:hover {
    background: rgba(255, 255, 255, 0.03);
    color: #fff;

    .note-dot {
      background: #00d4ff;
      box-shadow: 0 0 8px #00d4ff;
    }
  }

  &:focus {
    outline: none;
    background: rgba(0, 212, 255, 0.1);
  }

  .note-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.2);
    transition: all 0.2s;
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
  padding: 20px;
  text-align: center;
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
}

.new-note-btn {
  margin: 16px;
  margin-top: auto;
  padding: 14px;
  background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.3s;
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    transition: left 0.5s;
  }

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 212, 255, 0.4);

    &::before {
      left: 100%;
    }
  }

  .btn-icon {
    font-size: 18px;
    font-weight: 400;
  }
}

.context-menu {
  position: fixed;
  background: rgba(18, 18, 31, 0.98);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 10px;
  padding: 6px 0;
  min-width: 160px;
  z-index: 1000;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  transition: all 0.2s;

  &:hover {
    background: rgba(0, 212, 255, 0.1);
    color: #fff;
  }

  &.danger {
    color: #ef4444;

    &:hover {
      background: rgba(239, 68, 68, 0.1);
    }
  }

  .menu-icon {
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;

    svg {
      width: 100%;
      height: 100%;
    }
  }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal-content {
  background: linear-gradient(135deg, rgba(18, 18, 31, 0.98) 0%, rgba(26, 26, 46, 0.98) 100%);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 16px;
  padding: 24px;
  min-width: 320px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
  color: #fff;
}

.modal-input {
  width: 100%;
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 10px;
  color: #fff;
  font-size: 14px;
  margin-bottom: 16px;

  &:focus {
    outline: none;
    border-color: #00d4ff;
    box-shadow: 0 0 15px rgba(0, 212, 255, 0.2);
  }

  &::placeholder {
    color: rgba(255, 255, 255, 0.3);
  }
}

.color-picker {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.color-option {
  display: inline-block;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;

  &:hover {
    transform: scale(1.1);
  }

  &.active {
    border-color: #fff;
    box-shadow: 0 0 10px currentColor;
  }
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-cancel, .btn-confirm {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.7);

  &:hover {
    border-color: rgba(255, 255, 255, 0.4);
    color: #fff;
  }
}

.btn-confirm {
  background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
  border: none;
  color: white;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
  }
}
</style>
