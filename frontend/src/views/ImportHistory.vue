<template>
  <div class="imports">
    <div class="imports__inner">
      <header class="imports__head">
        <div class="imports__title-group">
          <span class="readout">IMPORT · 导入历史</span>
          <h1 class="imports__title">导入历史</h1>
          <p class="imports__desc">
            共 {{ importStore.historyTotal }} 条记录。PDF、网页与视频的解析结果都在这里。
          </p>
        </div>

        <div class="imports__tools">
          <AppSelect
            :model-value="filterType"
            :options="filterOptions"
            placeholder="全部来源"
            aria-label="按来源筛选"
            @update:model-value="onFilter"
          />
          <IconButton label="刷新" @click="reload">
            <RefreshCw :size="15" :stroke-width="1.8" :class="importStore.historyLoading && 'spin'" />
          </IconButton>
        </div>
      </header>

      <div class="imports__stats">
        <span class="imports__stat"><b class="num">{{ counts.completed }}</b> 已完成</span>
        <span class="imports__stat"><b class="num">{{ counts.processing }}</b> 处理中</span>
        <span class="imports__stat"><b class="num">{{ counts.failed }}</b> 失败</span>
        <span class="readout imports__stat-note">本页统计</span>
      </div>

      <div v-if="importStore.historyLoading" class="imports__skeleton">
        <Skeleton v-for="index in 6" :key="index" :height="14" />
      </div>

      <EmptyState
        v-else-if="!importStore.history.length"
        title="还没有导入记录"
        description="导入 PDF、网页或视频后，解析结果会出现在这里。"
      >
        <AppButton size="sm" @click="importStore.openImportModal()">开始导入</AppButton>
      </EmptyState>

      <div v-else class="imports__table">
        <div class="imports__thead" aria-hidden="true">
          <span>TIME</span>
          <span>TYPE</span>
          <span>TITLE</span>
          <span>STATUS</span>
          <span />
        </div>

        <button
          v-for="item in importStore.history"
          :key="item.id"
          type="button"
          :class="['import-row', item.note_id && 'import-row--linked']"
          :disabled="!item.note_id"
          @click="openItem(item)"
        >
          <span class="import-row__time">{{ formatTime(item.created_at) }}</span>

          <span class="import-row__type">
            <component :is="typeIcon(item.source_type)" :size="13" :stroke-width="1.8" />
            {{ typeLabel(item.source_type) }}
          </span>

          <span class="import-row__main">
            <span class="import-row__title">{{ item.generated_title || '未命名' }}</span>
            <span class="import-row__source">{{ sourceLine(item) }}</span>
          </span>

          <span class="import-row__status">
            <StatusDot :status="statusTone(item.status)" :label="statusLabel(item.status)" />
            {{ statusLabel(item.status) }}
          </span>

          <span class="import-row__action">
            <ExternalLink v-if="item.note_id" :size="13" :stroke-width="1.8" />
          </span>
        </button>
      </div>

      <div v-if="totalPages > 1" class="imports__pager">
        <button type="button" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
        <span class="num">{{ page }} / {{ totalPages }}</span>
        <button type="button" :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ExternalLink, FileText, Globe, RefreshCw, Video } from 'lucide-vue-next'
import AppButton from '@/components/ui/AppButton.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import IconButton from '@/components/ui/IconButton.vue'
import Skeleton from '@/components/ui/Skeleton.vue'
import StatusDot from '@/components/ui/StatusDot.vue'
import { useImportStore } from '@/stores/import'
import { parseServerTime } from '@/lib/time'
import type { ImportHistoryItem } from '@/types/import'

const router = useRouter()
const importStore = useImportStore()

const page = ref(1)
const pageSize = 20
const filterType = ref('')

const filterOptions = [
  { label: '全部来源', value: '' },
  { label: 'PDF 文档', value: 'pdf' },
  { label: '网页', value: 'url' },
  { label: '本地视频', value: 'video' },
  { label: '在线视频', value: 'video_url' }
]

const totalPages = computed(() => Math.max(1, Math.ceil(importStore.historyTotal / pageSize)))

const counts = computed(() => {
  let completed = 0
  let processing = 0
  let failed = 0

  for (const item of importStore.history) {
    if (item.status === 'completed') completed += 1
    else if (item.status === 'failed') failed += 1
    else processing += 1
  }

  return { completed, processing, failed }
})

const TYPE_LABELS: Record<string, string> = {
  pdf: 'PDF',
  url: '网页',
  video: '视频',
  video_url: '在线视频'
}

