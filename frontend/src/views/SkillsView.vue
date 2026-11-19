<template>
  <div class="skills-page">
    <PageHeader
      kicker="LAB · SKILLS"
      title="Skill 智能模块"
      description="把重复的知识处理流程固化为可执行技能，支持手动触发与定时运行。"
    >
      <template #actions>
        <AppButton size="sm" @click="showCreateModal = true">
          <template #icon><Plus :size="14" /></template>
          创建 Skill
        </AppButton>
      </template>
    </PageHeader>

    <div class="templates-section">
      <h2 class="section-title">
        <Package :size="18" class="title-icon" />
        模板库
      </h2>
      <div class="templates-grid">
        <div 
          v-for="(template, index) in templates" 
          :key="index"
          class="template-card"
          @click="createFromTemplate(index)"
        >
          <div class="template-icon" :style="{ color: template.color }">
            <Sparkles :size="28" />
          </div>
          <div class="template-info">
            <h3 class="template-name">{{ template.name }}</h3>
            <p class="template-desc">{{ template.description }}</p>
          </div>
          <div class="template-badge" :style="{ backgroundColor: template.color + '20', color: template.color }">
            {{ template.trigger_type === 'manual' ? '手动' : '定时' }}
          </div>
        </div>
      </div>
    </div>

    <div class="skills-section">
      <div class="section-header">
        <h2 class="section-title">
          <Rocket :size="18" class="title-icon" />
          我的 Skills
        </h2>
        <SegmentedControl
          :items="filterItems"
          :model-value="filterType"
          size="sm"
          aria-label="按触发方式筛选"
          @update:model-value="filterType = $event as 'all' | 'manual' | 'scheduled'"
        />
      </div>

      <div class="skills-grid">
        <div 
          v-for="skill in filteredSkills" 
          :key="skill.id"
          class="skill-card"
          :class="{ inactive: !skill.is_active }"
        >
          <div class="card-content">
            <div class="card-header">
              <span class="skill-icon" :style="{ color: skill.color }">
                <Zap :size="24" />
              </span>
              <div class="skill-info">
                <h3 class="skill-name">{{ skill.name }}</h3>
                <span class="skill-type" :style="{ backgroundColor: skill.color + '20', color: skill.color }">
                  {{ skill.trigger_type === 'manual' ? '手动触发' : '定时执行' }}
                </span>
              </div>
              <div class="skill-actions">
                <button @click="toggleSkillStatus(skill)" class="action-btn" :title="skill.is_active ? '停用' : '启用'">
                  <Pause v-if="skill.is_active" :size="14" />
                  <Play v-else :size="14" />
                </button>
                <button @click="editSkill(skill)" class="action-btn" title="编辑">
                  <Edit3 :size="14" />
                </button>
                <button @click="deleteSkill(skill)" class="action-btn danger" title="删除">
                  <Trash2 :size="14" />
                </button>
              </div>
            </div>
            
            <p class="skill-description">{{ skill.description || '暂无描述' }}</p>
            
            <div class="card-footer">
              <div class="skill-meta">
                <span class="meta-item">
                  <BarChart3 :size="12" />
                  {{ skill.execution_count || 0 }} 次执行
                </span>
                <span class="meta-item">
                  <Calendar :size="12" />
                  {{ formatDate(skill.updated_at) }}
                </span>
              </div>
              <button @click="executeSkill(skill)" class="execute-btn" :disabled="!skill.is_active">
                <Play :size="14" />
                执行
              </button>
            </div>
          </div>
        </div>

        <div v-if="filteredSkills.length === 0" class="empty-state">
          <Zap :size="48" class="empty-icon" />
          <h3>暂无 Skill</h3>
          <p>从模板库选择或创建自定义 Skill</p>
        </div>
      </div>
    </div>

    <AppModal
      :open="showCreateModal"
      title="创建 Skill"
      size="md"
      @update:open="(value) => (showCreateModal = value)"
    >
      <div class="skill-form">
        <div class="form-group">
          <label>Skill 名称</label>
          <input v-model="newSkill.name" type="text" placeholder="输入 Skill 名称" />
        </div>
        <div class="form-group">
          <label>描述</label>
          <textarea v-model="newSkill.description" placeholder="描述这个 Skill 的功能"></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>图标</label>
            <input v-model="newSkill.icon" type="text" placeholder="如：⚡" />
          </div>
          <div class="form-group">
            <label>颜色</label>
            <div class="color-picker">
              <span
                v-for="color in colorOptions"
                :key="color"
                class="color-dot"
                :class="{ active: newSkill.color === color }"
                :style="{ backgroundColor: color }"
                @click="newSkill.color = color"
              />
            </div>
          </div>
        </div>
        <div class="form-group">
          <label>触发类型</label>
          <select v-model="newSkill.trigger_type">
            <option value="manual">手动触发</option>
            <option value="scheduled">定时执行</option>
          </select>
        </div>
        <div class="form-group">
          <label>输出分类</label>
          <select v-model="newSkill.output_category_id">
            <option :value="null">不保存到知识库</option>
            <option v-for="cat in categoryStore.categories" :key="cat.id" :value="cat.id">
              {{ cat.name }}
            </option>
          </select>
        </div>
      </div>
      <template #footer>
        <AppButton variant="secondary" size="sm" @click="showCreateModal = false">取消</AppButton>
        <AppButton size="sm" @click="handleCreateSkill">创建</AppButton>
      </template>
    </AppModal>

    <AppModal
      :open="showExecuteModal"
      :title="`执行 Skill: ${currentSkill?.name ?? ''}`"
      size="md"
      @update:open="(value) => (showExecuteModal = value)"
    >
      <div class="skill-form">
        <div class="form-group">
          <label>输入数据 (JSON 格式)</label>
          <textarea
            v-model="executeInput"
            placeholder='{"key": "value"}'
            rows="6"
          ></textarea>
        </div>
        <div v-if="executeResult" class="execute-result">
          <h4>执行结果</h4>
          <pre>{{ JSON.stringify(executeResult, null, 2) }}</pre>
        </div>
      </div>
      <template #footer>
        <AppButton variant="secondary" size="sm" @click="showExecuteModal = false">关闭</AppButton>
        <AppButton size="sm" :disabled="executing" @click="handleExecuteSkill">
          {{ executing ? '执行中...' : '执行' }}
        </AppButton>
      </template>
    </AppModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useCategoryStore } from '@/stores/category'
