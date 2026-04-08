<template>
  <div class="prompts-page">
    <div class="page-header">
      <div class="header-left">
        <div class="header-top">
          <button @click="goBack" class="back-btn" title="返回">
            <ArrowLeft :size="18" />
          </button>
          <h1 class="page-title">
            <MessageSquare :size="28" class="title-icon" />
            提示词管理
          </h1>
        </div>
        <p class="page-subtitle">管理和配置 AI 提示词模板，优化 AI 输出质量</p>
      </div>
      <div class="header-actions">
        <button @click="initializePrompts" class="init-btn" :disabled="initializing">
          <RefreshCw :size="16" :class="{ spinning: initializing }" />
          {{ initializing ? '初始化中...' : '初始化默认提示词' }}
        </button>
        <button @click="showCreateModal = true" class="create-btn">
          <Plus :size="18" />
          创建提示词
        </button>
      </div>
    </div>

    <div class="templates-section">
      <h2 class="section-title">
        <Sparkles :size="18" class="title-icon" />
        模板库（系统预设不可修改）
      </h2>
      <div class="templates-grid">
        <div
          v-for="(template, index) in templates"
          :key="index"
          class="template-card"
        >
          <div class="template-icon">
            <BookOpen :size="24" />
          </div>
          <div class="template-info">
            <h3 class="template-name">{{ template.name }}</h3>
            <p class="template-desc">{{ template.description }}</p>
            <div class="template-meta">
              <span class="category-badge">{{ getCategoryLabel(template.category) }}</span>
              <span class="variable-count">{{ template.variables.length }} 个变量</span>
            </div>
          </div>
          <button @click="createFromTemplate(index)" class="use-template-btn" title="使用此模板创建">
            <Copy :size="16" />
          </button>
        </div>
      </div>
    </div>

    <div class="prompts-section">
      <div class="section-header">
        <h2 class="section-title">
          <FileText :size="18" class="title-icon" />
          我的提示词
        </h2>
        <div class="filter-tabs">
          <button
            :class="{ active: filterCategory === 'all' }"
            @click="filterCategory = 'all'"
          >
            全部
          </button>
          <button
            v-for="cat in availableCategories"
            :key="cat.value"
            :class="{ active: filterCategory === cat.value }"
            @click="filterCategory = cat.value"
          >
            {{ cat.label }}
          </button>
        </div>
      </div>

      <div class="prompts-grid">
        <div
          v-for="prompt in filteredPrompts"
          :key="prompt.id"
          class="prompt-card"
          :class="{ inactive: !prompt.is_active, system: prompt.is_system }"
        >
          <div class="card-content">
            <div class="card-header">
              <div class="prompt-info">
                <h3 class="prompt-name">
                  {{ prompt.name }}
                  <span v-if="prompt.is_system" class="system-badge">系统</span>
                  <span v-if="prompt.is_default" class="default-badge">默认</span>
                </h3>
                <span class="category-tag">{{ getCategoryLabel(prompt.category) }}</span>
              </div>
              <div class="prompt-actions">
                <button
                  v-if="!prompt.is_system"
                  @click="togglePromptStatus(prompt)"
                  class="action-btn"
                  :title="prompt.is_active ? '停用' : '启用'"
                >
                  <Pause v-if="prompt.is_active" :size="14" />
                  <Play v-else :size="14" />
                </button>
                <button
                  v-if="!prompt.is_system"
                  @click="editPrompt(prompt)"
                  class="action-btn"
                  title="编辑"
                >
                  <Edit3 :size="14" />
                </button>
                <button
                  v-if="!prompt.is_system"
                  @click="deletePrompt(prompt)"
                  class="action-btn danger"
                  title="删除"
                >
                  <Trash2 :size="14" />
                </button>
              </div>
            </div>

            <p class="prompt-description">{{ prompt.description || '暂无描述' }}</p>

            <div class="prompt-preview">
              <div class="preview-label">系统提示词预览：</div>
              <div class="preview-content">{{ truncateText(prompt.system_prompt, 150) }}</div>
            </div>

            <div class="card-footer">
              <span class="updated-time">
                <Clock :size="12" />
                {{ formatDate(prompt.updated_at) }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="filteredPrompts.length === 0" class="empty-state">
          <MessageSquare :size="48" class="empty-icon" />
          <h3>暂无自定义提示词</h3>
          <p>从模板库选择或创建自定义提示词</p>
        </div>
      </div>
    </div>

    <div v-if="showCreateModal" class="modal-overlay" @click.self="closeCreateModal">
      <div class="modal modal-large">
        <div class="modal-header">
          <h3>{{ editingPrompt ? '编辑提示词' : '创建提示词' }}</h3>
          <button @click="closeCreateModal" class="close-btn">
            <X :size="20" />
          </button>
        </div>
        <div class="modal-body">
          <div class="form-row">
            <div class="form-group">
              <label>提示词名称 <span class="required">*</span></label>
              <input v-model="promptForm.name" type="text" placeholder="输入提示词名称" />
            </div>
            <div class="form-group">
              <label>分类</label>
              <select v-model="promptForm.category">
                <option value="ai_chat">AI 对话</option>
                <option value="ai_search">AI 搜索</option>
                <option value="skill">技能模板</option>
                <option value="custom">自定义</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>描述</label>
            <input v-model="promptForm.description" type="text" placeholder="简短描述此提示词的用途" />
          </div>

          <div class="form-group">
            <label>系统提示词 (System Prompt) <span class="required">*</span></label>
            <div class="variable-hint">
              支持变量：{variable_name}，可用变量：current_date, current_weekday, context, question, conversation, content, resume_text
            </div>
            <textarea
              v-model="promptForm.system_prompt"
              placeholder="定义 AI 的角色、行为规则、限制等..."
              rows="8"
              class="code-textarea"
            ></textarea>
          </div>

          <div class="form-group">
            <label>用户提示词模板 (User Prompt Template)</label>
            <div class="variable-hint">
              用户输入将插入到此模板中，支持变量替换
            </div>
            <textarea
              v-model="promptForm.user_prompt_template"
              placeholder="可选，用于格式化用户输入..."
              rows="4"
              class="code-textarea"
            ></textarea>
          </div>

          <div class="form-group">
            <label>输出格式说明</label>
            <input v-model="promptForm.output_format" type="text" placeholder="描述期望的输出格式，如：JSON、自由文本等" />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="closeCreateModal" class="btn-cancel">取消</button>
          <button @click="handleSavePrompt" class="btn-confirm">
            {{ editingPrompt ? '保存' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notification'
import { promptsApi } from '@/api/prompts'
import type { Prompt, PromptTemplate, PromptCategory } from '@/types/prompt'
import { PROMPT_CATEGORIES } from '@/types/prompt'
import {
  ArrowLeft, MessageSquare, Plus, Sparkles, BookOpen, Copy,
  FileText, Edit3, Trash2, Play, Pause, Clock, X, RefreshCw
} from 'lucide-vue-next'

const router = useRouter()
const notification = useNotificationStore()

const templates = ref<PromptTemplate[]>([])
const prompts = ref<Prompt[]>([])
const categories = ref<PromptCategory[]>([])
const filterCategory = ref('all')
const showCreateModal = ref(false)
const editingPrompt = ref<Prompt | null>(null)
const initializing = ref(false)

const promptForm = ref<{
  name: string
  description: string
  category: string
  system_prompt: string
  user_prompt_template: string
  output_format: string
}>({
  name: '',
  description: '',
  category: 'ai_chat',
  system_prompt: '',
  user_prompt_template: '',
  output_format: ''
})

const availableCategories = computed(() => {
  const cats: PromptCategory[] = []
  prompts.value.forEach(p => {
    if (!cats.find(c => c.value === p.category)) {
      cats.push({ value: p.category, label: getCategoryLabel(p.category) })
    }
  })
  return cats
})

const filteredPrompts = computed(() => {
  if (filterCategory.value === 'all') return prompts.value
  return prompts.value.filter(p => p.category === filterCategory.value)
})

onMounted(async () => {
  await loadData()
})

async function loadData() {
  try {
    const [templatesRes, promptsRes, catsRes] = await Promise.all([
      promptsApi.getTemplates(),
      promptsApi.getPrompts(),
      promptsApi.getCategories()
    ])
    templates.value = templatesRes
    prompts.value = promptsRes.items
    categories.value = catsRes
  } catch (e) {
    console.error(e)
  }
}

async function initializePrompts() {
  initializing.value = true
  try {
    const result = await promptsApi.initializePrompts()
    notification.success('初始化成功', result.message)
    await loadData()
  } catch (e: any) {
    notification.error('初始化失败', e.response?.data?.detail || '操作失败')
  } finally {
    initializing.value = false
  }
}

async function createFromTemplate(index: number) {
  try {
    const prompt = await promptsApi.createFromTemplate(index)
    prompts.value.unshift(prompt as any)
    notification.success('创建成功', `「${prompt.name}」已添加到我的提示词`)
  } catch (e: any) {
    notification.error('创建失败', e.response?.data?.detail || '操作失败')
  }
}

function editPrompt(prompt: Prompt) {
  editingPrompt.value = prompt
  promptForm.value = {
    name: prompt.name,
    description: prompt.description || '',
    category: prompt.category,
    system_prompt: prompt.system_prompt,
    user_prompt_template: prompt.user_prompt_template,
    output_format: prompt.output_format
  }
  showCreateModal.value = true
}

async function handleSavePrompt() {
  if (!promptForm.value.name.trim()) {
    notification.warning('请输入提示词名称')
    return
  }
  if (!promptForm.value.system_prompt.trim()) {
    notification.warning('请输入系统提示词')
    return
  }

  try {
    if (editingPrompt.value) {
      const updated = await promptsApi.updatePrompt(editingPrompt.value.id, {
        name: promptForm.value.name,
        description: promptForm.value.description,
        category: promptForm.value.category,
        system_prompt: promptForm.value.system_prompt,
        user_prompt_template: promptForm.value.user_prompt_template,
        output_format: promptForm.value.output_format
      })
      const index = prompts.value.findIndex(p => p.id === editingPrompt.value!.id)
      if (index !== -1) {
        prompts.value[index] = updated as any
      }
      notification.success('保存成功')
    } else {
      const prompt = await promptsApi.createPrompt({
        name: promptForm.value.name,
        description: promptForm.value.description,
        category: promptForm.value.category,
        system_prompt: promptForm.value.system_prompt,
        user_prompt_template: promptForm.value.user_prompt_template,
        output_format: promptForm.value.output_format
      })
      prompts.value.unshift(prompt as any)
      notification.success('创建成功')
    }
    closeCreateModal()
  } catch (e: any) {
    notification.error('操作失败', e.response?.data?.detail || '操作失败')
  }
}

async function togglePromptStatus(prompt: Prompt) {
  try {
    const updated = await promptsApi.updatePrompt(prompt.id, { is_active: !prompt.is_active })
    const index = prompts.value.findIndex(p => p.id === prompt.id)
    if (index !== -1) {
      prompts.value[index] = updated as any
    }
    notification.success(updated.is_active ? '提示词已启用' : '提示词已停用')
  } catch (e: any) {
    notification.error('操作失败', e.response?.data?.detail || '操作失败')
  }
}

async function deletePrompt(prompt: Prompt) {
  if (!confirm(`确定要删除提示词「${prompt.name}」吗？`)) return

  try {
    await promptsApi.deletePrompt(prompt.id)
    prompts.value = prompts.value.filter(p => p.id !== prompt.id)
    notification.success('删除成功')
  } catch (e: any) {
    notification.error('删除失败', e.response?.data?.detail || '操作失败')
  }
}

function closeCreateModal() {
  showCreateModal.value = false
  editingPrompt.value = null
  promptForm.value = {
    name: '',
    description: '',
    category: 'ai_chat',
    system_prompt: '',
    user_prompt_template: '',
    output_format: ''
  }
}

function getCategoryLabel(category: string): string {
  return PROMPT_CATEGORIES[category] || category
}

function truncateText(text: string, maxLength: number): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.substring(0, maxLength) + '...'
}

function formatDate(date: string): string {
  const d = new Date(date)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function goBack() {
  router.back()
}
</script>

<style scoped lang="scss">
.prompts-page {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  background: var(--bg-primary);
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.header-top {
  display: flex;
  align-items: center;
  gap: 12px;
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
  font-size: 28px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-primary);

  .title-icon {
    color: var(--tech-blue);
  }
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.init-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--bg-hover);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: var(--bg-active);
    color: var(--text-primary);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .spinning {
    animation: spin 1s linear infinite;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.create-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: var(--primary-color);
  border: none;
  border-radius: var(--radius-md);
  color: #000;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: var(--primary-hover);
    transform: translateY(-1px);
  }
}

.templates-section, .prompts-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  color: var(--text-primary);

  .title-icon {
    color: var(--tech-blue);
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.filter-tabs {
  display: flex;
  gap: 8px;

  button {
    padding: 8px 16px;
    background: var(--bg-hover);
    border: 1px solid var(--border-subtle);
    border-radius: 20px;
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

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.template-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  position: relative;

  .template-icon {
    color: var(--tech-blue);
    flex-shrink: 0;
  }

  .template-info {
    flex: 1;
    min-width: 0;
  }

  .template-name {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 4px;
    color: var(--text-primary);
  }

  .template-desc {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 8px;
  }

  .template-meta {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .category-badge {
    padding: 2px 8px;
    background: var(--tech-blue-muted);
    color: var(--tech-blue);
    border-radius: 10px;
    font-size: 11px;
  }

  .variable-count {
    font-size: 11px;
    color: var(--text-muted);
  }

  .use-template-btn {
    position: absolute;
    top: 12px;
    right: 12px;
    width: 28px;
    height: 28px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-hover);
    border: none;
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    cursor: pointer;
    opacity: 0;
    transition: all 0.2s;

    &:hover {
      background: var(--primary-color);
      color: #000;
    }
  }

  &:hover .use-template-btn {
    opacity: 1;
  }
}

.prompts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 16px;
}

.prompt-card {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-xl);
  padding: 24px;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-2px);
    border-color: var(--border-default);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  }

  &.inactive {
    opacity: 0.6;
  }

  &.system {
    border-left: 3px solid var(--tech-blue);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
  }

  .prompt-name {
    font-size: 17px;
    font-weight: 600;
    margin-bottom: 6px;
    color: var(--text-primary);
    display: flex;
    align-items: center;
    gap: 8px;

    .system-badge, .default-badge {
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 10px;
      font-weight: 500;
    }

    .system-badge {
      background: var(--tech-blue-muted);
      color: var(--tech-blue);
    }

    .default-badge {
      background: rgba(16, 185, 129, 0.1);
      color: var(--accent-green);
    }
  }

  .category-tag {
    display: inline-block;
    padding: 3px 10px;
    background: var(--bg-hover);
    color: var(--text-muted);
    border-radius: 10px;
    font-size: 11px;
  }

  .prompt-actions {
    display: flex;
    gap: 6px;

    .action-btn {
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--bg-hover);
      border: none;
      border-radius: var(--radius-md);
      cursor: pointer;
      color: var(--text-secondary);
      transition: all 0.2s;

      &:hover {
        background: var(--bg-active);
        color: var(--text-primary);
      }

      &.danger:hover {
        background: rgba(239, 68, 68, 0.1);
        color: var(--accent-red);
      }
    }
  }

  .prompt-description {
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.6;
    margin-bottom: 16px;
  }

  .prompt-preview {
    background: var(--bg-hover);
    border-radius: var(--radius-md);
    padding: 12px;
    margin-bottom: 16px;

    .preview-label {
      font-size: 11px;
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    .preview-content {
      font-size: 12px;
      color: var(--text-secondary);
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }
  }

  .card-footer {
    display: flex;
    justify-content: flex-end;
  }

  .updated-time {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--text-muted);
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px;
  text-align: center;
  grid-column: 1 / -1;

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
  width: 500px;
  max-height: 80vh;
  overflow-y: auto;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-xl);

  &.modal-large {
    width: 700px;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid var(--border-subtle);

  h3 {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
  }

  .close-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-muted);
    cursor: pointer;

    &:hover {
      color: var(--text-primary);
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
    color: var(--text-secondary);
    margin-bottom: 8px;

    .required {
      color: var(--accent-red);
    }
  }

  input, textarea, select {
    width: 100%;
    padding: 10px 14px;
    background: var(--bg-hover);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-size: 14px;

    &:focus {
      outline: none;
      border-color: var(--tech-blue);
    }

    &::placeholder {
      color: var(--text-muted);
    }
  }

  textarea {
    resize: vertical;
    min-height: 80px;
  }

  select option {
    background: var(--bg-elevated);
  }

  .variable-hint {
    font-size: 11px;
    color: var(--text-muted);
    margin-bottom: 8px;
    padding: 8px;
    background: var(--bg-hover);
    border-radius: var(--radius-sm);
  }

  .code-textarea {
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 13px;
    line-height: 1.5;
  }
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid var(--border-subtle);
}

.btn-cancel, .btn-confirm {
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-secondary);

  &:hover {
    background: var(--bg-hover);
  }
}

.btn-confirm {
  background: var(--primary-color);
  border: none;
  color: #000;
  font-weight: 500;

  &:hover {
    background: var(--primary-hover);
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;
  }

  .prompts-grid, .templates-grid {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .modal-large {
    width: 95%;
  }
}
</style>
