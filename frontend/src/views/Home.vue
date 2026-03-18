<template>
  <div class="home-page">
    <div class="home-header">
      <div class="greeting-section">
        <div class="greeting-text">
          <span class="greeting-time">{{ timeGreeting }}</span>
          <h1 class="greeting-name">{{ username }}</h1>
        </div>
        <p class="greeting-hint">今天想记录些什么？</p>
      </div>
      <div class="quick-stats">
        <div class="stat-item">
          <span class="stat-value">{{ totalNotes }}</span>
          <span class="stat-label">篇笔记</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-value">{{ totalFolders }}</span>
          <span class="stat-label">个文件夹</span>
        </div>
        <div class="stat-divider"></div>
        <div class="stat-item">
          <span class="stat-value">{{ totalLinks }}</span>
          <span class="stat-label">条链接</span>
        </div>
      </div>
    </div>

    <div class="home-content">
      <div class="main-section">
        <div class="section-header">
          <h2 class="section-title">分类</h2>
          <span class="section-count">{{ categories.length }}</span>
        </div>
        <div class="category-list">
          <div
            v-for="category in categories"
            :key="category.id"
            class="category-item"
            @click="enterCategory(category)"
          >
            <div class="category-icon" :style="{ backgroundColor: getCategoryColor(category.name) + '20', color: getCategoryColor(category.name) }">
              <component :is="getCategoryIcon(category.name)" :size="20" />
            </div>
            <div class="category-info">
              <h3 class="category-name">{{ category.name }}</h3>
              <p class="category-desc">{{ getCategoryDesc(category.name) }}</p>
            </div>
            <div class="category-meta">
              <span class="meta-item">
                <Folder :size="14" />
                {{ getFolderCount(category.id) }}
              </span>
              <span class="meta-item">
                <FileText :size="14" />
                {{ getContentCount(category.id) }}
              </span>
            </div>
            <ChevronRight class="category-arrow" :size="18" />
          </div>
        </div>
      </div>

      <div class="side-section">
        <div class="quick-actions">
          <h3 class="section-title">快捷操作</h3>
          <div class="action-list">
            <button class="action-item" @click="goToSearch">
              <Search :size="18" />
              <span>搜索笔记</span>
            </button>
            <button class="action-item" @click="goToGraph">
              <Network :size="18" />
              <span>知识图谱</span>
            </button>
            <button class="action-item" @click="goToSkills">
              <Zap :size="18" />
              <span>智能模块</span>
            </button>
          </div>
        </div>

        <div class="recent-section">
          <h3 class="section-title">最近编辑</h3>
          <div class="recent-list">
            <div
              v-for="note in recentNotes"
              :key="note.id"
              class="recent-item"
              @click="openNote(note.id)"
            >
              <div class="recent-dot"></div>
              <div class="recent-info">
                <span class="recent-title">{{ note.title }}</span>
                <span class="recent-date">{{ formatDate(note.updated_at) }}</span>
              </div>
            </div>
            <div v-if="notesStore.notes.length === 0" class="empty-state">
              <p>暂无笔记</p>
              <p class="empty-hint">创建第一篇笔记开始记录</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useCategoryStore } from '@/stores/category'
import { useFoldersStore } from '@/stores/folders'
import { useNotesStore } from '@/stores/notes'
import { useAuthStore } from '@/stores/auth'
import { 
  FileText, Folder, ChevronRight, Search, Network, Zap, User, Briefcase, TrendingUp
} from 'lucide-vue-next'

const router = useRouter()
const categoryStore = useCategoryStore()
const foldersStore = useFoldersStore()
const notesStore = useNotesStore()
const authStore = useAuthStore()

const categories = computed(() => categoryStore.categories)
const username = computed(() => authStore.user?.username || '用户')
const totalNotes = computed(() => notesStore.notes.length)
const totalFolders = computed(() => foldersStore.folders.length)
const recentNotes = computed(() => notesStore.notes.slice(0, 5))

const totalLinks = computed(() => {
  let count = 0
  notesStore.notes.forEach(note => {
    const matches = note.content?.match(/\[\[([^\]]+)\]\]/g) || []
    count += matches.length
  })
  return count
})