function typeLabel(type: string) {
  return TYPE_LABELS[type] ?? type.toUpperCase()
}

function typeIcon(type: string) {
  if (type === 'pdf') return FileText
  if (type === 'url') return Globe
  return Video
}

function statusTone(status: string): 'success' | 'error' | 'running' | 'idle' {
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  if (status === 'pending') return 'idle'
  return 'running'
}

function statusLabel(status: string) {
  if (status === 'completed') return '已完成'
  if (status === 'failed') return '失败'
  if (status === 'pending') return '排队中'
  return '处理中'
}

function formatTime(value?: string) {
  if (!value) return '—'
  const date = parseServerTime(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function sourceLine(item: ImportHistoryItem) {
  return item.source_filename || item.source_url || item.platform || '—'
}

function openItem(item: ImportHistoryItem) {
  if (item.note_id) router.push(`/notes/${item.note_id}`)
}

async function load() {
  await importStore.fetchHistory({
    source_type: filterType.value || undefined,
    page: page.value,
    page_size: pageSize
  })
}

function reload() {
  page.value = 1
  void load()
}

function onFilter(value: string) {
  filterType.value = value
  page.value = 1
  void load()
}

function goPage(next: number) {
  page.value = next
  void load()
}

onMounted(load)
</script>

<style scoped>
.imports {
  min-height: 100%;
  padding: 40px 32px 72px;
}

.imports__inner {
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
}

.imports__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--line);
}

.imports__title-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.imports__title {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 500;
  line-height: 1.1;
  letter-spacing: -0.035em;
}

.imports__desc {
  font-size: 12px;
  line-height: 1.6;
  color: var(--t3);
}

.imports__tools {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
}

.imports__tools :deep(.select-trigger) {
  width: 132px;
}

.imports__stats {
  display: flex;
  align-items: baseline;
  gap: 22px;
  padding: 16px 0 14px;
}

.imports__stat {
  font-size: 11px;
  color: var(--t3);
}

.imports__stat b {
  margin-right: 4px;
  font-size: 14px;
  font-weight: 500;
  color: var(--gold);
}

.imports__stat-note {
  margin-left: auto;
  font-size: 8px;
}

.imports__skeleton {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 10px;
}

.imports__table {
  border-top: 1px solid var(--line);
}

.imports__thead,
.import-row {
  display: grid;
  grid-template-columns: 96px 88px minmax(0, 1fr) 104px 24px;
  align-items: center;
  gap: 16px;
}

.imports__thead {
  height: 30px;
  border-bottom: 1px solid var(--line);
  font-family: var(--font-mono);
  font-size: 8px;
  letter-spacing: 0.08em;
  color: var(--t3);
}

.import-row {
  width: 100%;
  min-height: 52px;
  padding: 8px 4px;
  border-bottom: 1px solid var(--line);
  text-align: left;
  transition: background-color var(--d-base) var(--ease-out),
    transform var(--d-base) var(--ease-out);
}

.import-row--linked {
  cursor: pointer;
}

.import-row--linked:hover {
  transform: translateX(4px);
  background: color-mix(in srgb, var(--panel) 45%, transparent);
}

.import-row:disabled {
  cursor: default;
}

.import-row__time {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.02em;
  color: var(--t3);
}

.import-row__type {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--t3);
}

.import-row__main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.import-row__title {
  font-size: 13px;
  color: var(--t2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color var(--d-fast) var(--ease-out);
}

.import-row--linked:hover .import-row__title {
  color: var(--gold);
}

.import-row__source {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--t3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.import-row__status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--t3);
  white-space: nowrap;
}

.import-row__action {
  display: inline-flex;
  justify-content: flex-end;
  color: var(--t3);
}

.imports__pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding-top: 20px;
  font-size: 11px;
  color: var(--t3);
}

.imports__pager button {
  color: var(--t2);
}

.imports__pager button:disabled {
  color: var(--t3);
  opacity: 0.4;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 767px) {
  .imports {
    padding: 24px 16px 56px;
  }

  .imports__head {
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
  }

  .imports__title {
    font-size: 26px;
  }

  .imports__tools {
    width: 100%;
  }

  .imports__tools :deep(.select-field) {
    flex: 1;
  }

  .imports__thead {
    display: none;
  }

  .import-row {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 6px 12px;
    padding: 12px 2px;
  }

  .import-row__time {
    order: 2;
  }

  .import-row__type {
    order: 3;
  }

  .import-row__main {
    order: 1;
    grid-column: 1 / -1;
  }

  .import-row__status {
    order: 4;
  }

  .import-row__action {
    order: 5;
  }
}
</style>
