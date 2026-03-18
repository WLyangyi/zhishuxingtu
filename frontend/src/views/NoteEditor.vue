<template>
  <div class="note-editor-page">
    <div class="editor-main">
      <div class="editor-header">
        <div class="header-left">
          <button @click="goHome" class="back-btn" title="返回主页">
            <ArrowLeft :size="16" />
            <span class="back-text">主页</span>
          </button>
          <input 
            v-model="title"
            type="text"
            placeholder="输入笔记标题..."
            class="title-input"
          />
          <div class="save-status" v-if="saving">
            <span class="status-dot"></span>
            保存中...
          </div>
          <div class="word-stats" v-if="content">
            <span class="stat-item">
              <FileText :size="14" />
              <span class="stat-value">{{ wordCount }}</span>
              <span class="stat-label">字</span>
            </span>
            <span class="stat-divider"></span>
            <span class="stat-item">
              <Clock :size="14" />
              <span class="stat-value">{{ readTime }}</span>
              <span class="stat-label">分钟</span>
            </span>
          </div>
        </div>
        <div class="editor-actions">
          <div class="view-toggle">
            <button 
              class="toggle-btn-item" 
              :class="{ active: viewMode === 'edit' }"
              @click="viewMode = 'edit'"
              title="编辑模式"
            >
              <Edit3 :size="16" />
            </button>
            <button 
              class="toggle-btn-item" 
              :class="{ active: viewMode === 'preview' }"
              @click="viewMode = 'preview'"
              title="预览模式"
            >
              <Eye :size="16" />
            </button>
            <div class="link-hint" :class="{ show: showLinkHint }">
              <div class="hint-header">双向链接语法</div>
              <div class="hint-content">
                <code>[[笔记标题]]</code> → 链接到其他笔记<br/>
                <span class="hint-example">示例：[[Vue3学习笔记]]</span>
              </div>
            </div>
            <button 
              class="help-btn"
              @mouseenter="showLinkHint = true"
              @mouseleave="showLinkHint = false"
              title="查看语法帮助"
            >
              <HelpCircle :size="14" />
            </button>
          </div>
          <button @click="saveNote" class="btn-save" :disabled="saving">
            <Save :size="16" />
            {{ saving ? '保存中' : '保存' }}
          </button>
          <button @click="deleteNote" class="btn-delete" v-if="noteId">
            <Trash2 :size="16" />
            删除
          </button>
        </div>
      </div>
      
      <div class="editor-container">
        <div class="editor-pane" v-show="viewMode === 'edit'">
          <textarea 
            v-model="content"
            placeholder="开始编写你的笔记...&#10;&#10;💡 使用 [[笔记标题]] 创建双向链接"
            class="editor-textarea"
          />
        </div>
        <div class="preview-pane" v-show="viewMode === 'preview'">
          <div class="preview-content" v-html="renderedContent" />
        </div>
      </div>
    </div>
    
    <div class="editor-sidebar" :class="{ collapsed: !showSidebar }">
      <button @click="showSidebar = !showSidebar" class="toggle-btn">
        <ChevronLeft v-if="showSidebar" :size="16" />
        <ChevronRight v-else :size="16" />
      </button>
      
      <div v-if="showSidebar" class="sidebar-content">
        <div class="sidebar-section">
          <h4 class="section-title">
            <Folder :size="14" class="section-icon" />
            文件夹
          </h4>
          <select v-model="folderId" class="folder-select">
            <option :value="null">根目录</option>
            <template v-for="folder in flatFolders" :key="folder.id">
              <option :value="folder.id">
                {{ folder.level > 0 ? '　└ ' : '' }}{{ folder.name }}
              </option>
            </template>
          </select>
        </div>
        
        <div class="sidebar-section">
          <h4 class="section-title">
            <Tag :size="14" class="section-icon" />
            标签
            <button class="add-tag-btn" @click="showNewTagInput = true" title="新建标签">
              <Plus :size="12" />
            </button>
          </h4>
          <div class="tag-selector">
            <label 
              v-for="tag in tagsStore.tags" 
              :key="tag.id" 
              class="tag-checkbox"
              :class="{ checked: selectedTagIds.includes(tag.id) }"
            >
              <input type="checkbox" :value="tag.id" v-model="selectedTagIds" />
              <span 
                class="tag-label"
                :style="{ 
                  backgroundColor: selectedTagIds.includes(tag.id) ? tag.color + '20' : 'transparent',
                  borderColor: tag.color,
                  color: tag.color
                }"
              >
                {{ tag.name }}
              </span>
            </label>
            <div v-if="showNewTagInput" class="new-tag-input">
              <input
                ref="newTagInputRef"
                v-model="newTagName"
                type="text"
                placeholder="输入标签名称"
                @keyup.enter="createNewTag"
                @keyup.escape="cancelNewTag"
                @blur="cancelNewTag"
              />
              <div class="color-options">
                <span 
                  v-for="color in tagColors" 
                  :key="color"
                  class="color-dot"
                  :class="{ active: newTagColor === color }"
                  :style="{ backgroundColor: color }"
                  @click="newTagColor = color"
                />
              </div>
            </div>
            <div v-if="tagsStore.tags.length === 0 && !showNewTagInput" class="empty-tags" @click="showNewTagInput = true">
              <Plus :size="14" />
              点击创建标签
            </div>
          </div>
        </div>
        
        <div class="sidebar-section">
          <h4 class="section-title">
            <Link :size="14" class="section-icon" />
            反向链接
            <span class="help-icon" title="反向链接是指向当前笔记的其他笔记。点击链接即可跳转到对应笔记。">
              <HelpCircle :size="12" />
            </span>
            <span class="count-badge" v-if="backlinks.length > 0">{{ backlinks.length }}</span>
          </h4>
          <div class="backlinks-list" v-if="backlinks.length > 0">
            <div 
              v-for="link in backlinks" 
              :key="link.id"
              class="backlink-item"
              @click="openNote(link.id)"
            >
              <ArrowRight :size="14" class="link-icon" />
              {{ link.title }}
            </div>
          </div>
          <div class="empty-tip" v-else>
            <p>暂无反向链接</p>
            <p class="tip-text">在其他笔记中使用 [[笔记标题]] 链接到当前笔记</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import { useNotesStore } from '@/stores/notes'
