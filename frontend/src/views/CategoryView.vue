<template>
  <div class="category-view">
    <div class="category-sidebar">
      <div class="sidebar-header">
        <div class="header-top">
          <button @click="goHome" class="back-btn" title="返回主页">
            <span>🏠</span>
          </button>
          <h2 class="sidebar-title">
            <span class="title-icon">📚</span>
            内容分类
          </h2>
        </div>
        <button @click="showCreateCategoryModal = true" class="add-btn" title="新建分类">
          <span>+</span>
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
            {{ category.icon }}
          </div>
          <div class="category-info">
            <span class="category-name">{{ category.name }}</span>
            <span class="category-count">{{ getCategoryContentCount(category.id) }} 项</span>
          </div>
          <div class="category-types">
            <span 
              v-for="type in category.content_types.slice(0, 3)" 
              :key="type.id"
              class="type-badge"
              :style="{ backgroundColor: type.color + '20', color: type.color }"
            >
              {{ type.icon }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div class="category-main">
      <div v-if="selectedCategory" class="main-content">
        <div class="main-header">
          <div class="header-left">
            <h1 class="page-title">
              <span class="title-icon" :style="{ color: selectedCategory.color }">
                {{ selectedCategory.icon }}
              </span>
              {{ selectedCategory.name }}
            </h1>
            <div class="type-tabs">
              <button 
                class="type-tab"
                :class="{ active: selectedTypeId === null }"
                @click="selectType(null)"
              >
                全部
              </button>
              <button 
                v-for="type in selectedCategory.content_types" 
                :key="type.id"
                class="type-tab"
                :class="{ active: selectedTypeId === type.id }"
                :style="{ '--type-color': type.color }"
                @click="selectType(type.id)"
              >
                {{ type.icon }} {{ type.name }}
              </button>
              <button class="type-tab add" @click="showCreateTypeModal = true">
                + 新建类型
              </button>
            </div>
          </div>
          <div class="header-actions">
            <div class="search-box">
              <span class="search-icon">🔍</span>
              <input 
                v-model="searchKeyword"
                type="text"
                placeholder="搜索内容..."
                @keyup.enter="searchContents"
              />
            </div>
            <button @click="createNewContent" class="create-btn">
              <span class="btn-icon">✏️</span>
              新建内容
            </button>
          </div>
        </div>

        <div class="content-grid">
          <div 
            v-for="content in categoryStore.contents" 
            :key="content.id"
            class="content-card"
            @click="openContent(content)"
          >
            <div class="card-header">
              <span class="content-type-badge" :style="{ color: content.content_type?.color }">
                {{ content.content_type?.icon }}
              </span>
              <h3 class="content-title">{{ content.title }}</h3>
            </div>
            <p class="content-preview">{{ getPreview(content.content) }}</p>
            <div class="card-footer">
              <div class="content-tags">
                <span 
                  v-for="tag in content.tags.slice(0, 2)" 
                  :key="tag.id"
                  class="tag"
                  :style="{ backgroundColor: tag.color + '20', color: tag.color }"
                >
                  {{ tag.name }}
                </span>
              </div>
              <span class="content-date">{{ formatDate(content.updated_at) }}</span>
            </div>
          </div>

          <div v-if="categoryStore.contents.length === 0" class="empty-state">
            <div class="empty-icon">📝</div>
            <h3>暂无内容</h3>
            <p>点击「新建内容」开始记录</p>
          </div>
        </div>

        <div v-if="categoryStore.totalContents > categoryStore.pageSize" class="pagination">
          <button 
            :disabled="categoryStore.currentPage === 1"
            @click="changePage(categoryStore.currentPage - 1)"
          >
            上一页
          </button>
          <span class="page-info">
            {{ categoryStore.currentPage }} / {{ totalPages }}
          </span>
          <button 
            :disabled="categoryStore.currentPage >= totalPages"
            @click="changePage(categoryStore.currentPage + 1)"
          >
            下一页
          </button>
        </div>
      </div>

      <div v-else class="empty-selection">
        <div class="empty-icon">👈</div>
        <h2>选择一个分类</h2>
        <p>从左侧选择分类查看内容</p>
      </div>
    </div>

    <div v-if="showCreateCategoryModal" class="modal-overlay" @click.self="showCreateCategoryModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新建分类</h3>
          <button @click="showCreateCategoryModal = false" class="close-btn">×</button>
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

    <div v-if="showCreateTypeModal" class="modal-overlay" @click.self="showCreateTypeModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新建内容类型</h3>
          <button @click="showCreateTypeModal = false" class="close-btn">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>类型名称</label>
            <input v-model="newType.name" type="text" placeholder="输入类型名称" />
          </div>
          <div class="form-group">
            <label>图标</label>
            <input v-model="newType.icon" type="text" placeholder="如：📝" />
          </div>
          <div class="form-group">
            <label>颜色</label>
            <div class="color-picker">
              <span 
                v-for="color in colorOptions" 
                :key="color"
                class="color-dot"
                :class="{ active: newType.color === color }"
                :style="{ backgroundColor: color }"
                @click="newType.color = color"
              />
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showCreateTypeModal = false" class="btn-cancel">取消</button>
          <button @click="handleCreateType" class="btn-confirm">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCategoryStore } from '@/stores/category'
