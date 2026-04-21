<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="importStore.showImportModal" class="modal-overlay" @click.self="handleClose">
        <div class="modal-container">
          <div class="modal-header">
            <h2 class="modal-title">智能导入</h2>
            <button class="close-btn" @click="handleClose">
              <X :size="20" />
            </button>
          </div>

          <div class="modal-body">
            <div v-if="!importStore.isImporting" class="source-tabs">
              <button
                v-for="tab in tabs"
                :key="tab.key"
                class="tab-btn"
                :class="{ active: activeTab === tab.key }"
                @click="activeTab = tab.key"
              >
                <component :is="tab.icon" :size="18" />
                <span>{{ tab.label }}</span>
              </button>
            </div>

            <div v-if="!importStore.isImporting" class="tab-content">
              <div v-if="activeTab === 'pdf'" class="upload-area">
                <div
                  class="drop-zone"
                  :class="{ dragging: isDragging }"
                  @dragover.prevent="isDragging = true"
                  @dragleave.prevent="isDragging = false"
                  @drop.prevent="handlePdfDrop"
                  @click="pdfInputRef?.click()"
                >
                  <FileText :size="48" class="drop-icon" />
                  <p class="drop-text">拖拽 PDF 文件到此处，或点击选择</p>
                  <p class="drop-hint">支持 .pdf 格式，最大 200MB</p>
                  <input
                    ref="pdfInputRef"
                    type="file"
                    accept=".pdf"
                    class="hidden-input"
                    @change="handlePdfSelect"
                  />
                </div>
              </div>

              <div v-if="activeTab === 'url'" class="url-area">
                <div class="input-group">
                  <Globe :size="18" class="input-icon" />
                  <input
                    v-model="urlInput"
                    type="url"
                    placeholder="输入网页链接，如 https://arxiv.org/abs/..."
                    class="url-input"
                    @keyup.enter="handleUrlSubmit"
                  />
                </div>
                <p class="input-hint">支持学术论文、博客、技术文档等网页</p>
              </div>

              <div v-if="activeTab === 'video'" class="video-area">
                <div class="video-tabs">
                  <button
                    class="video-tab-btn"
                    :class="{ active: videoTab === 'local' }"
                    @click="videoTab = 'local'"
                  >本地视频</button>
                  <button
                    class="video-tab-btn"
                    :class="{ active: videoTab === 'online' }"
                    @click="videoTab = 'online'"
                  >在线视频</button>
                </div>

                <div v-if="videoTab === 'local'" class="upload-area">
                  <div
                    class="drop-zone"
                    :class="{ dragging: isDragging }"
                    @dragover.prevent="isDragging = true"
                    @dragleave.prevent="isDragging = false"
                    @drop.prevent="handleVideoDrop"
                    @click="videoInputRef?.click()"
                  >
                    <Video :size="48" class="drop-icon" />
                    <p class="drop-text">拖拽视频文件到此处，或点击选择</p>
                    <p class="drop-hint">支持 MP4/MKV/AVI/MOV，最大 200MB</p>
                    <input
                      ref="videoInputRef"
                      type="file"
                      accept=".mp4,.mkv,.avi,.mov"
                      class="hidden-input"
                      @change="handleVideoSelect"
                    />
                  </div>
                </div>

                <div v-if="videoTab === 'online'" class="url-area">
                  <div class="input-group">
                    <Youtube :size="18" class="input-icon" />
                    <input
                      v-model="videoUrlInput"
                      type="url"
                      placeholder="输入视频链接，如 YouTube、Bilibili..."
                      class="url-input"
                      @keyup.enter="handleVideoUrlSubmit"
                    />
                  </div>
                  <p class="input-hint">支持 YouTube、Bilibili、抖音等主流平台</p>
                </div>
              </div>
            </div>

            <div v-if="importStore.isImporting" class="processing-area">
              <div class="progress-ring-container">
                <svg class="progress-ring" viewBox="0 0 120 120">
                  <circle class="progress-ring-bg" cx="60" cy="60" r="52" />
                  <circle
                    class="progress-ring-fill"
                    cx="60" cy="60" r="52"
                    :stroke-dasharray="circumference"
                    :stroke-dashoffset="circumference - (progress / 100) * circumference"
                  />
                </svg>
                <div class="progress-text">{{ progress }}%</div>
              </div>
              <p class="progress-message">{{ importStore.currentTask?.progress_message || '处理中...' }}</p>
              <div class="progress-steps">
                <div
                  v-for="(step, index) in currentSteps"
                  :key="index"
                  class="step-item"
                  :class="getStepClass(index)"
                >
                  <div class="step-indicator">
                    <Check v-if="getStepStatus(index) === 'done'" :size="14" />
                    <Loader2 v-else-if="getStepStatus(index) === 'active'" :size="14" class="spinning" />
                    <div v-else class="step-dot"></div>
                  </div>
                  <span class="step-label">{{ step }}</span>
                </div>
              </div>
              <button class="cancel-btn" @click="handleCancel">取消导入</button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useImportStore } from '@/stores/import'