import { useFoldersStore } from '@/stores/folders'
import { useTagsStore } from '@/stores/tags'
import { useNotificationStore } from '@/stores/notification'
import type { Backlink } from '@/types'
import { 
  ArrowLeft, Edit3, Eye, HelpCircle, Save, Trash2,
  Folder, Tag, Plus, Link, ArrowRight, FileText, Clock,
  ChevronLeft, ChevronRight
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const notesStore = useNotesStore()
const foldersStore = useFoldersStore()
const tagsStore = useTagsStore()
const notification = useNotificationStore()

const noteId = computed(() => route.params.id as string)
const isNewNote = computed(() => route.name === 'NewNote' || noteId.value === 'new')

const wordCount = computed(() => {
  if (!content.value) return 0
  const text = content.value.replace(/[#*`\[\]]/g, '').trim()
  return text.length
})

const readTime = computed(() => {
  const words = wordCount.value
  const minutes = Math.ceil(words / 250)
  return minutes
})

const title = ref('')
const content = ref('')
const folderId = ref<string | null>(null)
const selectedTagIds = ref<string[]>([])
const saving = ref(false)
const showSidebar = ref(true)
const backlinks = ref<Backlink[]>([])
const showNewTagInput = ref(false)
const newTagName = ref('')
const newTagColor = ref('#f59e0b')
const newTagInputRef = ref<HTMLInputElement | null>(null)
const viewMode = ref<'edit' | 'preview'>('edit')
const showLinkHint = ref(false)

const tagColors = [
  '#f59e0b', '#3b82f6', '#10b981', '#ef4444',
  '#8b5cf6', '#ec4899', '#06b6d4', '#6366f1'
]

interface FlatFolder {
  id: string
  name: string
  level: number
}

const flatFolders = computed(() => {
  const result: FlatFolder[] = []
  
  function flatten(folders: any[], level: number = 0) {
    for (const folder of folders) {
      result.push({ id: folder.id, name: folder.name, level })
      if (folder.children && folder.children.length > 0) {
        flatten(folder.children, level + 1)
      }
    }
  }
  
  flatten(foldersStore.folders)
  return result
})

const md = new MarkdownIt({
  html: true,
  linkify: true,
  typographer: true
})

const renderedContent = computed(() => {
  let html = md.render(content.value || '*开始编写笔记内容...*')
  html = html.replace(/\[\[([^\]]+)\]\]/g, (_match: string, titleText: string) => {
    const note = notesStore.notes.find(n => n.title === titleText)
    if (note) {
      return `<a href="/notes/${note.id}" class="internal-link">${titleText}</a>`
    }
    return `<span class="broken-link">${titleText}</span>`
  })
  return html
})

onMounted(async () => {
  await foldersStore.fetchFolders()
  await tagsStore.fetchTags()
  await loadNote()
})

async function loadNote() {
  if (isNewNote.value) {
    title.value = ''
    content.value = ''
    folderId.value = null
    selectedTagIds.value = []
    backlinks.value = []
    return
  }
  
  const note = await notesStore.getNote(noteId.value)
  if (note) {
    title.value = note.title
    content.value = note.content || ''
    folderId.value = note.folder_id
    selectedTagIds.value = note.tags.map(t => t.id)
    await notesStore.fetchBacklinks(noteId.value)
    backlinks.value = [...notesStore.backlinks]
  } else {
    router.push('/')
  }
}

watch(
  () => route.params.id,
  async (newId, oldId) => {
    const newIsNew = route.name === 'NewNote' || newId === 'new'
    const oldIsNew = oldId === undefined || oldId === 'new'
    
    if (newId !== oldId || newIsNew !== oldIsNew) {
      await loadNote()
    }
  }
)

watch(
  () => route.name,
  async (newName, oldName) => {
    if (newName === 'NewNote' && oldName !== 'NewNote') {
      await loadNote()
    }
  }
)

async function saveNote() {
  if (!title.value.trim()) {
    notification.warning('请输入笔记标题', '标题不能为空')
    return
  }
  
  saving.value = true
  try {
    const data = {
      title: title.value,
      content: content.value,
      folder_id: folderId.value,
      tag_ids: selectedTagIds.value
    }
    
    if (isNewNote.value) {
      const note = await notesStore.createNote(data)
      router.replace(`/notes/${note.id}`)
    } else {
      await notesStore.updateNote(noteId.value, data)
    }
  } catch (error) {
  } finally {
    saving.value = false
  }
}

async function deleteNote() {
  if (!confirm('确定要删除这篇笔记吗？此操作无法撤销。')) return
  
  try {
    await notesStore.deleteNote(noteId.value)
    router.push('/')
  } catch (error) {
  }
}

function openNote(id: string) {
  router.push(`/notes/${id}`)
}

function goHome() {
  router.push('/')
}

async function createNewTag() {
  const name = newTagName.value.trim()
  if (!name) {
    notification.warning('请输入标签名称')
    return
  }

  try {
    const tag = await tagsStore.createTag({ name, color: newTagColor.value })
    selectedTagIds.value.push(tag.id)
    notification.success('标签创建成功', `「${name}」已添加`)
    cancelNewTag()
  } catch (error: any) {
    notification.error('创建失败', error.response?.data?.detail || '操作失败')
  }
}

function cancelNewTag() {
  showNewTagInput.value = false
  newTagName.value = ''
  newTagColor.value = '#f59e0b'
}

watch(showNewTagInput, (val) => {
  if (val) {
    nextTick(() => {
      newTagInputRef.value?.focus()
    })
  }
})
</script>

<style scoped lang="scss">
.note-editor-page {
  display: flex;
  height: calc(100vh - 0px);
  background: var(--bg-primary);
}

.editor-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--bg-hover);
    border-color: var(--border-strong);
    color: var(--text-primary);
    transform: translateX(-2px);
  }
  
  &:active {
    transform: translateX(0);
  }
  
  .back-text {
    font-weight: 500;
  }
}

