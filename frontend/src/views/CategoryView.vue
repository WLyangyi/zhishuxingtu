<template>
  <div class="category-view">
    <div class="sidebar-overlay" v-if="sidebarOpen" @click="sidebarOpen = false"></div>
    
    <div class="category-sidebar" :class="{ open: sidebarOpen }">
      <div class="sidebar-header">
        <div class="header-top">
          <button @click="goHome" class="back-btn" title="返回主页">
            <Home :size="18" />
          </button>
          <h2 class="sidebar-title">
            <Library :size="20" class="title-icon" />
            内容分类
          </h2>
        </div>
        <button @click="showCreateCategoryModal = true" class="add-btn" title="新建分类">
          <Plus :size="18" />
        </button>
      </div>
      
      <div class="category-list">
        <div 
          v-for="category in categoryStore.categories" 
          :key="category.id"
          class="category-item"
          :class="{ active: selectedCategoryId === category.id }"
          @click="selectCategory(category)"
        >
          <div class="category-icon" :style="{ color: category.color }">
            <FolderOpen :size="22" />
          </div>
          <div class="category-info">
            <span class="category-name">{{ category.name }}</span>
            <span class="category-count">{{ getCategoryNoteCount(category.id) }} 项</span>
          </div>
        </div>
      </div>
    </div>

    <div class="category-main">
      <div v-if="selectedCategory" class="main-content">
        <div class="main-header">
          <div class="header-left">
            <div class="breadcrumb-nav">
              <button @click="sidebarOpen = !sidebarOpen" class="menu-toggle" title="切换分类">
                <Menu :size="20" />
              </button>
              
              <button v-if="navigationPath.length > 0" @click="goBack" class="back-nav-btn" title="返回上一层">
                <ChevronLeft :size="20" />
              </button>
              
              <div class="breadcrumb-items">
                <span 
                  class="breadcrumb-item"
                  @click="navigateToRoot"
                >
                  <span class="title-icon" :style="{ color: selectedCategory.color }">
                    <FolderOpen :size="18" />
                  </span>
                  {{ selectedCategory.name }}
                </span>
                <template v-for="(folder, index) in navigationPath" :key="folder.id">
                  <ChevronRight :size="16" class="breadcrumb-separator" />
                  <span 
                    class="breadcrumb-item"
                    :class="{ active: index === navigationPath.length - 1 }"
                    @click="navigateToFolder(index)"
                  >
                    {{ folder.name }}
                  </span>
                </template>
              </div>
            </div>
          </div>
          <div class="header-actions">
            <div class="search-box">
              <Search :size="16" class="search-icon" />
              <input 
                v-model="searchKeyword"
                type="text"
                placeholder="搜索内容..."
                @keyup.enter="searchNotes"
              />
            </div>
            <div class="create-btn-wrapper">
              <button @click.stop="toggleCreateDropdown" class="create-btn">
                <Edit3 :size="16" />
                新建
              </button>
              <div v-if="showCreateDropdown" class="create-dropdown" @click.stop>
                <div class="dropdown-item" @click="createNewNote">
                  <FileText :size="16" />
                  新建笔记
                </div>
                <div class="dropdown-item" @click="openNewFolderModal">
                  <FolderPlus :size="16" />
                  新建文件夹
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="content-area">
          <div class="folders-section" v-if="currentLevelFolders.length > 0">
            <h3 class="section-title">文件夹</h3>
            <div class="card-grid">
              <div 
                v-for="folder in currentLevelFolders" 
                :key="folder.id"
                class="content-card folder-card"
                @click="enterFolder(folder)"
                @contextmenu.prevent="showFolderContextMenu($event, folder)"
              >
                <div class="card-content">
                  <Folder :size="32" class="card-icon" />
                  <span class="card-title">{{ folder.name }}</span>
                  <span class="card-count">{{ getFolderNoteCount(folder.id) }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="notes-section" v-if="currentLevelNotes.length > 0">
            <h3 class="section-title">笔记</h3>
            <div class="card-grid">
              <div 
                v-for="note in currentLevelNotes" 
                :key="note.id"
                class="content-card note-card"
                @click="openNote(note.id)"
              >
                <div class="card-content">
                  <FileText :size="32" class="card-icon" />
                  <span class="card-title">{{ note.title }}</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentLevelFolders.length === 0 && currentLevelNotes.length === 0" class="empty-state">
            <FileText :size="48" class="empty-icon" />
            <h3>暂无内容</h3>
            <p>点击「新建」开始记录</p>
          </div>
        </div>
      </div>

      <div v-else class="empty-selection">
        <MousePointerClick :size="48" class="empty-icon" />
        <h2>选择一个分类</h2>
        <p>从左侧选择分类查看内容</p>
      </div>
    </div>

    <div v-if="showCreateCategoryModal" class="modal-overlay" @click.self="showCreateCategoryModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新建分类</h3>
          <button @click="showCreateCategoryModal = false" class="close-btn">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>分类名称</label>
            <input v-model="newCategory.name" type="text" placeholder="输入分类名称" />
          </div>
          <div class="form-group">
            <label>图标</label>
            <input v-model="newCategory.icon" type="text" placeholder="如：📁" />
          </div>
          <div class="form-group">
            <label>颜色</label>
            <div class="color-picker">
              <span 
                v-for="color in colorOptions" 
                :key="color"
                class="color-dot"
                :class="{ active: newCategory.color === color }"
                :style="{ backgroundColor: color }"
                @click="newCategory.color = color"
              />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showCreateCategoryModal = false" class="btn-cancel">取消</button>
          <button @click="handleCreateCategory" class="btn-confirm">创建</button>
        </div>
      </div>
    </div>

    <div v-if="showNewFolderModal" class="modal-overlay" @click.self="showNewFolderModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ parentFolderForCreate ? '新建子文件夹' : '新建文件夹' }}</h3>
          <button @click="closeFolderModal" class="close-btn">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body">
          <div v-if="parentFolderForCreate" class="parent-folder-info">
            <span class="parent-label">父文件夹：</span>
            <span class="parent-name">
              <Folder :size="14" />
              {{ parentFolderForCreate.name }}
            </span>
          </div>
          <div class="form-group">
            <label>文件夹名称</label>
            <input 
              v-model="newFolderName" 
              type="text" 
              placeholder="输入文件夹名称"
              @keyup.enter="handleCreateFolder"
            />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeFolderModal" class="btn-cancel">取消</button>
          <button @click="handleCreateFolder" class="btn-confirm">创建</button>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="folderContextMenu.visible"
        class="context-menu"
        :style="{ left: folderContextMenu.x + 'px', top: folderContextMenu.y + 'px' }"
        @click.stop
      >
        <div class="menu-item" @click="openSubfolderModal" v-if="folderContextMenu.folder && getFolderLevel(folderContextMenu.folder.id) < 3">
          <FolderPlus :size="14" />
          新建子文件夹
        </div>
        <div class="menu-item danger" @click="deleteFolderFromContext">
          <Trash2 :size="14" />
          删除文件夹
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useCategoryStore } from '@/stores/category'
import { useFoldersStore } from '@/stores/folders'
import { useNotesStore } from '@/stores/notes'
import { useNotificationStore } from '@/stores/notification'
import type { Category } from '@/types/category'
import type { FolderTree } from '@/types/folder'
import { 
  Home, Library, Plus, FolderOpen, Folder, FolderPlus, FileText, 
  Menu, ChevronLeft, ChevronRight, Search, Edit3, X, Trash2,
  MousePointerClick
} from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const categoryStore = useCategoryStore()
const foldersStore = useFoldersStore()
const notesStore = useNotesStore()
const notification = useNotificationStore()

