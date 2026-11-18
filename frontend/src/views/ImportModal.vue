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
              <SegmentedControl
                :items="sourceItems"
                :model-value="activeTab"
                aria-label="导入来源"
                @update:model-value="activeTab = $event as 'pdf' | 'url' | 'video'"
              />
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
                <SegmentedControl
                  :items="videoItems"
                  :model-value="videoTab"
                  size="sm"
                  aria-label="视频来源"
                  @update:model-value="videoTab = $event as 'local' | 'online'"
                />

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
import { SegmentedControl } from '@/components/ui'
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

const sourceItems = [
  { label: 'PDF 文档', value: 'pdf' },
  { label: '网页链接', value: 'url' },
  { label: '视频', value: 'video' }
]

const videoItems = [
  { label: '本地视频', value: 'local' },
  { label: '在线视频', value: 'online' }
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

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--overlay);
  backdrop-filter: blur(6px);
}

.modal-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 560px;
  max-height: 88vh;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-lg);
  background: var(--panel);
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--line);
}

.modal-title {
  font-family: var(--font-display);
  font-size: var(--fs-title-3);
  font-weight: 600;
  letter-spacing: -0.01em;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: var(--r-sm);
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out), background var(--d-fast) var(--ease-out);
}

.close-btn:hover {
  color: var(--text);
  background: var(--panel-2);
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 20px;
  overflow-y: auto;
}

.source-tabs {
  display: flex;
}

/* ---- 拖拽区 ---- */
.upload-area,
.url-area,
.video-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.video-area :deep(.seg) {
  align-self: flex-start;
}

.video-area :deep(.seg) {
  align-self: flex-start;
}

.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 38px 20px;
  border: 1px dashed var(--line-strong);
  border-radius: var(--r-md);
  background: var(--bg);
  cursor: pointer;
  text-align: center;
  transition: border-color var(--d-fast) var(--ease-out), background var(--d-fast) var(--ease-out);
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: var(--gold-line);
  background: var(--gold-soft);
}

.drop-icon {
  color: var(--t3);
  margin-bottom: 4px;
}

.drop-zone.dragging .drop-icon,
.drop-zone:hover .drop-icon {
  color: var(--gold);
}

.drop-text {
  font-size: var(--fs-body-s);
  color: var(--t2);
}

.drop-hint {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--t3);
}

.hidden-input {
  display: none;
}

/* ---- 链接输入 ---- */
.input-group {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 12px;
  color: var(--t3);
  pointer-events: none;
}

.url-input {
  width: 100%;
  height: 40px;
  padding: 0 12px 0 38px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-mono);
  font-size: var(--fs-micro);
  outline: none;
  transition: border-color var(--d-fast) var(--ease-out);
}

.url-input::placeholder {
  color: var(--t3);
  font-family: var(--font-body);
}

.url-input:focus {
  border-color: var(--gold-line);
}

.input-hint {
  font-size: 10.5px;
  color: var(--t3);
}

/* ---- 进度 ---- */
.processing-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  padding: 10px 0 4px;
}

.progress-ring-container {
  position: relative;
  width: 128px;
  height: 128px;
}

.progress-ring {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.progress-ring-bg {
  fill: none;
  stroke: var(--line);
  stroke-width: 2;
}

.progress-ring-fill {
  fill: none;
  stroke: var(--gold);
  stroke-width: 2;
  stroke-linecap: round;
  transition: stroke-dashoffset 400ms var(--ease-out);
}

.progress-text {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 26px;
  color: var(--text);
}

.progress-message {
  font-size: var(--fs-micro);
  color: var(--t2);
  text-align: center;
}

.progress-steps {
  display: flex;
  flex-direction: column;
  gap: 0;
  width: 100%;
  max-width: 320px;
  border-top: 1px solid var(--line);
}

.step-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 2px;
  border-bottom: 1px solid var(--line);
}

.step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  color: var(--t3);
}

.step-item.done .step-indicator {
  color: var(--success);
}

.step-item.active .step-indicator {
  color: var(--gold);
}

.step-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--line-strong);
}

.step-label {
  font-size: var(--fs-micro);
  color: var(--t3);
}

.step-item.done .step-label {
  color: var(--t2);
}

.step-item.active .step-label {
  color: var(--text);
}

.spinning {
  animation: spin 900ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.cancel-btn {
  height: 30px;
  padding: 0 14px;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-sm);
  font-size: var(--fs-micro);
  color: var(--t2);
  transition: color var(--d-fast) var(--ease-out), border-color var(--d-fast) var(--ease-out);
}

.cancel-btn:hover {
  color: var(--danger);
  border-color: var(--danger-line);
}

/* ---- 进出场 ---- */
.modal-enter-active,
.modal-leave-active {
  transition: opacity var(--d-base) var(--ease-out);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform var(--d-base) var(--ease-out);
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: translateY(8px) scale(0.99);
}

@media (max-width: 767px) {
  .modal-overlay {
    padding: 12px;
  }

  .modal-container {
    max-height: 92vh;
  }

  .modal-body {
    padding: 16px;
  }

  .drop-zone {
    padding: 30px 16px;
  }
}
</style>