import { FileText, Globe, Video, X, Check, Loader2, Youtube } from 'lucide-vue-next'

const importStore = useImportStore()

const activeTab = ref<'pdf' | 'url' | 'video'>('pdf')
const videoTab = ref<'local' | 'online'>('local')
const isDragging = ref(false)
const urlInput = ref('')
const videoUrlInput = ref('')
const pdfInputRef = ref<HTMLInputElement | null>(null)
const videoInputRef = ref<HTMLInputElement | null>(null)

const MAX_FILE_SIZE = 200 * 1024 * 1024

const tabs = [
  { key: 'pdf' as const, label: 'PDF 文档', icon: FileText },
  { key: 'url' as const, label: '网页链接', icon: Globe },
  { key: 'video' as const, label: '视频', icon: Video }
]

const progress = computed(() => importStore.currentTask?.progress || 0)
const circumference = 2 * Math.PI * 52

const pdfSteps = ['解析文件', '提取内容', '分析内容', '生成摘要']
const urlSteps = ['访问网页', '提取正文', '分析内容', '生成摘要']
const videoSteps = ['解析视频', '提取字幕/音频', '转录内容', '生成摘要']

const currentSteps = computed(() => {
  const type = importStore.currentTask?.source_type
  if (type === 'pdf') return pdfSteps
  if (type === 'url') return urlSteps
  return videoSteps
})

function getStepStatus(index: number): 'done' | 'active' | 'pending' {
  const p = progress.value
  const stepCount = currentSteps.value.length
  const stepSize = 100 / stepCount
  const currentStep = Math.floor(p / stepSize)

  if (index < currentStep) return 'done'
  if (index === currentStep && p > 0) return 'active'
  return 'pending'
}

function getStepClass(index: number): string {
  return getStepStatus(index)
}

function handlePdfSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) validateAndUploadPdf(file)
}

function handlePdfDrop(event: DragEvent) {
  isDragging.value = false
  const file = event.dataTransfer?.files[0]
  if (file) validateAndUploadPdf(file)
}

function validateAndUploadPdf(file: File) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    alert('仅支持 PDF 文件')
    return
  }
  if (file.size > MAX_FILE_SIZE) {
    alert('文件超过 200MB 限制')
    return
  }
  importStore.uploadPdf(file)
}

function handleUrlSubmit() {
  const url = urlInput.value.trim()
  if (!url) return
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    alert('请输入有效的 URL')
    return
  }
  importStore.submitUrl(url)
}

function handleVideoSelect(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) validateAndUploadVideo(file)
}

function handleVideoDrop(event: DragEvent) {
  isDragging.value = false
  const file = event.dataTransfer?.files[0]
  if (file) validateAndUploadVideo(file)
}

function validateAndUploadVideo(file: File) {
  const ext = file.name.toLowerCase().split('.').pop()
  if (!ext || !['mp4', 'mkv', 'avi', 'mov'].includes(ext)) {
    alert('仅支持 MP4/MKV/AVI/MOV 格式')
    return
  }
  if (file.size > MAX_FILE_SIZE) {
    alert('文件超过 200MB 限制')
    return
  }
  importStore.uploadVideo(file)
}

