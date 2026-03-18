<template>
  <div class="content-editor-page">
    <div class="editor-main">
      <div class="editor-header">
        <div class="header-left">
          <button @click="goBack" class="back-btn">
            <span class="back-icon">←</span>
            <span class="back-text">返回</span>
          </button>
          <input 
            v-model="title"
            type="text"
            placeholder="输入标题..."
            class="title-input"
          />
          <div class="save-status" v-if="saving">
            <span class="status-dot"></span>
            保存中...
          </div>
        </div>
        <div class="editor-actions">
          <button @click="saveContent" class="btn-save" :disabled="saving">
            <span class="btn-icon">💾</span>
            {{ saving ? '保存中' : '保存' }}
          </button>
          <button @click="deleteContent" class="btn-delete" v-if="contentId">
            <span class="btn-icon">🗑️</span>
            删除
          </button>
        </div>
      </div>
      
      <div class="editor-container">
        <div class="editor-pane">
          <textarea 
            v-model="content"
            placeholder="开始编写内容...&#10;&#10;💡 使用 [[标题]] 创建双向链接"
            class="editor-textarea"
          />
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
            分类
          </h4>
          <select v-model="categoryId" class="category-select">
            <option v-for="cat in categoryStore.categories" :key="cat.id" :value="cat.id">
              {{ cat.icon }} {{ cat.name }}
            </option>
          </select>
        </div>
        
        <div class="sidebar-section">
          <h4 class="section-title">
            <span class="section-icon">📝</span>
            内容类型
          </h4>
          <select v-model="typeId" class="type-select">
            <option v-for="type in availableTypes" :key="type.id" :value="type.id">
              {{ type.icon }} {{ type.name }}
            </option>
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
          </div>
        </div>
        
        <div class="sidebar-section">
          <h4 class="section-title">
            <span class="section-icon">🔗</span>
            反向链接
            <span class="count-badge" v-if="backlinks.length > 0">{{ backlinks.length }}</span>
          </h4>
          <div class="backlinks-list" v-if="backlinks.length > 0">
            <div 
              v-for="link in backlinks" 
              :key="link.id"
              class="backlink-item"
              @click="openContent(link.id)"
            >
              <span class="link-icon">→</span>
              {{ link.title }}
            </div>
          </div>
          <div class="empty-tip" v-else>
            <p>暂无反向链接</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCategoryStore } from '@/stores/category'
import { useTagsStore } from '@/stores/tags'
import { useNotificationStore } from '@/stores/notification'
import { contentsApi } from '@/api/categories'

const route = useRoute()
const router = useRouter()
const categoryStore = useCategoryStore()
const tagsStore = useTagsStore()
const notification = useNotificationStore()

const contentId = computed(() => route.params.id as string)
const isNewContent = computed(() => route.name === 'NewContent' || contentId.value === 'new')

const title = ref('')
const content = ref('')
const categoryId = ref<string>('')
const typeId = ref<string>('')
const selectedTagIds = ref<string[]>([])
const saving = ref(false)
const showSidebar = ref(true)
const backlinks = ref<{ id: string; title: string }[]>([])
const showNewTagInput = ref(false)
const newTagName = ref('')
const newTagColor = ref('#00d4ff')
const newTagInputRef = ref<HTMLInputElement | null>(null)

const tagColors = [
  '#00d4ff', '#7b2cbf', '#10b981', '#f59e0b', 
  '#ef4444', '#ec4899', '#8b5cf6', '#06b6d4'
]

const availableTypes = computed(() => {
  const cat = categoryStore.categories.find(c => c.id === categoryId.value)
  return cat?.content_types || []
})

onMounted(async () => {
  await categoryStore.fetchCategories()
  await tagsStore.fetchTags()
  
  if (route.query.category_id) {
    categoryId.value = route.query.category_id as string
  }
  if (route.query.type_id) {
    typeId.value = route.query.type_id as string
  }
  
  await loadContent()
})

watch(categoryId, () => {
  if (availableTypes.value.length > 0 && !typeId.value) {
    typeId.value = availableTypes.value[0].id
  }
})

async function loadContent() {
  if (isNewContent.value) {
    title.value = ''
    content.value = ''
    selectedTagIds.value = []
    backlinks.value = []
    return
  }
  
  const contentData = await categoryStore.getContent(contentId.value)
  if (contentData) {
    title.value = contentData.title
    content.value = contentData.content || ''
    categoryId.value = contentData.category_id
    typeId.value = contentData.type_id
    selectedTagIds.value = contentData.tags.map(t => t.id)
    
    try {
      const result = await contentsApi.getBacklinks(contentId.value)
      backlinks.value = result.items
    } catch (e) {
      console.error(e)
    }
  }
}

async function saveContent() {
  if (!title.value.trim()) {
    notification.warning('请输入标题', '标题不能为空')
    return
  }
  
  if (!categoryId.value || !typeId.value) {
    notification.warning('请选择分类和内容类型')
    return
  }
  
  saving.value = true
  try {
    const data = {
      title: title.value,
      content: content.value,
      type_id: typeId.value,
      category_id: categoryId.value,
      tag_ids: selectedTagIds.value
    }
    
    if (isNewContent.value) {
      const newContent = await categoryStore.createContent(data)
      router.replace({ 
        name: 'ContentEditor', 
        params: { 
          id: newContent.id,
          categoryId: newContent.category_id 
        }
      })
    } else {
      await categoryStore.updateContent(contentId.value, data)
    }
  } catch (error) {
    console.error(error)
  } finally {
    saving.value = false
  }
}

async function deleteContent() {
  if (!confirm('确定要删除此内容吗？此操作无法撤销。')) return
  
  try {
    await categoryStore.deleteContent(contentId.value)
    router.push('/categories')
  } catch (error) {
    console.error(error)
  }
}

function goBack() {
  router.push('/categories')
}

function openContent(id: string) {
  router.push({ name: 'ContentEditor', params: { id } })
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
.content-editor-page {
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

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.editor-actions {
  display: flex;
  gap: 12px;
}

.btn-save, .btn-delete {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-save {
  background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
  border: none;
  color: white;
  
  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 212, 255, 0.3);
  }
}

.btn-delete {
  background: transparent;
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #ef4444;
  
  &:hover {
    background: rgba(239, 68, 68, 0.1);
  }
}

.editor-container {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.editor-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
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
  }
}

.editor-sidebar {
  width: 280px;
  background: rgba(18, 18, 31, 0.95);
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
  margin-bottom: 12px;
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
  
  &:hover {
    background: rgba(0, 212, 255, 0.1);
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

.category-select, .type-select {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.2);
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  
  &:focus {
    outline: none;
    border-color: #00d4ff;
  }
  
  option {
    background: #1a1a2e;
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
    border: 1px solid;
    transition: all 0.2s;
  }
  
  &.checked .tag-label {
    box-shadow: 0 0 10px currentColor;
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
  }
}

.color-options {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.color-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  
  &:hover {
    transform: scale(1.15);
  }
  
  &.active {
    border-color: #fff;
    box-shadow: 0 0 8px currentColor;
  }
}

.backlinks-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
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
  
  &:hover {
    background: rgba(0, 212, 255, 0.1);
    color: #fff;
  }
}

.empty-tip {
  padding: 12px;
  text-align: center;
  color: rgba(255, 255, 255, 0.4);
  font-size: 13px;
}
</style>