const timeGreeting = computed(() => {
  const hour = new Date().getHours()
  if (hour >= 5 && hour < 12) return '早安'
  if (hour >= 12 && hour < 18) return '午安'
  if (hour >= 18 && hour < 22) return '傍晚好'
  return '夜深了'
})

function getCategoryIcon(name: string) {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('个人')) return User
  if (nameLower.includes('工作')) return Briefcase
  if (nameLower.includes('素材')) return TrendingUp
  return Folder
}

function getCategoryColor(name: string): string {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('个人')) return '#f59e0b'
  if (nameLower.includes('工作')) return '#3b82f6'
  if (nameLower.includes('素材')) return '#10b981'
  return '#8b5cf6'
}

function getCategoryDesc(name: string): string {
  const nameLower = name.toLowerCase()
  if (nameLower.includes('个人')) return '笔记、日记、灵感收集'
  if (nameLower.includes('工作')) return '项目文档、任务管理'
  if (nameLower.includes('素材')) return '图片、链接、附件'
  return '内容管理'
}

function getFolderCount(categoryId: string): number {
  return foldersStore.folders.filter(f => f.category_id === categoryId).length
}

function getContentCount(categoryId: string): number {
  return categoryStore.contents.filter(c => c.category_id === categoryId).length
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function enterCategory(category: any) {
  categoryStore.currentCategory = category
  router.push(`/categories/${category.id}`)
}

function openNote(noteId: string) {
  router.push(`/notes/${noteId}`)
}

function goToSearch() {
  router.push('/search')
}

function goToGraph() {
  router.push('/graph')
}

function goToSkills() {
  router.push('/skills')
}

onMounted(async () => {
  await categoryStore.fetchCategories()
  await foldersStore.fetchFolders()
  await categoryStore.fetchContents()
  await notesStore.fetchNotes()
})
</script>

<style scoped lang="scss">
.home-page {
  padding: 24px;
  min-height: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.home-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  margin-bottom: 24px;
}

.greeting-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.greeting-text {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.greeting-time {
  font-size: 14px;
  color: var(--text-tertiary);
}

.greeting-name {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.greeting-hint {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

.quick-stats {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius-lg);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--border-default);
}

.home-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
}

.main-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  margin: 0;
}

.section-count {
  font-size: 12px;
  color: var(--text-muted);
  padding: 2px 8px;
  background: var(--bg-hover);
  border-radius: 10px;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.category-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-base);

  &:hover {
    background: var(--bg-elevated);
    border-color: var(--border-default);
    transform: translateX(4px);

    .category-arrow {
      opacity: 1;
      transform: translateX(0);
    }
  }
}

.category-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  flex-shrink: 0;
}

.category-info {
  flex: 1;
  min-width: 0;
}

.category-name {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 4px;
}

.category-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.category-meta {
  display: flex;
  gap: 16px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-tertiary);
}

.category-arrow {
  color: var(--text-muted);
  opacity: 0;
  transform: translateX(-8px);
  transition: all var(--transition-base);
}

.side-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.quick-actions {
  padding: 20px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 12px;
}

.action-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: transparent;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 14px;
  text-align: left;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
  }
}

.recent-section {
  padding: 20px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 12px;
}

.recent-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);

  &:hover {
    background: var(--bg-hover);

    .recent-dot {
      background: var(--primary-color);
    }
  }
}

.recent-dot {
  width: 6px;
  height: 6px;
  margin-top: 6px;
  border-radius: 50%;
  background: var(--text-muted);
  flex-shrink: 0;
  transition: background var(--transition-fast);
}

.recent-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.recent-title {
  font-size: 13px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-date {
  font-size: 12px;
  color: var(--text-muted);
}

.empty-state {
  padding: 24px;
  text-align: center;

  p {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
  }

  .empty-hint {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
  }
}

@media (max-width: 900px) {
  .home-content {
    grid-template-columns: 1fr;
  }

  .side-section {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .quick-actions,
  .recent-section {
    flex: 1;
    min-width: 280px;
  }
}

@media (max-width: 600px) {
  .home-page {
    padding: 16px;
  }

  .home-header {
    flex-direction: column;
    gap: 16px;
    padding: 20px;
  }

  .quick-stats {
    width: 100%;
    justify-content: space-around;
  }

  .category-meta {
    display: none;
  }
}
</style>
