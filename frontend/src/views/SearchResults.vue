<template>
  <div class="search-page">
    <div class="search-header">
      <div class="header-top">
        <button @click="goHome" class="back-btn" title="返回主页">
          <Home :size="18" />
        </button>
        <h1 class="page-title">
          <Search :size="24" class="title-icon" />
          全局搜索
        </h1>
      </div>
      <div class="search-input-wrapper">
        <Search :size="20" class="search-icon" />
        <input
          ref="searchInputRef"
          v-model="searchQuery"
          type="text"
          placeholder="搜索笔记、标签、链接..."
          class="search-input"
          @input="handleSearch"
        />
        <kbd class="search-shortcut">ESC</kbd>
      </div>
    </div>

    <div class="search-content">
      <div class="results-section" v-if="searchQuery">
        <div class="results-header">
          <span class="results-count">找到 {{ totalResults }} 个结果</span>
          <div class="filter-tabs">
            <button 
              :class="{ active: filterType === 'all' }"
              @click="filterType = 'all'"
            >
              全部
            </button>
            <button 
              :class="{ active: filterType === 'notes' }"
              @click="filterType = 'notes'"
            >
              笔记
            </button>
            <button 
              :class="{ active: filterType === 'tags' }"
              @click="filterType = 'tags'"
            >
              标签
            </button>
          </div>
        </div>

        <div class="results-list">
          <div 
            v-for="result in filteredResults" 
            :key="result.id"
            class="result-item"
            @click="openResult(result)"
          >
            <div class="result-icon">
              <FileText v-if="result.type === 'note'" :size="20" />
              <Tag v-else-if="result.type === 'tag'" :size="20" />
              <Link v-else :size="20" />
            </div>
            <div class="result-content">
              <h3 class="result-title" v-html="highlightText(result.title)"></h3>
              <p class="result-excerpt" v-if="result.excerpt" v-html="highlightText(result.excerpt)"></p>
              <div class="result-meta">
                <span class="meta-item">
                  <Folder :size="12" />
                  {{ result.category || '未分类' }}
                </span>
                <span class="meta-item" v-if="result.updated_at">
                  <Clock :size="12" />
                  {{ formatDate(result.updated_at) }}
                </span>
              </div>
            </div>
            <ChevronRight :size="16" class="result-arrow" />
          </div>

          <div v-if="filteredResults.length === 0" class="empty-results">
            <Search :size="48" class="empty-icon" />
            <h3>未找到结果</h3>
            <p>尝试使用不同的关键词</p>
          </div>
        </div>
      </div>

      <div class="empty-state" v-else>
        <Search :size="64" class="empty-icon" />
        <h2>搜索你的知识库</h2>
        <p>输入关键词查找笔记、标签和链接</p>
        <div class="quick-tips">
          <div class="tip">
            <Hash :size="14" />
            使用 <code>#标签</code> 搜索特定标签
          </div>
          <div class="tip">
            <Link :size="14" />
            使用 <code>[[标题]]</code> 搜索双向链接
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNotesStore } from '@/stores/notes'
import { useTagsStore } from '@/stores/tags'
import { useCategoryStore } from '@/stores/category'
import { 
  Search, Home, FileText, Tag, Link, Folder, Clock,
  ChevronRight, Hash
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const notesStore = useNotesStore()
const tagsStore = useTagsStore()
const categoryStore = useCategoryStore()

const searchQuery = ref('')
const filterType = ref<'all' | 'notes' | 'tags'>('all')
const searchInputRef = ref<HTMLInputElement | null>(null)

interface SearchResult {
  id: string
  type: 'note' | 'tag' | 'link'
  title: string
  excerpt?: string
  category?: string
  updated_at?: string
}

const results = computed<SearchResult[]>(() => {
  if (!searchQuery.value.trim()) return []
  
  const query = searchQuery.value.toLowerCase()
  const results: SearchResult[] = []
  
  notesStore.notes.forEach(note => {
    if (note.title.toLowerCase().includes(query) || 
        (note.content && note.content.toLowerCase().includes(query))) {
      const cat = categoryStore.categories.find(c => c.id === note.category_id)
      results.push({
        id: note.id,
        type: 'note',
        title: note.title,
        excerpt: getExcerpt(note.content, query),
        category: cat?.name,
        updated_at: note.updated_at
      })
    }
  })
  
  tagsStore.tags.forEach(tag => {
    if (tag.name.toLowerCase().includes(query)) {
      results.push({
        id: tag.id,
        type: 'tag',
        title: tag.name
      })
    }
  })
  
  return results
})

const filteredResults = computed(() => {
  if (filterType.value === 'all') return results.value
  if (filterType.value === 'notes') return results.value.filter(r => r.type === 'note')
  if (filterType.value === 'tags') return results.value.filter(r => r.type === 'tag')
  return results.value
})

const totalResults = computed(() => results.value.length)

function getExcerpt(content: string | undefined, query: string): string {
  if (!content) return ''
  const lowerContent = content.toLowerCase()
  const index = lowerContent.indexOf(query)
  if (index === -1) return content.slice(0, 100)
  
  const start = Math.max(0, index - 30)
  const end = Math.min(content.length, index + query.length + 50)
  return (start > 0 ? '...' : '') + content.slice(start, end) + (end < content.length ? '...' : '')
}

function highlightText(text: string): string {
  if (!searchQuery.value) return text
  const regex = new RegExp(`(${searchQuery.value})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}

function formatDate(date: string): string {
  const d = new Date(date)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function handleSearch() {
}

function openResult(result: SearchResult) {
  if (result.type === 'note') {
    router.push(`/notes/${result.id}`)
  } else if (result.type === 'tag') {
    router.push({ path: '/search', query: { q: `#${result.title}` } })
  }
}

function goHome() {
  router.push('/')
}

onMounted(async () => {
  await Promise.all([
    notesStore.fetchNotes(),
    tagsStore.fetchTags(),
    categoryStore.fetchCategories()
  ])
  
  if (route.query.q) {
    searchQuery.value = route.query.q as string
  }
  
  searchInputRef.value?.focus()
  
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      searchQuery.value = ''
    }
  })
})

