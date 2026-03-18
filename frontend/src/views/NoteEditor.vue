<template>
  <div class="note-editor-page">
    <div class="editor-main">
      <div class="editor-header">
        <div class="header-left">
          <button @click="goHome" class="back-btn" title="返回主页">
            <span class="back-icon">←</span>
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
              <span class="stat-icon">📝</span>
              <span class="stat-value">{{ wordCount }}</span>
              <span class="stat-label">字</span>
            </span>
            <span class="stat-divider">|</span>
            <span class="stat-item">
              <span class="stat-icon">⏱️</span>
              <span class="stat-value">{{ readTime }}</span>
              <span class="stat-label">分钟阅读</span>
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
              ✏️
            </button>
            <button 
              class="toggle-btn-item" 
              :class="{ active: viewMode === 'preview' }"
              @click="viewMode = 'preview'"
              title="预览模式"
            >
              👁️
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
              ?
            </button>
          </div>
          <button @click="saveNote" class="btn-save" :disabled="saving">
            <span class="btn-icon">💾</span>
            {{ saving ? '保存中' : '保存' }}
          </button>
          <button @click="deleteNote" class="btn-delete" v-if="noteId">
            <span class="btn-icon">🗑️</span>
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
        <span v-if="showSidebar">◀</span>
        <span v-else>▶</span>
      </button>
      
      <div v-if="showSidebar" class="sidebar-content">
        <div class="sidebar-section">
          <h4 class="section-title">
            <span class="section-icon">📁</span>
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
            <span class="section-icon">🏷️</span>
            标签
            <button class="add-tag-btn" @click="showNewTagInput = true" title="新建标签">+</button>
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
                  backgroundColor: selectedTagIds.includes(tag.id) ? tag.color + '30' : 'transparent',
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
              <span class="empty-icon">+</span>
              点击创建标签
            </div>
          </div>
        </div>
        
        <div class="sidebar-section">
          <h4 class="section-title">
            <span class="section-icon">🔗</span>
            反向链接
            <span class="help-icon" title="反向链接是指向当前笔记的其他笔记。点击链接即可跳转到对应笔记。">?</span>
            <span class="count-badge" v-if="backlinks.length > 0">{{ backlinks.length }}</span>
          </h4>
          <div class="backlinks-list" v-if="backlinks.length > 0">
            <div 
              v-for="link in backlinks" 
              :key="link.id"
              class="backlink-item"
              @click="openNote(link.id)"
            >
              <span class="link-icon">→</span>
              {{ link.title }}
            </div>
          </div>
          <div class="empty-tip" v-else>
            <p>暂无反向链接</p>
            <p class="tip-text">反向链接是指向当前笔记的其他笔记</p>
            <p class="tip-text">在其他笔记中使用 [[笔记标题]] 链接到当前笔记即可显示在此处</p>
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
const newTagColor = ref('#00d4ff')
const newTagInputRef = ref<HTMLInputElement | null>(null)
const viewMode = ref<'edit' | 'preview'>('edit')
const showLinkHint = ref(false)

const tagColors = [
  '#00d4ff', '#7b2cbf', '#10b981', '#f59e0b', 
  '#ef4444', '#ec4899', '#8b5cf6', '#06b6d4'
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
    // 错误已在 store 中处理
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
    // 错误已在 store 中处理
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
  newTagColor.value = '#00d4ff'
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
  background: linear-gradient(135deg, #0a0a14 0%, #0d0d1a 100%);
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
  padding: 16px 24px;
  background: rgba(18, 18, 31, 0.8);
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
  backdrop-filter: blur(10px);
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
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 10px;
  color: #00d4ff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    background: rgba(0, 212, 255, 0.2);
    border-color: rgba(0, 212, 255, 0.4);
    transform: translateX(-2px);
    
    .back-icon {
      transform: translateX(-3px);
    }
  }
  
  .back-icon {
    font-size: 16px;
    transition: transform 0.3s;
  }
  
  .back-text {
    font-weight: 500;
  }
}

.title-input {
  flex: 1;
  font-size: 22px;
  font-weight: 600;
  border: none;
  background: transparent;
  color: #fff;
  padding: 8px 0;
  
  &:focus {
    outline: none;
  }
  
  &::placeholder {
    color: rgba(255, 255, 255, 0.3);
  }
}