const selectedCategoryId = ref<string | null>(null)
const currentFolderId = ref<string | null>(null)
const navigationPath = ref<FolderTree[]>([])
const searchKeyword = ref('')
const showCreateCategoryModal = ref(false)
const showCreateDropdown = ref(false)
const showNewFolderModal = ref(false)
const newFolderName = ref('')
const sidebarOpen = ref(false)
const parentFolderForCreate = ref<FolderTree | null>(null)

const folderContextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
  folder: null as FolderTree | null
})

const newCategory = ref({
  name: '',
  icon: '📁',
  color: '#0066FF'
})

const colorOptions = [
  '#0066FF', '#f59e0b', '#10b981', '#ef4444',
  '#ec4899', '#8b5cf6', '#06b6d4', '#3b82f6'
]

const selectedCategory = computed(() => 
  categoryStore.categories.find(c => c.id === selectedCategoryId.value)
)

const allFoldersFlat = computed(() => {
  const result: FolderTree[] = []
  
  function flatten(folders: FolderTree[]) {
    for (const folder of folders) {
      result.push(folder)
      if (folder.children && folder.children.length > 0) {
        flatten(folder.children)
      }
    }
  }
  
  flatten(foldersStore.folders)
  return result
})

const currentLevelFolders = computed(() => {
  if (!selectedCategoryId.value) return []
  
  const parentId = currentFolderId.value
  
  return allFoldersFlat.value.filter(f => {
    if (f.category_id !== selectedCategoryId.value) return false
    return f.parent_id === parentId
  })
})

