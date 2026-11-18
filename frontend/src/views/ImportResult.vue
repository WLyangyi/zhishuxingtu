<template>
  <AppModal
    :open="importStore.showResultModal && !!importStore.currentTask?.result"
    title="导入结果"
    size="lg"
    @update:open="(value) => !value && handleClose()"
  >
    <div class="result-section">
              <div class="field-group">
                <div class="field-header">
                  <label class="field-label">标题</label>
                  <button class="regen-btn" @click="regenerateField('title')" :disabled="regenerating" title="重新生成">
                    <RefreshCw :size="12" :class="{ spinning: regenerating }" />
                  </button>
                </div>
                <input v-model="editTitle" class="field-input" />
              </div>

              <div class="field-group">
                <div class="field-header">
                  <label class="field-label">摘要</label>
                  <button class="regen-btn" @click="regenerateField('summary')" :disabled="regenerating" title="重新生成">
                    <RefreshCw :size="12" :class="{ spinning: regenerating }" />
                  </button>
                </div>
                <textarea v-model="editSummary" class="field-textarea" rows="3"></textarea>
              </div>

              <div class="field-group">
                <div class="field-header">
                  <label class="field-label">关键要点</label>
                  <button class="regen-btn" @click="regenerateField('key_points')" :disabled="regenerating" title="重新生成">
                    <RefreshCw :size="12" :class="{ spinning: regenerating }" />
                  </button>
                </div>
                <div class="key-points-list">
                  <div v-for="(_point, index) in editKeyPoints" :key="index" class="key-point-item">
                    <span class="point-index">{{ index + 1 }}</span>
                    <input v-model="editKeyPoints[index]" class="point-input" />
                    <button class="remove-btn" @click="editKeyPoints.splice(index, 1)">
                      <X :size="14" />
                    </button>
                  </div>
                  <button class="add-point-btn" @click="editKeyPoints.push('')">
                    <Plus :size="14" />
                    <span>添加要点</span>
                  </button>
                </div>
              </div>

              <div class="field-group">
                <div class="field-header">
                  <label class="field-label">标签</label>
                  <button class="regen-btn" @click="regenerateField('tags')" :disabled="regenerating" title="重新生成">
                    <RefreshCw :size="12" :class="{ spinning: regenerating }" />
                  </button>
                </div>
                <div class="tags-list">
                  <span v-for="(tag, index) in editTags" :key="index" class="tag-item">
                    {{ tag }}
                    <button class="tag-remove" @click="editTags.splice(index, 1)">
                      <X :size="12" />
                    </button>
                  </span>
                  <div class="tag-input-wrapper">
                    <input
                      v-model="newTag"
                      class="tag-input"
                      placeholder="添加标签"
                      @keyup.enter="addTag"
                    />
                  </div>
                </div>
              </div>

              <div class="field-group">
                <label class="field-label">存储位置</label>
                <div class="folder-select">
                  <select v-model="selectedFolderId" class="folder-selector">
                    <option :value="null">根目录</option>
                    <option v-for="folder in folders" :key="folder.id" :value="folder.id">
                      {{ folder.name }}
                    </option>
                  </select>
                </div>
              </div>

              <div class="field-group">
                <label class="field-label">来源信息</label>
                <div class="source-info">
                  <div v-if="sourceInfo.filename" class="info-row">
                    <FileText :size="14" />
                    <span>{{ sourceInfo.filename }}</span>
                  </div>
                  <div v-if="sourceInfo.url" class="info-row">
                    <Globe :size="14" />
                    <a :href="sourceInfo.url" target="_blank" class="source-link">{{ sourceInfo.url }}</a>
                  </div>
                  <div v-if="sourceInfo.platform" class="info-row">
                    <Video :size="14" />
                    <span>{{ sourceInfo.platform }}</span>
                  </div>
                  <div v-if="sourceInfo.duration" class="info-row">
                    <Clock :size="14" />
                    <span>{{ formatDuration(sourceInfo.duration) }}</span>
                  </div>
                </div>
              </div>

              <div class="field-group">
                <button class="toggle-content-btn" @click="showOriginal = !showOriginal">
                  <ChevronDown v-if="!showOriginal" :size="16" />
                  <ChevronUp v-else :size="16" />
                  <span>{{ showOriginal ? '收起原始内容' : '查看原始提取内容' }}</span>
                </button>
                <div v-if="showOriginal" class="original-content">
                  <pre>{{ importStore.currentTask?.extracted_content || '无原始内容' }}</pre>
                </div>
              </div>
    </div>
    <template #footer>
      <AppButton variant="secondary" size="sm" @click="handleClose">取消</AppButton>
      <AppButton size="sm" :disabled="saving" @click="handleSave">
        <Loader2 v-if="saving" :size="16" class="spinning" />
        <Check v-else :size="16" />
        <span>{{ saving ? '保存中...' : '保存为笔记' }}</span>
      </AppButton>
    </template>
  </AppModal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useImportStore } from '@/stores/import'
import { useFoldersStore } from '@/stores/folders'
import { importApi } from '@/api/import'
import { useNotificationStore } from '@/stores/notification'
import { AppButton, AppModal } from '@/components/ui'
import { X, Plus, Check, FileText, Globe, Video, Clock, ChevronDown, ChevronUp, Loader2, RefreshCw } from 'lucide-vue-next'

