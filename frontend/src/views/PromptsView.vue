<template>
  <div class="prompts-page">
    <PageHeader
      kicker="LAB · PROMPTS"
      title="提示词管理"
      description="管理系统模板与自定义提示词，控制 AI 的角色、规则与输出格式。"
    >
      <template #actions>
        <AppButton size="sm" variant="ghost" :disabled="initializing" @click="initializePrompts">
          <template #icon><RefreshCw :size="14" :class="initializing && 'spinning'" /></template>
          {{ initializing ? '初始化中…' : '初始化默认提示词' }}
        </AppButton>
        <AppButton size="sm" @click="showCreateModal = true">
          <template #icon><Plus :size="14" /></template>
          创建提示词
        </AppButton>
      </template>
    </PageHeader>

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
        <SegmentedControl
          :items="categoryItems"
          :model-value="filterCategory"
          size="sm"
          aria-label="按分类筛选"
          @update:model-value="filterCategory = $event"
        />
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

    <AppModal
      :open="showCreateModal"
      :title="editingPrompt ? '编辑提示词' : '创建提示词'"
      size="lg"
      @update:open="(value) => !value && closeCreateModal()"
    >
      <div class="prompt-form">
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

      <template #footer>
        <AppButton variant="secondary" size="sm" @click="closeCreateModal">取消</AppButton>
        <AppButton size="sm" @click="handleSavePrompt">
          {{ editingPrompt ? '保存' : '创建' }}
        </AppButton>
      </template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useNotificationStore } from '@/stores/notification'
import { AppButton, AppModal, PageHeader, SegmentedControl } from '@/components/ui'
import { promptsApi } from '@/api/prompts'
import type { Prompt, PromptTemplate, PromptCategory } from '@/types/prompt'
import { PROMPT_CATEGORIES } from '@/types/prompt'
import {
  MessageSquare, Plus, Sparkles, BookOpen, Copy,
  FileText, Edit3, Trash2, Play, Pause, Clock, RefreshCw
} from 'lucide-vue-next'

const notification = useNotificationStore()
const route = useRoute()

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

const categoryItems = computed(() => [
  { label: '全部', value: 'all' },
  ...availableCategories.value.map((item) => ({ label: item.label, value: item.value }))
])

onMounted(async () => {
  await loadData()
  // P2-5: 命令面板「打开提示词: X」通过 ?open= 直达并打开编辑弹窗
  const openId = route.query.open as string | undefined
  if (openId) {
    const target = prompts.value.find((prompt) => prompt.id === openId)
    if (target) editPrompt(target)
  }
})

async function loadData() {
  try {
    const [templatesRes, promptsRes, catsRes] = await Promise.all([
      promptsApi.getTemplates(),
      promptsApi.getPrompts(),
      promptsApi.getCategories()
    ])
    templates.value = templatesRes.data
    prompts.value = promptsRes.data.items
    categories.value = catsRes.data
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
    const response = await promptsApi.createFromTemplate(index)
    prompts.value.unshift(response.data as any)
    notification.success('创建成功', `「${response.data.name}」已添加到我的提示词`)
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
    const response = await promptsApi.updatePrompt(prompt.id, { is_active: !prompt.is_active })
    const index = prompts.value.findIndex(p => p.id === prompt.id)
    if (index !== -1) {
      prompts.value[index] = response.data as any
    }
    notification.success(response.data.is_active ? '提示词已启用' : '提示词已停用')
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

</script>

<style scoped>
.prompts-page {
  position: relative;
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 48px 72px;
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.templates-section,
.prompts-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: var(--fs-title-2);
  font-weight: 600;
  letter-spacing: -0.02em;
}

.section-title .title-icon {
  color: var(--t3);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--line);
}

/* ---- 模板库 ---- */
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 10px;
}

.template-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--panel);
  transition: border-color var(--d-fast) var(--ease-out);
}

.template-card:hover {
  border-color: var(--line-strong);
}