function handleVideoUrlSubmit() {
  const url = videoUrlInput.value.trim()
  if (!url) return
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    alert('请输入有效的 URL')
    return
  }
  importStore.submitVideoUrl(url)
}

function handleCancel() {
  if (importStore.currentTask) {
    importStore.deleteTask(importStore.currentTask.task_id)
  }
  importStore.closeImportModal()
}

function handleClose() {
  if (importStore.isImporting) {
    handleCancel()
  } else {
    importStore.closeImportModal()
  }
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
  width: 560px;
  max-height: 90vh;
  background: var(--bg-primary, #1a1a2e);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  overflow: hidden;
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
  padding: 24px;
  overflow-y: auto;
}

.source-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  color: var(--text-secondary, #aaa);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.06);
    color: var(--text-primary, #fff);
  }

  &.active {
    background: rgba(0, 102, 255, 0.1);
    border-color: rgba(0, 102, 255, 0.3);
    color: var(--tech-blue, #0066FF);
  }
}

.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  border: 2px dashed rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;

  &:hover, &.dragging {
    border-color: var(--tech-blue, #0066FF);
    background: rgba(0, 102, 255, 0.05);
  }

  .drop-icon {
    color: var(--text-muted, #888);
    margin-bottom: 16px;
  }

  .drop-text {
    font-size: 15px;
    color: var(--text-secondary, #aaa);
    margin: 0 0 8px;
  }

  .drop-hint {
    font-size: 12px;
    color: var(--text-muted, #666);
    margin: 0;
  }
}

.hidden-input {
  display: none;
}

.url-area {
  .input-group {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 16px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    transition: all 0.2s;

    &:focus-within {
      border-color: var(--tech-blue, #0066FF);
      box-shadow: 0 0 0 3px rgba(0, 102, 255, 0.1);
    }

    .input-icon {
      color: var(--text-muted, #888);
      flex-shrink: 0;
    }

    .url-input {
      flex: 1;
      background: transparent;
      border: none;
      font-size: 14px;
      color: var(--text-primary, #fff);
      outline: none;

      &::placeholder {
        color: var(--text-muted, #666);
      }
    }
  }

  .input-hint {
    font-size: 12px;
    color: var(--text-muted, #666);
    margin: 8px 0 0;
  }
}

.video-area {
  .video-tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 16px;
  }

  .video-tab-btn {
    flex: 1;
    padding: 10px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    color: var(--text-secondary, #aaa);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s;

    &.active {
      background: rgba(0, 102, 255, 0.1);
      border-color: rgba(0, 102, 255, 0.3);
      color: var(--tech-blue, #0066FF);
    }
  }
}

.processing-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 24px 0;
}

.progress-ring-container {
  position: relative;
  width: 120px;
  height: 120px;
}

.progress-ring {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.progress-ring-bg {
  fill: none;
  stroke: rgba(255, 255, 255, 0.06);
  stroke-width: 8;
}

.progress-ring-fill {
  fill: none;
  stroke: var(--tech-blue, #0066FF);
  stroke-width: 8;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.5s ease;
}

.progress-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary, #fff);
}

.progress-message {
  font-size: 15px;
  color: var(--text-secondary, #aaa);
  margin: 0;
}

.progress-steps {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 8px;

  &.done {
    .step-indicator { color: #10b981; }
    .step-label { color: var(--text-secondary, #aaa); text-decoration: line-through; }
  }

  &.active {
    background: rgba(0, 102, 255, 0.05);
    .step-indicator { color: var(--tech-blue, #0066FF); }
    .step-label { color: var(--text-primary, #fff); font-weight: 500; }
  }

  &.pending {
    .step-indicator { color: var(--text-muted, #555); }
    .step-label { color: var(--text-muted, #555); }
  }
}

.step-indicator {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.step-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.step-label {
  font-size: 14px;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.cancel-btn {
  padding: 10px 24px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: var(--text-secondary, #aaa);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.3);
    color: #ef4444;
  }
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