.title-input {
  flex: 1;
  font-size: 18px;
  font-weight: 600;
  border: none;
  background: transparent;
  color: var(--text-primary);
  padding: 8px 0;
  
  &:focus {
    outline: none;
  }
  
  &::placeholder {
    color: var(--text-muted);
  }
}

.save-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
  
  .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--primary-color);
    animation: pulse 1s infinite;
  }
}

.word-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  font-size: 12px;
  color: var(--text-tertiary);
  
  .stat-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  
  .stat-value {
    font-weight: 600;
    color: var(--text-primary);
  }
  
  .stat-label {
    color: var(--text-muted);
  }
  
  .stat-divider {
    width: 1px;
    height: 12px;
    background: var(--border-default);
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.editor-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.view-toggle {
  display: flex;
  align-items: center;
  gap: 2px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 4px;
  position: relative;
}

.toggle-btn-item {
  width: 32px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-muted);
  transition: all var(--transition-fast);
  
  &:hover {
    color: var(--text-primary);
    background: var(--bg-hover);
  }
  
  &.active {
    background: var(--bg-active);
    color: var(--primary-color);
  }
}

.help-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--text-muted);
  margin-left: 4px;
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.link-hint {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 260px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  padding: 14px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-4px);
  transition: all var(--transition-base);
  z-index: 100;
  
  &.show {
    opacity: 1;
    visibility: visible;
    transform: translateY(0);
  }
  
  .hint-header {
    font-size: 12px;
    font-weight: 600;
    color: var(--primary-color);
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-subtle);
  }
  
  .hint-content {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.7;
    
    code {
      background: var(--primary-muted);
      padding: 2px 6px;
      border-radius: var(--radius-sm);
      color: var(--primary-color);
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
    }
  }
  
  .hint-example {
    display: block;
    margin-top: 8px;
    color: var(--text-muted);
    font-size: 12px;
  }
}