const currentLevelNotes = computed(() => {
  if (!selectedCategoryId.value) return []

  if (!currentFolderId.value) {
    return []
  }

  let notes = notesStore.notes.filter(n => n.folder_id === currentFolderId.value)

  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    notes = notes.filter(n =>
      n.title.toLowerCase().includes(keyword) ||
      (n.content && n.content.toLowerCase().includes(keyword))
    )
  }

  return notes
})

onMounted(async () => {
  document.addEventListener('click', hideCreateDropdown)
  document.addEventListener('click', hideFolderContextMenu)
  await categoryStore.fetchCategories()
  await foldersStore.fetchFolders()
  
  const categoryId = route.params.categoryId as string
  if (categoryId) {
    const category = categoryStore.categories.find(c => c.id === categoryId)
    if (category) {
      selectCategory(category)
      await notesStore.fetchNotes({ category_id: categoryId })
    }
  } else if (categoryStore.categories.length > 0) {
    const firstCategory = categoryStore.categories[0]
    selectCategory(firstCategory)
    await notesStore.fetchNotes({ category_id: firstCategory.id })
  }
})

onUnmounted(() => {
  document.removeEventListener('click', hideCreateDropdown)
  document.removeEventListener('click', hideFolderContextMenu)
})

function hideCreateDropdown() {
  showCreateDropdown.value = false
}

function toggleCreateDropdown() {
  showCreateDropdown.value = !showCreateDropdown.value
}

async function selectCategory(category: Category) {
  selectedCategoryId.value = category.id
  currentFolderId.value = null
  navigationPath.value = []
  searchKeyword.value = ''
  categoryStore.currentCategory = category
  sidebarOpen.value = false
  await notesStore.fetchNotes({ category_id: category.id })
}

function enterFolder(folder: FolderTree) {
  currentFolderId.value = folder.id
  navigationPath.value.push(folder)
}

function navigateToRoot() {
  currentFolderId.value = null
  navigationPath.value = []
}

function navigateToFolder(index: number) {
  navigationPath.value = navigationPath.value.slice(0, index + 1)
  currentFolderId.value = navigationPath.value[index].id
}

function goBack() {
  if (navigationPath.value.length > 0) {
    navigationPath.value.pop()
    currentFolderId.value = navigationPath.value.length > 0 
      ? navigationPath.value[navigationPath.value.length - 1].id 
      : null
  }
}

function searchNotes() {
}

function getCategoryNoteCount(categoryId: string): number {
  const categoryFolders = allFoldersFlat.value.filter(f => f.category_id === categoryId)
  const folderIds = categoryFolders.map(f => f.id)
  
  return notesStore.notes.filter(n => 
    folderIds.includes(n.folder_id || '')
  ).length
}

function getFolderNoteCount(folderId: string): number {
  const folder = allFoldersFlat.value.find(f => f.id === folderId)
  if (!folder) return 0
  return folder.note_count || 0
}