import type { Category } from '@/types/category'

const router = useRouter()
const categoryStore = useCategoryStore()

const selectedCategoryId = ref<string | null>(null)
const selectedTypeId = ref<string | null>(null)
const searchKeyword = ref('')
const showCreateCategoryModal = ref(false)
const showCreateTypeModal = ref(false)

const newCategory = ref({
  name: '',
  icon: '📁',
  color: '#00d4ff'
})

const newType = ref({
  name: '',
  icon: '📝',
  color: '#00d4ff'
})

const colorOptions = [
  '#00d4ff', '#7b2cbf', '#10b981', '#f59e0b',
  '#ef4444', '#ec4899', '#8b5cf6', '#06b6d4'
]

const selectedCategory = computed(() => 
  categoryStore.categories.find(c => c.id === selectedCategoryId.value)
)

const totalPages = computed(() => 
  Math.ceil(categoryStore.totalContents / categoryStore.pageSize)
)

onMounted(async () => {
  await categoryStore.fetchCategories()
  if (categoryStore.categories.length > 0) {
    selectCategory(categoryStore.categories[0])
  }
})

function selectCategory(category: Category) {
  selectedCategoryId.value = category.id
  selectedTypeId.value = null
  searchKeyword.value = ''
  categoryStore.currentCategory = category
  categoryStore.fetchContents({ category_id: category.id })
}

function selectType(typeId: string | null) {
  selectedTypeId.value = typeId
  categoryStore.fetchContents({ 
    category_id: selectedCategoryId.value!,
    type_id: typeId || undefined
  })
}

function searchContents() {
  categoryStore.fetchContents({
    category_id: selectedCategoryId.value!,
    type_id: selectedTypeId.value || undefined,
    keyword: searchKeyword.value || undefined
  })
}

function getCategoryContentCount(categoryId: string): number {
  return categoryStore.contents.filter(c => c.category_id === categoryId).length
}

function getPreview(content: string | null): string {
  if (!content) return '暂无内容...'
  const text = content.replace(/\[\[([^\]]+)\]\]/g, '→ $1')
  return text.slice(0, 100) + (text.length > 100 ? '...' : '')
}

function formatDate(date: string): string {
  const d = new Date(date)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function createNewContent() {
  router.push({ 
    name: 'NewContent', 
    query: { 
      category_id: selectedCategoryId.value,
      type_id: selectedTypeId.value
    }
  })
}

function openContent(content: any) {
  router.push({ name: 'ContentEditor', params: { id: content.id } })
}

function goHome() {
  router.push('/')
}

function changePage(page: number) {
  categoryStore.setPage(page)
  categoryStore.fetchContents({
    category_id: selectedCategoryId.value!,
    type_id: selectedTypeId.value || undefined,
    keyword: searchKeyword.value || undefined
  })
}

async function handleCreateCategory() {
  if (!newCategory.value.name.trim()) return
  
  try {
    await categoryStore.createCategory(newCategory.value)
    showCreateCategoryModal.value = false
    newCategory.value = { name: '', icon: '📁', color: '#00d4ff' }
  } catch (e) {
    console.error(e)
  }
}

async function handleCreateType() {
  if (!newType.value.name.trim() || !selectedCategoryId.value) return
  
  try {
    await categoryStore.createContentType({
      ...newType.value,
      category_id: selectedCategoryId.value
    })
    showCreateTypeModal.value = false
    newType.value = { name: '', icon: '📝', color: '#00d4ff' }
  } catch (e) {
    console.error(e)
  }
}
</script>

<style scoped lang="scss">
.category-view {
  display: flex;
  height: calc(100vh - 0px);
  background: linear-gradient(135deg, #0a0a14 0%, #0d0d1a 100%);
}

.category-sidebar {
  width: 280px;
  background: rgba(18, 18, 31, 0.95);
  border-right: 1px solid rgba(0, 212, 255, 0.1);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
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
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  cursor: pointer;
  font-size: 16px;
  transition: all 0.2s;

  &:hover {
    background: rgba(0, 212, 255, 0.2);
    border-color: #00d4ff;
  }
}

.sidebar-title {
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  
  .title-icon {
    font-size: 20px;
  }
}

.add-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 212, 255, 0.1);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  color: #00d4ff;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: rgba(0, 212, 255, 0.2);
    border-color: #00d4ff;
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
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 4px;
  
  &:hover {
    background: rgba(0, 212, 255, 0.08);
  }
  
  &.active {
    background: rgba(0, 212, 255, 0.15);
    border: 1px solid rgba(0, 212, 255, 0.3);
  }
}