.btn-save, .btn-delete {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-save {
  background: var(--primary-color);
  border: none;
  color: #000;
  
  &:hover:not(:disabled) {
    background: var(--primary-hover);
    transform: translateY(-1px);
  }
  
  &:active:not(:disabled) {
    transform: translateY(0);
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.btn-delete {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-tertiary);
  
  &:hover {
    background: rgba(239, 68, 68, 0.1);
    border-color: var(--accent-red);
    color: var(--accent-red);
  }
}

.editor-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-pane, .preview-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.editor-textarea {
  flex: 1;
  padding: 24px 32px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 14px;
  line-height: 1.8;
  resize: none;
  
  &:focus {
    outline: none;
  }
  
  &::placeholder {
    color: var(--text-muted);
    line-height: 1.6;
  }
}

.preview-pane {
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-subtle);
}

.preview-content {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  color: var(--text-primary);
  line-height: 1.8;
  
  :deep(h1), :deep(h2), :deep(h3) {
    color: var(--text-primary);
    margin-bottom: 12px;
    margin-top: 24px;
    font-weight: 600;
    
    &:first-child {
      margin-top: 0;
    }
  }
  
  :deep(h1) { font-size: 26px; }
  :deep(h2) { font-size: 22px; }
  :deep(h3) { font-size: 18px; }
  
  :deep(p) {
    margin-bottom: 14px;
  }
  
  :deep(code) {
    background: var(--primary-muted);
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: var(--primary-color);
  }
  
  :deep(pre) {
    background: var(--bg-tertiary);
    padding: 16px;
    border-radius: var(--radius-md);
    overflow-x: auto;
    margin-bottom: 14px;
    border: 1px solid var(--border-subtle);
    
    code {
      background: transparent;
      padding: 0;
      color: var(--text-primary);
    }
  }
  
  :deep(ul), :deep(ol) {
    margin-bottom: 14px;
    padding-left: 24px;
  }
  
  :deep(li) {
    margin-bottom: 6px;
  }
  
  :deep(blockquote) {
    border-left: 3px solid var(--primary-color);
    padding-left: 16px;
    margin: 16px 0;
    color: var(--text-tertiary);
  }
  
  :deep(.internal-link) {
    color: var(--primary-color);
    cursor: pointer;
    border-bottom: 1px dashed transparent;
    transition: all var(--transition-fast);
    
    &:hover {
      border-bottom-color: var(--primary-color);
    }
  }
  
  :deep(.broken-link) {
    color: var(--accent-red);
    text-decoration: line-through;
    opacity: 0.7;
  }
}

.editor-sidebar {
  width: 280px;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-subtle);
  position: relative;
  transition: width var(--transition-base);
  
  &.collapsed {
    width: 36px;
  }
}