function getFolderLevel(folderId: string): number {
  const folder = allFoldersFlat.value.find(f => f.id === folderId)
  return folder?.level || 0
}

function createNewNote() {
  showCreateDropdown.value = false
  router.push({ 
    name: 'NewNote', 
    query: { 
      category_id: selectedCategoryId.value,
      folder_id: currentFolderId.value
    }
  })
}

function openNewFolderModal() {
  showCreateDropdown.value = false
  if (currentFolderId.value) {
    const currentFolder = allFoldersFlat.value.find(f => f.id === currentFolderId.value)
    if (currentFolder) {
      parentFolderForCreate.value = currentFolder
    }
  } else {
    parentFolderForCreate.value = null
  }
  newFolderName.value = ''
  showNewFolderModal.value = true
}

function showFolderContextMenu(event: MouseEvent, folder: FolderTree) {
  folderContextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    folder
  }
}

function hideFolderContextMenu() {
  folderContextMenu.value.visible = false
}

function openSubfolderModal() {
  if (!folderContextMenu.value.folder) return
  parentFolderForCreate.value = folderContextMenu.value.folder
  hideFolderContextMenu()
  newFolderName.value = ''
  showNewFolderModal.value = true
}

async function deleteFolderFromContext() {
  if (!folderContextMenu.value.folder) return
  const folder = folderContextMenu.value.folder
  hideFolderContextMenu()
  
  if (!confirm(`确定要删除文件夹「${folder.name}」吗？\n文件夹必须为空才能删除。`)) {
    return
  }
  
  try {
    await foldersStore.deleteFolder(folder.id)
    notification.success('删除成功', `文件夹「${folder.name}」已删除`)
    if (currentFolderId.value === folder.id) {
      goBack()
    }
  } catch (error: any) {
    notification.error('删除失败', error.response?.data?.detail || '操作失败')
  }
}

function closeFolderModal() {
  showNewFolderModal.value = false
  newFolderName.value = ''
  parentFolderForCreate.value = null
}

async function handleCreateFolder() {
  if (!newFolderName.value.trim()) {
    notification.warning('请输入文件夹名称')
    return
  }
  try {
    const folderData: any = {
      name: newFolderName.value.trim(),
      category_id: selectedCategoryId.value!
    }
    if (parentFolderForCreate.value) {
      folderData.parent_id = parentFolderForCreate.value.id
    } else if (currentFolderId.value) {
      folderData.parent_id = currentFolderId.value
    }
    await foldersStore.createFolder(folderData)
    notification.success('创建成功', `文件夹「${newFolderName.value}」已创建`)
    closeFolderModal()
  } catch (error: any) {
    notification.error('创建失败', error.response?.data?.detail || '操作失败')
  }
}

function openNote(noteId: string) {
  router.push(`/notes/${noteId}`)
}

function goHome() {
  router.push('/')
}

async function handleCreateCategory() {
  if (!newCategory.value.name.trim()) return
  
  try {
    await categoryStore.createCategory(newCategory.value)
    showCreateCategoryModal.value = false
    newCategory.value = { name: '', icon: '📁', color: '#0066FF' }
  } catch (e) {
    console.error(e)
  }
}
</script>

<style scoped lang="scss">
.category-view {
  display: flex;
  height: calc(100vh - 0px);
  background: var(--bg-primary);
  position: relative;
}

.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 99;
}

.category-sidebar {
  position: fixed;
  left: 0;
  top: 0;
  height: 100%;
  width: 280px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  z-index: 100;
  transform: translateX(-100%);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  
  &.open {
    transform: translateX(0);
  }
}

.sidebar-header {
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-subtle);
}

.header-top {
  display: flex;
  align-items: center;
  gap: 10px;
}

.back-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;

  &:hover {
    background: var(--bg-active);
    color: var(--text-primary);
  }
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-primary);
  
  .title-icon {
    color: var(--tech-blue);
  }
}

.add-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  color: var(--tech-blue);
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: var(--tech-blue-muted);
    border-color: var(--tech-blue);
  }
}

