<template>
  <div class="search-page">
    <div class="search-header">
      <div class="header-left">
        <button @click="goHome" class="back-btn" title="返回主页">
          <span class="back-icon">←</span>
          <span class="back-text">主页</span>
        </button>
        <h2>搜索结果: "{{ searchQuery }}"</h2>
      </div>
    </div>
    
    <div class="search-results">
      <div 
        v-for="note in notesStore.notes" 
        :key="note.id"
        class="result-card"
        @click="openNote(note.id)"
      >
        <h3>{{ note.title }}</h3>
        <p class="result-preview">{{ getPreview(note.content) }}</p>
        <div class="result-meta">
          <span>{{ formatDate(note.updated_at) }}</span>
        </div>
      </div>
      
      <div v-if="notesStore.notes.length === 0" class="no-results">
        <div class="empty-icon">🔍</div>
        <h3>没有找到相关笔记</h3>
        <p>尝试使用不同的关键词搜索</p>
        <button @click="goHome" class="back-home-btn">返回主页</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNotesStore } from '@/stores/notes'
import { searchApi } from '@/api/search'

const route = useRoute()
const router = useRouter()
const notesStore = useNotesStore()

const searchQuery = ref('')

onMounted(async () => {
  searchQuery.value = route.query.q as string
  if (searchQuery.value) {
    const response = await searchApi.search(searchQuery.value)
    notesStore.notes = response.data.items
  }
})

watch(() => route.query.q, async (newQuery) => {
  if (newQuery) {
    searchQuery.value = newQuery as string
    const response = await searchApi.search(searchQuery.value)
    notesStore.notes = response.data.items
  }
})

function goHome() {
  router.push('/')
}

function openNote(id: string) {
  router.push(`/notes/${id}`)
}

function getPreview(content: string | null): string {
  if (!content) return '暂无内容'
  return content.slice(0, 200) + (content.length > 200 ? '...' : '')
}

function formatDate(date: string): string {
  return new Date(date).toLocaleDateString('zh-CN')
}
</script>

<style scoped lang="scss">
.search-page {
  padding: 24px;
  min-height: 100%;
}

.search-header {
  margin-bottom: 24px;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  
  h2 {
    font-size: 20px;
    font-weight: 600;
  }
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

.search-results {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-card {
  background: linear-gradient(135deg, rgba(18, 18, 31, 0.9) 0%, rgba(26, 26, 46, 0.9) 100%);
  border: 1px solid rgba(0, 212, 255, 0.1);
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    border-color: rgba(0, 212, 255, 0.3);
    transform: translateY(-2px);
    box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
  }
  
  h3 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
    color: #fff;
  }
  
  .result-preview {
    color: rgba(255, 255, 255, 0.5);
    font-size: 14px;
    line-height: 1.6;
    margin-bottom: 12px;
  }
  
  .result-meta {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.3);
  }
}

.no-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  
  .empty-icon {
    font-size: 48px;
    margin-bottom: 16px;
    opacity: 0.5;
  }
  
  h3 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 8px;
    color: rgba(255, 255, 255, 0.6);
  }
  
  p {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.3);
    margin-bottom: 20px;
  }
}

.back-home-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
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
}
</style>