watch(() => route.query.q, (q) => {
  if (q) {
    searchQuery.value = q as string
  }
})
</script>

<style scoped lang="scss">
.search-page {
  min-height: 100%;
  background: var(--bg-primary);
}

.search-header {
  padding: 24px 32px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-subtle);
}

.header-top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.back-btn {
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

.page-title {
  font-size: 24px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-primary);
  
  .title-icon {
    color: var(--tech-blue);
  }
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: var(--bg-hover);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  transition: all 0.2s;
  
  &:focus-within {
    border-color: var(--tech-blue);
    box-shadow: 0 0 0 3px var(--tech-blue-muted);
  }
  
  .search-icon {
    color: var(--text-muted);
  }
  
  .search-input {
    flex: 1;
    background: transparent;
    border: none;
    font-size: 16px;
    color: var(--text-primary);
    
    &:focus {
      outline: none;
    }
    
    &::placeholder {
      color: var(--text-muted);
    }
  }
  
  .search-shortcut {
    padding: 4px 8px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    font-size: 11px;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
  }
}

.search-content {
  padding: 24px 32px;
  max-width: 900px;
  margin: 0 auto;
}

.results-section {
  .results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }
  
  .results-count {
    font-size: 14px;
    color: var(--text-muted);
  }
}

.filter-tabs {
  display: flex;
  gap: 8px;
  
  button {
    padding: 6px 14px;
    background: var(--bg-hover);
    border: 1px solid var(--border-subtle);
    border-radius: 16px;
    color: var(--text-secondary);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover {
      background: var(--bg-active);
    }
    
    &.active {
      background: var(--tech-blue-muted);
      border-color: var(--tech-blue);
      color: var(--tech-blue);
    }
  }
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    background: var(--bg-hover);
    border-color: var(--border-default);
    transform: translateX(4px);
    
    .result-arrow {
      opacity: 1;
      transform: translateX(4px);
    }
  }
  
  .result-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--tech-blue-muted);
    border-radius: var(--radius-lg);
    color: var(--tech-blue);
    flex-shrink: 0;
  }
  
  .result-content {
    flex: 1;
    min-width: 0;
  }
  
  .result-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 6px;
    color: var(--text-primary);
    
    :deep(mark) {
      background: var(--primary-muted);
      color: var(--primary-color);
      padding: 0 2px;
      border-radius: 2px;
    }
  }
  
  .result-excerpt {
    font-size: 13px;
    color: var(--text-muted);
    margin-bottom: 8px;
    line-height: 1.5;
    
    :deep(mark) {
      background: var(--primary-muted);
      color: var(--primary-color);
      padding: 0 2px;
      border-radius: 2px;
    }
  }
  
  .result-meta {
    display: flex;
    gap: 16px;
  }
  
  .meta-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 12px;
    color: var(--text-muted);
  }
  
  .result-arrow {
    color: var(--text-muted);
    opacity: 0;
    transition: all 0.2s;
    margin-top: 12px;
  }
}

.empty-results {
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
  
  h3 {
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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;
  
  .empty-icon {
    color: var(--text-muted);
    margin-bottom: 24px;
    opacity: 0.3;
  }
  
  h2 {
    font-size: 24px;
    font-weight: 600;
    margin-bottom: 8px;
    color: var(--text-primary);
  }
  
  p {
    font-size: 15px;
    color: var(--text-muted);
    margin-bottom: 32px;
  }
}

.quick-tips {
  display: flex;
  flex-direction: column;
  gap: 12px;
  
  .tip {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 20px;
    background: var(--bg-hover);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-lg);
    font-size: 13px;
    color: var(--text-secondary);
    
    code {
      padding: 2px 8px;
      background: var(--tech-blue-muted);
      color: var(--tech-blue);
      border-radius: 4px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
    }
  }
}
</style>