import { AppButton, AppModal, PageHeader, SegmentedControl } from '@/components/ui'
import { useNotificationStore } from '@/stores/notification'
import { skillsApi } from '@/api/skills'
import type { Skill, SkillTemplate } from '@/types/skill'
import {
  Zap, Plus, Package, Sparkles, Play, Pause,
  Edit3, Trash2, BarChart3, Calendar, Rocket
} from 'lucide-vue-next'

const categoryStore = useCategoryStore()
const notification = useNotificationStore()
const route = useRoute()

const templates = ref<SkillTemplate[]>([])
const skills = ref<Skill[]>([])
const filterType = ref<'all' | 'manual' | 'scheduled'>('all')
const showCreateModal = ref(false)
const showExecuteModal = ref(false)
const currentSkill = ref<Skill | null>(null)
const executeInput = ref('{}')
const executeResult = ref<any>(null)
const executing = ref(false)

const newSkill = ref({
  name: '',
  description: '',
  icon: '⚡',
  color: '',
  trigger_type: 'manual',
  output_category_id: null as string | null
})

// 色板取自设计令牌，避免在组件里散落 hex；值在挂载时读取。
const SWATCH_TOKENS = ['--gold', '--steel', '--sage', '--danger', '--success']
const colorOptions = ref<string[]>([])

const filterItems = [
  { label: '全部', value: 'all' },
  { label: '手动', value: 'manual' },
  { label: '定时', value: 'scheduled' }
]

function loadSwatches() {
  const styles = getComputedStyle(document.documentElement)
  colorOptions.value = SWATCH_TOKENS.map((token) => styles.getPropertyValue(token).trim()).filter(Boolean)
  if (!newSkill.value.color) newSkill.value.color = colorOptions.value[0] ?? ''
}

const filteredSkills = computed(() => {
  if (filterType.value === 'all') return skills.value
  return skills.value.filter(s => s.trigger_type === filterType.value)
})

onMounted(async () => {
  loadSwatches()
  await Promise.all([
    loadTemplates(),
    loadSkills(),
    categoryStore.fetchCategories()
  ])
  // P2-5: 命令面板「执行 Skill: X」通过 ?execute= 直达并打开执行弹窗
  const executeId = route.query.execute as string | undefined
  if (executeId) {
    const target = skills.value.find((skill) => skill.id === executeId)
    if (target) executeSkill(target)
  }
})

async function loadTemplates() {
  try {
    templates.value = await skillsApi.getTemplates()
  } catch (e) {
    console.error(e)
  }
}

async function loadSkills() {
  try {
    const response = await skillsApi.getSkills()
    skills.value = response.items
  } catch (e) {
    console.error(e)
  }
}

async function createFromTemplate(index: number) {
  try {
    const skill = await skillsApi.createFromTemplate(index)
    skills.value.unshift(skill as any)
    notification.success('Skill 创建成功', `「${skill.name}」已添加`)
  } catch (e: any) {
    notification.error('创建失败', e.response?.data?.detail || '操作失败')
  }
}

async function handleCreateSkill() {
  if (!newSkill.value.name.trim()) {
    notification.warning('请输入 Skill 名称')
    return
  }

  try {
    const skill = await skillsApi.createSkill({
      name: newSkill.value.name,
      description: newSkill.value.description,
      icon: newSkill.value.icon,
      color: newSkill.value.color,
      trigger_type: newSkill.value.trigger_type,
      output_category_id: newSkill.value.output_category_id || undefined
    })
    skills.value.unshift(skill as any)
    showCreateModal.value = false
    notification.success('Skill 创建成功')
    resetNewSkill()
  } catch (e: any) {
    notification.error('创建失败', e.response?.data?.detail || '操作失败')
  }
}