.template-icon {
  flex: none;
  margin-top: 2px;
  color: var(--gold);
}

.template-info {
  flex: 1;
  min-width: 0;
}

.template-name {
  font-size: var(--fs-body);
  font-weight: 500;
  line-height: 1.4;
}

.template-desc {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-top: 3px;
  font-size: var(--fs-micro);
  line-height: 1.7;
  color: var(--t2);
}

.template-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.category-badge {
  padding: 1px 7px;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-pill);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.04em;
  color: var(--t3);
}

.variable-count {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--t3);
}

.use-template-btn {
  flex: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out), border-color var(--d-fast) var(--ease-out);
}

.use-template-btn:hover {
  border-color: var(--gold-line);
  color: var(--gold);
}

/* ---- 我的提示词 ---- */
.prompts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}

.prompt-card {
  display: flex;
  flex-direction: column;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--panel);
  transition: border-color var(--d-fast) var(--ease-out);
}

.prompt-card:hover {
  border-color: var(--line-strong);
}

.prompt-card.inactive {
  opacity: 0.62;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 100%;
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.prompt-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.prompt-name {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: var(--fs-body);
  font-weight: 500;
  line-height: 1.4;
}

.system-badge,
.default-badge {
  padding: 1px 5px;
  border: 1px solid var(--line-strong);
  border-radius: var(--r-pill);
  font-family: var(--font-mono);
  font-size: 8.5px;
  letter-spacing: 0.04em;
  color: var(--t3);
}

.default-badge {
  border-color: var(--gold-line);
  color: var(--gold);
}

.category-tag {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--t3);
}

.prompt-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.action-btn {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-sm);
  color: var(--t3);
  transition: color var(--d-fast) var(--ease-out), background var(--d-fast) var(--ease-out);
}

.action-btn:hover {
  color: var(--text);
  background: var(--panel-2);
}

.action-btn.danger:hover {
  color: var(--danger);
  background: var(--danger-soft);
}

.prompt-description {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: var(--fs-micro);
  line-height: 1.7;
  color: var(--t2);
}

.prompt-preview {
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bg);
}

.preview-label {
  margin-bottom: 5px;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.05em;
  color: var(--t3);
}

.preview-content {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 10.5px;
  line-height: 1.7;
  color: var(--t2);
  white-space: pre-wrap;
  word-break: break-word;
}

.card-footer {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}

.updated-time {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--t3);
}

/* ---- 空态 ---- */
.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 56px 16px;
  text-align: center;
  border: 1px dashed var(--line);
  border-radius: var(--r-md);
  color: var(--t3);
}

.empty-icon {
  color: var(--line-strong);
}

.empty-state h3 {
  font-family: var(--font-display);
  font-size: var(--fs-body);
  font-weight: 500;
  color: var(--t2);
}

.empty-state p {
  font-size: var(--fs-micro);
  line-height: 1.7;
}

/* ---- 弹窗内表单 ---- */
.prompt-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.05em;
  color: var(--t3);
}

.required {
  color: var(--danger);
}

.form-group input,
.form-group select,
.form-group textarea {
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

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  border-color: var(--gold-line);
}

.form-group textarea {
  line-height: 1.7;
  resize: vertical;
}

.code-textarea {
  font-family: var(--font-mono);
  font-size: 11px;
}

.variable-hint {
  margin-bottom: 6px;
  padding: 6px 8px;
  border-left: 1px solid var(--gold-line);
  background: var(--gold-soft);
  font-family: var(--font-mono);
  font-size: 9.5px;
  line-height: 1.7;
  color: var(--t3);
}

.spinning {
  animation: spin 900ms linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 1024px) {
  .prompts-page {
    padding: 28px 24px 64px;
  }
}

@media (max-width: 767px) {
  .prompts-page {
    padding: 24px 16px 56px;
    gap: 24px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .templates-grid,
  .prompts-grid {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .modal {
    max-height: 92vh;
  }
}
</style>