.toggle-btn {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 48px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-left: none;
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  cursor: pointer;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.sidebar-content {
  padding: 20px;
  margin-left: 24px;
}

.sidebar-section {
  margin-bottom: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.section-icon {
  color: var(--text-tertiary);
}

.add-tag-btn {
  margin-left: auto;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--bg-hover);
    border-color: var(--primary-color);
    color: var(--primary-color);
  }
}

.count-badge {
  margin-left: auto;
  background: var(--primary-muted);
  color: var(--primary-color);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.folder-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
  
  &:hover, &:focus {
    border-color: var(--border-default);
    outline: none;
  }
  
  option {
    background: var(--bg-elevated);
    color: var(--text-primary);
  }
}

.tag-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-checkbox {
  cursor: pointer;
  
  input {
    display: none;
  }
  
  .tag-label {
    display: block;
    padding: 5px 10px;
    border-radius: var(--radius-lg);
    font-size: 12px;
    font-weight: 500;
    border: 1px solid;
    transition: all var(--transition-fast);
  }
  
  &.checked .tag-label {
    box-shadow: 0 0 0 1px currentColor;
  }
  
  &:hover .tag-label {
    transform: translateY(-1px);
  }
}

.empty-tags {
  color: var(--text-muted);
  font-size: 12px;
  padding: 12px 14px;
  text-align: center;
  border: 1px dashed var(--border-default);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  
  &:hover {
    border-color: var(--primary-color);
    color: var(--primary-color);
    background: var(--primary-muted);
  }
}

.new-tag-input {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: 6px;
  
  input {
    width: 100%;
    padding: 8px 10px;
    background: var(--bg-secondary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-sm);
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
  
  .color-options {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  
  .color-dot {
    display: inline-block;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    cursor: pointer;
    transition: all var(--transition-fast);
    border: 2px solid transparent;
    
    &:hover {
      transform: scale(1.15);
    }
    
    &.active {
      border-color: var(--text-primary);
    }
  }
}

.backlinks-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.help-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-left: 4px;
  color: var(--text-muted);
  cursor: help;
  
  &:hover {
    color: var(--text-primary);
  }
}

.empty-tip {
  padding: 12px;
  text-align: center;
  
  p {
    color: var(--text-tertiary);
    font-size: 12px;
    margin: 0;
  }
  
  .tip-text {
    color: var(--text-muted);
    margin-top: 4px;
  }
}

.backlink-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
  
  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
    
    .link-icon {
      color: var(--primary-color);
    }
  }
  
  .link-icon {
    color: var(--text-muted);
    transition: color var(--transition-fast);
  }
}

@media (max-width: 900px) {
  .editor-sidebar {
    display: none;
  }
  
  .word-stats {
    display: none;
  }
}

@media (max-width: 600px) {
  .editor-header {
    padding: 10px 16px;
    flex-wrap: wrap;
    gap: 12px;
  }
  
  .header-left {
    width: 100%;
  }
  
  .editor-actions {
    width: 100%;
    justify-content: flex-end;
  }
  
  .editor-textarea {
    padding: 16px;
  }
  
  .preview-content {
    padding: 16px;
  }
}
</style>