.category-icon {
  font-size: 24px;
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
  color: #fff;
}

.category-count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
}

.category-types {
  display: flex;
  gap: 4px;
}

.type-badge {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  font-size: 12px;
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
  background: rgba(18, 18, 31, 0.8);
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 12px;
  
  .title-icon {
    font-size: 28px;
  }
}

.type-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.type-tab {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: rgba(255, 255, 255, 0.1);
  }
  
  &.active {
    background: rgba(var(--type-color, 0, 212, 255), 0.2);
    border-color: rgba(var(--type-color, 0, 212, 255), 0.5);
    color: rgb(var(--type-color, 0, 212, 255));
  }
  
  &.add {
    border-style: dashed;
    color: rgba(255, 255, 255, 0.4);
  }
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
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 12px;
  width: 300px;
  
  .search-icon {
    font-size: 14px;
    opacity: 0.5;
  }
  
  input {
    flex: 1;
    background: transparent;
    border: none;
    color: #fff;
    font-size: 14px;
    
    &:focus {
      outline: none;
    }
    
    &::placeholder {
      color: rgba(255, 255, 255, 0.3);
    }
  }
}

.create-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: linear-gradient(135deg, #00d4ff 0%, #7b2cbf 100%);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 212, 255, 0.3);
  }
  
  .btn-icon {
    font-size: 16px;
  }
}

.content-grid {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  align-content: start;
}

.content-card {
  background: rgba(18, 18, 31, 0.9);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    transform: translateY(-4px);
    border-color: rgba(0, 212, 255, 0.3);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
  }
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
}

.content-type-badge {
  font-size: 18px;
}

.content-title {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  line-height: 1.4;
  flex: 1;
}

.content-preview {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.6;
  margin-bottom: 12px;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.content-tags {
  display: flex;
  gap: 6px;
  
  .tag {
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
  }
}

.content-date {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
}

.empty-state, .empty-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  text-align: center;
  
  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.5;
  }
  
  h2, h3 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
    color: rgba(255, 255, 255, 0.6);
  }
  
  p {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.3);
  }
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 20px;
  
  button {
    padding: 8px 16px;
    background: rgba(0, 212, 255, 0.1);
    border: 1px solid rgba(0, 212, 255, 0.2);
    border-radius: 8px;
    color: #00d4ff;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover:not(:disabled) {
      background: rgba(0, 212, 255, 0.2);
    }
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
  }
  
  .page-info {
    color: rgba(255, 255, 255, 0.6);
    font-size: 14px;
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
  background: rgba(18, 18, 31, 0.98);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 16px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid rgba(0, 212, 255, 0.1);
  
  h3 {
    font-size: 18px;
    font-weight: 600;
  }
  
  .close-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: rgba(255, 255, 255, 0.5);
    font-size: 24px;
    cursor: pointer;
    
    &:hover {
      color: #fff;
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
    color: rgba(255, 255, 255, 0.6);
    margin-bottom: 8px;
  }
  
  input {
    width: 100%;
    padding: 10px 14px;
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(0, 212, 255, 0.2);
    border-radius: 8px;
    color: #fff;
    font-size: 14px;
    
    &:focus {
      outline: none;
      border-color: #00d4ff;
    }
    
    &::placeholder {
      color: rgba(255, 255, 255, 0.3);
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
    border-color: #fff;
    box-shadow: 0 0 10px currentColor;
  }
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid rgba(0, 212, 255, 0.1);
}

.btn-cancel, .btn-confirm {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: rgba(255, 255, 255, 0.7);
  
  &:hover {
    background: rgba(255, 255, 255, 0.05);
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