function resetNewSkill() {
  newSkill.value = {
    name: '',
    description: '',
    icon: '⚡',
    color: colorOptions.value[0] ?? '',
    trigger_type: 'manual',
    output_category_id: null
  }
}

async function toggleSkillStatus(skill: Skill) {
  try {
    const updated = await skillsApi.updateSkill(skill.id, { is_active: !skill.is_active })
    const index = skills.value.findIndex(s => s.id === skill.id)
    if (index !== -1) {
      skills.value[index] = updated as any
    }
    notification.success(updated.is_active ? 'Skill 已启用' : 'Skill 已停用')
  } catch (e: any) {
    notification.error('操作失败', e.response?.data?.detail || '操作失败')
  }
}

function editSkill(_skill: Skill) {
  notification.info('功能开发中', 'Skill 编辑功能即将上线')
}

async function deleteSkill(skill: Skill) {
  if (!confirm(`确定要删除 Skill「${skill.name}」吗？`)) return

  try {
    await skillsApi.deleteSkill(skill.id)
    skills.value = skills.value.filter(s => s.id !== skill.id)
    notification.success('Skill 已删除')
  } catch (e: any) {
    notification.error('删除失败', e.response?.data?.detail || '操作失败')
  }
}

function executeSkill(skill: Skill) {
  currentSkill.value = skill
  executeInput.value = '{}'
  executeResult.value = null
  showExecuteModal.value = true
}

async function handleExecuteSkill() {
  if (!currentSkill.value) return

  let inputData = {}
  try {
    inputData = JSON.parse(executeInput.value)
  } catch (e) {
    notification.warning('输入数据格式错误', '请输入有效的 JSON 格式')
    return
  }

  executing.value = true
  try {
    const result = await skillsApi.executeSkill(currentSkill.value.id, { input_data: inputData })
    executeResult.value = result.output_data
    notification.success('Skill 执行成功')
  } catch (e: any) {
    notification.error('执行失败', e.response?.data?.detail || '操作失败')
  } finally {
    executing.value = false
  }
}

function formatDate(date: string): string {
  const d = new Date(date)
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

</script>

<style scoped>
.skills-page {
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
.skills-section {
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
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 10px;
}

.template-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--panel);
  cursor: pointer;
  transition: border-color var(--d-fast) var(--ease-out), background var(--d-fast) var(--ease-out);
}

.template-card:hover {
  border-color: var(--gold-line);
  background: var(--panel-2);
}

.template-icon {
  flex: none;
  display: inline-flex;
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

.template-badge {
  flex: none;
  padding: 2px 8px;
  border-radius: var(--r-pill);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.04em;
}

/* ---- 我的 Skills ---- */
.skills-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}

.skill-card {
  display: flex;
  flex-direction: column;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--panel);
  transition: border-color var(--d-fast) var(--ease-out);
}

.skill-card:hover {
  border-color: var(--line-strong);
}

.skill-card.inactive {
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
  gap: 10px;
}

.skill-icon {
  flex: none;
  display: inline-flex;
  margin-top: 1px;
}

.skill-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.skill-name {
  font-size: var(--fs-body);
  font-weight: 500;
  line-height: 1.4;
}

.skill-type {
  padding: 1px 7px;
  border-radius: var(--r-pill);
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.04em;
}

.skill-actions {
  flex: none;
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

.skill-description {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  font-size: var(--fs-micro);
  line-height: 1.7;
  color: var(--t2);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}

.skill-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--t3);
}

.execute-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 12px;
  border: 1px solid var(--gold-line);
  border-radius: var(--r-sm);
  font-size: var(--fs-micro);
  color: var(--gold);
  transition: background var(--d-fast) var(--ease-out);
}

.execute-btn:hover:not(:disabled) {
  background: var(--gold-soft);
}

.execute-btn:disabled {
  border-color: var(--line);
  color: var(--t3);
  cursor: not-allowed;
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
.skill-form {
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
  font-family: var(--font-mono);
  line-height: 1.7;
  resize: vertical;
}

.color-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
}

.color-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color var(--d-fast) var(--ease-out), transform var(--d-fast) var(--ease-out);
}

.color-dot:hover {
  transform: scale(1.1);
}

.color-dot.active {
  outline: 1px solid var(--gold);
  outline-offset: 2px;
}

.execute-result {
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--bg);
}

.execute-result h4 {
  margin-bottom: 6px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.05em;
  color: var(--t3);
}

.execute-result pre {
  max-height: 260px;
  margin: 0;
  overflow: auto;
  font-family: var(--font-mono);
  font-size: 10px;
  line-height: 1.7;
  color: var(--t2);
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 1024px) {
  .skills-page {
    padding: 28px 24px 64px;
  }
}

@media (max-width: 767px) {
  .skills-page {
    padding: 24px 16px 56px;
    gap: 24px;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .templates-grid,
  .skills-grid {
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