.save-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  
  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #00d4ff;
    animation: pulse 1s infinite;
  }
}

.word-stats {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 20px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.6);
  
  .stat-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  
  .stat-icon {
    font-size: 12px;
  }
  
  .stat-value {
    font-weight: 600;
    color: #00d4ff;
  }
  
  .stat-label {
    color: rgba(255, 255, 255, 0.4);
  }
  
  .stat-divider {
    color: rgba(255, 255, 255, 0.2);
  }
}

:global(body.light) .word-stats {
  background: rgba(255, 255, 255, 0.6);
  border-color: rgba(8, 145, 178, 0.2);
  color: #64748b;
  
  .stat-value {
    color: #0891b2;
  }
  
  .stat-label {
    color: #94a3b8;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.editor-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.view-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 10px;
  padding: 4px;
  position: relative;
}

.toggle-btn-item {
  width: 36px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;
  
  &:hover {
    background: rgba(0, 212, 255, 0.1);
  }
  
  &.active {
    background: rgba(0, 212, 255, 0.2);
    box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
  }
}

.help-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 50%;
  cursor: pointer;
  color: #00d4ff;
  font-size: 14px;
  font-weight: 600;
  margin-left: 4px;
  transition: all 0.2s;
  
  &:hover {
    background: rgba(0, 212, 255, 0.1);
    border-color: #00d4ff;
  }
}

.link-hint {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  width: 260px;
  background: rgba(18, 18, 31, 0.98);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 12px;
  padding: 16px;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-8px);
  transition: all 0.3s;
  z-index: 100;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  
  &.show {
    opacity: 1;
    visibility: visible;
    transform: translateY(0);
  }
  
  .hint-header {
    font-size: 13px;
    font-weight: 600;
    color: #00d4ff;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(0, 212, 255, 0.2);
  }
  
  .hint-content {
    font-size: 13px;
    color: rgba(255, 255, 255, 0.8);
    line-height: 1.8;
    
    code {
      background: rgba(0, 212, 255, 0.15);
      padding: 2px 8px;
      border-radius: 4px;
      color: #00d4ff;
      font-family: 'JetBrains Mono', monospace;
    }
  }
  
  .hint-example {
    display: block;
    margin-top: 8px;
    color: rgba(255, 255, 255, 0.5);
    font-size: 12px;
  }
}

.btn-save, .btn-delete {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  
  .btn-icon {
    font-size: 16px;
  }
}

.btn-save {
  background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
  border: none;
  color: white;
  
  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 212, 255, 0.3);
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.btn-delete {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #ef4444;
  
  &:hover {
    background: rgba(239, 68, 68, 0.1);
    border-color: #ef4444;
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
  padding: 32px;
  border: none;
  background: transparent;
  color: rgba(255, 255, 255, 0.9);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 15px;
  line-height: 1.9;
  resize: none;
  
  &:focus {
    outline: none;
  }
  
  &::placeholder {
    color: rgba(255, 255, 255, 0.25);
    line-height: 1.6;
  }
}

.preview-pane {
  background: rgba(12, 12, 20, 0.5);
}

.preview-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  color: rgba(255, 255, 255, 0.85);
  line-height: 1.8;
  
  :deep(h1), :deep(h2), :deep(h3) {
    color: #fff;
    margin-bottom: 16px;
    margin-top: 24px;
    
    &:first-child {
      margin-top: 0;
    }
  }
  
  :deep(h1) { font-size: 28px; }
  :deep(h2) { font-size: 22px; }
  :deep(h3) { font-size: 18px; }
  
  :deep(p) {
    margin-bottom: 16px;
  }
  
  :deep(code) {
    background: rgba(0, 212, 255, 0.1);
    padding: 2px 8px;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #00d4ff;
  }
  
  :deep(pre) {
    background: rgba(0, 0, 0, 0.3);
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin-bottom: 16px;
    border: 1px solid rgba(0, 212, 255, 0.1);
    
    code {
      background: transparent;
      padding: 0;
      color: rgba(255, 255, 255, 0.85);
    }
  }
  
  :deep(ul), :deep(ol) {
    margin-bottom: 16px;
    padding-left: 24px;
  }
  
  :deep(li) {
    margin-bottom: 8px;
  }
  
  :deep(blockquote) {
    border-left: 3px solid #00d4ff;
    padding-left: 16px;
    margin: 16px 0;
    color: rgba(255, 255, 255, 0.6);
  }
  
  :deep(.internal-link) {
    color: #00d4ff;
    cursor: pointer;
    border-bottom: 1px dashed transparent;
    transition: all 0.2s;
    
    &:hover {
      border-bottom-color: #00d4ff;
      text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
    }
  }
  
  :deep(.broken-link) {
    color: #ff4757;
    text-decoration: line-through;
    opacity: 0.7;
  }
}