const importStore = useImportStore()
const foldersStore = useFoldersStore()
const notification = useNotificationStore()

const editTitle = ref('')
const editSummary = ref('')
const editKeyPoints = ref<string[]>([])
const editTags = ref<string[]>([])
const newTag = ref('')
const showOriginal = ref(false)
const saving = ref(false)
const regenerating = ref(false)
const selectedFolderId = ref<string | null>(null)

const folders = computed(() => foldersStore.folders)

const sourceInfo = computed(() => {
  return importStore.currentTask?.result?.source_info || {} as any
})

watch(() => importStore.showResultModal, (visible) => {
  if (visible && importStore.currentTask?.result) {
    const result = importStore.currentTask.result
    editTitle.value = result.title
    editSummary.value = result.summary
    editKeyPoints.value = [...result.key_points]
    editTags.value = [...result.tags]
    showOriginal.value = false
    saving.value = false
    selectedFolderId.value = null
    foldersStore.fetchFolders()
  }
})

function addTag() {
  const tag = newTag.value.trim()
  if (tag && !editTags.value.includes(tag)) {
    editTags.value.push(tag)
    newTag.value = ''
  }
}

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}分${s}秒`
}

async function regenerateField(field: string) {
  if (!importStore.currentTask) return
  regenerating.value = true

  try {
    const response = await importApi.regenerate(importStore.currentTask.task_id)
    const data = response.data

    if (field === 'title' || field === 'all') {
      editTitle.value = data.result?.title || ''
    }
    if (field === 'summary' || field === 'all') {
      editSummary.value = data.result?.summary || ''
    }
    if (field === 'key_points' || field === 'all') {
      editKeyPoints.value = data.result?.key_points || []
    }
    if (field === 'tags' || field === 'all') {
      editTags.value = data.result?.tags || []
    }

    notification.success('重新生成成功')
  } catch (error: any) {
    notification.error('重新生成失败', error.response?.data?.detail || '请重试')
  } finally {
    regenerating.value = false
  }
}

async function handleSave() {
  if (!importStore.currentTask) return
  saving.value = true

  try {
    await importStore.saveAsNote({
      task_id: importStore.currentTask.task_id,
      title: editTitle.value,
      summary: editSummary.value,
      key_points: editKeyPoints.value.filter(p => p.trim()),
      tags: editTags.value,
      folder_id: selectedFolderId.value
    })
  } finally {
    saving.value = false
  }
}

function handleClose() {
  importStore.closeResultModal()
}
</script>

<style scoped>
.result-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.field-label {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.05em;
  color: var(--t3);
}

.regen-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: var(--r-sm);
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out), background var(--d-fast) var(--ease-out);
}

.regen-btn:hover:not(:disabled) {
  color: var(--gold);
  background: var(--gold-soft);
}

.regen-btn:disabled {
  opacity: 0.4;
}

.field-input,
.field-textarea,
.point-input,
.tag-input,
.folder-selector {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-body);
  font-size: var(--fs-micro);
  outline: none;
  transition: border-color var(--d-fast) var(--ease-out);
}

.field-input:focus,
.field-textarea:focus,
.point-input:focus,
.tag-input:focus,
.folder-selector:focus {
  border-color: var(--gold-line);
}

.field-textarea {
  line-height: 1.7;
  resize: vertical;
}

/* ---- 关键要点 ---- */
.key-points-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.key-point-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.point-index {
  flex: none;
  width: 18px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  text-align: right;
  color: var(--t3);
}

.point-input {
  flex: 1;
  min-width: 0;
}

.remove-btn {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: var(--r-sm);
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out), background var(--d-fast) var(--ease-out);
}

.remove-btn:hover {
  color: var(--danger);
  background: var(--danger-soft);
}

.add-point-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  align-self: flex-start;
  height: 26px;
  padding: 0 10px;
  border: 1px dashed var(--line-strong);
  border-radius: var(--r-sm);
  font-size: var(--fs-micro);
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out), border-color var(--d-fast) var(--ease-out);
}

.add-point-btn:hover {
  border-color: var(--gold-line);
  color: var(--gold);
}

/* ---- 标签 ---- */
.tags-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 6px 3px 9px;
  border: 1px solid var(--gold-line);
  border-radius: var(--r-pill);
  background: var(--gold-soft);
  font-size: var(--fs-micro);
  color: var(--gold);
}

.tag-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  color: var(--gold);
  opacity: 0.7;
}

.tag-remove:hover {
  opacity: 1;
}

.tag-input-wrapper {
  flex: 1;
  min-width: 120px;
}

.tag-input {
  padding: 5px 10px;
}

/* ---- 存储与来源 ---- */
.folder-selector {
  appearance: none;
  cursor: pointer;
}

.source-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bg);
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-micro);
  color: var(--t2);
}

.info-row svg {
  flex: none;
  color: var(--t3);
}

.source-link {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--gold);
  text-decoration: underline dotted;
}

/* ---- 原始内容 ---- */
.toggle-content-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  font-size: var(--fs-micro);
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out);
}

.toggle-content-btn:hover {
  color: var(--text);
}

.original-content {
  max-height: 220px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bg);
  overflow: auto;
}

.original-content pre {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1.7;
  color: var(--t2);
  white-space: pre-wrap;
  word-break: break-word;
}

/* ---- 底部 ---- */
.spinning {
  animation: spin 900ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
