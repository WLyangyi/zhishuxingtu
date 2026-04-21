<template>
  <div class="import-history">
    <div class="history-header">
      <h2 class="history-title">导入历史</h2>
      <div class="history-filters">
        <select v-model="filterType" class="filter-select" @change="loadHistory">
          <option :value="null">全部类型</option>
          <option value="pdf">PDF 文档</option>
          <option value="url">网页</option>
          <option value="video">本地视频</option>
          <option value="video_url">在线视频</option>
        </select>
        <button class="refresh-btn" @click="loadHistory">
          <RefreshCw :size="16" />
        </button>
      </div>
    </div>

    <div v-if="importStore.historyLoading" class="loading-state">
      <Loader2 :size="24" class="spinning" />
      <span>加载中...</span>
    </div>

    <div v-else-if="importStore.history.length === 0" class="empty-state">
      <FileText :size="48" class="empty-icon" />
      <p>暂无导入记录</p>
    </div>

    <div v-else class="history-list">
      <div v-for="item in importStore.history" :key="item.id" class="history-item">
        <div class="item-icon">
          <FileText v-if="item.source_type === 'pdf'" :size="18" />
          <Globe v-else-if="item.source_type === 'url'" :size="18" />
          <Video v-else :size="18" />
        </div>
        <div class="item-content">
          <div class="item-title">{{ item.generated_title || '未命名' }}</div>
          <div class="item-meta">
            <span class="meta-type">{{ getTypeLabel(item.source_type) }}</span>
            <span v-if="item.source_filename" class="meta-filename">{{ item.source_filename }}</span>
            <span v-if="item.platform" class="meta-platform">{{ item.platform }}</span>
            <span v-if="item.created_at" class="meta-time">{{ formatTime(item.created_at) }}</span>
          </div>
        </div>
        <div class="item-status" :class="item.status">
          {{ item.status === 'completed' ? '已完成' : item.status }}
        </div>
        <button v-if="item.note_id" class="item-link" @click="goToNote(item.note_id)">
          <ExternalLink :size="14" />
        </button>
      </div>
    </div>

    <div v-if="importStore.historyTotal > pageSize" class="pagination">
      <button class="page-btn" :disabled="page <= 1" @click="page--; loadHistory()">上一页</button>
      <span class="page-info">{{ page }} / {{ totalPages }}</span>
      <button class="page-btn" :disabled="page >= totalPages" @click="page++; loadHistory()">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useImportStore } from '@/stores/import'
import { FileText, Globe, Video, RefreshCw, Loader2, ExternalLink } from 'lucide-vue-next'

const router = useRouter()
const importStore = useImportStore()

const filterType = ref<string | null>(null)
const page = ref(1)
const pageSize = 20

const totalPages = computed(() => Math.ceil(importStore.historyTotal / pageSize))

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    pdf: 'PDF',
    url: '网页',
    video: '视频',
    video_url: '在线视频'
  }
  return labels[type] || type
}

function formatTime(isoStr: string): string {
  try {
    const date = new Date(isoStr)
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function loadHistory() {
  importStore.fetchHistory({
    source_type: filterType.value || undefined,
    page: page.value,
    page_size: pageSize
  })
}

function goToNote(noteId: string) {
  router.push(`/notes/${noteId}`)
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped lang="scss">
.import-history {
  padding: 24px;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.history-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary, #fff);
  margin: 0;
}

.history-filters {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-select {
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary, #fff);
  outline: none;
  cursor: pointer;
  appearance: none;

  option {
    background: var(--bg-primary, #1a1a2e);
    color: var(--text-primary, #fff);
  }
}

.refresh-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--text-muted, #888);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: var(--text-primary, #fff);
  }
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px;
  color: var(--text-muted, #888);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px;
  color: var(--text-muted, #666);

  .empty-icon {
    opacity: 0.3;
  }

  p {
    margin: 0;
    font-size: 14px;
  }
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.08);
  }
}

.item-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(0, 102, 255, 0.1);
  color: var(--tech-blue, #0066FF);
  flex-shrink: 0;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #fff);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted, #888);
}

.item-status {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;

  &.completed {
    background: rgba(16, 185, 129, 0.1);
    color: #10b981;
  }

  &.failed {
    background: rgba(239, 68, 68, 0.1);
    color: #ef4444;
  }
}

.item-link {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: var(--text-muted, #888);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;

  &:hover {
    background: rgba(0, 102, 255, 0.1);
    color: var(--tech-blue, #0066FF);
  }
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 20px;
}

.page-btn {
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: var(--text-secondary, #aaa);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.08);
    color: var(--text-primary, #fff);
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.page-info {
  font-size: 13px;
  color: var(--text-muted, #888);
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