.editor-sidebar {
  width: 280px;
  background: linear-gradient(180deg, rgba(18, 18, 31, 0.95) 0%, rgba(12, 12, 20, 0.95) 100%);
  border-left: 1px solid rgba(0, 212, 255, 0.1);
  position: relative;
  transition: width 0.3s;
  
  &.collapsed {
    width: 40px;
  }
}

.toggle-btn {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 48px;
  background: rgba(0, 212, 255, 0.1);
  border: none;
  border-radius: 0 8px 8px 0;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.5);
  transition: all 0.2s;
  
  &:hover {
    background: rgba(0, 212, 255, 0.2);
    color: #00d4ff;
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
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.section-icon {
  font-size: 14px;
}

.add-tag-btn {
  margin-left: auto;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 6px;
  color: #00d4ff;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  
  &:hover {
    background: rgba(0, 212, 255, 0.1);
    border-color: #00d4ff;
  }
}

.count-badge {
  margin-left: auto;
  background: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
}

.folder-select {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.2);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover, &:focus {
    border-color: rgba(0, 212, 255, 0.4);
    outline: none;
  }
  
  option {
    background: #1a1a2e;
    color: #fff;
  }
}

.tag-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-checkbox {
  cursor: pointer;
  
  input {
    display: none;
  }
  
  .tag-label {
    display: block;
    padding: 6px 12px;
    border-radius: 16px;
    font-size: 12px;
    font-weight: 500;
    border: 1px solid;
    transition: all 0.2s;
  }
  
  &.checked .tag-label {
    box-shadow: 0 0 10px currentColor;
  }
  
  &:hover .tag-label {
    transform: translateY(-1px);
  }
}

.empty-tags {
  color: rgba(255, 255, 255, 0.4);
  font-size: 12px;
  padding: 12px 16px;
  text-align: center;
  border: 1px dashed rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  
  &:hover {
    border-color: rgba(0, 212, 255, 0.4);
    color: rgba(255, 255, 255, 0.6);
    background: rgba(0, 212, 255, 0.05);
  }
  
  .empty-icon {
    font-size: 16px;
    font-weight: 600;
  }
}

.new-tag-input {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 10px;
  margin-bottom: 8px;
  
  input {
    width: 100%;
    padding: 8px 12px;
    background: rgba(0, 0, 0, 0.3);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 6px;
    color: #fff;
    font-size: 13px;
    
    &:focus {
      outline: none;
      border-color: #00d4ff;
    }
    
    &::placeholder {
      color: rgba(255, 255, 255, 0.3);
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
    transition: all 0.2s;
    border: 2px solid transparent;
    
    &:hover {
      transform: scale(1.15);
    }
    
    &.active {
      border-color: #fff;
      box-shadow: 0 0 8px currentColor;
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
  width: 16px;
  height: 16px;
  margin-left: 6px;
  font-size: 11px;
  font-weight: bold;
  color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  cursor: help;
  
  &:hover {
    color: #fff;
    background: rgba(0, 212, 255, 0.3);
  }
}

.empty-tip {
  padding: 12px;
  text-align: center;
  
  p {
    color: rgba(255, 255, 255, 0.6);
    font-size: 13px;
    margin: 0;
  }
  
  .tip-text {
    color: rgba(255, 255, 255, 0.4);
    font-size: 12px;
    margin-top: 6px;
  }
}

.backlink-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  transition: all 0.2s;
  
  &:hover {
    background: rgba(0, 212, 255, 0.1);
    color: #fff;
    
    .link-icon {
      color: #00d4ff;
    }
  }
  
  .link-icon {
    color: rgba(255, 255, 255, 0.3);
    transition: color 0.2s;
  }
}
</style>