.category-list {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
  
  &:hover {
    background: var(--bg-hover);
  }
  
  &.active {
    background: var(--bg-active);
    border: 1px solid var(--border-default);
  }
}

.category-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.category-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.category-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.category-count {
  font-size: 11px;
  color: var(--text-muted);
}

.category-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-header {
  padding: 20px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.breadcrumb-nav {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-toggle {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
  
  &:hover {
    background: var(--bg-active);
    color: var(--text-primary);
  }
}

.back-nav-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
  
  &:hover {
    background: var(--bg-active);
    color: var(--text-primary);
  }
}

.breadcrumb-items {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.breadcrumb-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 600;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color 0.2s;
  
  &:hover {
    color: var(--tech-blue);
  }
  
  &.active {
    color: var(--text-primary);
  }
  
  .title-icon {
    display: flex;
  }
}

.breadcrumb-separator {
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  width: 300px;
  
  .search-icon {
    color: var(--text-muted);
  }
  
  input {
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text-primary);
    font-size: 14px;
    
    &:focus {
      outline: none;
    }
    
    &::placeholder {
      color: var(--text-muted);
    }
  }
}

.create-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--primary-color);
  border: none;
  border-radius: var(--radius-md);
  color: #000;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: var(--primary-hover);
    transform: translateY(-1px);
  }
}

.create-btn-wrapper {
  position: relative;
}

.create-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 8px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 6px 0;
  min-width: 150px;
  z-index: 100;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);

  .dropdown-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    font-size: 13px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: var(--bg-hover);
      color: var(--text-primary);
    }
  }
}

.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.folders-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

.content-card {
  position: relative;
  aspect-ratio: 1;
  border-radius: var(--radius-xl);
  cursor: pointer;
  overflow: hidden;
  transition: all 0.2s;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  
  &:hover {
    transform: translateY(-4px);
    border-color: var(--border-default);
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.3);
  }
}

.card-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 16px;
  gap: 8px;
  
  .card-icon {
    color: var(--text-muted);
    opacity: 0.5;
  }
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  text-align: center;
  word-break: break-word;
}

.card-count {
  font-size: 12px;
  color: var(--text-muted);
}

.empty-state, .empty-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  text-align: center;
  
  .empty-icon {
    color: var(--text-muted);
    margin-bottom: 16px;
    opacity: 0.5;
  }
  
  h2, h3 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
    color: var(--text-secondary);
  }
  
  p {
    font-size: 14px;
    color: var(--text-muted);
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
}

.modal {
  width: 400px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-subtle);
  
  h3 {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
  }
  
  .close-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    
    &:hover {
      color: var(--text-primary);
    }
  }
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 16px;
  
  label {
    display: block;
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }
  
  input {
    width: 100%;
    padding: 10px 14px;
    background: var(--bg-hover);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-size: 14px;
    
    &:focus {
      outline: none;
      border-color: var(--tech-blue);
    }
    
    &::placeholder {
      color: var(--text-muted);
    }
  }
}

.color-picker {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.color-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
  
  &:hover {
    transform: scale(1.15);
  }
  
  &.active {
    border-color: var(--text-primary);
  }
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid var(--border-subtle);
}

.btn-cancel, .btn-confirm {
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);
  
  &:hover {
    background: var(--bg-hover);
  }
}

.btn-confirm {
  background: var(--primary-color);
  border: none;
  color: #000;
  font-weight: 500;
  
  &:hover {
    background: var(--primary-hover);
  }
}

.parent-folder-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: 16px;
  
  .parent-label {
    font-size: 12px;
    color: var(--text-muted);
  }
  
  .parent-name {
    font-size: 13px;
    color: var(--tech-blue);
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 6px;
  }
}

.context-menu {
  position: fixed;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  padding: 6px 0;
  min-width: 160px;
  z-index: 1000;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  
  .menu-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    cursor: pointer;
    font-size: 13px;
    color: var(--text-secondary);
    transition: all 0.2s;
    
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
}

@media (max-width: 768px) {
  .search-box {
    width: 200px;
  }
  
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  }
}
</style>
