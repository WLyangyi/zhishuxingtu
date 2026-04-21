<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="importStore.showResultModal && importStore.currentTask?.result" class="modal-overlay" @click.self="handleClose">
        <div class="modal-container">
          <div class="modal-header">
            <h2 class="modal-title">导入结果</h2>
            <button class="close-btn" @click="handleClose">
              <X :size="20" />
            </button>
          </div>

          <div class="modal-body">
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
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="handleClose">取消</button>
            <button class="btn-primary" @click="handleSave" :disabled="saving">
              <Loader2 v-if="saving" :size="16" class="spinning" />
              <Check v-else :size="16" />
              <span>{{ saving ? '保存中...' : '保存为笔记' }}</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useImportStore } from '@/stores/import'
import { useFoldersStore } from '@/stores/folders'
import { importApi } from '@/api/import'
import { useNotificationStore } from '@/stores/notification'
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

<style scoped lang="scss">
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-container {
  width: 640px;
  max-height: 90vh;
  background: var(--bg-primary, #1a1a2e);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);

  .modal-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary, #fff);
    margin: 0;
  }

  .close-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    color: var(--text-muted, #888);
    transition: all 0.2s;
    background: transparent;
    border: none;
    cursor: pointer;

    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: var(--text-primary, #fff);
    }
  }
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.result-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary, #aaa);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.regen-btn {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: var(--text-muted, #666);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    color: var(--tech-blue, #0066FF);
    background: rgba(0, 102, 255, 0.1);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
}

.field-input {
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  font-size: 15px;
  color: var(--text-primary, #fff);
  outline: none;
  transition: all 0.2s;

  &:focus {
    border-color: var(--tech-blue, #0066FF);
    box-shadow: 0 0 0 3px rgba(0, 102, 255, 0.1);
  }
}

.field-textarea {
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-primary, #fff);
  outline: none;
  resize: vertical;
  font-family: inherit;
  line-height: 1.6;
  transition: all 0.2s;

  &:focus {
    border-color: var(--tech-blue, #0066FF);
    box-shadow: 0 0 0 3px rgba(0, 102, 255, 0.1);
  }
}

.key-points-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.key-point-item {
  display: flex;
  align-items: center;
  gap: 10px;

  .point-index {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 102, 255, 0.15);
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    color: var(--tech-blue, #0066FF);
    flex-shrink: 0;
  }

  .point-input {
    flex: 1;
    padding: 10px 12px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    font-size: 14px;
    color: var(--text-primary, #fff);
    outline: none;
    transition: all 0.2s;

    &:focus {
      border-color: var(--tech-blue, #0066FF);
    }
  }

  .remove-btn {
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
      background: rgba(239, 68, 68, 0.1);
      color: #ef4444;
    }
  }
}

.add-point-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: transparent;
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: var(--text-muted, #888);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--tech-blue, #0066FF);
    color: var(--tech-blue, #0066FF);
  }
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.tag-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(0, 102, 255, 0.1);
  border: 1px solid rgba(0, 102, 255, 0.2);
  border-radius: 20px;
  font-size: 13px;
  color: var(--tech-blue, #0066FF);

  .tag-remove {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    color: var(--tech-blue, #0066FF);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
    padding: 0;

    &:hover {
      background: rgba(239, 68, 68, 0.2);
      color: #ef4444;
    }
  }
}

.tag-input-wrapper {
  .tag-input {
    padding: 6px 12px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    font-size: 13px;
    color: var(--text-primary, #fff);
    outline: none;
    width: 100px;
    transition: all 0.2s;

    &:focus {
      border-color: var(--tech-blue, #0066FF);
      width: 140px;
    }

    &::placeholder {
      color: var(--text-muted, #666);
    }
  }
}

.folder-select {
  .folder-selector {
    width: 100%;
    padding: 10px 14px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    font-size: 14px;
    color: var(--text-primary, #fff);
    outline: none;
    cursor: pointer;
    transition: all 0.2s;
    appearance: none;

    &:focus {
      border-color: var(--tech-blue, #0066FF);
    }

    option {
      background: var(--bg-primary, #1a1a2e);
      color: var(--text-primary, #fff);
    }
  }
}

.source-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text-secondary, #aaa);

  a.source-link {
    color: var(--tech-blue, #0066FF);
    text-decoration: none;
    word-break: break-all;

    &:hover {
      text-decoration: underline;
    }
  }
}

.toggle-content-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 0;
  background: transparent;
  border: none;
  color: var(--text-muted, #888);
  font-size: 13px;
  cursor: pointer;
  transition: color 0.2s;

  &:hover {
    color: var(--tech-blue, #0066FF);
  }
}

.original-content {
  margin-top: 8px;
  padding: 12px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  max-height: 200px;
  overflow-y: auto;

  pre {
    font-size: 12px;
    color: var(--text-muted, #888);
    white-space: pre-wrap;
    word-break: break-all;
    margin: 0;
    font-family: 'JetBrains Mono', monospace;
  }
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.btn-secondary {
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: var(--text-secondary, #aaa);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: var(--text-primary, #fff);
  }
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--tech-blue, #0066FF);
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: #0052cc;
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;

  .modal-container {
    transform: scale(0.95) translateY(10px);
  }
}
</style>
